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
from starboard import api_v1  # noqa: E402

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
                     "properties": {"api_version": {"type": "string"}, "starboard_version": {"type": "string"}, "links": {"type": "object"}}},
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
                                                                   "now": {"type": "array", "items": ANY}, "errors": {"type": "array", "items": ANY}}}
CONTAINERS = {"type": "object", "required": ["available", "items"],
              "properties": {"available": {"type": "boolean"}, "checked_at": {"type": ["number", "null"]}, "items": {"type": "array", "items": ANY},
                             "next_cursor": {"type": ["string", "null"]}}}

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
                                       "parameters": P + [query("q", {"type": "string", "minLength": 1, "maxLength": 120}, "What to look for.", True)],
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
    "/api/v1/containers/check": {"post": write(CONTAINERS, "Look for newer images of the apps' containers now", "checkContainers", "Apps")},
    "/api/v1/version": {"get": {"operationId": "getVersion", "summary": "Starboard's version, and the newest release when looking for new versions is active", "tags": ["System"],
                                "responses": ok({"type": "object", "required": ["current"],
                                                 "properties": {"current": {"type": "string"}, "latest": {"type": ["string", "null"]},
                                                                "repo": {"type": ["string", "null"]}, "since": {"type": ["number", "null"]}}})}},
    "/api/v1/system/history": {"get": {"operationId": "getSystemHistory", "summary": "Processor, memory and network over the last hours", "tags": ["System"],
                                       "parameters": [query("hours", {"type": "string", "enum": ["1", "6", "24"], "default": "1"}, "How many hours.")],
                                       "responses": {**ok({"type": "object", "required": ["hours", "interval", "points"],
                                                           "properties": {"hours": {"type": "integer"}, "interval": {"type": "integer"},
                                                                          "points": {"type": "array", "items": ANY}}}),
                                                     "400": {"$ref": "#/components/responses/Problem"}}}},
    "/api/v1/alerts/test": {"post": write(OK_BODY, "Send a test alert to the channel set in Settings, Alerts", "testAlert", "System")},
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
                              "state": {"type": "string", "enum": ["waiting", "working", "done", "failed", "skipped", "not-needed"]},
                              "detail": {"type": "string"}}}
spec["components"]["schemas"]["UpdateRun"] = {
    "type": "object", "required": ["id", "target", "kind", "name", "action", "from", "to", "by", "state", "said", "started_at", "steps"],
    "properties": {"id": {"type": "string"}, "target": {"type": "string"}, "kind": {"type": "string", "enum": ["starboard", "reelix", "app", "plugin"]},
                   "name": {"type": "string"}, "action": {"type": "string", "enum": ["update", "rollback"]},
                   "from": {"type": "string"}, "to": {"type": "string"}, "by": {"type": "string"},
                   "state": {"type": "string", "enum": ["running", "updated", "up-to-date", "went-back", "rolled-back", "refused", "failed"]},
                   "said": {"type": "string"}, "started_at": {"type": "string", "format": "date-time"},
                   "finished_at": {"type": ["string", "null"], "format": "date-time"}, "steps": {"type": "array", "items": UPDATE_STEP}}}
spec["components"]["schemas"]["UpdateTarget"] = {
    "type": "object", "required": ["id", "kind", "name", "current", "latest", "update_available", "can_update", "can_roll_back"],
    "properties": {"id": {"type": "string"}, "kind": {"type": "string", "enum": ["starboard", "reelix", "app", "plugin"]},
                   "name": {"type": "string"}, "current": {"type": "string"}, "latest": {"type": "string"},
                   "update_available": {"type": "boolean"}, "can_update": {"type": "boolean"}, "why": {"type": "string"},
                   "can_roll_back": {"type": "boolean"}, "roll_back_to": {"type": "string"}, "note": {"type": "string"}}}
RUN = {"$ref": "#/components/schemas/UpdateRun"}
STARTED = {"type": "object", "required": ["accepted", "run", "status"],
           "properties": {"accepted": {"type": "boolean"}, "run": RUN, "status": {"type": "string"}}}
UPDATES_NOTE = "Only for keys that ticked Updates: a key with no scopes does not have them."
spec["paths"].update({
    "/api/v1/updates": {
        "get": {"operationId": "listUpdates", "summary": "What can be updated: Starboard, Reelix, the other apps and the plug-ins", "tags": ["Updates"],
                "description": UPDATES_NOTE + " From what Starboard already knows (its release check, the last look for app updates and the "
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
spec["components"]["parameters"]["idempotency"] = {
    "name": "Idempotency-Key", "in": "header", "required": False, "schema": {"type": "string", "pattern": "^[A-Za-z0-9._:-]{1,100}$"},
    "description": "Send the same value again to get the first answer back without doing it twice. Kept for 24 hours."}


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
            if method == "get":
                scope = next((sc for p, sc in reads if re.match(p, sample(path))), None)
            else:
                scope = next((sc for p, m, sc in writes if m == method.upper() and re.match(p, sample(path))), None)
            ordered = {}
            for k, v in op.items():
                ordered[k] = v
                if k == "tags":
                    ordered["x-scope"] = scope
                    if method != "get":
                        ordered["x-right"] = "manage"
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
