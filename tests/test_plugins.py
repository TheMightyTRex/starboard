"""Plug-ins, first part (DASH-149, DASH-272): the manifest check, permissions and the hardened Compose file."""
import json
import os
import unittest

from starboard import plugins

DIGEST = "sha256:" + "a" * 64
ON_DEMAND = {  # On demand's manifest as it becomes (design, section 11)
    "manifest_version": 1, "id": "on-demand", "name": "On demand", "version": "0.2.0",
    "description": "Films and series from your Stremio add-ons, in two Jellyfin libraries, played by torrent through your VPN.",
    "author": "TheMightyTRexUK", "licence": "MIT", "homepage": "https://example.invalid/on-demand",
    "support_url": "https://example.invalid/on-demand/issues", "starboard_api": ">=1.0 <2.0",
    "permissions": ["media:read", "network:vpn", "jellyfin:key"], "needs": ["jellyfin", "gluetun"],
    "containers": [
        {"name": "main", "image": f"ghcr.io/example/on-demand@{DIGEST}", "port": 7790, "network": "vpn",
         "volumes": ["data", "media/on-demand"], "user": "1000:1000"},
        {"name": "engine", "image": f"docker.io/stremio/server@{DIGEST}", "network": "vpn", "volumes": ["data"],
         "start": "when_needed", "idle_stop_minutes": 15, "user": "1000:1000", "env": {"APP_PATH": "/data"}}],
    "resources": {"main": {"memory": 40}, "engine": {"memory": 250}},
    "settings": [{"key": "quality", "label": "Picture quality", "type": "choice", "choices": ["4K", "1080p", "720p"], "default": "1080p"},
                 {"key": "catalogues", "label": "What it shows", "type": "custom", "choices": "/api/choices"},
                 {"key": "min_seeders", "label": "Minimum seeders", "type": "number", "min": 1, "max": 100, "default": 5}],
    "cards": [{"id": "titles", "title": "On demand", "type": "stat", "path": "/api/card", "format": "number", "label": "titles"}],
    "actions": [{"id": "sync", "label": "Update now", "path": "/api/sync"}],
    "health": "/api/health",
}


