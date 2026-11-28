[Help centre](../README.md) · Developers
<!-- help: dev / plugins -->
<!-- plugin-api: 1.25 -->

# AI prompts for developers

An AI assistant, such as Claude, can write a Starboard plug-in or a script that reads Starboard's API, if you give
it the rules. Copy one of the prompts on this page, fill in the parts in square brackets, and paste in the pages it
names. The prompts are written for plug-in API 1.25, in the Starboard release after 0.24.0 and later.

## Before you begin

- An AI assistant you already use.
- The pages each prompt names, open in your browser, so you can copy them in. An assistant that can open web
  addresses can read them itself: give it the addresses in the prompt instead.
- Starboard's help centre is the final word. If the assistant says something different, follow the help centre.

## Steps

1. Choose the prompt that fits what you want to make: [a card plug-in](#a-card-plug-in),
   [an app plug-in](#an-app-plug-in) or [a plug-in that converts files](#a-plug-in-that-converts-files).
2. Copy the whole prompt, and fill in the parts in square brackets.
3. Under the prompt, paste the full text of each page it names, each with its title.
4. Send it. Check what comes back with the plug-in tester before you use it. Read
   [Test and publish a plug-in](test-and-publish-a-plugin.md#test-it).
5. Paste the tester's issues back into the assistant and ask it to fix them.

## The checklist in every plug-in prompt

The three plug-in prompts end with the same checklist. The assistant must follow it, and say how it did:

- **Permissions:** the fewest that work, each explained in one sentence.
- **Memory limits:** the smallest that work, within 512 MB and 1.0 processor core (an app plug-in with `network:port`
  up to 2048 MB and 4 cores); `"start": "when_needed"` when Starboard is the only way it is reached.
- **Accessibility:** labels under 60 characters in sentence case, with no colon; a hint on every switch and choice; a
  title on every card, and `titles` for each size within its limit, so each stays on one line; a logo with an `alt`
  that says what it shows.
- **Updates:** `changes` for each version; `update.before` and `update.after` when it works in the background; a
  `health` path that answers 200 only when it can really work.
- **Card refresh times:** cards answer from a small file the plug-in keeps, never by doing the work when asked;
  `refresh_seconds` (10 to 3600) only for a card that shows progress, and the slowest one that still feels current.
- **The content rules:** British English, sentence case, no em dashes, no contractions, no exclamation marks; settings
  are activated or deactivated.

### A card plug-in

For a plug-in that shows something on the dashboard, such as Watching now or Disk forecast. Paste in
[Plug-in manifest reference](plugin-manifest-reference.md), [Plug-in API reference](plugin-api-reference.md) and
[Make your first plug-in](make-a-plugin.md).

```text
Write a Starboard plug-in for plug-in API 1.25 that [say what it should do, and what its card shows].
Starboard is a lightweight home-server dashboard (https://github.com/TheMightyTRex/starboard). I have
pasted three pages from its help centre below: the plug-in manifest reference, the plug-in API reference
and the "Make your first plug-in" tutorial. Use only what they describe.

Give me:
- starboard-plugin.json, with manifest_version 1, "starboard_api": ">=1.14 <2.0", and only the fields in
  the manifest reference.
- The program for its one container, in Python with only the standard library, answering on one port:
  its health path, each card's path, each action's path and each job's path.
- A Dockerfile. The container runs read only as a user that is not root: write only to /tmp, or to /data
  if the manifest asks for the data volume.
- logo.svg, named in "logo" with an "alt": a simple solid symbol on a rounded tile, readable at 32 pixels
  in light and dark, with only shapes and paths (no scripts, styles, pictures or outside links), under
  16 KB.
- A "changes" entry for version 1.0.0.

The card:
- Choose stat, list, status or sparkline (a small line for each series, such as response times over a day,
  with the latest, lowest and highest value in words Starboard works out), and answer in exactly that shape,
  with an example in the manifest. A sparkline card needs "starboard_api": ">=1.17 <2.0".
- To send alerts, ask for the alerts:send permission and POST /api/v1/plugin/alerts as "Sending alerts" in
  the plug-in API reference says: raised once until cleared, at most 30 new alerts an hour.
- Starboard draws the grey band (logo, name, status chip, when it last updated). Add "status" (one of the
  values in "The card band"), "updated" (seconds since 1970, when what it shows last changed, never in the
  future) and "status_label" (up to 24 characters) only where Starboard's word does not fit.
- Give the card "titles", a title for each size that fits on one line: small up to 17 characters,
  medium 28, half 22, wide 43 and full 45. Put the words that matter first. Titles need
  "starboard_api": ">=1.15 <2.0", or ">=1.17 <2.0" for a sparkline card or alerts.
- If it works with one system, such as Jellyfin or Plex, name it in "requires" (for example ["jellyfin only"] or
  ["plex or emby"]), which needs "starboard_api": ">=1.19 <2.0". Without it, Starboard works the tag out from the
  permissions.
- If the app starts with a password everyone knows, make Starboard set a long random one and show it once: name it in
  "first_sign_in" (the sign-in name, the {secret:name} the app reads and a file its start-up writes when the password
  is set), which needs "starboard_api": ">=1.21 <2.0".
- Keep a small JSON file in /data up to date in the background, and have the card only read it.
- Leave out refresh_seconds unless the card shows progress.

Rules:
- Read settings from /run/starboard/settings.json and keys from /run/starboard, as the plug-in API
  reference says. Never print a secret or a key to the log.
- Use the default network unless it truly needs my home network (network:lan) or my VPN (network:vpn).
- If it runs a job when people choose, use a setting of type "schedule" and name it in the job's
  "schedule".

- If it changes Jellyfin's posters, photos or details, ask for "jellyfin:metadata", mount
  "jellyfin-metadata" (or "jellyfin-metadata:ro" to only read) at /metadata, run as "user": "media", and
  check each file before it replaces the one Jellyfin saved.
- If it fills folders that Jellyfin shows as libraries, ask for "jellyfin:libraries" and name each library
  in "jellyfin_libraries" (name, type and a folder inside a media folder it mounts). Leave out
  "realtime_monitor" unless Jellyfin must notice files the plug-in does not tell it about: Starboard keeps
  real-time monitoring deactivated, so the plug-in must ask Jellyfin to refresh the library after it adds
  files.
- If I will share it only as a zip file (a private plug-in), mark the container "build": true with the
  image "local/<id>:<version>", and keep the Dockerfile to the rules in "Built from a zip file" in the
  manifest reference: no "# syntax=" line, no RUN --mount, ADD only from the zip, FROM with a full image
  name.
- If it moves films or series out of the library, ask for "library:holding", mount "media:holding" at
  /media, run as "user": "media", move only into /media/.holding/<id>/ keeping the folders, never delete,
  show a preview first, and offer Put back with "restore" on each moved row.
- Set starboard_api to the lowest plug-in API version that has every field it uses.
Then follow this checklist and say, for each line, what you did:
1. Permissions: the fewest that work, each explained in one sentence.
2. Memory limits: the smallest "resources" that work, within 512 MB and 1.0 core; "when_needed" if only
   Starboard reaches it.
3. Accessibility: labels under 60 characters, sentence case, no colon; a hint on every switch and choice;
   a title on every card, and titles for each size within their limits; the logo's alt says what it shows.
4. Updates: "changes" for the version; update.before and update.after if it works in the background; a
   health path that answers 200 only when it can work.
5. Card refresh times: the card reads a file; refresh_seconds only for progress.
6. Content rules: British English, sentence case, no em dashes, no contractions, no exclamation marks;
   settings are activated or deactivated.
Use an image tag for now (unless it is a zip file), and tell me how to pin it by digest before I share it.
After the files, list each permission, network and folder it asks for, in plain words.

The pages:
[paste the three pages here]
```

### An app plug-in

For a whole app made by others, such as Seerr or Kavita, run by Starboard with its own web page on the home network.
Paste in [Plug-in manifest reference](plugin-manifest-reference.md) (in particular [App plug-ins](plugin-manifest-reference.md#app-plug-ins)
and [Resources](plugin-manifest-reference.md#resources)) and [Test and publish a plug-in](test-and-publish-a-plugin.md).

```text
Write a Starboard app plug-in for plug-in API 1.25 that runs [the app, with its image name and the
version I want] so people on my home network can use it. Starboard is a lightweight home-server
dashboard (https://github.com/TheMightyTRex/starboard). I have pasted its manifest reference and its page
on testing and publishing below. Use only what they describe.

Give me:
- starboard-plugin.json with "starboard_api": ">=1.14 <2.0", the permissions network:lan and
  network:port, and one container per part of the app (the app, and its database if it needs one).
- For the app's container: "network": "lan", "publish": true and "host_port" set to the app's usual port,
  so Starboard chooses a free port and shows the address with Open.
- Its folders at the paths the app expects ("data:/config" and the like), and media folders read only
  ("media/books:ro") unless the app must change them; say why for each one.
- "tmpfs" for any folder the app writes to in memory, and "pids" if the app starts many threads.
- "env" values from {secret:<name>}, {jellyfin:url} or {jellyfin:key} where the app needs them.
- "adopt" only if the main install may already run this app and its data should be copied in.
- logo.svg and "logo" with an "alt": a neutral symbol of what the app does on a rounded tile, never the
  app's own logo.
- A README with: who it is for, how to set it up (its admin account first), what it may do, what it uses
  at rest (leave the figures as "not measured yet" until I measure them), and what removing it keeps.

Then follow this checklist and say, for each line, what you did:
1. Permissions: only network:lan and network:port unless the app needs more, each explained.
2. Memory limits: "resources" for each container from the app's own advice, at most 2048 MB and 4 cores.
3. Accessibility: say in the README that the app's own pages are made by others and not checked by
   Starboard; labels and hints in the manifest follow the plug-in tester's rules.
4. Updates: a "changes" entry; the image pinned by digest; what happens to the app's data on Roll back.
5. Card refresh times: an app plug-in needs no card; if you add one, it reads a file and has no
   refresh_seconds.
6. Content rules: British English, sentence case, no em dashes, no contractions, no exclamation marks;
   settings are activated or deactivated.

The pages:
[paste the pages here]
```

### A plug-in that converts files

For a plug-in that changes files in the media folder or Jellyfin's pictures, one at a time, such as Direct play or
Picture shrinker. Paste in [Plug-in manifest reference](plugin-manifest-reference.md) (in particular
[Adding files to the media folder](plugin-manifest-reference.md#adding-files-to-the-media-folder),
[Jellyfin's metadata folder](plugin-manifest-reference.md#jellyfins-metadata-folder) and [Updates](plugin-manifest-reference.md#updates)),
[Plug-in API reference](plugin-api-reference.md) and [Write a plug-in that updates safely](update-a-plugin-safely.md).

```text
Write a Starboard plug-in for plug-in API 1.25 that [say what it converts, and why], one file at a time.
Starboard is a lightweight home-server dashboard (https://github.com/TheMightyTRex/starboard). I have
pasted its manifest reference, its plug-in API reference and its page on updating a plug-in safely
below. Use only what they describe. Direct play, in the starboard-plugins collection, is the model:
https://github.com/TheMightyTRex/starboard-plugins/tree/main/direct-play

Give me:
- starboard-plugin.json with "starboard_api": ">=1.14 <2.0", mounting only the media folders it changes
  ("media/movies", "media/tv") or "jellyfin-metadata" with the permission "jellyfin:metadata", and
  "user": "media" so the files it writes belong to the media folder's owner.
- A worker that converts one file at a time at the lowest priority (nice 19), only in the hours people
  choose (a "choice" or a "schedule" setting), with Pause and Resume buttons.
- A check of every new file before it replaces the original: it opens, it is the right length, and it is
  smaller or better as promised. A file that fails is left as it was and listed. Write each new file
  beside the original under a hidden name and swap it in only after the check.
- A setting to keep the originals instead of replacing them.
- Two cards: a list card of what it converts now, what is next and the totals, and a stat card of the
  space saved with "format": "bytes".
- update.before that stops or finishes the file being converted and starts no new one, answering
  {"ok": false, "said": "..."} when it is not safe; update.after that carries on, for "updated" and
  "rolled_back"; a health path; and "changes".

Its list card, worked through (Direct play's):
- Manifest: {"id": "now", "title": "Direct play", "type": "list", "path": "/card", "refresh_seconds": 30}
- Answer: {"items": [{"title": "Converting now: Dune (2021)", "detail": "Shrink, 34% done, about 1 hour
  5 minutes left"}, {"title": "Next: Slow Horses, series 1 episode 3", "detail": "Add a playable sound
  track"}, {"title": "Totals", "detail": "1,173 files fixed, 1.03 TB saved, 40 files still to do"}],
  "refresh_seconds": 30, "status": "converting", "updated": 1794694110}
- refresh_seconds comes from a "Card updates every" setting (10, 30, 60 or 300 seconds), so the answer
  wins over the manifest. status is converting, paused, done, needs_setup (no device chosen) or waiting.
  updated is when the status file last changed. The card only reads that file: nothing is probed when
  the card is asked, and the worker writes the file only as often as the card is asked.

Then follow this checklist and say, for each line, what you did:
1. Permissions: only the folders it changes, and jellyfin:key or reelix:key only if it must tell
   Jellyfin or Reelix; each explained.
2. Memory limits: within 512 MB and 1.0 core; the converter runs only while a file is converted.
3. Accessibility: labels under 60 characters, sentence case; a hint on every switch and choice; both
   cards titled; the logo's alt says what it shows; progress in words, not only a number.
4. Updates: update.before, update.after, health and changes as above; no half-written file is ever left.
5. Card refresh times: refresh_seconds only on the progress card, from the setting; the stat card asked
   every 10 minutes ("refresh_minutes": 10).
6. Content rules: British English, sentence case, no em dashes, no contractions, no exclamation marks;
   settings are activated or deactivated.

The pages:
[paste the pages here]
```

## More prompts

### Make a plug-in's next version update safely

Paste in [Write a plug-in that updates safely](update-a-plugin-safely.md), the [Updates](plugin-manifest-reference.md#updates)
and [Changes](plugin-manifest-reference.md#changes) parts of the manifest reference, then both versions of your
`starboard-plugin.json`.

```text
I am making version [new version] of my Starboard plug-in, [its name]. I have pasted Starboard's help on
updating a plug-in safely, then the manifest of the version people have now, then the new one. Use only
what the help describes.

Give me, for the new manifest:
- A "changes" entry for the new version, newest first, in Added, Changed, Removed and Fixed, saying in
  plain words any setting that moves or goes.
- "update.migrations": a step named after the version that made each change, with "rename" for every
  setting key that changed, "remove" for every key that went, and "defaults" only where a default changed
  and people who never chose a value should get the new one. Keep the older steps.
- "update.before" and "update.after" if it does work in the background, and the code for both paths.
- A "health" path that answers 200 only when it can really work, and a "health_wait_seconds" long enough
  for it to start.
- "starboard_api" of at least ">=1.14 <2.0".
Then list how I test the update from the old version, the Roll back, and a failing health check.

The pages and both manifests:
[paste them here]
```

### Write a script that reads Starboard's API

Paste in [API reference](api-reference.md), [Authentication and keys](api-authentication.md) and the
[list of API errors](../../api/errors.md). Or give it your Starboard's own description, at `/api/v1/openapi.json`.

```text
Write a [Python / shell] script that [say what it should do with Starboard's information].
Starboard is a lightweight home-server dashboard with a read-only API at /api/v1. I have pasted its API
reference, its page on authentication and keys, and its list of errors below. Use only what they describe.

About my set-up:
- Starboard's address: http://192.168.1.20:8095 (change this to mine before I run it).
- The script runs: [on the server / on another computer at home / in Home Assistant].

Rules:
- Read the key from the environment variable STARBOARD_KEY. Never put a key in the code, in an
  address or in the output. Send it only as the header Authorization: Bearer <key>.
- Python: use only the standard library (urllib.request and json).
- For lists, follow next_cursor until it is null, with limit up to 200.
- Keep the last ETag and send If-None-Match; treat 304 as "nothing new".
- Stay under 120 requests a minute. On 429, wait the seconds in Retry-After.
- For updates, use a key with only the "updates" scope, one update at a time, and follow
  GET /api/v1/updates/runs/{id} until it is not "running".
- On an error, print its code and detail from the problem details, and stop.

The pages:
[paste the pages here]
```

### Ask questions about the API or the plug-in system

```text
Answer my questions about Starboard, a lightweight home-server dashboard, using only the help pages I
have pasted below. If the pages do not say, tell me so rather than guessing. Quote the heading you used
for each answer.

My question: [your question]

The pages:
[paste the pages here]
```

## Which pages to give it

| To do this | Give it these pages |
|---|---|
| Build a card plug-in | [Plug-in manifest reference](plugin-manifest-reference.md), [Plug-in API reference](plugin-api-reference.md), [Make your first plug-in](make-a-plugin.md) |
| Build an app plug-in | [App plug-ins](plugin-manifest-reference.md#app-plug-ins), [Resources](plugin-manifest-reference.md#resources), [Test and publish a plug-in](test-and-publish-a-plugin.md) |
| Build a plug-in that converts files | [Adding files to the media folder](plugin-manifest-reference.md#adding-files-to-the-media-folder), [Jellyfin's metadata folder](plugin-manifest-reference.md#jellyfins-metadata-folder), [Write a plug-in that updates safely](update-a-plugin-safely.md) |
| Design a card or a logo | [The card band](plugin-api-reference.md#the-card-band-api-114), [How often a card is asked](plugin-api-reference.md#how-often-a-card-is-asked-api-114), [Logo](plugin-manifest-reference.md#logo) |
| Make a new version that updates safely | [Write a plug-in that updates safely](update-a-plugin-safely.md), [Updates](plugin-manifest-reference.md#updates), [Changes](plugin-manifest-reference.md#changes) |
| Run a job when people choose | [A job on a schedule from its settings](plugin-manifest-reference.md#a-job-on-a-schedule-from-its-settings) |
| Publish a plug-in or a catalogue | [Test and publish a plug-in](test-and-publish-a-plugin.md), [Catalogues](plugin-api-reference.md#catalogues) |
| Read Starboard's API | [API reference](api-reference.md), [Authentication and keys](api-authentication.md), [List of API errors](../../api/errors.md) |
| Find every developer page | The help centre's `llms.txt`, a plain list of these pages made for AI assistants |

## Things to note

- **Recommended:** only Starboard's own plug-in collection may mark a catalogue entry `recommended`, which puts it
  first with a **Recommended** chip. Leave it out of your own catalogue: Starboard ignores it there, and nothing is
  ever added until the person chooses it.
- **Examples to copy:** the [starboard-plugins collection](https://github.com/TheMightyTRex/starboard-plugins) has a
  plug-in of each kind, and its [help centre](https://themightytrex.github.io/starboard-plugins/help/) explains how each
  is built, with Direct play's card worked through.
- An AI assistant can be wrong with confidence. Test every plug-in with the plug-in tester, and test every script
  with a key you can revoke.
- Never paste a real API key, password or your home address on the internet into an assistant. Use
  `STARBOARD_KEY` in what you share, and revoke any key you paste by mistake.
- Read the permissions an assistant asks for in a manifest. Remove any it does not need.
- These prompts describe plug-in API 1.15. When Starboard's plug-in API moves on, Starboard's own checks fail until
  someone updates this page.

## Find out more

- [Make your first plug-in](make-a-plugin.md)
- [Write a plug-in that updates safely](update-a-plugin-safely.md)
- [Ask an AI assistant to help you set up](../topics/ask-an-ai-for-help.md)
- [The plug-in collection](../basics/plugin-collection.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
