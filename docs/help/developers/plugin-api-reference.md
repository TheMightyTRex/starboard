[Help centre](../README.md) · Developers

# Plug-in API reference

What Starboard calls on a plug-in, what it sends and what it expects back, and what a plug-in finds and may call in
return. This page matches plug-in API 1.4.0. The fields that ask for each of these are in the
[Plug-in manifest reference](plugin-manifest-reference.md).

## How Starboard reaches a plug-in

- Starboard always calls the **first** container in `containers`, on its `port` (80 when it is left out).
- It reaches the container by its name, `plugin-<id>-<name>`, on the plug-in's own network. A container on the
  `vpn` network is reached through Gluetun.
- Every request has `User-Agent: Starboard` and asks for JSON. Answer with `Content-Type: application/json`.
- Starboard never puts what a plug-in sends into a page as HTML. It keeps only the fields below, cuts each text to
  its length, and draws everything itself.

| What | Method and path | Time limit | Largest answer read |
|---|---|---|---|
| A card | GET the card's `path` | 3 seconds | 64 KB |
| A button | POST the action's `path` | 10 seconds | 64 KB |
| A custom setting | GET or POST the setting's `choices` path | 60 seconds | 2 MB |
| An event | POST `/events` | 3 seconds, tried twice | not read |
| A job | POST the job's `path` | its `time_limit_minutes` | 64 KB |

## Card answers

Starboard asks a card's path only while someone has a dashboard with the card open, and at most once a minute, or
once every `refresh_minutes`. Answer with one JSON object in the shape for the card's type.

| Type | Answer | Rules |
|---|---|---|
| `stat` | `{"value": 42, "label": "titles", "note": "3 added today"}` | `value` must be a number. `label` is cut to 40 characters, `note` to 80 |
| `list` | `{"items": [{"title": "Dune", "detail": "Added today", "link": "https://example.invalid/dune"}]}` | Up to 10 items are shown. Each needs a `title` (80 characters); `detail` is cut to 120. A `link` must start with `http://` or `https://`, or it is left out |
| `status` | `{"state": "ok", "text": "Up to date"}` | `state` is `ok`, `warning` or `problem`. `text` is cut to 160 characters |
| `guide` | `{"items": [{"channel": "Kestrel Sport", "number": "601", "now": "Football Extra", "start": 1794600000, "stop": 1794603600, "next": "Darts", "next_start": 1794603600}], "note": ""}` | From API 1.8. Up to 12 items, each with a `channel` (80 characters); `now` and `next` are cut to 120. `start`, `stop` and `next_start` are seconds since 1970: Starboard shows the times and how far through the programme it is |

A `stat` card's `format` in the manifest says how `value` is shown: `number`, `bytes`, `percent`, `duration`
(seconds) or `date` (seconds since 1970).

When the path does not answer in 3 seconds, answers more than 64 KB, or answers the wrong shape, the card says
"No answer from" and the plug-in's name, with what was wrong.

## Actions

A button in the plug-in's section of **Settings**, then **Plug-ins**, sends a POST with an empty body to the
action's `path`. Answer within 10 seconds with:

```json
{"said": "Started building the channel list"}
```

Starboard shows `said` to the person, cut to 160 characters. With no `said`, it shows the button's label and
"started". When the plug-in does not answer, it shows the plug-in's name and "did not answer". Do long work in the
background and answer at once.

## Custom screens

A setting of type `custom` lets the plug-in describe a list, such as a list of channels or sources, and Starboard
draws it with its own controls. The setting's `choices` is a path on the plug-in. Starboard calls it with the
plug-in's own API key in the `X-Api-Key` header, so the plug-in can tell the call came from Starboard.

**GET** the path. Answer with:

```json
{
  "type": "list",
  "title": "Channels",
  "intro": "Every channel by section.",
  "add": {"label": "Add a channel", "hint": "Its stream address", "placeholder": "https://"},
  "items": [
    {"id": "news-1", "title": "News one", "detail": "Guide refreshed today", "state": "ok", "group": "News",
     "on": true, "address": "https://example.invalid/news-1", "actions": ["test", "toggle", "remove", "up", "down"],
     "choice": {"label": "Weight", "value": "2", "options": [["1", "Low"], ["2", "Normal"], ["3", "High"]]}}
  ]
}
```

