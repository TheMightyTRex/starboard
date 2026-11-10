[Help centre](../README.md) · Install and update · how-to

# Go back to an earlier version

If a new version of Starboard causes you a problem, go back to an earlier one with one command. Your settings are
backed up first, and you can update again when you are ready.

## Before you begin

- A terminal open on the server. Read [The terminal: typing commands](../basics/the-terminal.md).
- Know which version you had before, such as `v0.7.2`. The steps show how to list the versions.

## Steps if you used the installer

1. Go to the Starboard folder:

   ```bash
   cd ~/starboard
   ```

2. List the versions you can go back to. The newest is last:

   ```bash
   git tag -l 'v*' --sort=v:refname
   ```

3. Install the version you want. Put its name in place of `v0.7.2`, with the `v` at the start:

   ```bash
   ./update.sh --to v0.7.2
   ```

   The updater backs up your settings, installs that version and restarts Starboard. The last line says "Updated to"
   and the version you chose.

4. Reload Starboard in your browser.

## Steps if you used the ready-made image

1. Go to the folder that holds `compose.image.yaml`:

   ```bash
   cd ~/starboard
   ```

2. Open the Compose file in the text editor nano:

   ```bash
   nano compose.image.yaml
   ```

3. Find the line that starts `image: ghcr.io/themightytrex/starboard:`. Change the word after the last colon, usually
   `latest`, to the version you want, without the `v`. For example:

   ```
   image: ghcr.io/themightytrex/starboard:0.7.2
   ```

4. Save with **Ctrl** and **O**, then Enter. Leave nano with **Ctrl** and **X**.
5. Download that version:

   ```bash
   docker compose -f compose.image.yaml pull
   ```

6. Start Starboard with it:

   ```bash
   docker compose -f compose.image.yaml up -d
   ```

## Go forward again

- **With the installer:** run `./update.sh` on its own. It installs the newest release.
- **With the ready-made image:** change the version in the `image:` line back to `latest`, then run the commands in
  Steps 5 and 6 again.

## Things to note

- Staying on an older version means you miss fixes, including security fixes. Go forward again once the problem is
  solved.
- A newer version can change how settings are stored. When it does, Starboard keeps a copy of the old settings in
  `data/backups` first. If something looks wrong on the older version, put back the backup from before the update. Read
  [If it does not work](#if-it-does-not-work).
- Tell the people who make Starboard what went wrong, so it can be fixed. Read
  [Read the log and report a problem](read-the-log.md).

## If it does not work

- **"Stopped: there is no release called":** the version name is wrong. Check it in the list from Step 2, including the
  `v` at the start.
- **Settings are wrong on the older version (installer):** each update saved your `data` folder in the `backups`
  folder, in a file named with the date and time, such as `starboard-data-2026-11-01-093000-a1b2c3d.tar.gz`. To put
  one back:
  1. List the backups. The names include the date and time:

     ```bash
     ls backups
     ```

  2. Stop Starboard:

     ```bash
     docker compose down
     ```

  3. Move the current settings aside, so nothing is lost:

     ```bash
     mv data data.newer
     ```

  4. Unpack the backup from before the update that caused the problem. The newest backup was made when you went
     back, so use the one before it. Put its file name in place of the example:

     ```bash
     tar -xzf backups/starboard-data-2026-11-01-093000-a1b2c3d.tar.gz
     ```

  5. Start Starboard again:

     ```bash
     docker compose up -d
     ```

  If you installed with `--native`, use `systemctl --user stop starboard` and `systemctl --user start starboard` in
  place of the two docker commands.
- **Settings are wrong on the older version (ready-made image):** do the same with the copy you made before updating,
  `starboard-data-before-update.tar.gz`, and the commands `docker compose -f compose.image.yaml down` and
  `docker compose -f compose.image.yaml up -d`.

## Find out more

- [Update Starboard](update-starboard.md)
- [Back up and restore Starboard's settings](back-up-settings.md)
- [Restore a saved copy of your settings](restore-a-saved-copy.md)
- [Read the log and report a problem](read-the-log.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
