"""Taking over apps someone runs from their own Compose file (takeover.py, DASH-151): what each app keeps, the
Compose file Starboard writes for it, the rollback point, and the helper's scripts, run for real against temporary
folders with a stand-in docker command."""
import json
import os
import re
import stat
import subprocess
import tempfile
import unittest
from unittest import mock

from starboard import stack, takeover

BASE = "/home/owner/jellyfin/config"


def jellyfin_info(net="stack_proxy"):
    return {"Image": "sha256:jf", "Name": "/jellyfin",
            "Config": {"Image": "lscr.io/linuxserver/jellyfin:latest",
                       "Env": ["PUID=1000", "PGID=1000", "JELLYFIN_PublishedServerUrl=http://films.example", "PATH=/usr/bin",
                               "S6_STAGE2_HOOK=/x"]},
            "HostConfig": {"NetworkMode": net, "Devices": [{"PathOnHost": "/dev/dri", "PathInContainer": "/dev/dri"}],
                           "PortBindings": {"8096/tcp": [{"HostPort": "8096"}], "8920/tcp": [{"HostPort": "8920"}]}},
            "Mounts": [{"Type": "bind", "Source": "/mnt/pool/media", "Destination": "/media", "RW": True},
                       {"Type": "bind", "Source": "/mnt/pool", "Destination": "/pool", "RW": True},
                       {"Type": "bind", "Source": f"{BASE}/jellyfin/config", "Destination": "/config", "RW": True}]}


IMAGE_ENV = {"PATH": "/usr/bin", "S6_STAGE2_HOOK": "/x"}
GLOBALS = {"PUID": "1000", "PGID": "1000", "TZ": "Europe/London"}


class KeepTest(unittest.TestCase):
    def test_jellyfin_keeps_paths_devices_ports_and_its_own_settings(self):
        keep, copies, shared = takeover.keep_for("jellyfin", "jellyfin", jellyfin_info(), IMAGE_ENV, "/srv/new", "/mnt/pool",
                                                 BASE, GLOBALS, {})
        self.assertEqual(copies, [(f"{BASE}/jellyfin/config", "/srv/new/jellyfin")])
        self.assertIn("/mnt/pool/media:/media", keep["volumes"])
        self.assertIn("/mnt/pool:/pool", keep["volumes"])
        self.assertEqual(keep["devices"], ["/dev/dri"])
        self.assertEqual(keep["ports"], ["8920:8920"])
        self.assertEqual(keep["port_map"], {"8096": 8096})
        self.assertEqual(keep["env"], {"JELLYFIN_PublishedServerUrl": {"value": "http://films.example"}})
        self.assertNotIn("image", keep)  # the image Starboard uses anyway
        self.assertEqual(shared, [])

    def test_app_through_the_vpn_keeps_the_port_gluetun_publishes(self):
        info = {"Image": "sha256:b", "Config": {"Image": "lscr.io/linuxserver/bazarr:latest", "Env": []},
                "HostConfig": {"NetworkMode": "container:abc", "PortBindings": {}},
                "Mounts": [{"Type": "bind", "Source": f"{BASE}/bazarr/config", "Destination": "/config"},
                           {"Type": "bind", "Source": "/mnt/pool", "Destination": "/data"}]}
        keep, copies, _ = takeover.keep_for("bazarr", "bazarr", info, {}, "/srv/new", "/mnt/pool", BASE, GLOBALS,
                                            {"abc": "gluetun"}, {"6767/tcp": [{"HostPort": "16767"}]})
        self.assertTrue(keep["vpn"])  # Bazarr is not through the VPN by default: kept as it was
        self.assertEqual(keep["port_map"], {"6767": 16767})
        self.assertEqual(keep["volumes"], ["/mnt/pool:/data"])

    def test_secrets_go_to_env_and_placeholders_keep_their_value(self):
        info = {"Image": "x", "Config": {"Image": "cyfershepard/jellystat:latest",
                                         "Env": ["POSTGRES_PASSWORD=old-pw", "JWT_SECRET=old-jwt", "POSTGRES_IP=jellystat-db",
                                                 "API_TOKEN=tok"]},
                "HostConfig": {}, "Mounts": []}
        keep, _, _ = takeover.keep_for("jellystat", "jellystat", info, {}, "/srv/new", "/mnt/pool", BASE, GLOBALS, {})
        self.assertEqual(keep["vars"], {"JELLYSTAT_DB_PASSWORD": "old-pw", "JELLYSTAT_JWT_SECRET": "old-jwt"})
        self.assertEqual(keep["env"], {"API_TOKEN": {"var": "KEPT_JELLYSTAT_API_TOKEN", "value": "tok"}})

    def test_a_secret_with_a_quote_mark_is_refused(self):
        info = {"Image": "x", "Config": {"Image": "i", "Env": ["MY_PASSWORD=it's"]}, "HostConfig": {}, "Mounts": []}
        with self.assertRaisesRegex(ValueError, "' mark"):
            takeover.keep_for("wizarr", "wizarr", info, {}, "/srv/new", "/mnt/pool", BASE, GLOBALS, {})

    def test_an_extra_settings_folder_goes_beside_the_app_folder(self):
        info = {"Image": "x", "Config": {"Image": "ghcr.io/wizarrrr/wizarr:latest", "Env": []}, "HostConfig": {},
                "Mounts": [{"Type": "bind", "Source": f"{BASE}/wizarr/data/database", "Destination": "/data/database"},
                           {"Type": "bind", "Source": f"{BASE}/wizarr/cache", "Destination": "/.cache"}]}
        keep, copies, _ = takeover.keep_for("wizarr", "wizarr", info, {}, "/srv/new", "/mnt/pool", BASE, GLOBALS, {})
        self.assertEqual(copies, [(f"{BASE}/wizarr/data/database", "/srv/new/wizarr"),
                                  (f"{BASE}/wizarr/cache", "/srv/new/wizarr-kept/.cache")])
        self.assertEqual(keep["volumes"], ["${CONFIG_DIR}/wizarr-kept/.cache:/.cache"])

    def test_config_base_is_the_common_parent(self):
        infos = {"jellyfin": jellyfin_info(),
                 "bazarr": {"Mounts": [{"Source": f"{BASE}/bazarr/config", "Destination": "/config"}]}}
        self.assertEqual(takeover.config_base(infos, {"jellyfin": "jellyfin", "bazarr": "bazarr"}), BASE)


