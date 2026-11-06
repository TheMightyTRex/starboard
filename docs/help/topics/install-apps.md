[Help centre](../README.md) · Apps · how-to

# Install apps with Starboard

**Install apps** sets up a media server for you: it picks the apps for what you want, writes their set-up files
and starts them. At the end, the apps are running and Starboard shows how to connect them. It takes about
15 minutes, and the first downloads take longer.

## Before you begin

- Docker is installed on the server. Read [Install Docker](install-docker.md), and [What Docker is](../basics/what-is-docker.md) if it is new to you.
- You have a folder or drive with room for your media, such as `/srv/media`.
- Optional: an account with a VPN (virtual private network) provider, to keep your downloads private.
- Optional: Docker access lets Starboard start the apps itself. Without it, you run one command. Read
  [Change what Starboard can access](change-what-starboard-can-access.md).
- If you are not sure what each app does, read [The apps Starboard works with](../basics/the-apps.md).

## Steps

1. Go to **Settings**, then **Apps**, then **Manage apps**, and select **Install apps**.
2. On **Start here**, read how the apps work together. Tick **Advanced settings** only if you want to choose
   each app and folder yourself. Select **Begin**.
3. On **What to set up**, tick what you want your server to do, such as **Movies**, **TV**, **Watching** and
   **Downloads**. Starboard shows how many apps that is and how much memory they use. Select **Continue**.
4. On **Folders**, type your **Media folder**, such as `/srv/media`. If your other apps already use a media
   folder, Starboard offers it. Select **Continue**.
5. If you ticked **VPN**, the **VPN** step asks for your **VPN provider** and the details from its website.
   Select **Continue**.
6. If you ticked **SABnzbd**, the **Usenet** step lists some Usenet providers. They are affiliate links: if you
   sign up through one, the provider pays a small commission towards Starboard's development, and you pay the same
   price. Use Usenet only for files you have the right to download. Select **Continue**.
7. If Starboard found apps you already have, the **Moving over** step asks what to bring across later. Tick what
   you want, then select **Continue**.
8. On **Check**, read the summary. Select **Change** beside anything you want to change. When it is right,
   select **Write the files**.
9. On **Start**, type **Your Starboard password**, then select **Start the apps**. Starboard downloads and starts
   each app. This can take several minutes the first time.
10. When Starboard shows **The apps are running**, select **Add the ticked apps to Starboard**.
11. Follow **Connect your apps, in this order**. It gives each app's address, folders and settings to type.
12. Select **Go to Apps**.

### If Starboard has no Docker access

Docker access is off unless you said yes to it in the installer. Then the Run first window starts the apps for
Starboard: keep it open until Starboard shows **The apps are running**. The password and **Start the apps** work
as above.

If you closed that window, Starboard shows **Run one command** instead of a password. Select **Copy the command**,
then paste it into a terminal on the server. It makes the apps' folders, downloads the apps and starts them:

```bash
cd ~/starboard && ./install.sh --start-apps
```

If Starboard is in another folder, use that folder instead of `~/starboard`. If the terminal says your user is not
allowed to use Docker yet, sign out of the server and back in, then paste it again.

Then go back to Starboard and select **Find the new apps**. Continue from Step 9.

## Things to note

- Nothing is written until you select **Write the files**, and nothing starts until you select **Start the
  apps** or run the command.
- Starboard writes two files into `data/stack`: `compose.yaml` lists the apps, and `.env` holds your settings
  and VPN details. Older copies are kept.
- Starboard makes `movies`, `tv`, `books` and `downloads` folders, and others you need, inside your media folder.
- If a port is already in use, the app uses the next free one, and the **Check** step says so.
- Some apps, such as Unpackerr, need their own settings file first. Starboard writes them but does not start
  them yet.
- Several drives? On **Folders**, select **Join several drives into one** to make a pool. Starboard gives you
  commands to run on the server first. Nothing on the drives is erased.
- Starboard only starts apps from its own list, and only with folders it has checked.
- After **The apps are running**, Starboard waits for each app to answer, which takes a minute or two, then adds
  it to your apps. You can carry on with the set-up meanwhile.

## If it does not work

- **Nothing to download with:** tick **Downloads** too, or select **Continue** again to go on without it.
- **Enter the full path of a folder, starting with /:** type the whole path, such as `/srv/media`.
- **Something did not start:** read the log Starboard shows, change what it says, then run **Install apps**
  again.
- **Gluetun shows as unhealthy, and qBittorrent or SABnzbd do not open:** the VPN details are not right. Both
  download apps go through the VPN, so they wait for it. Check the provider, the private key and the address
  (ending in /32) in **Settings, Install apps**, then start the apps again.
- **An app is missing from your apps after a few minutes:** it had not answered yet. Go to **Settings, Manage
  apps**, select **Search for new apps**, then tick it.
- **Jellystat keeps restarting, and its log says "no pg_hba.conf entry":** its database did not finish setting
  up, which happened with Starboard 0.9.2 and earlier. Stop Jellystat and jellystat-db, move the `jellystat-db`
  folder from the apps' settings folder to a holding folder, then start the apps again. The database sets itself
  up afresh. Jellystat had no history yet, so nothing is lost.

## Find out more

- [Build a media server from nothing](../guides/build-a-media-server-from-nothing.md)
- [Add an app](add-an-app.md)
- [Copy settings from one app to another](copy-app-settings.md)
- [Update your apps](update-your-apps.md)
- [The terminal: typing commands](../basics/the-terminal.md)
