[Help centre](../README.md) · Install and update · how-to

# Remove Starboard

Stop Starboard and take it off your server with one command. Your media apps are not affected. Keep the Starboard
folder, or move it somewhere safe, so you can bring your settings back if you change your mind.

## Before you begin

- A terminal open on the server. Read [The terminal: typing commands](../basics/the-terminal.md).
- If you might want your settings again, download a copy first. Read
  [Back up and restore Starboard's settings](back-up-settings.md).

## Steps if you used the installer

1. Go to the Starboard folder:

   ```bash
   cd ~/starboard
   ```

2. Stop Starboard and remove its container:

   ```bash
   docker compose down
   ```

   Starboard stops and no longer starts when the computer starts.

## Steps if you installed with --native

1. Stop Starboard and stop it starting with the computer:

   ```bash
   systemctl --user disable --now starboard
   ```

## Steps if you used the ready-made image

1. Go to the folder that holds `compose.image.yaml`:

   ```bash
   cd ~/starboard
   ```

2. Stop Starboard and remove its container:

   ```bash
   docker compose -f compose.image.yaml down
   ```

## If you activated Disk health

The installer set up a small job that checks your drives every 30 minutes. It keeps running after Starboard is gone,
so remove it too.

1. Go to the Starboard folder:

   ```bash
   cd ~/starboard
   ```

2. Remove the job. It asks for your password:

   ```bash
   sudo deploy/install-smart.sh --remove
   ```

   It says "Removed the Disk health timer". The reports it already saved stay in the `smart` folder.

## Your settings and the Starboard folder

The Starboard folder still holds your settings, API keys and backups, in the `data` and `backups` folders and the
`.env` file. None of the steps in this article removes them.

- **If you might use Starboard again:** keep the folder as it is. To start Starboard again later, run
  `docker compose up -d` in it, or `docker compose -f compose.image.yaml up -d` for the ready-made image.
- **If you want it out of the way:** move the whole folder somewhere else, such as an external drive or a folder for
  old things. It holds your API keys, so keep it somewhere private.
- **Only when you are sure** you will never want the settings again, delete the folder. This cannot be undone.

## Things to note

- Removing Starboard does not touch your media apps, your films and series, or anything Starboard installed for you
  with **Install apps**. Those keep running.
- Docker keeps a copy of Starboard's image, which takes some disk space. Removing it is optional. For the installer it
  is called `starboard:local`; for the ready-made image, `ghcr.io/themightytrex/starboard`. Remove it with
  `docker image rm` and the name.

## Find out more

- [Back up and restore Starboard's settings](back-up-settings.md)
- [Move Starboard to a new computer](../guides/move-starboard-to-a-new-computer.md)
- [Install Starboard with the installer](install-with-the-installer.md)
