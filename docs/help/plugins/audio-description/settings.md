# Audio description: Settings
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Audio description's settings are on its own tab: go to **Settings**, then **Plug-ins**, then **Audio description**. Starboard draws them and keeps them; secrets are never shown again once saved.

## Reelix searches

| Setting | What it does | Default |
|---|---|---|
| **Prefer releases with audio description** | Reelix chooses with its own Audio description format: set it to Prefer in **Settings**, **Reelix**, **Picture quality**. While this is activated, **Check the Reelix choice now** reminds you when Reelix does not prefer it. Activated or deactivated. | Activated |

## People

| Setting | What it does | Default |
|---|---|---|
| **Play the described track** | A page of its own that lists everyone in Jellyfin. Activate a person and, when they start a title with a described track while another plays, Starboard asks their app to change to the described track, within about half a minute. Not every Jellyfin app accepts this; the page says when one did not. | Nobody |
| **People who want audio description** | A page of its own that lists everyone in Jellyfin. Activate a person and Jellyfin remembers the sound track they choose, so they choose the described track once for each film and series. Deactivate them and Jellyfin goes back to what they had. | Nobody |

## Your library

| Setting | What it does | Default |
|---|---|---|
| **Add them to the Audio description collection** | The films and series with a described track go into one Jellyfin collection called Audio description, and the ones without are taken out. Every Jellyfin app shows it. Deactivated, the collection stays as it is. Activated or deactivated. | Activated |
| **Titles with audio description** | A page of its own that lists every film and every episode with a described sound track, from the last check. Read [Titles with audio description](#titles-with-audio-description). | Not a setting |
| **Films to list** | How many films **Titles with audio description** lists: **All**, or the **Last 10**, **Last 20**, **Last 50**, **Last 100** or **Last 500** added to Jellyfin, newest first. | Last 20 |
| **Series to list** | How many series **Titles with audio description** lists, by their newest described episode: **All**, or the **Last 10**, **Last 20**, **Last 50**, **Last 100** or **Last 500**, newest first. Each series still lists all its described episodes. | Last 20 |
| **Jellyfin address for links** | The address you open Jellyfin at in a browser, such as http://192.0.2.10:8096. Each title on **Titles with audio description** opens its page there. Left empty, Starboard's own address for Jellyfin is used when a browser can open it; when Starboard reaches Jellyfin at an address only it can use, such as host.docker.internal, the titles have no link until you enter this. | Empty |

## Titles with audio description

The same page, with the same columns and words, as **Titles with audio description** in Jellyfin's own Audio description plug-in. It lists what the last check found, so it opens straight away and asks Jellyfin nothing.

1. Go to **Settings**, then **Plug-ins**, then **Audio description**, then **Titles with audio description**.
2. The first line says how many films, and how many episodes in how many series, have a described sound track, and when it last checked. Then how many it shows, such as "Showing the last 20 of 143 films and all 6 series, newest first". To change how many, choose **Films to list** and **Series to list** under **Your library**.
3. Choose **Films** or **Series**. Each says its count, such as "3 titles with audio description", and **Series** how many series. **Back to Titles with audio description** returns to the choice.
4. Under **Films**, each film is a row with its name and year, **Described track:** and the track's name, and its status, **Described**.
5. Under **Series**, each series is a row with its name and year, how many of its episodes are described, such as "3 of 6 episodes described" or "All 6 episodes described", and its described track. Choose a series to list its described episodes, in order, such as "S1 E3: Part three", each with its described track and **Described**.
6. Each film and episode has a link, such as "Open Harbour Lights (2019) in Jellyfin", that opens its page in Jellyfin in a new tab.

| Part | What it shows |
|---|---|
| **Title** | The film's name and year, or the episode's series and episode number, such as S1 E3, and its name |
| **Described track** | The name of the first sound track that is audio description, as Jellyfin shows it, such as "English (Audio Description)" |
| **Status** | **Described** for a film or episode; for a series, how many of its episodes are described |
| **Link** | Opens the title's page in Jellyfin, in a new tab, when Starboard knows an address a browser can open |

Films and series are listed newest first, by when they were added to Jellyfin; a series by its newest described episode. More than 150 series open by first letter, with each series as a heading. Up to 4,000 titles are listed. A list kept by version 1.3.0 or earlier has no years, episodes or links: select **Check for described titles now** once to fill it.

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
- **Check the Reelix choice now** reads how Reelix treats releases with audio description and says so, such as "Reelix prefers releases with audio description in 4 quality levels". Where no level prefers them and **Prefer releases with audio description** is activated, it says "To prefer releases with audio description, set Audio description to Prefer in Settings, Reelix, Picture quality". It never changes Reelix: only an admin key may, and Starboard never gives plug-ins one.

## Things to note

- At each check, every film and episode with a described track, and each series with one, gets the tag **Audio description** in Jellyfin, and the tag comes off when the track goes. Other tags stay as they are. In any Jellyfin app, filter a library by that tag.
- When Jellyfin's own Audio description plug-in is installed, this one leaves the tag, the collection and **Play the described track** to it, and its card says **Idle**. The lists, the Reelix choice and the sources still work.
- The words, the tag and the collection's name come from the rules file it shares with the Jellyfin version, rules 1.0.
- The choice itself is made in Starboard: **Settings**, **Reelix**, **Picture quality**, where **Audio description** can be set to **Prefer**, **Neutral** or **Never**. It uses Reelix's own Audio description format, which comes with Reelix; an older Reelix has none, and the plug-in says so.
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

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
