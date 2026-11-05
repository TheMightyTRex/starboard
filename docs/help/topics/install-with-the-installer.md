[Help centre](../README.md) · Install and update · how-to

# Install Starboard with the installer

The installer downloads Starboard, asks what it may access on your computer, and starts it. At the end it prints the
addresses to open Starboard and a one-time setup code for choosing your password. It takes about 10 minutes.

The [Run first script](run-first.md) installs Docker and git if they are missing and then starts the installer for
you. Use this page to do it by hand.

## Before you begin

- A Linux computer that is big enough. Read [What you need to run Starboard](what-you-need.md).
- Docker is installed and `docker compose version` prints a version number. Read [Install Docker](install-docker.md).
- A terminal open on that computer. Read [The terminal: typing commands](../basics/the-terminal.md).
- Run everything as your normal user. Do not type `sudo` in front of the installer.

## Steps

1. Install git, the tool that downloads Starboard and later updates it. It asks for your password. On Ubuntu, Linux
   Mint, Debian and Raspberry Pi OS:

   ```bash
   sudo apt install git
   ```

   On Fedora:

   ```bash
   sudo dnf install git
   ```

2. Go to your home folder:

   ```bash
   cd ~
   ```

3. Download Starboard. This makes a folder called `starboard` in your home folder:

   ```bash
   git clone https://github.com/TheMightyTRex/starboard.git
   ```

4. Go into the new folder:

   ```bash
   cd starboard
   ```

5. Start the installer:

   ```bash
   ./install.sh
   ```

   It explains what it is going to do, checks that Docker is installed, then asks its questions one at a time.

6. Answer each question, then press Enter. The next section explains every question. The answer in capitals in the
   brackets is the default: `[Y/n]` means Enter on its own says yes, and `[y/N]` means Enter on its own says no.
7. Wait while the installer builds and starts Starboard. The first time, this downloads what Starboard needs and can
   take several minutes.
8. When it finishes, the installer prints the addresses and the setup code. Keep the terminal open, or write the code
   down.
9. Open the first address in a browser on this computer and choose your password. Read
   [Create your password and sign in](create-your-password.md).

## The questions, in plain words

Every question is optional. If you are unsure, answer no: only that part of Starboard is missing, and you can change
your answer later.

1. **"Name your dashboard (shown in the header; change it later in Settings) [Starboard]"**
   The name shown in the header of every page, such as "Sam's server". Press Enter to keep "Starboard". Asked on a new
   install only.
2. **"Let your home network open Starboard? [Y/n]"**
   Yes means phones and other computers at home can open Starboard, with your password. No means only this computer
   can. Most people answer yes. Asked on a new install only: after that, it is a switch in **Settings**,
   **Security**.
3. **"Give Starboard access to Docker for app updates? [y/N]"**
   Yes lets Starboard update your other apps for you on **System**, **Apps**, **Updates**, and find their API keys. This gives
   Starboard full control of Docker, which is the same as full control of the computer. If unsure, answer no.
4. **"Show each app's processor and memory use? [y/N]"**
   Yes lets **System**, **Overview**, **Monitor** show what each app is using. Starboard only reads, and only while that page is
   open. No means Monitor shows the whole server only.
5. **"Give Starboard a Live TV folder? [y/N]"**
   Only for Jellyfin users who want free Live TV channels. Yes asks for the folder Jellyfin reads its Live TV files
   from, for example `/srv/jellyfin/config/iptv`. Starboard writes only in that folder. If you do not use Jellyfin,
   answer no.
6. **"Choose folders to show? [y/N]"**
   Yes lets **System**, **Storage** show how full your drives are. Type one folder per line as a name, an equals
   sign and the folder, such as `Media=/mnt/media`, then press Enter on an empty line to finish. Starboard reads how
   full they are, never the files.
7. **"Set up Disk health reports? [y/N]"**
   Yes lets **System**, **Storage**, **Disk health** show each drive's health report, which can warn of a failing drive. It installs a small job that checks your
   drives every 30 minutes, so it asks for your password. It needs a program called smartmontools.

When you run the installer again later, it shows your last answers as the defaults.

## What it prints at the end

When Starboard is running, the last lines look like this, with your own address and code:

```
== Starboard is running
On this computer: http://localhost:8095
On your phone or other computers: http://192.168.1.20:8095
What Starboard can access, and how to change it: Settings, About and updates.
Setup code (you need it once, to choose your password): <your setup code>
To update later: ./update.sh
```

- **On this computer** is the address to use in a browser on the server itself.
- **On your phone or other computers** is the address for every other device at home. It appears only if you let your
  home network open Starboard.
- **Setup code** is the one-time code you enter before choosing a password. If you lose it, read
  [Find the setup code](find-the-setup-code.md).

## Things to note

- Your answers are saved in two files in the Starboard folder: `.env` and `compose.access.yaml`. Your settings and
  password are kept in the `data` folder. None of them leave your computer.
- To change your answers later, go to the Starboard folder and run `./install.sh` again. Your settings and password
  stay. Read [Change what Starboard can access](change-what-starboard-can-access.md).
- No browser to finish in? Run `./install.sh --terminal`, and the installer asks for your password, the apps and
  your download hours in the terminal too. Read [Set up Starboard in the terminal](set-up-in-the-terminal.md).
- Without Docker, the installer can run Starboard with the computer's own Python instead: `./install.sh --native`.
  This needs Python 3.10 or newer. When it finishes, it prints one more command to run so Starboard keeps running
  after you sign out.

## If it does not work

- **"Stopped: install git first":** git is missing. Run Step 1 again.
- **"Stopped: install Docker first, or use --native"** or **"install the Docker Compose plugin first":** Docker is
  missing or incomplete. Follow [Install Docker](install-docker.md).
- **"Stopped: run this as your normal user, not root":** you typed `sudo` before the installer. Run `./install.sh` on
  its own.
- **"permission denied" while it builds:** you have not signed out and back in since installing Docker. Sign out,
  sign in, go to the Starboard folder with `cd ~/starboard`, and run `./install.sh` again.
- **"Stopped: there is no folder":** a folder you typed does not exist. Check the spelling, including capitals, and
  run the installer again.
- **"install smartmontools first":** for Disk health, install smartmontools with `sudo apt install smartmontools`
  (Fedora: `sudo dnf install smartmontools`), then run `./install.sh` again.
- **"Stopped: Starboard did not start":** read what went wrong with `docker compose logs starboard`, then read
  [Starboard does not open](starboard-does-not-open.md).

## Find out more

- [Find the setup code](find-the-setup-code.md)
- [Set up Starboard in the terminal, with no browser](set-up-in-the-terminal.md)
- [Create your password and sign in](create-your-password.md)
- [Open Starboard from a phone or another computer](open-from-another-device.md)
- [Install Starboard from the ready-made image](install-from-the-ready-made-image.md)
- [Install Starboard on a Linux computer](../guides/install-on-a-linux-computer.md)
- [Update Starboard](update-starboard.md)
