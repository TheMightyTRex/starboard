[Help centre](../README.md) · Install and update · how-to

# Update Starboard

Update Starboard by running one command on the server. If you used the installer, `./update.sh` backs up your
settings, installs the newest release and goes back to the version you had if the new one does not start.

## Before you begin

- A terminal open on the server. Read [The terminal: typing commands](../basics/the-terminal.md).
- Know which way you installed Starboard: with the installer, or from the ready-made image. If your Starboard folder
  has a file called `update.sh`, you used the installer.

## Find out whether an update is out

- The footer of every page shows Starboard's version. When a newer one is out, **Upgrade available** and the new
  version number appear beside it. Select it to go to **Settings**, **Updates**.
- On **About and updates**, a notice says "Version 0.8.0 is out", for example, with a **Release notes** button that
  says what changed.

For this to work, **Check GitHub for new releases** must be active. It is on **About and updates**, under **Updates**.

## Steps if you used the installer

1. Go to the Starboard folder:

   ```bash
   cd ~/starboard
   ```

2. Run the updater:

   ```bash
   ./update.sh
   ```

   It shows "You have:" and "Available:" with two version numbers, then lists what changed. It backs up your
   settings, installs the new version and restarts Starboard.

3. Wait for the prompt to come back. The last line says "Updated to" and the new version.
4. Reload Starboard in your browser.

If you only want to know whether an update is out, without installing it, run `./update.sh --check`.

## Steps if you used the ready-made image

1. Go to the folder that holds `compose.image.yaml`:

   ```bash
   cd ~/starboard
   ```

2. Make a copy of your settings first, in case you need to go back. This saves the `data` folder in one file:

   ```bash
   tar -czf starboard-data-before-update.tar.gz data
   ```

3. Download the newest image:

   ```bash
   docker compose -f compose.image.yaml pull
   ```

4. Start Starboard again with the new image:

   ```bash
   docker compose -f compose.image.yaml up -d
   ```

5. Reload Starboard in your browser.

## After the update

- Select the version number in the footer of any page to read the release notes.
- If the new version brings settings worth choosing, a notice offers to open the upgrade guide. It asks only the new
  questions. You can leave it for later.

## Things to note

- The updater keeps a backup of your `data` folder in the `backups` folder each time it runs, named with the date. It
  never sends anything anywhere.
- If the new version does not start, the updater goes back to the version you had and puts your settings back. The
  last lines say "Back on" and the version.
- If the `image:` line in your Compose file ends in a version, such as `:0.7.2` instead of `:latest`, pulling does not
  change it. Change the version in the file first. Read [Go back to an earlier version](go-back-to-an-earlier-version.md)
  for how to edit it.
- Starboard only updates itself. To update your other apps, read [Update your apps](update-your-apps.md).

## If it does not work

- **"Already up to date":** you have the newest release. Nothing changed.
- **"Stopped: files in this folder have been changed":** a file that came with Starboard was edited. Move any changes
  you want to keep somewhere else, then put the files back as they were with this command, and run `./update.sh` again:

  ```bash
  git checkout -- .
  ```

  Your settings are safe: they are in `data` and `.env`, which this does not touch.
- **"Stopped: this folder is not a git clone of Starboard":** you are in the wrong folder, or you used the ready-made
  image. Run `cd ~/starboard`, or follow the steps for the ready-made image.
- **"Starboard is still not starting":** read what went wrong with `docker compose logs starboard`, then read
  [Starboard does not open](starboard-does-not-open.md).

## Find out more

- [Go back to an earlier version](go-back-to-an-earlier-version.md)
- [Back up and restore Starboard's settings](back-up-settings.md)
- [Update your apps](update-your-apps.md)
- [Read the log and report a problem](read-the-log.md)
