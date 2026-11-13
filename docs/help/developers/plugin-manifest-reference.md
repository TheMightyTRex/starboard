[Help centre](../README.md) · Developers

# Plug-in manifest reference

Every field of `starboard-plugin.json`, version 1, with the check Starboard runs on it and why. Starboard refuses
any field it does not know, so a mistake cannot slip through. This page matches plug-in API 1.12.0
(`API_VERSION` in `starboard/plugins.py`).

The same rules are in a JSON Schema, `starboard/plugin-manifest.schema.json`, for editors and other tools. The
check in `starboard/plugins.py` is what Starboard itself runs, and the [plug-in tester](test-and-publish-a-plugin.md#test-it)
runs it too. For a first plug-in, read [Make your first plug-in](make-a-plugin.md).

## The top level

| Field | Required | What it is | Check |
|---|---|---|---|
| `manifest_version` | yes | The manifest's format | Must be `1` |
| `id` | yes | Its id, used in folders, containers and addresses | 3 to 40 lower case letters, numbers and hyphens; starts and ends with a letter or number |
| `name` | yes | What people read | Text, up to 40 characters |
| `version` | yes | Its version | A version such as `1.2.0`, optionally with `-beta.1` |
| `description` | yes | One sentence about what it does | Text, up to 200 characters |
| `author` | yes | Your public name | Text, up to 60 characters |
| `licence` | yes | Its licence | An SPDX licence id, such as `MIT` |
| `homepage` | yes | Its page | An `https` address |
| `support_url` | yes | Where people report problems | An `https` address |
| `starboard_api` | yes | The plug-in API versions it works with | A range such as `>=1.0 <2.0`, using `>=`, `>`, `<=`, `<` and `=`; this Starboard's API must be inside it |
| `permissions` | yes | What it may do | A list from [Permissions](#permissions); may be empty |
| `containers` | no | The small apps Starboard runs for it | One to four; none only for a plug-in with only `styles` |
| `resources` | no | Memory and processor for each container | Read [Resources](#resources) |
| `settings` | no | Its settings, drawn by Starboard | Read [Settings](#settings) |
| `setup_required` | no | It must be set up before it can start | `true` or `false`. API 1.4 |
| `cards` | no | Its dashboard cards | Read [Cards](#cards) |
| `actions` | no | Its buttons | Read [Actions](#actions) |
| `health` | no | A path that answers 200 while it works | A path such as `/health` |
| `needs` | no | Apps it needs, shown before install | A list of app names such as `jellyfin`: 2 to 30 lower case letters, numbers and hyphens |
| `styles` | no | Styles for **Display** | Read [Styles](#styles) |
| `notices` | no | Things people must know before install | Read [Notices](#notices). API 1.4 |
| `events` | no | Events Starboard sends it | Read [Events](#events). API 1.4 |
| `jobs` | no | Jobs Starboard runs for it | Read [Jobs](#jobs). API 1.4 |
| `changes` | no | What changed in each version, shown as **What is new** after an update | Read [Changes](#changes). API 1.10 |

## Permissions

Each permission is shown in plain words with its risk before anyone adds the plug-in. Ask only for what you use:
people read every one, and the plug-in's API key gets only the read permissions it asked for.

| Permission | What people read | Risk | Key scope |
|---|---|---|---|
| `apps:read` | See your apps and whether they answer | low | `apps` |
| `downloads:read` | See what is downloading | low | `downloads` |
| `media:read` | See your films, series and books (the media folder, read only, and the library) | medium | `media` |
| `system:read` | See processor, memory and disks | low | `system` |
| `network:lan` | Reach other computers on your home network | medium | none |
| `network:vpn` | Run inside your VPN connection | medium | none |
| `jellyfin:key` | Use Jellyfin's API key, kept by Starboard | high | none |
| `reelix:key` | Use Reelix's API key, kept by Starboard (API 1.6) | high | none |
| `usenet:servers` | Use your news server's address and sign-in, from NZBGet or SABnzbd (API 1.6) | high | none |
| `appearance:styles` | Add styles to Display: colours, corners, a font and shadows, checked for accessibility | low | none |

The plug-in's risk is its highest permission's risk. Read [What a plug-in can change](../basics/what-plugins-can-change.md)
for how people see this.

## Containers

Each item in `containers` is one container. Starboard always calls the **first** one for cards, buttons, custom
settings, events and jobs.

| Field | What it is | Check |
|---|---|---|
| `name` | Its short name | Lower case letters, numbers and hyphens, up to 21 characters, different from the others |
| `image` | Its image | Pinned by digest: `registry/name@sha256:` and 64 hex characters. Read [Security rules](#security-rules) |
| `port` | The port it answers on | 1 to 65535. Starboard uses 80 when it is left out |
| `network` | Which network it joins | `default`, `lan` or `vpn`. Read [Networks](#networks) |
| `volumes` | Folders it gets | `data`, `media:ro` or `media/<one folder>`. Read [Volumes](#volumes) |
| `env` | Settings passed as environment variables | Names in `UPPER_CASE`; values text, numbers or `true` and `false` |
| `start` | When it runs | `always` (the default) or `when_needed`, for the first container only. Read [Resting when idle](plugin-api-reference.md#resting-when-idle) |
| `idle_stop_minutes` | For `when_needed`: minutes idle before it rests | A whole number; 15 when left out |
| `publish` | Puts `port` on Gluetun for the home network (plug-in API 1.9) | true or false; only with `network: vpn` and a `port` |
| `user` | The user it runs as | `uid:gid` such as `1000:1000`, never root (uid 0); `10001:10001` when left out. From API 1.12, `media`: the media folder's owner, only for a container that mounts `media/<one folder>`. Read [Adding files to the media folder](#adding-files-to-the-media-folder) |
| `command` | The command it runs | Only plug-ins built into Starboard may set it |

The container's name on the server is `plugin-<id>-<name>`, such as `plugin-hello-card-main`.

### Networks

| Value | What it reaches | Permission needed |
|---|---|---|
| `default` | Only Starboard, on the plug-in's own network, which has no way out | none |
| `lan` | Also your home network and the internet, and the server itself as `host.docker.internal` | `network:lan` |
| `vpn` | The internet through your VPN: it runs inside Gluetun's network | `network:vpn` |

### Volumes

| Value | Where the plug-in sees it | Permission needed |
|---|---|---|
| `data` | `/data`, read and write: its own folder, `data/plugins/<id>/data/<container name>` | none |
| `media:ro` | `/media`, read only: the whole media folder | `media:read` |
| `media/<one folder>` | `/media/<one folder>`, read and write: one folder in the media folder, such as `media/music` | none, but people see it as something it can change |

Nothing else can be mounted. The folder name after `media/` is 1 to 60 letters, numbers, dots, underscores and
hyphens, so it cannot climb out with `..`.

### Adding files to the media folder

A container that adds files to `media/<one folder>`, such as a sound track next to a film in `media/movies`, needs to
write as the folder's owner. From API 1.12, give it `"user": "media"`:

- It runs as the media folder's owner, the apps' user and group from **Install apps** (1000:1000 when Starboard does
  not know them), never root.
- Before it starts, Starboard makes each `media/<one folder>` it mounts that is missing, owned by the user it runs as.
  A folder that is there already is left as it is.
- People read, before they add it, the folders it can change and that it runs as the media folder's owner.

Ask for the fewest folders you need. Never delete the person's files: move them to a folder of your own and let them
delete it.

### Security rules

Starboard writes each plug-in's Compose file itself, `data/plugins/<id>/compose.yaml`, and the plug-in cannot change
what it writes. Each rule is there for one reason.

- **Images pinned by digest.** A tag such as `:latest` can point at different code tomorrow. A digest cannot, so
  what people approved is what runs. The tester's development box allows a tag only while you test.
- **No Docker socket, no privileged mode, no devices, no host network.** Any of these would give the plug-in
  control of the whole computer. No manifest field can ask for them.
- **Only the volumes above.** A plug-in sees its own folder and, if allowed, the media folder. It never sees other
  apps' settings or Starboard's own data.
- **Never root.** `user` must not be uid 0. A program running as root inside a container is one mistake away from
  root on the server.
- **Read only, with no extra rights.** Every container runs with a read-only file system and a 64 MB `/tmp`, every
  Linux capability dropped, no new privileges, and at most 64 processes.
- **Its own network.** With `default`, the plug-in reaches Starboard and nothing else.

### Resources

`resources` maps a container's `name` to its limits:

```json
"resources": {"main": {"memory": 256, "cpus": 0.5}}
```

| Field | What it is | Default | Ceiling |
|---|---|---|---|
| `memory` | Memory in MB | 128 | 512 |
| `cpus` | Processor cores | 0.25 | 1.0 |

The ceilings keep Starboard light on small servers, such as a Raspberry Pi. People see each container's limits
before they add the plug-in.

## Settings

Starboard draws a plug-in's settings in its section of **Settings**, then **Plug-ins**, checks each value, and saves
them in the plug-in's `settings.json`. Read [Settings and key files](plugin-api-reference.md#settings-and-key-files).

| Field | What it is |
|---|---|
| `key` | Its name in `settings.json`: lower case letters, numbers and underscores, starting with a letter, up to 41 characters. Required |
| `label` | What people read. Required. Keep it under 60 characters, in sentence case, with no colon |
| `type` | One of the types below. Required |
| `hint` | One sentence under the field |
| `default` | Its value when the plug-in is added, or when an update adds the setting |
| `min`, `max`, `unit` | For `number` |
| `choices` | For `choice`: the list to choose from, each a value such as `"eng"` or, from API 1.5, `{"value": "eng", "label": "English"}` so people read words, not codes. For `custom`: the path that gives its choices |
| `required` | `true` when the plug-in cannot start without it. API 1.4 |
| `group` | The section it goes in, such as `Picture and sound`: up to 40 characters, in sentence case. Settings without one go in **Settings**. API 1.5 |
| `restart`, `item` | Accepted, reserved for later |

| Type | What people get | What Starboard checks |
|---|---|---|
| `text` | A text box | Up to 500 characters |
| `number` | A number box | A number from `min` to `max` |
| `switch` | Activate or deactivate | Saved as `true` or `false` |
| `choice` | A list | One of `choices` |
| `address` | An address box | An address Starboard is allowed to call |
| `secret` | A password box | Never sent back to the browser; shown as set or not set. Up to 2000 characters |
| `folder` | Browse, inside what the plug-in mounts | A folder inside `/media` or `/media/<one folder>`. Needs a container that mounts `media:ro` or `media/<one folder>`. API 1.3 |
| `list` | Several values | Up to 200, each up to 500 characters |
| `custom` | A list the plug-in describes, drawn by Starboard | `choices` is a path on the plug-in. Read [Custom screens](plugin-api-reference.md#custom-screens) |

### Setting up before it starts

- A setting with `"required": true` and no value keeps the plug-in in the `needs-setup` state, and Starboard says
  which settings are missing.
- `"setup_required": true` keeps it there until its settings have been saved once with nothing required missing.
- People are told before install that it needs setting up.

Both came in API 1.4. Read [States](plugin-api-reference.md#states).

### How Starboard lays them out

Starboard draws every plug-in's settings the same way, as Starboard's own Settings pages are drawn:

- Each `group` is its own section, with a topic tab, in the order the groups first appear. Settings with no group
  come first, under **Settings**. Use groups once a plug-in has more than about six settings.
- Switches, choices, numbers and folders save as soon as they change, with **Saved at** and the time beside them.
- Text, addresses, secrets, lists and required numbers are one form per section with one **Save** at its foot.
- The plug-in's `actions` are buttons in an **Actions** section, after its settings and screens.

## Cards

Each item in `cards` is a card people can add with **Edit dashboard**. Read
[Card answers](plugin-api-reference.md#card-answers) for what the path answers.

| Field | What it is | Check |
|---|---|---|
| `id` | Its id, in the card's address | Letters, numbers, hyphens and underscores, up to 40. Give every card one |
| `title` | Its name on the dashboard | A card needs a `title` (or a `label`), so a screen reader can name it |
| `type` | `stat`, `list`, `status` or, from API 1.8, `guide` | Required |
| `path` | The path on the first container that answers | Required: starts with `/`, up to 80 letters, numbers, `/`, `_`, `.` and `-` |
| `format` | For `stat`: `number`, `bytes`, `percent`, `duration` (seconds) or `date` (seconds since 1970) | `number` when left out |
| `label` | Another name for the card | Optional |
| `example` | What the path answers | The tester checks its shape, and warns when it is missing |
| `refresh_minutes` | How often Starboard asks | Minutes between asks, 1 to 1440; 1 when left out. Starboard never asks more often than once a minute. API 1.4 |

## Actions

Each item in `actions` is a button in the plug-in's section of **Settings**, then **Plug-ins**. Read
[Actions](plugin-api-reference.md#actions) for what Starboard sends.

| Field | What it is |
|---|---|
| `id` | Its id: letters, numbers, hyphens and underscores, up to 40. Give every button one. A button without one is known by its place in the list, counting from 0, which changes when you move it |
| `label` | The words on the button, saying what it does, such as `Run Live TV now`. Required |
| `path` | The path on the first container that Starboard sends a POST to. Required |
| `confirm` | Accepted, reserved for a question before the button runs |

## Health

`health` is a path, such as `/health`, that answers 200 while the plug-in works. Keep it cheap: no calls to other
apps. The tester warns when a plug-in with containers has none. Starboard asks it when **Settings**, then
**Plug-ins**, is opened, and shows **Not answering** when it does not answer 200. For plug-ins built into
Starboard, it is also the container's health check.

## Styles

`styles` lists 1 to 32 styles for **Display** (16 before API 1.2), and needs the permission `appearance:styles`.
Each style has an `id`, a `name`, and a `light` and a `dark` set of colours. Starboard checks every style for
contrast in light and dark before it can be added. A plug-in with only styles runs no container. Read
[Styles in Write a plug-in](../basics/write-a-plugin.md#styles), and the JSON Schema for every style field.

## Notices

`notices` lists what people must know before they add the plug-in. Each is shown with the install warning. API 1.4.

| Notice | What people read |
|---|---|
| `p2p` | Shares files with other people over the internet, which can show your internet address |
| `adult` | Has adult content |

## Events

`events` lists the events Starboard sends the plug-in. Each needs the read permission that already covers what it
tells, and a container to send it to. API 1.4. Read [Events](plugin-api-reference.md#events) for what each one
sends.

| Event | When | Permission needed |
|---|---|---|
| `item.added` | When something new arrives in your library | `media:read` |
| `download.finished` | When a download finishes | `downloads:read` |
| `app.down` | When one of your apps stops answering | `apps:read` |
| `app.up` | When one of your apps answers again | `apps:read` |
| `playback.started` | When someone starts playing something | `media:read` |
| `request.available` | When something someone asked for is ready to watch. API 1.11 | `media:read` |
| `download.failed` | When a download stops with a problem. API 1.11 | `downloads:read` |
| `disk.nearly_full` | When a disk is nearly full. API 1.11 | `system:read` |
| `update.available` | When an update is ready for Starboard, an app or a plug-in. API 1.11 | `apps:read` |

## Jobs

`jobs` lists up to eight jobs that Starboard runs for the plug-in on its own clock. They need a container to run
in. API 1.4. Read [Jobs](plugin-api-reference.md#jobs) for what Starboard sends.

| Field | What it is | Check |
|---|---|---|
| `id` | Its id | Lower case letters, numbers and hyphens, starting with a letter, up to 31; different from the others |
| `label` | What people read in **System**, then **Jobs** | Required, up to 60 characters |
| `path` | The path on the first container | Required |
| `daily` | A time each day, such as `03:30` | Give exactly one of `daily`, `every_hours` and `at_start` |
| `every_hours` | Every so many hours | A whole number from 1 to 168 |
| `at_start` | Once each time Starboard starts | Must be `true` |
| `time_limit_minutes` | How long it may take | 1 to 120; 10 when left out |
| `quiet_hours` | Run only in quiet hours | `true` or `false` |

```json
"jobs": [
  {"id": "tidy", "label": "Tidy old files", "path": "/jobs/tidy", "daily": "03:30", "time_limit_minutes": 20, "quiet_hours": true}
]
```

## Changes

`changes` lists what changed in each version, newest first, in the types of
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Copy the lines from your `CHANGELOG.md`. After an update, a
Roll back or an update from an address, the plug-in's **State** shows **What is new** with the versions between the
one people had and the one they have now: each type's first line, and **All changes** for the rest. It stays until
someone chooses **Got it**, which Starboard keeps, so it is not shown again on any device. API 1.10.

| Field | What it is | Check |
|---|---|---|
| `version` | The version these changes are in | Required. A version such as `1.2.0`, different from the others |
| `date` | When it was released | A date such as `2026-11-13` |
| `added`, `changed`, `deprecated`, `removed`, `fixed`, `security` | The changes of that type | Give at least one. Each lists 1 to 20 lines of up to 300 characters |

Up to 20 versions. A line may use `**bold**` and `` `code` ``; Starboard shows them as text, never as HTML.
Start each line with what people notice, in a few words.

```json
"changes": [
  {"version": "1.1.0", "date": "2026-11-12", "added": ["**Three new styles:** Sunset, Graphite and Editorial"],
   "fixed": ["A style chosen on a phone is kept after Starboard restarts"]},
  {"version": "1.0.0", "date": "2026-11-10", "added": ["The first ten styles"]}
]
```

## What each API version added

| Version | Date | Added |
|---|---|---|
| 1.0 | 10 November 2026 | The manifest, containers, permissions, settings, cards, actions, health, needs and styles (up to 16) |
| 1.1 | 11 November 2026 | Styles may set more colours, a heading font and weight, and the focus width |
| 1.2 | 12 November 2026 | Styles may also set card, button, border, tab, header, side menu and chip styles; up to 32 styles |
| 1.3 | 12 November 2026 | The `folder` setting: a folder inside the media folders the plug-in mounts, chosen with Browse |
| 1.4 | 12 November 2026 | `required` settings, `setup_required`, `notices`, `events`, `jobs` and card `refresh_minutes` |
| 1.5 | 12 November 2026 | A setting's `group`, and choices with a `label` |
| 1.6 | 12 November 2026 | The `reelix:key` and `usenet:servers` permissions, with `/run/starboard/reelix.json` and `/run/starboard/usenet.json` |
| 1.7 | 13 November 2026 | Sub menus in a custom setting's list: `menus`, and `menu` on its items and switches |
| 1.8 | 13 November 2026 | Sections with tables in a custom setting's list, selecting several, guides, and notices with progress |
| 1.9 | 13 November 2026 | `publish` on a container with `network: vpn` |
| 1.10 | 13 November 2026 | `changes`: what changed in each version, shown as **What is new** after an update |
| 1.12 | 13 November 2026 | `"user": "media"` on a container that mounts `media/<one folder>`; `link` and `state_label` on a custom setting's item; `file_only` on its add box |
| 1.11 | 13 November 2026 | Four more events (`request.available`, `download.failed`, `disk.nearly_full`, `update.available`), and `readonly` on a custom setting's list with folds |

Use the lowest version that has what you use in `starboard_api`, such as `">=1.4 <2.0"` for a plug-in with jobs.
Read [API changelog](api-changelog.md).

## Find out more

- [Make your first plug-in](make-a-plugin.md)
- [Plug-in API reference](plugin-api-reference.md)
- [Test and publish a plug-in](test-and-publish-a-plugin.md)
- [Write a plug-in](../basics/write-a-plugin.md)
- [What a plug-in can change](../basics/what-plugins-can-change.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
