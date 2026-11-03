[Help centre](../README.md) · Backup and restore · how-to

# Back up and restore Starboard's settings

Download Starboard's settings as one file, and put them back from that file later. The file holds your
apps, their API keys, your categories and your other settings, so you can rebuild your dashboard in minutes.

## Before you begin

- You know Starboard's password. Starboard asks for it before every download and every restore.

## Steps

### Download a backup

1. Go to **System**, then **Backup and restore**.
2. Find **Starboard's settings**.
3. Select **Download a backup**.
4. Starboard asks for **Your password**. Type it and select **Download**.

Your browser saves a file named like `starboard-settings-2026-11-03.json`, with the date you made it.
Starboard shows how many apps the backup holds.

### Restore from a file

1. Go to **System**, then **Backup and restore**.
2. In **Starboard's settings**, select **Restore from a file**.
3. Choose the backup file you downloaded.
4. Starboard asks **Restore Starboard's settings?** and says how many apps the file holds and when it was
   made. Type **Your password** and select **Restore settings**.

Starboard shows **Settings restored** and how many apps it put back.

## Things to note

- The backup holds your apps' API keys. Keep the file somewhere private, such as a USB stick you keep at
  home, and do not share it.
- The backup never holds your password or anyone's sign-in. A restore leaves both as they are.
- A restore replaces all your apps, categories and settings with the ones in the file.
- Before every restore, Starboard saves a copy of the settings you had. To go back, read
  [Restore a saved copy of your settings](restore-a-saved-copy.md).
- You can restore a backup made by an older version of Starboard. Starboard brings it up to date as it
  restores: a choice that no longer exists goes back to its default, and an app of a kind Starboard no
  longer knows becomes a plain link.
- This backup covers Starboard only, not your other apps or your media. For the whole server, read
  [Back up the whole server](back-up-the-server.md).

## If it does not work

- **"That password is not right":** check Caps Lock and type it again.
- **"That file is not a Starboard backup":** choose the file you downloaded with **Download a backup**. It
  ends in `.json`.

## Find out more

- [Restore a saved copy of your settings](restore-a-saved-copy.md)
- [Move Starboard to a new computer](../guides/move-starboard-to-a-new-computer.md)
- [Back up the whole server](back-up-the-server.md)
- [What an API key is](../basics/what-is-an-api-key.md)
