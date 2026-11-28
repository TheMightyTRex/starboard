# Starboard API errors

Every error from `/api/v1` is an RFC 9457 problem: `type` links to its entry below, `code` is the same word for
scripts, `title` and `detail` say what happened, and `instance` is the request id, also in the `X-Request-Id` header.

## key_needed

**401.** No key was sent, or the key is wrong, revoked or out of date. Make a key in Starboard, **Settings**,
**Security**, **API keys**, and send it as `Authorization: Bearer sb_read_...`. Keys in the address are refused.

## too_many_attempts

**429.** Too many refused keys from your address. Wait 15 minutes (`Retry-After` says how long), then send a key
that works.

## rate_limited

**429.** More than 120 requests a minute with one key. Wait the seconds in `Retry-After`. A `304` counts as a
request too, but it has no body to read, so send `If-None-Match` with the last `ETag` and ask no more often than
`Cache-Control` says.

## not_found

**404.** No such route, no such object, or nothing there for this key's scopes.

## bad_request

**400.** A value is wrong, such as `limit` outside 1 to 200 or a `cursor` Starboard did not give. `detail` says which.

## method_not_allowed

**405.** That address does not take that method, such as a `POST` to an address that only reads. `Allow` lists
what works.

## right_needed

**403.** The key only reads, and this address changes something. Make a key with **Read and manage** in
**Settings**, **Security**, **API keys**, with only the scopes it needs.

## gone

**410.** This address was removed after its notice period. `detail` names what replaces it, and a `Link` header points to
the page about the change. Before it was removed, every answer from it carried `Deprecation` and `Sunset` headers, and
`GET /api/v1/` listed it under `deprecations`.

## too_large

**413.** The body is larger than 64 KB. Send a JSON object of up to 64 KB.

## not_set_up

**409.** What the address needs is not set up yet, such as Reelix for the Library and history. `detail` says what to
add, in **Settings**, **Manage apps**.

## update_running

**409.** Another update is running (API 1.2.0). Starboard runs one update at a time. Read `/api/v1/updates` to see
which, and try again once its run has finished.

## cannot_update

**409.** Starboard cannot do that update or roll back now (API 1.2.0). `detail` says why, for example that no newer
version is known yet (look for app updates first with `POST /api/v1/containers/check`), that the app was not started
by Docker Compose, or that Starboard and the apps go back by themselves and only a plug-in can be rolled back later.

## app_failed

**502.** An app Starboard asked, such as Reelix, Seerr or a download app, did not answer or said no. `detail` has
what it said. Try again later, or open the app.

## too_many_streams

**503.** 8 event streams are open already. Close one, or wait the seconds in `Retry-After`.

## mcp_off

**403.** AI assistants cannot connect to `/api/v1/mcp` yet (API 1.7.0). The owner turns them on in Starboard,
**Settings**, **Security**, **API keys**, **AI assistants**. Nothing is shared until then.

## read_key_needed

**403.** `/api/v1/mcp` takes only a key made with **Read only** (API 1.7.0). Make one for the assistant in
**Settings**, **Security**, **API keys**, with only the scopes it needs.

## origin_refused

**403.** The request came from a web page on another site (its `Origin` header names a different address), which
`/api/v1/mcp` never answers (API 1.7.0). Connect the assistant from an app or a terminal, not from a web page.