| Field | Rules |
|---|---|
| `type` | Must be `list` |
| `title`, `intro` | Cut to 80 and 400 characters |
| `add` | Optional. Shows an add box; `label`, `hint` and `placeholder` are cut to 120 characters. Optional `file`: `{"label", "hint", "accept"}` also shows a file picker, where `accept` lists file endings such as `.m3u,.json,.gz` |
| `items` | Up to 4000. An item without an `id` is left out. The whole answer can be up to 2 MB |
| `id`, `title`, `detail` | Cut to 600, 120 and 200 characters |
| `state` | `ok`, `warning`, `problem`, `off` or `unknown`; anything else is `unknown` |
| `group` | A heading the item sits under, cut to 40 characters |
| `on` | `true` or `false`; `true` when left out |
| `address` | Shown under the title, cut to 500 characters |
| `actions` | The buttons on the row, from `test`, `toggle`, `remove`, `up` and `down` |
| `choice` | Optional. A small list on the row: up to 12 `options`, each `[value, words]`, cut to 40 characters |
| `bulk` | Optional. Up to 60 switches (400 with `menus`) for whole sets of items, each `{"id", "label", "kind", "on", "total"}`: `on` is how many of its `total` items are active. Starboard groups them by `kind`, in the order given. Optional: `active` (`true` or `false`) when the set is more than its items, such as a whole source that can be stopped, and `hint`, up to 160 characters, in place of the words "3 of 5 active" |

### Sub menus

From plug-in API 1.7, a long list can be split into sub menus, so no one page holds every item. Live TV's
**Channels** uses them: each list opens to its regions and sections, and each section to its channels. Add `menus`,
and name a menu in each item's and switch's `menu`:

```json
{
  "type": "list",
  "title": "Channels",
  "menus": [
    {"id": "uk", "title": "UK", "group": "Regions"},
    {"id": "uk-news", "title": "News", "group": "Sections", "parent": "uk", "detail": "Refreshed every hour"}
  ],
  "bulk": [{"id": "uk-news", "label": "Every channel in News", "kind": "", "on": 1, "total": 2, "menu": "uk-news"}],
  "items": [{"id": "news-1", "title": "News one", "on": true, "actions": ["toggle"], "menu": "uk-news"}]
}
```

| Field | Rules |
|---|---|
| `menus` | Optional. Up to 200, each `{"id", "title"}`: `id` up to 120 characters, `title` up to 80. A menu without a title is left out |
| `parent` | The menu it opens from; left out for the first level. A parent must come before its sub menus, and menus go at most 4 levels deep. Anything else is left out, so a menu can never open itself |
| `group` | A heading its row sits under, cut to 40 characters |
| `detail` | Shown under its title, cut to 200 characters |
| `active` | Optional. `false` marks the menu **Inactive** whatever its items say, such as a whole source that is stopped |
| `menu`, on an item or a `bulk` switch | The menu it is shown in. Left out, or naming no menu, it stays on the first level |

Starboard draws each level's menus as rows that open, with their state (**Active**, **Partly active** or
**Inactive**) and how many of their items are active, counting the items in their sub menus too. An opened menu
shows a back link above its heading, its own switches, sub menus and items, and the All, Active and Inactive
filter. Focus goes to the opened menu's heading, and back to its row on the way back. **Test all** and the add box
are on the first level only. With menus, `bulk` can have up to 400 switches.

A list without `menus` is drawn as before, so an older Starboard shows every item in one list.

### Sections that fold, with a table each (API 1.8)

Send `"layout": "folds"` with `columns` to show each `group` as a section that folds: one line with its name, how many
of its items are active, and its own switch, which opens to a table of its items. Starboard adds a search, the All,
Active and Inactive filter, filter chips and a tick box on each row, so several items from any section can be
activated or deactivated at once. Only open sections draw their rows.

| Field | Rules |
|---|---|
| `columns` | Up to 8, each `{"key", "label", "type"}`. `key` is lower case letters, numbers and `_`; `type` `number` sorts as numbers. Every column sorts |
| `cells`, on an item | `{key: text}` for each column, cut to 80 characters |
| `filters` | Up to 4, each `{"key", "label"}` naming a column: a chip for each value in it. Chips of one filter add up; filters narrow |
| `fold`, on a `bulk` switch | The `group` whose line it goes on |

Ticked items are sent as `{"action": "bulk_ids", "ids": ["news-1", "news-2"], "value": "on"}`, up to 1000 ids.

### Something for one item, and notices (API 1.8)

