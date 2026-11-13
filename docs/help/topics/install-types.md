[Help centre](../README.md) · Apps · reference

# Basics, Full install and Everything: what each one has

**Install apps** offers three installs. This page lists what each one does, its apps, and the computer and accounts
it needs. You can change from one to another later, either way: read [Change your install](change-your-install.md).

## At a glance

| | Basics | Full install | Everything |
|---|---|---|---|
| Who it is for | Most homes: a complete media server that stays light | A household that wants watch statistics, logs and smaller files | Someone who wants every app Starboard offers |
| Apps | 7 | 11 | 16 |
| Memory when idle | about 0.6 to 1.6 GB | about 1.1 to 2.6 GB | about 1.9 to 3.4 GB |
| Memory at load | about 1.2 to 2.3 GB | about 2.6 to 4.1 GB | about 3.7 to 4.9 GB |
| Processor when idle | under 5% of one core | under 10% of one core | under 10% of one core |
| Processor at load | 1 to 2 cores in bursts | 2 cores, or every core while Tdarr converts | 2 cores, or every core while Tdarr converts |
| Disk for the apps | about 3.5 GB | about 9 GB | about 16 GB |
| Smallest computer | 2 cores, 2 GB | 4 cores, 6 GB | 4 cores, 8 GB |
| Recommended computer | 4 cores, 4 GB, or a Raspberry Pi 5 with 4 GB | 4 cores, 8 GB, ideally with an Intel processor | 4 or more cores, 8 GB or more |

