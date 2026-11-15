# Line speed: Settings
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Line speed's settings are on its own tab: go to **Settings**, then **Plug-ins**, then **Line speed**. Starboard draws them and keeps them; secrets are never shown again once saved.

## Settings

| Setting | What it does | Default |
|---|---|---|
| **Test at** | Choose an hour when nothing is downloading. A number from 0 to 23 o'clock. | 4 o'clock |
| **Test size** | Larger is more accurate on fast lines, and uses more of any data allowance. A number from 5 to 200 MB. | 25 MB |

## Buttons

These are on Line speed's tab.

- **Test now** runs a test straight away, downloading one test file. When it is done, Starboard shows the speed in **Actions** and on the cards. It is in **Actions**, and works only while Line speed is active.

## Things to note

- Each setting is saved when you leave the box.
- A setting you change is used straight away; you do not need to deactivate it first.
- **How it tests:** it downloads a file of **Test size** from Cloudflare's speed test (`speed.cloudflare.com`) and times it. It measures download speed only, not upload.
- **When it tests:** it looks every 10 minutes, and tests once during the hour you chose, if there is no result for today yet. A **Test now** earlier the same day counts as today's result, so the night's test is skipped.
- **What it keeps:** the last 14 results, in its own folder. **Line speed this week** shows the newest 7.
- Every test uses **Test size** of any data allowance you have.
- Settings are kept when you update or deactivate it, and when you remove it they stay in its folder.

## Find out more

- [Install](../line-speed/install.md)
- [Dashboard card](../line-speed/dashboard-card.md)
- [Problems](../line-speed/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