class BuildTest(unittest.TestCase):
    def choice(self, keep):
        return {"apps": ["jellyfin", "qbittorrent", "gluetun"], "config_dir": "/srv/new", "data_dir": "/mnt/pool", "tz": "Europe/London",
                "vpn": {"provider": "mullvad", "type": "openvpn", "openvpn_user": "u", "openvpn_password": "p"}, "keep": keep}

    def test_build_writes_what_was_kept(self):
        keep = {"jellyfin": {"port_map": {"8096": 8096}, "ports": ["8920:8920"], "devices": ["/dev/dri"],
                             "volumes": ["/mnt/pool/media:/media", "/mnt/pool/films:/data/media"],
                             "env": {"JELLYFIN_PublishedServerUrl": {"value": "http://a/$x"}, "SECRET_KEY": {"var": "KEPT_JF_SECRET_KEY", "value": "s3"}}},
                "qbittorrent": {"image": "lscr.io/linuxserver/qbittorrent:pinned", "port_map": {"8080": 18080}},
                "gluetun": {"env": {"VPN_PORT_FORWARDING_UP_COMMAND": {"value": "/bin/sh -c 'wget \"{{PORT}}\"'"}}}}
        taken = {8096, 8920, 8080, 18080}  # the kept ports are in use (by the old apps): they still do not move
        with mock.patch.object(stack, "_port_free", side_effect=lambda port: port not in taken):
            built = stack.build(self.choice(keep))
        c = built["compose"]
        jf = re.search(r"(?ms)^  jellyfin:\n(.*?)(?=^  \S)", c).group(1)
        self.assertIn('"8096:8096"', jf)
        self.assertIn('"8920:8920"', jf)
        self.assertIn('"/dev/dri"', jf)
        self.assertIn('"/mnt/pool/media:/media"', jf)
        self.assertIn('"/mnt/pool/films:/data/media"', jf)
        self.assertNotIn("${DATA_DIR}/media:/data/media", jf)  # replaced by the kept one for the same place
        self.assertIn('JELLYFIN_PublishedServerUrl: "http://a/$$x"', jf)
        self.assertIn('SECRET_KEY: "${KEPT_JF_SECRET_KEY}"', jf)
        self.assertNotIn("s3", c)
        self.assertIn("KEPT_JF_SECRET_KEY=s3", built["env"])
        self.assertIn("image: lscr.io/linuxserver/qbittorrent:pinned", c)
        self.assertIn('"18080:8080"', re.search(r"(?ms)^  gluetun:\n(.*?)(?=^  \S|\Z)", c).group(1))
        self.assertIn("\\\"{{PORT}}\\\"", c)
        self.assertEqual(built["moved"], [m for m in built["moved"] if "Jellyfin" not in m and "qBittorrent" not in m])

    def test_kept_values_replace_made_up_ones(self):
        choice = {"apps": ["jellystat"], "config_dir": "/srv/new", "data_dir": "/mnt/pool",
                  "keep": {"jellystat": {"vars": {"JELLYSTAT_DB_PASSWORD": "old", "JELLYSTAT_JWT_SECRET": "jwt"}},
                           "jellystat-db": {"vars": {"JELLYSTAT_DB_PASSWORD": "old"}}}}
        built = stack.build(choice)
        self.assertIn("JELLYSTAT_DB_PASSWORD=old\n", built["env"])
        self.assertEqual(built["env_shown"]["JELLYSTAT_DB_PASSWORD"], "(kept from your old set-up)")
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "stack"))
            with open(os.path.join(d, "stack", ".env"), "w") as f:
                f.write("JELLYSTAT_DB_PASSWORD=made-up-earlier\n")
            stack.write(d, built)
            with open(os.path.join(d, "stack", ".env")) as f:
                self.assertIn("JELLYSTAT_DB_PASSWORD=old\n", f.read())  # not swapped back for the made-up one

    def test_kept_json_round_trip_and_later_changes_keep_it(self):
        keep = {"jellyfin": {"port_map": {"8096": 8096}, "devices": ["/dev/dri"],
                             "env": {"A": {"value": "1"}, "B_TOKEN": {"var": "KEPT_JELLYFIN_B_TOKEN", "value": "t"}}}}
        with tempfile.TemporaryDirectory() as d:
            built = stack.build({"apps": ["jellyfin"], "config_dir": "/srv/new", "data_dir": "/mnt/pool", "keep": keep})
            stack.write(d, built)
            stack.save_keep(d, keep)
            with open(os.path.join(d, "stack", stack.KEEP_FILE)) as f:
                self.assertNotIn('"t"', f.read())  # the secret's value lives in .env only
            again = stack.current_choice(d)
            self.assertEqual(again["keep"]["jellyfin"]["env"]["B_TOKEN"]["value"], "t")
            self.assertEqual(stack.build(again)["compose"], built["compose"])


