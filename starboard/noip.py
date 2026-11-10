"""The No-IP updater (DASH-170): noip-duc keeps a No-IP address pointing at this server. Starboard shows whether it
runs, when it last updated the address and which addresses it keeps up to date, and says plainly when No-IP refuses
the sign-in, with a form for a new DDNS key or password. The sign-in lives in data/stack/noip.env next to the
Compose file, never in Starboard's settings; the updater reads it when it starts.

What it last did comes from its own log (noip-duc 3.3 writes "update successful; current=..." and "Incorrect
credentials"), read through Docker's API, a few hundred lines at most.
"""
import os
import re
import threading
import time

from . import stack

FILE = "noip.env"
SERVICE = "noip-duc"
KEEP = 60
_cache = {}
_lock = threading.Lock()
_STAMP = re.compile(r"^\[(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)\s+(\w+)\s+[^\]]*\]\s*(.*)$")


def path(data_dir):
    return os.path.join(stack.folder(data_dir), FILE)


def read(data_dir):
    """{username, hostnames, password_set}; the password itself is never sent to a page."""
    values = {}
    try:
        with open(path(data_dir), encoding="utf-8") as f:
            for line in f.read().splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    k, v = line.split("=", 1)
                    values[k.strip()] = v.strip().strip("'\"")
    except OSError:
        pass
    return {"username": values.get("NOIP_USERNAME", ""), "hostnames": values.get("NOIP_HOSTNAMES", ""),
            "password_set": bool(values.get("NOIP_PASSWORD"))}


def _clean(value, what, pattern, limit=200):
    value = str(value or "").strip()
    if len(value) > limit or not re.match(pattern, value):
        raise ValueError(f"Check the {what}: it has a character No-IP does not use")
    return value


def save(data_dir, username, password, hostnames):
    """Writes noip.env (owner only). A password left empty keeps the one there is."""
    username = _clean(username, "DDNS key's user name", r"^[A-Za-z0-9@._+-]{1,200}$")
    hostnames = _clean(hostnames, "addresses", r"^[A-Za-z0-9.-]+(,[A-Za-z0-9.-]+)*$", 1000)
    password = str(password or "")
    if any(c in password for c in "\r\n'\"") or len(password) > 200:
        raise ValueError("Check the password: it cannot have quotes or line breaks")
    if not password:
        try:
            with open(path(data_dir), encoding="utf-8") as f:
                password = next((line.split("=", 1)[1].strip().strip("'\"") for line in f.read().splitlines()
                                 if line.startswith("NOIP_PASSWORD=")), "")
        except OSError:
            password = ""
    if not password:
        raise ValueError("Type the DDNS key's password")
    os.makedirs(stack.folder(data_dir), mode=0o700, exist_ok=True)
    tmp = path(data_dir) + ".new"
    with os.fdopen(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
        f.write(f"NOIP_USERNAME={username}\nNOIP_PASSWORD={password}\nNOIP_HOSTNAMES={hostnames}\n")
    os.replace(tmp, path(data_dir))
    forget()
    return read(data_dir)


def ensure_file(data_dir):
    """An empty noip.env for a new install, so Compose can start the updater; it waits for a DDNS key."""
    if not os.path.exists(path(data_dir)):
        os.makedirs(stack.folder(data_dir), mode=0o700, exist_ok=True)
        with os.fdopen(os.open(path(data_dir), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8") as f:
            f.write("NOIP_USERNAME=\nNOIP_PASSWORD=\nNOIP_HOSTNAMES=\n")


def parse(log_text):
    """What the log says: {state, last_update, address, said}. state: "ok", "refused", "waiting" or "unknown"."""
    out = {"state": "unknown", "last_update": None, "address": None, "said": ""}
    for line in log_text.splitlines():
        m = _STAMP.match(line.strip())
        when, level, text = (m.group(1), m.group(2), m.group(3)) if m else (None, "", line.strip())
        low = text.lower()
        if "update successful" in low or "nochg" in low or "good " in low:
            out.update(state="ok", last_update=when or out["last_update"], said="")
            found = re.search(r"current=([0-9a-fA-F.:]+)", text)
            if found:
                out["address"] = found.group(1)
        elif "incorrect credentials" in low or "badauth" in low or "unauthorized" in low:
            out.update(state="refused", said="Type a new DDNS key or password below, then save. The updater starts again with it.")
        elif ("checking ip again" in low or "attempting to get ip" in low) and out["state"] == "unknown":
            out["state"] = "waiting"
        elif level in ("ERROR", "WARN") and text:
            out["said"] = text[:200]
    return out


def status(data_dir, docker=None, logs=None):
    """{installed, running, state, last_update, address, said, username, hostnames, password_set}, kept a minute."""
    with _lock:
        hit = _cache.get("status")
        if hit and time.time() - hit[0] < KEEP:
            return hit[1]
    from . import containers
    out = {"installed": False, "running": False, **read(data_dir), **parse("")}
    try:
        info = (docker or containers.docker)("GET", f"/containers/{SERVICE}/json")
        out["installed"] = True
        out["running"] = bool((info.get("State") or {}).get("Running"))
        text = (logs or _logs)(docker)
        out.update(parse(text))
    except containers.DockerError:
        pass
    with _lock:
        _cache["status"] = (time.time(), out)
    return out


def _logs(docker=None):
    from . import reelix_setup
    return reelix_setup._log_text(SERVICE, docker)


def forget():
    with _lock:
        _cache.clear()
