[Help centre](../README.md) · Developers
<!-- help: dev / plugins -->

# AI prompts for developers

An AI assistant, such as Claude, can write a Starboard plug-in or a script that reads Starboard's API, if you give
it the rules. Copy one of the prompts on this page, fill in the parts in square brackets, and paste in the pages it
names. The assistant then works from Starboard's own reference rather than guessing.

## Before you begin

- An AI assistant you already use.
- The pages each prompt names, open in your browser, so you can copy them in. An assistant that can open web
  addresses can read them itself: give it the addresses in the prompt instead.
- Starboard's help centre is the final word. If the assistant says something different, follow the help centre.

## Steps

1. Choose the prompt that fits what you want to make.
2. Copy the whole prompt, and fill in the parts in square brackets.
3. Under the prompt, paste the full text of each page it names, each with its title.
4. Send it. Check what comes back with the plug-in tester or a test call before you use it.

### Build a plug-in

Paste in [Plug-in manifest reference](plugin-manifest-reference.md),
[Plug-in API reference](plugin-api-reference.md) and [Make your first plug-in](make-a-plugin.md).

```text
Write a Starboard plug-in that [say what it should do, and what it shows on the dashboard].
Starboard is a lightweight home-server dashboard (https://github.com/TheMightyTRex/starboard).
I have pasted three pages from its help centre below: the plug-in manifest reference, the plug-in API
reference and the "Make your first plug-in" tutorial. Use only what they describe.

Give me:
- starboard-plugin.json, with manifest_version 1 and only the fields in the manifest reference.
- The program for its one container, in Python with only the standard library, answering on one port.
  It must answer every path the manifest names: health, each card's path, each action, /events if it
  lists events, and each job's path.
- A Dockerfile. The container runs read only as a user that is not root, so write only to /tmp, or to
  /data if the manifest asks for the data volume.
- logo.svg next to the manifest, named in "logo" with an "alt" that says what it shows: a simple, solid
  shape on a 24 by 24 viewBox that reads at 32 pixels, with only shapes and paths (no scripts, styles,
  pictures, text links or url() other than url(#id)), under 16 KB.

Rules:
- Ask for the fewest permissions that work, and tell me why each one is needed.
- Use the default network unless it truly needs my home network (network:lan) or my VPN (network:vpn).
- Read settings from /run/starboard/settings.json and the API key from /run/starboard/key, as the
  plug-in API reference says. Never print a secret or the key to the log.
- Answer each card in exactly the shape for its type, with an example in the manifest.
- Do not lay out the card: Starboard draws a grey band with the logo, the plug-in's name, a status chip and
  when it last updated. If the plug-in works in the background, add "status" (one of the values in "The
  card band" in the plug-in API reference), "updated" (seconds since 1970) and, if Starboard's words do not
  fit, "status_label" (up to 24 characters) to each card's answer. Use "refresh_seconds" (10 to 3600) only
  for a card that shows progress.
- If a job should run when the person chooses, give it a setting of type "schedule" with a default (every
  day, every week on a day, or every month on a date, at a time) and name that setting's key in the job's
  "schedule", rather than a fixed "daily" time.
- If it changes Jellyfin's posters, photos or details, ask for "jellyfin:metadata", mount
  "jellyfin-metadata" (or "jellyfin-metadata:ro" to only read) at /metadata, run as "user": "media", and
  check each file before it replaces the one Jellyfin saved.
- If it fills folders that Jellyfin shows as libraries, ask for "jellyfin:libraries" and name each library
  in "jellyfin_libraries" (name, type and a folder inside a media folder it mounts). Leave out
  "realtime_monitor" unless Jellyfin must notice files the plug-in does not tell it about: Starboard keeps
  real-time monitoring deactivated, so the plug-in must ask Jellyfin to refresh the library after it adds
  files.
- Keep memory and processor within 512 MB and 1.0 processor core; less is better.
- Use a tag for the image for now, and tell me how to pin it by digest before I share it. If I will share
  it only as a zip file (a private plug-in), instead mark the container "build": true with the image
  "local/<id>:<version>", and keep the Dockerfile to the rules in "Built from a zip file" in the manifest
  reference: no "# syntax=" line, no RUN --mount, ADD only from the zip, FROM with a full image name.
- Set starboard_api to the lowest plug-in API version that has every field it uses.
- After the files, list each permission, network and folder it asks for, in plain words.

The pages:
[paste the three pages here]
```

