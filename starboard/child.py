"""Heavy jobs in a short-lived process (DASH-79), so the long-running server's memory stays low.

The watch history import, listening progress, the Live TV job (built in, or in the Live TV plug-in's container) and
building a Library index read whole lists from the apps or the guide sites. Run inside the server, the memory they used stayed with it afterwards (on the owner's server
the hourly import took Starboard from 18 MB to 164 MB at its peak, and it was still at 61 MB eight minutes later).
Each now runs in its own Python process, started for the job and gone when it ends, so everything it used is given
back to the system. Starting one costs about 0.2 seconds and 15 MB while it runs.

Only the real server (python -m starboard) and the Live TV plug-in do this; tests and tools run the same work in
their own process. STARBOARD_CHILD_JOBS=0 runs it in the server instead.
The child gets its work on standard input and answers with one JSON line; what it logs goes back to the server's
log, so System, Logs reads as before.
"""

import json
import os
import subprocess
import sys

ENABLED = False  # set by __main__ for the running server
MARK = "\x1estarboard-child "


def _work(kind, args):
    if kind == "import":
        from . import migrate
        return migrate.apply(args["data_dir"], args["services"])
    if kind == "listening":
        from . import listening
        return listening.apply(args["data_dir"], args["services"])
    if kind == "livetv":
        from . import livetv, livetv_jellyfin
        summary = livetv.run(args["self_url"], args["white_logos"], force=args["force"])
        added = livetv_jellyfin.connect(args["services"], args["settings"], args["data_dir"])
        return f"{summary} · {added}" if added else summary
    if kind == "livetv-plugin":
        from . import livetv_plugin
        return livetv_plugin.run_once(force=args["force"])
    if kind == "library":
        from . import library
        return library.build_and_write(args["data_dir"], args["reelix"], args["tab"])
    raise ValueError(f"No such job: {kind}")


def run(kind, args, timeout=3600):
    """The job's result, worked out in a child process when ENABLED, else here. Errors come back as the same kind:
    ServiceError (with its status), ValueError, or RuntimeError for anything else."""
    if not ENABLED:
        return _work(kind, args)
    from . import logs, services
    detailed = bool(logs._current and logs._current.detailed())
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = {**os.environ, "PYTHONPATH": here + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else "")}
    try:
        done = subprocess.run([sys.executable, "-m", "starboard.child", kind], input=json.dumps({"args": args, "detail": detailed}).encode(),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, env=env, cwd=here, check=False)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"The {kind} job took longer than {timeout // 60} minutes and was stopped") from None
    out = None
    for line in done.stdout.decode("utf-8", "replace").split("\n"):  # not splitlines(): it splits at MARK too
        if line.startswith(MARK):
            try:
                out = json.loads(line[len(MARK):])
            except ValueError:
                out = None
        elif line.strip():
            logs.event("info", kind, line.strip()[:500])
    if out is None:
        said = done.stderr.decode("utf-8", "replace").strip().splitlines()[-1:] or [f"exit code {done.returncode}"]
        raise RuntimeError(f"The {kind} job stopped: {said[0][:300]}")
    for how, level, area, message, extra in out.get("logs") or []:
        if how == "detail":
            logs.detail(area, message, **extra)
        else:
            logs.event(level, area, message, **extra)
    if out.get("ok"):
        return out.get("result")
    if out.get("type") == "ServiceError":
        e = services.ServiceError(out.get("error", ""))
        e.status = out.get("status")
        raise e
    if out.get("type") == "ValueError":
        raise ValueError(out.get("error", ""))
    raise RuntimeError(out.get("error", ""))


def main():
    from . import logs, services
    kind = sys.argv[1]
    given = json.load(sys.stdin)
    said = []
    logs.event = lambda level, area, message, **extra: said.append(["event", level, area, str(message), extra])
    if given.get("detail"):
        logs.detail = lambda area, message, **extra: said.append(["detail", "detail", area, str(message), extra])
    else:
        logs.detail = lambda area, message, **extra: None
    try:
        out = {"ok": True, "result": _work(kind, given["args"])}
    except services.ServiceError as e:
        out = {"ok": False, "type": "ServiceError", "error": str(e), "status": getattr(e, "status", None)}
    except ValueError as e:
        out = {"ok": False, "type": "ValueError", "error": str(e)}
    except Exception as e:  # noqa: BLE001 - every other failure goes back to the server as words
        out = {"ok": False, "type": type(e).__name__, "error": str(e)}
    out["logs"] = said
    sys.stdout.write("\n" + MARK + json.dumps(out, default=str) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
