"""Connect an AI tool (DASH-655, release 1 of the AI assistant family): the Settings wizard's server side.

The wizard is a page (web/settings-security-ai.html). It turns the MCP address on (starboard/mcp.py), makes one named key
that only reads, and shows the address and key once, with the set-up for each kind of AI tool. This module holds:

- the plain-English words the wizard, the help and the tests all share (what each thing a key may read lets a tool do),
- the set-up text for each kind of AI tool, with {{address}} and {{key}} where the page puts the values it holds,
- GET /api/ai-tools: what the page needs, and what the AI tools did lately, from the audit log, in plain words,
- POST /api/ai-tools/connect: the one action, with the password, which turns the address on and makes the key together.

Nothing here runs unless the owner opens the page. A key is made only by a signed-in person who gives the password; a key
can never make a key, turn the address on, or revoke one (GENERAL_RIGHTS says mcp_enabled is never changed by a key).
"""
import json
import os
import re

from . import api_v1, logs, mcp

PATH = "/api/ai-tools"

# What each thing a key may read lets an AI tool do, in the words the wizard shows beside each tick. One list: the wizard,
# the keys page, the help and the tests read it, so they cannot say different things. (scope: title, what, default ticked)
SCOPE_WORDS = {
    "apps": ("Your apps", "Check whether each app answers, which problems it reports, what version it runs and which updates it says wait.", True),
    "downloads": ("Downloads", "Read what is downloading now, and which downloads failed or need attention.", True),
    "media": ("What is new and playing", "Read what was added lately, what is coming up, and what people are watching or listening to now.", True),
    "system": ("Disk space", "Read how big each disk is and how full.", True),
    "library": ("Your Library", "Search your films, series, music and books by title. Titles are text that anyone can write, so leave this off unless you need it.", False),
    "requests": ("Requests", "Read the requests people made for films and series.", False),
    "logs": ("Logs", "Read the last lines of Starboard's log and your apps' logs, with keys, emails, addresses and folder names hidden.", False),
    "updates": ("Updates", "Read which updates wait for Starboard, its apps and its plug-ins. It cannot start one.", False),
}
ALWAYS_CANNOT = [
    "Change anything: turn an app on or off, start an update, delete a file, or change a setting.",
    "Read a password, an app's key, a token or the set-up code.",
    "Reach another computer or open a web address.",
    "Make another key, or turn AI tools on or off.",
]
ENDS = {"30": "In 30 days", "90": "In 90 days (recommended)", "365": "In a year", "never": "Never"}