| Field | Rules |
|---|---|
| `attach`, on an item | `{"label", "field", "hint", "placeholder", "accept", "value"}`, with `attach` in its `actions`: a button, such as **Add guide**, that opens a small form under the row for an address or a file. The address is sent as `{"action": "attach", "id", "value"}`; a file goes to the `/file` path with `id` added. `detach` in `actions` adds a **Remove guide** item to its More menu |
| `notices` | Up to 5, each `{"id", "tone", "title", "text", "progress", "dismiss"}`, at the top of the page. `tone` is `info`, `success`, `warning` or `danger`. With `progress` (0 to 100) Starboard shows a bar and asks again every 3 seconds until it has gone. With `dismiss`, a **Close** button sends `{"action": "dismiss", "id"}` |

**POST** the path when the person does something. The body is:

```json
{"action": "toggle", "id": "news-1", "value": ""}
```

`action` is one of `add`, `test`, `test_all`, `toggle`, `remove`, `up`, `down`, `choose`, `bulk` and, from API 1.8,
`bulk_ids`, `attach`, `detach` and `dismiss`. `id` is the row,
and `value` is what the person entered or chose. For `bulk`, `id` is the set and `value` is `on` to activate every item
in it or `off` to deactivate them. Answer with the whole list again, in the same shape, with `said`
added: one sentence, up to 200 characters, that Starboard shows. To refuse, answer with an HTTP error status and
`{"error": "A sentence saying why"}`; Starboard shows the sentence.

When `add` has a `file`, a chosen file is sent as it is, not as JSON: Starboard streams it to your `choices` path
plus `/file`, such as `/sources/file?name=channels.m3u`, with `Content-Type: application/octet-stream`, the file's size
in `Content-Length` and the file's name in `name`. Files can be up to 60 MB. Read the body a piece at a time and answer
with the whole list, in the same shape, with `said` added; to refuse, answer with an HTTP error status and `{"error": ...}`.
A plug-in without this path answers 404, and Starboard says the plug-in does not take files.

## Health

Answer GET on the `health` path with status 200 while the plug-in works. Keep it cheap. Starboard asks it when
someone opens **Settings**, then **Plug-ins**, at most once a minute, and waits 2 seconds. Any other answer shows
the plug-in as **Not answering**, with the reason. For plug-ins built into Starboard, it is also the container's
Docker health check, every 60 seconds.

## Events

When a plug-in lists `events` in its manifest, and it is active, Starboard sends each event as a POST to `/events`
on its first container. Your plug-in must answer that path.

```json
{"event": "item.added", "at": "2026-11-12T09:30:00+00:00", "data": {"title": "Dune", "series": null, "type": "Movie", "year": 2021}}
```

- `at` is when Starboard saw it, in UTC (RFC 3339).
- Starboard waits 3 seconds, tries once more a second later, then gives up. Nothing is queued or kept, so an
  event can be missed while the plug-in is stopped.
- No key is sent with an event.

| Event | `data` | How Starboard finds out |
|---|---|---|
| `item.added` | `title`, `series`, `type`, `year` | Jellyfin's recently added list, checked every 5 minutes |
| `playback.started` | `title`, `series`, `type`, `user`, `client` | What is playing in Jellyfin, checked every 5 minutes |
| `download.finished` | `title`, `app` | The download queue, checked every 5 minutes: an item that reaches 100% |
| `app.down` | `app` (its name), `type` | After two of Starboard's checks in a row with no answer |
| `app.up` | `app` (its name), `type` | When an app that was down answers again |

For the three events checked every 5 minutes, the first check after Starboard starts only sets a starting point,
so nothing old is sent, and something that comes and goes between two checks is not seen.

## Jobs

Starboard runs plug-in jobs on its own clock, which wakes every 5 minutes while an active plug-in has a job. A job
is a POST with an empty body to the job's `path`.

- `daily` runs within 5 minutes after its time, in the server's own time zone.
- `every_hours` runs when that many hours have passed since it last started.
- `at_start` runs once after each start of Starboard.
- `quiet_hours` runs it only in quiet hours: the download hours, when they are set, or from 01:00 to 06:00.
- Answer within `time_limit_minutes` (10 when left out) with `{"said": "Tidied 12 files"}`. Starboard keeps `said`,
  cut to 160 characters, as the job's summary in **System**, then **Jobs**. With no `said`, the summary is "Done".