class PluginsTest(unittest.TestCase):
    def test_on_demand_as_it_becomes_is_valid(self):
        self.assertEqual(plugins.check(ON_DEMAND), [])
        self.assertEqual(plugins.key_scopes(ON_DEMAND), ["media"])
        self.assertEqual([p["risk"] for p in plugins.permission_words(ON_DEMAND)], ["medium", "medium", "high"])

    def test_bad_manifests_say_what_is_wrong(self):
        bad = {**ON_DEMAND, "privileged": True, "id": "On Demand!", "starboard_api": ">=2.0"}
        problems = plugins.check(bad)
        self.assertIn("Unknown field privileged", problems)
        self.assertTrue(any(p.startswith("id must be") for p in problems))
        self.assertTrue(any("needs Starboard's API >=2.0" in p for p in problems))

    def test_never_granted_whatever_the_manifest_says(self):
        for change in ({"volumes": ["/var/run/docker.sock:/var/run/docker.sock"]}, {"volumes": ["../../etc"]},
                       {"network": "host"}, {"user": "0:0"}, {"image": "ghcr.io/example/x:latest"}, {"devices": ["/dev/dri"]}):
            c = {**ON_DEMAND["containers"][0], **change}
            self.assertNotEqual(plugins.check({**ON_DEMAND, "containers": [c, ON_DEMAND["containers"][1]]}), [], change)
        tagged = {**ON_DEMAND["containers"][0], "image": "ghcr.io/example/x:0.2.0"}
        self.assertEqual(plugins.check({**ON_DEMAND, "containers": [tagged, ON_DEMAND["containers"][1]]}, dev=True), [])

    def test_a_network_or_folder_needs_its_permission(self):
        m = {**ON_DEMAND, "permissions": []}
        problems = plugins.check(m)
        self.assertTrue(any("needs the permission network:vpn" in p for p in problems))

    def test_the_compose_file_has_the_hardened_defaults(self):
        text = plugins.compose(ON_DEMAND, "/srv/starboard/data/plugins/on-demand", "/srv/media")
        for line in ("read_only: true", "- ALL", "- no-new-privileges:true", "pids_limit: 64", "mem_limit: 40m", "mem_limit: 250m",
                     'network_mode: "container:gluetun"', '"/srv/media/on-demand:/media/on-demand"', "starboard.idle_stop_minutes"):
            self.assertIn(line, text)
        for never in ("privileged", "docker.sock", "network_mode: host", "devices", "cap_add"):
            self.assertNotIn(never, text)
        plain = {**ON_DEMAND, "permissions": [], "containers": [{"name": "main", "image": f"ghcr.io/example/hello@{DIGEST}", "port": 8080}], "resources": {}}
        text = plugins.compose(plain, "/srv/p", "/srv/media")
        self.assertIn("internal: true", text)
        self.assertIn('user: "10001:10001"', text)
        self.assertIn("mem_limit: 128m", text)

    def test_a_container_may_run_as_the_media_folders_owner(self):  # API 1.12 (DASH-410)
        tracks = {**ON_DEMAND, "permissions": ["jellyfin:key", "network:lan"],
                  "containers": [{"name": "main", "image": f"ghcr.io/example/tracks@{DIGEST}", "port": 8080, "network": "lan",
                                  "volumes": ["data", "media/movies", "media/tv"], "user": "media"}], "resources": {}}
        self.assertEqual(plugins.check(tracks), [])
        self.assertIn('user: "1001:1002"', plugins.compose(tracks, "/srv/p", "/srv/media", media_user="1001:1002"))
        self.assertIn('user: "1000:1000"', plugins.compose(tracks, "/srv/p", "/srv/media"))
        self.assertIn('user: "1000:1000"', plugins.compose(tracks, "/srv/p", "/srv/media", media_user="0:0"))  # never root
        warning = plugins.install_warning(tracks)
        self.assertTrue(any(c.startswith("Files in your media folder under movies") for c in warning["change"]))  # API 1.13 says what it can do there
        self.assertTrue(any("owner of your media folder" in c for c in warning["change"]))
        only_data = {**tracks, "containers": [{**tracks["containers"][0], "volumes": ["data", "media:ro"]}]}
        self.assertIn("containers[0]: user media is only for a container that mounts media/<one folder>", plugins.check(only_data))
        self.assertTrue(any("non-root uid:gid" in p for p in plugins.check({**tracks, "containers": [{**tracks["containers"][0], "user": "root"}]})))

    def test_api_ranges(self):
        self.assertTrue(plugins._range_ok(">=1.0 <2.0", "1.4.2"))
        self.assertFalse(plugins._range_ok(">=1.0 <2.0", "2.0.0"))
        self.assertFalse(plugins._range_ok("~1.0", "1.0.0"))

    def test_changes_are_optional_and_checked(self):  # API 1.10 (DASH-393)
        self.assertEqual(plugins.check({**ON_DEMAND, "changes": [{"version": "0.2.0", "date": "2026-11-13", "added": ["Usenet"]}]}), [])
        bad = plugins.check({**ON_DEMAND, "changes": [{"version": "soon", "added": "Usenet", "colour": "red"}, {"version": "0.1.0"}]})
        self.assertIn("changes[0]: unknown field colour", bad)
        self.assertIn("changes[0]: needs its own version, such as 1.2.0", bad)
        self.assertIn("changes[0]: added must list one to 20 lines of up to 300 characters", bad)
        self.assertTrue(any("changes[1]: needs at least one of" in b for b in bad))
        self.assertEqual(plugins.check({**ON_DEMAND, "changes": []}), ["changes must list one to 20 versions, newest first"])

    def test_the_published_schema_is_up_to_date(self):
        path = os.path.join(os.path.dirname(plugins.__file__), "plugin-manifest.schema.json")
        with open(path) as f:
            shipped = json.load(f)
        self.assertEqual(sorted(shipped["required"]), sorted(plugins.REQUIRED))
        self.assertEqual(sorted(shipped["properties"]), sorted(plugins.TOP))


if __name__ == "__main__":
    unittest.main()
