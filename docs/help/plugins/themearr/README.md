# Themearr
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Themearr puts a theme tune, theme.mp3, in the folder of each film Reelix has, and Jellyfin plays it on the film's page. It needs a RapidAPI key to fetch the tunes.

An app plug-in for Starboard (plug-in API 1.14 or later): Themearr runs outside the main install, in Starboard's locked-down
containers, with its own page on your home network. Starboard chooses the port (8080 when it is free) and shows the address
on the plug-in's page with **Open**.

## Who it is for

People who like a film's music to play while they browse it in Jellyfin. Themearr reads your films from Reelix, finds each film's theme on YouTube and saves it as `theme.mp3` beside the film, where Jellyfin, Plex, Emby and Kodi find it.

## Set it up

1. Activate it. Within 2 minutes Starboard gives Themearr Reelix's address and key, as its Radarr, and your films folder: nothing to enter.
2. Make a RapidAPI account and subscribe to the youtube-mp36 service (its free plan has a monthly limit). Enter its key and your RapidAPI user name in the plug-in's settings in Starboard. Themearr fetches tunes through it.
3. To open Themearr's own page, copy the access token from **Sign in to Themearr** on the plug-in's tab, choose **Open Themearr** and paste it there.

## What it may do

- It can change: Its own folder in Starboard's data (data/plugins/themearr), and the `movies` folder in your media folder, as the media folder's owner: it adds `theme.mp3` to each film's folder and changes nothing else there.
- It can use: Reelix's API key, kept by Starboard, to read the films Reelix has.
- It can reach: Other computers on your home network, and the internet (YouTube and RapidAPI).
- It can reach: Its own web page is opened on your home network: anyone on your home network can open it, at this computer's address and a port Starboard chooses. It asks for the access token.

It runs read only, as a user that is not root, with no extra rights, like every plug-in. A small helper beside it, run in the
official Python image, gives Themearr its settings and answers Starboard's card; it reaches only Starboard and Themearr. Its images, pinned by digest:

- `main`: `docker.io/library/python@sha256:c5ba3deef00c7758561a0f03c26f44f10589263d40e732b8748e0d1f38f6dd89` (Python 3.12 on Alpine)
- `app`: `ghcr.io/themearr/themearr@sha256:0a5c617c35f93342f8fc44eb2ce874005f2142315d2c7b4410c709790143448a` (Themearr 1.52.1)

## At rest

What it uses when nobody is using it, measured with `tools/app_check.py` (median of 36 readings over 3 minutes, after
2 minutes to settle). A real library uses more.

| Reading | Memory | Processor (one core) |
|---|---|---|
| As Starboard runs it (hardened, no films yet), 17 November 2026 | 47.6 MiB (helper 14.0, Themearr 33.6) | 0.6% |
| With a test library read from Reelix, 17 November 2026 | about 71 MiB (helper 14, Themearr 57) | under 1% |

Themearr's image is about 1 GB to download. The tunes are full length unless you choose trimming in Themearr: about 3.7 GB for every 1,000 films, by Themearr's own figures.

## Removing it

**Settings**, **Plug-ins**, Themearr, **Remove**. Its containers stop and go and its key stops working. You choose
where its folder goes, with everything it kept (settings and its list of films):
kept in `data/plugins/.removed`, or moved to the holding folder in **System**, **Clean up**.
From there you can put it back or delete it permanently. Starboard never deletes it. The `theme.mp3` files stay in your film folders.

## Licence

This plug-in is MIT, by TheMightyTRexUK. Themearr itself is under the MIT licence, made by others: https://github.com/Themearr/themearr

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
