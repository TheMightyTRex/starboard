[Help centre](../README.md) · Developers

# API changelog

What changed in Starboard's API and in the plug-in API, newest first. Each entry is tagged Added, Changed,
Deprecated, Removed, Fixed or Security. Within version 1, changes only add: nothing you rely on is taken away
without warning. A field that will go is marked deprecated first and removed no sooner than 6 months later, in
the next major version.

## Two version numbers

- **Starboard's API** (`/api/v1`): its description, `starboard/openapi.json`, has `info.version`, and
  `GET /api/v1/` answers `api_version`.
- **The plug-in API**: `API_VERSION` in `starboard/plugins.py`. A plug-in names the versions it works with in
  `starboard_api`. Read [What each API version added](plugin-manifest-reference.md#what-each-api-version-added).

## Plug-in API 1.5.0, 12 November 2026

- **Added:** a setting may have a `group`. Each group is its own section of the plug-in's page in Settings.
- **Added:** a choice may be `{"value": ..., "label": ...}`, so people choose by name. `settings.json` still holds
  the value.
- **Changed:** the plug-in's page follows Starboard's settings patterns. Numbers save as soon as they change,
  the plug-in's buttons are in an Actions section, and nothing shows a toast for a saved setting.
- A manifest that uses either needs `">=1.5 <2.0"` in `starboard_api`. An older Starboard refuses it.

## Plug-in API 1.6.0, 12 November 2026

- **Added:** the `reelix:key` permission, with Reelix's address and key in `/run/starboard/reelix.json`.
- **Added:** the `usenet:servers` permission, with the active news servers from NZBGet or SABnzbd in
  `/run/starboard/usenet.json`. Both are high risk and shown as new in an update's warning.

## Plug-in API 1.4.0, fixes, 12 November 2026

- **Fixed:** what a plug-in reads comes as the folder `/run/starboard`, readable by any container user. Before,
  only a container running as Starboard's own user could read it, and a running plug-in kept the settings it
  started with. Older plug-ins change over when Starboard starts.
- **Fixed:** a button without an `id` runs. It is known by its place in the list.
- **Fixed:** `health` is asked by Starboard for every plug-in, not only those built into Starboard.
- **Fixed:** `start: when_needed` and `idle_stop_minutes` work, for the first container. Read
  [Resting when idle](plugin-api-reference.md#resting-when-idle).
- **Added:** **Update from an address** on a plug-in's own page, in **Versions**.

## Starboard API, description 1.0.0 again, 12 November 2026

- **Fixed:** the description's `info.version` is 1.0.0 again, the same as `api_version`. It became 1.1.0 by
  mistake on 11 November. A test now keeps them the same.
- **Added:** each route in the description has `x-scope`, the scope a key needs for it (`null` for none).

## Plug-in API 1.4.0, 12 November 2026

- **Added:** settings may be `required`, and a plug-in may set `setup_required`. Until it is set up, it is in the
  `needs-setup` state and cannot be activated.
- **Added:** `notices`, `p2p` and `adult`, shown with the install warning.
- **Added:** `events`: `item.added`, `download.finished`, `app.down`, `app.up` and `playback.started`, sent as a
  POST to `/events`. Each needs the read permission that covers what it tells.
- **Added:** `jobs`, up to eight, run by Starboard's clock: `daily`, `every_hours` or `at_start`, with
  `time_limit_minutes` and `quiet_hours`. They show in **System**, then **Jobs**.
- **Added:** card `refresh_minutes`, from 1 to 1440.
- **Added:** catalogue versions, each with `starboard_api` and `manifest_sha256`. Starboard offers the newest version
  that fits, and refuses a manifest whose SHA-256 does not match.
- **Added:** **Update to** a newer version and **Roll back** to the one before, and the `not-supported` and
  `failed` states with one button each.
- **Added:** catalogues added from a link, up to 10.

## Plug-in API 1.3.0, 12 November 2026

- **Added:** a `folder` setting is a folder inside the media folders the plug-in mounts (`media:ro` or
  `media/<one folder>`), chosen with Browse. A `folder` setting without such a mount is refused.

## Plug-in API 1.2.0, 12 November 2026

- **Added:** styles may also set card, button, border, tab, header, side menu and chip styles.
- **Changed:** a plug-in may list up to 32 styles, up from 16.

## Plug-in API 1.1.0, 11 November 2026

- **Added:** styles may set more colours (status, side menu, panel, chart and logo), a heading font and weight,
  the focus width, and two more shadows.

## Starboard API, description 1.1.0, 11 November 2026

- **Changed:** the description's `info.version` became 1.1.0, released with plug-in API 1.1. No address or answer
  changed, and `GET /api/v1/` still answers `api_version` 1.0.0.

## Starboard API 1.0.0, 10 November 2026

- **Added:** version 1 of the API, read only, at `/api/v1`: `/`, `/me`, `/openapi.json`, `/apps`, `/apps/{id}`,
  `/status`, `/health`, `/downloads`, `/recent`, `/playing` and `/system`.
- **Added:** keys of its own, `sb_read_...`, made and revoked in **Settings**, **Security** with the password,
  shown once, kept only as SHA-256, with optional scopes and an end date.
- **Security:** keys are read only from the `Authorization: Bearer` header. Wrong keys count towards the sign-in
  lockout for each address, and every key made, revoked or refused is written to the audit log.
- **Added:** problem details for errors, `limit` and `cursor` for lists, `ETag` and `304`, 120 requests a minute
  for each key with `RateLimit` headers, and `X-Request-Id` on every answer.
- **Fixed:** each error's `type` links to its entry in the [list of API errors](../../api/errors.md).

## Plug-in API 1.0.0, 10 November 2026

- **Added:** the manifest, version 1, with its JSON Schema and a check that says what is wrong.
- **Added:** permissions in plain words with their risk, and an API key for each plug-in with exactly the scopes of
  its read permissions.
- **Added:** the Compose file Starboard writes for each plug-in, with defaults the plug-in cannot change: read
  only, no extra rights, not root, memory and processor limits, its own network and only its own folders.
- **Added:** settings, cards (`stat`, `list` and `status`), actions, `health`, `needs` and styles, and the plug-in
  tester.
- **Added**, 11 November 2026: `custom` settings, a list the plug-in describes and Starboard draws.

## Find out more

- [Plug-in manifest reference](plugin-manifest-reference.md)
- [API reference](api-reference.md)
- [API quickstart](api-quickstart.md)
- [Plug-in API reference](plugin-api-reference.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
