[Help centre](../README.md) · Apps · how-to

# Change your install

**Settings**, **Apps**, **Your install** shows what Starboard installed on your server and changes it. You can move
to a bigger or smaller install, change the app that downloads from Usenet, or switch between the two versions of
Reelix. Every change works both ways.

## The three installs

| | Basics | Full install | Everything |
|---|---|---|---|
| Reelix | Reelix (Lite) | Reelix with YouTube and Spotify downloads | Reelix with YouTube and Spotify downloads |
| Watching and listening | Jellyfin, Audiobookshelf | Jellyfin, Audiobookshelf, Jellystat | All of those, plus Wizarr and Dispatcharr |
| Subtitles | Bazarr | Bazarr | Bazarr |
| Downloads | qBittorrent and NZBGet through a VPN (Gluetun) | The same, plus FlareSolverr; SABnzbd in place of NZBGet if you choose it | The same, plus Soulseek (slskd) |
| Extras | | Disk health, Tdarr (smaller files) | Disk health, Dozzle, Tdarr, Kapowarr |
| Memory when idle | about 0.6 to 1.6 GB | about 1.1 to 2.6 GB | about 1.9 to 3.4 GB |

Everything also has the No-IP updater. Apps that need another app bring it with them. Read
[Basics, Full install and Everything](install-types.md#the-apps-in-each) for every app in each.

## Before you begin

- Install apps set up your apps. On a server set up by hand, Starboard can take your apps over first: read
  [Take over the apps you already run](take-over-your-apps.md).
- You know your Starboard password.
- For an install with a VPN, the VPN details you gave Install apps are used again.

## Steps

1. Go to **Settings**, then **Apps**, then **Your install**. **Your install now** shows the install, which Reelix
   runs, the Usenet app, the apps and the memory they use.
2. Under **Change your install**, choose **Basics**, **Full install** or **Everything**. Each one says what it adds or
   takes away.
3. Under **Usenet app**, choose **NZBGet** or **SABnzbd**, if you want to change it.
4. Under **Reelix**, choose the version, if you want to change it.
5. Under **Make the change**, read the summary, enter **Your password**, then select **Change my install**.
6. Wait until Starboard shows **Your install is changed**. It then updates the dashboard and Reelix, and the page
   shows what was done.

To add one app without changing the install, go to **System**, then **Apps**, then **Install apps**, and select
**Add** beside it.

### If Starboard has no Docker access

Starboard writes the new set-up and shows **One step on the server**. Select **Copy the command**, then paste it into a
terminal on the server:

```bash
cd ~/starboard && ./install.sh --start-apps
```

Once the apps have started, Starboard finishes off by itself within a minute. Open **Your install** again to read what
was done. If the Run first window is still open, Starboard asks it to start the apps instead.

## How changing works

1. Starboard keeps a copy of the set-up file in `data/stack`, named `compose.yaml.before-` and the date.
2. It writes the new set-up file with the same folders, user, time zone, VPN details and passwords, so databases and
   connections keep working.
3. It downloads the apps being added and starts them. Apps taken away stop and are removed. Their settings folders
   stay, so adding one back later carries on where it left off.
4. **From SABnzbd to NZBGet**, your Usenet servers move across: address, port, user name, password, connections, SSL,
   retention, priority and whether each is on. The queue and history do not. **From NZBGet to SABnzbd**, add your
   servers in **Settings**, **Downloads**: read [Choose a Usenet provider and add it](choose-a-usenet-provider.md).
5. Reelix is given the new download app in place of the old one. New apps are added to your dashboard as they answer;
   apps taken away leave it.

## Things to note

- **NZBGet or SABnzbd:** both download from Usenet. NZBGet uses far less memory and processor. SABnzbd has more
  extras. Reelix works with either. Basics always uses NZBGet.
- **SABnzbd's port** is 8085, not its usual 8080, because through the VPN it shares an address with qBittorrent. If
  you already had SABnzbd settings, Starboard leaves them as they are: check the port in SABnzbd, **Config**,
  **General**.
- **NZBGet's sign-in:** Starboard makes up NZBGet's password and keeps it in `data/stack/.env` (`NZBGET_USER` and
  `NZBGET_PASS`).
- **Going back to Reelix Lite** works when Lite is on the same release as the full version or a newer one. Starboard
  says when it has to wait. Read [Switch between the two versions of Reelix](switch-reelix-version.md).
- **If the full Reelix cannot be downloaded,** Full install and Everything use Reelix Lite, and say so.
- Apps you added yourself outside Install apps are not touched.

## If it does not work

- **"Install apps did not set up the apps here":** run Install apps first, or read
  [Take over the apps you already run](take-over-your-apps.md).
- **"Choose your VPN provider":** the new install has a VPN, but none was set up before. Run Install apps and fill in
  the VPN step.
- **"That is what runs already":** choose a different install, Usenet app or Reelix version.
- **The apps did not all start:** read the details Starboard shows. The old set-up file is kept in `data/stack`.

## Find out more

- [Basics, Full install and Everything: what each one has](install-types.md)
- [Install apps with Starboard](install-apps.md)
- [Switch between the two versions of Reelix](switch-reelix-version.md)
- [Take over the apps you already run](take-over-your-apps.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
