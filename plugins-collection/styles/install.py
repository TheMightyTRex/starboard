#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The Styles plug-in's installer: opens your Starboard's Settings, Plug-ins with this plug-in ready to add.

    python3 install.py                      asks for your Starboard's address
    python3 install.py http://192.0.2.10:8095
    python3 install.py --print http://...   prints the link instead of opening it

Nothing is sent anywhere but your own Starboard, and nothing is added until you read what it may do and type
your Starboard password there. Needs only Python 3.8 or later.
"""
import base64
import json
import os
import re
import sys
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))


def main(argv):
    only_print = "--print" in argv
    args = [a for a in argv if a != "--print"]
    with open(os.path.join(HERE, "starboard-plugin.json"), encoding="utf-8") as f:
        raw = f.read()
    manifest = json.loads(raw)  # a broken file stops here, before anything opens
    address = args[0] if args else input("Your Starboard's address, such as http://192.0.2.10:8095: ").strip()
    address = address.rstrip("/")
    if not re.match(r"^https?://[^\s/]+$", address):
        print("Give the address you open Starboard at, such as http://192.0.2.10:8095, with nothing after the port.")
        return 2
    packed = base64.urlsafe_b64encode(json.dumps(manifest, separators=(",", ":")).encode()).decode().rstrip("=")
    link = f"{address}/settings-plugins.html#manifest={packed}"  # after #, so the browser keeps it to itself
    print(f"{manifest['name']} {manifest['version']}: {len(manifest.get('styles', []))} styles.")
    if only_print or not webbrowser.open(link):
        print("Open this link in the browser you use for Starboard:\n" + link)
    else:
        print("Starboard is opening. Sign in if asked, check what the plug-in may do, and select Add.")
    print("Then activate it in Settings, Plug-ins, and pick a style in Display.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
