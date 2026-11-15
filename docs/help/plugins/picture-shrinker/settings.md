# Picture shrinker: Settings
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Picture shrinker's settings are on its own tab: go to **Settings**, then **Plug-ins**, then **Picture shrinker**. Starboard draws them and keeps them; secrets are never shown again once saved.

## Settings

| Setting | What it does | Default |
|---|---|---|
| **Space saved** | A page of its own: how much space it has saved, how many pictures it has shrunk and when it runs next, then a table of each run with what started it, how many pictures were shrunk, left as they were or could not be read, and how it ended. Pictures it could not read are listed under **Could not read**, with the reason. You can read it, but not change it. | None |
| **When to shrink** | Every day, week or month, at a time. It works at the lowest priority, so a time when the server is quiet is best. In a month without the date you chose, such as the 31st in April, it runs on the last day. | Every week on Sunday at 03:30 |
| **Posters no taller than** | A poster taller than this is shrunk to this height. 900 pixels looks sharp on a television. A number from 300 to 3,000 pixels. | 900 pixels |
| **Photos of people no wider than** | A photo of a cast or crew member wider than this is shrunk to this width. A number from 100 to 2,000 pixels. | 400 pixels |
| **Shrink new pictures in quiet hours** | Each hour of quiet hours, shrinks the posters and photos Jellyfin saved since the last pass, so they never build up. Activated or deactivated. | Deactivated |

## Buttons

These are on Picture shrinker's tab.

- **Shrink now** starts a run straight away, at the lowest priority. If a run is already going, it says "Already shrinking". The card and the **Space saved** page say how far it has gone. **Run now** in **System**, then **Jobs**, does the same.
- **Stop shrinking** stops the run after the picture it is on. The next run carries on where it stopped.

## Things to note

- A change to the sizes is used from the next run; you do not need to deactivate it first. A smaller number saves more space. A picture already shrunk is not made larger again if you choose a larger number.
- A run stops itself after 115 minutes, and the next one carries on. Pictures already shrunk are only opened, never written again.
- It changes only posters and photos of people. Backdrops, logos and every other picture are left alone.
- **System**, then **Jobs**, shows when it runs next.
- The pictures it shrank stay shrunk when you remove it. Jellyfin downloads a larger copy again if you choose **Refresh metadata** and **Replace existing images** for a film or series in Jellyfin.
- Settings are kept when you update or deactivate it, and when you remove it they stay in its folder.

## Find out more

- [Install](../picture-shrinker/install.md)
- [Dashboard card](../picture-shrinker/dashboard-card.md)
- [Problems](../picture-shrinker/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
