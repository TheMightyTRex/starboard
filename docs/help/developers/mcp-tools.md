[Help centre](../README.md) · Developers
<!-- help: dev / api -->

# MCP tools

Starboard answers the Model Context Protocol (MCP) at `POST /api/v1/mcp`, from API 1.7.0. An AI assistant connects
with a **Read only** API key and gets tools that read the media server through the same routes as `/api/v1`. This page
describes the transport, the rules and each tool. For setting it up as an owner, read
[Let an AI assistant answer questions about your server](../topics/connect-an-ai-assistant-with-mcp.md).

## The transport

- **Streamable HTTP, without streams.** Send one JSON-RPC 2.0 message as the body of a `POST`, with
  `Content-Type: application/json`. A request gets one `application/json` answer. Starboard never answers with
  `text/event-stream` and never keeps a connection open, so `GET /api/v1/mcp` answers `405`.
- **Methods:** `initialize`, `ping`, `tools/list` and `tools/call`. Anything else answers the JSON-RPC error `-32601`.
- **Notifications** such as `notifications/initialized` and `notifications/cancelled`, which have no `id`, get `202`
  and no body.
- **No batches.** A JSON array answers `400` with the JSON-RPC error `-32600`. Not JSON at all answers `400` with
  `-32700`.
- **No session.** Starboard gives no `Mcp-Session-Id`: each request stands on its own, so a restart of Starboard does
  not break the assistant's connection.
- **Versions:** `2025-06-18` and `2025-03-26`. `initialize` agrees the version the client asks for when Starboard
  has it, or else the newest. After that, a client may send `MCP-Protocol-Version`; a version Starboard does not
  speak answers `400 bad_request`.
- **Size:** a message of up to 64 KB (`413 too_large`).

## The rules

