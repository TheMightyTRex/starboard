#!/usr/bin/env python3
"""Takes the comments, the indentation and the blank lines out of the page scripts and style sheets (DASH-573).

    python3 tools/minify.py <web folder>        rewrites every .js and .css under js/ and css/ in place

It runs once when the image is built (see the Dockerfile), never on a running server and never on the files in the
repository: the repository keeps the readable sources. Only things that cannot change what a file does are removed:

- comments (but not /*! ... */ notices);
- the spaces and tabs at the start and end of each line, and empty lines;
- nothing inside a string, a template literal or a regular expression, and no line is joined to another, so where a
  statement ends (automatic semicolons) stays as written.

Names are not shortened and code is not rewritten, so what the browser reports still reads like the source. About a
third of the bytes of common.js and half of components.css go; about 35 KB less over the wire (gzip) on each page's
first visit.
"""
import os
import sys

# After one of these words a "/" starts a regular expression; after a name, a number or a closing bracket it divides.
_REGEX_AFTER_WORD = {"return", "typeof", "instanceof", "in", "of", "new", "delete", "void", "throw", "case", "do", "else", "yield", "await"}
_REGEX_AFTER_CHAR = set("(,=:[!&|?{};+-*%<>~^")


def _tail_word(out):
    i = len(out)
    while i and (out[i - 1].isalnum() or out[i - 1] in "_$"):
        i -= 1
    return "".join(out[i:])


def _regex_allowed(out):
    j = len(out)
    while j and out[j - 1] in " \t\n":
        j -= 1
    if not j:
        return True
    c = out[j - 1]
    if c in _REGEX_AFTER_CHAR:
        return True
    return _tail_word(out[:j]) in _REGEX_AFTER_WORD


def _copy_quoted(s, i, out, q):
    out.append(s[i])
    i += 1
    n = len(s)
    while i < n:
        c = s[i]
        out.append(c)
        i += 1
        if c == "\\" and i < n:
            out.append(s[i])
            i += 1
        elif c == q or c == "\n":
            break
    return i


def _copy_template(s, i, out):
    """A template literal, copied exactly (its line breaks and spaces are part of the text); code inside ${ } is scanned."""
    out.append("`")
    i += 1
    n = len(s)
    while i < n:
        c = s[i]
        if c == "\\" and i + 1 < n:
            out.append(s[i:i + 2])
            i += 2
        elif c == "`":
            out.append(c)
            return i + 1
        elif c == "$" and s[i + 1:i + 2] == "{":
            out.append("${")
            i = _scan(s, i + 2, out, in_braces=True)
        else:
            out.append(c)
            i += 1
    return i


def _copy_regex(s, i, out):
    """A regular expression from its opening slash, or None when the line ends first (then it was a division after all)."""
    j, n, in_class = i + 1, len(s), False
    while j < n and s[j] != "\n":
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == "[":
            in_class = True
        elif c == "]":
            in_class = False
        elif c == "/" and not in_class:
            out.append(s[i:j + 1])
            return j + 1
        j += 1
    return None


def _newline(out):
    while out and out[-1] in (" ", "\t"):
        out.pop()
    if out and out[-1] != "\n":
        out.append("\n")


def _scan(s, i, out, in_braces=False):
    n, depth = len(s), 0
    while i < n:
        c = s[i]
        if c in "\"'":
            i = _copy_quoted(s, i, out, c)
        elif c == "`":
            i = _copy_template(s, i, out)
        elif c == "/" and s[i + 1:i + 2] == "/":
            while i < n and s[i] != "\n":
                i += 1
        elif c == "/" and s[i + 1:i + 2] == "*":
            end = s.find("*/", i + 2)
            end = n if end < 0 else end + 2
            if s[i + 2:i + 3] == "!":
                out.append(s[i:end])
            elif "\n" in s[i:end]:
                _newline(out)
            else:
                out.append(" ")
            i = end
        elif c == "/":
            took = _copy_regex(s, i, out) if _regex_allowed(out) else None
            if took is None:
                out.append(c)
                i += 1
            else:
                i = took
        elif c == "\n":
            _newline(out)
            i += 1
            while i < n and s[i] in " \t\r":
                i += 1
        elif c == "\r":
            i += 1
        else:
            if in_braces:
                if c == "{":
                    depth += 1
                elif c == "}":
                    if depth == 0:
                        out.append(c)
                        return i + 1
                    depth -= 1
            out.append(c)
            i += 1
    return i


def minify_js(text):
    out = []
    _scan(text.lstrip(" \t\r\n"), 0, out)
    return "".join(out).rstrip() + "\n"


def minify_css(text):
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c in "\"'":
            i = _copy_quoted(text, i, out, c)
        elif c == "/" and text[i + 1:i + 2] == "*":
            end = text.find("*/", i + 2)
            end = n if end < 0 else end + 2
            if text[i + 2:i + 3] == "!":
                out.append(text[i:end])
            else:
                out.append(" ")
            i = end
        elif c == "\n":
            _newline(out)
            i += 1
            while i < n and text[i] in " \t\r":
                i += 1
        elif c == "\r":
            i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out).strip() + "\n"


def main(folder):
    total = [0, 0]
    for sub, fn in (("js", minify_js), ("css", minify_css)):
        for root, _, files in os.walk(os.path.join(folder, sub)):
            for name in files:
                if not name.endswith("." + sub):
                    continue
                path = os.path.join(root, name)
                with open(path, encoding="utf-8") as f:
                    before = f.read()
                after = fn(before)
                with open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(after)
                total[0] += len(before.encode())
                total[1] += len(after.encode())
    print(f"minified: {total[0]} bytes became {total[1]}")


if __name__ == "__main__":
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        sys.exit("usage: python3 tools/minify.py <web folder>")
    main(sys.argv[1])
