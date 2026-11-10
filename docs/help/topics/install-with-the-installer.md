[Help centre](../README.md) · Install and update · how-to

# Install Starboard with the installer

The installer asks what Starboard may access on your computer, then builds and starts it. At the end it shows the
addresses to open Starboard and a one-time setup code for choosing your password. It takes about 10 minutes.

Most people use the [Run first script](run-first.md) instead. It installs Docker and everything else, then runs
this installer for you. Use this page to do it by hand.

## Before you begin

- A Linux computer that is big enough. Read [What you need to run Starboard](what-you-need.md).
- Docker is installed and `docker compose version` shows a version number. Read [Install Docker](install-docker.md).
- A terminal open on that computer. Read [The terminal: typing commands](../basics/the-terminal.md).
- Run everything as your normal user. Do not put `sudo` in front of the installer.

## Steps

1. Install git, the tool that downloads Starboard and later updates it. It asks for your password:

   ```bash
   sudo apt install git
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

   It says what it is going to do, checks that Docker is installed, then asks its questions one at a time.
6. Answer each question: enter the number of your answer and press Enter. Press Enter on its own to take the
   recommended answer. When you run the installer again, your last answer is the default instead.
7. Wait while the installer builds and starts Starboard. The first time, this can take several minutes.
8. When it finishes, the installer shows the addresses and the setup code. Keep the terminal open, or write the code
   down.
9. Open the first address in a browser on this computer and choose your password. Read
   [Create your password and sign in](create-your-password.md).

## The questions, in plain words

Every question is optional. If you are unsure, answer no: only that part of Starboard is missing, and you can change
your answer later. On a new install it asks only about your home network, Docker access and, when the computer has
more than one extra drive, Drive pools. When you run it again, it also asks about each app's use, a Live TV folder,
folders to show and disk health.

[What the installer asks, and what each answer means](what-the-installer-asks.md#the-access-it-asks-for) explains
every question. Your dashboard's name, media folder, apps and alerts come next, in Starboard's own set-up, in the
browser or the terminal.

## What it prints at the end

When Starboard is running, the installer shows **Open Starboard** with these lines:

- **On this computer:** the address to use in a browser on the server itself, such as `http://localhost:8095`.
- **On other devices:** the address for every other device at home, such as `http://192.168.1.20:8095`. It appears
  only if you let your home network open Starboard.
- **Setup code:** the one-time code you enter before choosing a password. If you lose it, read
  [Find the setup code](find-the-setup-code.md).
- **Ask again** and **Update:** the commands to change your answers and to update Starboard.

## Things to note

- Your answers are saved in two files in the Starboard folder: `.env` and `compose.access.yaml`. Your settings and
  password are kept in the `data` folder. None of them leave your computer.
- To change your answers later, run `./install.sh` again in the Starboard folder. Your settings and password stay.
  Read [Change what Starboard can access](change-what-starboard-can-access.md).
- No browser to finish in? Run `./install.sh --terminal`. Read
  [Set up Starboard in the terminal, with no browser](set-up-in-the-terminal.md).
- Without Docker, the installer can run Starboard with the computer's own Python: `./install.sh --native`. This
  needs Python 3.10 or newer. At the end, it shows one more command to run so Starboard keeps running after you sign
  out.

## If it does not work

Each time the installer stops, it shows an error number, such as "Error IN-07". Find it in
[Run first and installer error numbers](run-first-errors.md#starboards-installer). The most common are:

- **IN-05, IN-07 or IN-08:** git, Docker or Docker Compose is missing. Read
  [IN-07](run-first-errors.md#in-07).
- **IN-04:** you put `sudo` in front of the installer. Run `./install.sh` on its own.
- **IN-22:** you have not signed out and back in since installing Docker. Read [IN-22](run-first-errors.md#in-22).
- **IN-24:** Starboard did not start. Read [Starboard does not open](starboard-does-not-open.md).

## Find out more

- [Find the setup code](find-the-setup-code.md)
- [Set up Starboard in the terminal, with no browser](set-up-in-the-terminal.md)
- [Create your password and sign in](create-your-password.md)
- [Open Starboard from a phone or another computer](open-from-another-device.md)
- [Install Starboard from the ready-made image](install-from-the-ready-made-image.md)
- [Install Starboard on a Linux computer](../guides/install-on-a-linux-computer.md)
- [Update Starboard](update-starboard.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
