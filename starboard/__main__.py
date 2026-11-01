"""Run with: python -m starboard  (settings: STARBOARD_HOST, STARBOARD_PORT, STARBOARD_DATA)."""

import os

from .server import make_server


def main():
    host = os.environ.get("STARBOARD_HOST", "127.0.0.1")
    port = int(os.environ.get("STARBOARD_PORT", "8095"))
    data_dir = os.environ.get("STARBOARD_DATA", os.path.join(os.path.expanduser("~"), ".local", "share", "starboard"))
    server, app = make_server(host, port, data_dir)
    print(f"[starboard] {app.version} listening on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
