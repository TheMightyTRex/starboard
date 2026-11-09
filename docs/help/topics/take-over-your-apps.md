[Help centre](../README.md) · Apps · how-to

# Take over the apps you already run

If you set up your media server by hand, with your own Compose file, Starboard can take it over. It moves Radarr,
Sonarr, Lidarr, Readarr (or Bookshelf), Prowlarr and Seerr into Reelix. It then runs your other apps, such as
Jellyfin, Audiobookshelf and qBittorrent, from its own set-up, so **Settings**, **Apps**, **Your install** can change
them later. Each app keeps its settings, its ports and what it relies on, and you can go back.

## Before you begin

- Starboard has Docker access. Without it, Starboard cannot stop or start your apps.
- Your apps are running and were started from a Compose file (`docker compose up`). Apps that are stopped, or
  that were started another way, are left as they are.
- There is room on the disk for a copy of your apps' settings. Starboard checks before it copies, and stops if there
  is not.
- You know your Starboard password, and your qBittorrent password if you want Reelix to use qBittorrent.

## Steps

1. Go to **Settings**, then **Apps**, then **Your install**, then **Apps you already run**. Starboard lists the apps
   it found: the ones it takes over, the ones Reelix or NZBGet replaces, the ones it installs new and the ones it
   leaves as they are.
2. If the page shows **Step 1: install Reelix**, select **Install apps** and choose **Full install**. Your apps that
   already run are left as they are, so this adds only Reelix, NZBGet and Tdarr. Then come back to **Your install**.
   If **Apps you already run** then shows **Finish setting up Reelix**, select it: on **Settings**, **Reelix**, type
   **Your password** and select **Finish setting up Reelix**. Reelix's admin account gets the same password as Starboard.
3. Under **Step 1: move them into Reelix**, type **Your password**, and **qBittorrent's password** if you want
   Reelix to use qBittorrent. Select **Show what moves** to see what Reelix will add from each app.
4. Select **Move them into Reelix**. Films and series move in a minute or two. Reelix then finds their files, which
   takes about an hour for a big library. Leave **Hold the sites to search** selected, so only your old apps search
   until the next step.
5. Under **Step 2: Starboard runs your apps**, check the **Settings folder**. The copies of your apps' settings go
   there. It must not be inside the folder your apps use now.
6. Type **Your password**, then select **Take over my apps**. Your apps stop for a few minutes while their settings
   are copied, then start again from Starboard's set-up.
7. In Starboard, go to **Settings**, **Reelix**, **Sites to search**. For each site, select **More**, then **Change**,
   activate **Active** and select **Save**.

## What Starboard does

1. **Before anything stops,** it saves the way back. It tags each app's image as `starboard-rollback/<app>:<date>`,
   so the exact version stays on the server. It copies your Compose file and its `.env`, and Starboard's own set-up
   files, into `data/stack/takeover`.
2. It stops the apps it takes over and the ones being replaced.
3. It copies each app's settings into the settings folder. It never moves them, and never writes in your old
   folders. A folder that already has files is never copied over: Starboard stops and starts your apps again.
4. It removes the old containers. Their settings folders and images stay.
5. It starts the apps from its own set-up. **SABnzbd's** news servers move into NZBGet, and Reelix is given NZBGet
   and qBittorrent by their names on Starboard's set-up.

If anything goes wrong before the old containers are removed, Starboard starts your apps again as they were and
changes nothing else.

## What each app keeps

- **Its ports.** Jellyfin stays on 8096, Audiobookshelf on 13378, and every other app on the port it had. A port the
  app did not use before, such as qBittorrent's 6881 when your VPN forwards a port, stays closed.
- **The folders it uses as they are,** such as Jellyfin's `/media`, so your libraries and watch history stay.
- **Devices,** such as `/dev/dri` for hardware transcoding.
- **Its own settings** in the Compose file, such as Jellyfin's published address or Gluetun's port forwarding.
  Passwords and keys go in `data/stack/.env`, which only you can read.
- **Its version,** when you chose one, such as a pinned qBittorrent.
- **Whether it runs through the VPN.**

Starboard keeps all this in `data/stack/kept.json`, so later changes in **Your install** keep it too.

## Roll back

Until you choose **Keep it**, **Apps you already run** shows **Roll back**.

1. Type **Your password**, then select **Roll back**.
2. Starboard stops the apps it took over, puts its own set-up back as it was, and starts your old apps from your
   own Compose file, on the versions they ran.

Anything that changed since the takeover, such as new downloads in the new qBittorrent or new watch history in
Jellyfin, is not in your old apps: they carry on from the moment they stopped.

## Keep it

Once everything works, select **Keep it**. The way back is moved aside to `data/stack/takeover-kept-<date>`, and
nothing is deleted. Your old settings folders and the `starboard-rollback` images stay until you remove them.

## Things to note

- **Your own Compose file still lists the old apps.** Do not start it with `docker compose up` while Starboard runs
  them: the container names are taken, so it fails for those apps.
- **Apps the install does not have,** such as Kapowarr, and apps that are stopped, are left as they are in your own
  Compose file.
- **What does not move into Reelix:** custom formats, delay profiles, notifications, import lists and history. Set
  those up again in Reelix. [Move from Radarr, Sonarr and the others to Reelix](move-your-apps-to-reelix.md) lists
  them.

## If it does not work

- **"Choose a settings folder outside ...":** the settings folder is inside, or holds, a folder your apps use now.
  Choose another one, such as `/srv/media-stack/config`.
- **"Already has files, so nothing was copied over it":** the settings folder has files from before. Choose an empty
  one. Your apps run again as they were.
- **"Not enough space":** free some space on the disk with the settings folder, or choose a settings folder on
  another disk.
- **"Move ... into Reelix first":** do step 1 first, or select that you do not need them moved.
- **"qBittorrent did not accept that password":** type the password you use to sign in to qBittorrent, or leave it
  empty and add qBittorrent in Starboard: **Settings**, **Reelix**, **Download apps**.

## Find out more

- [Change your install](change-your-install.md)
- [Move from Radarr, Sonarr and the others to Reelix](move-your-apps-to-reelix.md)
- [Install apps with Starboard](install-apps.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
