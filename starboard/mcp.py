"""AI assistants over MCP, the Model Context Protocol (DASH-464, API 1.7.0): POST /api/v1/mcp.

The Streamable HTTP transport, in the standard library: JSON-RPC 2.0 over one POST address, answered as one JSON
object (never a stream, so nothing stays open). It takes initialize, ping, tools/list and tools/call, and
notifications such as notifications/initialized, which it accepts with 202. No session id is given: each request
stands on its own, so a restart loses nothing.

Rules:
- Off until the owner turns it on in Settings, Security, API keys (mcp_enabled, never by key). While off, the
  address answers 403 mcp_off to a working key, so nothing is shared.
- A Starboard API key with the read right, as Authorization: Bearer (api_v1.handle checks the key, counts refused
  keys towards the lockout, writes them to the audit log and takes a token from the key's bucket before this module
  is called). A manage key is refused: an assistant gets a key that only reads.
- Each tool reads through the same route function as /api/v1, with the same scope, so the API and the tools always
  agree: a key sees only the tools its scopes cover, and a tool it may not use is unknown to it.
- Read only. Every tool says readOnlyHint, and none changes anything. Changes, each approved in Starboard's page
  first, are left for a later version.
- Each tools/call writes a line to the audit log: the key, the tool and whether it worked, never the arguments.
- An Origin header from a page on another site is refused (the transport's rule against DNS rebinding), on top of
  the Host check every request already has.
"""
import json
import re
import urllib.parse

from . import api_v1

PATH = "/api/v1/mcp"
PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26")  # newest first; an older client gets the newest we have
MAX_BODY = 64 * 1024
INSTRUCTIONS = ("Starboard runs a home media server. These tools read it: the Library, what is new, what is coming up, "
                "what is playing, downloads, requests, the apps' health and disk space. They change nothing. Answers come "
                "from the apps Starboard manages and hold no passwords, keys or private addresses.")

# JSON-RPC 2.0 error codes
PARSE_ERROR, INVALID_REQUEST, METHOD_NOT_FOUND, INVALID_PARAMS, INTERNAL_ERROR = -32700, -32600, -32601, -32602, -32603

LIMIT = {"type": "integer", "minimum": 1, "maximum": 50, "default": 20, "description": "How many to give back, from 1 to 50."}
ANY = {"type": "object", "additionalProperties": True}
ROWS = {"type": "array", "items": ANY}
MORE = {"type": "boolean", "description": "true when there are more than were given back."}


def _obj(props, required=()):
    return {"type": "object", "properties": props, "required": list(required), "additionalProperties": False}


def _out(props, required):
    return {"type": "object", "properties": props, "required": list(required)}


# The tools ------------------------------------------------------------------------------------------------------------
# Each reads one or two /api/v1 routes through api_v1.routes(), with the key's scopes checked again for each route.

def _route(h, k, path, query=None):
    """The body /api/v1 would answer for `path`, from the same route function, or LookupError when the key's scopes
    do not cover it."""
    for pattern, scope, _fresh, fn in api_v1.routes():
        m = re.match(pattern, path)
        if m and fn:
            if not api_v1._scoped(k, scope):
                raise LookupError("Nothing here for this key")
            return fn(h, m, {n: [str(v)] for n, v in (query or {}).items()})
    raise LookupError("No such route")


def _listing(body, *extra):
    return {"items": body.get("items") or [], "more": bool(body.get("next_cursor")), **{n: body.get(n) for n in extra}}


def search_library(h, k, a):
    body = _route(h, k, "/api/v1/library/search", {"q": a["query"], "limit": a.get("limit", 20)})
    return _listing(body)


def recently_added(h, k, a):
    return _listing(_route(h, k, "/api/v1/recent", {"limit": a.get("limit", 20)}))


def coming_up(h, k, a):
    query = {"limit": a.get("limit", 20)}
    if a.get("month"):
        query["month"] = a["month"]
    body = _route(h, k, "/api/v1/calendar", query)
    return {**_listing(body), "errors": body.get("errors") or []}


def now_playing(h, k, a):
    body = _route(h, k, "/api/v1/playing")
    return {"configured": bool(body.get("configured")), "items": body.get("items") or []}


def downloads(h, k, a):
    body = _route(h, k, "/api/v1/downloads", {"limit": a.get("limit", 20)})
    return {**_listing(body), "errors": body.get("errors") or []}


def download_problems(h, k, a):
    body = _route(h, k, "/api/v1/downloads/issues")
    return {"count": int(body.get("count") or 0), "items": (body.get("items") or [])[:a.get("limit", 20)], "errors": body.get("errors") or []}


def requests(h, k, a):
    body = _route(h, k, "/api/v1/requests", {"pending": "true" if a.get("pending_only") else "false", "limit": a.get("limit", 20)})
    return {**_listing(body), "configured": bool(body.get("configured")), "pending": int(body.get("pending") or 0)}


