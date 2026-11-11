"""Writes starboard/openapi.json, the description of the public API (DASH-274). Run after changing a route."""
import json
import os

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
    "info": {"title": "Starboard API", "version": "1.1.0",
             "description": "Read only for now. Make a key in Starboard: Settings, Security, API keys. Send it as Authorization: Bearer sb_read_... "
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
        "securitySchemes": {"key": {"type": "http", "scheme": "bearer", "description": "A Starboard API key, sb_read_..."}},
        "parameters": page,
        "headers": {"ETag": {"schema": {"type": "string"}, "description": "Send it back in If-None-Match."},
                    "X-Request-Id": {"schema": {"type": "string"}, "description": "Yours, or one Starboard made; also in problem.instance."}},
        "responses": {"Problem": {"description": "RFC 9457 problem details.",
                                  "content": {"application/problem+json": {"schema": {"$ref": "#/components/schemas/Problem"}}}}},
        "schemas": {
            "Root": {"type": "object", "required": ["api_version", "starboard_version", "links"],
                     "properties": {"api_version": {"type": "string"}, "starboard_version": {"type": "string"}, "links": {"type": "object"}}},
            "Key": {"type": "object", "required": ["id", "name", "right", "scopes", "created_at", "prefix"],
                    "properties": {"id": {"type": "string"}, "name": {"type": "string"}, "right": {"type": "string", "enum": ["read"]},
                                   "scopes": {"type": "array", "items": {"type": "string", "enum": ["apps", "downloads", "media", "system"]}},
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
open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "starboard", "openapi.json"), "w").write(json.dumps(spec, indent=1) + "\n")
print(len(spec["paths"]), "paths")
