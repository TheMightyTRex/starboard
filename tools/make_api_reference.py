#!/usr/bin/env python3
"""Writes docs/help/developers/api-reference.md from starboard/openapi.json (DASH-150, DASH-275; rule D3 of the
developer best practice: the reference is built from the API's own description, never written by hand).

For each path and method it gives what it does, the scope a key needs, its parameters, the answer's shape in brief,
its errors, and an example with curl and with Python's standard library. How long an answer stays fresh is not in
the description, so it is read from the route table in starboard/api_v1.py (the same table the server answers from).
Standard library only. Run it after tools/make_openapi.py, and commit both files. With --check it writes nothing and
fails when the page is out of date (DASH-281).

    python3 tools/make_api_reference.py
    python3 tools/make_api_reference.py --check
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEC = ROOT / "starboard" / "openapi.json"
OUT = ROOT / "docs" / "help" / "developers" / "api-reference.md"
ERRORS = "../../api/errors.md"
BASE = "http://192.168.1.20:8095"
# What each problem status can be, by its code in docs/api/errors.md.
CODES = {400: ["bad_request"], 401: ["key_needed"], 404: ["not_found"], 405: ["method_not_allowed"],
         429: ["too_many_attempts", "rate_limited"]}
SCOPE_WORDS = {"apps": "your apps and their status", "downloads": "what is downloading",
               "media": "your library and what is playing", "system": "processor, memory and disks"}


def route_table():
    """[(compiled pattern, scope or None, seconds fresh)] from starboard/api_v1.py's read routes."""
    sys.path.insert(0, str(ROOT))
    from starboard import api_v1
    return [(re.compile(pattern), scope, int(fresh)) for pattern, scope, fresh, *_ in api_v1.routes()]


def route_for(path, table):
    """The route that answers a described path, trying it with a made-up value in each {name}."""
    sample = re.sub(r"\{[^}]+\}", "example", path)
    for pattern, scope, fresh in table:
        if pattern.match(sample):
            return scope, fresh
    return None


def resolve(spec, ref):
    node = spec
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node


def ref_name(ref):
    return ref.rsplit("/", 1)[-1]


def kind(spec, schema, used):
    """A schema in a few words, such as 'a list of App' or 'text or null'. Named objects are added to `used`."""
    if not schema:
        return "anything"
    if "$ref" in schema:
        name = ref_name(schema["$ref"])
        used.add(name)
        return f"[{name}](#{name.lower()})"
    if "enum" in schema:
        return "one of " + ", ".join(f"`{v}`" for v in schema["enum"])
    t = schema.get("type")
    if isinstance(t, list):
        return " or ".join(kind(spec, {**schema, "type": x}, used) for x in t)
    if t == "array":
        items = schema.get("items") or {}
        if "enum" in items:
            return "a list from " + ", ".join(f"`{v}`" for v in items["enum"])
        return "a list of " + kind(spec, items, used)
    if t == "object":
        if schema.get("properties"):
            return "an object"
        return "an object (its fields vary)"
    if t == "null":
        return "null"
    fmt = schema.get("format")
    words = {"string": "text", "integer": "a whole number", "number": "a number", "boolean": "true or false"}.get(t, t or "anything")
    return f"{words} ({fmt})" if fmt else words


def fields(spec, schema, used):
    """Markdown rows: each field of an object, its kind, and whether it is always there."""
    required = set(schema.get("required") or [])
    rows = ["| Field | What it is | Always there |", "|---|---|---|"]
    for name, sub in (schema.get("properties") or {}).items():
        rows.append(f"| `{name}` | {kind(spec, sub, used)} | {'yes' if name in required else 'no'} |")
    return rows


def parameter_rows(spec, params):
    rows = ["| Name | In | What it is |", "|---|---|---|"]
    for p in params:
        p = resolve(spec, p["$ref"]) if "$ref" in p else p
        sch = p.get("schema") or {}
        limits = []
        if "minimum" in sch and "maximum" in sch:
            limits.append(f"{sch['minimum']} to {sch['maximum']}")
        if "default" in sch:
            limits.append(f"{sch['default']} if left out")
        desc = (p.get("description") or "").rstrip(".")
        bits = [b for b in [desc, ", ".join(limits)] if b]
        req = " Required." if p.get("required") else ""
        rows.append(f"| `{p['name']}` | {p['in']} | {'; '.join(bits) or kind(spec, sch, set())}.{req} |")
    return rows


def example_path(path):
    return re.sub(r"\{[^}]+\}", "sonarr", path)


