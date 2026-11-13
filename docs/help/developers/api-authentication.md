[Help centre](../README.md) · Developers

# Authentication and keys

Every call to Starboard's API needs a key of its own, sent in a header. This page explains what a key is, what it
can read, how long it lasts, and the limits on it. To make one and use it, read [API quickstart](api-quickstart.md).

## What a key is

- A key looks like `sb_read_a1b2c3_` or `sb_manage_a1b2c3_` and a long secret: `sb`, its right, its id (six
  letters and numbers), then the secret.
- Starboard shows the key once, when it is made. It keeps only the key's SHA-256 fingerprint, so nobody can read
  the key back, Starboard included.
- Keys are separate from signing in. A key cannot open Starboard's pages, and the browser's sign-in cannot call
  the API.
- Starboard keeps up to 50 keys. Make one for each app or script, named after it, so you can revoke one without
  stopping the others.

## Send it in the header only

Send the key in the `Authorization` header, as `Bearer`, a space, then the key:

```bash
curl -s -H "Authorization: Bearer $STARBOARD_KEY" http://192.168.1.20:8095/api/v1/me
```

A key anywhere else, such as in the address (`?key=...`), is not read, and the call is refused with
[`key_needed`](../../api/errors.md#key_needed). Addresses end up in logs and browser history, and a header does not.

## Rights and scopes

| Right | Shown as | What it allows |
|---|---|---|
| `read` | **Read only** | Read what the API offers |
| `manage` | **Read and manage** | Read, and the everyday actions of the pages: approve or decline a request, remove or block a download, pause or resume downloads, build a Library tab again, look for container updates, run a Jellyfin job and send a test alert |

Every address that changes something is a `POST`, marked **Needs:** `manage` in the [API reference](api-reference.md).
A read key gets `403` [`right_needed`](../../api/errors.md#right_needed) there.

No key, whatever its right, can change settings, keys or plug-ins, change the install, take over or roll back,
restore a backup, use Reelix's admin password, or make Starboard call an address the key gives. Those stay with a
person signed in to Starboard. Read [What the API covers](api-coverage.md) for every page action and its right.

A key's scopes narrow what it reads and does. A key with no scopes reaches everything its right allows. In
**Settings**, **Security**, **What it may see**, tick only what the app or script needs. Plug-in keys only read, with
the scopes of the read permissions the person approved. Read
[The plug-in's API key](plugin-api-reference.md#the-plug-ins-api-key).

| Scope | Shown as | What it covers |
|---|---|---|
| `apps` | **Apps** | `/apps`, `/apps/{id}`, `/status`, `/health`, `/uptime`, `/app-updates`, `/numbers` and `/containers`; looking for container updates |
| `downloads` | **Downloads** | `/downloads`, `/transfer`, `/download-hours` and `/history`; download actions and download hours |
| `media` | **Media** | `/recent`, `/playing`, `/calendar` and `/extras`; running a Jellyfin or Audiobookshelf job |
| `library` | **Library** | `/library`, `/library/search` and `/library/status`; building a tab again |
| `requests` | **Requests** | `/requests`; approving and declining |
| `system` | **System** | `/system`, `/system/history` and `/version`; sending a test alert |
| `logs` | **Logs** | `/logs`: Starboard's log, with addresses, names and keys taken out. Only a key with `logs` ticked reads it: a key with no scopes does not |

`/api/v1/` and `/me` work with any key. `/openapi.json` needs no key. `/events` works with any key, and each event
reaches only the keys whose scopes cover it.

A key asking for something outside its scopes gets `404` [`not_found`](../../api/errors.md#not_found), not `403`,
so a key cannot find out what exists beyond what it may read.

Whatever the key, the API never sends a secret: an app's API key shows only as `api_key_set`, `true` or `false`,
and the VPN's own internet address is left out.

## Changes, safely

- Send the body as JSON, of up to 64 KB, such as `{"action": "pause"}`. A larger one gets `413`
  [`too_large`](../../api/errors.md#too_large).
- Send an `Idempotency-Key` header, such as a new random value for each action, to make a retry safe: the same key
  and value within 24 hours gets the first answer again, with `Idempotent-Replayed: true`, and nothing is done twice.
- Work that takes a while, such as building a Library tab, answers `202` with `status`, the address to read to see
  how it went.
- Every change made with a key is written to the audit log with the key's id, the address and the answer.

## Expiry

When you make a key, **Ends** sets when it stops working: **In 90 days**, **In a year** or **Never**. The list of
keys shows when each one ends. After that, it gets [`key_needed`](../../api/errors.md#key_needed). Make a new one to
carry on.

## Revoke a key

Go to **Settings**, then **Security**, then **API keys**, and select **Revoke** beside the key. Anything using it
stops working at once. Changing your password or signing out everywhere does not stop a key: revoke it.

The list shows when each key was last used, to the nearest minute, so you can find keys nothing uses any more.

## Rate limits

- Each key can make up to 120 requests a minute. Past that, the answer is `429`
  [`rate_limited`](../../api/errors.md#rate_limited), with `Retry-After`: the seconds to wait.
- Every answer has a `RateLimit` header saying how many requests are left, such as `"per-key";r=118;t=0`, and a
  `RateLimit-Policy` header, `"per-key";q=120;w=60`.
- Wrong keys count towards the same lockout as wrong passwords, for each address. Too many, and the address gets
  `429` [`too_many_attempts`](../../api/errors.md#too_many_attempts) for 15 minutes.

Every request counts, a `304` included. To stay well inside the limit, ask no more often than the answer's
`Cache-Control` says it stays fresh, and use `If-None-Match` with the last `ETag` so an answer that has not changed
has no body to read. Read [API quickstart](api-quickstart.md#5-ask-again-only-when-it-changed).

## The audit log

Starboard writes a line to its audit log, `data/logs/audit.jsonl`, each time a key is made or revoked, each time
a key changes something (`api_write`, with the key's id, the address and the answer's status), and each time a wrong
key is refused, with the address it came from. Plug-ins being added, updated, rolled back, activated
and removed are written there too. The log never holds a key or a password. It keeps 5 files of about 1 MB each.

## Keep keys safe

- Treat a key like a password. Keep it in an environment variable or a file only you can read, not in your code.
- Do not paste a key into a chat, a forum or an AI assistant. If one gets out, revoke it and make another.
- Starboard's API answers over plain `http` on your home network. To use it away from home, read
  [Use Starboard away from home safely](../guides/use-starboard-away-from-home.md).

## Find out more

- [API quickstart](api-quickstart.md)
- [API reference](api-reference.md)
- [What the API covers](api-coverage.md)
- [Connect an AI assistant](connect-an-ai-assistant.md)
- [List of API errors](../../api/errors.md)
- [Make an API key and use Starboard's API](../topics/use-starboards-api.md)
- [How Starboard keeps your server safe](../basics/how-starboard-keeps-you-safe.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
