[Help centre](../README.md) · Install and update · how-to

# Set up everything with the Run first script

Once Linux is installed, the Run first script sets up everything else: it checks the computer, installs Docker and
anything else that is missing, downloads Starboard and starts its installer. Then the set-up opens in your browser
if the computer has a desktop, or carries on in the terminal if it does not. It takes about 15 minutes.

## Before you begin

- A computer with Linux installed: Linux Mint 22.3 (recommended), Debian 13, Ubuntu Server 26.04 or Raspberry Pi
  OS (64-bit), or a later version, with or without a desktop. Read [Install Linux on a computer](install-linux.md).
  Each system has its own page, with the computer it needs and its common problems:
  [Linux Mint](start-on-linux-mint.md), [Debian](start-on-debian.md), [Ubuntu Server](start-on-ubuntu-server.md)
  and [Raspberry Pi OS](start-on-raspberry-pi-os.md).
- The computer is connected to the internet. Not sure? Read
  [Connect to the internet, by cable or Wi-Fi](connect-to-the-internet.md).
- The password you use to sign in to that computer. It is asked for when something needs installing.
- A terminal open on that computer, or connected to it. Read [The terminal: typing commands](../basics/the-terminal.md).

## Steps

1. Copy this command into the terminal and press Enter:

   ```bash
   curl -fsSL https://raw.githubusercontent.com/TheMightyTRex/starboard/main/run-first.sh | bash
   ```

   Type it exactly, or better, copy and paste it: `main/run-first.sh` must be in small letters, with a hyphen, and
   the GitHub account is `TheMightyTRex`. A typing mistake gives "error: 404", which means "not found". Read
   [Capital letters matter](../basics/the-terminal.md#capital-letters-matter).

   The `|` in the middle is the vertical bar, which is in a different place on different keyboards: on a UK
   keyboard it is **Shift** and the `\` key next to the left **Shift**. Read
   [Symbols that are in different places on different keyboards](../basics/the-terminal.md#symbols-that-are-in-different-places-on-different-keyboards).
   With no `|` at all, these two commands do the same:

   ```bash
   curl -fsSL -o run-first.sh https://raw.githubusercontent.com/TheMightyTRex/starboard/main/run-first.sh
   bash run-first.sh
   ```

   If it says "Command 'curl' not found" (a new Debian does not include curl), use this command instead. It does
   the same with `wget`, which Linux Mint, Debian, Ubuntu Server and Raspberry Pi OS include:

   ```bash
   wget -qO- https://raw.githubusercontent.com/TheMightyTRex/starboard/main/run-first.sh | bash
   ```

2. The first question is about how it looks. Press Enter for the standard look, or type `a` and press Enter for
   **accessible mode**: plain lines with no boxes or colour, for software that reads text aloud. Your choice is kept
   for the whole installation.
3. **Welcome:** choose how to finish setting up. **In a browser** is recommended when the computer has a desktop;
   **Here in the terminal** when it has none, such as when you are connected over SSH. Press Enter for the
   recommended answer.
4. **Check this computer:** it lists what is already there, with a tick, and what is missing. This changes nothing.
5. **Install what is missing:** it shows the commands it will run. Press Enter to install them. When it asks for
   your password, type it and press Enter. Nothing shows as you type. If everything is already there, it says so.
6. **Download Starboard:** it downloads Starboard into a folder called `starboard` in your home folder, or updates
   it if it is already there.
7. **Install Starboard:** check the summary and press Enter. Starboard's installer asks about your home network and
   Docker access, and about drive pools when there is more than one drive. If you are unsure, the answer in capitals
   is the safe one. Answer yes to Docker access if you want Starboard to start your media apps for you. The script
   tells Starboard what it found on this computer (drives, apps already running, memory), so the set-up can
   recommend the right answers.
8. Finish setting up:
   - **In a browser, on a computer with a desktop:** the set-up page opens by itself with the setup code filled in.
     Choose your password. Read [Create your password and sign in](create-your-password.md).
   - **In a browser, with no desktop:** open the address it prints on a phone or another computer at home, and
     enter the setup code it shows.
   - **Here in the terminal:** answer the set-up questions. Read
     [Set up Starboard in the terminal, with no browser](set-up-in-the-terminal.md). At the end, the script makes the
     set-up's changes to this computer, such as disk health, and asks for your password if it needs it.

## How to answer

- Press Enter on its own to take the recommended answer.
- Type `b` and press Enter to go back a step, `?` for help with the step, or `q` to stop. Stopping changes nothing
  more, and you can run the script again at any time.
- Each step starts on an empty terminal window. The heading and progress bar stay at the top and the keys stay on
  the bottom line.

## Things to note

- You can run it again at any time: it only installs what is missing, and updates Starboard if it is already
  downloaded.
- To only check the computer, with no changes, add `--check`:

  ```bash
  curl -fsSL https://raw.githubusercontent.com/TheMightyTRex/starboard/main/run-first.sh | bash -s -- --check
  ```

- Prefer to read a script before running it? Download it, read it, then run it:

  ```bash
  curl -fsSL -o run-first.sh https://raw.githubusercontent.com/TheMightyTRex/starboard/main/run-first.sh
  less run-first.sh
  bash run-first.sh
  ```

- It never runs as administrator by itself and never keeps your password: sudo asks for it, only when something is
  being installed.
- It allows your user to use Docker. This is the same as administrator control of the computer, so only run it as
  your own user.
- After it allows your user to use Docker, sign out and back in once, so ordinary `docker` commands work in new
  terminals too. The installer itself does not need this.

## If it does not work

- **An error number, such as "Error RF-11":** look it up in [Run first error numbers](run-first-errors.md),
  which says what each one means and how to put it right.
- **"The requested URL returned error: 404":** the address was typed with a difference. Copy and paste it instead,
  or check that `main/run-first.sh` is in small letters with a hyphen and the account is `TheMightyTRex`.
- **"Command 'curl' not found" or "curl: command not found":** use the same command with `wget` instead:

  ```bash
  wget -qO- https://raw.githubusercontent.com/TheMightyTRex/starboard/main/run-first.sh | bash
  ```

  If `wget` is missing too, install curl, then run the first command again. Use the command below, not the
  `sudo snap install curl` that Ubuntu suggests: the snap version is sandboxed and cannot save the files the script
  needs:

  ```bash
  sudo apt install curl
  ```

- **"curl: (23) client returned ERROR on write", with a message about `curl.snap`:** curl was installed as a snap,
  which cannot save files where the script needs them. Install the usual curl, then run the script again; it uses
  that one from then on:

  ```bash
  sudo apt install curl
  ```

- **"This Linux is not one this script knows how to install on":** install Docker by hand with
  [Install Docker](install-docker.md), then run the script again.
- **A command fails while installing:** read the lines above the message. Most often the computer is not online, or
  another update is running. Wait a few minutes and run the script again.
- **"exists but is not a Starboard download":** a folder called `starboard` is already in your home folder. Move or
  rename it, then run the script again.

## Find out more

- [Run first error numbers](run-first-errors.md)
- [Get Starboard up and running, from a bare computer](../guides/get-up-and-running.md)
- [Install Linux on a computer](install-linux.md)
- [Install Docker](install-docker.md), to do it by hand
- [Install Starboard with the installer](install-with-the-installer.md), to do it by hand

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
