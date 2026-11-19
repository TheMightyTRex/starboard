# Checkrr: Settings
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Checkrr's settings are on its own tab: go to **Settings**, then **Plug-ins**, then **Checkrr**. Starboard draws them.

## Settings

| Setting | What it does | Default |
|---|---|---|
| **Files that failed the check** | A page of its own: each file Checkrr could not read as a film or episode in its last check, grouped into Films and Series, with Checkrr's reason and when it found it. You can read it, but not change it. | None |

## Buttons

These are on Checkrr's tab.

- **Check now** starts a check straight away, after you confirm, rather than waiting for Sunday night. It reads each file and changes nothing.

## What it checks

- **Which files:** everything in your `movies` and `tv` folders, except pictures, subtitles and text files such as `.nfo`, `.srt` and `.jpg`, and folders whose names start with a dot.
- **How:** the start of each file must be a known film, episode or sound file, and FFprobe must read it. A film or episode with no sound track also fails.
- **What it finds:** files whose start is damaged, files that are not media at all, and videos with no sound. A file cut short part way through can pass, because the deeper check that plays each file through FFmpeg is not used here: it would take far more of the processor every week.
- **When:** each Sunday at 03:30, in the server's time zone, and when you select **Check now**. A file that passed is remembered, so the next check skips it unless it changed.

## Things to note

- **It only reports.** It never deletes, moves, renames or replaces a file, and it cannot: your folders are read only to it, and it is given no Reelix, Radarr, Sonarr or Lidarr.
- **Its settings file** is `data/plugins/checkrr/data/app/checkrr.yaml` in Starboard's data. Starboard writes it once, when Checkrr first starts, and never over a change you make. Change it only if you know Checkrr well, then deactivate and activate the plug-in.
- **Its own page** lists the same files and its figures. Anyone on your home network can open it and start a check or clear its list: clearing the list does not touch the files.
- Its list and figures are kept when you update or deactivate it, and when you remove it they stay in its folder.

## Find out more

- [Install](../checkrr/install.md)
- [Dashboard card](../checkrr/dashboard-card.md)
- [Problems](../checkrr/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
