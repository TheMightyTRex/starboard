"""The Live TV plug-in's own program (DASH-285): run by Starboard's own image in the plug-in's container,
`python -m starboard.livetv_plugin`. It does what Starboard's Live TV job did: once an hour it refreshes the guides
that are due, rebuilds a channel list when its source changed (or weekly), whitens logos, and adds the lists and
guides to Jellyfin (livetv.py, livetv_jellyfin.py, unchanged). Starboard itself still serves the logos and the Pluto
TV links to Jellyfin at the same addresses as before, from the same Live TV folder, so Jellyfin sees no change.

Its settings come from /run/starboard/settings.json (Settings, Plug-ins, Live TV), Jellyfin's address and key from
/run/starboard/jellyfin.json. It answers on port 8080:
  GET  /health   200 while it runs
  GET  /card     the dashboard card: {"state": "ok" | "warning" | "problem", "text": ...}
  POST /run      run now, every list rebuilt (Run Live TV now)
"""
import http.server
import json
import os
import threading
import time

SETTINGS = os.environ.get("STARBOARD_PLUGIN_SETTINGS", "/run/starboard/settings.json")
JELLYFIN = os.environ.get("STARBOARD_PLUGIN_JELLYFIN", "/run/starboard/jellyfin.json")
STATUS = os.environ.get("STARBOARD_PLUGIN_STATUS", "/data/status.json")
EVERY = 3600
_wake = threading.Event()
_force = {"now": False}
_lock = threading.Lock()


def _read(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def status():
    return _read(STATUS, {})


def _save_status(**values):
    current = {**status(), **values}
    tmp = STATUS + ".new"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(current, f)
    os.replace(tmp, STATUS)


def run_once(force=False, build=None, connect=None, refresh=None):
    """One run: the files, then Jellyfin. Returns the sentence the card shows."""
    from . import livetv, livetv_jellyfin
    s = _read(SETTINGS, {})
    address = str(s.get("address") or "").rstrip("/")
    if not address:
        raise ValueError("Set the address Jellyfin uses to reach Starboard in Settings, Plug-ins, Live TV")
    guides = [os.path.join(livetv.folder() or "", g) for g in livetv_jellyfin.GUIDES]
    before = [_mtime(g) for g in guides]
    summary = (build or livetv.run)(address, bool(s.get("white_logos", True)), force=force)
    jf = _read(JELLYFIN, {})
    services = [{"type": "jellyfin", "url": jf["url"], "api_key": jf["api_key"]}] if jf.get("url") and jf.get("api_key") else []
    added = (connect or livetv_jellyfin.connect)(services, {"livetv_jellyfin_folder": s.get("jellyfin_folder") or ""}, "",
                                                 local_folder=livetv.folder(), host_path="", env={})
    if not added and [_mtime(g) for g in guides] != before:  # new guides: Jellyfin reads them now, not tomorrow
        added = (refresh or livetv_jellyfin.refresh_guide)(services)
    return f"{summary} · {added}" if added else summary


def _mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def card():
    st = status()
    if not st:
        return {"state": "warning", "text": "Not run yet. It runs within the hour, or select Run Live TV now."}
    when = time.strftime("%H:%M on %d %b", time.localtime(st.get("finished") or st.get("started") or 0))
    if st.get("state") == "running":
        return {"state": "ok", "text": "Running now: refreshing guides and testing channels."}
    if st.get("state") == "failed":
        return {"state": "problem", "text": f"Last run failed at {when}: {st.get('summary', '')}"[:160]}
    return {"state": "ok", "text": f"Last run at {when}: {st.get('summary', '')}"[:160]}


def loop(stop=None):
    while not (stop and stop.is_set()):
        with _lock:
            force, _force["now"] = _force["now"], False
        try:
            _save_status(state="running", started=time.time())
            said = run_once(force=force)  # first: the finish time is taken after the run
            _save_status(state="done", finished=time.time(), summary=said)
        except Exception as e:  # recorded for the card and the plug-in's section; the next run tries again
            try:
                _save_status(state="failed", finished=time.time(), summary=str(e)[:300])
            except OSError as again:  # its folder cannot be written: said in its log, and it keeps running
                print(f"Live TV could not save its status: {again}; the run said: {e}", flush=True)
        _wake.wait(EVERY)
        _wake.clear()


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def answer(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/health":
            return self.answer(200, {"ok": True})
        if self.path == "/card":
            return self.answer(200, card())
        return self.answer(404, {"error": "Not found"})

    def do_POST(self):
        if self.path == "/run":
            with _lock:
                _force["now"] = True
            _wake.set()
            return self.answer(202, {"said": "Live TV is running now. Testing every channel takes a few minutes."})
        return self.answer(404, {"error": "Not found"})


def main():
    threading.Thread(target=loop, name="livetv", daemon=True).start()
    http.server.ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()  # inside its own container  # nosec B104


if __name__ == "__main__":
    main()
