# Tdarr: Settings
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Tdarr's tab has a **Settings** section that Starboard draws: the same choices as Starboard's own Tdarr page, in **Settings**, then **Tdarr**. Starboard writes them into Tdarr, so you never sign in to it. Tdarr's own page, opened with **Open Tdarr**, still shows everything.

The section is there while Tdarr is active. When it is not, it says to activate Tdarr first. Each choice is used straight away and says so beside itself: there is nothing to save.

## Its settings

| Setting | What it does | Default |
|---|---|---|
| **Libraries** | **Films** and **Series**: the folders Tdarr works on. Inside its container they are `/media/movies` and `/media/tv`. | Both |
| **What Tdarr does** | **Save space** converts to H.265 and keeps the new file only when it is smaller. **Check files only** finds damaged files and changes nothing. **Off** means Tdarr does nothing until you choose again. | Not checked |
| **Conversions at once** | From **1 at a time (lightest)** to **4 at a time**. Each one uses about one processor core while it runs. | 1 at a time |
| **When** | **Any time** starts on new files straight away. **In quiet hours** converts in Starboard's download hours when they are set, otherwise 01:00 to 06:00, so the server stays quick in the day. | In quiet hours |

Under the choices, **Files Tdarr knows** shows how many files it has converted and checked, and the space saved so far. If Tdarr also has libraries you made yourself, the section names them and Starboard leaves them as they are.

## Buttons

- **Connect Tdarr** is there while Tdarr is not connected yet. It gives Tdarr a key Starboard keeps, so you never sign in to Tdarr. Tdarr restarts once, and Starboard waits up to 90 seconds for it to answer.
- **Bring in the Tdarr you already have…**, under **Your Tdarr**, copies the Tdarr from the main install into the plug-in, with its libraries, flows and history. It is there while the plug-in is not active. Read [Install](../tdarr/install.md#set-it-up).
- **Open Tdarr** opens Tdarr's own page in a new tab. It is there while it is active.
- **Activate** starts it, and Starboard chooses a free port for its page. **Deactivate** stops it and keeps its folder.
- **Try again** starts it again when it did not start.
- **Remove Tdarr** stops it and takes it away. You choose where its folder goes; nothing is deleted, and files it already converted stay as they are.

## Things to note

- **Save space** replaces a file with its smaller copy, in `media/movies` and `media/tv` only. It runs as the owner of your media folder, so the new file is yours.
- Tdarr converts in a `tdarr-cache` folder in your media folder, on the same disks as your films, so working copies of large films cannot fill the system disk.
- Converting is heavy work: Tdarr may use up to 2 GB of memory and 2 processor cores. Keep **Conversions at once** low on a small server.
- Its settings, history and converted-file records are kept when you update or deactivate it, and when you remove it they stay in its folder.

## Find out more

- [Install](../tdarr/install.md)
- [Dashboard card](../tdarr/dashboard-card.md)
- [Problems](../tdarr/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
