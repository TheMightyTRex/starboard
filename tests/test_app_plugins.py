"""App plug-ins (plug-in API 1.13, DASH-411, owner, 13 November 2026: "a plugin that can install and uninstall jellystat
as an option"): an app with its database on a private network, its web page on the home network at a port Starboard
chooses, a database password made for the install, Jellyfin's details handed over, data mounted where the app wants
it, a clear choice on removal, and copying an app the main install already runs (adopt)."""
import json
import os
import tempfile
import unittest
from unittest import mock

from starboard import plugins, plugins_admin as pa

PG = "docker.io/library/postgres@sha256:" + "a" * 64
APP = "docker.io/example/app@sha256:" + "b" * 64


def app_manifest(**more):
    m = {"manifest_version": 1, "id": "stats-app", "name": "Stats app", "version": "1.0.0", "description": "An app and its database",
         "author": "TheMightyTRexUK", "licence": "MIT", "homepage": "https://example.org", "support_url": "https://example.org",
         "starboard_api": ">=1.13 <2.0", "permissions": ["jellyfin:key", "network:lan", "network:port"],
         "containers": [
             {"name": "app", "image": APP, "port": 3000, "network": "lan", "publish": True, "host_port": 3000,
              "volumes": ["data:/app/backup", "media/music:ro"],
              "env": {"DB_PASSWORD": "{secret:db_password}", "JF_HOST": "{jellyfin:url}", "JF_API_KEY": "{jellyfin:key}", "serverIP": "0.0.0.0"}},
             {"name": "db", "image": PG, "port": 5432, "user": "70:70", "volumes": ["data"], "tmpfs": ["/var/run/postgresql"],
              "env": {"POSTGRES_PASSWORD": "{secret:db_password}", "PGDATA": "/data/pgdata"}}],
         "resources": {"app": {"memory": 256, "cpus": 0.5, "pids": 128}}}
    m.update(more)
    return m


class Check(unittest.TestCase):
    def test_an_app_with_its_database_passes(self):
        self.assertEqual(plugins.check(app_manifest()), [])

    def test_publish_on_the_home_network_needs_network_port(self):
        m = app_manifest(permissions=["jellyfin:key", "network:lan"])
        self.assertIn("containers[0]: publish on the lan network needs the permission network:port", plugins.check(m))
        m = app_manifest()
        m["containers"][1]["publish"] = True  # the database, on the private network only
        self.assertTrue([p for p in plugins.check(m) if "containers[1]: publish" in p])

    def test_paths_inside_and_tmpfs_are_limited(self):
        for bad in (["/run/starboard"], ["/"], ["/a/../etc"], ["/tmp"], ["x"], ["/a"] * 7):
            m = app_manifest()
            m["containers"][1]["tmpfs"] = bad
            self.assertTrue([p for p in plugins.check(m) if "tmpfs" in p], bad)
        for bad in ("data:/", "data:/tmp", "data:/run/starboard/x", "data:relative", "data/../x:/a", "media/music:rw"):
            m = app_manifest()
            m["containers"][0]["volumes"] = [bad]
            self.assertTrue([p for p in plugins.check(m) if "containers[0]" in p], bad)

    def test_holes_in_env(self):
        m = app_manifest(permissions=["network:lan", "network:port"])
        self.assertTrue([p for p in plugins.check(m) if "{jellyfin:url}" in p])
        m = app_manifest()
        m["containers"][0]["env"]["X"] = "{secret:Bad-Name}"
        self.assertTrue([p for p in plugins.check(m) if "Starboard does not know" in p])

    def test_pids_and_host_port(self):
        m = app_manifest()
        m["resources"]["app"]["pids"] = 5000
        self.assertTrue([p for p in plugins.check(m) if "pids" in p])
        m = app_manifest()
        m["containers"][0]["host_port"] = 80
        self.assertTrue([p for p in plugins.check(m) if "host_port" in p])

    def test_adopt(self):
        ok = {"app": "tdarr", "name": "Tdarr", "into": "app", "copy": {"/app/server": "server"}, "stop": True}
        self.assertEqual(plugins.check(app_manifest(adopt=ok)), [])
        for bad in ({**ok, "into": "nothing"}, {**ok, "copy": {"/app/server": "../x"}}, {**ok, "copy": {}}, {**ok, "app": "Bad Name"},
                    {**ok, "delete": True}):
            self.assertTrue([p for p in plugins.check(app_manifest(adopt=bad)) if "adopt" in p], bad)

    def test_the_warning_says_the_page_and_the_read_only_folder(self):
        w = plugins.install_warning(app_manifest())
        self.assertTrue(any("anyone on your home network can open it" in r for r in w["reach"]))
        self.assertIn("Files in your media folder under music (read only)", w["see"])
        w = plugins.install_warning(app_manifest(adopt={"app": "tdarr", "name": "Tdarr", "into": "app", "copy": {"/a": "a"}}))
        self.assertTrue(any("never changed" in c for c in w["change"]))


