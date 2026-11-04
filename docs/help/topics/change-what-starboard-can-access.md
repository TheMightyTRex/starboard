[Help centre](../README.md) · Install and update · how-to

# Change what Starboard can access

Starboard lists everything it can reach on one page, says whether each is active, and tells you how to change it. Some
are switches in Starboard. Others you change by running the installer again, which keeps your settings and password.

## Before you begin

- You can sign in to Starboard. Read [Create your password and sign in](create-your-password.md).
- For changes made with the installer, a terminal open on the server. Read
  [The terminal: typing commands](../basics/the-terminal.md).

## See what Starboard can access now

1. Go to **Settings**, then **Updates**.
2. Find **What Starboard can access**.

Each row names one kind of access, says what it is for and what it costs your server, and shows whether it is active. Each
row also shows how to change it: a switch, a button such as **Change it**, or a command to run on the server.

## Change a switch in Starboard

These apply at once:

- **Your home network:** go to **Settings**, then **Security**, and use **Phones and other computers on your home
  network**. Read [Choose who can open Starboard](choose-who-can-open-starboard.md).
- **Your apps:** add, change or remove apps and their API keys in **Settings**, **Apps**, **Manage apps**. The row's
  **Manage apps** button goes there. Read
  [Change or remove an app](change-or-remove-an-app.md).
- **The dashboard-icons collection, for app icons** and **Posters on Coming up:** use the switch in the row on
  **About and updates**.
- **GitHub, for new Starboard versions:** use **Check GitHub for new releases**, under **Updates** on the same page.
- **Pausing and resuming downloads, Watching in the background and alerts, and the Jellyfin and Audiobookshelf
  extras:** select **Change it** in the row to go to the page with the switch.

## Change access with the installer

These need a change on the server: Docker for app updates, per-app processor and memory use, Jellyfin's Live TV folder,
your folders for free space, and Disk health reports.

1. On the server, go to the Starboard folder:

   ```bash
   cd ~/starboard
   ```

2. Run the installer again:

   ```bash
   ./install.sh
   ```

3. Answer the questions. Each one shows your last answer as the default, so press Enter to keep it. Read
   [Install Starboard with the installer](install-with-the-installer.md) for what each question means.
4. Wait for "Starboard is running". Starboard restarts with the new access. Your settings and password stay.

On **About and updates**, each row that needs the installer also shows the exact command, such as
`./install.sh --no-docker`, with a copy button. Running that command changes that one answer straight away and asks the
other questions as usual.

## If you used the ready-made image

The ready-made image has no installer. Instead, you change the Compose file.

1. On the server, go to the folder that holds `compose.image.yaml`:

   ```bash
   cd ~/starboard
   ```

2. Open the Compose file in the text editor nano:

   ```bash
   nano compose.image.yaml
   ```

3. To activate an extra, remove the `#` and the space after it at the start of its line. To deactivate it, put the
   `#` back. Each extra has a comment that explains it.
4. Save with **Ctrl** and **O**, then Enter. Leave nano with **Ctrl** and **X**.
5. Start Starboard again with the new file:

   ```bash
   docker compose -f compose.image.yaml up -d
   ```

## Things to note

- Every kind of access is optional. If you say no, only that part of Starboard is missing, and its page says what it
  needs.
- Docker access gives Starboard full control of Docker, which is the same as full control of the computer. Activate it
  only if you want Starboard to update your other apps.
- If you turn Disk health off, the job on the server stays installed. The installer prints the command that removes
  it: `sudo deploy/install-smart.sh --remove`.
- Folders and disks you set up by hand in `compose.override.yaml` are left alone by the installer.
- A backup job on the server is set up by hand. The README in Starboard's folder explains how.

## Find out more

- [Install Starboard with the installer](install-with-the-installer.md)
- [Choose who can open Starboard](choose-who-can-open-starboard.md)
- [Make Starboard use less of your server](make-starboard-lighter.md)
- [Check free space and what is using it](check-storage.md)
- [Check your disks' health](check-disk-health.md)
- [What Docker is](../basics/what-is-docker.md)
