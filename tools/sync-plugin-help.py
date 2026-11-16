#!/usr/bin/env python3
"""Mirrors the plug-ins help (DASH-426) from the starboard-plugins repository into Starboard's help centre, so the
Plug-ins area here has the same eight pages for every plug-in in the collection as
https://themightytrex.github.io/starboard-plugins/help/ (owner, 14 November 2026: "this should also be mirrored on
the starboard plugin help center section"). The pages are written there; never change the copies here.

    python3 tools/sync-plugin-help.py <starboard-plugins checkout>          # writes docs/help/plugins/
    python3 tools/sync-plugin-help.py <starboard-plugins checkout> --check  # says whether the copy is out of date

It copies catalogue.json, each plug-in's README.md (its Overview) and its seven pages, with their pictures (from
help/images/<id>/ to docs/help/images/plugins/<id>/), mends their links for this help centre (pages of Starboard's
own help become links between articles; the collection's own articles and the plug-ins' other files go to their
published addresses), adds the download rights footer, and copies the plug-in groups from the collection's
help-centre.json into Starboard's.
"""
import importlib.util
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HELP = ROOT / "docs" / "help"
OUT = HELP / "plugins"
PAGES = ["install", "settings", "dashboard-card", "updates", "accessibility", "problems", "for-developers"]
SB_SITE = "https://themightytrex.github.io/starboard/help/"
PL_SITE = "https://themightytrex.github.io/starboard-plugins/help/"
PL_BLOB = "https://github.com/TheMightyTRex/starboard-plugins/blob/main/"
NOTE = "<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->"

spec = importlib.util.spec_from_file_location("help_footer", pathlib.Path(__file__).with_name("help_footer.py"))
footer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(footer)


def mend(md, src_rel, out_dir):
    """Links in a page from the plug-ins repository (at src_rel there), for its copy in out_dir here."""
    src_dir = pathlib.PurePosixPath(src_rel).parent

    def fix(m):
        text, url = m.group(1), m.group(2)
        path, _, anchor = url.partition("#")
        tail = "#" + anchor if anchor else ""
        if path.startswith(SB_SITE):  # Starboard's own help: a link between articles here
            rel = path[len(SB_SITE):]
            target = HELP / (rel[:-5] + ".md" if rel.endswith(".html") else rel)
            if target.exists():
                return f"[{text}]({pathlib.Path(*['..'] * len(out_dir.relative_to(HELP).parts), target.relative_to(HELP)).as_posix()}{tail})"
            return m.group(0)
        if re.match(r"^[a-z]+:|^#", url):
            return m.group(0)
        resolved = pathlib.PurePosixPath(*_norm(src_dir / path).parts)
        parts = resolved.parts
        if len(parts) == 2 and parts[1] == "README.md":  # another plug-in's Overview
            return f"[{text}](../{parts[0]}/README.md{tail})"
        if len(parts) == 4 and parts[:2] == ("help", "plugins") and parts[3][:-3] in PAGES:  # a plug-in's own page
            return f"[{text}](../{parts[2]}/{parts[3]}{tail})"
        if parts and parts[0] == "help" and resolved.suffix == ".md":  # the collection's own articles
            return f"[{text}]({PL_SITE}{pathlib.PurePosixPath(*parts[1:]).with_suffix('.html').as_posix()}{tail})"
        return f"[{text}]({PL_BLOB}{resolved.as_posix()}{tail})"  # the plug-ins' other files

    def picture(m):
        alt, url = m.group(1), m.group(2)
        if re.match(r"^[a-z]+:", url):
            return m.group(0)
        parts = _norm(src_dir / url).parts
        if len(parts) > 2 and parts[:2] == ("help", "images"):  # a help picture: copied to images/plugins/ here
            up = [".."] * len(out_dir.relative_to(HELP).parts)
            return f"![{alt}]({pathlib.PurePosixPath(*up, 'images', 'plugins', *parts[2:]).as_posix()})"
        return m.group(0)

    md = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", picture, md)
    return re.sub(r"(?<!!)\[([^\]]+)\]\(([^)\s]+)\)", fix, md)


def _norm(p):
    out = []
    for part in p.parts:
        if part == "..":
            out.pop()
        elif part != ".":
            out.append(part)
    return pathlib.PurePosixPath(*out)


def page(md, src_rel, out_dir):
    md = mend(md, src_rel, out_dir)
    lines = md.splitlines()
    md = "\n".join(lines[:1] + [NOTE] + lines[1:]) + "\n"
    return footer.with_footer(md)


def wanted(src):
    """{path here: text} for every file of the mirror."""
    out = {}
    cat = json.loads((src / "catalogue.json").read_text(encoding="utf-8"))
    out[OUT / "catalogue.json"] = json.dumps(cat, indent=1, ensure_ascii=False) + "\n"
    for p in cat["plugins"]:
        pid = p["id"]
        d = OUT / pid
        out[d / "README.md"] = page((src / pid / "README.md").read_text(encoding="utf-8"), f"{pid}/README.md", d)
        for key in PAGES:
            rel = f"help/plugins/{pid}/{key}.md"
            out[d / f"{key}.md"] = page((src / rel).read_text(encoding="utf-8"), rel, d)
    return out


def pictures(src):
    """{path here: bytes} for the collection's help pictures (help/images/<id>/), mirrored under images/plugins/."""
    base = src / "help" / "images"
    out = {}
    for p in sorted(base.rglob("*")) if base.exists() else []:
        if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif") and len(p.relative_to(base).parts) > 1:
            out[HELP / "images" / "plugins" / p.relative_to(base)] = p.read_bytes()
    return out


def config(src):
    """Starboard's help-centre.json with the collection's plug-in groups, as plug-in mode reads them."""
    mine = json.loads((ROOT / "help-centre.json").read_text(encoding="utf-8"))
    theirs = json.loads((src / "help-centre.json").read_text(encoding="utf-8"))["plugins"]
    mine["plugins"] = {"catalogue": "docs/help/plugins/catalogue.json", "overview": "docs/help/plugins/{id}/README.md",
                       "pages": "docs/help/plugins/{id}/{page}.md", "groups": theirs["groups"], "details": theirs.get("details", {})}
    return json.dumps(mine, indent=2, ensure_ascii=False) + "\n"


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = pathlib.Path(sys.argv[1]).resolve()
    files = wanted(src)
    files[ROOT / "help-centre.json"] = config(src)
    images = pictures(src)
    stale = [p for p, text in files.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
    stale += [p for p, data in images.items() if not p.exists() or p.read_bytes() != data]
    pics = HELP / "images" / "plugins"
    extra = [p for p in OUT.rglob("*") if p.is_file() and p not in files]
    extra += [p for p in pics.rglob("*") if p.is_file() and p not in images] if pics.exists() else []
    if "--check" in sys.argv:
        for p in stale + extra:
            print(f"out of date: {p.relative_to(ROOT)}")
        print("The plug-ins help mirror is " + ("out of date: run tools/sync-plugin-help.py" if stale or extra else "up to date"))
        return 1 if stale or extra else 0
    for p, text in files.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    for p, data in images.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    for p in extra:
        print(f"no longer in the collection, left for you to move: {p.relative_to(ROOT)}")
    print(f"{len(files) + len(images)} files written, {len(stale)} changed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
