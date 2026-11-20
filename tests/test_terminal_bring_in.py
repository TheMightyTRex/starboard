"""Bring in media in the terminal set-up (DASH-455): the same four parts, in the same place and order, with the same
questions as the browser's, and the folder picker as numbered lists with the path at the top. Starboard's API is
answered by the real bring_in and folders code here, against throwaway folders."""
import io
import json
import os
import pathlib
import re
import shutil
import tempfile
import unittest
import urllib.parse
from unittest import mock

from starboard import bring_in as b, folders, terminal_setup as ts
from tests.test_terminal_setup import Answers

ROOT = pathlib.Path(__file__).resolve().parent.parent


class LocalApi:
    """Starboard's own routes for this step, answered in this process."""

    def __init__(self, data):
        self.data, self.calls = data, []

    def call(self, method, path, body=None, timeout=30):
        self.calls.append((method, path, body))
        u = urllib.parse.urlparse(path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        p = u.path
        try:
            if p == "/api/folders/places":
                return {"places": folders.places(self.data, q.get("for", ""))}
            if p == "/api/folders":
                return folders.browse(q.get("path", ""))
            if p == "/api/folders/sizes":
                return {"folders": folders.sizes(q.get("path", ""))}
            if p == "/api/bring-in" and method == "GET":
                return b.public(self.data)
            if p == "/api/bring-in/sources":
                return b.save_sources(self.data, body.get("sources"), body.get("hardlinks"), body.get("media"))
            if p == "/api/bring-in/look":
                return b.look(self.data, body["source"])
            if p == "/api/bring-in/check":
                b.build_plan(self.data)
                b.check_names(type("C", (), {"data": {"services": []}})(), self.data)
                return b.plan_page(self.data, "matched")
            if p == "/api/bring-in/plan":
                return b.plan_page(self.data, q.get("state", "matched"))
            if p == "/api/bring-in/start":
                return {"state": "running"}
        except (ValueError, b.BringInError, LookupError) as e:
            raise ts.Problem(str(e)) from None
        raise AssertionError(f"not answered: {method} {path}")


class TerminalBringIn(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bring-in-term-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = os.path.join(self.tmp, "mnt")
        self.data = os.path.join(self.tmp, "data")
        os.makedirs(os.path.join(self.root, "media"))
        os.makedirs(self.data)
        for rel in ("nas/Films/Harbour.Lights.2019.mkv", "nas/Music/Midnight Garden/First Light/01.flac"):
            p = os.path.join(self.root, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(os.urandom(500))
        for patch in (mock.patch.object(folders, "ROOTS", (self.root,)), mock.patch.object(b, "_in_docker", lambda: False),
                      mock.patch.object(folders, "_in_docker", lambda: False), mock.patch.object(folders, "disk_places", lambda: [])):
            patch.start()
            self.addCleanup(patch.stop)

    def test_the_step_comes_after_storage_in_four_parts_as_in_the_browser(self):
        ids = ts.job_steps({"start": "new"})
        at = ids.index("storage")
        self.assertEqual(ids[at + 1:at + 5], ["bring-sources", "bring-what", "bring-names", "bring-copy"])
        browser = (ROOT / "web/js/bring-in.js").read_text()
        self.assertIn('const BRING_PARTS = ["bring-sources", "bring-what", "bring-names", "bring-copy"];', browser)
        guide = "".join(p.read_text(encoding="utf-8") for p in sorted((ROOT / "web" / "js").glob("settings-*.js")))
        self.assertLess(guide.index('id: "drives"'), guide.index("bringInSteps(T)"))
        self.assertLess(guide.index("bringInSteps(T)"), guide.index('...flow.before().filter((x) => x.id !== "moving")'))
        table = {s["id"]: s for s in json.loads((ROOT / "web/setup-steps.json").read_text())["steps"]}
        for part in ("bring-sources", "bring-what", "bring-names", "bring-copy"):
            self.assertEqual(ts.question(part), table[part]["question"])
        self.assertNotIn("bring-sources", ts.job_steps({"start": "move"}))

    def test_a_whole_run_by_numbers_with_the_picker_as_numbered_lists(self):
        out = io.StringIO()
        # Add a source; This computer; the usual place; nas (after media); Use this folder; Continue; Continue (what);
        # No, copy them; Continue (names); Copy once the apps are running.
        typed = ["1", "1", "1", "3", "1", "1", "1", "1", "1", "1"]
        term = ts.Terminal(out=out, ask=Answers(typed), secret=Answers([]), fancy=False)
        api = LocalApi(self.data)
        state = {"start": "new", "media_dir": os.path.join(self.root, "media")}
        self.assertTrue(ts.step_bring(api, term, state))
        text = out.getvalue()
        for part in ("bring-sources", "bring-what", "bring-names", "bring-copy"):
            self.assertIn(ts.question(part), text)
        self.assertIn("Where you are: This computer", text)
        self.assertIn("Use this folder", text)
        self.assertRegex(text, r"nas: [0-9.]+ (KB|bytes), 1 film, 1 album")  # each folder with its size and what is in it
        self.assertEqual(b.settings(self.data)["sources"][0]["path"], os.path.join(self.root, "nas"))
        self.assertIn(("POST", "/api/bring-in/start", {}), api.calls)
        self.assertFalse(b.settings(self.data)["hardlinks"])  # off unless chosen

    def test_skip_this_step_leaves_it_for_later(self):
        out = io.StringIO()
        term = ts.Terminal(out=out, ask=Answers(["2"]), secret=Answers([]), fancy=False)
        state = {"start": "new"}
        self.assertTrue(ts.step_bring(LocalApi(self.data), term, state))
        self.assertEqual(state["bring"], "skipped")
        self.assertIn("Library, Bring in media", out.getvalue())

    def test_the_words_follow_the_content_rules(self):
        text = (ROOT / "starboard/terminal_setup.py").read_text() + (ROOT / "web/js/bring-in.js").read_text() + \
            (ROOT / "starboard/bring_in.py").read_text() + (ROOT / "docs/help/topics/bring-in-media-you-already-have.md").read_text()
        self.assertNotIn("—", text)
        self.assertIsNone(re.search(r"\b(can't|won't|don't|doesn't|isn't|it's|that's|you're)\b", text))


if __name__ == "__main__":
    unittest.main()