def app_health(h, k, a):
    status = _route(h, k, "/api/v1/status", {"limit": 200})
    health = _route(h, k, "/api/v1/health", {"limit": 200})
    return {"apps": status.get("items") or [], "problems": health.get("items") or [], "errors": health.get("errors") or []}


def disk_space(h, k, a):
    return {"disks": _route(h, k, "/api/v1/system").get("disks") or []}


READ_ONLY = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}

# (name, title, description, scope, input schema, output schema, function)
TOOLS = [
    ("search_library", "Search the Library",
     "Searches the films, series, music, books and audiobooks in the Library by title or name. Needs Reelix.",
     "library", _obj({"query": {"type": "string", "minLength": 1, "maxLength": 120, "description": "What to search for, such as a title."},
                      "limit": LIMIT}, ["query"]),
     _out({"items": ROWS, "more": MORE}, ["items", "more"]), search_library),
    ("recently_added", "Recently added",
     "Films, episodes, music and books added in the last 7 days, newest first.",
     "media", _obj({"limit": LIMIT}), _out({"items": ROWS, "more": MORE}, ["items", "more"]), recently_added),
    ("coming_up", "Coming up",
     "Films, episodes and books due out soon, from the calendar on the Coming up page. Give month for a whole month.",
     "media", _obj({"month": {"type": "string", "pattern": r"^\d{4}-\d{2}$", "description": "A month, such as 2026-11. Leave it out for the next days."},
                    "limit": LIMIT}),
     _out({"items": ROWS, "more": MORE, "errors": ROWS}, ["items", "more", "errors"]), coming_up),
    ("now_playing", "Now playing",
     "What people are watching or listening to in Jellyfin now.",
     "media", _obj({}), _out({"configured": {"type": "boolean"}, "items": ROWS}, ["configured", "items"]), now_playing),
    ("downloads_in_progress", "Downloads in progress",
     "What the download apps are downloading now, with progress and time left.",
     "downloads", _obj({"limit": LIMIT}), _out({"items": ROWS, "more": MORE, "errors": ROWS}, ["items", "more", "errors"]), downloads),
    ("download_problems", "Download problems",
     "Downloads that need attention or failed, with what each app said and what Starboard already tried.",
     "downloads", _obj({"limit": LIMIT}),
     _out({"count": {"type": "integer"}, "items": ROWS, "errors": ROWS}, ["count", "items", "errors"]), download_problems),
    ("requests", "Requests",
     "Requests for films and series from Seerr or Reelix, newest first, and how many wait for an answer.",
     "requests", _obj({"pending_only": {"type": "boolean", "default": False, "description": "true for only those waiting for an answer."},
                       "limit": LIMIT}),
     _out({"items": ROWS, "more": MORE, "configured": {"type": "boolean"}, "pending": {"type": "integer"}},
          ["items", "more", "configured", "pending"]), requests),
    ("app_health", "App health",
     "Whether each app answers, and the problems the apps report about themselves.",
     "apps", _obj({}), _out({"apps": ROWS, "problems": ROWS, "errors": ROWS}, ["apps", "problems", "errors"]), app_health),
    ("disk_space", "Disk space",
     "Each disk Starboard watches: its size, the space used and the space free, in bytes.",
     "system", _obj({}), _out({"disks": ROWS}, ["disks"]), disk_space),
]


def tools_for(k):
    """The tools key k may use, as tools/list gives them."""
    return [{"name": name, "title": title, "description": desc, "inputSchema": schema, "outputSchema": out, "annotations": {**READ_ONLY, "title": title}}
            for name, title, desc, scope, schema, out, _ in TOOLS if api_v1._scoped(k, scope)]


def valid(schema, value, where="arguments"):
    """A small JSON Schema check, enough for the tools' own schemas: types, required, enums, lengths, ranges, patterns
    and additionalProperties false. Returns the first problem in words, or "" when the value fits."""
    kinds = schema.get("type")
    if kinds:
        kinds = kinds if isinstance(kinds, list) else [kinds]
        py = {"object": dict, "array": list, "string": str, "integer": int, "number": (int, float), "boolean": bool, "null": type(None)}
        if not any(isinstance(value, py[t]) and not (t in ("integer", "number") and isinstance(value, bool)) for t in kinds):
            return f"{where} must be {' or '.join(kinds)}"
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", 1 << 30):
            return f"{where} must be from {schema.get('minLength', 0)} to {schema.get('maxLength')} letters"
        if "pattern" in schema and not re.search(schema["pattern"], value):
            return f"{where} is not in the right form"
    if isinstance(value, int) and not isinstance(value, bool):
        if value < schema.get("minimum", -(1 << 62)) or value > schema.get("maximum", 1 << 62):
            return f"{where} must be from {schema.get('minimum')} to {schema.get('maximum')}"
    if isinstance(value, dict):
        for name in schema.get("required", []):
            if name not in value:
                return f"{where}.{name} is missing"
        props = schema.get("properties") or {}
        for name, sub in props.items():
            if name in value:
                wrong = valid(sub, value[name], f"{where}.{name}")
                if wrong:
                    return wrong
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(props))
            if extra:
                return f"{where} does not take {', '.join(extra)[:100]}"
    if isinstance(value, list) and "items" in schema:
        for i, v in enumerate(value):
            wrong = valid(schema["items"], v, f"{where}[{i}]")
            if wrong:
                return wrong
    return ""