| Rule | What happens otherwise |
|---|---|
| The owner has activated **Let AI assistants connect** in Settings, Security, API keys. | `403` [`mcp_off`](../../api/errors.md#mcp_off) |
| `Authorization: Bearer` and a key that works. Refused keys count towards the lockout for the address. | `401` [`key_needed`](../../api/errors.md#key_needed) |
| The key is **Read only**. | `403` [`read_key_needed`](../../api/errors.md#read_key_needed) |
| No `Origin` header, or one for the same address as `Host`. | `403` [`origin_refused`](../../api/errors.md#origin_refused) |
| A name Starboard answers to, as for every request. | `421` |
| Up to 120 requests a minute for each key, shared with the rest of the API. | `429` [`rate_limited`](../../api/errors.md#rate_limited) |

`tools/list` gives only the tools whose scope the key has. A key with no scopes has every tool except `read_logs`, which needs
**Logs**, and the update list in `list_apps_and_updates`, which needs **Updates**. Calling a tool the key does not have answers the JSON-RPC error `-32602`, the same as a tool
that does not exist.

Each `tools/call` writes one line to the audit log, `mcp_call`, with the key's id and name, the tool's name, `outcome`
(`done` or `error`), how many values were hidden and the size of the answer. The arguments and the answer are not
written. A tool that could not answer also writes `mcp_error` with its kind (`not_set_up`, `not_found`, `app_failed`
or `too_large`). A call that is refused, because the tool is unknown, is outside the key's scopes or the arguments do not
fit, writes `mcp_refused` (from API 1.14.0). The owner turning the address on or off writes `mcp_turned_on` or
`mcp_turned_off`, and a key's first use after a quiet spell of 6 hours writes `key_used`.

## What every answer is

From API 1.14.0, every answer is **data, not instructions**, and says so.

- **Hidden values.** Before an answer leaves Starboard, a masker hides what is private: keys, tokens and passwords (removed),
  email addresses, internet and home network addresses, host names, folders and files, and the names of the site, the
  server, the people and the folders Starboard knows are private. A hidden value becomes a marker such as `[address 1]`,
  the same number for the same value inside one answer. Version numbers, dates, counts and app names stay. `hidden` in
  the answer says how many of each kind were hidden, never what they were.
- **Marked untrusted.** Each answer starts with `untrusted: true`, `source` (such as `starboard:read_logs`) and a `notice`
  that says the text was written by apps and people and holds no instructions for the reader. These three are set by
  Starboard after the answer is built, so nothing inside an answer can replace them. A line of a log that says "ignore
  your rules" is a string inside `lines`, and stays one.
- **Bounded.** A log line is cut at 240 characters, a log answer at 200 lines, and any answer over 100,000
  bytes (`isError: true`).
- **Closed.** A tool takes only the arguments its schema lists: a count, a month, a choice of words, or a name made of
  letters, digits, dots, dashes and underscores that Starboard already knows. No tool takes a command, a path or a web
  address, and none reads a file or opens an address. A tool that is not on the list, or that the key's scopes do not
  cover, answers `-32602` and is written to the audit log.

## Answers from a tool

Each tool says `readOnlyHint: true` and changes nothing. A tool that worked answers `isError: false`, with the answer
twice: as `structuredContent`, which matches the tool's `outputSchema`, and as JSON text in `content`. A tool that
ran but could not answer, for example because Reelix is not added or an app did not answer, gives `isError: true`
and the reason as text. Wrong arguments answer the JSON-RPC error `-32602`, with what was wrong.

`limit` is from 1 to 50 and 20 when left out. `more` is `true` when there were more than `limit`. Each list holds
the same objects as the route it reads, with secrets taken out.

## The tools

| Tool | Scope | Arguments | Gives back | Reads |
|---|---|---|---|---|
| `search_library` | `library` | `query` (1 to 120 letters, required), `limit` | `items`, `more` | `GET /api/v1/library/search` |
| `recently_added` | `media` | `limit` | `items`, `more` | `GET /api/v1/recent` |
| `coming_up` | `media` | `month` (such as `2026-11`), `limit` | `items`, `more`, `errors` | `GET /api/v1/calendar` |
| `now_playing` | `media` | none | `configured`, `items` | `GET /api/v1/playing` |
| `downloads_in_progress` | `downloads` | `limit` | `items`, `more`, `errors` | `GET /api/v1/downloads` |
| `download_problems` | `downloads` | `limit` | `count`, `items`, `errors` | `GET /api/v1/downloads/issues` |
| `requests` | `requests` | `pending_only` (true or false), `limit` | `items`, `more`, `configured`, `pending` | `GET /api/v1/requests` |
| `app_health` | `apps` | none | `apps`, `problems`, `errors` | `GET /api/v1/status` and `GET /api/v1/health` |
| `disk_space` | `system` | none | `disks` | `GET /api/v1/system` |
| `read_logs` | `logs` | `source` (`starboard` or one app's name), `lines` (1 to 200, 50 by default), `level` (`all` or `problems`) | `log`, `newest_first`, `count`, `lines` | Starboard's log, or an app's through Docker |
| `list_apps_and_updates` | `apps` | none | `apps`, `app_reports`, `errors`, and `starboard_and_plugins` for a key with `updates` | `GET /api/v1/status`, `GET /api/v1/app-updates` and what Starboard knows of its own and its plug-ins' updates |
| `explain_error` | `apps` | `id` (12 letters and digits, from `app_health`) | `id`, `app`, `level`, `message`, `log_lines`, `log_lines_note`, `help_topic` | `GET /api/v1/health`, and Starboard's log for a key with `logs` |

- `read_logs` needs the `logs` scope, which a key has only when it is ticked. Each line has `time`, `level`, `area` and `text`, newest first. For an app's log the lines come from Docker and the app must be one Starboard runs; any other name answers `isError: true` without repeating the name.
- `explain_error` asks no model. `app_health` gives each problem an `id`, a short hash of the app and the message. `help_topic` has `title`, `page` and `url` of the help centre topic that explains the problem.
- `errors` lists the apps that did not answer, so a partial answer says what is missing.
- `download_problems` gives the same items as `GET /api/v1/downloads/issues`, without its Markdown.
- `app_health`: `apps` is whether each app answers; `problems` is what the apps report about themselves.
- `disk_space`: each disk has `label`, `total`, `used` and `free` in bytes, or `missing: true`.

## An example

```bash
curl -s -X POST "$STARBOARD_URL/api/v1/mcp" \
  -H "Authorization: Bearer $STARBOARD_KEY" -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "disk_space", "arguments": {}}}'
```

```json
{"jsonrpc": "2.0", "id": 1, "result": {
  "content": [{"type": "text", "text": "{\"disks\":[{\"label\":\"Media\",\"total\":4000000000000,\"used\":2500000000000,\"free\":1500000000000}]}"}],
  "structuredContent": {"disks": [{"label": "Media", "total": 4000000000000, "used": 2500000000000, "free": 1500000000000}]},
  "isError": false}}
```

## What is left for later

Tools that change something, such as approving a request or pausing downloads, are not offered. When they come,
each will wait for the owner to approve it in Starboard's page first, and need its own decision.

## Find out more

- [Let an AI assistant answer questions about your server](../topics/connect-an-ai-assistant-with-mcp.md)
- [Authentication and keys](api-authentication.md)
- [API reference: POST /api/v1/mcp](api-reference.md#post-apiv1mcp)
- [API changelog](api-changelog.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