- When the main container is resting (read [Resting when idle](#resting-when-idle)), Starboard starts it before
  the job.
- A job never runs twice at once. People can also run it now from **System**, then **Jobs**, while the plug-in is
  active.

## Settings and key files

Starboard keeps each plug-in in its own folder on the server, `data/plugins/<id>/`, which only Starboard can open.
It copies what the containers read into `data/plugins/<id>/run/` and mounts that folder as `/run/starboard`, read
only, so any user a container runs as can read these files:

| In the container | What it is |
|---|---|
| `/run/starboard/settings.json` | The settings, as one JSON object of `key` and value, secrets included |
| `/run/starboard/key` | The plug-in's own API key, as one line of text |
| `/run/starboard/jellyfin.json` | Only with `jellyfin:key`: `{"url": ..., "api_key": ...}`. An address on the server itself is given as `host.docker.internal` |
| `/run/starboard/reelix.json` | Only with `reelix:key` (API 1.6): `{"url": ..., "api_key": ...}`, Reelix's address and key |
| `/run/starboard/usenet.json` | Only with `usenet:servers` (API 1.6): `{"servers": [{"name", "host", "port", "ssl", "user", "password", "connections", "level"}]}`, the active news servers from NZBGet (or SABnzbd), first choice first. Use fewer connections than `connections`: the download app uses the same account |
| `/data` | Only with the `data` volume: its own folder, read and write |

And these environment variables, with the `env` from the manifest:

| Name | Value |
|---|---|
| `STARBOARD_API` | `http://starboard:8095/api/v1/` |
| `STARBOARD_API_KEY_FILE` | `/run/starboard/key` |

Starboard writes `reelix.json` and `usenet.json` again each time it starts and each time the plug-in is activated,
so a changed password reaches the plug-in without a reinstall.

Starboard does not restart a plug-in when its settings change, but the new `settings.json` is there at once:
Starboard replaces each file whole, so you never read half of one. Read `settings.json` when you need a value,
rather than once at start. Never write secrets to the container's log.

Plug-ins added before 12 November 2026 got each file mounted on its own. A file mounted that way kept the copy the
container started with. Starboard changes them to the folder when it starts, and starts each active one again
once.

## Resting when idle

A plug-in whose first container has `"start": "when_needed"` rests when it is not used:

- Starboard stops that container once two things are both true for `idle_stop_minutes` (15 when left out):
  Starboard has not called it, and its network has been quiet.
- Network traffic keeps it running, so Jellyfin or another app streaming from it straight away does not count as
  idle. A container on the VPN shares Gluetun's network, so Starboard cannot tell, and it never rests.
- The next time Starboard calls it, for a card, a button, its own page, an event or a job, Starboard starts it
  first and waits up to 20 seconds for it to answer.
- Only Starboard can start it again. Use `when_needed` only when Starboard is how people reach it.
- Only the first container can rest. The tester warns about `when_needed` on any other container, which runs
  always.

## The plug-in's API key

Every plug-in with a container gets its own key to [Starboard's API](api-reference.md), made when it is added.

- It is named `Plug-in:` and the plug-in's name, and it can only read.
- Its scopes are the read permissions the person approved: `apps:read` gives `apps`, `downloads:read` gives
  `downloads`, `media:read` gives `media` and `system:read` gives `system`.
- It does not expire. It stops working when the plug-in is removed.
- When an update or **Roll back** changes the read permissions, Starboard revokes the key and writes a new one to
  the same file. Read the file again when a call answers `401`.
- With the `default` network, Starboard's API is the only thing the plug-in can reach.

Send it as for any key:

```python
import json, os, urllib.request

key = open(os.environ["STARBOARD_API_KEY_FILE"]).read().strip()
req = urllib.request.Request(os.environ["STARBOARD_API"] + "downloads", headers={"Authorization": "Bearer " + key})
with urllib.request.urlopen(req, timeout=10) as r:
    print(json.load(r)["items"])
```

The rules for every key, such as 120 requests a minute, are in [Authentication and keys](api-authentication.md).

## States

Starboard keeps one state for each plug-in, and shows each with one sentence and one button.

| State | What it means | The button |
|---|---|---|
| `installed` | Added, not started yet | **Activate** |
| `enabled` | Active and running | **Deactivate** |
| `disabled` | Deactivated: stopped, with its settings and data kept | **Activate** |
| `failed` | It did not start, or stopped answering. The message says why | **Try again**, or **Roll back** to the version before within 10 minutes of an update |
| `needs-setup` | A required setting is empty, or `setup_required` and it has never been set up | **Finish setting up** |
| `not-supported` | This Starboard's plug-in API is outside the plug-in's `starboard_api`, so it is stopped | **Look for an update** |

The first four are stored in the plug-in's `state.json`. Starboard works out `needs-setup` and `not-supported` each
time, and a plug-in in either cannot be activated. **Deactivate all plug-ins** stops every active plug-in at once.

## Updates and Roll back

- When a catalogue lists a newer version, the plug-in's tab offers **Update to** and that version. Starboard
  shows the same warning as when adding it, with any new permissions marked, and the changelog. It asks for the
  password.
- Settings stay. A new setting gets its `default`.
- An active plug-in is started again on the new version.
- Starboard keeps the version before in `data/plugins/<id>/previous/`: its manifest, settings and Compose file. Only
  one earlier version is kept.
- **Roll back** swaps the two, with no download, and asks for the password. The newer version is kept in its place.
- Plug-ins built into Starboard update with Starboard.
- Each update and roll back is written to the audit log.

## Catalogues

A catalogue is one file, `catalogue.json`, at an `https` address, that lists plug-ins and their versions. People
add it from a link. Starboard reads each catalogue at most once a day, 256 KB and 5 seconds at most, and up to 10
catalogues besides its own.

```json
{
  "name": "Sam's plug-ins",
  "plugins": [
    {
      "id": "hello-card",
      "name": "Hello card",
      "description": "Shows on your dashboard how long it has been running.",
      "kind": "System",
      "author": "Sam",
      "permissions": [],
      "notices": [],
      "published": true,
      "versions": [
        {"version": "0.2.0", "starboard_api": ">=1.4 <2.0", "released": "2026-11-12",
         "manifest": "https://example.invalid/hello-card/0.2.0/starboard-plugin.json",
         "manifest_sha256": "9b1d3f5a7c2e4b6d8f0a1c3e5b7d9f2a4c6e8b0d1f3a5c7e9b2d4f6a8c0e1b3d",
         "changelog": "A list card of the last five starts."},
        {"version": "0.1.0", "starboard_api": ">=1.0 <2.0", "released": "2026-11-10",
         "manifest": "https://example.invalid/hello-card/0.1.0/starboard-plugin.json",
         "manifest_sha256": "2e4c6a8b0d1f3e5a7c9b2d4f6e8a0c1b3d5f7a9c2e4b6d8f0a1c3e5b7d9f2a4c"}
      ]
    }
  ]
}
```

| Field | Rules |
|---|---|
| `name` | The catalogue's name, up to 60 characters. Its address's host name when left out |
| `plugins` | Required. Up to 200 are read |
| `id` | The plug-in's `id`. An entry with a wrong id is left out |
| `name`, `description`, `kind`, `author` | Up to 40, 240, 30 and 60 characters. `kind` groups the plug-ins, `Other` when left out |
| `permissions`, `notices` | Shown before anyone opens the plug-in. Unknown ones are left out |
| `published` | `false` shows it as **Coming soon**, with no way to add it |
| `versions` | Up to 50, in any order |
| `version` | The plug-in's version |
| `starboard_api` | The range it needs, as in the manifest. Left out, it fits any Starboard |
| `manifest` | Required: the `https` address of that version's `starboard-plugin.json` |
| `manifest_sha256` | The SHA-256 of that file, 64 hex characters |
| `changelog`, `released` | Shown with an update. Up to 600 and 10 characters |

How Starboard uses it:

- It offers the newest version whose `starboard_api` includes this Starboard, and says how many newer versions it
  hid and which API they need.
- When it fetches a manifest, it checks the file's SHA-256 against `manifest_sha256`. If the file changed since the
  catalogue listed it, Starboard refuses it.
- An entry with no `versions` is one version, read from the entry's own `version`, `starboard_api`, `manifest` and
  `manifest_sha256`.

How to write one is in [Test and publish a plug-in](test-and-publish-a-plugin.md#write-a-catalogue).

## Find out more

- [Plug-in manifest reference](plugin-manifest-reference.md)
- [Make your first plug-in](make-a-plugin.md)
- [Test and publish a plug-in](test-and-publish-a-plugin.md)
- [API reference](api-reference.md)
- [What a plug-in can change](../basics/what-plugins-can-change.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
