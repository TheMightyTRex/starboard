[Help centre](../README.md) · Backup and restore · how-to

# Restore a saved copy of your settings

Starboard saves a copy of its settings before every restore and before an update changes them. You can put
one of those copies back with no file to find.

## Before you begin

- You know Starboard's password. Starboard asks for it before it restores or downloads a copy.

## Steps

1. Go to **Settings**, then **Updates**, then **Restore**, and find **Restore your settings**. The same list is
   on **System**, **Backup**, under **Copies Starboard saved**.
2. In the list, the newest copy comes first. Each one shows when it was made and why: **Before a restore** or
   **Before an update changed the settings**.
3. Select the date of a copy to show what it holds: how many apps, its categories and the apps' names.
4. Select **Restore this copy**. You can also select **Restore** straight from the list.
5. Starboard asks **Restore Starboard's settings?** Enter **Your password** and select **Restore settings**.

Starboard shows **Settings restored** and how many apps it put back. The settings you had a moment ago are
saved as a new copy, so you can change your mind.

## Things to note

- A restore replaces your apps, categories and settings. Your password and sign-ins stay as they are.
- To keep a copy somewhere else, open it and select **Download**. You can put it back later with
  **Restore from a file**. Read [Back up and restore Starboard's settings](back-up-settings.md#restore-from-a-file).
- The copies are kept on the server, in the `data/backups` folder inside the Starboard folder. The page
  lists the newest 30.
- "No saved copies yet" means Starboard has not restored or updated its settings so far.
- These copies are separate from the backup of the whole `data` folder that `./update.sh` makes before an
  update. For that one, read [Go back to an earlier version](go-back-to-an-earlier-version.md).

## If it does not work

- **"That password is not right":** check Caps Lock and enter it again.

## Find out more

- [Back up and restore Starboard's settings](back-up-settings.md)
- [Update Starboard](update-starboard.md)
- [Go back to an earlier version](go-back-to-an-earlier-version.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
