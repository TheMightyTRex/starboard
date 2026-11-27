[Help centre](../README.md) · Developers
<!-- help: dev / api -->

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

## Plug-in API 1.20.0 (not released yet), 26 November 2026

- **Changed:** a plug-in that this Starboard cannot run is now stopped when Starboard starts, and shows **Needs an update**
  (before, **Not supported**, and it kept running). It cannot run when its `starboard_api` leaves out this API, or when it
  uses a field, permission, card type, setting type, event or container option that no longer exists. Its settings, data
  and key are kept, the page says why in words, and **Check for an update** or **Roll back** work as before. No 1.x
  release removes anything, so this changes nothing for a plug-in that fits.
- **Added:** `first_sign_in`, a password Starboard makes for an app plug-in and shows once on its page, so the app does
  not start with a default one that everyone knows. The manifest names the sign-in name, the `{secret:name}` the app
  reads from its environment and a file the app's start-up writes once it has set the password. Starboard offers
  **Show the password** only after that file is there, asks for the Starboard password, shows it once and keeps only
  the date. Read [A first sign-in shown once](plugin-manifest-reference.md#a-first-sign-in-shown-once-first_sign_in).
- **Changed:** nothing a plug-in relies on. A plug-in that does not use it is drawn as before. Name `>=1.20` in
  `starboard_api` to use it, so an older Starboard offers the earlier version instead of one whose password nobody is shown.

## Plug-in API 1.19.0 (not released yet), 25 November 2026

- **Added:** `requires`, the system a plug-in needs, as a list of up to four needs: `"jellyfin"`, `"jellyfin only"`,
  `"plex or emby"`, `"reelix"`. Starboard shows it as a tag in words on the Catalogue, the plug-in's page, Manage and
  Ready to update, and says why when the system is not on this Starboard. An empty list says it needs nothing. Read
  [What it needs](plugin-manifest-reference.md#what-it-needs-requires).
- **Changed:** nothing a plug-in relies on. A manifest without `requires` gets its tag from the permissions it already
  asks for: `jellyfin:key`, `jellyfin:metadata` and `jellyfin:libraries` mean Jellyfin, `reelix:key` means Reelix and
  `usenet:servers` means SABnzbd or NZBGet. No plug-in is stopped, refused or failed because its system is missing.
- Version 1.18 is kept for the `power:hold` permission and the time setting type (DASH-572). Name `>=1.19` in
  `starboard_api` to use `requires`.

## Plug-in API 1.17.0, Starboard 0.31.0, 25 November 2026

- **Fixed:** a `sparkline` card may answer an empty list of `series`, with a `note` that says why, for a plug-in that is
  not set up yet. Before, Starboard refused it although the dashboard already showed the note.

## Plug-in API 1.17.0 and Starboard API 1.8.0 (not released yet), 20 November 2026

- **Added:** the `sparkline` card type. A card answers `series`, up to 8, each with a `title` and 1 to 96 `points`
  (numbers of 0 or more, with `null` for a gap), and an optional `unit` and `detail`, and a `note`. Starboard draws a
  small line for each series, hidden from screen readers, and the latest, lowest and highest value in words, which
  everyone reads. Read [Sparkline cards](plugin-api-reference.md#sparkline-cards-api-117).
- **Added:** the `alerts:send` permission (low risk, no key scope) and `POST /api/v1/plugin/alerts`. A plug-in raises
  and clears its own alerts with `key`, `state` (`raised` or `cleared`), `title`, `message` and `level`. Each is sent
  once until cleared, through the same channel, `alert.raised` and `alert.cleared` events and log as Starboard's own,
  and only while alerts are on. The answer is `{"ok": true, "sent": true}`, or `false` when nothing was sent. Only the
  plug-in's own key, while the plug-in is active and approved `alerts:send`; any other key gets `404 not_found`. Up to
  30 new alerts an hour for each plug-in, then `429 rate_limited` with `Retry-After`. Read
  [Sending alerts](plugin-api-reference.md#sending-alerts-api-117).
- **Added:** `GET /api/v1/logs/limits` answers `show_lines` (50, 100, 200, 500 or 1000; 200 by default), `show_lines_choices`
  and `alerts_only` (errors and warnings only), and `POST /api/v1/logs/limits` sets them: what System, Logs, Copy and
  Download show, not what is stored.
- **Changed:** in `openapi.json`, `x-right` may be `plugin`, for an address answered only to a plug-in's own key.
- Nothing was taken away: every earlier address and card answers as before. Name `>=1.17` in `starboard_api` to use
  either.

## Starboard API 1.7.0 (Starboard 0.23.0), 19 November 2026

- **Added:** `POST /mcp`, for AI assistants that speak the Model Context Protocol (MCP), over its Streamable HTTP
  transport: one JSON-RPC 2.0 message in, one JSON answer back, never a stream. It takes `initialize`, `ping`,
  `tools/list` and `tools/call`; a notification gets `202`. Off until the owner activates **AI assistants** in
  Settings, Security, API keys (`403 mcp_off`), and only with a **Read only** key (`403 read_key_needed`). Its tools
  only read, each through the same route and scope as the address it is named after, and each call is written to
  the audit log. Read [MCP tools](mcp-tools.md).
- **Added:** `links.mcp` in `GET /api/v1/`.
- Nothing was taken away: every earlier address answers as before.

## Plug-in API 1.16.0, Starboard 0.24.1, 19 November 2026

- **Changed:** a file streamed to a plug-in's `choices` path plus `/file` may be up to 100 MB, not 60 MB, so a
  plug-in can take larger files such as a TV channel's holding slide. A plug-in still refuses what is too big for it.

## Plug-in API 1.16.0 (Starboard 0.23.0 and 0.24.0), 19 November 2026

- **Added (Starboard 0.24.0):** custom pages that save in place, choose several and come in cards (19 November 2026). Starboard sends
  `X-Starboard-Can: partial,picker,cards` with every call to a custom page. A plug-in may then answer an action with
  `"partial": {"menus": [ids]}` and only those menus and their items; give an item a `picker` and `pick` in its
  `actions` for a slide-out that sends `browse` for each page and `pick` with the ticked `ids`; send
  `"layout": "cards"` and `hints`; and give an item an `image` and its `attach` a `detach_label`. Read
  [Save in place, choose several, cards and pictures](plugin-api-reference.md#save-in-place-choose-several-cards-and-pictures-api-116).
  An older Starboard sends no header, and a plug-in that gets none answers as before.
- **Changed (Starboard 0.24.0):** a link on a custom page's item that goes to the plug-in's own published port opens at the address the
  page was opened with, as Its web page does.

- **Added:** the `disk.changed` event, with the `system:read` permission: a pool job the root helper finished
  (`action`, `state`, `disk`, `erased`, `result`), however it was asked for, so a notifications plug-in can say when a
  disk is erased, added to the pool or taken out of it. Name `>=1.16` in `starboard_api` to use it.

- **Fixed:** a plug-in on its own network (`default`) or the VPN can reach Starboard's API again (DASH-482). Starboard
  runs on the server's own network, so it could never join the plug-in's network, and `http://starboard:8095` did not
  answer there.
- **Added:** `STARBOARD_API_SOCKET`, `/run/starboard/api.sock`, in every plug-in container: a Unix socket Starboard
  keeps in the plug-in's run folder while the plug-in is active. Send the usual HTTP requests to it, with the path
  from `STARBOARD_API` and the plug-in's own key; it answers only `/api/v1`, and refuses any other key with `401`.
  The plug-in's own network stays internal. Read
  [Settings and key files](plugin-api-reference.md#settings-and-key-files).
- **Changed:** Starboard no longer tries to join each plug-in's network when it starts one.
- **Added:** `STARBOARD_HOME_ADDRESS` for a container with `publish` on the `lan` network: its own address on the
  home network, such as `http://192.168.1.20:8790`. Create your own TV channel gives it to Jellyfin's Live TV.
- **Changed:** a custom page's `add` box and an item's `attach` form take plain text, not only a web address, so a
  plug-in can ask for a name or a number. Check what you are sent: the browser no longer checks it is an address.
- **Changed:** Starboard activates a plug-in once it is installed, from a catalogue, an address or a zip file. One
  with `setup_required` or required settings stays waiting until they are saved, as before. Plan for your first
  start to come straight after the install.
- Nothing was taken away: every 1.15 plug-in works as before, and `STARBOARD_API` is as before.

## Starboard API 1.6.0 (Starboard 0.20.0), 16 November 2026

- **Added:** `GET /backup/copies`, with the `system` scope and a read key: where copies of full backups go off this
  computer (another disk, a share or a cloud service), how many are kept there, the last copy and the last Test
  connection. Never a password, key or rclone config. Read [the API reference](api-reference.md#get-apiv1backupcopies).
- **Added:** `POST /backup/copies/test`, with the `system` scope and a manage key: Test connection, as the button on
  Settings, General, Backup/Logs. It reaches the place, writes a small file, reads it back, removes it and
  checks there is room for the newest backup, in 2 minutes at most, and keeps the result. `409 not_set_up` when no
  place is set up, `409 cannot_test` when a test is already running. An `error` that starts `SIGNIN|` means a cloud
  service no longer accepts the sign-in.
- Nothing was taken away: every earlier address answers as before.

## Starboard API 1.5.0 (Starboard 0.20.0), 16 November 2026

- **Added:** Install all updates, for keys that ticked `updates`: `GET /updates/all` says what would install, in the
  order it runs (the other apps, Jellyfin's plug-ins, Starboard's plug-ins, Reelix, then Starboard last), and what is
  held back with `why` (a plug-in asking for new permissions or that comes as a zip file, a new major version, or
  anything Starboard cannot update from here). With a manage key, `POST /updates/all` starts them as one batch, one at
  a time, each with its own copy, check and way back; send `{"targets": [...]}` to run only the ones you showed
  someone. It answers 202 with the batch's run, which `GET /updates/runs/{id}` follows: its steps are the updates, with
  the states `went-back` and `held` too, and the batch ends `updated`, `some-updated`, `went-back` or `failed`. Read
  [the API reference](api-reference.md#post-apiv1updatesall).
- **Added:** `big_change` on apps and Reelix in `GET /updates`.
- Nothing was taken away: every 1.4.0 address answers as before.

## Starboard API 1.4.0 (Starboard 0.20.0), 16 November 2026

- **Added:** the log limits, for keys that ticked `logs`: `GET /logs/limits` says how long Starboard keeps its logs
  (`keep_days`, 30 by default), the most they may take together (`max_mb`, 50 by default), what they take now, what
  the limits cover, and the apps' own limit read from Docker (`apps`). With a manage key, `POST /logs/limits` with
  `{"keep_days": 14, "max_mb": 25}` changes them, from the same choices as the page, and older days go at once.
  Read [the API reference](api-reference.md#post-apiv1logslimits).
- **Added:** `POST /logs/delete` with `{"confirm": true}` and a manage key that ticked `logs`: Delete all logs, as on
  Settings, General, Backup/Logs. Today's file and the audit log are emptied, not removed, and the first new
  line says which key deleted them.
- **Changed:** a manage key with `logs` may change these two settings and delete the logs, the second exception to
  "a key never changes settings" after `updates`. A key with no scopes still has neither.
- Nothing was taken away: every 1.3.0 address answers as before.

## Starboard API 1.3.0 (Starboard 0.19.0), 15 November 2026

- **Added:** `GET /downloads/issues`, with the `downloads` scope and a read key: every download in the queue that
  needs attention or failed, with its app, download client, the app's own state, every message, size, progress,
  age, indexer, paths inside the container, the ids in Reelix or the app, the download client's ids and what
  Starboard already tried. `markdown` holds the same as Markdown, with a short prompt at the top for an AI helper.
  Each app's queue is asked only when you call it, at most every 10 seconds. Keys, passwords, tokens, private
  addresses and full download addresses are taken out. Read [the API reference](api-reference.md#get-apiv1downloadsissues).
- **Fixed:** an update run's `kind` in `GET /updates/runs` can be `jellyfin-plugins` (Jellyfin's own plug-ins updated by
  Starboard, DASH-422), which the description now lists.
- Nothing was taken away: every 1.2.0 address answers as before.

## Starboard API 1.2.0, 14 November 2026

- **Added:** updates, for keys that ticked the new `updates` scope (a key with no scopes does not have it, as with
  `logs`): `GET /updates` lists what can be updated (Starboard, Reelix, the other apps and the plug-ins) from what
  Starboard already knows, with the update running now; `POST /updates` with `{"target": "plugin:direct-play"}`
  starts an update to the newest version Starboard knows, and answers `202` with the run; `GET /updates/runs` and
  `GET /updates/runs/{id}` give each update's steps and how it ended; `POST /updates/rollback` rolls a plug-in back
  to the version kept before. Read [the API reference](api-reference.md#updates).
- **Added:** each update has the same backup, health check and way back as on the pages, and `update_started` and
  `update_finished` lines in the audit log as well as the `api_write` line. One update runs at a time. Never from an
  address the key gives.
- **Added:** the errors [`update_running`](../../api/errors.md#update_running) and
  [`cannot_update`](../../api/errors.md#cannot_update), both `409`.
- **Changed:** the API reference says that `logs` and `updates` are only for keys that ticked them.
- Nothing was taken away: every 1.1.0 address answers as before, and a key made before keeps what it had.

## Starboard API 1.1.0, 13 November 2026

- **Added:** reads for the rest of the pages: `/calendar` (with `?month=`), `/requests`, `/transfer`,
  `/download-hours`, `/history`, `/library`, `/library/search`, `/library/status`, `/uptime`, `/app-updates`,
  `/numbers`, `/containers`, `/version`, `/system/history` and `/extras`.
- **Added:** the `manage` right (**Read and manage**, keys `sb_manage_...`) and the everyday actions, each a `POST`:
  `/downloads/actions`, `/download-hours`, `/requests/{id}/approve` and `/decline`, `/library/refresh`,
  `/containers/check`, `/alerts/test` and `/extras/{name}/run`. A read key gets `403`
  [`right_needed`](../../api/errors.md#right_needed). Bodies are JSON of up to 64 KB, `Idempotency-Key` makes a retry
  safe, and every change is in the audit log.
- **Added:** `/events`, Server-Sent Events: apps going down and coming back, alerts, new items, finished downloads
  and playback starting, each heard only by keys whose scopes cover it.
- **Added:** the scopes `library` and `requests`, and scopes and the right chosen in **Make a key**.
- **Added:** `/logs`, Starboard's log with addresses, names and keys taken out, for the `logs` scope only: a key with
  no scopes does not read it. For AI assistants, read [Connect an AI assistant](connect-an-ai-assistant.md).
- **Added:** each write in the description has `x-right: manage`; the errors `not_set_up`, `app_failed`,
  `too_large` and `too_many_streams`.
- **Changed:** a `Link` header for the next page keeps the other query parameters, such as `limit`.
- Nothing was taken away: every 1.0.0 address answers as before, and a read key works as it did.

## Plug-in API 1.15.0 (Starboard 0.19.0), 15 November 2026

- **Added:** `build` on a container (DASH-414): its image is built by Starboard from the `Dockerfile` in the plug-in's
  zip file and tagged `local/<id>:<version>`, for a private plug-in with no registry, such as On demand. Installed
  with **Settings**, **Plug-ins**, **Add a plug-in**, **Upload a zip file**, and updated with **Update from a zip
  file** on its page; **Roll back** works as for any plug-in. The zip and the Dockerfile are checked first, and the
  build runs with limits (2 GB of memory, 2 processor cores, 20 minutes, an image of up to 3 GB). Read
  [Built from a zip file](plugin-manifest-reference.md#built-from-a-zip-file).
- **Added:** `jellyfin_libraries` and the permission `jellyfin:libraries` (medium risk, DASH-430): Jellyfin libraries
  for folders the plug-in fills, which Starboard adds on each activation with real-time monitoring deactivated unless
  the plug-in sets `realtime_monitor`, and keeps that way. Read
  [Jellyfin libraries](plugin-manifest-reference.md#jellyfin-libraries).
- **Changed:** a manifest with `build` from an address or a catalogue is refused, with words that point to the zip.
- **Added:** the permission `library:holding` (high risk) with the volume `media:holding`: the media folder, read and
  write, at `/media`, so a plug-in can move films and series into the holding folder inside it,
  `media/.holding/<plug-in id>/`, keeping the folders each was in, and put them back. A container that mounts it may
  run as `"user": "media"`. Read
  [The holding folder in the media folder](plugin-manifest-reference.md#the-holding-folder-in-the-media-folder).
  (DASH-406, for Library clean-up)
- **Added:** `restore` in a custom setting item's `actions`, drawn as a **Put back** button on the row and sent as
  `{"action": "restore", "id"}`. (DASH-406)
- **Added:** `titles` on a card (DASH-443): a title for each card size (`small`, `medium`, `half`, `wide`, `full`),
  each the card's heading on its own, on one line, at that size; the plug-in's name follows it for screen readers.
  Each is limited to what fits on one line in that size: small 17, medium 28, half 22, wide 43 and full 45
  characters. A longer title is refused by the manifest check and named by the plug-in tester. A size left out shows
  the plug-in's name with the card's `title`, as before. Read
  [A title for each size](plugin-manifest-reference.md#a-title-for-each-size-api-115).
- **Changed:** on a small card the band's status chip shows only its icon; its words are still read to screen readers.
- Nothing was taken away: a plug-in made for 1.14 works as before.

## Plug-in API 1.14.0 (Starboard 0.18.0), 14 November 2026

- **Added:** a card's own refresh time, `refresh_seconds`, from 10 to 3600 seconds, in the manifest and in the card's
  answer, which wins, so a plug-in setting can change it. 10 seconds is the quickest: a smaller value in an answer is
  raised to 10, and one in a manifest is an error. Read
  [How often a card is asked](plugin-api-reference.md#how-often-a-card-is-asked-api-114).
- **Added:** the dashboard asks cards due at the same time in one request, and nothing while the tab is hidden.
- **Added:** `recommended` on an entry in Starboard's own catalogue, shown in **Recommended** at the top of the
  Catalogue with a chip. Adding stays a choice, with what it may do and the password.
- **Added:** `logo` (DASH-428): a small SVG or PNG beside the manifest, with `alt`, checked and cleaned by Starboard
  (SVG up to 16 KB with no scripts, styles, pictures, event handlers or outside links; PNG square, 32 to 256 pixels,
  up to 32 KB) and shown in **Manage**, the **Catalogue**, the plug-in's page and its cards. Without one, its initials.
  A catalogue entry may carry it as `logo` (a data address) and `logo_alt`. Read
  [Logo](plugin-manifest-reference.md#logo).
- **Added:** the card band (DASH-428, design 2): every plug-in card has a grey band with the logo, the plug-in's name
  as the heading, and a status chip and when it last updated, from `status`, `status_label` and `updated` in the
  card's answer. Read [The card band](plugin-api-reference.md#the-card-band-api-114).
- **Added:** a job on a schedule from the plug-in's settings (DASH-432): a setting of type `schedule` (every day,
  every week on a day, or every month on a date, at a time) and `schedule` on a job naming it. Shown in
  **System**, then **Jobs**, with when it runs next and **Run now**. Read
  [A job on a schedule from its settings](plugin-manifest-reference.md#a-job-on-a-schedule-from-its-settings).
- **Added:** the permission `jellyfin:metadata` (medium risk) and the volumes `jellyfin-metadata` and
  `jellyfin-metadata:ro`: Jellyfin's metadata folder at `/metadata`, mounted only when granted, and `"user": "media"`
  with it. Read [Jellyfin's metadata folder](plugin-manifest-reference.md#jellyfins-metadata-folder).
- **Added:** `update` (DASH-424): a `before` step on the installed version and an `after` step on the version
  running at the end, each a `POST` with a time limit of 5 to 300 seconds; a failing `before` stops the update with
  nothing changed. `health_wait_seconds` (10 to 600, 60 by default): after every update Starboard waits for the new
  version's `health` path, and goes back to the version before by itself when it does not answer. `migrations`:
  `rename`, `remove` and new `defaults` for saved settings, by version, kept for Roll back. Read
  [Updates](plugin-manifest-reference.md#updates) and [Write a plug-in that updates safely](update-a-plugin-safely.md).
- **Added:** **What is new since** the installed version, from the new version's `changes`, in the warning before an
  update, with the settings that move and how the update is kept safe.
- **Changed:** an update and a Roll back run as steps in a dialog, followed with `GET /api/updates/runs/{id}/job` on
  Starboard's own pages; `POST /api/plugins/{id}/update` and `/rollback` answer with the run.
- **Changed:** the plug-in tester warns when `changes` has nothing for the manifest's own version, and gives a tip when
  a plug-in with jobs has no `before` step.
- **Changed:** the plug-in tester reports a logo that fails its checks, a `status` Starboard does not know in a card's
  `example`, and suggests a logo and a status where there is none.
- **Changed:** `GET /api/plugins` and `GET /api/plugins/cards` (Starboard's own pages) give each plug-in's `logo`,
  `{url, alt}` or `null`; `GET /api/plugins/{id}/logo` serves the cleaned copy; a card's answer has `asked`. The
  public `/api/v1` did not change.
- Nothing changed for a card without `refresh_seconds`: it is asked once a minute, or every `refresh_minutes`.
- A plug-in without `update` is updated as before, with one addition: when it has a `health` path, Starboard waits up
  to 60 seconds for it after the update, and goes back by itself if it does not answer.
- Nothing was taken away: a manifest that worked with 1.13 works the same, and its cards gain the band with its
  initials and when Starboard last asked it.

## Plug-in API 1.13.0, 13 November 2026

- **Added:** app plug-ins (DASH-411), a whole app kept out of the main install, such as Jellystat with its
  database. Read [App plug-ins](plugin-manifest-reference.md#app-plug-ins).
- **Added:** the permission `network:port`, and `publish` on the `lan` network with `host_port`: the app's own web
  page on the home network, at a port Starboard chooses and keeps.
- **Added:** `{secret:<name>}`, `{jellyfin:url}` and `{jellyfin:key}` in `env`; `tmpfs`; `data:<path>`,
  `data/<folder>:<path>` and `media/<one folder>:ro` in `volumes`; `pids` in `resources`, up to 1024.
- **Added:** `adopt`, which copies an app the main install already runs into the plug-in, never moving or changing
  its folders.
- **Added:** removing a plug-in asks where its folder goes: kept in `data/plugins/.removed`, or the holding folder.
- **Added:** `rest` in a catalogue entry, the memory and processor an app uses at rest.
- **Changed:** `env` names may have lower case letters, such as `serverIP`.
- Nothing was taken away: a manifest that worked with 1.12 works the same.

## Plug-in API 1.12.0, 13 November 2026

- **Added:** `"user": "media"` on a container that mounts a `media/<one folder>` volume: it runs as the media folder's
  owner (the apps' user from **Install apps**), so the files it adds are the person's own. Starboard makes each
  `media/<one folder>` that is missing, owned by the user the container runs as; a folder that is there already is
  left as it is. People read that it runs as the media folder's owner before they add it. Read
  [Containers](plugin-manifest-reference.md#containers).
- **Added:** `link` on a custom setting's item, `{"url", "label"}`: a link that opens in a new tab, such as a search for
  the title on another site. Only `http` and `https` addresses are kept. Read
  [Custom pages](plugin-api-reference.md#custom-pages).
- **Added:** `state_label` on a custom setting's item: the plug-in's own words for its state, such as `Added`, in
  place of **Works** or **Not answering**, in the state's colour.
- **Added:** `file_only` on a custom setting's `add`: only the file picker is shown, for a plug-in that takes files and
  never an address.
- An older Starboard refuses `"user": "media"`, so set `starboard_api` to `>=1.12` when you use it. It ignores `link`
  and `file_only` (it shows the add box's address field too).

## Plug-in API 1.11.0, 13 November 2026

- **Added:** four events, each from a check Starboard already makes every 5 minutes: `request.available` (with
  `media:read`), `download.failed` (with `downloads:read`), `disk.nearly_full` (with `system:read`) and
  `update.available` (with `apps:read`). Read [Events](plugin-api-reference.md#events).
- **Added:** `readonly` on a custom setting's list with `"layout": "folds"`: tables to read, with no tick boxes, states or
  buttons. Read [Tables to read only](plugin-api-reference.md#tables-to-read-only-api-111).
- An older Starboard refuses a manifest that lists the new events, so set `starboard_api` to `>=1.11` when you use
  them. It ignores `readonly`.

## Plug-in API 1.10.0, 13 November 2026

- **Added:** `changes`, an optional list of the plug-in's own changes by version, in Keep a Changelog's types
  (`added`, `changed`, `deprecated`, `removed`, `fixed`, `security`). After an update, a Roll back or an update from
  an address, the plug-in's **State** shows **What is new** with the changes between the two versions, until someone
  chooses **Got it**. Nothing is fetched: Starboard reads them from the manifest it already has. Read
  [Changes](plugin-manifest-reference.md#changes).
- A plug-in without `changes` still works. Its **State** shows the catalogue's line about the version, or says its
  maker did not list what changed.
- An older Starboard refuses a manifest with `changes`, so set `starboard_api` to `>=1.10` when you use it.

## Plug-in API 1.9.0, 13 November 2026

- **Added:** `publish` on a container with `network: vpn` and a `port`. Starboard puts that port on Gluetun, so the
  home network can reach the container, and restarts Gluetun once when the plug-in starts. Use it only when
  something outside the server must open the container's address, such as a TV app that plays a stream address
  Jellyfin hands it. Read [Containers](plugin-manifest-reference.md).
- An older Starboard refuses a manifest with `publish`, so set `starboard_api` to `1.9` when you use it.

## Plug-in API 1.7.0, 13 November 2026

- **Added:** a custom setting's list may have sub menus: `menus`, each with a `parent` for the level it opens from, and
  `menu` on each item and switch. Read [Sub menus](plugin-api-reference.md#sub-menus).
- **Changed:** **Test all** shows only on a list whose items can be tested, or that has none yet.
- **Changed:** a plug-in's **State** says its version, for plug-ins built into Starboard too.
- Nothing in the manifest changes, so `starboard_api` can stay as it is. An older Starboard leaves `menus` out and
  shows every item in one list.

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

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
