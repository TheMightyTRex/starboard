"""Starboard's API for a plug-in on its own network (DASH-482): a Unix socket in the plug-in's run folder.

Starboard runs on the computer's own network (network_mode host), so it cannot join a plug-in's internal network,
and a plug-in there has no way to reach Starboard's port. Instead Starboard listens on run/api.sock inside the
plug-in's folder, which each of its containers already mounts as /run/starboard, so the plug-in reaches the API at
/run/starboard/api.sock (STARBOARD_API_SOCKET) and nothing else: its network stays internal, and no extra container
or opening in the firewall is needed.

What the socket answers: only /api/v1, only with that plug-in's own key (its scopes as approved, the same checks as
over HTTP: rate limits, refused keys counted, audit). Another plug-in's key, or a key a person made, is refused, so a
plug-in cannot borrow wider rights through it. The run folder sits inside the plug-in's 0700 folder, so only
Starboard and the plug-in's own containers reach the socket; it is 0666 so any user a container runs as may connect.

Light on small servers: one thread for every plug-in's socket together, which sleeps until a plug-in connects (no
polling), and a thread for each request while it is answered, as on Starboard's own port.
"""
import os
import selectors
import socket
import socketserver
import stat
import threading
import urllib.parse

from . import logs

NAME = "api.sock"  # in run/, so /run/starboard/api.sock inside the plug-in's containers
IN_CONTAINER = "/run/starboard/" + NAME
MAX_PATH = 107  # a Unix socket's address holds at most 107 bytes on Linux; a longer path goes through /proc
SLOTS = threading.BoundedSemaphore(16)  # requests from every plug-in at once; more wait their turn

_lock = threading.Lock()
_state = {"app": None, "handler": None, "selector": None, "wake": None, "thread": None}
_servers = {}  # plug-in id -> its listening server


def path_for(data_dir, pid):
    from . import plugins_admin
    return os.path.join(plugins_admin.folder(data_dir, pid), "run", NAME)


def _key_id(data_dir, pid):
    from . import plugins_admin
    st = plugins_admin._read(os.path.join(plugins_admin.folder(data_dir, pid), "state.json"), {}) or {}
    return st.get("key_id")


class _Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    block_on_close = False

    def __init__(self, path, handler, pid):
        self.pid = pid
        super().__init__(path, handler)

    def get_request(self):
        conn, _ = self.socket.accept()
        return conn, (f"plugin:{self.pid}", 0)  # the address the API's limits and audit lines name

    def process_request(self, request, client_address):
        if not SLOTS.acquire(timeout=10):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            SLOTS.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            SLOTS.release()


def handler_for(base):
    """Starboard's own request handler, answering only /api/v1 and only to the plug-in's own key."""
    from . import api_v1

    class PluginHandler(base):
        disable_nagle_algorithm = False  # a Unix socket has no Nagle algorithm to turn off
        via_socket = True  # a key made only for the socket (DASH-603) is accepted here and nowhere else

        def client_address_text(self):
            return self.client_address[0]

        def local_only_refused(self):
            return False  # only the plug-in's own containers reach this socket

        def host_refused(self):
            return False  # no web page can reach a Unix socket, so there is no DNS rebinding to guard against

        def is_https(self):
            return False

        def do_GET(self):
            self.plugin_api("GET")

        def do_POST(self):
            self.plugin_api("POST")

        def do_PUT(self):
            self.plugin_api("PUT")

        def do_DELETE(self):
            self.plugin_api("DELETE")

        def plugin_api(self, method):
            path = urllib.parse.urlparse(self.path).path
            if method != "GET":
                self.close_connection = True  # its body may not be read
            if not (path.startswith("/api/v1/") or path == "/api/v1"):
                self.close_connection = True
                return self.send(404, b"Only Starboard's API v1 answers here", "text/plain; charset=utf-8")
            pid = self.server.pid
            k = api_v1.find_key(self.app.data_dir, self.headers.get("Authorization"))
            if k and k["id"] != _key_id(self.app.data_dir, pid):
                self.close_connection = True
                api_v1.audit(self.app.data_dir, "key_refused", address=self.client_address_text(), path=path[:100])
                self.app.limits.attempt(self.client_address_text())
                return self.json(401, {"title": "This socket answers only to this plug-in's own key", "status": 401,
                                       "code": "key_needed"}, {"WWW-Authenticate": 'Bearer realm="starboard"'})
            return api_v1.handle(self, method, path)

    return PluginHandler


