# Download summary: Settings
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Download summary has no settings of its own, and no buttons. It reads the download queue from Starboard.

## Things to note

- It only counts what goes through the queue in Starboard, from the apps added in **Settings**, then **Apps**. Downloads made any other way are not counted.
- It reads the queue once a minute. A download that was already partly done when it first saw it counts only from then on.
- The last minute of a download that finishes and leaves the queue before the next reading may be missed, so the totals can be a little low.
- It keeps the last 14 days of totals in its own folder. Nothing is sent anywhere.
- It only reads. It never pauses, removes or changes a download.

## Find out more

- [Install](../download-summary/install.md)
- [Dashboard card](../download-summary/dashboard-card.md)
- [Problems](../download-summary/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
