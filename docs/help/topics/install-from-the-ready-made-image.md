[Help centre](../README.md) · Install and update · how-to

# Install Starboard from the ready-made image

The ready-made image is the quickest way to install Starboard: Docker downloads it already built, so there is nothing
to build and no questions to answer. At the end, Starboard is running and you have the setup code for choosing your
password.

## Before you begin

- A Linux computer that is big enough. Read [What you need to run Starboard](what-you-need.md). Images are made for
  64-bit computers and for Raspberry Pi models on 32-bit or 64-bit Raspberry Pi OS.
- Docker is installed and `docker compose version` prints a version number. Read [Install Docker](install-docker.md).
- A terminal open on that computer. Read [The terminal: typing commands](../basics/the-terminal.md).

## Steps

1. Make a folder for Starboard in your home folder:

   ```bash
   mkdir ~/starboard
   ```

2. Go into it:

   ```bash
   cd ~/starboard
   ```

3. Download Starboard's Compose file, the list that tells Docker how to run it:

   ```bash
   curl -fsSLO https://raw.githubusercontent.com/TheMightyTRex/starboard/main/compose.image.yaml
   ```

4. Make the `data` folder, where Starboard keeps its settings. Making it yourself, before Starboard starts, means
   the folder belongs to you:

   ```bash
   mkdir -p data
   ```

5. Check your user number. This command prints it, usually `1000`:

   ```bash
   id -u
   ```

6. Check your group number, also usually `1000`:

   ```bash
   id -g
   ```

7. If both are `1000`, go to Step 8. If not, or if you want to set your time zone, change the Compose file. Open it
   in the text editor nano:

   ```bash
   nano compose.image.yaml
   ```

   - On the line `user: "1000:1000"`, put your user number, a colon, then your group number.
   - On the line `- TZ=Europe/London`, put your own time zone, such as `Europe/Dublin` or `America/New_York`.
     Download hours follow it.
   - To save, press **Ctrl** and **O**, then Enter. To leave nano, press **Ctrl** and **X**.

8. Start Starboard. Docker downloads the image, which takes a minute or two the first time:

   ```bash
   docker compose -f compose.image.yaml up -d
   ```

   When the prompt comes back, Starboard is running.

9. Show Starboard's log, which holds the setup code:

   ```bash
   docker logs starboard
   ```

   Look for the line "No password yet. Open the dashboard and enter this setup code:" followed by the code.

10. In a browser on this computer, open `http://localhost:8095`. Enter the setup code and choose your password. Read
    [Create your password and sign in](create-your-password.md).

## Optional extras

The Compose file has some extra lines that start with `#`, which means they are inactive. Each has a comment
that explains it. To switch one on, open the file with nano, remove the `#` and the space after it at the start of
the line, save, and run the command in Step 8 again.

- **Folders for System, Storage:** shows how full your drives are. You need two lines: the `STARBOARD_DISKS` line,
  and one line for each folder under `volumes`, such as `/mnt/media:/disks/media:ro`. The `:ro` means read-only.
- **The Docker socket:** lets **System**, **Apps**, **Updates** update your other apps and lets Starboard find their API keys.
  This gives Starboard full control of Docker, which is the same as full control of the computer. Leave it out if
  you are unsure. It needs three lines: the `docker.sock` line, and the `group_add:` line with the number under
  it. Put your own number there: this command prints it.

  ```bash
  stat -c %g /var/run/docker.sock
  ```

Read [Change what Starboard can access](change-what-starboard-can-access.md) for more.

## Things to note

- Unlike the installer, the ready-made image asks no questions. Phones and other computers on your home network can
  open Starboard straight away, with your password. To change that, go to **Settings**, then **Security**. Read
  [Choose who can open Starboard](choose-who-can-open-starboard.md).
- Every command for this kind of install includes `-f compose.image.yaml`, and runs in the folder that holds that
  file. Without it, Docker does not know which Compose file you mean.
- Your settings, sessions and API keys stay in the `data` folder. Keep it when you update or remove Starboard.

## If it does not work

- **"permission denied" when you run a docker command:** you have not signed out and back in since installing
  Docker. Sign out, sign in and try again.
- **"no configuration file provided" or "no such file":** you are not in the Starboard folder. Run `cd ~/starboard`
  first.
- **Starboard stops straight after it starts, or the log says it cannot write to `/data`:** the `data` folder belongs
  to another user, or the numbers on the `user:` line are not yours. Check Steps 4 to 7.
- **No setup code in the log:** a password has already been chosen. If you have forgotten it, read
  [Reset a forgotten password](reset-a-forgotten-password.md).

## Find out more

- [Find the setup code](find-the-setup-code.md)
- [Open Starboard from a phone or another computer](open-from-another-device.md)
- [Update Starboard](update-starboard.md)
- [Install Starboard with the installer](install-with-the-installer.md)
- [What Docker is](../basics/what-is-docker.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
