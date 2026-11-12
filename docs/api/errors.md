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

**405.** Version 1 of the API only reads for now. `Allow` lists what works.