The figures include Starboard (about 25 MB) and Docker (about 80 MB). They are for the computer described in
[Memory and processor](#memory-and-processor). The lower figure is for a small library and the higher one for a
large library, mostly because of Jellyfin. Converting video needs much more processor.

## Memory and processor

**The computer these figures are for:** an AMD Ryzen 5 1600 (6 cores, 12 threads, 3.2 GHz, from 2017) with 16 GB of
memory and an NVIDIA GeForce GT 710, which cannot convert video, so the processor does all video work. "Core" means
one of its 12 threads. A Raspberry Pi 5 core does about half as much, so double the processor figures there. A
recent Intel processor does about the same or more, and converts video with its own hardware.

**Idle**, or at rest, means nothing is downloading, scanning or playing. **At load**, or while working, means
downloading at about 100 Mbit/s through the VPN, Reelix scanning a new folder and one film playing directly (not
converted), all at once. Figures marked **measured** were read on that computer; the rest are typical for each app.

**Library size matters.** Reelix and Jellyfin keep more in memory the more films, series and music you have. The
measurements of 13 November 2026 were taken on a server with a large library while Reelix was working.

### Each install

Converting video comes on top of the figures in [At a glance](#at-a-glance):

| | Basics | Full install | Everything |
|---|---|---|---|
| Converting one 1080p film for a phone (Jellyfin) | 3 to 4 cores, +1 GB | 3 to 4 cores, +1 GB | 3 to 4 cores, +1 GB |
| Tdarr converting the library | | every core it is given, for hours, +1 to 2 GB | every core it is given, for hours, +1 to 2 GB |

### Each app

| App | Memory idle | Memory at load | Processor idle | Processor at load |
|---|---|---|---|---|
| Starboard | 20 to 25 MB | 37 MB (measured, every page open) | about 0 | a few seconds for every page |
| Docker | about 80 MB | about 100 MB | about 0 | low |
| Reelix Lite | At rest: 37 MB empty, 80 MB with 257 films and 227 series (measured) | While working: 120 to 200 MB scanning a small library (measured); with a large library, as the full Reelix | under 1% at rest (measured) | 1 core in bursts while scanning |
| Reelix full | At rest: 10 to 30 MB more than Lite | While working with a large library: 350 to 380 MB (measured 13 November 2026); 100 to 300 MB more during a YouTube or Spotify download | 3 to 18% while working (measured) | +1 core while converting a download |
| Jellyfin | Depends on library size: 150 to 300 MB with a small library; 590 to 920 MB with a large one (measured 4 and 13 November 2026), much of it cache | 300 to 500 MB more playing directly; +1 GB converting | 1 to 3% (measured) | almost none playing directly; 3 to 4 cores converting 1080p |
| Audiobookshelf | 80 to 150 MB | 150 to 250 MB scanning | under 1% | 1 core briefly while scanning |
| Bazarr | 120 to 200 MB | 200 to 300 MB | under 1% | short bursts while searching |
| qBittorrent | 15 MB (measured) | 50 to 150 MB with active torrents | under 1% (measured) | 5 to 20% of a core at 100 Mbit/s |
| NZBGet | 20 to 50 MB | 50 to 150 MB | under 1% | 1 to 2 cores briefly, repairing and unpacking |
| SABnzbd (if chosen) | 96 MB (measured) | 150 to 300 MB | under 1% (measured) | 2 to 3 cores briefly, repairing and unpacking |
| Gluetun (VPN) | 37 MB (measured) | 40 to 60 MB | under 1% (measured) | up to 10% of a core at 100 Mbit/s |
| FlareSolverr | 100 to 150 MB | +300 to 600 MB for a few seconds | under 1% | 1 core for a few seconds per site check |
| Jellystat and its database | 150 to 250 MB | 250 to 350 MB | under 1% | low |
| Wizarr | 80 to 120 MB | 120 to 150 MB | under 1% | low |
| Dispatcharr | 250 to 500 MB | 400 to 700 MB refreshing guides | 1 to 2% | 1 core refreshing guides; more if it converts streams |
| Dozzle | 15 to 30 MB | 30 to 50 MB with logs open | under 1% | low |
| Tdarr | 300 to 500 MB | +1 to 2 GB converting | under 1% | every core it is given |
| Disk health | none | none | none | a few seconds every 30 minutes |
| Kapowarr | 80 to 120 MB | 120 to 200 MB | under 1% | low |

## What you can do with each

| Feature | Basics | Full install | Everything |
|---|---|---|---|
| Find, download and sort films and series | ✓ | ✓ | ✓ |
| Books, audiobooks and music, sorted into your library | ✓ | ✓ | ✓ |
| Radio shows and podcasts | ✓ | ✓ | ✓ |
| Requests from the people you share with | ✓ | ✓ | ✓ |
| Download from YouTube and Spotify | | ✓ | ✓ |
| Download torrents through a VPN | ✓ | ✓ | ✓ |
| Download from Usenet | ✓ NZBGet | ✓ NZBGet, or SABnzbd if you choose | ✓ NZBGet, or SABnzbd if you choose |
| Get past browser checks on some search sites | | ✓ | ✓ |
| Watch films and series on TVs, phones and browsers | ✓ | ✓ | ✓ |
| Listen to audiobooks and podcasts, keeping your place | ✓ | ✓ | ✓ |
| Subtitles found for you | ✓ | ✓ | ✓ |
| Free live TV channels and guides (the Live TV plug-in) | ✓ | ✓ | ✓ |
| Who watched what, and when | | ✓ | ✓ |
| Convert the library to smaller files | | ✓ | ✓ |
| Read every app's log in the browser | | ✓ | ✓ |
| A warning before a disk fails (disk health) | | ✓ | ✓ |
| Invite friends and family with a link (Wizarr) | | | ✓ |
| Paid IPTV or full control of channels (Dispatcharr) | | | ✓ |
| Music and books from the Soulseek network | | | ✓ |
| Keep a No-IP address pointing at your server | | | ✓ |
| Comics and graphic novels | | | ✓ |
| Starboard's dashboard, alerts, download hours, backups and updates | ✓ | ✓ | ✓ |

Live TV is a plug-in that comes with Starboard, not an app in the install: read
[Set up free Live TV in Jellyfin](set-up-live-tv.md#add-live-tv).

## The apps in each

| App | What it does | Basics | Full install | Everything | Needs |
|---|---|---|---|---|---|
| Starboard | The dashboard that installs, watches and updates the rest | ✓ | ✓ | ✓ | Docker |
| Reelix | Finds, chooses and sorts films, series, books, audiobooks, music and radio; takes requests | ✓ Lite | ✓ Full | ✓ Full | A download app |
| Jellyfin | Plays your films, series and music | ✓ | ✓ | ✓ | |
| Audiobookshelf | Plays audiobooks and podcasts | ✓ | ✓ | ✓ | |
| Bazarr | Finds subtitles | ✓ | ✓ | ✓ | Reelix |
| qBittorrent | Downloads torrents | ✓ | ✓ | ✓ | |
| NZBGet | Downloads from Usenet; light on memory | ✓ | ✓ | ✓ | A Usenet provider |
| SABnzbd | Downloads from Usenet, in place of NZBGet | | if chosen | if chosen | A Usenet provider |
| Gluetun | Sends downloads through your VPN | ✓ | ✓ | ✓ | A VPN account; a download app |
| FlareSolverr | Gets past browser checks on some search sites | | ✓ | ✓ | Reelix |
| Jellystat | Watch statistics for Jellyfin, with its own database | | ✓ | ✓ | Jellyfin |
| Wizarr | Invites people to Jellyfin | | | ✓ | Jellyfin |
| Dispatcharr | Paid IPTV channels in Jellyfin (Starboard's own Live TV plug-in covers free channels) | | | ✓ | Jellyfin |
| Dozzle | Reads every app's log in the browser, with no sign-in (System, Logs shows app logs too) | | | ✓ | |
| Tdarr | Converts the library to smaller files | | ✓ | ✓ | Processor time |
| Disk health | Checks each disk every 30 minutes (on the server, not an app) | | ✓ | ✓ | The server's password once |
| Wizarr | Invites people to Jellyfin | | | ✓ | Jellyfin |
| Dispatcharr | Paid IPTV, backup streams or full control of channels in Jellyfin | | | ✓ | Jellyfin |
| Soulseek (slskd) | Music and books from the Soulseek network | | | ✓ | A Soulseek name and password |
| No-IP updater | Keeps your No-IP address pointing at the server | | | ✓ | A No-IP account |
| Kapowarr | Comics and graphic novels | | | ✓ | A download app |

An app always brings what it needs: choosing Jellystat also installs Jellyfin, and Reelix installs qBittorrent if
there is no download app.

**Storyarr** was retired on 11 November 2026 and is no longer offered. Reelix does its work: books, audiobooks and
radio. An install that has Storyarr keeps it until you take it away in [Change your install](change-your-install.md);
read [Move your apps to Reelix](move-your-apps-to-reelix.md) for what to do with its books.

## What you need for each

| You need | Basics | Full install | Everything |
|---|---|---|---|
| A computer running Linux Mint 22.3, Debian 13, Ubuntu Server 26.04 or Raspberry Pi OS (read [What you need](what-you-need.md)) | ✓ | ✓ | ✓ |
| A folder or drive for your media | ✓ | ✓ | ✓ |
| An account with a VPN provider, for the VPN | ✓ | ✓ | ✓ |
| An account with a Usenet provider, to download from Usenet | Only for Usenet | Only for Usenet | Only for Usenet |
| A TMDB API key, free from themoviedb.org | Recommended | Recommended | Recommended |
| A Spotify account, for Spotify downloads | | Only for Spotify | Only for Spotify |
| Disk for the apps, before any media | about 3.5 GB | about 9 GB | about 16 GB |

- **The VPN** is in every install, because it keeps your address private when downloading torrents. Your provider's
  website gives the details the set-up asks for.
- **Usenet** needs a paid provider. Without one, NZBGet is installed but has nothing to download from; torrents still
  work. Read [Choose a Usenet provider and add it](choose-a-usenet-provider.md).
- **TMDB:** without a key, Reelix uses open data for films and series (Wikidata and TVmaze), with no film posters. A
  free key gives the full details and pictures.
- **Disk** is the apps as downloaded, measured on a server (NZBGet and Tdarr estimated). The biggest are Dispatcharr
  (about 4.3 GB), Tdarr (about 2 GB), Jellyfin (1.3 GB) and Jellystat with its database (1.6 GB). The full Reelix
  takes about 0.7 GB more than Lite (1.1 GB against 0.4 GB).

## Things to note

- **Changing later:** **Settings**, **Apps**, **Your install** moves between the three either way. Apps taken away
  keep their settings folders, so adding one back carries on where it left off.
- **Add-ons:** any app can be added to any install. Go to **System**, then **Apps**, then **Install apps**, and
  select **Add** beside it under 'You can add'.
- **Choose myself:** Install apps also lets you tick each group, and with **Advanced settings** each app.
- **Apps already running** on the server are left out of a new install.
- **Converting video** (Jellyfin for phones and browsers, or Tdarr) is the heaviest work on any install. With an
  Intel processor from 2018 or later, Jellyfin uses its video hardware.

## Find out more

- [Install apps with Starboard](install-apps.md)
- [Change your install](change-your-install.md)
- [Choose a Usenet provider and add it](choose-a-usenet-provider.md)
- [Set up free Live TV in Jellyfin](set-up-live-tv.md)
- [What you need](what-you-need.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
