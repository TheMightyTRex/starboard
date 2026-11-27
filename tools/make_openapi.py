"""Writes starboard/openapi.json, the description of the public API (DASH-274). Run after changing a route.

The scope each route needs (x-scope) and the version come from starboard/api_v1.py, the table the server answers
from, so the description cannot say something the code does not do. With --check it writes nothing and fails when
the file in the repository is not what it would write (DASH-281: tools/check-api.sh and CI run it that way).

    python3 tools/make_openapi.py           # write starboard/openapi.json
    python3 tools/make_openapi.py --check   # fail if it is out of date
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from starboard import api_v1, mcp  # noqa: E402

page = {"limit": {"name": "limit", "in": "query", "schema": {"type": "integer", "minimum": 1, "maximum": 200, "default": 50},
                  "description": "How many to give back."},
        "cursor": {"name": "cursor", "in": "query", "schema": {"type": "string"},
                   "description": "The next_cursor of the previous answer."}}
P = [{"$ref": "#/components/parameters/limit"}, {"$ref": "#/components/parameters/cursor"}]


def ok(schema, desc="It worked."):
    return {"200": {"description": desc, "headers": {"ETag": {"$ref": "#/components/headers/ETag"}, "X-Request-Id": {"$ref": "#/components/headers/X-Request-Id"}},
                    "content": {"application/json": {"schema": schema}}},
            "304": {"description": "Not changed since the ETag sent in If-None-Match."},
            "401": {"$ref": "#/components/responses/Problem"}, "429": {"$ref": "#/components/responses/Problem"}}


def listing(item, extra=None):
    props = {"items": {"type": "array", "items": item}, "next_cursor": {"type": ["string", "null"]}, **(extra or {})}
    return {"type": "object", "required": ["items", "next_cursor"], "properties": props}


ANY = {"type": "object", "additionalProperties": True}
spec = {
    "openapi": "3.1.0",
    "info": {"title": "Starboard API", "version": api_v1.API_VERSION,
             "description": "Make a key in Starboard: Settings, Security, API keys. Send it as Authorization: Bearer sb_read_... or sb_manage_... "
                            "A read key reads; a manage key also does the everyday actions (each POST, marked x-right: manage). x-scope is the scope a key needs. "
                            "Errors are RFC 9457 problem details. Lists use limit and cursor. Answers carry an ETag; send If-None-Match to get 304.",
             "license": {"name": "MIT", "identifier": "MIT"}},
    "servers": [{"url": "/"}],
    "security": [{"key": []}],
    "paths": {
        "/api/v1/": {"get": {"operationId": "getRoot", "summary": "The API's version, Starboard's version and links", "tags": ["About"],
                             "responses": ok({"$ref": "#/components/schemas/Root"})}},
        "/api/v1/me": {"get": {"operationId": "getMe", "summary": "The key you are using: its name, right and scopes", "tags": ["About"],
                               "responses": ok({"$ref": "#/components/schemas/Key"})}},
        "/api/v1/openapi.json": {"get": {"operationId": "getOpenApi", "summary": "This description", "tags": ["About"], "security": [],
                                         "responses": {"200": {"description": "The OpenAPI 3.1 description.", "content": {"application/json": {"schema": ANY}}}}}},
        "/api/v1/apps": {"get": {"operationId": "listApps", "summary": "The apps on the dashboard", "tags": ["Apps"], "parameters": P,
                                 "responses": ok(listing({"$ref": "#/components/schemas/App"}))}},
        "/api/v1/apps/{id}": {"get": {"operationId": "getApp", "summary": "One app", "tags": ["Apps"],
                                      "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                                      "responses": {**ok({"$ref": "#/components/schemas/App"}), "404": {"$ref": "#/components/responses/Problem"}}}},
        "/api/v1/status": {"get": {"operationId": "listStatus", "summary": "Whether each app answers, checked every 15 seconds at most", "tags": ["Apps"],
                                   "parameters": P, "responses": ok(listing(ANY))}},
        "/api/v1/health": {"get": {"operationId": "listHealth", "summary": "Problems the apps report", "tags": ["Apps"], "parameters": P,
                                   "responses": ok(listing(ANY, {"errors": {"type": "array", "items": ANY}}))}},
        "/api/v1/downloads": {"get": {"operationId": "listDownloads", "summary": "What is downloading", "tags": ["Downloads"], "parameters": P,
                                      "responses": ok(listing(ANY, {"errors": {"type": "array", "items": ANY}}))}},
        "/api/v1/recent": {"get": {"operationId": "listRecent", "summary": "Recently added films, series and books", "tags": ["Media"], "parameters": P,
                                   "responses": ok(listing(ANY))}},
        "/api/v1/playing": {"get": {"operationId": "getPlaying", "summary": "What is playing in Jellyfin", "tags": ["Media"],
                                    "responses": ok({"type": "object", "required": ["configured", "items"],
                                                     "properties": {"configured": {"type": "boolean"}, "items": {"type": "array", "items": ANY}}})}},
        "/api/v1/system": {"get": {"operationId": "getSystem", "summary": "Processor, memory, disks and uptime", "tags": ["System"],
                                   "responses": ok({"type": "object", "properties": {"cpus": {"type": "integer"}, "load": {"type": "array", "items": {"type": "number"}}, "memory": ANY,
                                                                                     "disks": {"type": "array", "items": ANY}, "uptime_seconds": {"type": "number"}}})}},
    },
    "components": {
        "securitySchemes": {"key": {"type": "http", "scheme": "bearer", "description": "A Starboard API key, sb_read_... or sb_manage_..."}},
        "parameters": page,
        "headers": {"ETag": {"schema": {"type": "string"}, "description": "Send it back in If-None-Match."},
                    "X-Request-Id": {"schema": {"type": "string"}, "description": "Yours, or one Starboard made; also in problem.instance."}},
        "responses": {"Problem": {"description": "RFC 9457 problem details.",
                                  "content": {"application/problem+json": {"schema": {"$ref": "#/components/schemas/Problem"}}}}},
        "schemas": {
            "Root": {"type": "object", "required": ["api_version", "starboard_version", "links"],
                     "properties": {"api_version": {"type": "string"}, "starboard_version": {"type": "string"}, "links": {"type": "object"},
                                   "deprecations": {"type": "array", "description": "Features that are going: each has method, path, deprecated, sunset (dates), replacement and removed.",
                                                    "items": {"type": "object", "additionalProperties": True}},
                                   "capabilities": {"type": "array", "items": {"type": "string"}, "description": "The names of the optional plug-in parts this Starboard has, such as first-sign-in and media-server-slot."}}},
            "Key": {"type": "object", "required": ["id", "name", "right", "scopes", "created_at", "prefix"],
                    "properties": {"id": {"type": "string"}, "name": {"type": "string"}, "right": {"type": "string", "enum": list(api_v1.RIGHTS)},
                                   "scopes": {"type": "array", "items": {"type": "string", "enum": list(api_v1.ALL_SCOPES)}},
                                   "created_at": {"type": "string", "format": "date-time"},
                                   "expires_at": {"type": ["string", "null"], "format": "date-time"},
                                   "last_used_at": {"type": ["string", "null"], "format": "date-time"}, "prefix": {"type": "string"}}},
            "App": {"type": "object", "required": ["id", "name", "type", "group", "enabled", "url", "api_key_set"],
                    "properties": {"id": {"type": "string"}, "name": {"type": "string"}, "type": {"type": "string"}, "group": {"type": "string"},
                                   "enabled": {"type": "boolean"}, "url": {"type": "string"}, "api_key_set": {"type": "boolean"}}},
            "Problem": {"type": "object", "required": ["type", "title", "status", "code"],
                        "properties": {"type": {"type": "string"}, "title": {"type": "string"}, "status": {"type": "integer"}, "detail": {"type": "string"},
                                       "instance": {"type": "string"}, "code": {"type": "string"}}},
        },
    },
}


# Added in 1.1.0 (DASH-274, DASH-246): the other read rows of the capabilities list, the manage actions and events.
ERRS = {"errors": {"type": "array", "items": ANY}}


def query(name, schema, description, required=False):
    return {"name": name, "in": "query", "required": required, "schema": schema, "description": description}


def path_param(name, schema=None):
    return {"name": name, "in": "path", "required": True, "schema": schema or {"type": "string"}}


def needs_reelix(responses):
    return {**responses, "409": {"$ref": "#/components/responses/Problem"}, "502": {"$ref": "#/components/responses/Problem"}}


def write(schema, summary, op_id, tag, body=None, status="200", desc="It worked.", extra=None):
    """A manage action: POST with a JSON body, an optional Idempotency-Key, and its errors."""
    op = {"operationId": op_id, "summary": summary, "tags": [tag],
          "parameters": [{"$ref": "#/components/parameters/idempotency"}],
          "requestBody": {"required": False, "content": {"application/json": {"schema": body or {"type": "object"}}}},
          "responses": {status: {"description": desc, "headers": {"X-Request-Id": {"$ref": "#/components/headers/X-Request-Id"}},
                                 "content": {"application/json": {"schema": schema}}},
                        "400": {"$ref": "#/components/responses/Problem"}, "401": {"$ref": "#/components/responses/Problem"},
                        "403": {"$ref": "#/components/responses/Problem"}, "404": {"$ref": "#/components/responses/Problem"},
                        "413": {"$ref": "#/components/responses/Problem"}, "429": {"$ref": "#/components/responses/Problem"},
                        **(extra or {})}}
    return op


OK_BODY = {"type": "object", "required": ["ok"], "properties": {"ok": {"type": "boolean"}}}
ACCEPTED = {"type": "object", "required": ["accepted", "status"], "properties": {"accepted": {"type": "boolean"}, "status": {"type": "string"}}}
HOURS = {"type": "object", "required": ["enabled"], "properties": {"enabled": {"type": "boolean"}, "start": {"type": "integer"}, "end": {"type": "integer"},
                                                                   "mode": {"type": "string", "enum": ["run", "pause"]}, "reason": {"type": "string"},
                                                                   "next_change": {"type": "string"}, "clients": {"type": "array", "items": {"type": "string"}},
                                                                   "now": {"type": "array", "items": ANY}, "errors": {"type": "array", "items": ANY},
                                                                   "held": {"type": "object", "required": ["held"], "description": "Added in 1.12.0: whether a plug-in holds heavy work now (such as the UPS and power plug-in on battery), which pauses downloads whatever the hours say",
                                                                            "properties": {"held": {"type": "boolean"}, "reason": {"type": "string"}, "until": {"type": "integer"}, "by": {"type": "string"}}}}}
CONTAINERS = {"type": "object", "required": ["available", "items"],
              "properties": {"available": {"type": "boolean"}, "checked_at": {"type": ["number", "null"]}, "restored": {"type": "boolean"},
                             "items": {"type": "array", "items": ANY}, "next_cursor": {"type": ["string", "null"]}}}

spec["paths"].update({
    "/api/v1/calendar": {"get": {"operationId": "listCalendar", "summary": "Coming up: films, episodes, albums and books due, from the apps", "tags": ["Media"],
                                 "parameters": P + [query("month", {"type": "string", "pattern": "^\\d{4}-\\d{2}$"},
                                                          "A month, such as 2026-11, with a week either side. Without it, from yesterday for the days set in Settings, General.")],
                                 "responses": {**ok(listing(ANY, ERRS)), "400": {"$ref": "#/components/responses/Problem"}}}},
    "/api/v1/requests": {"get": {"operationId": "listRequests", "summary": "Requests from Seerr or Reelix, newest first", "tags": ["Requests"],
                                 "parameters": P + [query("pending", {"type": "string", "enum": ["true", "false"]}, "true for only those waiting for an answer.")],
                                 "responses": ok(listing(ANY, {"configured": {"type": "boolean"}, "pending": {"type": "integer"}}))}},
    "/api/v1/requests/{id}/approve": {"post": write(OK_BODY, "Approve a request", "approveRequest", "Requests", extra={"502": {"$ref": "#/components/responses/Problem"}}) | {
        "parameters": [path_param("id"), {"$ref": "#/components/parameters/idempotency"}]}},
    "/api/v1/requests/{id}/decline": {"post": write(OK_BODY, "Decline a request, with an optional reason", "declineRequest", "Requests",
                                                    body={"type": "object", "properties": {"reason": {"type": "string", "maxLength": 500}}},
                                                    extra={"502": {"$ref": "#/components/responses/Problem"}}) | {
        "parameters": [path_param("id"), {"$ref": "#/components/parameters/idempotency"}]}},
    "/api/v1/transfer": {"get": {"operationId": "getTransfer", "summary": "Download speeds from each download app, and whether the VPN is connected", "tags": ["Downloads"],
                                 "responses": ok({"type": "object", "required": ["clients", "vpn", "errors"],
                                                  "properties": {"clients": {"type": "array", "items": ANY}, "vpn": {"type": "array", "items": ANY}, **ERRS}})}},
    "/api/v1/download-hours": {
        "get": {"operationId": "getDownloadHours", "summary": "Download hours: whether they are active, and whether downloads run or wait now", "tags": ["Downloads"],
                "responses": ok(HOURS)},
        "post": write(HOURS, "Resume or pause downloads until the next change of the hours, or follow the hours again", "actOnDownloadHours", "Downloads",
                      body={"type": "object", "required": ["action"], "properties": {"action": {"type": "string", "enum": ["resume", "pause", "follow"]}}})},
    "/api/v1/downloads/actions": {"post": write(OK_BODY, "Remove, block, or block and search again for one download, as the Downloads page does", "actOnDownload", "Downloads",
                                                body={"type": "object", "required": ["app_id", "id", "action"],
                                                      "properties": {"app_id": {"type": "string", "description": "service from /api/v1/downloads."},
                                                                     "id": {"type": "integer", "description": "id from /api/v1/downloads."},
                                                                     "action": {"type": "string", "enum": ["remove", "block", "block-search", "import", "ignore"]}}},
                                                extra={"502": {"$ref": "#/components/responses/Problem"}})},
    "/api/v1/history": {"get": {"operationId": "listHistory", "summary": "Reelix's history: what was sent to download, added and failed, newest first", "tags": ["Downloads"],
                                "parameters": [{"$ref": "#/components/parameters/cursor"},
                                               query("which", {"type": "string", "enum": ["all", "grabbed", "imported", "failed"], "default": "all"}, "Which events.")],
                                "responses": needs_reelix({**ok(listing(ANY)), "400": {"$ref": "#/components/responses/Problem"}})}},
    "/api/v1/library": {"get": {"operationId": "getLibrary", "summary": "The Library: recently added, and how many there are on each tab", "tags": ["Library"],
                                "responses": needs_reelix(ok({"type": "object", "required": ["recent", "tabs"],
                                                              "properties": {"recent": {"type": "array", "items": ANY}, "tabs": {"type": "array", "items": ANY}}}))}},
    "/api/v1/library/search": {"get": {"operationId": "searchLibrary", "summary": "Search the Library: matches on each tab, best first", "tags": ["Library"],
                                       "parameters": P + [query("q", {"type": "string", "minLength": 1, "maxLength": 120}, "What to search for.", True)],
                                       "responses": needs_reelix({**ok(listing(ANY)), "400": {"$ref": "#/components/responses/Problem"}})}},
    "/api/v1/library/status": {"get": {"operationId": "getLibraryStatus", "summary": "How big each tab's index is, when it was built, and any error", "tags": ["Library"],
                                       "responses": ok({"type": "object", "required": ["tabs", "errors"],
                                                        "properties": {"tabs": {"type": "array", "items": ANY}, "errors": ANY}})}},
    "/api/v1/library/refresh": {"post": write(ACCEPTED, "Build one tab's index again, in the background", "refreshLibrary", "Library", status="202",
                                              desc="Started. Read /api/v1/library/status to see when it is built.",
                                              body={"type": "object", "required": ["tab"],
                                                    "properties": {"tab": {"type": "string", "enum": ["films", "tv", "music", "radio", "books", "audiobooks"]}}},
                                              extra={"409": {"$ref": "#/components/responses/Problem"}})},
    "/api/v1/uptime": {"get": {"operationId": "listUptime", "summary": "How long each app has answered, from the watch's checks", "tags": ["Apps"],
                               "parameters": P, "responses": ok(listing(ANY, {"enabled": {"type": "boolean"}}))}},
    "/api/v1/app-updates": {"get": {"operationId": "listAppUpdates", "summary": "Updates that Sonarr, Radarr, Lidarr, Readarr and Prowlarr report", "tags": ["Apps"],
                                    "parameters": P, "responses": ok(listing(ANY, ERRS))}},
    "/api/v1/numbers": {"get": {"operationId": "listNumbers", "summary": "Counts from each app, such as films, series and books", "tags": ["Apps"],
                                "parameters": P, "responses": ok(listing(ANY))}},
    "/api/v1/containers": {"get": {"operationId": "listContainers", "summary": "Each app's container, its version and whether a newer image is out", "tags": ["Apps"],
                                   "parameters": P, "responses": ok(CONTAINERS)}},
    "/api/v1/containers/check": {"post": write(CONTAINERS, "Check for newer images of the apps' containers now", "checkContainers", "Apps")},
    "/api/v1/version": {"get": {"operationId": "getVersion", "summary": "Starboard's version, and the newest release when checking for new versions is active", "tags": ["System"],
                                "responses": ok({"type": "object", "required": ["current"],
                                                 "properties": {"current": {"type": "string"}, "latest": {"type": ["string", "null"]},
                                                                "repo": {"type": ["string", "null"]}, "since": {"type": ["number", "null"]}}})}},
    "/api/v1/system/history": {"get": {"operationId": "getSystemHistory", "summary": "Processor, memory and network over the last hours", "tags": ["System"],
                                       "parameters": [query("hours", {"type": "string", "enum": ["1", "6", "24"], "default": "1"}, "How many hours.")],
                                       "responses": {**ok({"type": "object", "required": ["hours", "interval", "points"],
                                                           "properties": {"hours": {"type": "integer"}, "interval": {"type": "integer"},
                                                                          "points": {"type": "array", "items": ANY}}}),
                                                     "400": {"$ref": "#/components/responses/Problem"}}}},
    "/api/v1/alerts/test": {"post": write(OK_BODY, "Send a test alert to the channel set in Settings, General, Alerts", "testAlert", "System")},
    "/api/v1/extras": {"get": {"operationId": "listExtras", "summary": "Jellyfin and Audiobookshelf jobs: Live TV, watch history, user defaults and listening progress", "tags": ["Media"],
                               "responses": ok({"type": "object", "required": ["items"], "properties": {"items": {"type": "array", "items": ANY}}})}},
    "/api/v1/extras/{name}/run": {"post": write(ACCEPTED, "Run a Jellyfin or Audiobookshelf job now", "runExtra", "Media", status="202",
                                                desc="Started. Read /api/v1/extras to see how it went.") | {
        "parameters": [path_param("name", {"type": "string", "enum": ["livetv", "import", "defaults", "listening"]}),
                       {"$ref": "#/components/parameters/idempotency"}]}},
    "/api/v1/logs": {"get": {"operationId": "listLogs", "summary": "Starboard's log, newest first, with addresses, names and keys taken out", "tags": ["System"],
                             "description": "Only for keys that ticked Logs: a key with no scopes does not read them.",
                             "parameters": P + [query("level", {"type": "string", "enum": ["all", "problems"], "default": "all"}, "problems for warnings and errors only."),
                                                query("q", {"type": "string", "maxLength": 100}, "Only lines with these words.")],
                             "responses": {**ok(listing({"type": "object", "required": ["time", "level", "area", "message"],
                                                         "properties": {"time": {"type": "string", "format": "date-time"}, "level": {"type": "string"},
                                                                        "area": {"type": "string"}, "message": {"type": "string"}}})),
                                           "400": {"$ref": "#/components/responses/Problem"}}}},
    "/api/v1/events": {"get": {"operationId": "streamEvents", "summary": "Events as they happen, as Server-Sent Events", "tags": ["Events"],
                               "description": "A text/event-stream. Each event is CloudEvents-shaped JSON: specversion, id, type (such as starboard.app.down), "
                                              "source, time and data. A key hears only the events its scopes cover. Send Last-Event-ID to resume. "
                                              "Up to 8 streams at once; each closes after an hour.",
                               "parameters": [{"name": "Last-Event-ID", "in": "header", "required": False, "schema": {"type": "string"},
                                               "description": "The id of the last event you read."}],
                               "responses": {"200": {"description": "The stream.", "content": {"text/event-stream": {"schema": {"type": "string"}}}},
                                             "401": {"$ref": "#/components/responses/Problem"}, "429": {"$ref": "#/components/responses/Problem"},
                                             "503": {"$ref": "#/components/responses/Problem"}}}},
})

# Added in 1.2.0 (DASH-424): updates. Only for keys that ticked Updates; starting one and rolling back need manage.
TARGET = {"type": "string", "pattern": "^(starboard|reelix|app:[A-Za-z0-9_-]{1,64}|plugin:[a-z0-9-]{3,40})$",
          "description": "starboard, reelix, app:<app id> or plugin:<plug-in id>, as /api/v1/updates lists them."}
UPDATE_STEP = {"type": "object", "required": ["id", "label", "state"],
               "properties": {"id": {"type": "string"}, "label": {"type": "string"},
                              "state": {"type": "string", "enum": ["waiting", "working", "done", "failed", "skipped", "not-needed", "went-back", "held"],
                                        "description": "went-back and held only in Install all updates, where each step is one update."},
                              "detail": {"type": "string"}}}
spec["components"]["schemas"]["UpdateRun"] = {
    "type": "object", "required": ["id", "target", "kind", "name", "action", "from", "to", "by", "state", "said", "started_at", "steps"],
    "properties": {"id": {"type": "string"}, "target": {"type": "string"}, "kind": {"type": "string", "enum": ["starboard", "reelix", "app", "plugin", "jellyfin-plugins", "batch"]},
                   "name": {"type": "string"}, "action": {"type": "string", "enum": ["update", "rollback"]},
                   "from": {"type": "string"}, "to": {"type": "string"}, "by": {"type": "string"},
                   "state": {"type": "string", "enum": ["running", "updated", "up-to-date", "went-back", "rolled-back", "refused", "failed", "some-updated"],
                             "description": "some-updated only for Install all updates (kind batch): some updated, some did not."},
                   "said": {"type": "string"}, "started_at": {"type": "string", "format": "date-time"},
                   "finished_at": {"type": ["string", "null"], "format": "date-time"}, "steps": {"type": "array", "items": UPDATE_STEP}}}
spec["components"]["schemas"]["UpdateTarget"] = {
    "type": "object", "required": ["id", "kind", "name", "current", "latest", "update_available", "can_update", "can_roll_back"],
    "properties": {"id": {"type": "string"}, "kind": {"type": "string", "enum": ["starboard", "reelix", "app", "plugin"]},
                   "name": {"type": "string"}, "current": {"type": "string"}, "latest": {"type": "string"},
                   "update_available": {"type": "boolean"}, "can_update": {"type": "boolean"}, "why": {"type": "string"},
                   "can_roll_back": {"type": "boolean"}, "roll_back_to": {"type": "string"}, "note": {"type": "string"},
                   "big_change": {"type": "boolean", "description": "An app or Reelix: the new version is a new major version (1.5.0)."}}}
RUN = {"$ref": "#/components/schemas/UpdateRun"}
STARTED = {"type": "object", "required": ["accepted", "run", "status"],
           "properties": {"accepted": {"type": "boolean"}, "run": RUN, "status": {"type": "string"}}}
UPDATES_NOTE = "Only for keys that ticked Updates: a key with no scopes does not have them."
spec["paths"].update({
    "/api/v1/updates": {
        "get": {"operationId": "listUpdates", "summary": "What can be updated: Starboard, Reelix, the other apps and the plug-ins", "tags": ["Updates"],
                "description": UPDATES_NOTE + " From what Starboard already knows (its release check, the last check for app updates and the "
                               "catalogues it has read): nothing is fetched to answer. running is the update running now, if any.",
                "parameters": P, "responses": ok(listing({"$ref": "#/components/schemas/UpdateTarget"}, {"running": {"oneOf": [RUN, {"type": "null"}]}}))},
        "post": write(STARTED, "Start an update to the newest version Starboard knows", "startUpdate", "Updates", status="202",
                      desc="Started. Read status, the run's address, every few seconds until its state is not running.",
                      body={"type": "object", "required": ["target"], "properties": {"target": TARGET}},
                      extra={"409": {"$ref": "#/components/responses/Problem"}, "502": {"$ref": "#/components/responses/Problem"}}) | {
            "description": UPDATES_NOTE + " One update runs at a time. Each has the same backup, health check and way back as on the pages: "
                           "Starboard runs update.sh; Reelix and the other apps keep their old image until the new one is healthy; "
                           "a plug-in runs its before step, moves its settings, waits for its health check and goes back by itself if it fails. "
                           "Never from an address: only the version Starboard already found."}},
    "/api/v1/updates/rollback": {"post": write(STARTED, "Roll a plug-in back to the version kept before its last update", "rollBackUpdate", "Updates",
                                               status="202", desc="Started. Read status until its state is rolled-back.",
                                               body={"type": "object", "required": ["target"], "properties": {"target": TARGET}},
                                               extra={"409": {"$ref": "#/components/responses/Problem"}}) | {
        "description": UPDATES_NOTE + " Only plug-ins keep the version before. Starboard and the apps go back by themselves when a new "
                       "version does not answer, so for them this answers 409 cannot_update."}},
    "/api/v1/updates/runs": {"get": {"operationId": "listUpdateRuns", "summary": "The last 20 updates and roll backs, newest first", "tags": ["Updates"],
                                     "description": UPDATES_NOTE, "parameters": P, "responses": ok(listing(RUN))}},
    "/api/v1/updates/runs/{id}": {"get": {"operationId": "getUpdateRun", "summary": "One update's progress, step by step, and how it ended", "tags": ["Updates"],
                                          "description": UPDATES_NOTE + " While Starboard itself updates it restarts: the answer may not come for about a minute.",
                                          "parameters": [path_param("id", {"type": "string", "pattern": "^[0-9a-f]{12}$"})],
                                          "responses": {**ok(RUN), "404": {"$ref": "#/components/responses/Problem"}}}},
})
# Added in 1.5.0 (DASH-454): Install all updates, as one batch.
BATCH_ITEM = {"type": "object", "required": ["target", "kind", "name", "from", "to", "order"],
              "properties": {"target": {"type": "string"}, "kind": {"type": "string", "enum": ["starboard", "reelix", "app", "plugin", "jellyfin-plugins"]},
                             "name": {"type": "string"}, "from": {"type": "string"}, "to": {"type": "string"},
                             "order": {"type": "integer", "description": "Lower runs first."},
                             "why": {"type": "string", "description": "Held back only: why it waits for you."},
                             "note": {"type": "string"}}}
spec["paths"]["/api/v1/updates/all"] = {
    "get": {"operationId": "planAllUpdates", "summary": "What Install all updates would do now, in order, and what is held back", "tags": ["Updates"],
            "description": UPDATES_NOTE + " items run one at a time, in this order: the other apps, Jellyfin's plug-ins, Starboard's plug-ins, Reelix, "
                           "then Jellyfin restarts once (never while someone is watching), then Starboard last. held lists what always waits for "
                           "you: a plug-in asking for new permissions or that comes as a zip file, a new major version, and anything Starboard "
                           "cannot update here. Reads each waiting plug-in's new manifest from its catalogue (kept 10 minutes). count does not "
                           "include Jellyfin's plug-ins, whose new versions only Jellyfin knows.",
            "responses": ok({"type": "object", "required": ["items", "held", "count"],
                             "properties": {"items": {"type": "array", "items": BATCH_ITEM}, "held": {"type": "array", "items": BATCH_ITEM},
                                            "count": {"type": "integer"}}})},
    "post": write(STARTED, "Install all updates: every waiting update as one batch", "startAllUpdates", "Updates", status="202",
                  desc="Started. Read status every few seconds: its steps are the updates, in order, each with its state. Starboard updates "
                       "last and restarts, so the answer may not come for about a minute near the end.",
                  body={"type": "object", "properties": {"targets": {"type": "array", "items": {"type": "string"}, "maxItems": 200,
                                                                       "description": "Only these targets of GET /api/v1/updates/all, such as the ones you showed a person. Leave it out for all of them."}}},
                  extra={"409": {"$ref": "#/components/responses/Problem"}}) | {
        "description": UPDATES_NOTE + " One at a time, never in parallel, each with its own backup, health check and way back. One that fails "
                       "goes back by itself and the rest carry on. Answers 409 update_running while another update runs, and 409 "
                       "cannot_update when nothing is waiting or everything waiting is held back."}}
# Added in 1.3.0 (DASH-434): the queue's issues, for an AI helper.
STR_MAP = {"type": "object", "additionalProperties": {"type": "string"}}
spec["components"]["schemas"]["DownloadIssue"] = {
    "type": "object",
    "required": ["app", "app_id", "app_type", "reelix", "kind", "what", "title", "status", "app_state", "messages", "size", "progress",
                 "time_left", "added", "age", "indexer", "protocol", "quality", "download_client", "download_client_ids", "paths", "ids", "tried"],
    "properties": {"app": {"type": "string"}, "app_id": {"type": "string"}, "app_type": {"type": "string", "enum": ["sonarr", "radarr", "lidarr", "readarr", "reelix"]},
                   "reelix": {"type": "boolean", "description": "true when the download is Reelix's."},
                   "kind": {"type": "string", "description": "film, episode, album, book or radio episode, when known."},
                   "what": {"type": "string", "description": "The film, episode or book it is for, when the app says."},
                   "title": {"type": "string", "description": "The release's name."},
                   "status": {"type": "string", "enum": ["Needs attention", "Failed"]},
                   "app_state": {**STR_MAP, "description": "The app's own state words, such as tracked_state importBlocked."},
                   "messages": {"type": "array", "items": {"type": "string"}, "description": "Every message from the app, with secrets and private addresses taken out."},
                   "size": {"type": "number"}, "progress": {"type": "number"}, "time_left": {"type": "string"},
                   "added": {"type": "string"}, "age": {"type": "string"}, "indexer": {"type": "string"}, "protocol": {"type": "string"},
                   "quality": {"type": "string"}, "download_client": {"type": "string"},
                   "download_client_ids": {"type": "object", "description": "download_id (the torrent's id or the Usenet download's id) and, for Reelix, client_id_in_reelix."},
                   "paths": {**STR_MAP, "description": "output: where it downloaded to, as the app sees it inside its container. Only media and download folders."},
                   "ids": {"type": "object", "description": "The ids in the app (in Reelix, Reelix's ids): queue, and film, series, episode, album, book or radio show."},
                   "can_manual_import": {"type": "boolean"},
                   "tried": {"type": "array", "items": {"type": "object", "required": ["at", "what"],
                                                         "properties": {"at": {"type": "string", "format": "date-time"}, "what": {"type": "string"}}},
                             "description": "What Starboard already did about it, oldest first."}}}
spec["paths"]["/api/v1/downloads/issues"] = {"get": {
    "operationId": "listDownloadIssues", "summary": "Every download that needs attention or failed, with its details, and as Markdown for an AI helper",
    "tags": ["Downloads"],
    "description": "Each app's queue is asked once when you call this (at most every 10 seconds), never on a timer. markdown starts with a short "
                   "prompt telling an AI helper what to do, then one section for each download. Keys, passwords, tokens, private addresses "
                   "and full download addresses are taken out; paths are only those in media and download folders.",
    "responses": ok({"type": "object", "required": ["generated_at", "count", "apps_asked", "items", "errors", "markdown"],
                     "properties": {"generated_at": {"type": "string", "format": "date-time"}, "count": {"type": "integer"},
                                    "apps_asked": {"type": "integer"}, "items": {"type": "array", "items": {"$ref": "#/components/schemas/DownloadIssue"}},
                                    **ERRS, "markdown": {"type": "string"}}})}}
# Added in 1.4.0 (DASH-451): the log limits and Delete all logs. Only for keys that ticked Logs; changing the limits
# and deleting need manage.
LOGS_NOTE = "Only for keys that ticked Logs: a key with no scopes does not have them."
LOG_SUMMARY = {"type": "object", "required": ["days", "oldest", "bytes", "files", "keep_days", "max_bytes"],
               "properties": {"days": {"type": "integer", "description": "Day files kept."},
                              "oldest": {"type": ["string", "null"], "description": "The oldest day kept, YYYY-MM-DD."},
                              "bytes": {"type": "integer", "description": "What every log the limits cover takes now."},
                              "files": {"type": "integer"}, "keep_days": {"type": "integer"}, "max_bytes": {"type": "integer"}}}
APP_LIMITS = {"type": "object", "required": ["available", "driver", "max_size", "max_file", "per_app", "capped", "uncapped"],
              "description": "The apps' own logs, which Docker keeps: the limit most containers have (from daemon.json or their "
                             "Compose file), read from Docker. Starboard cannot change daemon.json.",
              "properties": {"available": {"type": "boolean", "description": "false when Starboard cannot reach Docker."},
                             "driver": {"type": "string"}, "max_size": {"type": "string", "description": "Such as 10m."},
                             "max_file": {"type": "string"}, "per_app": {"type": ["integer", "null"], "description": "The most bytes each container keeps."},
                             "capped": {"type": "integer"}, "uncapped": {"type": "array", "items": {"type": "string"},
                                                                         "description": "Containers whose log has no size limit."}}}
LIMITS = {"keep_days": {"type": "integer", "enum": [7, 14, 30, 60, 90, 180, 365], "description": "Days kept (30 by default)."},
          "max_mb": {"type": "integer", "enum": [10, 25, 50, 100, 250, 500], "description": "The most every log may take together, in MB (50 by default)."},
          "show_lines": {"type": "integer", "enum": [50, 100, 200, 500, 1000], "description": "The most lines System, Logs, Copy and Download give, the newest ones (200 by default). Added in 1.8.0 (DASH-534); it does not change what is stored."},
          "alerts_only": {"type": "boolean", "description": "Only errors and warnings in System, Logs, Copy and Download, leaving out information and detail (off by default). Added in 1.8.0 (DASH-534)."}}
LOG_LIMITS = {"type": "object", "required": ["keep_days", "max_mb", "keep_days_choices", "max_mb_choices", "summary", "covers"],
              "properties": {**LIMITS, "keep_days_choices": {"type": "array", "items": {"type": "integer"}},
                             "show_lines_choices": {"type": "array", "items": {"type": "integer"}, "description": "The choices for show_lines (50, 100, 200, 500, 1000)."},
                             "max_mb_choices": {"type": "array", "items": {"type": "integer"}}, "summary": LOG_SUMMARY,
                             "covers": {"type": "array", "items": {"type": "string"}}, "apps": APP_LIMITS,
                             "removed": {"type": "integer", "description": "After a change: files removed by the new limits."},
                             "freed": {"type": "integer"}}}
spec["paths"].update({
    "/api/v1/logs/limits": {
        "get": {"operationId": "getLogLimits", "summary": "How long Starboard keeps its logs, the most they may take, and what they take now", "tags": ["System"],
                "description": LOGS_NOTE + " Whichever limit comes first removes the oldest days: when a new day starts, when the limits change "
                               "and when the size written passes the limit. They cover Starboard's own log (with its jobs, updates and plug-ins' "
                               "lines), the API's audit log and the last Starboard update's log. apps is the apps' own limit, read from Docker.",
                "responses": ok(LOG_LIMITS)},
        "post": write(LOG_LIMITS, "Change how long Starboard keeps its logs and the most they may take", "setLogLimits", "System",
                      body={"type": "object", "properties": LIMITS}) | {
            "description": LOGS_NOTE + " The same choices as Settings, General, Backup/Logs. Older days go at once; the answer says how many."}},
    "/api/v1/logs/delete": {"post": write(
        {"type": "object", "required": ["removed", "emptied", "freed", "summary"],
         "properties": {"removed": {"type": "integer"}, "emptied": {"type": "integer", "description": "Today's file and the audit log, emptied so logging goes on."},
                        "freed": {"type": "integer"}, "summary": LOG_SUMMARY}},
        "Delete all logs", "deleteLogs", "System",
        body={"type": "object", "required": ["confirm"], "properties": {"confirm": {"const": True, "description": "Must be true."}}}) | {
        "description": LOGS_NOTE + " Every log the limits cover goes, apart from today's file and the audit log, which are emptied, and the "
                       "last update's log while an update runs. Cannot be undone. The first new line says the key deleted them; this "
                       "write is in the audit log too. The apps' own logs (Docker's) are not touched."}},
})
TESTED = {"type": ["object", "null"], "description": "The last Test connection: ok, each step (folder, write, read, remove) done or not, "
           "free bytes there when the place says, when (at, seconds since 1970), and error in words when it did not work. An error "
           "that starts SIGNIN| means the cloud service no longer accepts the sign-in: sign in again on the page.",
           "properties": {"ok": {"type": "boolean"}, "steps": {"type": "array", "items": ANY}, "free": {"type": ["integer", "null"]},
                          "at": {"type": "number"}, "error": {"type": "string"}, "where": {"type": "string"}, "count": {"type": ["integer", "null"]}}}
spec["paths"]["/api/v1/backup/copies"] = {"get": {
    "operationId": "getBackupCopies", "summary": "Where copies of full backups go off this computer, the last copy and the last Test connection",
    "tags": ["System"], "description": "Never a password, key or rclone config: only whether the place is set up and where.",
    "responses": ok({"type": "object", "required": ["kind"], "properties": {
        "kind": {"type": "string", "enum": ["off", "disk", "smb", "nfs", "rclone"]}, "where": {"type": "string"}, "where_words": {"type": "string"},
        "service": {"type": "string", "description": "The cloud service the wizard connected (drive, onedrive, dropbox, b2, s3, webdav, sftp), or empty"},
        "keep": {"type": "integer"}, "status": ANY, "tested": TESTED,
        "destinations": {"type": "array", "description": "Added in 1.9.0: every place a backup can go, each with its own switch (enabled), keep counts, last copy (status, state_word, shape) and last test. The fields above are the first place's.",
                         "items": {"type": "object", "properties": {"id": {"type": "string"}, "title": {"type": "string"}, "kind": {"type": "string"},
                                                                    "kind_words": {"type": "string"}, "enabled": {"type": "boolean"}, "where": {"type": "string"},
                                                                    "where_words": {"type": "string"}, "service": {"type": "string"}, "keep": {"type": "integer"},
                                                                    "keep_settings": {"type": "integer"}, "status": ANY, "tested": TESTED,
                                                                    "state_word": {"type": "string"}, "shape": {"type": "string"}}}},
        "safe": {**ANY, "description": "Added in 1.9.0: safe is true only when every place that is activated has copied the newest full backup and read it back; words says it, places says which."},
        "settings_zip": {**ANY, "description": "Added in 1.9.0: the key for the server settings copies (set, never the key) and each place's last settings copy."}}})}}
spec["paths"]["/api/v1/backup/settings-copy"] = {"post": write(
    {"type": "object", "required": ["accepted"], "properties": {"accepted": {"type": "boolean"}, "status": {"type": "string"}, "settings_zip": ANY}},
    "Copy the server's settings zip to every place that is activated, encrypted with rclone crypt first, as the server's own backup job asks after writing it (1.9.0). Body: name, the zip's file name in the server backups folder (the newest when left out). Never sent without a key.",
    "copyServerSettings", "System", status="202", extra={"409": {"$ref": "#/components/responses/Problem"}})}
spec["paths"]["/api/v1/backup/copies/test"] = {"post": write(
    {"type": "object", "required": ["ok", "tested"], "properties": {"ok": {"type": "boolean"}, "tested": TESTED}},
    "Test connection: reach the place, write a small file, read it back, remove it and check the room, as the page's button does",
    "testBackupCopies", "System", extra={"409": {"$ref": "#/components/responses/Problem"}})}
spec["components"]["parameters"]["idempotency"] = {
    "name": "Idempotency-Key", "in": "header", "required": False, "schema": {"type": "string", "pattern": "^[A-Za-z0-9._:-]{1,100}$"},
    "description": "Send the same value again to get the first answer back without doing it twice. Kept for 24 hours."}

# Added in 1.7.0 (DASH-464): AI assistants over MCP. One POST address taking JSON-RPC 2.0; read keys only.
RPC_ID = {"type": ["string", "integer"]}
spec["components"]["schemas"]["JsonRpcRequest"] = {
    "type": "object", "required": ["jsonrpc", "method"],
    "properties": {"jsonrpc": {"type": "string", "enum": ["2.0"]}, "id": RPC_ID,
                   "method": {"type": "string", "description": "initialize, ping, tools/list or tools/call; or a notification, such as notifications/initialized, with no id."},
                   "params": ANY}}
spec["components"]["schemas"]["JsonRpcResponse"] = {
    "type": "object", "required": ["jsonrpc", "id"],
    "properties": {"jsonrpc": {"type": "string", "enum": ["2.0"]}, "id": {"type": ["string", "integer", "null"]},
                   "result": {**ANY, "description": "initialize: protocolVersion, capabilities, serverInfo and instructions. tools/list: tools. "
                                                    "tools/call: content, structuredContent and isError."},
                   "error": {"type": "object", "required": ["code", "message"],
                             "properties": {"code": {"type": "integer"}, "message": {"type": "string"}}}}}
spec["paths"]["/api/v1/mcp"] = {"post": {
    "operationId": "mcp", "summary": "AI assistants: the Model Context Protocol, read-only tools about the media server", "tags": ["AI assistants"],
    "description": "The MCP Streamable HTTP transport: send one JSON-RPC 2.0 message as JSON (no batches) and get one JSON answer, "
                   "never a stream. It takes initialize, ping, tools/list and tools/call; notifications, with no id, get 202 and no body. "
                   "Off until the owner activates AI assistants in Settings, Security, API keys (403 mcp_off). Only a Read only key "
                   "(403 read_key_needed). tools/list gives the tools the key's scopes cover: search_library (library), recently_added, "
                   "coming_up and now_playing (media), downloads_in_progress and download_problems (downloads), requests (requests), "
                   "app_health (apps) and disk_space (system). Each reads the same as its /api/v1 route and changes nothing. "
                   "Each tools/call is written to the audit log. An Origin header from another site is refused (403 origin_refused). "
                   "MCP versions 2025-06-18 and 2025-03-26; send MCP-Protocol-Version after initialize.",
    "parameters": [{"name": "MCP-Protocol-Version", "in": "header", "required": False, "schema": {"type": "string", "enum": list(mcp.PROTOCOL_VERSIONS)},
                    "description": "The version initialize agreed."}],
    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/JsonRpcRequest"},
                                                                "example": {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}}}},
    "responses": {"200": {"description": "The JSON-RPC answer: result, or error with a JSON-RPC code such as -32601 for a method Starboard does not take.",
                          "headers": {"X-Request-Id": {"$ref": "#/components/headers/X-Request-Id"}},
                          "content": {"application/json": {"schema": {"$ref": "#/components/schemas/JsonRpcResponse"}}}},
                  "202": {"description": "A notification was taken. No body."},
                  "400": {"description": "Not JSON, or not one JSON-RPC 2.0 message (a JSON-RPC error), or an MCP version Starboard does not speak (a problem).",
                          "content": {"application/json": {"schema": {"$ref": "#/components/schemas/JsonRpcResponse"}},
                                      "application/problem+json": {"schema": {"$ref": "#/components/schemas/Problem"}}}},
                  "401": {"$ref": "#/components/responses/Problem"}, "403": {"$ref": "#/components/responses/Problem"},
                  "405": {"$ref": "#/components/responses/Problem"}, "413": {"$ref": "#/components/responses/Problem"},
                  "429": {"$ref": "#/components/responses/Problem"}}}}

# Added in 1.8.0 (plug-in API 1.17): alerts from a plug-in, answered only to its own key (x-right: plugin).
spec["paths"]["/api/v1/plugin/alerts"] = {"post": write(
    {"type": "object", "required": ["ok", "sent"], "properties": {
        "ok": {"type": "boolean"},
        "sent": {"type": "boolean", "description": "false when it was already raised, there was nothing to clear, or alerts are off in Settings, General, Alerts"}}},
    "A plug-in raises or clears one of its alerts, sent through Starboard's own alerts", "sendPluginAlert", "Plug-ins",
    body={"type": "object", "required": ["key", "state"], "properties": {
        "key": {"type": "string", "pattern": "^[A-Za-z0-9._:-]{1,80}$", "description": "The plug-in's own name for the alert, such as check-router. Raised once until cleared."},
        "state": {"type": "string", "enum": ["raised", "cleared"]},
        "title": {"type": "string", "maxLength": 120, "description": "Required to raise. One line."},
        "message": {"type": "string", "maxLength": 500, "description": "Sent after the plug-in's name, such as On demand: Ping: no answer for 3 checks in a row."},
        "level": {"type": "string", "enum": list(api_v1.ALERT_LEVELS), "default": "problem"}}})
    | {"description": "Only the plug-in's own key, while the plug-in is active and its approved permissions include alerts:send: "
                      "any other key gets 404 not_found. The one write a plug-in's read-only key may do. An alert goes out once until "
                      "it is cleared, to where Starboard sends its own (ntfy, Gotify or a webhook), as the alert.raised and alert.cleared "
                      "events and in the log, and only while alerts are on. Up to 30 new alerts an hour for each plug-in (429 rate_limited "
                      "with Retry-After); raising one that is already raised does not count."}}
_alerts = spec["paths"]["/api/v1/plugin/alerts"]["post"]
_alerts["responses"].pop("403")  # a plug-in's key is never asked for manage
_alerts["requestBody"]["content"]["application/json"]["example"] = {
    "key": "check-router", "state": "raised", "title": "Router is not answering", "message": "Ping: no answer for 3 checks in a row.",
    "level": "problem"}

# Added in 1.12.0 (plug-in API 1.24, DASH-572): a hold on heavy work from a plug-in, answered only to its own key.
spec["paths"]["/api/v1/plugin/hold"] = {"post": write(
    {"type": "object", "required": ["ok", "held"], "properties": {
        "ok": {"type": "boolean"},
        "held": {"type": "boolean", "description": "Whether anything is held now, by this plug-in or another"},
        "reason": {"type": "string"}, "until": {"type": "integer", "description": "When the longest hold ends if it is not renewed, as epoch seconds"},
        "by": {"type": "string", "description": "The plug-in whose hold lasts longest"}}},
    "A plug-in holds Starboard's heavy automatic work while the computer runs on battery, or lets it go", "holdHeavyJobs", "Plug-ins",
    body={"type": "object", "required": ["on"], "properties": {
        "on": {"type": "boolean", "description": "true starts or renews the hold, false ends it"},
        "reason": {"type": "string", "maxLength": 80, "description": "One line shown to people, such as On battery. Defaults to On battery."},
        "minutes": {"type": "integer", "minimum": 1, "maximum": 30, "default": 10,
                    "description": "How long the hold lasts if it is not renewed. Ask again before it ends to keep it."}}})
    | {"description": "Only the plug-in's own key, while the plug-in is active and its approved permissions include power:hold: any other "
                      "key gets 404 not_found. While a hold lasts, Starboard does not start by itself its background jobs (Live TV, "
                      "watch history, listening progress, the automatic updates), its scheduled backups or other plug-ins' scheduled jobs, "
                      "and it pauses downloads as Download hours does, even when Download hours is off. Anything a person starts with a "
                      "click still runs. A hold ends by itself after minutes, so a plug-in that stops cannot hold for ever; what was due "
                      "starts at the next check after it ends, and downloads Starboard paused start again."}}
_hold = spec["paths"]["/api/v1/plugin/hold"]["post"]
_hold["responses"].pop("403")  # a plug-in's key is never asked for manage
_hold["requestBody"]["content"]["application/json"]["example"] = {"on": True, "reason": "On battery", "minutes": 10}


SAMPLES = {"id": "123", "name": "livetv"}
RUN_ID = "0123456789ab"  # an update run's id, for /api/v1/updates/runs/{id}


def sample(path):
    """A described path with a made-up value in each {name}, to match it against the route table."""
    if path.startswith("/api/v1/updates/runs/"):
        return path.replace("{id}", RUN_ID)
    return re.sub(r"\{(\w+)\}", lambda m: SAMPLES.get(m.group(1), "abc"), path)


def with_scopes(spec):
    """Puts x-scope (and x-right on writes) after tags in each operation the API answers with a key, from api_v1's
    route tables: routes() for GET, actions() for the rest."""
    reads = [(p, scope) for p, scope, *_ in api_v1.routes()]
    writes = [(p, method, scope) for p, method, scope, _ in api_v1.actions()]
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            if op.get("security") == []:
                continue
            if path == mcp.PATH:  # each tool has its own scope; the address takes read keys only
                scope, right = None, "read"
            elif method == "get":
                scope = next((sc for p, sc in reads if re.match(p, sample(path))), None)
            else:
                scope = next((sc for p, m, sc in writes if m == method.upper() and re.match(p, sample(path))), None)
            if scope in api_v1.PLUGIN_PERMISSION:  # 1.8.0: a plug-in's own key, by its approved permission, not a scope
                scope, right = None, "plugin"
            elif path != mcp.PATH:
                right = "manage"
            ordered = {}
            for k, v in op.items():
                ordered[k] = v
                if k == "tags":
                    ordered["x-scope"] = scope
                    if method != "get":
                        ordered["x-right"] = right
            ops[method] = ordered
    return spec


text = json.dumps(with_scopes(spec), indent=1) + "\n"
out = os.path.join(ROOT, "starboard", "openapi.json")
if "--check" in sys.argv:
    with open(out, encoding="utf-8") as f:
        if f.read() != text:
            sys.exit("starboard/openapi.json is out of date: run python3 tools/make_openapi.py and commit it")
    print(len(spec["paths"]), "paths, description up to date")
else:
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(len(spec["paths"]), "paths")
