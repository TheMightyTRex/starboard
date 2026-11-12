"""Run with: python -m starboard  (settings: STARBOARD_PORT, STARBOARD_DATA; STARBOARD_HOST fixes the address)."""

import os
import signal
import threading

from . import logs, recovery
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
        thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 5}, daemon=True)  # wakes every 5 s, not twice a second, only to check for shutdown
        thread.start()
        where = "this computer only" if host.startswith("127.") else "your network"
        logs.event("info", "start", f"Starboard {self.app.version} listening on port {self.app.port} ({where})")
        return thread

    def rebind(self):
        with self.lock:
            old_host = self.host
            self.server.shutdown()
            self.server.server_close()
            try:
                self.start()
            except OSError as e:
                logs.event("error", "start", f"Could not move the listener ({e}); going back to the previous address")
                self.start(old_host)


def main():
    data_dir = os.environ.get("STARBOARD_DATA", os.path.join(os.path.expanduser("~"), ".local", "share", "starboard"))
    runner = Runner(App(data_dir))
    runner.start()
    stop = threading.Event()

    def stop_cleanly(_signum, _frame):
        # Docker, systemd and Ctrl+C stop Starboard this way: noted, so the next start knows the stop was clean
        # (DASH-88). Without the handler, Python as the container's first process would ignore SIGTERM until killed.
        recovery.mark_clean(data_dir)
        stop.set()
    signal.signal(signal.SIGTERM, stop_cleanly)
    signal.signal(signal.SIGINT, stop_cleanly)
    stop.wait()
    logs.event("info", "start", "Starboard stopped")


if __name__ == "__main__":
    main()
