"""Run with: python -m starboard  (settings: STARBOARD_PORT, STARBOARD_DATA; STARBOARD_HOST fixes the address)."""

import os
import threading

from .server import App, make_server


class Runner:
    """Keeps one listener running, and moves it when Settings turns network access on or off."""

    def __init__(self, app):
        self.app = app
        self.server = None
        self.host = None
        self.lock = threading.Lock()
        app.on_network_change = self.rebind

    def start(self, host=None):
        host = host or self.app.listen_host()
        self.server, _ = make_server(host, self.app.port, self.app)
        self.host = host
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        where = "this computer only" if host.startswith("127.") else "your network"
        print(f"[starboard] {self.app.version} listening on http://{host}:{self.app.port} ({where})", flush=True)
        return thread

    def rebind(self):
        with self.lock:
            old_host = self.host
            self.server.shutdown()
            self.server.server_close()
            try:
                self.start()
            except OSError as e:
                print(f"[starboard] Could not move the listener ({e}); going back to {old_host}", flush=True)
                self.start(old_host)


def main():
    data_dir = os.environ.get("STARBOARD_DATA", os.path.join(os.path.expanduser("~"), ".local", "share", "starboard"))
    runner = Runner(App(data_dir))
    runner.start()
    stop = threading.Event()
    try:
        stop.wait()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
