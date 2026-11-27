[Help centre](../README.md) · Developers
<!-- help: dev / plugins -->

# Plug-in API reference

What Starboard calls on a plug-in, what it sends and what it expects back, and what a plug-in finds and may call in
return. This page matches plug-in API 1.17.0. The fields that ask for each of these are in the
[Plug-in manifest reference](plugin-manifest-reference.md).

## How Starboard reaches a plug-in

- Starboard always calls the **first** container in `containers`, on its `port` (80 when it is left out).
- It reaches the container by its name, `plugin-<id>-<name>`, on the plug-in's own network. A container on the
  `vpn` network is reached through Gluetun.
- An app plug-in's own web page (API 1.13) is not called by Starboard: people open it at the port Starboard chose.
  Read [App plug-ins](plugin-manifest-reference.md#app-plug-ins). Put a small helper first in `containers` if
  Starboard should show cards or buttons for the app.
- Every request has `User-Agent: Starboard` and asks for JSON. Answer with `Content-Type: application/json`.
- Starboard never puts what a plug-in sends into a page as HTML. It keeps only the fields in this section, cuts each text to
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
once every `refresh_minutes`, or at the card's own `refresh_seconds` (API 1.14, read **How often a card is asked**). Answer with one JSON object in the shape for the card's type.

| Type | Answer | Rules |
|---|---|---|
| `stat` | `{"value": 42, "label": "titles", "note": "3 added today"}` | `value` must be a number. `label` is cut to 40 characters, `note` to 80 |
| `list` | `{"items": [{"title": "Dune", "detail": "Added today", "link": "https://example.invalid/dune"}]}` | Up to 10 items are shown. Each needs a `title` (80 characters); `detail` is cut to 120. A `link` must start with `http://` or `https://`, or it is left out |
| `status` | `{"state": "ok", "text": "Up to date"}` | `state` is `ok`, `warning` or `problem`. `text` is cut to 160 characters |
| `guide` | `{"items": [{"channel": "Kestrel Sport", "number": "601", "now": "Football Extra", "start": 1794600000, "stop": 1794603600, "next": "Darts", "next_start": 1794603600}], "note": ""}` | From API 1.8. Up to 12 items, each with a `channel` (80 characters); `now` and `next` are cut to 120. `start`, `stop` and `next_start` are seconds since 1970: Starboard shows the times and how far through the programme it is |
| `sparkline` | `{"series": [{"title": "Router", "points": [12.5, 14, null, 15], "unit": "ms", "detail": "Average 13 ms"}], "note": "Hourly averages, the last 24 hours"}` | From API 1.17. Up to 8 series are shown; an empty list is allowed, and the card then shows the `note`. Each needs a `title` (80 characters) and `points`: 1 to 96 numbers of 0 or more, oldest first, with `null` for a gap. Any other point, or more than 96, is refused with what is wrong. `unit` is cut to 8 characters, `detail` and `note` to 120. Read [Sparkline cards](#sparkline-cards-api-117) |

### Sparkline cards (API 1.17)

A sparkline card shows how something changed, such as a router's response times over the last day. Starboard draws
one row for each series:

1. The series' `title`.
2. A small line of its `points`, oldest at the left, broken where a point is `null`. It has no axes or numbers of its
   own, and it is drawn in the accent colour with no animation, so it follows light, dark, high contrast and
   forced colours.
3. Words Starboard works out from the points, such as "Now 15 ms, lowest 12.5 ms, highest 15 ms", rounded to what
   matters (1,500, 15, 12.5 or 0.25). When the last point is a gap it says "Latest" in place of "Now", and with no
   numbers at all it says "No readings yet".
4. The series' `detail`, such as "Average 13 ms".

The `note` goes under the rows. The line is hidden from screen readers (`aria-hidden="true"`), which read the title,
the words and the detail instead, so nothing depends on the line. It is not a live region: a refresh does not
interrupt a screen reader. Every card size works, down to a phone 320 pixels wide, as the line stretches to the
card's width.

```json
{"series": [{"title": "Router", "points": [12.5, 14, null, 15], "unit": "ms", "detail": "Average 13 ms"},
            {"title": "Jellyfin", "points": [40, 38, 41, 39], "unit": "ms"}],
 "note": "Hourly averages, the last 24 hours", "status": "ok", "updated": 1794694110}
```

Send what you measured, not a picture of it: Starboard keeps only the fields here and draws the line itself.

### How often a card is asked (API 1.14)

Any card's answer may add `refresh_seconds`, how often the dashboard asks it again while the page is open and in
view. It overrides the `refresh_seconds` in the manifest, so a plug-in can let people choose it in a setting.

```json
{"items": [{"title": "Converting now: Dune (2021)", "detail": "Shrink, 34% done, about 1 hour 5 minutes left"}],
 "refresh_seconds": 30}
```

- It is held to 10 to 3600 seconds: a value under 10 is asked every 10 seconds, so no card can be asked more often.
- Starboard keeps the answer for that long, so many people using it at once still ask the plug-in once.
- Nothing is asked while the browser tab is hidden. Cards due at the same time are asked in one request.
- With no `refresh_seconds` anywhere, the card is asked as before: once a minute, or every `refresh_minutes`.
- Keep the answer cheap. Read a small file your plug-in keeps up to date rather than doing the work when asked.

### The card band (API 1.14)

From API 1.14 Starboard draws every plug-in card the same way (design 2, "band with status"): a grey band across
the top that starts with the plug-in's logo (its [logo](plugin-manifest-reference.md#logo), or its initials on a
plain tile), then the plug-in's name as the card's heading (the card's `title` under it, smaller, when it differs),
and ends with a status chip. The body shows the answer as before, and a lighter grey footer says when the
card last updated (from Starboard 0.19.1; before, the time sat in the band).
From API 1.15 a card may give its own title for each size (`titles` in the manifest); the title for the card's size
is then the heading on its own, on one line. On a small card the chip shows only its icon, and its words are still
read to screen readers. Read [A title for each size](plugin-manifest-reference.md#a-title-for-each-size-api-115).

Any card's answer may add these, all optional:

| Field | What it is | Rules |
|---|---|---|
| `status` | The card's state, shown as a chip in the band | One of the values in **States**. An unknown value is left out, and the tester reports it |
| `status_label` | Your own words on the chip, such as `Waiting for 03:30` | Up to 24 characters, cut beyond. Needs a `status`, which sets the chip's colour and shape |
| `updated` | When what the card shows last changed, in seconds since 1970 | Not in the future. Left out, the footer says when Starboard last asked the plug-in |

```json
{"items": [{"title": "Converting now: Dune (2021)", "detail": "Shrink, 34% done"}],
 "refresh_seconds": 30, "status": "converting", "updated": 1794694110}
```

| `status` | Words on the chip | Chip |
|---|---|---|
| `ok`, `done`, `ready`, `protected` | OK, Done, Ready, Protected | success: a tick |
| `working`, `converting`, `scanning`, `updating`, `running` | Working, Converting, Scanning, Updating, Running | info |
| `waiting`, `idle`, `scheduled` | Waiting, Idle, Scheduled | neutral: a clock |
| `paused`, `inactive` | Paused, Inactive | muted |
| `warning`, `needs_setup` | Warning, Needs setting up | warning: a diamond |
| `problem`, `failed`, `stopped` | Problem, Failed, Stopped | danger: a cross |

- The chips are the design system's status chips: words, an icon and a colour together, never colour alone.
- A screen reader reads the heading, then "Status: Converting", the body, and "Updated 30 seconds ago" in the
  footer, so each makes sense on its own. The cards' headings are level 2, under the dashboard's own heading.
- The time is kept in words as it ages ("2 minutes ago") without asking the plug-in again. Nothing in the band or the
  footer is a live region, so a refresh does not interrupt a screen reader.
- A `status` card's own `state` shows as the chip when the answer has no `status`.
- An older Starboard ignores these fields, so a plug-in can send them whatever `starboard_api` it names.

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

## Custom pages

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
| `add` | Optional. Shows an add box; `label`, `hint` and `placeholder` are cut to 120 characters. The box takes plain text, such as a name or an address (Starboard 0.23.0 and later; before, only a web address): check what you are sent and answer with an error in words when it does not fit. Optional `file`: `{"label", "hint", "accept"}` also shows a file picker, where `accept` lists file endings such as `.m3u,.json,.gz`. From API 1.12, `"file_only": true` with a `file` shows only the file picker |
| `items` | Up to 4000. An item without an `id` is left out. The whole answer can be up to 2 MB |
| `id`, `title`, `detail` | Cut to 600, 120 and 200 characters |
| `state` | `ok`, `warning`, `problem`, `off` or `unknown`; anything else is `unknown` |
| `state_label` | Optional, from API 1.12. Your own words for the state, up to 30 characters, such as `Added` or `Lengths differ`, shown in the state's colour in place of Starboard's words (**Works**, **Slow**, **Not answering**, **Inactive**, **Not tested**), which suit a list of sources but not every list |
| `group` | A heading the item sits under, cut to 40 characters |
| `on` | `true` or `false`; `true` when left out |
| `address` | Shown under the title, cut to 500 characters |
| `actions` | The buttons on the row, from `test`, `toggle`, `remove`, `up` and `down` |
| `link` | Optional, from API 1.12. `{"url", "label"}`: a link on the row that opens in a new tab, such as a search for the title on another site. `url` must start with `http://` or `https://`; `label`, up to 80 characters, should say where it goes, such as "Search AudioVault for Dune". Starboard adds "opens in a new tab" for screen readers |
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
shows a back link before its heading, its own switches, sub menus and items, and the All, Active and Inactive
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

### Tables to read only (API 1.11)

Send `"readonly": true` with `"layout": "folds"` for figures people read but do not change, such as watch statistics.
Each section opens to a table with only your `columns`: no tick boxes, no **State** column, no **Activate** buttons
and no All, Active and Inactive filter. Its line says how many rows it has. The first column is each row's header, so
a screen reader names the row by it. Search, sorting by any column and the filter chips still work. Use a custom
setting for each table, so each has its own columns and its own tab. An older Starboard ignores `readonly` and draws
the table as before.

### Something for one item, and notices (API 1.8)

| Field | Rules |
|---|---|
| `attach`, on an item | `{"label", "field", "hint", "placeholder", "accept", "value"}`, with `attach` in its `actions`: a button, such as **Add guide**, that opens a small form under the row for plain text, such as a name, a number or an address (Starboard 0.23.0 and later), or a file. The address is sent as `{"action": "attach", "id", "value"}`; a file goes to the `/file` path with `id` added. `detach` in `actions` adds a **Remove guide** item to its More menu |
| `restore` in an item's `actions` (API 1.15) | A **Put back** button on the row, for something your plug-in moved aside, such as a film Library clean-up moved to the holding folder. It sends `{"action": "restore", "id"}`; answer with the list again and `said`, such as "Put back in movies, and Reelix follows it again". An older Starboard leaves the button out |
| `notices` | Up to 5, each `{"id", "tone", "title", "text", "progress", "dismiss"}`, at the top of the page. `tone` is `info`, `success`, `warning` or `danger`. With `progress` (0 to 100) Starboard shows a bar and asks again every 3 seconds until it has gone. With `dismiss`, a **Close** button sends `{"action": "dismiss", "id"}` |

**POST** the path when the person does something. The body is:

```json
{"action": "toggle", "id": "news-1", "value": ""}
```

`action` is one of `add`, `test`, `test_all`, `toggle`, `remove`, `up`, `down`, `choose`, `bulk` and, from API 1.8,
`bulk_ids`, `attach`, `detach` and `dismiss`, from API 1.15 `restore`, and from API 1.16 `browse` and `pick`. `id` is the row,
and `value` is what the person entered or chose. For `bulk`, `id` is the set and `value` is `on` to activate every item
in it or `off` to deactivate them. Answer with the whole list again, in the same shape, with `said`
added: one sentence, up to 200 characters, that Starboard shows. To refuse, answer with an HTTP error status and
`{"error": "A sentence saying why"}`; Starboard shows the sentence.

When `add` has a `file`, a chosen file is sent as it is, not as JSON: Starboard streams it to your `choices` path
plus `/file`, such as `/sources/file?name=channels.m3u`, with `Content-Type: application/octet-stream`, the file's size
in `Content-Length` and the file's name in `name`. Files can be up to 100 MB (60 MB before Starboard 0.24.1); refuse anything too big for you with your own words. Read the body a piece at a time and answer
with the whole list, in the same shape, with `said` added; to refuse, answer with an HTTP error status and `{"error": ...}`.
A plug-in without this path answers 404, and Starboard says the plug-in does not take files.

### Save in place, choose several, cards and pictures (API 1.16)

Starboard 0.23.0 sends `X-Starboard-Can: partial,picker,cards` with every GET, POST and file it sends to a custom page.
Use these only when the header names them; an older Starboard sends no header, and gets the page as before.

| Field or action | What it does |
|---|---|
| `"partial": {"menus": ["c1"]}`, in an answer to an action | Answer with only those menus and the items in them, and `said`. Starboard puts them in place of the ones it has, so the open menu, the scroll position and focus stay, and the changed control stays where it was on the page. `said` is shown beside the control that was changed, as a status a screen reader reads once. Answer with the whole list when a change moves other menus, such as a channel's number |
| `picker`, on an item with `pick` in its `actions` | `{"label", "title", "search", "filters": [[value, words]], "submit"}`: a button that opens a slide-out with a search box, a radio button for each filter (up to 8), and a tick box for each thing. Focus starts in the search box and goes back to the button when it closes |
| `{"action": "browse", "id", "value", "filter", "start"}` | Sent for each page of the slide-out: `value` is the search words, `filter` the filter chosen and `start` where the page starts. Answer `{"type": "picker", "items": [{"id", "title", "detail", "on"}], "total", "more"}`, up to 200 items; `on: true` shows one as added already, ticked and unchangeable. Starboard asks once for each filter and search while the slide-out is open, and again for **Show more** |
| `{"action": "pick", "id", "ids": [...]}` | Sent by the slide-out's Add button with every ticked id, up to 1000. Answer as for any action, with `said` |
| `"layout": "cards"` and `"hints": {"group": "sentence"}` | Each first-level menu is drawn as a small card with its title, its state and its detail, and each `group` of items as a card with the grey band, its heading and its sentence from `hints` (up to 200 characters). The All, Active and Inactive filter is left out, as each card shows its state |
| `image`, on an item | `{"src", "alt"}`: a small picture on the row, such as an uploaded logo. `src` is a PNG or JPEG data address, `data:image/png;base64,...`, of up to 64 KB, so the page never loads anything from the plug-in; `alt` says what it shows, up to 120 characters. Without `alt` it is left out |
| `detach_label`, in an item's `attach` | The words for `detach` in the row's More menu, up to 40 characters, such as `Remove the logo`, in place of **Remove guide** |

A link on an item that goes to the plug-in's own published port, such as a page on its own web server, opens at the
address the person opened Starboard with, at that port, as **Its web page** does. The plug-in only knows the
server's home network address (`STARBOARD_HOME_ADDRESS`), which a browser that reaches Starboard another way may not.

## Health

Answer GET on the `health` path with status 200 while the plug-in works. Keep it cheap. Starboard asks it when
someone opens **Settings**, then **Plug-ins**, at most once a minute, and waits 2 seconds. Any other answer shows
the plug-in as **Not answering**, with the reason. For plug-ins built into Starboard, it is also the container's
Docker health check, every 60 seconds. After an update, Starboard asks it every 3 seconds until it answers 200, for up
to `update.health_wait_seconds` (60 when left out), and goes back to the version before if it does not (API 1.14).
Answer 200 only once the plug-in can do its work, not as soon as the program starts.

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
| `request.available` | `title`, `year`, `kind` (`Film` or `Series`), `by` (who asked) | Reelix's or Seerr's newest 30 requests, checked every 5 minutes: one that becomes Available or Completed. API 1.11 |
| `download.failed` | `title`, `app`, `reason` | The download queue, checked every 5 minutes: an item that shows a problem. API 1.11 |
| `disk.nearly_full` | `disk` (its name), `percent`, `free` (bytes) | The disks on **System**, checked every 5 minutes: one that reaches the alerts' **Disk nearly full** limit, or 90% when it is not set. Sent again only after it drops 2 points under that limit. API 1.11 |
| `disk.changed` | `action` (`add`, `remove` or `balance`), `state` (`done` or `failed`), `disk` (its name), `erased` (the names of disks it erased), `result` | The pool helper's job record, checked every 5 minutes: a job that finished since the last check, however it was asked for. API 1.16 |
| `update.available` | `app`, `current`, `latest` | What Starboard already knows, checked every 5 minutes: a new Starboard release (its own check, at most every 6 hours), an app image from the last check on **Apps**, **Updates**, and a plug-in version from a catalogue. Nothing extra is fetched. API 1.11 |

For the events checked every 5 minutes, the first check after Starboard starts only sets a starting point,
so nothing old is sent, and something that comes and goes between two checks is not found.

## Jobs

Starboard runs plug-in jobs on its own clock, which wakes every 5 minutes while an active plug-in has a job. A job
is a POST with an empty body to the job's `path`.

- `daily` runs within 5 minutes after its time, in the server's own time zone.
- `every_hours` runs when that many hours have passed since it last started.
- `at_start` runs once after each start of Starboard.
- `schedule` (API 1.14) runs on the schedule the person chose in one of the plug-in's settings: every day, every week
  on a day, or every month on a date (the last day in a shorter month), at a time. It runs within 5 minutes after
  that time, or up to 6 hours late if the server was off, otherwise at the next time. Read
  [A job on a schedule from its settings](plugin-manifest-reference.md#a-job-on-a-schedule-from-its-settings).
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
| `/run/starboard/settings.json` | The settings, as one JSON object of `key` and value, secrets included. A `schedule` setting is an object, such as `{"every": "month", "date": 31, "time": "03:30"}` (API 1.14) |
| `/run/starboard/key` | The plug-in's own API key, as one line of text. Starboard makes a new one each time the plug-in starts or updates and revokes the old one, so read the file for each call, not once at start-up (Starboard's helper does). The key ends 30 days after it was last used |
| `/run/starboard/jellyfin.json` | Only with `jellyfin:key`: `{"url": ..., "api_key": ...}`. An address on the server itself is given as `host.docker.internal` |
| `/run/starboard/reelix.json` | Only with `reelix:key` (API 1.6): `{"url": ..., "api_key": ...}`, Reelix's address and key |
| `/run/starboard/usenet.json` | Only with `usenet:servers` (API 1.6): `{"servers": [{"name", "host", "port", "ssl", "user", "password", "connections", "level"}]}`, the active news servers from NZBGet (or SABnzbd), first choice first. Use fewer connections than `connections`: the download app uses the same account |
| `/run/starboard/api.sock` | Starboard's API, for a plug-in on its own network or the VPN, which has no other way to reach it. Only while the plug-in is active |
| `/data` | Only with the `data` volume: its own folder, read and write |

And these environment variables, with the `env` from the manifest:

| Name | Value |
|---|---|
| `STARBOARD_API` | On the `lan` network, `http://host.docker.internal:<Starboard's port>/api/v1/`. On the `default` network or the VPN, `http://starboard:8095/api/v1/`: use only its path, and send the request to `STARBOARD_API_SOCKET` |
| `STARBOARD_API_KEY_FILE` | `/run/starboard/key` |
| `STARBOARD_API_SOCKET` | `/run/starboard/api.sock`, on every network |
| `STARBOARD_HOME_ADDRESS` | Only for a container with `publish` on the `lan` network (Starboard 0.23.0 and later): its own address on the home network, such as `http://192.168.1.20:8790`, the server's address and the port Starboard chose. Give it to Jellyfin or a device that needs to reach the plug-in, rather than asking the person to open its page first |

Starboard runs on the server's own network, so it cannot join a plug-in's own network, which stays internal: a
plug-in on the `default` network can reach nothing outside it, Starboard's port included. Starboard listens for it
on a Unix socket in its run folder instead, `STARBOARD_API_SOCKET`. Send the same HTTP requests to that socket, with
the path from `STARBOARD_API`, any `Host` and the plug-in's own key. The socket answers only `/api/v1`, and only to
that plug-in's key: another key is refused with `401`. A plug-in with no container on the `lan` network can reach no other address, so its key works on the socket alone, and the port refuses it. A plug-in on the `lan` network may use either. The helper
`sbplugin.py` in the example plug-ins uses the socket whenever `STARBOARD_API_SOCKET` names one that is there.

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

- Starboard stops that container once three things are all true for `idle_stop_minutes` (15 when left out):
  Starboard has not called it, its network has been quiet, and it has used almost no processor time.
- Network traffic keeps it running, so Jellyfin or another app streaming from it straight away does not count as
  idle. So does processor time (more than 0.3 seconds a minute), so a plug-in that is converting a file or shrinking
  pictures is never stopped in the middle of its work, even with no network traffic. A container on the VPN shares Gluetun's network, so Starboard cannot tell, and it never rests.
- The next time Starboard calls it, for a card, a button, its own page, an event or a job, Starboard starts it
  first and waits up to 20 seconds for it to answer.
- Only Starboard can start it again. Use `when_needed` only when Starboard is how people reach it.
- Only the first container can rest. The tester warns about `when_needed` on any other container, which runs
  always.

## The plug-in's API key

Every plug-in with a container gets its own key to [Starboard's API](api-reference.md), made when it is added.

- It is named `Plug-in:` and the plug-in's name, and it can only read, with one exception from API 1.17: a plug-in
  approved `alerts:send` may raise and clear its own alerts. Read [Sending alerts](#sending-alerts-api-117).
- Its scopes are the read permissions the person approved: `apps:read` gives `apps`, `downloads:read` gives
  `downloads`, `media:read` gives `media` and `system:read` gives `system`.
- It does not expire. It stops working when the plug-in is removed.
- When an update or **Roll back** changes the read permissions, Starboard revokes the key and writes a new one to
  the same file. Read the file again when a call answers `401`.
- With the `default` network, Starboard's API, through `STARBOARD_API_SOCKET`, is the only thing the plug-in can
  reach.

Send it as for any key, through the socket when there is one:

```python
import http.client, json, os, socket, urllib.parse

class Starboard(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.settimeout(10)
        self.sock.connect(os.environ["STARBOARD_API_SOCKET"])

key = open(os.environ["STARBOARD_API_KEY_FILE"]).read().strip()
path = urllib.parse.urlsplit(os.environ["STARBOARD_API"]).path + "downloads"
c = Starboard("localhost", timeout=10)
c.request("GET", path, headers={"Authorization": "Bearer " + key})
print(json.load(c.getresponse())["items"])
```

The rules for every key, such as 120 requests a minute, are in [Authentication and keys](api-authentication.md).

## Sending alerts (API 1.17)

A plug-in with the `alerts:send` permission may send alerts through Starboard, to where Starboard sends its own:
ntfy, Gotify or a webhook, set in Settings, General, Alerts, and plug-ins that pass them on, such as Notifications. It sends
`POST /api/v1/plugin/alerts` (Starboard API 1.8.0) with its own key, through `STARBOARD_API_SOCKET`, or over HTTP
for a plug-in on the `lan` network.

```json
{"key": "check-router", "state": "raised", "title": "Router is not answering",
 "message": "Ping: no answer for 3 checks in a row.", "level": "problem"}
```

| Field | What it is | Rules |
|---|---|---|
| `key` | Your own name for the alert, such as `check-router` | Required. 1 to 80 letters, numbers, dots, colons, underscores and hyphens |
| `state` | `raised` when something is wrong, `cleared` when it is right again | Required |
| `title` | The alert's heading | Required to raise; optional to clear. One line, up to 120 characters |
| `message` | What happened | Up to 500 characters. Starboard puts your plug-in's name in front, such as "Network check: Ping: no answer for 3 checks in a row." |
| `level` | `problem`, `warning` or `info` | `problem` when left out. It sets the alert's priority, as for Starboard's own |

The answer is `{"ok": true, "sent": true}`, or `"sent": false` when nothing was sent: the alert was already raised,
there was nothing to clear, or alerts are off in Settings, General, Alerts.

- **Once until cleared.** Each `key` is raised once. Send `raised` as often as you check: it is sent again only after
  you send `cleared`. Then it is sent as Starboard's own alerts are: to the alert channel, as the `alert.raised` and
  `alert.cleared` events, and in Starboard's log.
- **Alerts off.** When alerts are off in Settings, General, Alerts, nothing is sent, as for Starboard's own.
- **Limits.** Up to 30 new alerts an hour for each plug-in. Beyond that the answer is `429 rate_limited` with
  `Retry-After`, the seconds to wait. Raising one that is already raised, and clearing, never count.
- **Errors.** A body that does not follow the rules gets `400 bad_request` saying what to change. Any key but the
  plug-in's own, a plug-in without `alerts:send`, or one that is not active, gets `404 not_found`.
- **Removed.** When the plug-in is removed, its alerts are forgotten without a word.
- Every call is written to the audit log, as every change through the API is.

```python
import http.client, json, os, socket, urllib.parse

class Starboard(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.settimeout(10)
        self.sock.connect(os.environ["STARBOARD_API_SOCKET"])

key = open(os.environ["STARBOARD_API_KEY_FILE"]).read().strip()
path = urllib.parse.urlsplit(os.environ["STARBOARD_API"]).path + "plugin/alerts"
alert = {"key": "check-router", "state": "raised", "title": "Router is not answering",
         "message": "Ping: no answer for 3 checks in a row.", "level": "problem"}
c = Starboard("localhost", timeout=10)
c.request("POST", path, body=json.dumps(alert),
          headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
print(json.load(c.getresponse()))  # {"ok": true, "sent": true}
```

When the router answers again, send `{"key": "check-router", "state": "cleared", "title": "Router is answering again"}`.

## Holding heavy jobs (API 1.24)

A plug-in with the `power:hold` permission may ask Starboard to hold its heavy automatic work, for example while the UPS and
power plug-in sees the computer run on battery. It sends `POST /api/v1/plugin/hold` (Starboard API 1.12.0) with its own key,
through `STARBOARD_API_SOCKET`, or over HTTP for a plug-in on the `lan` network.

```json
{"on": true, "reason": "On battery", "minutes": 10}
```

| Field | What it is | Rules |
|---|---|---|
| `on` | `true` starts or renews the hold, `false` lets it go | Required |
| `reason` | A line people read, such as "On battery" | Up to 80 characters, one line. "On battery" when left out |
| `minutes` | How long the hold lasts if it is not renewed | A whole number from 1 to 30. 10 when left out |

The answer is `{"ok": true, "held": true, "reason": "On battery", "until": 1795364538, "by": "UPS and power"}`. `held` is
`false` when nothing is held. If more than one plug-in holds, the answer is about the hold that lasts longest.

- **What is held.** Starboard's own background jobs (Live TV, watch history, listening progress and the automatic updates of
  Starboard, Reelix, apps and plug-ins), its scheduled backups, the scheduled jobs of other plug-ins, and downloads, which pause as
  Download hours pauses them, even when Download hours is off and even after a person chose Resume now.
- **What is not held.** Anything a person starts with a click, the two light jobs (Jellyfin user defaults and VPN port
  forwarding), and your own plug-in's jobs.
- **It ends by itself.** Ask again before `minutes` pass to keep it. A plug-in that stops, crashes or loses its network
  cannot hold Starboard for ever. A good rhythm is to ask every minute with `minutes` of 5 while on battery, and to send
  `"on": false` as soon as the mains power is back.
- **Held work resumes.** What was due while the hold lasted starts at the next check after it ends, within a minute.
  Downloads that Starboard paused start again at once; downloads a person had stopped stay stopped.
- **Starboard restarts.** A hold is kept in memory only, so ask again after Starboard starts. Your next call does that.
- **People see it.** The Downloads page says why downloads are paused, and Starboard's log says when a hold starts and ends.
- **Errors.** A body that does not follow the rules gets `400 bad_request` saying what to change. Any key but the plug-in's
  own, a plug-in without `power:hold`, or one that is not active, gets `404 not_found`.
- Every call is written to the audit log, as every change through the API is.

```python
import http.client, json, os, socket, urllib.parse

class Starboard(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.settimeout(10)
        self.sock.connect(os.environ["STARBOARD_API_SOCKET"])

key = open(os.environ["STARBOARD_API_KEY_FILE"]).read().strip()
path = urllib.parse.urlsplit(os.environ["STARBOARD_API"]).path + "plugin/hold"
c = Starboard("localhost", timeout=10)
c.request("POST", path, body=json.dumps({"on": True, "reason": "On battery", "minutes": 5}),
          headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
print(json.load(c.getresponse()))  # {"ok": true, "held": true, ...}
```

## States

Starboard keeps one state for each plug-in, and shows each with one sentence and one button.

| State | What it means | The button |
|---|---|---|
| `installed` | Added, not started yet. From Starboard 0.23.0 a plug-in is activated as soon as it is installed, so it stays `installed` only when it needs setting up first or did not start | **Activate** |
| `enabled` | Active and running | **Deactivate** |
| `disabled` | Deactivated: stopped, with its settings and data kept | **Activate** |
| `failed` | It did not start, or stopped answering. The message says why | **Try again**, or **Roll back** to the version before within 10 minutes of an update |
| `needs-setup` | A required setting is empty, or `setup_required` and it has never been set up | **Finish setting up** |
| `not-supported` | Shown as **Needs an update**. This Starboard cannot run the plug-in: its `starboard_api` leaves out this Starboard's plug-in API, or it uses something this Starboard no longer has. Starboard stops it, keeps its settings and data, and says why | **Check for an update** |

The first four are stored in the plug-in's `state.json`. Starboard works out `needs-setup` and `not-supported` each
time, and a plug-in in either cannot be activated. When Starboard starts, it stops every active plug-in that is
**Needs an update**. It stops the containers, never removes them, and keeps the settings, data and key. Docker does not
start a stopped container again, whatever its restart policy says. **Deactivate all plug-ins** stops every active plug-in at once.

## Updates and Roll back

- When a catalogue lists a newer version, the plug-in's page offers **Update to** and that version. Starboard
  shows the same warning as when adding it, with any new permissions marked, **What is new since** the installed
  version from the new version's `changes`, the settings that move, and how the update is kept safe. It asks for the
  password. **Update from an address** does the same for a plug-in that is not in a catalogue.
- The update runs as steps, in a dialog: **Asking it to get ready** (`update.before`), **Moving its settings**
  (`update.migrations`), **Installing the new version**, **Waiting for it to answer** (`health`, for up to
  `update.health_wait_seconds`) and **Asking it to tidy up** (`update.after`). A step that does not apply is left out.
  Read [Updates](plugin-manifest-reference.md#updates) for each one. API 1.14.
- Settings stay, moved by the new version's migrations. A new setting gets its `default`.
- An active plug-in is started again on the new version. If it does not start, or does not answer its health path in
  time, Starboard goes back to the version before by itself, with its settings as they were, and says why on the
  plug-in's **State**, in the log and in an alert.
- Starboard keeps the version before in `data/plugins/<id>/previous/`: its manifest, settings, Compose file and logo.
  Only one earlier version is kept.
- **Roll back** swaps the two, with no download, and asks for the password. It calls `update.before` on the version
  running and `update.after` on the one brought back. The newer version is kept in its place.
- Plug-ins built into Starboard update with Starboard.
- One update runs at a time. Each update and roll back is written to the audit log (`update_started`,
  `plugin_updated`, `plugin_update_rolled_back`, `plugin_rolled_back`, `update_finished`).
- After an update, a Roll back or an update from an address, the plug-in's **State** shows **What is new**: the
  changes between the two versions from the manifest's `changes` (API 1.10), or the catalogue's line when it has
  none. **Got it** hides it on every device. Read [Changes](plugin-manifest-reference.md#changes).
- Starboard's API can do the same with a key that has the `updates` scope: read
  [Updates through the API](#updates-through-the-api).

### The update steps a plug-in answers (API 1.14)

Starboard sends each step to the main (first) container, on the plug-in's own network, as `POST` with JSON:

| Step | Sent to | Body | Answer |
|---|---|---|---|
| Before | The installed version's `update.before.path` | `{"from": "1.0.0", "to": "2.0.0"}` | 2xx and `{"ok": true, "said": "No job was running"}` when it is ready; `{"ok": false, "said": "A scan is half way"}` or any other status stops the update |
| After | The running version's `update.after.path` | `{"from": "1.0.0", "to": "2.0.0", "outcome": "updated"}`, or `"rolled_back"` | 2xx and `{"ok": true, "said": "..."}`; anything else is said, and the update stays |

`said` is shown in the update's steps, up to 200 characters. Answer within `time_limit_seconds`. A resting container
is started first, as for any call. Keep both steps short and safe to run twice: a person may update, roll back and
update again.

### Updates through the API

A key made with **Read and manage** and the `updates` scope ticked can list what can be updated, start an update to
the version Starboard already knows of, follow its steps and roll a plug-in back: `GET /api/v1/updates`,
`POST /api/v1/updates`, `GET /api/v1/updates/runs/{id}` and `POST /api/v1/updates/rollback`. Read
[the API reference](api-reference.md#updates). A plug-in's own key never has this scope.

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
| `published` | `false` shows it as **Not published**, with no way to add it |
| `versions` | Up to 50, in any order |
| `version` | The plug-in's version |
| `starboard_api` | The range it needs, as in the manifest. Left out, it fits any Starboard |
| `manifest` | Required: the `https` address of that version's `starboard-plugin.json` |
| `manifest_sha256` | The SHA-256 of that file, 64 hex characters |
| `changelog`, `released` | Shown with an update. Up to 600 and 10 characters |
| `recommended` | `true` puts the entry in **Recommended** at the top of the collection, with a Recommended chip. Only Starboard's own collection may recommend; other catalogues' entries are listed as usual. Nothing is added until the person chooses it (API 1.14) |
| `logo`, `logo_alt` | The plug-in's logo for the Catalogue, before it is added: a data address, `data:image/svg+xml;base64,...` or `data:image/png;base64,...`, of up to 24 KB, and what it shows in words (3 to 80 characters). Checked and cleaned as a logo file is; left out when it fails or has no `logo_alt`. The plug-ins repository's `tools/make_examples.py` can fill both from each plug-in's `logo` (API 1.14) |
| `rest` | For an app plug-in: `{"memory_mb": 117, "cpu_percent": 0.22}`, what it uses at rest, measured. Shown under it in the catalogue (API 1.13) |

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
- [Write a plug-in that updates safely](update-a-plugin-safely.md)
- [API reference](api-reference.md)
- [What a plug-in can change](../basics/what-plugins-can-change.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