def start(app):
    """Called once at start: listens for every plug-in that is on. Later, enable() and disable() call serve() and
    stop() for one plug-in."""
    from . import plugins_admin, server
    with _lock:
        if _state["app"] is not None:
            return
        _state["app"] = app
        _state["handler"] = handler_for(type("BoundHandler", (server.Handler,), {"app": app}))
        if _state["selector"] is None:  # one thread for the life of the process
            _state["selector"] = selectors.DefaultSelector()
            r, w = socket.socketpair()
            r.setblocking(False)
            _state["wake"] = (r, w)
            _state["selector"].register(r, selectors.EVENT_READ, None)
            _state["thread"] = threading.Thread(target=_loop, name="plugin-sockets", daemon=True)
            _state["thread"].start()
    for p in plugins_admin.basics(app.data_dir):
        if p.get("state") == "enabled" and not plugins_admin._runs_nothing(app.data_dir, p["id"]):
            serve(app.data_dir, p["id"])


def running():
    return _state["app"] is not None


def serve(data_dir, pid):
    """Listens on the plug-in's run/api.sock. True when listening; False when Starboard is not serving sockets here
    (tests, a command run by hand) or the socket could not be made, which is logged."""
    app = _state["app"]
    if app is None or os.path.abspath(data_dir) != os.path.abspath(app.data_dir):
        return False
    path = path_for(data_dir, pid)
    with _lock:
        if pid in _servers and os.path.exists(path):
            return True
        _close(pid)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            _remove_socket(path)
            srv = _bind(path, pid)
            os.chmod(path, 0o666)  # nosec B103: inside the plug-in's 0700 folder; any container user may connect
        except OSError as e:
            logs.event("warning", "plugins", f"Could not open the API socket for the plug-in {pid} ({e})")
            return False
        srv.socket.setblocking(False)
        _servers[pid] = srv
        _state["selector"].register(srv.socket, selectors.EVENT_READ, srv)
        _state["wake"][1].send(b"x")
    return True


def _bind(path, pid):
    """The listening server at path. A path longer than a socket's address can hold (a data folder deep in a home
    folder) is reached through the folder's open handle in /proc instead, which is short."""
    if len(path.encode()) <= MAX_PATH:
        srv = _Server(path, _state["handler"], pid)
    else:
        fd = os.open(os.path.dirname(path), os.O_RDONLY | os.O_DIRECTORY)
        try:
            srv = _Server(f"/proc/self/fd/{fd}/{NAME}", _state["handler"], pid)
        finally:
            os.close(fd)
    srv.path = path
    return srv


def stop(pid):
    """Stops listening for the plug-in and removes its socket file. Safe when it was not listening."""
    with _lock:
        _close(pid)


def _close(pid):
    srv = _servers.pop(pid, None)
    if srv is None:
        return
    try:
        _state["selector"].unregister(srv.socket)
    except (KeyError, ValueError):
        pass
    srv.server_close()
    _remove_socket(srv.path)


def _remove_socket(path):
    """Removes an old socket file, never anything else that may have that name."""
    try:
        if stat.S_ISSOCK(os.lstat(path).st_mode):
            os.unlink(path)
    except OSError:
        pass


def _loop():
    sel, (wake, _) = _state["selector"], _state["wake"]
    while True:
        for key, _events in sel.select():
            if key.data is None:
                try:
                    wake.recv(64)
                except OSError:
                    pass
                continue
            srv = key.data
            try:
                request, address = srv.get_request()
            except OSError:
                continue  # closed while waiting, or another wake-up took it
            request.setblocking(True)
            try:
                srv.process_request(request, address)
            except Exception:  # noqa: BLE001 - one bad connection never stops the others
                srv.shutdown_request(request)


def _reset_for_tests():
    """Stops every socket and forgets the app, so a test can start again."""
    with _lock:
        for pid in list(_servers):
            _close(pid)
        _state.update(app=None, handler=None)
