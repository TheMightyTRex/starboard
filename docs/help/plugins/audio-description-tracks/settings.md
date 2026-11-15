# Audio description tracks: Settings
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Audio description tracks' settings are on its own tab: go to **Settings**, then **Plug-ins**, then **Audio description tracks**. Starboard draws them and keeps them; secrets are never shown again once saved.

## Tracks

| Setting | What it does | Default |
|---|---|---|
| **Description tracks to add** | A page of its own that lists each file in the audio-description folder, what it was matched to and what happened, in **To check**, **Added: check each plays in step** and **Done**. Upload a track there, choose the right film or episode when it is not sure, and say whether an added track plays in step. | Not a setting |

## Settings

| Setting | What it does | Default |
|---|---|---|
| **Language of the description tracks** | The track is named after it, such as English (Audio Description). One of: English, French, German, Spanish, Italian, Dutch, Portuguese, Polish, Swedish, Danish, Norwegian, Finnish. | English |
| **How close the lengths must be** | A track is added only when it is this close to the film's length. A bigger difference usually means another cut of the film. A number from 1 to 30 seconds. | 5 seconds |

## Buttons

These are on Audio description tracks' tab.

- **Look in the folder now** looks in the audio-description folder straight away, in the background, and checks each new file. It says "Looking in the folder. The list updates in a minute". It also looks when **Description tracks to add** opens and there are new files, and once a night at 04:40, in quiet hours.

## Things to note

- A setting you change is used for the next track it checks. Tracks already added keep the name and language they were given.
- Name each file as the film and its year, such as `Dune (2021).mp3`, or a series with its episode, such as `Slow Horses S01E03.mp3`.
- Uploads on **Description tracks to add** can be up to 60 MB. Put a larger file in the audio-description folder in your media folder instead.
- MP3, M4A, M4B, AAC, MKA, Opus, Ogg, FLAC and WAV files work, and so does a zip of them, as AudioVault gives series.
- A track is added next to the film as a file such as `Dune (2021).Audio Description.eng.mka`, with the flag that marks it as audio description, and is never the sound track that plays first. The film's own file is not changed.
- Nothing is ever deleted. Files move to the **Confirmed**, **Taken off** and **Unzipped** folders inside the audio-description folder, and you delete them there when you like.
- Settings are kept when you update or deactivate it, and when you remove it they stay in its folder.

## Find out more

- [Install](../audio-description-tracks/install.md)
- [Dashboard card](../audio-description-tracks/dashboard-card.md)
- [Problems](../audio-description-tracks/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