def operation(spec, path, method, op, table, used):
    lines = [f"### {method.upper()} {path}", "", f"{op.get('summary', '').rstrip('.')}."]
    if op.get("description"):
        lines += ["", op["description"]]
    lines.append("")
    open_route = op.get("security") == []
    found = route_for(path, table)
    if open_route:
        lines.append("- **Key:** none needed.")
    else:
        scope = op.get("x-scope") or (found[0] if found else None)
        if scope:
            lines.append(f"- **Key:** any read key whose scopes are empty or include `{scope}` ({SCOPE_WORDS.get(scope, scope)}). "
                         f"A key without it gets `404 not_found`.")
        else:
            lines.append("- **Key:** any read key.")
    if found and not open_route:
        lines.append(f"- **Fresh for:** {found[1]} seconds (`Cache-Control: private, max-age={found[1]}`).")
    lines.append(f"- **Operation id:** `{op.get('operationId', '')}`.")
    params = op.get("parameters") or []
    if params:
        lines += ["", "Parameters:", ""] + parameter_rows(spec, params)
    responses = op.get("responses") or {}
    good = responses.get("200") or {}
    schema = ((good.get("content") or {}).get("application/json") or {}).get("schema") or {}
    lines += ["", "The answer:", ""]
    said = (good.get("description") or "").rstrip(".")
    if schema.get("properties"):
        lines += fields(spec, schema, used)
    elif "$ref" not in schema and said and said != "It worked":
        lines.append(f"- {said}.")
    else:
        lines.append(f"- {kind(spec, schema, used)}.")
    errs, also = [], []
    for code in sorted(responses, key=lambda c: int(c) if c.isdigit() else 0):
        if code == "200":
            continue
        r = responses[code]
        if code.isdigit() and int(code) < 400:
            also.append(f"- **{code}:** {(r.get('description') or '').rstrip('.')}.")
        elif "$ref" in r and int(code) in CODES:
            errs.append(f"- **{code}:** " + ", ".join(f"[`{c}`]({ERRORS}#{c})" for c in CODES[int(code)]) + ".")
        else:
            errs.append(f"- **{code}:** {(r.get('description') or '').rstrip('.')}.")
    if any(p.get("$ref", "").endswith(("/limit", "/cursor")) for p in params) and "400" not in responses:
        errs.insert(0, f"- **400:** [`bad_request`]({ERRORS}#bad_request), when `limit` or `cursor` is wrong.")
    if also:
        lines += ["", "Other answers:", ""] + also
    if errs:
        lines += ["", "Errors:", ""] + errs
    url = BASE + example_path(path)
    auth = "" if open_route else ' -H "Authorization: Bearer $STARBOARD_KEY"'
    lines += ["", "Example:", "", "```bash", f'curl -s{auth} "{url}"', "```", "", "```python",
              "import json, os, urllib.request", ""]
    if open_route:
        lines.append(f'req = urllib.request.Request("{url}")')
    else:
        lines.append(f'req = urllib.request.Request("{url}",')
        lines.append('                             headers={"Authorization": "Bearer " + os.environ["STARBOARD_KEY"]})')
    lines += ["with urllib.request.urlopen(req, timeout=10) as r:", "    print(json.load(r))", "```", ""]
    return lines


def build():
    spec = json.loads(SPEC.read_text())
    table = route_table()
    info = spec.get("info") or {}
    used = set()
    body = []
    by_tag = {}
    for path, methods in spec.get("paths", {}).items():
        for method, op in methods.items():
            tag = (op.get("tags") or ["Other"])[0]
            by_tag.setdefault(tag, []).append((path, method, op))
    for tag, ops in by_tag.items():
        body += [f"## {tag}", ""]
        for path, method, op in ops:
            body += operation(spec, path, method, op, table, used)
    objects = ["## Objects", "", "The named objects the answers use.", ""]
    schemas = (spec.get("components") or {}).get("schemas") or {}
    done = set()
    while used - done:
        name = sorted(used - done)[0]
        done.add(name)
        if name not in schemas:
            continue
        objects += [f"### {name}", ""] + fields(spec, schemas[name], used) + [""]
    head = [
        "[Help centre](../README.md) · Developers",
        "",
        "# API reference",
        "",
        "<!-- Generated by tools/make_api_reference.py from starboard/openapi.json. Do not change it by hand: change the",
        "     description (tools/make_openapi.py), then run both tools again. -->",
        "",
        f"This page is made from Starboard's API description, `starboard/openapi.json` (version {info.get('version', '')}), "
        "by `tools/make_api_reference.py`. It lists every address in version 1 of the API.",
        "",
        "- Every address starts with `/api/v1` on your Starboard, such as `http://192.168.1.20:8095/api/v1/apps`.",
        "- The API only reads. Every request except the description itself needs a key, sent as "
        "`Authorization: Bearer` and the key. Read [Authentication and keys](api-authentication.md).",
        "- The examples read the key from `STARBOARD_KEY`. Set it first, such as `export STARBOARD_KEY=sb_read_...`.",
        "- Lists take `limit` and `cursor`, and every answer has an `ETag`. Read [API quickstart](api-quickstart.md).",
        f"- Errors are problem details (RFC 9457), each explained in the [list of API errors]({ERRORS}).",
        "- The same description is on your Starboard at `/api/v1/openapi.json`, for tools that read OpenAPI.",
        "",
    ]
    tail = [
        "## Find out more",
        "",
        "- [API quickstart](api-quickstart.md)",
        "- [Authentication and keys](api-authentication.md)",
        "- [API changelog](api-changelog.md)",
        f"- [List of API errors]({ERRORS})",
        "- [Make an API key and use Starboard's API](../topics/use-starboards-api.md)",
        "",
    ]
    return "\n".join(head + body + objects + tail)


def main():
    text = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # Keep the download rights footer that tools/help_footer.py adds, so running this tool again changes nothing else.
    old = OUT.read_text() if OUT.exists() else ""
    footer = re.search(r"<!-- footer: download rights -->.*?<!-- /footer -->\n?", old, flags=re.S)
    new = text + ("\n" + footer.group(0) if footer else "")
    if "--check" in sys.argv:
        if new != old:
            sys.exit(f"{OUT.relative_to(ROOT)} is out of date: run python3 tools/make_api_reference.py and commit it")
        print(f"{OUT.relative_to(ROOT)} is up to date")
        return
    OUT.write_text(new)
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
