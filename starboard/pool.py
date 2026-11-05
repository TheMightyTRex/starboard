"""System, Storage, Pool (DASH-87): Starboard's side of the drive pool.

Starboard never runs as root and never touches a drive itself. The pool helper (deploy/install-pool.sh installs
starboard/pool_helper.py as /usr/local/bin/starboard-pool) does the work as root. Starboard drops a small JSON
request in STARBOARD_POOL_DIR/requests, the one place it may write, and reads the helper's answers, plans,
progress and the pool's state from STARBOARD_POOL_DIR/status, read only. Nothing is shown when it is not set.
"""
import json
import os
import re
import secrets

KINDS = {"add", "remove", "balance"}


def folder():
    return os.environ.get("STARBOARD_POOL_DIR", "")


def _read(*parts):
    try:
        with open(os.path.join(folder(), "status", *parts), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def status():
    if not folder():
        return {"set_up": False, "why": "not set up"}
    found = _read("status.json")
    if not found:
        return {"set_up": False, "why": "no answer", "folder": folder()}
    found["set_up"] = True
    found["job"] = _read("job.json") or found.get("job")
    found["nightly"] = _read("nightly.json") or found.get("nightly")
    return found


def ask(action, **fields):
    """Write one request for the helper; returns its ID, to read the answer with answer(). The file is written under
    a name the helper skips, then renamed, so the helper never reads half a request."""
    if not folder():
        raise ValueError("The pool helper is not set up. Run ./install.sh again and say yes to Drive pools")
    rid = secrets.token_hex(8)
    req = dict(fields, action=action, id=rid)
    base = os.path.join(folder(), "requests")
    tmp = os.path.join(base, f".{rid}.part")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(req, f)
        os.replace(tmp, os.path.join(base, f"{rid}.json"))
    except OSError:
        raise ValueError("Starboard cannot ask the pool helper: its requests folder is not writable") from None
    return rid


def answer(rid):
    if not re.fullmatch(r"[0-9a-f]{16}", rid or ""):
        raise ValueError("That is not a request")
    return _read("answers", f"{rid}.json")


def plan_request(data, download_hours=None):
    """The fields of a plan request, checked: only what the helper understands goes through."""
    kind = data.get("kind")
    if kind not in KINDS:
        raise ValueError("Choose add, remove or balance")
    out = {"kind": kind}
    if kind in ("add", "remove"):
        drive = str(data.get("drive", ""))
        if not re.fullmatch(r"[A-Za-z0-9/._:-]{1,200}", drive):
            raise ValueError("Choose a drive")
        out["drive"] = drive
    if kind == "add":
        role = data.get("as")
        if role not in ("pool", "parity", "copy"):
            raise ValueError("Choose the pool, a parity drive or a copy drive")
        out.update({"as": role, "erase": bool(data.get("erase"))})
        folders = [str(x).strip("/") for x in data.get("folders") or [] if str(x).strip("/")]
        if any(not re.fullmatch(r"[\w .()'-]+(/[\w .()'-]+)*", f) or ".." in f.split("/") for f in folders):
            raise ValueError("Folders are names inside the pool, such as media or media/photos")
        out["folders"] = folders[:20]
    if kind == "balance":
        out["engine"] = "mergerfs.balance" if data.get("engine") == "mergerfs.balance" else "starboard"
        hours = download_hours or {}
        if data.get("pause", True) and hours.get("enabled"):
            out["pause"] = [[f"{int(hours['start']):02d}:00", f"{int(hours['end']):02d}:00"]]
    return out


def apply_request(data):
    plan = str(data.get("plan", ""))
    if not re.fullmatch(r"[0-9a-f]{12}", plan):
        raise ValueError("That is not a plan")
    confirm = {str(k)[:200]: re.sub(r"[^A-Za-z0-9]", "", str(v))[:8] for k, v in (data.get("confirm") or {}).items()}
    return {"plan": plan, "confirm": confirm}
