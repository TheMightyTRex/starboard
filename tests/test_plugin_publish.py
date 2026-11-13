"""A plug-in container on the VPN may publish its port on Gluetun for the home network (plug-in API 1.9,
13 November 2026: a Roku could not reach On demand's streams at gluetun:7790)."""

import json
import os
import tempfile
import unittest

from starboard import plugins, stack

COMPOSE = """services:
  gluetun:
    image: qmcgaw/gluetun
    ports:  # apps that go through the VPN are reached on Gluetun's ports
      - "8080:8080"
      - "6789:6789"
    environment:
      TZ: Europe/London
  qbittorrent:
    image: lscr.io/linuxserver/qbittorrent
    network_mode: "service:gluetun"
"""


def manifest(**c):
    return {"manifest_version": 1, "id": "on-demand", "name": "On demand", "version": "1.0.0", "description": "x",
            "author": "x", "licence": "MIT", "starboard_api": "1.9", "permissions": ["network:vpn"],
            "containers": [{"name": "on-demand", "image": "local/x:1", "network": "vpn", "port": 7790, **c}]}


class Publish(unittest.TestCase):
    def test_check(self):
        self.assertFalse([p for p in plugins.check(manifest(publish=True), dev=True) if "publish" in p])
        bad = manifest(publish=True)
        bad["containers"][0]["network"] = "default"
        self.assertTrue([p for p in plugins.check(bad, dev=True) if "publish" in p])
        self.assertTrue([p for p in plugins.check(manifest(publish="yes"), dev=True) if "publish" in p])

    def test_ports_of_active_plug_ins_only(self):
        d = tempfile.mkdtemp()
        for pid, state, pub in (("on-demand", "enabled", True), ("other", "disabled", True), ("quiet", "enabled", False)):
            os.makedirs(os.path.join(d, "plugins", pid))
            m = manifest(publish=pub)
            m["containers"][0]["port"] = {"on-demand": 7790, "other": 7791, "quiet": 7792}[pid]
            json.dump(m, open(os.path.join(d, "plugins", pid, "manifest.json"), "w"))
            json.dump({"state": state}, open(os.path.join(d, "plugins", pid, "state.json"), "w"))
        self.assertEqual(stack.plugin_vpn_ports(d), ["7790:7790"])

    def test_added_once_to_gluetun_only(self):
        text, changed = stack.with_plugin_ports(COMPOSE, ["7790:7790"])
        self.assertTrue(changed)
        g = text.split("  qbittorrent:")[0]
        self.assertIn('- "7790:7790"', g)
        self.assertEqual(text.split("  qbittorrent:")[1], COMPOSE.split("  qbittorrent:")[1])
        again, changed = stack.with_plugin_ports(text, ["7790:7790"])
        self.assertFalse(changed)
        self.assertEqual(again, text)

    def test_no_gluetun_no_change(self):
        self.assertEqual(stack.with_plugin_ports("services:\n  jellyfin:\n    image: x\n", ["7790:7790"]), ("services:\n  jellyfin:\n    image: x\n", False))


if __name__ == "__main__":
    unittest.main()