# JSON-RPC --------------------------------------------------------------------------------------------------------------

class RpcError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _error(rid, code, message):
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


def call_tool(h, k, params):
    """tools/call: the result, with isError true when the tool ran but could not answer (such as Reelix not added)."""
    from . import services
    name = params.get("name")
    args = params.get("arguments")
    args = {} if args is None else args
    tool = next((t for t in TOOLS if t[0] == name and api_v1._scoped(k, t[3])), None)
    if not tool:
        raise RpcError(INVALID_PARAMS, f"No tool called {str(name)[:60]} for this key")
    wrong = valid(tool[4], args)
    if wrong:
        raise RpcError(INVALID_PARAMS, wrong)
    try:
        out = api_v1.scrub(tool[6](h, k, args))
        ok, text = True, ""
    except api_v1.NotReady as e:
        ok, text = False, f"Not set up: {e}"
    except (LookupError, ValueError) as e:
        ok, text = False, str(e)
    except services.ServiceError as e:
        ok, text = False, "An app did not answer: " + str(e)[:300]
    api_v1.audit(h.app.data_dir, "mcp_call", key_id=k["id"], tool=name, ok=ok)
    if not ok:
        return {"content": [{"type": "text", "text": text}], "isError": True}
    raw = json.dumps(out, separators=(",", ":"), default=str)
    return {"content": [{"type": "text", "text": raw}], "structuredContent": json.loads(raw), "isError": False}


def answer(h, k, msg):
    """The result of one JSON-RPC request, or RpcError."""
    method, params = msg.get("method"), msg.get("params")
    if params is not None and not isinstance(params, dict):
        raise RpcError(INVALID_PARAMS, "params must be an object")
    params = params or {}
    if method == "initialize":
        asked = params.get("protocolVersion")
        return {"protocolVersion": asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "starboard", "title": "Starboard", "version": str(h.app.version)},
                "instructions": INSTRUCTIONS}
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": tools_for(k)}
    if method == "tools/call":
        return call_tool(h, k, params)
    raise RpcError(METHOD_NOT_FOUND, f"Starboard does not answer {str(method)[:60]}")


def handle(h, k, base, rate, problem):
    """One POST to /api/v1/mcp from key k, after api_v1.handle has checked the key and its rate."""
    if not h.app.config.data.get("mcp_enabled"):
        return problem(403, "mcp_off", "AI assistants cannot connect: turn them on in Settings, Security, API keys")
    origin = h.headers.get("Origin")
    if origin:
        host = h.headers.get("X-Forwarded-Host") if h.app.trust_proxy and h.headers.get("X-Forwarded-Host") else h.headers.get("Host", "")
        if urllib.parse.urlparse(origin).netloc != host:
            return problem(403, "origin_refused", "Starboard does not answer pages on other sites")
    if k["right"] != "read":
        return problem(403, "read_key_needed", "Give an AI assistant a Read only key. Make one in Settings, Security, API keys")
    version = (h.headers.get("MCP-Protocol-Version") or "").strip()
    if version and version not in PROTOCOL_VERSIONS:
        return problem(400, "bad_request", f"Starboard speaks MCP {' and '.join(PROTOCOL_VERSIONS)}, not {version[:20]}")
    try:
        length = h.content_length()
    except ValueError as e:
        return problem(400, "bad_request", str(e))
    if length > MAX_BODY:
        return problem(413, "too_large", "Send a JSON-RPC message of up to 64 KB")
    raw = h.rfile.read(length) if length else b""
    h._body_read = True
    headers = {**base, **rate, "Cache-Control": "no-store"}

    def reply(status, body):
        return h.send(status, json.dumps(body, separators=(",", ":"), default=str).encode(), "application/json", headers)

    try:
        msg = json.loads(raw)
    except ValueError:
        return reply(400, _error(None, PARSE_ERROR, "Send one JSON-RPC 2.0 message as JSON"))
    if isinstance(msg, list):
        return reply(400, _error(None, INVALID_REQUEST, "Send one message at a time: batches are not taken"))
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
        return reply(400, _error(None, INVALID_REQUEST, 'Send a JSON-RPC 2.0 object, with "jsonrpc": "2.0"'))
    if "method" not in msg or "id" not in msg:
        return h.send(202, b"", "application/json", headers)  # a notification, or a client's answer: nothing to say back
    rid = msg["id"]
    if isinstance(rid, bool) or not isinstance(rid, (str, int)):
        return reply(400, _error(None, INVALID_REQUEST, "id must be a string or a whole number"))
    try:
        return reply(200, {"jsonrpc": "2.0", "id": rid, "result": answer(h, k, msg)})
    except RpcError as e:
        return reply(200, _error(rid, e.code, str(e)))
