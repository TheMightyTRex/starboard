"""tools/minify.py (DASH-573): comments, indentation and blank lines go; strings, templates, regular expressions and
line breaks stay, so a script does what it did. Run: python3 -m unittest tests.test_minify"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import minify  # noqa: E402


class Js(unittest.TestCase):
    def test_comments_indentation_and_blank_lines_go(self):
        src = "// header\nfunction f(a) {\n    // why\n    const x = a; // trailing   \n\n\n    /* block\n       over lines */\n    return x;\n}\n"
        self.assertEqual(minify.minify_js(src), "function f(a) {\nconst x = a;\nreturn x;\n}\n")

    def test_a_block_comment_between_words_keeps_them_apart(self):
        self.assertEqual(minify.minify_js("a/* c */b\n"), "a b\n")

    def test_the_lines_stay_lines(self):
        # no semicolons: where a statement ends depends on the line breaks, so none may be joined
        src = "let a = 1\nlet b = 2\n(function () {})()\n"
        self.assertEqual(minify.minify_js(src), src)

    def test_notices_stay(self):
        self.assertEqual(minify.minify_js("/*! keep me */\nx\n"), "/*! keep me */\nx\n")

    def test_strings_are_not_touched(self):
        src = "const u = \"http://example.test/a\"; const s = 'it\\'s // not a comment'; const t = \"/* no */\";\n"
        self.assertEqual(minify.minify_js(src), src)

    def test_template_literals_keep_their_lines_and_spaces(self):
        src = "const h = `\n    <p>// not a comment</p>\n      ${items.map(i => `<li>${i /* c */}</li>`).join(\"\")}\n`;\nnext();\n"
        out = minify.minify_js(src)
        self.assertIn("`\n    <p>// not a comment</p>\n      ${items.map(i => `<li>${i  }</li>`).join(\"\")}\n`;", out.replace("${i }", "${i  }"))
        self.assertTrue(out.endswith("`;\nnext();\n"))

    def test_regular_expressions_are_not_comments_or_quotes(self):
        src = "const a = /\\/\\/ [\"'] /g;\nconst b = x.replace(/'/g, \"\");\nif (/^\\s*\\/\\*/.test(s)) go();\nconst c = [/\"/, /[/]/];\n"
        self.assertEqual(minify.minify_js(src), src)

    def test_division_is_not_a_regular_expression(self):
        src = "const r = a / b; const q = (a + b) / 2; const t = arr[0] / 3; // note\nconst s = \"x\";\n"
        self.assertEqual(minify.minify_js(src), "const r = a / b; const q = (a + b) / 2; const t = arr[0] / 3;\nconst s = \"x\";\n")

    def test_regex_after_return_and_a_comment_after_it(self):
        self.assertEqual(minify.minify_js("function f(s) {\n  return /['\"]/.test(s); // yes\n}\n"), "function f(s) {\nreturn /['\"]/.test(s);\n}\n")

    def test_it_is_idempotent(self):
        once = minify.minify_js("a = 1; // x\n\n  b = `\n  keep\n`;\n")
        self.assertEqual(minify.minify_js(once), once)


class Css(unittest.TestCase):
    def test_comments_and_indentation_go(self):
        src = "/* title */\n.a {\n  color: red; /* note */\n\n  margin: 0;\n}\n"
        self.assertEqual(minify.minify_css(src), ".a {\ncolor: red;\n\nmargin: 0;\n}\n".replace("\n\n", "\n"))

    def test_strings_stay(self):
        src = ".a::before { content: \"/* not a comment */\"; background: url('a//b.png'); }\n"
        self.assertEqual(minify.minify_css(src), src)


class TheRealFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="sb-minify-")
        cls.web = os.path.join(cls.tmp, "web")
        shutil.copytree(ROOT / "web", cls.web, ignore=shutil.ignore_patterns("images", "fonts", "icons", "*.html"))
        minify.main(cls.web)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def files(self, sub):
        return sorted(f for f in (ROOT / "web" / sub).rglob("*." + sub))

    def test_every_file_is_smaller_and_stable(self):
        for sub, fn in (("js", minify.minify_js), ("css", minify.minify_css)):
            for src in self.files(sub):
                new = pathlib.Path(self.web, src.relative_to(ROOT / "web")).read_text(encoding="utf-8")
                self.assertLessEqual(len(new), len(src.read_text(encoding="utf-8")), src.name)
                self.assertEqual(fn(new), new, f"{src.name} is not stable")

    @unittest.skipUnless(shutil.which("node"), "needs node")
    def test_every_script_still_parses(self):
        for src in self.files("js"):
            p = pathlib.Path(self.web, src.relative_to(ROOT / "web"))
            r = subprocess.run(["node", "--check", str(p)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{src.name}: {r.stderr[:300]}")


if __name__ == "__main__":
    unittest.main()
