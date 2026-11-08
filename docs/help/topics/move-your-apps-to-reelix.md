[Help centre](../README.md) · Apps · how-to

# Move from Radarr, Sonarr and the others to Reelix

Reelix can read your Radarr, Sonarr, Lidarr, Readarr (or Bookshelf), Prowlarr and Jellyseerr (or Seerr) and set
itself up from them: your films and series, your folders, quality profiles, download apps, indexers, users and
requests. Your media files stay where they are, and your old apps are not changed. This page says what moves, what
does not, and what to do afterwards.

## Before you begin

- Reelix is installed and set up. Read [Install apps with Starboard](install-apps.md).
- Your old apps are running, so Reelix can read them.
- Reelix sees your media folder at the same path as your old apps do, such as `/data/media/movies`. If the paths
  differ, add a **Path rewrite** when you connect each app.
- A TMDB API key is best but not needed. In Reelix, **Settings**, **Metadata**, add one first if you have it (free
  from themoviedb.org). Without it, the Reelix that Starboard installs uses open data: films from Wikidata and
  series from TVmaze. Almost everything comes across, but films have no posters, and a few titles those sites do
  not list are left out.

## Steps

Starboard can do these steps for you, with the keys filled in: read
[Take over the apps you already run](take-over-your-apps.md). To do them in Reelix yourself:

1. In Reelix, go to **System**, then **Migrate**.
2. Move **Prowlarr** first, so your indexers come from one place. The indexers Prowlarr gave your other apps are
   then left out of those, as they should be.
3. Then move **Radarr**, **Sonarr**, **Lidarr** and **Readarr**, one at a time. For each one, type its address and
   API key (Settings, General in that app), select **Test connection**, then **Preview migration**. Read the list,
   then select **Start migration**.
4. Move **Jellyseerr** or **Seerr** last, for your users and requests.
5. Leave **Search for missing items after adding them** off for the first move. Reelix then finds your files
   without downloading anything.

Reelix then looks through your folders and links each file to its film or episode. For a large library this takes
a while: on a pool of hard drives, about 20 seconds for each series, so over an hour for 200 series. Your library
works in Reelix while it runs.

## What moves

- Films and series, with which ones are monitored, their folders and their quality profile.
- Your files: Reelix finds them in the folders and reads their quality, size and media details.
- Library folders, tags and remote path mappings.
- Quality profiles. A profile with the same name as one of Reelix's own, such as **HD-1080p**, is not copied:
  Reelix keeps its own, and the preview says so. Check them in **Settings**, **Profiles** after the move. A name
  used by another kind of profile (Lidarr's **Any** after Radarr's) comes across with the app's name added, such as
  **Any (Lidarr)**.
- Indexers from Prowlarr, and download apps (qBittorrent, SABnzbd and others), with the details each app shows.
- Users and requests from Jellyseerr or Seerr. Jellyfin, Emby and Plex users keep signing in with their media
  server account.

## What does not move

- Custom formats, delay profiles, release profiles, notifications (such as the Jellyfin library update), import
  lists and history. Set them up again in Reelix.
- Prowlarr's apps, sync profiles and its FlareSolverr proxy.
- Indexers that Reelix has no definition for (such as Knaben). Update the definitions in **Settings**,
  **Indexers**, then move Prowlarr again.
- Disc images, such as `.iso` Blu-ray copies. Reelix does not see them as films, so those films show as missing.
- Without a TMDB key: films that Wikidata does not list, and series that TVmaze does not list or that have no TMDB
  link on Wikidata. In a test library, 6 of 257 films and 5 of 227 series. Add a TMDB key and move the app again
  to bring them across.
- Some specials and pilots (season 0, or names such as `S07E00`). Link them by hand in Reelix after the move.
- Storyarr. Reelix cannot read Storyarr's books, reading lists, wanted releases or radio. Add your books folders in
  Reelix instead: read "Books and audiobooks" below.

## What to type in yourself afterwards

Your old apps hide passwords and API keys, so Reelix cannot copy them:

- **Usenet indexers** from Prowlarr (such as NZBgeek or NZBFinder): the preview says **Some passwords or API keys
  are hidden**. Type each indexer's API key below it, then select **Preview migration** again.
- **SABnzbd** in an app that hides its API key: type the key from SABnzbd's **Config**, **General**. To use NZBGet
  instead, change the Usenet app in Starboard, **Settings**, **Your install**: your Usenet servers move across.
- **qBittorrent's password.** If your old apps reached qBittorrent without a password (qBittorrent lets chosen
  addresses in without one), Reelix cannot, as it has its own address. Type qBittorrent's user name and password in
  Reelix: **Settings**, **Download Clients**, **qBittorrent**.
- **qBittorrent through a VPN:** if your old apps reached qBittorrent by a fixed number address for the VPN
  container, change the host to the VPN container's name, such as `gluetun`.
- **Local Jellyseerr or Seerr users** need a new password in Reelix: **Settings**, **Users**.

## Books and audiobooks

Reelix moves authors from Readarr or Bookshelf. From any other app, or for books it does not know, add the folder
in Reelix: **Books**, **Import Library**, choose the books or audiobooks folder, then **Import books**. Reelix
suggests an author for each folder from Open Library.

- A folder named after two authors, such as `Larry Niven, Jerry Pournelle`, gets no suggestion. Search for one of
  the authors by hand.
- A folder for a series or a group, such as a podcast name, gets no suggestion either.
- Pick an audiobook quality profile when you import an audiobooks folder.

## If it does not work

- **"this film is not on Wikidata"** or **"this series is not on TVmaze"**: open data does not list it. Add a TMDB
  API key in **Settings**, **Metadata**, then move the app again.
- **A quality profile named "Any" already exists**, or **"invalid type: map, expected a string"** when adding an
  author: you run an older Reelix. Update Reelix (Starboard, System, Apps, Updates), then move the app again.
- **Reelix shows as unhealthy after the move:** a download app it cannot reach, usually qBittorrent. Read "What to
  type in yourself afterwards".
- **Connection failed** for qBittorrent: read "What to type in yourself afterwards".
- **A move says it is already running:** wait for the one before it to finish. Moving an app again is safe; what
  is in Reelix already is kept.

## Find out more

- [Install apps with Starboard](install-apps.md)
- [Switch between the two versions of Reelix](switch-reelix-version.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
