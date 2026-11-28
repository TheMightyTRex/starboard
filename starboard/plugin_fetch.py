"""Fetch from named sites for a plug-in (plug-in API 1.25, DASH-620).

A plug-in that was approved the permission `fetch` lists the sites it may reach in its manifest (`"fetch": ["api.openverse.org"]`).
It keeps its own network (no way out) and asks Starboard to fetch an address with POST /api/v1/plugin/fetch. Starboard:

- takes only an https address on a listed site (port 443, no user name, no fragment); a site not on the list is refused;
- looks the name up itself and refuses the call unless every address it gets is a public internet address: never this
  computer, a home network address, a link-local address (cloud metadata) or anything reserved. It connects to the address
  it checked, so the answer cannot change between the check and the call (DNS rebinding);
- follows a redirect only to another listed site, at most 3 times, checking each the same way;
- sends only a few headers (Accept, Authorization, X-Api-Key) and asks for no compression;
- stops at a size limit (25 MB, or less if the plug-in asks) and a time limit (30 seconds, 120 at most);
- runs one fetch at a time for every plug-in together (a second one waits up to 10 seconds, then is told to try again), so
  a small server never has two downloads at once;
- keeps a short record for the person: when, which site, what it was for (the plug-in's own words), how big. Never the
  address's path or query, never a header, never what came back. People read it on the plug-in's page, "What it fetched".

Nothing runs while no plug-in asks: there is no thread, no timer and no open connection here. Starboard's own memory
grows by the size of one answer while it is held (up to 2 MB, or the file is written to the plug-in's folder instead).
"""
import base64
import http.client
import ipaddress
import json
import os
import re
import socket
import ssl
import threading
import time
import urllib.parse

HOST = re.compile(r"^(?=.{4,100}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24}$")
NOT_HOSTS = (".local", ".localhost", ".internal", ".lan", ".home", ".home.arpa", ".test", ".example", ".invalid", ".onion", ".corp", ".private")
MAX_HOSTS = 12
MAX_BYTES, DEFAULT_BYTES = 25 * 1024 * 1024, 25 * 1024 * 1024
INLINE_BYTES = 2 * 1024 * 1024  # an answer returned in the reply; more than this must be saved to a file
ERROR_BYTES = 64 * 1024  # the start of an error page, returned so the plug-in can say why
DEFAULT_SECONDS, MAX_SECONDS = 30, 120
MAX_REDIRECTS = 3
BUSY_WAIT = 10
PER_MINUTE = 60
KEEP = 200
FILE = "fetched.jsonl"
HEADERS = {"accept": "Accept", "authorization": "Authorization", "x-api-key": "X-Api-Key"}
SAVE_AS = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
WHAT = re.compile(r"[\x00-\x1f\x7f<>`]")

_one = threading.Semaphore(1)  # one fetch at a time, for every plug-in
_lock = threading.Lock()
_recent = {}  # plug-in id -> times of its fetches in the last minute


class Refused(ValueError):
    """The call is not allowed (a 400 with the reason in words)."""


class Failed(Exception):
    """The site did not answer as needed (a 502 with the reason in words)."""


def host_problem(host):
    """Why a name cannot be on a plug-in's fetch list, in words, or ''."""
    if not isinstance(host, str) or host != host.lower() or not HOST.match(host):
        return f"{host!r} is not a site name such as api.example.com (lower case, no address, no port, no *)"
    if any(host.endswith(s) for s in NOT_HOSTS):
        return f"{host} is a name for a computer at home, which a plug-in may not fetch from"
    return ""


def hosts_problems(hosts, name="fetch"):
    if not isinstance(hosts, list) or not 1 <= len(hosts) <= MAX_HOSTS or len(set(hosts)) != len(hosts):
        return [f"{name} must list one to {MAX_HOSTS} different site names, such as api.openverse.org"]
    return [host_problem(h) for h in hosts if host_problem(h)]


