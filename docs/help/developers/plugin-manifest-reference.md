[Help centre](../README.md) · Developers
<!-- help: dev / plugins -->

# Plug-in manifest reference

Every field of `starboard-plugin.json`, version 1, with the check Starboard runs on it and why. Starboard refuses
any field it does not know, so a mistake cannot slip through. This page matches plug-in API 1.22.0
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
| `starboard_tested` | no | The newest plug-in API version you tested with (API 1.22) | Text such as `1.22`. Starboard never refuses a plug-in for it; the plug-in tester says when it is missing or newer than this Starboard |
| `capabilities` | no | Optional parts it needs or uses, by name (API 1.22) | An object with `needs` and `uses`, each up to 12 names from [Capabilities](#capabilities-api-122). A plug-in that needs a name this Starboard does not have is not added, and a catalogue version that needs one is not offered |
| `permissions` | yes | What it may do | A list from [Permissions](#permissions); may be empty |
| `containers` | no | The small apps Starboard runs for it | One to four; none only for a plug-in with only `styles` |
| `resources` | no | Memory and processor for each container | Read [Resources](#resources) |
| `settings` | no | Its settings, drawn by Starboard | Read [Settings](#settings) |
| `setup_required` | no | It must be set up before it can start | `true` or `false`. API 1.4 |
| `cards` | no | Its dashboard cards | Read [Cards](#cards) |
| `actions` | no | Its buttons | Read [Actions](#actions) |
| `health` | no | A path that answers 200 while it works | A path such as `/health` |
| `needs` | no | Apps it needs, shown before install | A list of app names such as `jellyfin`: 2 to 30 lower case letters, numbers and hyphens |
| `requires` | no | The system it works with, shown as a tag | A list of up to four needs. Read [What it needs](#what-it-needs-requires). API 1.19 |
| `needs_plugins` | no | The plug-ins it needs | A list of up to 10 plug-in ids. Read [Plug-ins that need another plug-in](#plug-ins-that-need-another-plug-in-needs_plugins-and-switch). API 1.21 |
| `switch` | no | The setting that is the plug-in's main switch | The `key` of one of its own `switch` settings. Read [Plug-ins that need another plug-in](#plug-ins-that-need-another-plug-in-needs_plugins-and-switch). API 1.21 |
| `first_sign_in` | no | A password Starboard makes for the app and shows once on its page | Read [A first sign-in shown once](#a-first-sign-in-shown-once-first_sign_in). API 1.20 |
| `styles` | no | Styles for **Display** | Read [Styles](#styles) |
| `notices` | no | Things people must know before install | Read [Notices](#notices). API 1.4 |
| `events` | no | Events Starboard sends it | Read [Events](#events). API 1.4 |
| `jobs` | no | Jobs Starboard runs for it | Read [Jobs](#jobs). API 1.4 |
| `changes` | no | What changed in each version, shown as **What is new** before and after an update | Read [Changes](#changes). API 1.10; before the update since API 1.14 |
| `adopt` | no | An app the main install may already run, which Starboard can copy into the plug-in | Read [App plug-ins](#app-plug-ins). API 1.13 |
| `logo` | no | A small logo, shown in **Settings**, **Plug-ins** and on its dashboard cards | Read [Logo](#logo). API 1.14 |
| `update` | no | How it updates safely: a step before and after, the health wait and settings migrations | Read [Updates](#updates). API 1.14 |
| `jellyfin_libraries` | no | Jellyfin libraries for folders it fills, which Starboard adds with real-time monitoring deactivated | Read [Jellyfin libraries](#jellyfin-libraries). API 1.15 |

## What it needs (requires)

From API 1.19, a plug-in that works with one system says so in `requires`. Starboard shows it as a tag in words on the
Catalogue, on the plug-in's page (the **What it needs** line of its **State** card), in **Manage** and in **Ready to update**, and says why when that
system is not on this Starboard.

```json
"requires": ["jellyfin only"]
```

| A need | Shown as | Meaning |
|---|---|---|
| `"jellyfin"` or `"jellyfin only"` | Jellyfin only | Works with that media server, and no other |
| `"plex or emby"` | Plex or Emby | Works with either; one is enough |
| `"reelix"` | Needs Reelix | Works with an app that is not a media server |
| `["jellyfin", "reelix"]` | Jellyfin only, needs Reelix | Every need in the list must be met |
| `[]` | no tag | Needs nothing named, even if its permissions would suggest a system |

- Systems Starboard knows: `jellyfin`, `plex`, `emby`, `reelix`, `qbittorrent`, `sabnzbd`, `nzbget`, `sonarr`, `radarr`,
  `lidarr`, `readarr`, `prowlarr`, `bazarr`, `audiobookshelf`, `kavita`, `calibre-web`, `navidrome`, `gluetun`, `slskd`,
  `tdarr`, `seerr` and `dispatcharr`. Any other name is refused.
- `only` goes after one system and means the same as naming it alone; it is there so the manifest reads as the tag does.
  Alternatives are joined with `or`, up to six, and cannot end in `only`.
- **Older manifests keep working.** Without `requires`, Starboard works the tag out from the permissions: `jellyfin:key`,
  `jellyfin:metadata` and `jellyfin:libraries` mean Jellyfin, `reelix:key` means Reelix and `usenet:servers` means SABnzbd
  or NZBGet. A catalogue entry may carry `requires` too; without it, its permissions are used. Name `>=1.19` in
  `starboard_api` to use the field.
- **A plug-in is never stopped for it.** When the system is not on this Starboard, the catalogue says "Needs Jellyfin,
  which this Starboard does not use" and an installed plug-in says it is waiting, keeps its settings and carries on when
  the system is there. Installing is still possible, because a person may add the system next.
- A system is there when Starboard has an active app of that type with an address (Reelix by its icon), or, from
  the media server plug-ins of DASH-565, an active media server plug-in.

## Plug-ins that need another plug-in (needs_plugins and switch)

Some plug-ins only make sense while another is on, such as an app that signs in through a sign-in provider. From API 1.21:

- **`needs_plugins`** lists the ids of the plug-ins this one needs, up to 10. It cannot list itself.
- **`switch`** names one of the plug-in's own `switch` settings as its main switch, such as `enabled`.

Starboard checks both when someone **deactivates** a plug-in or saves its switch as off. If other plug-ins that are active list it in
`needs_plugins`, Starboard stops, names them in plain English and asks for a yes. Nothing changes until the answer is yes. On yes it
deactivates those plug-ins first, then the one asked about. Nothing is deleted, and each can be activated again. The route answers
`409` with `error` (the words to show) and `dependents` (`id` and `name` of each), and the same request with `"confirm_dependents": true`
does it. Activating the switch, saving other settings and deactivating a plug-in that nothing needs never ask. Starboard does not
activate a needed plug-in for you, and a plug-in that needs another still starts when that one is off: it should say so on its card.
A plug-in that does not use these fields works as before. Name `>=1.21` in `starboard_api` to use them.

## A first sign-in shown once (first_sign_in)

From API 1.20, an app plug-in whose app starts with a password everyone knows, such as Calibre-Web's `admin123`, can
ask Starboard for a long random one instead and show it once on the plug-in's page.

```json
"first_sign_in": {"user": "admin", "secret": "admin_password", "ready_file": "app/starboard-first-sign-in.done"}
```

| Field | What it is | Check |
|---|---|---|
| `user` | The sign-in name | Up to 40 letters, numbers and `. _ @ -` |
| `secret` | The `{secret:name}` the plug-in uses in a container's `env` or `files` | Must be one the plug-in uses. Starboard makes it once and keeps it owner-only, as every secret |
| `ready_file` | A file the app's start-up writes once the password is set | `<container>/<file name>`, inside that container's data folder |

- The app sets the password itself, before it first starts, from the environment value. It never prints it, never puts it
  on a command line and never writes it to a log.
- **Let Starboard check the file.** A container's data folder is closed (`700`, for the user the container runs as) and
  Starboard runs as another user, so it cannot tell that `ready_file` is there. When the app writes it, it also runs
  `chmod 711` on its data folder: that lets Starboard check one named file, and nothing more, as the plug-in's own folder
  that holds it is closed to everyone but Starboard. Starboard makes the folder `700` again each time it starts the plug-in,
  so the app does it at every start.
- Until `ready_file` is there, the page offers nothing, so a plug-in that was already set up is never shown a password
  that was not set.
- **Show the password** asks for the Starboard password, shows the password once and marks it shown. The listing never
  holds it, and the log says only that it was shown.
- Name `>=1.20` in `starboard_api`, so an older Starboard, which would make a password nobody is shown, is offered the
  earlier version of the plug-in instead.

## Permissions

Each permission is shown in plain words with its risk before anyone adds the plug-in. Ask only for what you use:
people read every one, and the plug-in's API key gets only the read permissions it asked for.

| Permission | What people read | Risk | Key scope |
|---|---|---|---|
| `apps:read` | Your apps and whether they answer | low | `apps` |
| `downloads:read` | What is downloading | low | `downloads` |
| `media:read` | Your films, series and books (the media folder, read only, and the library) | medium | `media` |
| `system:read` | Processor, memory and disks | low | `system` |
| `network:lan` | Reach other computers on your home network | medium | none |
| `network:vpn` | Run inside your VPN connection | medium | none |
| `jellyfin:key` | Use Jellyfin's API key, kept by Starboard | high | none |
| `reelix:key` | Use Reelix's API key, kept by Starboard (API 1.6) | high | none |
| `usenet:servers` | Use your news server's address and sign-in, from NZBGet or SABnzbd (API 1.6) | high | none |
| `network:port` | Open its own web page on your home network, at a port Starboard chooses (API 1.13) | medium | none |
| `appearance:styles` | Add styles to Display: colours, corners, a font and shadows, checked for accessibility | low | none |
| `jellyfin:metadata` | Read and change Jellyfin's metadata folder: the posters, photos and details Jellyfin saved (API 1.14) | medium | none |
| `jellyfin:libraries` | Have Starboard add its own libraries to Jellyfin, for folders it fills in your media folder (API 1.15) | medium | none |
| `library:holding` | Move films and series from your library into the holding folder in your media folder, and put them back (API 1.15) | high | none |
| `alerts:send` | Send alerts through Starboard, to where it sends its own (ntfy, Gotify, a webhook, and plug-ins that pass them on) (API 1.17). The one thing the plug-in's read-only key may change: read [Sending alerts](plugin-api-reference.md#sending-alerts-api-117) | low | none |
| `slot:media-server` | Be Starboard's media server: answer for the dashboard panel, Library, Activity and System, using the address and key kept in Settings, Apps. Reserved for plug-ins that come with Starboard (Jellyfin first); any other plug-in that asks for it is refused for now | high | none |

The plug-in's risk is its highest permission's risk. Read [What a plug-in can change](../basics/what-plugins-can-change.md)
for how this is shown to people.

## Containers

Each item in `containers` is one container. Starboard always calls the **first** one for cards, buttons, custom
settings, events and jobs.

| Field | What it is | Check |
|---|---|---|
| `name` | Its short name | Lower case letters, numbers and hyphens, up to 21 characters, different from the others |
| `image` | Its image | Pinned by digest: `registry/name@sha256:` and 64 hex characters. Read [Security rules](#security-rules) |
| `port` | The port it answers on | 1 to 65535. Starboard uses 80 when it is left out |
| `network` | Which network it joins | `default`, `lan` or `vpn`. Read [Networks](#networks) |
| `volumes` | Folders it gets | `data`, `data:<path>`, `data/<folder>:<path>`, `media:ro`, `media:holding` (API 1.15), `media/<one folder>` or `media/<one folder>:ro`. Read [Volumes](#volumes) |
| `env` | Settings passed as environment variables | Names of letters, numbers and `_` (`UPPER_CASE` before API 1.13; an app such as Tdarr reads `serverIP`); values text, numbers or `true` and `false`. From API 1.13 a value may hold `{secret:<name>}`, `{jellyfin:url}` or `{jellyfin:key}`. Read [App plug-ins](#app-plug-ins) |
| `start` | When it runs | `always` (the default) or `when_needed`, for the first container only. Read [Resting when idle](plugin-api-reference.md#resting-when-idle) |
| `idle_stop_minutes` | For `when_needed`: minutes idle before it rests | A whole number; 15 when left out |
| `publish` | Puts `port` on the home network: on Gluetun for `network: vpn` (plug-in API 1.9), or as the app's own web page for `network: lan` (API 1.13) | true or false; only with `network: vpn` or `lan` and a `port`; on `lan` it needs `network:port` |
| `host_port` | For `publish` on `lan`: the port Starboard tries first, usually the app's own, such as `3000` | 1024 to 65535. Starboard takes the next free port when it is in use. API 1.13 |
| `tmpfs` | Folders in memory the app writes to, such as `/var/run/postgresql`, owned by its user | Up to 6 paths inside the container, never `/tmp` (it always has one) or `/run/starboard`. Only `/run` may run programs, for images with s6. API 1.13 |
| `user` | The user it runs as | `uid:gid` such as `1000:1000`, never root (uid 0); `10001:10001` when left out. From API 1.12, `media`: the media folder's owner, only for a container that mounts `media/<one folder>`, from API 1.14 `jellyfin-metadata`, or from API 1.15 `media:holding`. Read [Adding files to the media folder](#adding-files-to-the-media-folder) |
| `command` | The command it runs | Only plug-ins built into Starboard may set it |
| `entrypoint` | The program it starts, in place of the image's own (API 1.13) | A list of one to 20 words, each up to 300 characters, such as `["python3", "app.py"]` |
| `files` | Small files Starboard writes once into the container's data folder, such as a settings file an app needs before it starts | An object of one to four file names (letters, numbers, `.`, `_` and `-`, up to 61 characters, starting with a letter or number) with the text of each, up to 16 KB each. The container needs a `data` or `data:<path>` volume to write them into |
| `build` | Its image is built by Starboard from the `Dockerfile` in the plug-in's zip file (API 1.15) | `true` or left out. With it, `image` must be `local/<id>:<version>`, such as `local/on-demand:0.9.2`, and the plug-in installs only from a zip file. Read [Built from a zip file](#built-from-a-zip-file) |

The container's name on the server is `plugin-<id>-<name>`, such as `plugin-hello-card-main`.

### Networks

| Value | What it reaches | Permission needed |
|---|---|---|
| `default` | Only Starboard, on the plug-in's own network, which has no way out | none |
| `lan` | Also your home network and the internet, and the server itself as `host.docker.internal` | `network:lan` |
| `vpn` | The internet through your VPN: it runs inside Gluetun's network | `network:vpn` |

### Volumes

| Value | Path inside the plug-in | Permission needed |
|---|---|---|
| `data` | `/data`, read and write: its own folder, `data/plugins/<id>/data/<container name>` | none |
| `media:ro` | `/media`, read only: the whole media folder | `media:read` |
| `media/<one folder>` | `/media/<one folder>`, read and write: one folder in the media folder, such as `media/music` | none, but it is listed as something it can change |
| `media/<one folder>:ro` | `/media/<one folder>`, read only (API 1.13) | none; it is listed as something it can read |
| `data:<path>` | Its own folder, at the path the app expects, such as `data:/config` (API 1.13) | none |
| `data/<folder>:<path>` | A folder inside its own folder, at a path, for an app with several, such as `data/server:/app/server` (API 1.13) | none |
| `jellyfin-metadata` | `/metadata`, read and write: Jellyfin's metadata folder, its posters, photos and details (API 1.14). Read [Jellyfin's metadata folder](#jellyfins-metadata-folder) | `jellyfin:metadata` |
| `jellyfin-metadata:ro` | `/metadata`, read only (API 1.14) | `jellyfin:metadata` |
| `media:holding` | `/media`, read and write: the whole media folder, to move items into its holding folder, `/media/.holding/<id>`, and back (API 1.15). Read [The holding folder in the media folder](#the-holding-folder-in-the-media-folder) | `library:holding` |

Nothing else can be mounted. The folder name after `media/` is 1 to 60 letters, numbers, dots, underscores and
hyphens, so it cannot climb out with `..`.

### Jellyfin's metadata folder

From API 1.14, a plug-in that works on the pictures and details Jellyfin keeps, such as one that shrinks posters,
mounts Jellyfin's metadata folder with `jellyfin-metadata` (read and write) or `jellyfin-metadata:ro` (read only),
and asks for the permission `jellyfin:metadata`. Nothing else gets the folder: without the permission the manifest is
refused, and the folder is mounted only for a plug-in that was granted it.

- In the container it is always `/metadata`. On the server, Starboard finds it where Jellyfin mounts it: `/metadata`
  on new installs (`${CONFIG_DIR}/jellyfin-metadata`), or Jellyfin's own `config/data/metadata` on an install that
  has not been moved yet. When Jellyfin is not installed, the plug-in cannot be added, and Starboard says so.
- To change files there, run the container as `"user": "media"`, the apps' own user, which owns Jellyfin's files.
- People read before they add it: "Jellyfin's metadata folder: the posters, photos and details Jellyfin saved. It can
  change, replace and remove them, and Jellyfin shows what it leaves there". Its risk is medium.
- Check each file before it replaces the one Jellyfin saved, and keep the work slow and quiet: Jellyfin reads these
  files while people watch.

```json
"permissions": ["jellyfin:metadata"],
"containers": [{"name": "main", "image": "ghcr.io/you/picture-shrinker@sha256:...", "port": 8080,
                "volumes": ["data", "jellyfin-metadata"], "user": "media"}]
```

### Built from a zip file

From API 1.15, a private plug-in with no registry, such as On demand, can ship its own image as a `Dockerfile` in a
zip file. People add it in **Settings**, **Plug-ins**, **Add a plug-in**, **Upload a zip file**; a newer zip updates
it from its page, with **Update from a zip file**. A plug-in with `build` cannot be added from an address or a
catalogue, because there is nothing to build from.

```json
"containers": [{"name": "on-demand", "image": "local/on-demand:0.9.2", "build": true, "port": 7790,
                "volumes": ["data", "media/on-demand"], "user": "1000:1000"}]
```

**The zip.** `starboard-plugin.json` and `Dockerfile` at the top of the zip, not in a folder inside it. Up to 50 MB,
unpacking to at most 200 MB in at most 2,000 files. Only files and folders: no links, devices or pipes, no names that
climb out with `..` or start with `/`, no backslashes, no two files with the same name, and nothing encrypted.

**The Dockerfile.** It may build from public images and the zip's own files, and nothing more:

- no parser directives such as `# syntax=` (they would run someone else's builder);
- no `RUN --mount`, `--network` or `--security`;
- no `ADD` from the internet or git, and `COPY --from` only from an earlier stage of the same Dockerfile;
- no `VOLUME` or `ONBUILD`;
- `FROM` names its image in full (no variables), never an image built on the computer (`local/...`), at most 6 times.

**The build.** Docker's own builder, with up to 2 GB of memory (and no swap beyond it), 2 processor cores and 20
minutes. The build can reach the internet to fetch what the Dockerfile names, never the server's own network, folders,
Docker or other apps. No build arguments or secrets are passed. An image over 3 GB is refused. The image is tagged
`local/<id>:<version>`, so **Roll back** finds the version before without a download, and Starboard keeps the zips of
the current and the previous version beside the plug-in, so an image that has gone is built again on **Activate**.

People read before they add it: "Starboard builds its image, local/on-demand:0.9.2, from the Dockerfile in the zip",
with the limits and the image it starts from. Make the zip from your committed files, as On demand's
`tools/make-zip.sh` does with `git archive`.

### The holding folder in the media folder

From API 1.15, a plug-in that tidies the library, such as Library clean-up, can move films and series out of it and
put them back. It asks for the permission `library:holding` and mounts `media:holding`: the whole media folder, read
and write, at `/media`. Without the permission the manifest is refused.

- What it moves goes in `/media/.holding/<plug-in id>/`, keeping the folders it was in, so
  `/media/movies/A Film (2001)` becomes `/media/.holding/library-cleanup/movies/A Film (2001)` and can go back to the
  same place. The holding folder is inside the media folder because a move between two folders Docker mounts
  separately is a copy and then a delete, even on one disk; inside one mount it is a rename, which is instant and
  needs no free space. Its name starts with a dot and it is outside every library folder, so Jellyfin and Reelix do
  not list what is in it.
- Never delete. The folder is mounted read and write, so Starboard cannot stop a plug-in that deletes; people read
  that before they add it, and the collection's tests check that its code has no way to delete a media file.
- Offer **Put back** for each item: a row with the `restore` action on a custom setting's list (API 1.15), and say
  first, with a preview, what would move and how much space it frees.
- Tell Reelix (with `reelix:key`) to stop following what moves, so it is not downloaded again, and to follow it again
  when it is put back; tell Jellyfin (with `jellyfin:key`) the folder has gone, and that it is back.
- Run the container as `"user": "media"`, the owner of the media folder, so moved folders keep their owner.
- People read before they add it: "Your media folder: it can move films and series into the holding folder there
  (media/.holding) and put them back. It is given the whole folder to read and change, so add only a plug-in you
  trust; what it moves leaves Jellyfin until it is put back". Its risk is high.

```json
"permissions": ["jellyfin:key", "reelix:key", "library:holding", "network:lan"],
"containers": [{"name": "main", "image": "ghcr.io/you/library-cleanup@sha256:...", "port": 8080, "network": "lan",
                "volumes": ["data", "media:holding"], "user": "media"}]
```

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
- **Only these volumes.** A plug-in reaches its own folder and, if allowed, the media folder. It never reaches other
  apps' settings or Starboard's own data.
- **Never root.** `user` must not be uid 0. A program running as root inside a container is one mistake away from
  root on the server.
- **Read only, with no extra rights.** Every container runs with a read-only file system and a 64 MB `/tmp`, every
  Linux capability dropped, no new privileges, and at most 64 processes (an app plug-in may ask for up to 1024 with
  `pids`, API 1.13).
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
| `pids` | Processes and threads, for an app such as Kavita or Tdarr (API 1.13) | 64 | 1024 |

The ceilings keep Starboard light on small servers, such as a Raspberry Pi. Each container's limits are shown to people
before they add the plug-in.

## App plug-ins

From API 1.13 (DASH-411) a plug-in can be a whole app that is kept out of the main install, such as Jellystat with
its PostgreSQL database, or Navidrome. Starboard still writes its Compose file and every security rule on this page still
applies: the app runs read only, as a user that is not root, with no capabilities.

- **An app and its database.** Up to four containers share the plug-in's own network, which reaches nothing else.
  Each reaches the others by its container name, `plugin-<id>-<name>`, such as `plugin-jellystat-db`.
- **Its web page.** A container on `lan` with `publish: true` and a `port` is opened on the home network. It needs
  `network:port`, which is shown to people before they add it. Starboard chooses the port on this computer: `host_port` if it
  is free, otherwise the next free one, avoiding ports other containers, other plug-ins and Starboard's own apps use.
  If something outside Docker holds it, the start fails and Starboard takes the next port and tries again. The port is
  kept, so it stays the same after an update or a Roll back. Starboard shows the address on the plug-in's page,
  with **Open**, and on **Your plug-ins**.
- **Passwords made for the install.** `{secret:db_password}` in `env` is a random value Starboard makes once for this
  install and keeps owner-only in `data/plugins/<id>/secrets.json`. Use the same name in the app and its database.
- **Jellyfin's address and key.** With `jellyfin:key`, `{jellyfin:url}` and `{jellyfin:key}` in `env` are filled in
  from Starboard's Jellyfin each time the plug-in starts, as `run/jellyfin.json` is.
- **Data where the app wants it.** `data:/config` mounts the container's own folder at `/config`;
  `data/server:/app/server` mounts a folder inside it. `tmpfs` gives folders in memory, such as
  `/var/run/postgresql`.
- **Removing it.** Removing any plug-in keeps its folder. People choose where it goes: kept in `data/plugins/.removed`,
  or moved to the holding folder in **System**, **Clean up**, from where they can put it back or delete it for good.
- **Taking over an app.** `adopt` names an app the main install may run, so Starboard can copy its settings into the
  plug-in:

```json
"adopt": {"app": "tdarr", "name": "Tdarr", "into": "server", "stop": true,
          "copy": {"/app/server": "server", "/app/configs": "configs", "/app/logs": "logs"}}
```

| Field | What it is |
|---|---|
| `app` | The app's container name in the main install |
| `name` | What people read, up to 40 characters |
| `into` | The plug-in's container whose data folder gets the copies |
| `copy` | One to eight folders: the folder inside the app, and the folder inside `data/plugins/<id>/data/<into>` it is copied to |
| `stop` | `true` to stop the app first, so its files are copied whole and its port is free. It is stopped, never removed |

Starboard copies with the app's folders mounted read only, so they are never moved, changed or deleted. Anything the
plug-in already wrote there is put beside, as `<folder>.before-copy-<date>`. The plug-in must be inactive. Only folders
the app keeps on the computer (bind mounts) can be copied; a Docker volume is said plainly. Afterwards the person
removes the app from the main install themselves, in **Settings**, **Install apps**.

In a catalogue entry, `rest` says what the app uses at rest, measured: `{"memory_mb": 117, "cpu_percent": 0.22}`.
Starboard shows it under the plug-in in the catalogue, so people with a small server can choose.

## Jellyfin libraries

From API 1.15, a plug-in that fills folders for Jellyfin, such as On demand's films and series, names its libraries
in `jellyfin_libraries` and asks for `jellyfin:libraries`. Starboard adds each one Jellyfin does not have when the
plug-in is activated, and checks them again on every activation, so after each install, update and **Roll back**.

```json
"permissions": ["jellyfin:libraries"],
"jellyfin_libraries": [
  {"name": "On demand Films", "type": "movies", "folder": "media/on-demand/films"},
  {"name": "On demand TV", "type": "tvshows", "folder": "media/on-demand/tv"}
]
```

| Field | Required | What it is | Check |
|---|---|---|---|
| `name` | yes | The library's name in Jellyfin | Text, up to 40 characters, different from its other libraries |
| `type` | yes | What it holds | `movies`, `tvshows`, `music`, `books`, `homevideos`, `musicvideos` or `mixed` |
| `folder` | yes | Its folder | Inside a media folder one of its containers mounts, such as `media/on-demand/films`, up to 3 folders deep |
| `realtime_monitor` | no | Whether Jellyfin watches the folder for new files | `true` or `false`; `false` when left out |

- **Real-time monitoring is deactivated unless you set it.** Jellyfin watching a folder costs one of the computer's
  folder watches for every folder in it, and a large library can use them all up before the person's own Films and
  TV. A plug-in that adds files itself tells Jellyfin to check (a library refresh) instead.
- **Starboard keeps it as you set it.** Someone who activates monitoring in Jellyfin finds it deactivated again on the
  next activation of the plug-in. Nothing else about the library is changed.
- **Found by its folder, then by its name.** A library Jellyfin already has, from an older version or made by hand,
  is used, not added twice.
- **The folders are made first,** owned by the container's user, because Jellyfin will not add a folder that is not
  there.
- **They stay when the plug-in is removed.** They are the person's to keep or remove in Jellyfin.
- **Never a stop.** When Jellyfin is not connected or does not answer, the plug-in still starts, and its state says
  what went wrong.

People read before they add it: "Jellyfin: Starboard adds 2 libraries On demand Films and On demand TV, for folders it
fills in your media folder. Real-time monitoring is deactivated for On demand Films and On demand TV, as the plug-in
refreshes them itself."

## Settings

Starboard draws a plug-in's settings in its section of **Settings**, then **Plug-ins**, checks each value, and saves
them in the plug-in's `settings.json`. Read [Settings and key files](plugin-api-reference.md#settings-and-key-files).

| Field | What it is |
|---|---|
| `key` | Its name in `settings.json`: lower case letters, numbers and underscores, starting with a letter, up to 41 characters. Required |
| `label` | What people read. Required. Keep it under 60 characters, in sentence case, with no colon |
| `type` | One of the types listed in this section. Required |
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
| `list` | A box with one value a line | Saved as a list of strings, blank lines left out. Up to 200, each up to 500 characters |
| `custom` | A list the plug-in describes, drawn by Starboard | `choices` is a path on the plug-in. Read [Custom pages](plugin-api-reference.md#custom-pages) |
| `schedule` | How often (every day, every week or every month), the day or the date, and a time, side by side | Every day, week or month; a day of the week for a week; a date from 1 to 31 for a month; a time such as `03:30`. A month without the date runs on its last day. API 1.14. Read [A job on a schedule from its settings](#a-job-on-a-schedule-from-its-settings) |

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
- The plug-in's `actions` are buttons in an **Actions** section, after its settings and pages.

## Cards

Each item in `cards` is a card people can add with **Edit dashboard**. Read
[Card answers](plugin-api-reference.md#card-answers) for what the path answers.

| Field | What it is | Check |
|---|---|---|
| `id` | Its id, in the card's address | Letters, numbers, hyphens and underscores, up to 40. Give every card one |
| `title` | Its name on the dashboard | A card needs a `title` (or a `label`), so a screen reader can name it |
| `titles` | Its title for each card size, so it fits on one line in that size: any of `small`, `medium`, `half`, `wide` and `full` | Each one line of words, up to the size's limit: small 17, medium 28, half 22, wide 43 and full 45 characters. A size left out shows the plug-in's name with the card's `title` under it. Read [A title for each size](#a-title-for-each-size-api-115). API 1.15 |
| `type` | `stat`, `list`, `status`, from API 1.8 `guide`, or from API 1.17 `sparkline` | Required |
| `path` | The path on the first container that answers | Required: starts with `/`, up to 80 letters, numbers, `/`, `_`, `.` and `-` |
| `format` | For `stat`: `number`, `bytes`, `percent`, `duration` (seconds) or `date` (seconds since 1970) | `number` when left out |
| `label` | Another name for the card | Optional |
| `example` | What the path answers | The tester checks its shape, and warns when it is missing |
| `refresh_minutes` | How often Starboard asks | Minutes between asks, 1 to 1440; 1 when left out. Starboard never asks more often than once a minute, unless the card has `refresh_seconds`. API 1.4 |
| `refresh_seconds` | How often the dashboard asks, in seconds, such as `30` for a card that shows progress | A whole number from 10 to 3600. 10 seconds is the quickest any card is asked. The card's answer may give its own `refresh_seconds`, which wins, so a setting can change it. Left out, the card is asked as before, once a minute or every `refresh_minutes`. API 1.14 |

```json
"cards": [
  {"id": "now", "title": "Direct play", "type": "list", "path": "/card", "refresh_seconds": 30}
]
```

A card with `refresh_seconds` is asked again at that time while its dashboard is open and in view, never while the
browser tab is hidden. Cards due at the same time are asked in one request. Read
[How often a card is asked](plugin-api-reference.md#how-often-a-card-is-asked-api-114).

From API 1.14 Starboard draws every plug-in card with a grey band across the top: the plug-in's [logo](#logo) (or
its initials), the plug-in's name as the card's heading, the card's `title` under it when it differs, and at the
right a status chip and when it last updated, from the card's answer. You do not lay any of it out. Read
[The card band](plugin-api-reference.md#the-card-band-api-114).

### A title for each size (API 1.15)

People choose each card's size in **Edit dashboard**: small (a quarter of the width), medium (a third), half, wide
(two thirds) or full width. From API 1.15 a card can have its own title for each size in `titles`, so a small card
has a short title and a wide one can say more. The title for the card's size is then the card's heading on its own,
on one line beside the logo, and screen readers hear the plug-in's name after it when the title does not say it. A
size you leave out shows the plug-in's name with the card's `title` under it, as before.

| Size | Up to | Measured at its narrowest |
|---|---|---|
| `small` | 17 characters | A quarter of the width, in a window 1101 pixels wide. The chip (its icon only) and the time sit under the title |
| `medium` | 28 characters | A third of the width, 1101 pixels. The chip and the time sit under the title, as they do not fit beside it |
| `half` | 22 characters | Half the width, 1101 pixels, with the chip and the time beside it |
| `wide` | 43 characters | Two thirds of the width, 1101 pixels, with the chip and the time beside it |
| `full` | 45 characters | The whole width, in a window 768 pixels wide, with the chip and the time beside it |

```json
"cards": [
  {"id": "saved", "title": "Space saved", "type": "stat", "path": "/card", "format": "bytes",
   "titles": {"small": "Space saved", "medium": "Picture space saved", "half": "Pictures: space saved",
              "wide": "Space saved by shrinking pictures", "full": "Space saved by shrinking posters and photos"}}
]
```

Each limit is what fits on one line in the card's band, beside the logo, the status chip and the time, at the
standard text size in the narrowest window that size is shown at, measured with wide words. On a small card the chip shows only its icon (screen readers still hear its words), and the chip and the time sit under the title; on a medium card they sit under it in windows 1101 pixels wide and wider, where they do not fit beside it. When
someone makes the text larger in **Display**, a title may take two lines; Starboard never cuts a title short. The
manifest check refuses a title longer than its size's limit, and the plug-in tester names it with its limit. Keep the
words that matter first, and write each title in sentence case.

## Actions

Each item in `actions` is a button in the plug-in's section of **Settings**, then **Plug-ins**. Read
[Actions](plugin-api-reference.md#actions) for what Starboard sends.

| Field | What it is |
|---|---|
| `id` | Its id: letters, numbers, hyphens and underscores, up to 40. Give every button one. A button without one is known by its place in the list, counting from 0, which changes when you move it |
| `label` | The words on the button, saying what it does, such as `Run Live TV now`. Required |
| `path` | The path on the first container that Starboard sends a POST to. Required |
| `confirm` | A question Starboard asks before the button runs, such as `Downloads a test file now. Continue?`, in its standard confirm box. The box starts on **Cancel**, and Escape cancels. Up to 300 characters |

## Health

`health` is a path, such as `/health`, that answers 200 while the plug-in works. Keep it cheap: no calls to other
apps. The tester warns when a plug-in with containers has none. Starboard asks it when **Settings**, then
**Plug-ins**, is opened, and shows **Not answering** when it does not answer 200. For plug-ins built into
Starboard, it is also the container's health check. After an update, Starboard waits for it to answer before it
keeps the new version (API 1.14): read [Updates](#updates).

## Styles

`styles` lists 1 to 32 styles for **Display** (16 before API 1.2), and needs the permission `appearance:styles`.
Each style has an `id`, a `name`, and a `light` and a `dark` set of colours. Starboard checks every style for
contrast in light and dark before it can be added. A plug-in with only styles runs no container. Read
[Styles in Write a plug-in](../basics/write-a-plugin.md#styles).

These are the other fields of a style, all optional. They come from the JSON Schema, so the table and the check
cannot differ.

| Field | Its values |
|---|---|
| `description` | Text, up to 120 characters |
| `radius` | A whole number from 0 to 24 (pixels) |
| `font` and `heading_font` | `hyperlegible`, `system`, `rounded`, `serif` or `mono` |
| `heading_weight` | `600`, `700` or `800` |
| `heading_case` | `none` or `labels` |
| `heading_tracking` | `tight`, `normal` or `wide` |
| `shadow` | `none`, `soft`, `strong`, `layered`, `glow`, `clay` or `hairline` |
| `card_style` | `flat`, `outlined`, `elevated` or `tonal` |
| `button_fill` | `solid`, `outline`, `soft` or `ghost` |
| `border_width` | `1`, `2` or `3` (pixels) |
| `focus_width` | A whole number from 3 to 5 (pixels). Never less than 3, so the focus outline stays clear |
| `tab_style` | `underline`, `pill` or `boxed` |
| `header_style` | `solid`, `blurred`, `accent_bar` or `rule` |
| `rail_style` | `solid`, `floating` or `tinted` |
| `chip_style` | `soft` or `outline` |
| `gradient` | `none`, `linear`, `radial` or `mesh` |
| `gradient_angle` | A whole number from 0 to 360 (degrees) |
| `texture` | `none`, `dots`, `grid`, `lines` or `grain` |
| `primary_gradient`, `glass` and `rounded_controls` | `true` or `false` |

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
| `disk.changed` | When a disk is erased, added to the pool or taken out of it. API 1.16 | `system:read` |

## Jobs

`jobs` lists up to eight jobs that Starboard runs for the plug-in on its own clock. They need a container to run
in. API 1.4. Read [Jobs](plugin-api-reference.md#jobs) for what Starboard sends.

| Field | What it is | Check |
|---|---|---|
| `id` | Its id | Lower case letters, numbers and hyphens, starting with a letter, up to 31; different from the others |
| `label` | What people read in **System**, then **Jobs** | Required, up to 60 characters |
| `path` | The path on the first container | Required |
| `daily` | A time each day, such as `03:30` | Give exactly one of `daily`, `every_hours`, `at_start` and `schedule` |
| `every_hours` | Every so many hours | A whole number from 1 to 168 |
| `at_start` | Once each time Starboard starts | Must be `true` |
| `schedule` | When the person chooses, in one of its settings | The `key` of one of its settings of type `schedule`. API 1.14 |
| `time_limit_minutes` | How long it may take | 1 to 120; 10 when left out |
| `quiet_hours` | Run only in quiet hours | `true` or `false` |

```json
"jobs": [
  {"id": "tidy", "label": "Tidy old files", "path": "/jobs/tidy", "daily": "03:30", "time_limit_minutes": 20, "quiet_hours": true}
]
```

### A job on a schedule from its settings

From API 1.14 a job can run when the person chooses rather than at a time you fixed: every day, every week on a
chosen day, or every month on a chosen date, at a chosen time. Add a setting of type `schedule`, with a `default`, and
name its `key` in the job's `schedule`:

```json
"settings": [
  {"key": "when", "label": "When to shrink", "type": "schedule", "hint": "It runs at this time.",
   "default": {"every": "week", "day": "sunday", "time": "03:30"}}
],
"jobs": [
  {"id": "shrink", "label": "Shrink pictures", "path": "/jobs/shrink", "schedule": "when", "time_limit_minutes": 120}
]
```

| Value | What it is |
|---|---|
| `every` | `day`, `week` or `month`. Required |
| `time` | The time, such as `03:30`, in the server's own time zone. Required |
| `day` | For `week`: `monday`, `tuesday`, `wednesday`, `thursday`, `friday`, `saturday` or `sunday` |
| `date` | For `month`: 1 to 31. In a month without that date, such as the 31st in April, it runs on the month's last day |

- Starboard draws the setting as **How often**, then **Day** or **Date**, then **Time**, and saves each change at
  once. It checks the value, says what is wrong in plain words ("When to shrink: needs a day of the week"), and keeps
  only the parts the schedule uses.
- The job runs within 5 minutes after its time. If the server was off then, it still runs up to 6 hours late, and
  otherwise waits for the next time, so it never starts in the middle of the day by surprise.
- **System**, then **Jobs**, says the schedule in words and when it runs next, such as "Every week on Sunday at 03:30,
  next Sunday 16 November at 03:30", with **Run now** as for any job.
- The install warning says the job runs on the schedule people choose, and what it starts with.
- Without a usable value or default, the job does not run by itself; **Run now** still works.
- With `quiet_hours`, it runs only when its time falls in quiet hours.

## Logo

From API 1.14 a plug-in may have a small logo: an SVG or PNG file next to `starboard-plugin.json`. Starboard shows it
in **Settings**, **Plug-ins** (**Manage** and the **Catalogue**), on the plug-in's own page, and in the grey band of
each of its dashboard cards. A plug-in without one gets its initials on a plain tile, so every card has the same layout.

```json
"logo": {"file": "logo.svg", "alt": "A play symbol on a screen"}
```

| Field | What it is | Check |
|---|---|---|
| `file` | The file's name, next to the manifest or in one folder under it, such as `logo.svg` or `images/logo.png` | Ends in `.svg` or `.png`; no `..` |
| `alt` | What the logo shows, in words, for people who cannot view it | 3 to 80 characters, such as "A play symbol on a screen". Not the plug-in's name: that is always beside it |

How Starboard reads it:

- When the plug-in is added or updated from an address (or the catalogue), Starboard fetches the file from beside the
  manifest, checks it, and keeps a cleaned copy in the plug-in's folder. It serves that copy itself; the browser never
  loads anything from your site. A manifest pasted into **Test a plug-in** has no address, so its logo cannot be read.
- **SVG**: up to 16 KB, with a `viewBox`; only shapes, paths, groups, gradients, `use` of its own parts, `title` and
  text. No scripts, `foreignObject`, pictures, `style` elements or attributes, animation, event handlers (`on...`),
  links outside the file or `url()` other than `url(#id)`, and no DOCTYPE or entities. Starboard draws the SVG again
  from what it allows.
- **PNG**: up to 32 KB, square, from 32 to 256 pixels a side.
- It is shown at 32 and 40 pixels: use one solid shape that reads at that size in light and dark.
- A logo that fails a check is not used: the plug-in is still added, with its initials, and the plug-in tester
  reports it as a warning with what to change.
- Roll back brings back the logo of the version before.

A catalogue entry can carry the same logo for the Catalogue, before anything is added. Read
[Catalogues](plugin-api-reference.md#catalogues).

## Updates

`update` tells Starboard how to update the plug-in safely. Every part is optional. API 1.14. Read
[Write a plug-in that updates safely](update-a-plugin-safely.md) for a walk through.

| Field | What it is | Check |
|---|---|---|
| `before` | A step Starboard calls on the version that is installed, before anything changes: finish or pause work | `{"path": "/update/before", "time_limit_seconds": 60}`. The path starts with `/`; the time limit is 5 to 300 seconds, 60 when left out. Needs a container |
| `after` | A step Starboard calls on the version running at the end: tidy up or start work again | The same as `before` |
| `health_wait_seconds` | How long Starboard waits for the new version's `health` path to answer 200 | 10 to 600, 60 when left out. Needs `health` |
| `migrations` | How saved settings move from older versions | 1 to 20 steps, each in this section |

Each step of `migrations`:

| Field | What it is | Check |
|---|---|---|
| `version` | The version that made the change | Required. A version such as `2.0.0`, different from the others, no newer than the manifest's `version` |
| `rename` | Old setting keys and their new keys | Up to 20. The new key must be one of this version's `settings` |
| `remove` | Setting keys this version no longer has | Up to 20. A key still in `settings` is refused, unless a later step renames something to it |
| `defaults` | New default values | Up to 20. The key must be one of this version's `settings` |

Give at least one of `rename`, `remove` or `defaults` in each step.

What Starboard does, in order:

1. **Before.** If the plug-in is active and the installed version has `before`, Starboard sends it `POST` with
   `{"from": "1.0.0", "to": "2.0.0"}`. An answer other than 2xx, `{"ok": false, "said": "..."}`, or no answer within
   the time limit stops the update, and nothing is changed. The words in `said` are shown.
2. **Settings.** Each migration step whose `version` is later than the installed version and no later than the new one is
   applied, oldest first. `rename` moves a value to its new key (a value already under the new key wins). `remove`
   drops a key. `defaults` sets a new value only where the saved value is still the installed version's default, or
   there is none, so a value someone chose is kept. A new setting then gets its `default`.
3. **Install.** The new manifest, settings and Compose file are written, the version before is kept in
   `previous/` with its settings as they were, and an active plug-in starts on the new version.
4. **Health.** Starboard asks `health` every 3 seconds, for up to `health_wait_seconds`. If the new version does not
   start or does not answer 200 in time, Starboard rolls back by itself: the version before, with its settings as they
   were, and its `after` step hears `{"outcome": "rolled_back"}`.
5. **After.** The new version's `after` step hears `{"from": "1.0.0", "to": "2.0.0", "outcome": "updated"}`. A failing
   `after` does not undo the update; it is said in the result and the log.

A plug-in that is not active is updated without its steps or the health wait. **Roll back** calls `before` on the
version running and `after` on the one brought back, with `{"outcome": "rolled_back"}`, and puts back the settings
kept from before the update. Settings changed since the update are not kept by a Roll back.

```json
"update": {
  "before": {"path": "/update/before", "time_limit_seconds": 60},
  "after": {"path": "/update/after"},
  "health_wait_seconds": 90,
  "migrations": [
    {"version": "1.5.0", "rename": {"minutes": "every_minutes"}},
    {"version": "2.0.0", "remove": ["old_mode"], "defaults": {"every_minutes": 30}}
  ]
}
```

A plug-in made for an earlier API has no `update`: it is updated as before, and Starboard still waits up to 60 seconds
for its `health` path when it has one, and goes back by itself if it does not answer.

## Changes

`changes` lists what changed in each version, newest first, in the types of
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Copy the lines from your `CHANGELOG.md`. Before an update,
the warning shows **What is new since** the installed version, from the new version's `changes` (API 1.14). After an
update, a Roll back or an update from an address, the plug-in's **State** shows **What is new** with the versions between the
one people had and the one they have now: each type's first line, and **All changes** for the rest. It stays until
someone chooses **Got it**, which Starboard keeps, so it is not shown again on any device. API 1.10.

| Field | What it is | Check |
|---|---|---|
| `version` | The version these changes are in | Required. A version such as `1.2.0`, different from the others |
| `date` | When it was released | A date such as `2026-11-13` |
| `added`, `changed`, `deprecated`, `removed`, `fixed`, `security` | The changes of that type | Give at least one. Each lists 1 to 20 lines of up to 300 characters |

Up to 20 versions. A line may use `**bold**` and `` `code` ``; Starboard shows them as text, never as HTML.
Start each line with what people notice, in a few words. Include the manifest's own `version`: the tester warns when
it is missing, because What is new then cannot say what changed. Say when settings move.

```json
"changes": [
  {"version": "1.1.0", "date": "2026-11-12", "added": ["**Three new styles:** Sunset, Graphite and Editorial"],
   "fixed": ["A style chosen on a phone is kept after Starboard restarts"]},
  {"version": "1.0.0", "date": "2026-11-10", "added": ["The first ten styles"]}
]
```

## Capabilities (API 1.22)

A version number says this Starboard has the whole API up to there. An optional part is better asked for by name.
Name what your plug-in **needs** (it cannot work without it) and what it **uses** if it is there:

```json
"capabilities": {"needs": ["first-sign-in"], "uses": ["sparkline-card"]}
```

`GET /api/v1/` answers `capabilities`, the names this Starboard has. A plug-in that needs a name that is not there is not
added, and the catalogue offers the newest version that fits. For a name you only use, read `GET /api/v1/` when your
plug-in starts and work without it. Names are never reused or renamed.

| Name | What it is |
|---|---|
| `media-server-slot` | Be Starboard's media server (API 1.17) |
| `first-sign-in` | A first password Starboard makes and shows once (API 1.20) |
| `sparkline-card` | The sparkline card (API 1.17) |
| `guide-card` | The guide card, what is on now (API 1.8) |
| `alerts-send` | Raise and clear alerts through Starboard (API 1.17) |
| `partial-pages` | Custom pages that save in place, choose several and come in cards (API 1.16) |
| `api-socket` | Starboard's API on a Unix socket in the run folder (API 1.16) |
| `update-steps` | Steps before and after an update, a health wait and settings that move with a version (API 1.14) |
| `app-plugins` | A whole app as a plug-in, with its own port, secrets and data (API 1.13) |
| `schedule-setting` | A setting that is a time of day, week or month, and a job that uses it (API 1.14) |

A catalogue version may carry `capabilities_needed`, a list of the same names, next to its `starboard_api`.

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
| 1.11 | 13 November 2026 | Four more events (`request.available`, `download.failed`, `disk.nearly_full`, `update.available`), and `readonly` on a custom setting's list with folds |
| 1.12 | 13 November 2026 | `"user": "media"` on a container that mounts `media/<one folder>`; `link` and `state_label` on a custom setting's item; `file_only` on its add box |
| 1.13 | 13 November 2026 | App plug-ins: `network:port` and `publish` on `lan` with `host_port`, `{secret:...}` and `{jellyfin:...}` in `env`, `tmpfs`, `data:<path>` and `media/<one folder>:ro`, `pids`, and `adopt` |
| 1.14 | 14 November 2026 | A card's own refresh time, `refresh_seconds`, in the manifest and in its answer, 10 seconds at the quickest; `recommended` on a catalogue entry; `logo` (and `logo`, `logo_alt` on a catalogue entry); every card drawn with a grey band holding the logo, the name, a status chip and when it last updated (`status`, `status_label` and `updated` in its answer); a `schedule` setting and a job's `schedule`; the `jellyfin:metadata` permission with the `jellyfin-metadata` volume; `update` (a `before` and an `after` step, `health_wait_seconds` and settings `migrations`), with the health wait and an automatic Roll back after every update, and **What is new** shown before an update too |
| 1.20 | 26 November 2026 | `first_sign_in`: a password Starboard makes for an app plug-in, set by the app before it first starts and shown once on the plug-in's page |
| 1.22 | 27 November 2026 | `starboard_tested` and `capabilities`: named optional parts a plug-in needs or uses, listed by `GET /api/v1/`; the plug-in tester checks the range a plug-in names |
| 1.21 | 27 November 2026 | `needs_plugins` and `switch`: a plug-in may list the plug-ins it needs and name its own main switch; deactivating a plug-in or saving its switch as inactive a plug-in that others need asks first and deactivates them too |
| 1.19 | 25 November 2026 | `requires`: the system a plug-in needs, shown as a tag (Jellyfin only, Plex or Emby, Needs Reelix), worked out from the permissions of older manifests; 1.18 is DASH-572's |
| 1.17 | 20 November 2026 | The `sparkline` card: a small line for each series, with the latest, lowest and highest value in words; the `alerts:send` permission, with `POST /api/v1/plugin/alerts` to raise and clear alerts through Starboard's own |
| 1.16 | 19 November 2026 | The `disk.changed` event; a plug-in is activated when installed; a custom setting's `add` box and an item's `attach` form take plain text; `STARBOARD_HOME_ADDRESS` for a container with `publish` on the `lan` network |
| 1.15 | 15 November 2026 | `build` on a container, for an image Starboard builds from the `Dockerfile` in the plug-in's zip file, installed with **Upload a zip file** and updated with **Update from a zip file**; `jellyfin_libraries` with the `jellyfin:libraries` permission; the `library:holding` permission with the `media:holding` volume (the media folder, read and write, for its holding folder `media/.holding/<id>`), and `restore` on a custom setting's item, drawn as **Put back**; `titles` on a card, a title for each card size that fits on one line in that size |

Use the lowest version that has what you use in `starboard_api`, such as `">=1.4 <2.0"` for a plug-in with jobs.
Read [API changelog](api-changelog.md).

## Find out more

- [Make your first plug-in](make-a-plugin.md)
- [Plug-in API reference](plugin-api-reference.md)
- [Test and publish a plug-in](test-and-publish-a-plugin.md)
- [Write a plug-in that updates safely](update-a-plugin-safely.md)
- [Write a plug-in](../basics/write-a-plugin.md)
- [What a plug-in can change](../basics/what-plugins-can-change.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
