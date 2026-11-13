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

## too_large

**413.** The body is larger than 64 KB. Send a JSON object of up to 64 KB.

## not_set_up

**409.** What the address needs is not set up yet, such as Reelix for the Library and history. `detail` says what to
add, in **Settings**, **Manage apps**.

## app_failed

**502.** An app Starboard asked, such as Reelix, Seerr or a download app, did not answer or said no. `detail` has
what it said. Try again later, or open the app.

## too_many_streams

**503.** 8 event streams are open already. Close one, or wait the seconds in `Retry-After`.
