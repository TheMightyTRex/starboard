"""A local "from . import library" inside the request handler made "library" local to the whole function and broke
every Library page (12 November 2026). The handler's module names must never be imported again by those names."""
import os
import re
import unittest

SERVER = os.path.join(os.path.dirname(__file__), "..", "starboard", "server.py")


class NoShadow(unittest.TestCase):
    def test_top_level_modules_not_imported_again_in_functions(self):
        src = open(SERVER, encoding="utf-8").read()
        top = set()
        for line in src.splitlines():
            m = re.match(r"^from \. import (.+?)(\s+#.*)?$", line)
            if m:
                top |= {n.strip().split(" as ")[-1] for n in m.group(1).split(",")}
        for n, line in enumerate(src.splitlines(), 1):
            m = re.match(r"^\s+from \. import (.+?)(\s+#.*)?$", line)
            if not m:
                continue
            names = {x.strip() for x in m.group(1).split(",") if " as " not in x}
            self.assertFalse(names & top, f"server.py line {n} imports {names & top} again inside a function")


if __name__ == "__main__":
    unittest.main()
