# Audio description
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Audio description is a second sound track in which a narrator says what is happening in the picture, for blind and
partially sighted people. This plug-in finds the films and series in Jellyfin that have one, prefers releases with one
in Reelix, and helps each person who wants it keep the described track.

A Starboard plug-in by TheMightyTRexUK, MIT licence. Starboard's first set-up offers it, unticked.

## What it does

- **Your library:** once a night, in quiet hours, it reads the sound tracks of every film and episode in Jellyfin and
  lists those with a track named as audio description, such as "English (Audio Description)", "AD" or "Descriptive
  audio". Commentary tracks never count.
- **Reelix searches:** it adds an **Audio description** format to Reelix that matches release names such as
  `WiTH.AD`, `ENG.AD`, `BSL.and.AD`, `Audio.Description` and `DVS`, and prefers it in every video quality level.
  Reelix still takes a release without it when there is no other. Deactivate **Prefer releases with audio
  description** to put the scores back to neutral.
- **People:** for each person you activate, Jellyfin remembers the sound track they choose, so choosing the
  described track once is enough for each film and series.
- **Elsewhere:** a list of places with audio description in their own apps, such as BBC iPlayer and ITVX, each a link
  that opens in a new tab. It only links to them.

## Sources

Each source is its own part, activated or deactivated under **Sources**, and each only links out. Nothing is fetched
from any of them.

- **AudioVault search links** (deactivated until you activate it): for each film and series in Jellyfin without audio
  description, a link to AudioVault's own search for it. AudioVault is a free community library of description tracks
  for blind and partially sighted people. It states no licence and no terms for automated use, has no API, and limits
  each account to 25 downloads a day, so Starboard never reads its pages or downloads from it: you open the link, sign
  in there and keep to its rules. To add a track you downloaded, use the
  [Audio description tracks](https://github.com/TheMightyTRex/starboard-plugins/blob/main/audio-description-tracks) plug-in, which checks it is the same length as your film.
- **YouDescribe search links** (activated): for each film and series, a link to YouDescribe's own search. YouDescribe
  is a free website where volunteers describe YouTube videos, such as trailers and clips; they play there, in your
  browser. Its programming interface serves its own website and is not offered to other apps, and its code is
  published without a licence, so Starboard only links to the search and never searches it for you.
- **MovieReading and Earcatch** (activated): a short guide to these free phone apps, which play a description
  through headphones in step with a film by listening to its sound, so they work alongside Jellyfin on your
  television; and links to them in the App Store, on Google Play and on their websites. Neither publishes a list of
  titles that other apps may read (MovieReading's website names only the films it has now; Earcatch's terms forbid
  collecting its content with automated tools for AI), so Starboard cannot say which of your films they have. RNIB
  says neither is offered in the UK yet; MovieReading is mostly Italian, Earcatch mostly Dutch and Flemish.

## What it may do

- It uses Jellyfin's key, which Starboard keeps: to read sound tracks and to change one setting (remember my audio
  track) for the people you activate.
- It uses Reelix's key, which Starboard keeps: to add the Audio description format and score it.
- It reaches your home network, where Jellyfin and Reelix are.
- It runs one small container (64 MB of memory at most) that rests when it is not needed. Starboard wakes it for the
  nightly check, when Starboard starts, and when you open its pages or select its buttons.

## What it never does

- Download from, or read pages of, any website, AudioVault included.
- Record or copy from BBC iPlayer, ITVX, Channel 4, My5 or any other app.
- Change a media file.

## What Jellyfin cannot do yet

Jellyfin does not read the "visual impaired" flag that marks a described track inside a file, and has no setting that
picks a described track by itself. So the plug-in finds tracks by their names, and each person chooses the described
track once per film or series. Both are listed in Starboard's accessibility research (DASH-400).

## On the dashboard

- **Audio description**: how many films and series have a described sound track.
- **Recently found with audio description**: the newest ten.

## Settings

- **Prefer releases with audio description**: Adds an Audio description format to Reelix and prefers it in every
  quality level. Reelix still takes a release without it when there is no other.
- **People who want audio description**: activate each person.
- **Titles with audio description**: the list, by films and series.
- **Audio description elsewhere**: places with audio description in their own apps.
- **Sources**: AudioVault search links, YouDescribe search links, MovieReading and Earcatch.
- **Search AudioVault**: the links, by films and series, opening by first letter when the list is long.
- **Search YouDescribe**: the links for every film and series, the same way.
- **MovieReading and Earcatch**: the guide and the links.

## Add it

Needs Starboard with plug-in API 1.14 or later. An older Starboard keeps version 1.1.0. In Starboard, go to **Settings**, then **Plug-ins**, then **Catalogue**, and find it there. Or, under **Add one from elsewhere**, give this address:

`https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/audio-description/starboard-plugin.json`

Or run `python3 install.py` in this folder.

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