def public_address(ip):
    """True for an ordinary address on the internet. Not this computer, a home network, link-local (cloud metadata),
    multicast, shared (carrier) or reserved space, and an IPv4 address inside IPv6 is judged as IPv4."""
    try:
        a = ipaddress.ip_address(str(ip).split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(a, ipaddress.IPv6Address):
        if a.ipv4_mapped:
            a = a.ipv4_mapped
        elif a.sixtofour or a.teredo:
            return False
        elif a in ipaddress.ip_network("64:ff9b::/96"):  # NAT64 reaches IPv4 hosts: never a way round the check
            return False
    return bool(a.is_global) and not a.is_multicast


def resolve(host):
    """The addresses of a site name, only when every one is public. Refuses otherwise."""
    try:
        found = {i[4][0] for i in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    except OSError:
        raise Failed(f"Starboard could not find {host}. Check the connection of this computer") from None
    if not found:
        raise Failed(f"Starboard could not find {host}")
    bad = [a for a in found if not public_address(a)]
    if bad:
        raise Refused(f"{host} points to an address that is not on the internet, so Starboard did not call it")
    return sorted(found, key=lambda a: ":" in a)  # IPv4 first: the plain way round for most home connections


def parse(url, allowed):
    """(host, path_and_query) of an https address on an allowed site, or Refused."""
    if not isinstance(url, str) or len(url) > 2000 or re.search(r"[^\x21-\x7e]", url):
        raise Refused("url must be an address of up to 2000 plain characters")
    u = urllib.parse.urlsplit(url)
    if u.scheme != "https":
        raise Refused("Starboard fetches https addresses only")
    if u.username is not None or u.password is not None or u.fragment:
        raise Refused("The address may not have a user name, a password or a # part")
    try:
        port = u.port
    except ValueError:
        raise Refused("The address has a port that is not a number") from None
    if port not in (None, 443):
        raise Refused("Starboard fetches the usual https port only")
    host = (u.hostname or "").lower().rstrip(".")
    if host not in allowed:
        raise Refused(f"{host or 'That address'} is not on this plug-in's list of sites")
    path = u.path or "/"
    if "\\" in path or ".." in path.split("/"):
        raise Refused("The address has a path Starboard does not follow")
    return host, path + (f"?{u.query}" if u.query else "")


class _Pinned(http.client.HTTPSConnection):
    """An https connection to an address already checked, with the site's name for the certificate."""

    def __init__(self, host, ip, timeout, context):
        super().__init__(host, 443, timeout=timeout, context=context)
        self._ip = ip

    def connect(self):
        sock = socket.create_connection((self._ip, 443), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def _clean_headers(headers):
    out = {}
    if headers is None:
        return out
    if not isinstance(headers, dict) or len(headers) > 4:
        raise Refused("headers must be an object of up to 4 headers: Accept, Authorization or X-Api-Key")
    for k, v in headers.items():
        name = HEADERS.get(str(k).lower())
        if not name:
            raise Refused("Starboard sends only the headers Accept, Authorization and X-Api-Key")
        if not isinstance(v, str) or len(v) > 400 or re.search(r"[\x00-\x1f\x7f]", v):
            raise Refused(f"The {name} header must be one line of up to 400 characters")
        out[name] = v
    return out


def _get(host, path, ip, headers, timeout, context):
    conn = _Pinned(host, ip, timeout, context)
    try:
        conn.request("GET", path, headers={"User-Agent": "Starboard-plugin/1", "Accept-Encoding": "identity", **headers})
        return conn, conn.getresponse()
    except Exception:
        conn.close()
        raise


def clean_what(what):
    if what in (None, ""):
        return ""
    if not isinstance(what, str) or len(what) > 60 or WHAT.search(what):
        raise Refused("what must be a few plain words saying what it is for, up to 60 characters, such as Search for music")
    return what.strip()


def fetch(data_dir, plugin, hosts, body, context=None, now=None):
    """One fetch for a plug-in. `plugin` is {id, name}, `hosts` its manifest's list. Returns the answer as a dict, or raises
    Refused (the call is not allowed), Failed (the site did not answer) or api_v1.RateLimited."""
    from . import api_v1
    if not isinstance(body, dict):
        raise Refused("Send a JSON object with url")
    what = clean_what(body.get("what"))
    seconds = body.get("seconds", DEFAULT_SECONDS)
    limit = body.get("max_bytes", DEFAULT_BYTES)
    save_as = body.get("save_as")
    if isinstance(seconds, bool) or not isinstance(seconds, int) or not 1 <= seconds <= MAX_SECONDS:
        raise Refused(f"seconds must be a whole number from 1 to {MAX_SECONDS}")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_BYTES:
        raise Refused(f"max_bytes must be a whole number from 1 to {MAX_BYTES}")
    if save_as is not None and not (isinstance(save_as, str) and SAVE_AS.match(save_as)):
        raise Refused("save_as must be a file name of letters, numbers, dots, dashes and underscores, up to 81 characters")
    if save_as is None and limit > INLINE_BYTES:
        limit = INLINE_BYTES  # an answer without a file is returned in the reply, which is kept small
    headers = _clean_headers(body.get("headers"))
    try:
        host, path = parse(body.get("url"), hosts)
    except Refused as e:
        _record(data_dir, plugin["id"], _shown_host(body.get("url")), what, 0, "refused", now)
        raise e
    t = time.time() if now is None else now
    with _lock:
        mine = [x for x in _recent.get(plugin["id"], []) if t - x < 60]
        if len(mine) >= PER_MINUTE:
            raise api_v1.RateLimited(f"A plug-in may fetch up to {PER_MINUTE} times a minute", int(60 - (t - mine[0])) + 1)
        _recent[plugin["id"]] = mine + [t]
    if not _one.acquire(timeout=BUSY_WAIT):
        raise api_v1.RateLimited("Starboard is fetching for another plug-in. Try again in a few seconds", BUSY_WAIT)
    try:
        return _run(data_dir, plugin, hosts, host, path, headers, what, seconds, limit, save_as, context or ssl.create_default_context(), now)
    finally:
        _one.release()


def _shown_host(url):
    """The site part of an address Starboard refused a plug-in, cleaned for the record (never the path or a query)."""
    try:
        h = (urllib.parse.urlsplit(url).hostname or "").lower()
    except (ValueError, AttributeError):
        h = ""
    return re.sub(r"[^a-z0-9.-]", "", h)[:100] or "(not an address)"


def _run(data_dir, plugin, hosts, host, path, headers, what, seconds, limit, save_as, context, now):
    deadline = time.monotonic() + seconds
    redirects = 0
    status, ctype, size, data, saved = 0, "", 0, b"", None
    try:
        while True:
            ips = resolve(host)
            left = deadline - time.monotonic()
            if left <= 0:
                raise Failed(f"{host} took longer than {seconds} seconds")
            try:
                conn, resp = _get(host, path, ips[0], headers, max(1, left), context)
            except (OSError, ssl.SSLError, http.client.HTTPException) as e:
                raise Failed(f"Starboard could not get an answer from {host} ({type(e).__name__})") from None
            try:
                status = resp.status
                if status in (301, 302, 303, 307, 308):
                    where = resp.getheader("Location") or ""
                    redirects += 1
                    if redirects > MAX_REDIRECTS:
                        raise Failed(f"{host} sent Starboard round in a circle")
                    try:
                        nhost, npath = parse(urllib.parse.urljoin(f"https://{host}{path}", where), hosts)
                    except Refused:
                        raise Refused(f"{host} tried to send Starboard to another site, which is not on this plug-in's list") from None
                    if nhost != host:
                        headers = {k: v for k, v in headers.items() if k.lower() == "accept"}  # a key never follows to another site
                    host, path = nhost, npath
                    continue
                ctype = (resp.getheader("Content-Type") or "").split(";")[0].strip().lower()[:100]
                ok = 200 <= status < 300
                cap = limit if ok else ERROR_BYTES
                declared = resp.getheader("Content-Length")
                if ok and declared and declared.isdigit() and int(declared) > limit:
                    raise Failed(f"{host} has a file of {int(declared) // 1024} KB, more than the {limit // 1024} KB this call may fetch")
                chunks, size = [], 0
                tmp = None
                if ok and save_as:
                    tmp = _open_save(data_dir, plugin["id"], save_as)
                try:
                    while True:
                        if time.monotonic() > deadline:
                            raise Failed(f"{host} took longer than {seconds} seconds")
                        block = resp.read(65536)
                        if not block:
                            break
                        size += len(block)
                        if size > cap:
                            if not ok:
                                chunks.append(block[:max(0, cap - (size - len(block)))])
                                size = cap
                                break
                            raise Failed(f"{host} sent more than the {limit // 1024} KB this call may fetch")
                        if tmp:
                            tmp[0].write(block)
                        else:
                            chunks.append(block)
                    if tmp:
                        tmp[0].close()
                        os.replace(tmp[1], tmp[2])
                        saved = save_as
                        tmp = None
                finally:
                    if tmp:
                        tmp[0].close()
                        try:
                            os.unlink(tmp[1])
                        except OSError:
                            pass
                data = b"".join(chunks)
                break
            except (OSError, ssl.SSLError, http.client.HTTPException) as e:
                raise Failed(f"The answer from {host} stopped part way ({type(e).__name__})") from None
            finally:
                conn.close()
    except Refused as e:
        _record(data_dir, plugin["id"], host, what, 0, "refused", now)
        raise e
    except Failed as e:
        _record(data_dir, plugin["id"], host, what, size, "failed", now)
        raise e
    _record(data_dir, plugin["id"], host, what, size, "ok" if 200 <= status < 300 else f"answered {status}", now)
    out = {"ok": True, "status": status, "host": host, "content_type": ctype, "size": size}
    if saved:
        out["saved"] = saved
    else:
        out["body_base64"] = base64.b64encode(data).decode()
    return out


def _save_dir(data_dir, pid):
    from . import plugins_admin
    where = plugins_admin.folder(data_dir, pid)
    m = plugins_admin._read_kept(os.path.join(where, "manifest.json"), {}) or {}
    names = [c.get("name") for c in m.get("containers") or [] if isinstance(c, dict) and "data" in (c.get("volumes") or [])]
    if not names:
        raise Refused("save_as needs a container with the volume data, to keep the file in")
    return os.path.join(where, "data", names[0], "fetched")


def _open_save(data_dir, pid, name):
    d = _save_dir(data_dir, pid)
    os.makedirs(d, exist_ok=True)
    os.chmod(d, 0o777)  # nosec B103: the plug-in's own container may run as any user; the folder is inside its own 0700 folder
    tmp = os.path.join(d, f".{name}.part")
    f = open(tmp, "wb")  # noqa: SIM115
    try:
        os.chmod(tmp, 0o666)  # nosec B103: the plug-in's container must be able to read and delete it
    except OSError:
        pass
    return f, tmp, os.path.join(d, name)


def _record(data_dir, pid, host, what, size, result, now=None):
    from . import plugins_admin
    path = os.path.join(plugins_admin.folder(data_dir, pid), FILE)
    line = json.dumps({"at": int(time.time() if now is None else now), "host": host, "what": what, "size": int(size), "result": result},
                      separators=(",", ":"))
    try:
        with _lock:
            lines = []
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    lines = f.read().splitlines()
            lines.append(line)
            if len(lines) > KEEP * 2:
                lines = lines[-KEEP:]
            tmp = path + ".part"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            os.chmod(tmp, 0o600)
            os.replace(tmp, path)
    except OSError:
        pass  # a record that cannot be kept never stops the fetch


def record_of(data_dir, pid):
    """What a plug-in fetched, newest first, up to 200: [{at, host, what, size, result}]. Starboard reads it only when the page opens."""
    from . import plugins_admin
    path = os.path.join(plugins_admin.folder(data_dir, pid), FILE)
    out = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f.read().splitlines()[-KEEP:]:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and isinstance(r.get("at"), int):
                    out.append({"at": r["at"], "host": str(r.get("host", ""))[:100], "what": str(r.get("what", ""))[:60],
                                "size": int(r.get("size") or 0), "result": str(r.get("result", ""))[:30]})
    except OSError:
        return []
    return out[::-1]


def hosts_of(manifest):
    return [h for h in (manifest or {}).get("fetch") or [] if isinstance(h, str)]


def reset():
    """For tests."""
    with _lock:
        _recent.clear()
