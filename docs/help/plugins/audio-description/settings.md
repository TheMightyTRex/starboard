# Audio description: Settings
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Audio description's settings are on its own tab: go to **Settings**, then **Plug-ins**, then **Audio description**. Starboard draws them and keeps them; secrets are never shown again once saved.

## Reelix searches

| Setting | What it does | Default |
|---|---|---|
| **Prefer releases with audio description** | Adds an Audio description format to Reelix and prefers it in every quality level. Reelix still takes a release without it when there is no other. Activated or deactivated. | Activated |

## People

| Setting | What it does | Default |
|---|---|---|
| **People who want audio description** | A page of its own that lists everyone in Jellyfin. Activate a person and Jellyfin remembers the sound track they choose, so they choose the described track once for each film and series. Deactivate them and Jellyfin goes back to what they had. | Nobody |

## Your library

| Setting | What it does | Default |
|---|---|---|
| **Titles with audio description** | A page of its own that lists the films with a described sound track, with the track's name, and the series, with how many episodes are described, from the last check. It says when it last checked. | Not a setting |

## Elsewhere

| Setting | What it does | Default |
|---|---|---|
| **Audio description elsewhere** | A page of its own with links to places that offer audio description in their own apps, such as BBC iPlayer, ITVX, Channel 4, My5 and Netflix, and to RNIB, The Audio Description Project and AudioVault. Each link opens in a new tab. | Not a setting |

## Sources

| Setting | What it does | Default |
|---|---|---|
| **AudioVault search links** | A link to AudioVault's own search for each film and series without audio description. Starboard never downloads from AudioVault or reads its pages. Activated or deactivated. | Deactivated |
| **YouDescribe search links** | A link to YouDescribe's own search for each film and series, for described trailers and clips on YouTube. Nothing is fetched from YouDescribe. Activated or deactivated. | Activated |
| **MovieReading and Earcatch** | How to use these phone apps alongside Jellyfin, and where to get them. Neither publishes a list of titles, so Starboard cannot say which films they have. Activated or deactivated. | Activated |

## AudioVault

| Setting | What it does | Default |
|---|---|---|
| **Search AudioVault** | A page of its own, while **AudioVault search links** is activated, with a link to AudioVault's own search for each film and series without audio description. Films and series are listed apart, by first letter when there are more than 80. | Not a setting |

## YouDescribe

| Setting | What it does | Default |
|---|---|---|
| **Search YouDescribe** | A page of its own, while **YouDescribe search links** is activated, with a link to YouDescribe's own search for every film and series, each marked **Described here** or **No description here**. | Not a setting |

## MovieReading and Earcatch

| Setting | What it does | Default |
|---|---|---|
| **MovieReading and Earcatch** | A page of its own, while **MovieReading and Earcatch** under **Sources** is activated: what each app is, links to it in the App Store, on Google Play and on its website, and five steps to use one alongside Jellyfin. | Not a setting |

## Buttons

These are on Audio description's tab.

- **Check for described titles now** reads the sound tracks of every film and episode in Jellyfin straight away, in the background, instead of waiting for tonight's check. It says "Checking for described titles. The list updates in a minute or two".
- **Apply the Reelix choice now** makes Reelix match **Prefer releases with audio description**. It adds the **Audio description** format to Reelix if it is not there, and prefers it in every video quality level. When the setting is deactivated, it puts the scores back to neutral. It says what it did, such as "Reelix prefers releases with audio description in 4 quality levels".

## Things to note

- A change to **Prefer releases with audio description** reaches Reelix when you select **Apply the Reelix choice now**, or the next time Starboard starts.
- A score you set for the **Audio description** format yourself in Reelix is kept. Deactivating **Prefer releases with audio description** puts the score back to neutral but leaves the format in Reelix.
- The switches under **Sources** are used straight away: their pages show or hide their links the next time you open them.
- It checks the library once a night at 04:20, in quiet hours. The lists and cards change after each check.
- It finds a described track by its name, such as "English (Audio Description)", "AD" or "Descriptive audio". Commentary tracks never count. Jellyfin does not read the flag that marks a described track inside a file.
- It never downloads from, or reads the pages of, any website it links to, and never changes a media file.
- Settings are kept when you update or deactivate it, and when you remove it they stay in its folder.

## Find out more

- [Install](../audio-description/install.md)
- [Dashboard card](../audio-description/dashboard-card.md)
- [Problems](../audio-description/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