def fake_found(running=True):
    def c(name, key, project="stack", service=None):
        return {"name": name, "key": key, "running": running, "project": project, "service": service or name,
                "folder": "/home/owner/jellyfin/stack", "files": ["/home/owner/jellyfin/stack/docker-compose.yml"]}
    return [c("jellyfin", "jellyfin"), c("radarr", "radarr"), c("sabnzbd", "sabnzbd"), c("kapowarr", "kapowarr"),
            {**c("storyarr", "storyarr"), "running": False}, {**c("wizarr", "wizarr"), "project": None}]


class PlanTest(unittest.TestCase):
    def test_sorts_apps_and_keeps_ports(self):
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(takeover.containers, "available", return_value=True), \
                mock.patch.object(takeover, "found", return_value=fake_found()), \
                mock.patch.object(takeover, "_inspect", return_value=jellyfin_info()), \
                mock.patch.object(takeover, "_image_env", return_value=IMAGE_ENV), \
                mock.patch.object(takeover.containers, "docker", return_value=[]), \
                mock.patch.object(stack, "can_download", return_value=True):
            p = takeover.plan(d, "full", "nzbget", config_dir="/srv/new", media_dir="/mnt/pool")
        self.assertEqual([t["name"] for t in p["take"]], ["jellyfin"])
        self.assertEqual({r["name"]: r["by"] for r in p["replace"]}, {"radarr": "Reelix", "sabnzbd": "NZBGet"})
        why = {l["name"]: l["why"] for l in p["leave"]}
        self.assertIn("not part of Full install", why["kapowarr"])
        self.assertIn("stopped", why["storyarr"])
        self.assertIn("Compose file", why["wizarr"])
        self.assertTrue(p["sab"])
        self.assertIn(8096, p["choice"]["own_ports"])
        self.assertIn("Reelix", p["new"])

    def test_refuses_a_settings_folder_inside_the_old_one(self):
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(takeover.containers, "available", return_value=True), \
                mock.patch.object(takeover, "found", return_value=fake_found()), \
                mock.patch.object(takeover, "_inspect", return_value=jellyfin_info()), \
                mock.patch.object(takeover.containers, "docker", return_value=[]), \
                mock.patch.object(stack, "can_download", return_value=True):
            with self.assertRaisesRegex(ValueError, "outside"):
                takeover.plan(d, "full", config_dir=f"{BASE}/jellyfin/config/new", media_dir="/mnt/pool")


class RecordTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        os.makedirs(os.path.join(self.d, "stack"))
        with open(os.path.join(self.d, "stack", "compose.yaml"), "w") as f:
            f.write("services:\n  reelix:\n    image: x\n    container_name: reelix\n")
        self.p = {"containers": fake_found()[:2], "copies": [("/a", "/b")], "install": "full"}

    def tearDown(self):
        self.tmp.cleanup()

    def test_record_tags_images_and_pins_them(self):
        tagged = []
        with mock.patch.object(takeover, "_inspect", side_effect=lambda n: {"Image": f"sha256:{n}", "Config": {"Image": f"img/{n}"}}):
            rec = takeover.make_record(self.d, self.p, "20261108-1200", tag=lambda i, r, t: tagged.append((i, r, t)))
        self.assertEqual(tagged, [("sha256:jellyfin", "starboard-rollback/jellyfin", "20261108-1200"),
                                  ("sha256:radarr", "starboard-rollback/radarr", "20261108-1200")])
        with open(os.path.join(self.d, "stack", "takeover", "rollback-stack.yaml")) as f:
            self.assertIn("image: starboard-rollback/radarr:20261108-1200", f.read())
        self.assertTrue(rec["had_stack"])
        self.assertTrue(os.path.exists(os.path.join(self.d, "stack", "takeover", "stack-before", "compose.yaml")))
        with self.assertRaisesRegex(ValueError, "rolled back"):  # one takeover at a time
            takeover.make_record(self.d, self.p, "x", tag=lambda *a: None)

    def test_rollback_script_restores_starboard_then_starts_the_old_apps(self):
        with mock.patch.object(takeover, "_inspect", side_effect=lambda n: {"Image": f"sha256:{n}", "Config": {}}):
            rec = takeover.make_record(self.d, self.p, "s", tag=lambda *a: None)
        script = takeover.rollback_script(rec, "/host/stack")
        self.assertLess(script.index("stack-before/compose.yaml"), script.index("--remove-orphans"))
        self.assertIn("up -d --no-deps 'jellyfin' 'radarr'", script)
        self.assertIn("-f '/host/stack'/takeover/rollback-'stack'.yaml", script)


STUB = """#!/bin/sh
echo "docker $*" >> "$DOCKER_LOG"
case "$1 $2" in "stop "*) [ -n "$FAIL_STOP" ] && exit 1 ;; esac
exit 0
"""


