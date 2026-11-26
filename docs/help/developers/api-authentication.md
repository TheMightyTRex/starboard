[Help centre](../README.md) · Developers
<!-- help: dev / api -->

# Authentication and keys

Every call to Starboard's API needs a key of its own, sent in a header. This page explains what a key is, what it
can read, how long it lasts, and the limits on it. To make one and use it, read [API quickstart](api-quickstart.md).

## What a key is

- A key has the form `sb_read_a1b2c3_` or `sb_manage_a1b2c3_` and a long secret: `sb`, its right, its id (six
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

Starboard does not read a key anywhere else, such as in the address (`?key=...`), and refuses the call with
[`key_needed`](../../api/errors.md#key_needed). Addresses end up in logs and browser history, and a header does not.

## Rights and scopes

| Right | Shown as | What it allows |
|---|---|---|
| `read` | **Read only** | Read what the API offers |
| `manage` | **Read and manage** | Read, and the everyday actions of the pages: approve or decline a request, remove or block a download, pause or resume downloads, build a Library tab again, check for container updates, run a Jellyfin job and send a test alert. With **Updates** ticked, also update Starboard, Reelix, an app or a plug-in, and roll a plug-in back (API 1.2.0) |

Every address that changes something is a `POST`, marked **Needs:** `manage` in the [API reference](api-reference.md).
A read key gets `403` [`right_needed`](../../api/errors.md#right_needed) there.

No key, whatever its right, can do any of these things:

- change settings, keys or plug-in choices
- add or remove plug-ins
- change the install
- take over your apps
- restore a backup
- use Reelix's admin password
- make Starboard call an address the key gives

The one change to the install that a key can make is an update, and only with **Updates** ticked. It updates to the
version Starboard already found, with the same backup, health check and way back as the pages. The other actions stay
with a person signed in to Starboard. Read [What the API covers](api-coverage.md) for every page action and its right.

A key's scopes narrow what it reads and does. A key with no scopes reaches everything its right allows. In
**Settings**, **Security**, **What it may read**, tick only what the app or script needs. Plug-in keys only read, with
the scopes of the read permissions the person approved. Read
[The plug-in's API key](plugin-api-reference.md#the-plug-ins-api-key).

| Scope | Shown as | What it covers |
|---|---|---|
| `apps` | **Apps** | `/apps`, `/apps/{id}`, `/status`, `/health`, `/uptime`, `/app-updates`, `/numbers` and `/containers`; checking for container updates |
| `downloads` | **Downloads** | `/downloads`, `/downloads/issues`, `/transfer`, `/download-hours` and `/history`; download actions and download hours |
| `media` | **Media** | `/recent`, `/playing`, `/calendar` and `/extras`; running a Jellyfin or Audiobookshelf job |
| `library` | **Library** | `/library`, `/library/search` and `/library/status`; building a tab again |
| `requests` | **Requests** | `/requests`; approving and declining |
| `system` | **System** | `/system`, `/system/history` and `/version`; sending a test alert |
| `logs` | **Logs** | `/logs`: Starboard's log, with addresses, names and keys taken out, and `/logs/limits`. With Read and manage, also change the log limits and delete all logs. Only a key with `logs` ticked has it: a key with no scopes does not |
| `updates` | **Updates** | `/updates`, `/updates/runs` and `/updates/runs/{id}`; with **Read and manage**, starting an update and rolling a plug-in back. Only a key with `updates` ticked has it: a key with no scopes does not. API 1.2.0 |

`/api/v1/` and `/me` work with any key. `/openapi.json` needs no key. `/events` works with any key, and each event
reaches only the keys whose scopes cover it.

A key asking for something outside its scopes gets `404` [`not_found`](../../api/errors.md#not_found), not `403`,
so a key cannot find out what exists beyond what it may read.

Whatever the key, the API never sends a secret. An app's API key shows only as `api_key_set`, `true` or `false`,
and the API leaves out the VPN's own internet address.

## Changes, safely

- Send the body as JSON, of up to 64 KB, such as `{"action": "pause"}`. A larger one gets `413`
  [`too_large`](../../api/errors.md#too_large).
- Send an `Idempotency-Key` header, such as a new random value for each action, to make a retry safe. If you send
  the same key and value within 24 hours, you get the first answer again, with `Idempotent-Replayed: true`, and
  Starboard does nothing twice.
- Work that takes a while, such as building a Library tab, answers `202` with `status`, the address to read to find out
  how it went.
- Starboard writes every change made with a key to the audit log, with the key's id, the address and the answer.

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
`Cache-Control` says it stays fresh. Use `If-None-Match` with the last `ETag`, so an answer that has not changed
has no body to read. Read [API quickstart](api-quickstart.md#5-ask-again-only-when-it-changed).

## The audit log

Starboard writes a line to its audit log, `data/logs/audit.jsonl`, in these cases:

- each time someone makes or revokes a key;
- each time a key changes something (`api_write`, with the key's id, the address and the answer's status);
- each time Starboard refuses a wrong key, with the address it came from;
- each time someone adds, updates, rolls back, activates or removes a plug-in;
- each sign-in step beyond the password: the two-step code activated or off, a code or recovery code used or refused,
  single sign-on set up, tested, activated or off, and each sign-in it allowed or refused, with the address it came
  from (`totp_enabled`, `sign_in_code_ok`, `sign_in_code_failed`, `sign_in_recovery_code_used`, `sso_configured`,
  `sign_in_sso`, `sso_refused` and the like).

The log never holds a key or a password. It keeps 5 files of about 1 MB each, and counts towards the log limits in
Settings, General, Backup/Logs. Its older files go with the oldest days, and Delete all logs empties it (the
delete itself is its next line).

## The calendar address is not a key

The Coming up page makes an address for calendar apps, `/calendar.ics?token=sbcal_...`, because a calendar app
cannot send a header. Its token is not an API key:

- It opens that one iCalendar file and nothing else. The API, the pages and the sign-in never accept it, and an API
  key or a signed-in browser cannot open the file.
- There is one at a time. Starboard keeps only its SHA-256 fingerprint and shows it once; a new one stops the old
  one at once.
- A refused token counts towards the same lockout per address as a refused key. A good one shares the limit of 120
  a minute, and the file is kept for 15 minutes, so asking more often reads nothing new.
- Making or stopping it is written to the audit log as `calendar_address_made` or `calendar_address_stopped`, and a
  refused one as `calendar_refused`.

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

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
