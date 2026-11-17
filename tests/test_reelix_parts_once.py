"""System, Apps, Updates lists Reelix once: its films, series, books and music connections run in Reelix's own
container, so they are not rows with "No container found" (owner, 17 November 2026)."""
import unittest
from unittest import mock

from starboard import containers


def box(name):
    return {"name": name, "image": f"ghcr.io/example/{name}:latest", "state": "running", "status": "Up", "version": "1",
            "created": 0, "service": name, "project": "stack", "folder": "/x", "files": ["compose.yaml"]}


SERVICES = [
    {"id": "reelix", "name": "Reelix", "icon": "reelix", "type": "link", "container": ""},
    {"id": "reelix-films", "name": "Reelix films", "icon": "reelix", "type": "radarr", "container": ""},
    {"id": "reelix-series", "name": "Reelix series", "icon": "reelix", "type": "sonarr", "container": ""},
    {"id": "jellyfin", "name": "Jellyfin", "icon": "jellyfin", "type": "jellyfin", "container": ""},
    {"id": "elsewhere", "name": "On another computer", "icon": "radarr", "type": "radarr", "container": ""},
]


class ReelixPartsOnce(unittest.TestCase):
    def rows(self, found):
        with mock.patch.object(containers, "containers", return_value=found):
            return {r["id"]: r for r in containers.apps(SERVICES)["items"]}

    def test_reelix_is_one_row_and_its_parts_are_left_out(self):
        rows = self.rows([box("reelix"), box("jellyfin")])
        self.assertEqual(rows["reelix"]["container"]["name"], "reelix")
        self.assertNotIn("reelix-films", rows)
        self.assertNotIn("reelix-series", rows)

    def test_other_apps_with_no_container_still_say_so(self):
        rows = self.rows([box("reelix"), box("jellyfin")])
        self.assertIsNone(rows["elsewhere"]["container"])

    def test_a_part_given_its_own_container_is_kept(self):
        services = SERVICES + [{"id": "reelix-music", "name": "Reelix music", "icon": "reelix", "container": "reelix"}]
        with mock.patch.object(containers, "containers", return_value=[box("reelix")]):
            ids = [r["id"] for r in containers.apps(services)["items"]]
        self.assertIn("reelix-music", ids)


if __name__ == "__main__":
    unittest.main()