# The kinds of AI tool and how each is set up. {{address}} and {{key}} are filled in by the page, in the browser only: the
# key is shown once and never sent back to the server. Wording of each step is plain, and checked by tests/test_ai_tools.py.
CLIENTS = [
    {"id": "claude-desktop", "name": "Claude Desktop", "name_suggestion": "Claude Desktop",
     "line": "Anthropic's Claude app for a computer. It can reach Starboard through a small helper called mcp-remote.",
     "needs": "Node.js on the same computer, because the helper runs with npx.",
     "steps": ["In Claude Desktop, open Settings, then Developer, then Edit config. This opens the file claude_desktop_config.json.",
               "Add the block below inside the file. If the file already has mcpServers, add only the starboard part to it.",
               "Save the file and quit Claude Desktop completely, then open it again.",
               "Start a new chat. The tools show under the tools icon. Ask it: Which of my apps have a problem?"],
     "snippets": [{"label": "Add to claude_desktop_config.json", "language": "json", "text": json.dumps(
         {"mcpServers": {"starboard": {"command": "npx", "args": ["-y", "mcp-remote", "{{address}}", "--header", "Authorization:${STARBOARD_AUTH}"],
                                       "env": {"STARBOARD_AUTH": "Bearer {{key}}"}}}}, indent=2)}],
     "note_http": "Your address starts with http, not https, so add \"--allow-http\" after the address in args. mcp-remote refuses a plain http address without it."},
    {"id": "claude-code", "name": "Claude Code", "name_suggestion": "Claude Code",
     "line": "Anthropic's Claude in a terminal. It speaks to Starboard directly.",
     "needs": "The claude command, on a computer that can reach Starboard.",
     "steps": ["Open a terminal on that computer.",
               "Run the first line below. It asks for the key without showing it, so the key is not saved in your history. Paste the key and press Enter.",
               "Run the second line to add Starboard.",
               "Start claude and ask it: Which of my apps have a problem? Use /mcp to check that starboard shows as connected."],
     "snippets": [{"label": "In a terminal", "language": "bash", "text": "read -rs STARBOARD_KEY && export STARBOARD_KEY\n"
                   "claude mcp add --transport http starboard {{address}} --header \"Authorization: Bearer $STARBOARD_KEY\""}]},
    {"id": "other-mcp", "name": "Another MCP tool, such as Goose or Jan", "name_suggestion": "AI tool",
     "line": "Any tool that can connect to an MCP server over HTTP (Streamable HTTP).",
     "needs": "A tool that lists MCP servers or extensions in its settings.",
     "steps": ["Open the tool's settings and find where it adds an MCP server or extension.",
               "Choose the HTTP kind. It may be called Streamable HTTP or Remote.",
               "Enter the address, then add one header: Authorization, with Bearer, a space and the key.",
               "In Goose, you can instead add the extension block below to its config file, or run goose configure and choose Add Extension, then Remote Extension.",
               "Ask it: Which of my apps have a problem?"],
     "snippets": [{"label": "The values to enter", "language": "text", "text": "Type: HTTP (Streamable HTTP)\nAddress: {{address}}\nHeader name: Authorization\nHeader value: Bearer {{key}}"},
                  {"label": "Goose: an extension in its config file", "language": "yaml", "text": "extensions:\n  starboard:\n    name: Starboard\n    type: streamable_http\n"
                   "    uri: {{address}}\n    enabled: true\n    timeout: 300\n    headers:\n      Authorization: Bearer {{key}}"}]},
    {"id": "openai-compatible", "name": "A tool that speaks only the OpenAI language", "name_suggestion": "AI tool",
     "line": "Some chat tools and apps can talk to a model through an OpenAI-compatible address but cannot use MCP tools.",
     "needs": "A tool that can call MCP servers.",
     "steps": ["Starboard does not offer an OpenAI-compatible address. It offers MCP, which is a different language for tools.",
               "A tool that speaks only OpenAI cannot read Starboard on its own. Use a tool that speaks MCP, such as Goose or Jan. They can use any model, including one that speaks the OpenAI language, and Starboard through MCP at the same time.",
               "Then follow the steps for Another MCP tool."],
     "snippets": []},
]

TAILSCALE = {
    "title": "Away from home: use Tailscale Serve, never Funnel",
    "steps": ["Install Tailscale on the server and on the computer that runs the AI tool, and sign in to the same Tailscale account on both.",
              "On the server, run: tailscale serve --bg 8095. This shares Starboard only with your own devices, over HTTPS. Change 8095 if Starboard uses another port.",
              "Run tailscale serve status. It shows your server's name, such as <your-server>.<your-tailnet>.ts.net. Enter that name in the wizard.",
              "Tell Starboard the name. On the server, open the .env file in the Starboard folder and add the name to STARBOARD_ALLOWED_HOSTS, for example STARBOARD_ALLOWED_HOSTS=<your-server>.<your-tailnet>.ts.net. Then run docker compose up -d. Starboard otherwise answers 421.",
              "Never run tailscale funnel for Starboard, and never open port 8095 on your router. Funnel and an open port put Starboard on the public internet. Run tailscale funnel status: it should say Funnel is off."],
}

MAX_NAME = 60


def _words(scopes):
    return [SCOPE_WORDS[s][0] for s in scopes if s in SCOPE_WORDS]


def tools():
    """The tools an AI tool may be given, with the scope each needs: the wizard lists them under What it may do."""
    return [{"name": t[0], "title": t[1], "scope": t[3]} for t in mcp.TOOLS]


def overview(h):
    app = h.app
    info = app.network_info(h.client_address_text())
    keys = [k for k in api_v1._load(app.data_dir) if k.get("client")]
    return {"enabled": bool(app.config.data.get("mcp_enabled")), "path": mcp.PATH, "port": info["port"], "addresses": info["addresses"],
            "network_access": info["network_access"], "you_are_on_this_computer": info["you_are_on_this_computer"],
            "scopes": [{"id": s, "title": w[0], "what": w[1], "default": w[2]} for s, w in SCOPE_WORDS.items()],
            "cannot": ALWAYS_CANNOT, "ends": [{"id": k, "title": v} for k, v in ENDS.items()],
            "clients": CLIENTS, "tailscale": TAILSCALE, "tools": tools(),
            "keys": [{**api_v1.public(k), "client": k["client"], "can": _words(k.get("scopes") or [])} for k in keys],
            "activity": activity(app.data_dir)}