class Compose(unittest.TestCase):
    def test_ports_secrets_jellyfin_tmpfs_and_data_paths(self):
        text = plugins.compose(app_manifest(), "/srv/data/plugins/stats-app", "/srv/media", None, extra=
                               {"ports": {"app": 3001}, "secrets": {"db_password": "s3cret"},
                                "jellyfin": {"url": "http://host.docker.internal:8096", "api_key": "jfkey"}})
        app, db = text.split("  plugin-stats-app-db:")
        self.assertIn('- "3001:3000"', app)
        self.assertNotIn("ports:", db)  # the database stays on the private network only
        self.assertIn('DB_PASSWORD: "s3cret"', app)
        self.assertIn('POSTGRES_PASSWORD: "s3cret"', db)
        self.assertIn('JF_API_KEY: "jfkey"', app)
        self.assertIn('serverIP: "0.0.0.0"', app)
        self.assertIn('"/srv/data/plugins/stats-app/data/app:/app/backup"', app)
        self.assertIn('"/srv/media/music:/media/music:ro"', app)
        self.assertIn('- "/var/run/postgresql:size=64m,mode=0700,uid=70,gid=70"', db)
        self.assertIn("pids_limit: 128", app)
        for hardened in ("read_only: true", "cap_drop:", "no-new-privileges:true"):
            self.assertIn(hardened, app)
            self.assertIn(hardened, db)

    def test_media_user_and_extra_together(self):
        # API 1.12's user "media" with 1.13's tmpfs and port: the tmpfs belongs to the media folder's owner
        m = app_manifest()
        m["containers"][0].update(user="media", tmpfs=["/run"], volumes=["data:/app/backup", "media/movies"])
        text = plugins.compose(m, "/p", "/m", None, media_user="1001:1002", extra={"ports": {"app": 3000}})
        app = text.split("  plugin-stats-app-db:")[0]
        self.assertIn('user: "1001:1002"', app)
        self.assertIn('- "/run:size=64m,mode=0700,uid=1001,gid=1002,exec"', app)
        self.assertIn('- "3000:3000"', app)
        w = plugins.install_warning(m)
        self.assertIn("Files in your media folder under movies: it can change, replace and remove them", w["change"])
        self.assertTrue(any("owner of your media folder" in c for c in w["change"]))

    def test_without_details_a_hole_is_left_empty(self):
        text = plugins.compose(app_manifest(), "/p", "/m")
        self.assertIn('DB_PASSWORD: ""', text)
        self.assertNotIn("ports:", text)


