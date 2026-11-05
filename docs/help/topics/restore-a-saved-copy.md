[Help centre](../README.md) · Backup and restore · how-to

# Restore a saved copy of your settings

Starboard saves a copy of its settings before every restore and before an update changes them. You can put
one of those copies back from **Settings**, **Updates**, **Restore**, or from **System**, **Backup**, with no file to
find.

## Before you begin

- You know Starboard's password. Starboard asks for it before it restores or downloads a copy.

## Steps

1. Go to **Settings**, **Updates**, then **Restore**. **Restore your settings** is open at the top. (On **System**,
   **Backup**, the same list is under **Copies Starboard saved**.)
2. Find the list of saved copies. The newest copy comes first. Each one shows when it was made and why:
   **Before a restore** or **Before an update changed the settings**.
3. Select the date of a copy to see what it holds: how many apps, its categories and the apps' names.
4. Select **Restore this copy**. You can also select **Restore** straight from the list.
5. Starboard asks **Restore Starboard's settings?** Type **Your password** and select **Restore settings**.

Starboard shows **Settings restored** and how many apps it put back. The settings you had a moment ago are
saved as a new copy, so you can change your mind.

## Things to note

- A restore replaces your apps, categories and settings. Your password and sign-ins stay as they are.
- To keep a copy somewhere else, open it and select **Download**. You can later put it back with
  **Restore from a file**, as described in
  [Back up and restore Starboard's settings](back-up-settings.md).
- The copies are kept on the server, in the `data/backups` folder inside the Starboard folder. The page
  lists the newest 30.
- If the list says "No saved copies yet", Starboard has not restored or updated its settings so far.
- These copies are separate from the backup that `./update.sh` makes of the whole `data` folder before an
  update. Read [Go back to an earlier version](go-back-to-an-earlier-version.md) for that one.

## If it does not work

- **"That password is not right":** check Caps Lock and type it again.

## Find out more

- [Back up and restore Starboard's settings](back-up-settings.md)
- [Update Starboard](update-starboard.md)
- [Go back to an earlier version](go-back-to-an-earlier-version.md)