class ScriptTest(unittest.TestCase):
    """The takeover script, run for real with sh, GNU tools and a stand-in docker."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        self.bin = os.path.join(t, "bin")
        os.makedirs(self.bin)
        with open(os.path.join(self.bin, "docker"), "w") as f:
            f.write(STUB)
        os.chmod(os.path.join(self.bin, "docker"), 0o755)
        self.old = os.path.join(t, "old", "jellyfin", "config")
        os.makedirs(os.path.join(self.old, "data"))
        with open(os.path.join(self.old, "data", "library.db"), "w") as f:
            f.write("films")
        os.chmod(self.old, 0o750)
        self.cfg = os.path.join(t, "new")
        self.hs = os.path.join(t, "stack")
        os.makedirs(self.hs)
        compose_dir = os.path.join(t, "compose")
        os.makedirs(compose_dir)
        with open(os.path.join(compose_dir, "docker-compose.yml"), "w") as f:
            f.write("services: {}\n")
        self.rec = {"containers": [{"name": "jellyfin", "project": "stack", "service": "jellyfin", "folder": compose_dir,
                                    "files": [os.path.join(compose_dir, "docker-compose.yml")]}],
                    "copies": [(self.old, os.path.join(self.cfg, "jellyfin"))]}
        self.log = os.path.join(t, "docker.log")

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, **env):
        script = takeover.takeover_script(self.rec, self.hs, self.cfg, None, [os.path.join(self.cfg, "tdarr")])
        return subprocess.run(["sh", "-c", script], env={**os.environ, "PATH": f"{self.bin}:{os.environ['PATH']}",
                                                         "DOCKER_LOG": self.log, **env}, capture_output=True, text=True)

    def calls(self):
        with open(self.log) as f:
            return f.read().splitlines()

    def test_stops_copies_removes_then_starts(self):
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with open(os.path.join(self.cfg, "jellyfin", "data", "library.db")) as f:
            self.assertEqual(f.read(), "films")
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(self.cfg, "jellyfin")).st_mode), 0o750)  # as the old folder
        self.assertTrue(os.path.exists(os.path.join(self.old, "data", "library.db")))  # the old folder is untouched
        calls = self.calls()
        self.assertEqual([c.split()[1] for c in calls], ["stop", "rm", "compose"])
        self.assertTrue(os.path.exists(os.path.join(self.hs, "takeover", "old", "stack--docker-compose.yml")))
        self.assertTrue(os.path.isdir(os.path.join(self.cfg, "tdarr")))

    def test_a_folder_with_files_is_never_copied_over_and_the_apps_start_again(self):
        os.makedirs(os.path.join(self.cfg, "jellyfin"))
        with open(os.path.join(self.cfg, "jellyfin", "mine"), "w") as f:
            f.write("x")
        r = self.run_script()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Already has files", r.stdout)
        self.assertEqual([c.split()[1] for c in self.calls()], ["stop", "start"])  # no rm, no compose: back as it was
        self.assertFalse(os.path.exists(os.path.join(self.cfg, "jellyfin", "data")))

    def test_an_empty_folder_gets_the_contents_not_a_folder_inside(self):
        os.makedirs(os.path.join(self.cfg, "jellyfin"))
        self.assertEqual(self.run_script().returncode, 0)
        self.assertTrue(os.path.exists(os.path.join(self.cfg, "jellyfin", "data", "library.db")))
        self.assertFalse(os.path.exists(os.path.join(self.cfg, "jellyfin", "config")))

    def test_a_failed_stop_starts_them_again(self):
        r = self.run_script(FAIL_STOP="1")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual([c.split()[1] for c in self.calls()], ["stop", "start"])
        self.assertFalse(os.path.exists(os.path.join(self.cfg, "jellyfin")))


class RestoreTest(unittest.TestCase):
    def test_a_failed_takeover_puts_starboards_files_back(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "stack"))
            for name, text in (("compose.yaml", "before"), (".env", "A=1\n")):
                with open(os.path.join(d, "stack", name), "w") as f:
                    f.write(text)
            with mock.patch.object(takeover, "_inspect", return_value={"Image": "sha256:x", "Config": {}}):
                rec = takeover.make_record(d, {"containers": fake_found()[:1], "copies": [], "install": "full"}, "s", tag=lambda *a: None)
            with open(os.path.join(d, "stack", "compose.yaml"), "w") as f:
                f.write("after")
            stack.save_keep(d, {"jellyfin": {"devices": ["/dev/dri"]}})
            takeover._restore_files(d, rec)
            with open(os.path.join(d, "stack", "compose.yaml")) as f:
                self.assertEqual(f.read(), "before")
            self.assertFalse(os.path.exists(os.path.join(d, "stack", stack.KEEP_FILE)))
            self.assertIsNone(takeover.read_record(d))  # nothing to roll back after a failure


if __name__ == "__main__":
    unittest.main()


class AfterTakeoverTest(unittest.TestCase):
    """The replaced apps leave the dashboard, including entries from before Starboard marked them; Reelix's stay."""

    def test_old_entries_are_found_by_type_or_name_and_reelix_stays(self):
        from starboard import server
        services = [{"id": 1, "name": "Radarr", "type": "radarr"}, {"id": 2, "name": "Seerr", "type": "link"},
                    {"id": 3, "name": "Readarr", "type": "readarr"}, {"id": 4, "name": "Reelix films", "type": "radarr", "icon": "reelix"},
                    {"id": 5, "name": "Jellyfin", "type": "jellyfin"}]
        app = mock.Mock()
        app.config.data = {"services": services}
        app.config.remove_service.side_effect = lambda i: services.remove(next(s for s in services if s["id"] == i))
        p = {"choice": {"apps": ["jellyfin"]}, "take": [{"key": "jellyfin"}],
             "replace": [{"key": "radarr", "name": "radarr", "app": "Radarr"}, {"key": "seerr", "name": "seerr", "app": "Seerr"},
                         {"key": "bookshelf", "name": "readarr", "app": "Bookshelf"}]}
        with mock.patch.object(server, "adopt_started_apps"), mock.patch.object(server.services, "forget"), \
                mock.patch.object(server.logs, "event"), mock.patch.object(server.stack, "reelix_url", return_value=None):
            notes = server.after_takeover(app, "pw", p, None)(True)
        self.assertEqual([s["name"] for s in services], ["Reelix films", "Jellyfin"])
        self.assertEqual(len([n for n in notes if n.startswith("Took")]), 3)