def connect(h, body):
    """Turns the address on and makes the key. All or nothing: if the key cannot be made, the address is left as it was."""
    app = h.app
    h.check_password(body)
    name = re.sub(r"\s+", " ", str(body.get("name") or "")).strip()[:MAX_NAME]
    scopes = body.get("scopes")
    if not isinstance(scopes, list) or not scopes:
        raise ValueError("Choose at least one thing the AI tool may read")
    if any(s not in api_v1.ALL_SCOPES for s in scopes):
        raise ValueError("Choose from the list of what it may read")
    days = str(body.get("expires_days", "90"))
    if days not in ENDS:
        raise ValueError("Choose when the key ends")
    client = str(body.get("client") or "other-mcp")
    if client not in {c["id"] for c in CLIENTS}:
        raise ValueError("Choose a kind of AI tool from the list")
    was_on = bool(app.config.data.get("mcp_enabled"))
    if not was_on:
        app.config.update_general({"mcp_enabled": True})
    try:
        key, item = api_v1.create_key(app.data_dir, name, "read", scopes, None if days == "never" else int(days), via="ai-tools")
    except ValueError:
        if not was_on:
            app.config.update_general({"mcp_enabled": False})
        raise
    keys = api_v1._load(app.data_dir)  # the kind of tool the key was made for: kept with the key, never shown in the API
    for k in keys:
        if k["id"] == item["id"]:
            k["client"] = client
    api_v1._save(app.data_dir, keys)
    if not was_on:
        api_v1.audit(app.data_dir, "mcp_turned_on", session=h.session_label(), via="ai-tools")
    logs.event("info", "security", f"AI tools turned on and a key made: {item['name']}" if not was_on else f"A key for an AI tool was made: {item['name']}")
    return {"key": key, "item": item, "enabled": True, "turned_on_now": not was_on, "can": _words(scopes), "cannot": ALWAYS_CANNOT}


def route(h, method, path):
    if method == "GET" and path == PATH:
        return h.json(200, overview(h), {"Cache-Control": "no-store"})
    if method == "POST" and path == PATH + "/connect":
        return h.json(200, connect(h, h.body()), {"Cache-Control": "no-store"})
    return h.error(404, "Not found")


# Recent activity, in plain words ------------------------------------------------------------------------------------

LINES = ("key_created", "key_used", "key_revoked", "mcp_call", "mcp_refused", "mcp_turned_on", "mcp_turned_off")
TITLES = {t[0]: t[1] for t in mcp.TOOLS}


def _sentence(e):
    what, name = e.get("what"), str(e.get("name") or e.get("key_name") or "A key")[:60]
    if what == "key_created":
        return name, f"Key made. It may read: {', '.join(_words(e.get('scopes') or [])) or 'everything but logs and updates'}."
    if what == "key_used":
        return name, "Used for the first time." if e.get("first") else "Used again after a quiet spell."
    if what == "key_revoked":
        return name, "Revoked. It no longer works."
    if what == "mcp_call":
        tool = TITLES.get(str(e.get("tool")), "a tool")
        return name, f"Asked: {tool}. " + ("Done." if e.get("ok") else "It did not work.")
    if what == "mcp_refused":
        return name, "Asked for something this key may not have. Starboard refused it."
    if what in ("mcp_turned_on", "mcp_turned_off"):
        return "You", "AI tools turned on." if what.endswith("on") else "AI tools turned off. Every AI tool stopped."
    return name, what


def activity(data_dir, most=30):
    """The newest lines about AI tools in the audit log, newest first, as {time, who, what}. Keys that belong to plug-ins
    are left out. Reads the last two files, backwards, and stops as soon as it has enough."""
    base = os.path.join(data_dir, "logs", "audit.jsonl")
    out = []
    for path in (base, base + ".1"):
        try:
            for raw in logs._lines_backwards(path):
                try:
                    e = json.loads(raw)
                except ValueError:
                    continue
                if not isinstance(e, dict) or e.get("what") not in LINES:
                    continue
                if str(e.get("name", "")).startswith("Plug-in: "):
                    continue
                who, said = _sentence(e)
                out.append({"time": e.get("time"), "who": who, "what": said})
                if len(out) >= most:
                    return out
        except OSError:
            continue
    return out
