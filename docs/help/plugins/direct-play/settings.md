# Direct play: Settings
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Direct play's settings are on its own tab: go to **Settings**, then **Plug-ins**, then **Direct play**. Starboard draws them and keeps them; secrets are never shown again once saved.

## Files

| Setting | What it does | Default |
|---|---|---|
| **Files** | A page of its own: every file in tables, **Converting now**, **Still to do**, **Not fixed** with the reason, and **Left alone**, such as HEVC files or files it cannot read. Its first lines say how many files are fixed, how much space is saved and which file was fixed last. You can search and filter it, but not change it. | None |

## Devices

| Setting | What it does | Default |
|---|---|---|
| **Roku Express and older Rokus** | H.264 up to 1080p; Dolby Digital, AAC and MP3 sound. No HEVC, DTS or TrueHD. Activated or deactivated. | Activated |
| **Roku 4K** | Roku Express 4K, Streaming Stick 4K and Ultra: H.264 and HEVC up to 4K. No DTS or TrueHD. Activated or deactivated. | Deactivated |
| **Fire TV Sticks** | H.264 and HEVC up to 1080p, so the HD sticks play them too. No DTS or TrueHD. Activated or deactivated. | Deactivated |
| **Chromecast** | H.264 up to 1080p; AAC, MP3, Opus and FLAC sound. No HEVC, Dolby Digital, DTS or TrueHD. Activated or deactivated. | Deactivated |
| **Smart TV apps** | Jellyfin on Samsung and LG televisions: H.264 and HEVC up to 4K. No DTS or TrueHD. Activated or deactivated. | Deactivated |
| **Web browsers** | H.264 up to 4K; AAC, MP3, Opus and FLAC sound. No HEVC or Dolby Digital, so files with only Dolby Digital get a stereo track. Activated or deactivated. | Deactivated |
| **Apple TV** | H.264 and HEVC up to 4K; Dolby Digital, AAC and FLAC sound. No DTS or TrueHD. Activated or deactivated. | Deactivated |
| **Nvidia Shield** | Nearly everything, DTS and TrueHD included, up to 4K. Activated or deactivated. | Deactivated |

## When it works

| Setting | What it does | Default |
|---|---|---|
| **When it works** | One file at a time, at the lowest priority. The file being converted always finishes, so work can run past the end of the hours. One of: At weekends (all day Saturday and Sunday), In Starboard's quiet hours (your download hours if you set them, or 01:00 to 06:00), Any time. | At weekends |

## Shrink

| Setting | What it does | Default |
|---|---|---|
| **Shrink very large H.264 files** | Converts again any H.264 file with a higher bitrate than its size's limit, at the same picture quality. A file is kept as it was when it would not get at least a tenth smaller. Activated or deactivated. | Activated |
| **Shrink 1080p files over** | A number from 4 to 80 Mbps. | 15 Mbps |
| **Shrink 720p files over** | A number from 2 to 40 Mbps. | 8 Mbps |
| **Shrink smaller files over** | A number from 1 to 20 Mbps. | 5 Mbps |

## More

| Setting | What it does | Default |
|---|---|---|
| **Convert HEVC to H.264** | Only when none of your devices plays HEVC. H.264 files are larger, so this uses more space. Activated or deactivated. | Deactivated |
| **Keep the originals** | Moves each original to a .direct-play-originals folder in movies or tv instead of replacing it, so you can delete them yourself. Saves no space until you do. Activated or deactivated. | Deactivated |
| **Card updates every** | How often the Direct play card on the dashboard shows the progress while a file is converted. One of: 10 seconds, 30 seconds, 1 minute, 5 minutes. | 30 seconds |

## Buttons

These are on Direct play's tab.

- **Pause fixing** stops the file being converted at once, removes its unfinished copy and leaves the original as it was. That file is done again later. Nothing new starts until you resume.
- **Resume fixing** carries on, straight away when it is inside the hours set in **When it works**, or when they next start.
- **Check the library now** finds new or changed files in your movies and tv folders straight away, at any hour, even while paused. Only new or changed files are read.

## Things to note

- Choose your devices before you activate it. **Roku Express and older Rokus** is activated when you add it. A file is fixed only when one of the devices you chose cannot play it.
- A setting you change is used from the next file; you do not need to deactivate it first. The file being converted finishes with the settings it started with.
- It only works in your movies and tv folders, and never downloads anything.
- With **Keep the originals**, the `.direct-play-originals` folders stay when you remove it. Delete them yourself when you are happy with the new files.
- A file that failed its check is not tried again until the file changes.
- Settings are kept when you update or deactivate it, and when you remove it they stay in its folder.

## Find out more

- [Install](../direct-play/install.md)
- [Dashboard card](../direct-play/dashboard-card.md)
- [Problems](../direct-play/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
