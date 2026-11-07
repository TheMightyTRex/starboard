"""Checks data/stack/compose.yaml before the Run first window or ./install.sh --start-apps starts it (7 November 2026).

The Starboard container can write data/stack, and the window on the computer runs `docker compose up` on what is
there, with the docker group. So the window checks the file first, with Starboard's own rules, instead of trusting it:

- every service's image is one Starboard's catalogue offers (Install apps' apps, their databases, Reelix's images);
- no privileged containers, host network, host processes or extra capabilities, apart from Gluetun's NET_ADMIN and
  /dev/net/tun, which a VPN needs;
- every folder a service mounts is inside the settings folder or the media folder from .env, and those two pass the
  same rules as Install apps (no system folders, no top folders, no home folder itself).

Usage: docker compose ... config --format json | python3 -m starboard.compose_check data/stack/.env
Prints one problem a line; exits 1 when there are any.
"""
import json
import os
import re
import sys

from . import stack

ALLOWED_DEVICES = {"gluetun": {"/dev/net/tun"}}
ALLOWED_CAPS = {"gluetun": {"NET_ADMIN"}}


def allowed_images():
    images = {a["image"] for a in stack.APPS.values() if a.get("image") and a["image"] != "none"}
    images |= {a["db"]["image"] for a in stack.APPS.values() if a.get("db")}
    images |= {stack.REELIX_IMAGE, *stack.REELIX_FULL_IMAGES}
    for name in ("STARBOARD_REELIX_IMAGE", "STARBOARD_REELIX_FULL_IMAGE"):
        if os.environ.get(name):
            images.add(os.environ[name])
    return images


def problems(config, env):
    """What is wrong with a `docker compose config --format json` document, given .env's values."""
    out = []
    dirs = []
    for key, what in (("CONFIG_DIR", "settings folder"), ("DATA_DIR", "media folder")):
        try:
            dirs.append(stack.clean_folder(env.get(key, ""), what))
        except ValueError as e:
            out.append(f"{key}: {e}")
    images = allowed_images()

    def inside(path):
        p = os.path.normpath(path)
        return any(p == d or p.startswith(d + "/") for d in dirs)

    for name, svc in sorted((config.get("services") or {}).items()):
        image = str(svc.get("image", ""))
        if image not in images:
            out.append(f"{name}: the image {image or '(none)'} is not one Starboard installs")
        if svc.get("privileged"):
            out.append(f"{name}: runs privileged, with full control of this computer")
        for field in ("network_mode", "pid", "ipc", "userns_mode"):
            v = str(svc.get(field, ""))
            if v == "host":
                out.append(f"{name}: {field} is host")
        caps = set(svc.get("cap_add") or [])
        extra = caps - ALLOWED_CAPS.get(name, set())
        if extra:
            out.append(f"{name}: asks for {', '.join(sorted(extra))}")
        for dev in svc.get("devices") or []:
            source = dev.get("source") if isinstance(dev, dict) else str(dev).split(":", 1)[0]
            if source not in ALLOWED_DEVICES.get(name, set()):
                out.append(f"{name}: uses the device {source}")
        if svc.get("security_opt") or svc.get("volumes_from"):
            out.append(f"{name}: has security or shared-volume settings Starboard does not write")
        for vol in svc.get("volumes") or []:
            if isinstance(vol, dict):
                kind, source = vol.get("type", "bind"), str(vol.get("source", ""))
            else:
                kind, source = "bind", str(vol).split(":", 1)[0]
            if kind == "bind" and not inside(source):
                out.append(f"{name}: mounts {source}, outside the settings and media folders")
    return out


def read_env(path):
    try:
        with open(path, encoding="utf-8") as f:
            return {k: v.strip().strip("'\"") for k, v in (l.split("=", 1) for l in f.read().splitlines()
                                                         if "=" in l and not l.startswith("#"))}
    except OSError:
        return {}


def main():
    env = read_env(sys.argv[1] if len(sys.argv) > 1 else "data/stack/.env")
    try:
        config = json.load(sys.stdin)
    except ValueError:
        print("The set-up file could not be read")
        return 1
    found = problems(config, env)
    for p in found:
        print(p)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