Then test it. Read [Test and publish a plug-in](test-and-publish-a-plugin.md#test-it). Paste the tester's issues
back into the assistant and ask it to fix them.

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
  address or in the output.
- Send the key only as the header Authorization: Bearer <key>.
- Python: use only the standard library (urllib.request and json). No extra packages.
- For lists, follow next_cursor until it is null, with limit up to 200.
- Keep the last ETag and send If-None-Match; treat 304 as "nothing new".
- Stay under 120 requests a minute. On 429, wait the seconds in Retry-After.
- On an error, print its code and detail from the problem details, and stop.
- Explain each part in a sentence, then show me how to run it.

The pages:
[paste the pages here]
```

### Design a plug-in's card and logo

Paste in [Plug-in API reference](plugin-api-reference.md) (its Card answers and The card band) and the
[Logo](plugin-manifest-reference.md#logo) part of the manifest reference.

```text
Help me design the dashboard card and the logo for my Starboard plug-in, [its name], which [say what it
does]. I have pasted the parts of Starboard's help that describe card answers, the card band and logos.
Use only what they describe.

Give me:
- Which card type fits (stat, list, status or guide) and why, with an example answer in that exact shape.
- Which "status" values it should send and when, with "status_label" only where Starboard's own words do
  not fit, and how it fills "updated". Remember Starboard draws the grey band, the name and the chip itself.
- A "refresh_seconds" only if the card shows progress, and the slowest one that still feels current.
- logo.svg: a simple solid shape on a 24 by 24 viewBox that reads at 32 pixels in light and dark, using only
  shapes, paths and gradients (no scripts, styles, pictures, links outside it or event handlers), under
  16 KB, and an "alt" of 3 to 80 characters saying what it shows, not the plug-in's name.

The pages:
[paste the pages here]
```

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
- "update.before" and "update.after" if it does work in the background, and the code for both paths in its
  program: before finishes or pauses the work and answers {"ok": false, "said": "..."} when it is not safe
  to update; after starts the work again for outcome "updated" and "rolled_back".
- A "health" path that answers 200 only when it can really work, and a "health_wait_seconds" long enough
  for it to start.
- "starboard_api" of at least ">=1.14 <2.0".
Then list how I test the update from the old version, the Roll back, and a failing health check.

The pages and both manifests:
[paste them here]
```

### Update Starboard and its plug-ins from a script

Paste in [the API reference](api-reference.md) (its Updates part) and [Authentication and keys](api-authentication.md).

```text
Write a [Python or shell] script that keeps my Starboard up to date through its API. It reads the key from
the STARBOARD_KEY environment variable: a "Read and manage" key with only the "updates" scope ticked.
I have pasted the parts of Starboard's help that describe the updates addresses and keys. Use only what
they describe.

It should:
- Read GET /api/v1/updates and list each item with update_available, and why when it cannot update.
- For [the items I want, such as every plug-in], POST /api/v1/updates with {"target": ...} and a new
  Idempotency-Key, one at a time, because Starboard runs one update at a time.
- Follow GET /api/v1/updates/runs/{id} every 5 seconds until its state is not "running", printing each
  step, and stop on "went-back", "refused" or "failed" with the run's "said".
- Wait and try again later on 409 update_running; never retry a 409 cannot_update.

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
| Build or change a plug-in | [Plug-in manifest reference](plugin-manifest-reference.md), [Plug-in API reference](plugin-api-reference.md), [Make your first plug-in](make-a-plugin.md) |
| Design a card or a logo | [Plug-in API reference](plugin-api-reference.md#the-card-band-api-114), [Logo](plugin-manifest-reference.md#logo) |
| Make a new version that updates safely | [Write a plug-in that updates safely](update-a-plugin-safely.md), [Updates](plugin-manifest-reference.md#updates), [Changes](plugin-manifest-reference.md#changes) |
| Update Starboard, apps and plug-ins from a script | [API reference: Updates](api-reference.md#updates), [Authentication and keys](api-authentication.md#rights-and-scopes) |
| Run a job when people choose | [A job on a schedule from its settings](plugin-manifest-reference.md#a-job-on-a-schedule-from-its-settings) |
| Add styles to a plug-in | [Write a plug-in](../basics/write-a-plugin.md), which also has a prompt for styles |
| Publish a plug-in or a catalogue | [Test and publish a plug-in](test-and-publish-a-plugin.md), [Plug-in API reference](plugin-api-reference.md#catalogues) |
| Read Starboard's API | [API reference](api-reference.md), [Authentication and keys](api-authentication.md), [List of API errors](../../api/errors.md) |
| Find every developer page | The help centre's `llms.txt`, a plain list of these pages made for AI assistants |

## Things to note

- An AI assistant can be wrong with confidence. Test every plug-in with the plug-in tester, and every script with
  a key you can revoke.
- Never paste a real API key, password or your home address on the internet into an assistant. Use
  `STARBOARD_KEY` in what you share, and revoke any key you paste by mistake.
- Read the permissions an assistant asks for in a manifest. Remove any it does not need.

## Find out more

- [Ask an AI assistant to help you set up](../topics/ask-an-ai-for-help.md)
- [Make your first plug-in](make-a-plugin.md)
- [API quickstart](api-quickstart.md)
- [Write a plug-in](../basics/write-a-plugin.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