class Admin(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = self.tmp.name
        for target, value in ((pa, "host_path"), (pa, "ports_in_use"), (pa, "_media_dir_from")):
            p = mock.patch.object(target, value, {"host_path": lambda d, pid: f"/srv/data/plugins/{pid}",
                                                  "ports_in_use": lambda skip=None: {3000},
                                                  "_media_dir_from": lambda where: "/srv/media"}[value])
            p.start()
            self.addCleanup(p.stop)
        pa.install(self.d, app_manifest(), "/srv/media")
        self.where = pa.folder(self.d, "stats-app")

    def compose_text(self):
        with open(os.path.join(self.where, "compose.yaml")) as f:
            return f.read()

    def test_secret_made_once_and_kept_owner_only(self):
        pa.write_compose(self.d, "stats-app")
        first = json.load(open(os.path.join(self.where, "secrets.json")))["db_password"]
        self.assertGreaterEqual(len(first), 32)
        self.assertEqual(oct(os.stat(os.path.join(self.where, "secrets.json")).st_mode & 0o777), "0o600")
        pa.write_compose(self.d, "stats-app")
        self.assertEqual(json.load(open(os.path.join(self.where, "secrets.json")))["db_password"], first)
        self.assertIn(f'DB_PASSWORD: "{first}"', self.compose_text())

    def test_port_chosen_free_and_kept(self):
        # 3000 is taken by another container, so the next one is chosen, and kept on the next start
        self.assertEqual(pa.choose_ports(self.d, "stats-app", app_manifest()), {"app": 3001})
        self.assertEqual(pa.choose_ports(self.d, "stats-app", app_manifest()), {"app": 3001})
        self.assertEqual(pa.choose_ports(self.d, "stats-app", app_manifest(), refused=[3001]), {"app": 3002})
        self.assertEqual(pa.listing(self.d)[0]["web"], [{"container": "app", "port": 3002, "label": "Open Stats app"}])

    def test_reserved_ports_never_chosen(self):
        m = app_manifest()
        m["containers"][0]["host_port"] = 8095  # Starboard's own
        self.assertNotEqual(pa.choose_ports(self.d, "stats-app", m)["app"], 8095)

    def test_a_port_taken_outside_docker_is_tried_again(self):
        calls = []

        def helper(folder, script):
            calls.append(script)
            if len(calls) == 1:
                return 1, "Error response from daemon: failed to bind host port 0.0.0.0:3001/tcp: address already in use"
            return 0, "Started"
        pa.enable(self.d, "stats-app", helper=helper)
        self.assertEqual(len(calls), 2)
        self.assertIn('- "3002:3000"', self.compose_text())
        self.assertEqual(pa.listing(self.d)[0]["state"], "enabled")

    def test_remove_to_the_holding_folder(self):
        held = pa.uninstall(self.d, "stats-app", helper=lambda f, s: (0, ""), to_holding=True)
        self.assertTrue(held.endswith("holding"))
        names = os.listdir(held)
        self.assertTrue(any(n.endswith("stats-app-" + n.rsplit("stats-app-", 1)[-1]) and not n.endswith(".json") for n in names))
        self.assertFalse(os.path.exists(self.where))

    def test_remove_keeps_it_by_default(self):
        kept = pa.uninstall(self.d, "stats-app", helper=lambda f, s: (0, ""))
        self.assertIn(".removed", kept)
        self.assertTrue(os.path.isdir(kept))


class Adopt(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = self.tmp.name
        p = mock.patch.object(pa, "host_path", lambda d, pid: f"/srv/data/plugins/{pid}")
        p.start()
        self.addCleanup(p.stop)
        self.m = app_manifest(adopt={"app": "tdarr", "name": "Tdarr", "into": "app", "stop": True,
                                     "copy": {"/app/server": "server", "/app/configs": "configs"}})
        pa.install(self.d, self.m, "/srv/media")
        self.docker_calls = []

    def docker(self, method, path, body=None, timeout=None, **kw):
        self.docker_calls.append((method, path))
        if path == "/containers/tdarr/json":
            return {"State": {"Running": True}, "Mounts": [
                {"Type": "bind", "Source": "/home/me/config/tdarr/server", "Destination": "/app/server"},
                {"Type": "bind", "Source": "/home/me/config/tdarr/configs", "Destination": "/app/configs"},
                {"Type": "bind", "Source": "/mnt/media", "Destination": "/media"}]}
        return {}

    def test_preview_and_copy_never_move(self):
        from starboard import containers
        scripts = []
        with mock.patch.object(containers, "docker", self.docker):
            v = pa.adopt_preview(self.d, "stats-app")
            self.assertTrue(v["found"] and v["stops"])
            self.assertEqual([f["to"] for f in v["folders"]], ["data/app/server", "data/app/configs"])
            said = pa.adopt(self.d, "stats-app", helper=lambda folder, script: scripts.append(script) or (0, "42"))
        self.assertIn(("POST", "/containers/tdarr/stop?t=60"), self.docker_calls)
        self.assertNotIn("rm ", scripts[0].replace("rm -", ""))
        self.assertIn("cp -a '/home/me/config/tdarr/server'/. 'data/app/server'/", scripts[0])
        self.assertIn("chown -R 10001:10001 'data/app/server'", scripts[0])
        self.assertNotIn("/mnt/media", scripts[0])  # only the folders the manifest names
        self.assertIn("about 42 MB", said)
        self.assertIn("stopped, not removed", said)
        st = json.load(open(os.path.join(pa.folder(self.d, "stats-app"), "state.json")))
        self.assertEqual(st["adopted"]["app"], "tdarr")

    def test_copies_belong_to_the_media_folders_owner(self):
        from starboard import containers
        m = json.loads(json.dumps(self.m))
        m["containers"][0].update(user="media", volumes=["data:/app/backup", "media/movies"])
        with open(os.path.join(pa.folder(self.d, "stats-app"), "manifest.json"), "w") as f:
            json.dump(m, f)
        scripts = []
        with mock.patch.object(containers, "docker", self.docker), mock.patch.object(pa, "media_owner", lambda d: "1001:1002"):
            pa.adopt(self.d, "stats-app", helper=lambda folder, script: scripts.append(script) or (0, "1"))
        self.assertIn("chown -R 1001:1002 'data/app/server'", scripts[0])

    def test_refused_while_active_and_when_missing(self):
        from starboard import containers
        pa.set_state(self.d, "stats-app", "enabled")
        with mock.patch.object(containers, "docker", self.docker), self.assertRaisesRegex(ValueError, "Deactivate"):
            pa.adopt(self.d, "stats-app", helper=lambda f, s: (0, ""))
        pa.set_state(self.d, "stats-app", "disabled")

        def missing(*a, **k):
            raise containers.DockerError("No such container")
        with mock.patch.object(containers, "docker", missing):
            self.assertFalse(pa.adopt_preview(self.d, "stats-app")["found"])


class Catalogue(unittest.TestCase):
    def test_rest_figures_are_cleaned(self):
        base = {"id": "jellystat", "name": "Jellystat", "manifest": "https://example.org/m.json", "kind": "Apps you can add"}
        self.assertEqual(pa._clean_entry({**base, "rest": {"memory_mb": 117.4, "cpu_percent": 0.22}})["rest"], {"memory_mb": 117, "cpu_percent": 0.22})
        for bad in ("lots", {"memory_mb": "x"}, {"memory_mb": -1}, None):
            self.assertIsNone(pa._clean_entry({**base, "rest": bad})["rest"])


if __name__ == "__main__":
    unittest.main()
