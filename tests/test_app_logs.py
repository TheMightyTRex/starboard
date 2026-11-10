"""App logs on System, Logs (DASH-223): only apps on this computer, cleaned like Starboard's own log."""
import unittest

from starboard import app_logs


def frame(text):
    data = text.encode()
    return b"\x01\x00\x00\x00" + len(data).to_bytes(4, "big") + data


class FakeDocker:
    def __call__(self, method, path, *a, **k):
        if path.startswith("/containers/json"):
            return [{"Names": ["/reelix"], "State": "running"}, {"Names": ["/starboard-updater-123"], "State": "exited"},
                    {"Names": ["/jellyfin"], "State": "exited"}]
        if path.startswith("/containers/reelix/logs"):
            return frame("2026-11-10T10:00:00Z Started with api_key=made-up-secret-value-1234567890\n"
                         "2026-11-10T10:00:01Z \x1b[32mINFO\x1b[0m Connected to http://192.168.1.20:8096\n"
                         "2026-11-10T10:00:02Z Ready on Harbour\n")
        raise AssertionError(path)


class AppLogsTest(unittest.TestCase):
    def test_only_apps_on_this_computer_without_starboards_helpers(self):
        out = app_logs.listing(FakeDocker())
        self.assertEqual([a["name"] for a in out["apps"]], ["jellyfin", "reelix"])

    def test_lines_are_cleaned_and_can_be_found(self):
        out = app_logs.lines("reelix", 100, docker=FakeDocker(), words=["Harbour"])
        text = "\n".join(out["lines"])
        for gone in ("made-up-secret-value", "192.168.1.20", "Harbour", "\x1b["):
            self.assertNotIn(gone, text)
        self.assertEqual(len(app_logs.lines("reelix", 100, "ready", docker=FakeDocker(), words=())["lines"]), 1)

    def test_an_unknown_name_is_refused(self):
        with self.assertRaises(LookupError):
            app_logs.lines("../../etc", docker=FakeDocker())


if __name__ == "__main__":
    unittest.main()
