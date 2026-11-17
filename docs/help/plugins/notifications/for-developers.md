# Notifications: For developers
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

How Notifications is built, for anyone who wants to change it or make one like it. It is MIT, by TheMightyTRexUK, and works with plug-in API `>=1.14 <2.0`.

## Its files

- [`starboard-plugin.json`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/notifications/starboard-plugin.json)
- [`app.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/notifications/app.py)
- [`sbplugin.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/notifications/sbplugin.py)
- [`Dockerfile`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/notifications/Dockerfile)
- [`install.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/notifications/install.py)
- [`logo.svg`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/notifications/logo.svg)
- [`CHANGELOG.md`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/notifications/CHANGELOG.md)
- [`tests/test_notifications.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tests/test_notifications.py)

## Containers

| Container | Network | Folders | Runs as | Starts | Limits |
|---|---|---|---|---|---|
| `main` | `lan` | `data` | `10001:10001` | `when_needed` | 48 MB, 0.1 core |

Each image is pinned by digest in the manifest:

- `main`: `ghcr.io/themightytrex/starboard-plugin-examples@sha256:83b980f1828cdee537bcdf03702ddf6458710cba53f9009938225df430d34d9e`

## What Starboard calls

| Path | What it is |
|---|---|
| `GET /health` | Health: 200 while it can work |
| `GET /card` | The Notifications card (status) |
| `GET /recent` | The Notifications sent card (list) |
| `POST /test/email` | The Send a test email button |
| `POST /test/telegram` | The Send a test to Telegram button |
| `POST /test/discord` | The Send a test to Discord button |
| `POST /test/signal` | The Send a test by Signal button |
| `POST /test/pushover` | The Send a test by Pushover button |
| `POST /test/ntfy` | The Send a test by ntfy button |
| `POST /test/webhook` | The Send a test to the webhooks button |
| `POST /weekly-now` | The Send New this week now button |
| `POST /jobs/weekly` | The job Send New this week on the chosen day |
| `POST /events` | Events: `request.available`, `download.failed`, `app.down`, `app.up`, `disk.nearly_full`, `update.available`, `item.added` |
| `POST /update/before` | The update's before step, 60 seconds at most |
| `POST /update/after` | The update's after step, 10 seconds at most |

## Jobs

- `weekly`: daily at 09:00, 2 minutes at most.

## How it works

- Starboard runs it: each event is a `POST /events`, and New this week is a daily job at 09:00 that sends only on the chosen day, once a week. The container rests 5 minutes after the last one (`start: when_needed`).
- `POST /events` answers at once and sends in the background, because Starboard waits 3 seconds and tries again once. The same event sent twice within 10 minutes is sent once.
- `item.added` is not sent: it is kept in `/data/week.json`, 8 days at most, for New this week. New this week also reads Starboard's `recent`, what the download apps imported.
- One message at a time. The last 20 results are kept in `/data/log.json`, cleaned of every secret first, for both cards.
- Secrets are read from the settings each time and never written to the log, the cards or `/data`.
- Words: meaning is always in the words, never in a symbol or colour, and a link has words before it, "Open Starboard:" and the address.
- Cards set their status with `band()` from `sbplugin.py`. Its before update step holds new runs and waits for one that is running.

## Find out more

- [The plug-in collection's developer pages](https://themightytrex.github.io/starboard-plugins/help/developers/plug-in-api.html)
- [Plug-in manifest reference](../../developers/plugin-manifest-reference.md)
- [Plug-in API reference](../../developers/plugin-api-reference.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
