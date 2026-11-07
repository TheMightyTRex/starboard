[Help centre](../README.md) · Install and update · how-to

# Find the setup code

The setup code is a one-time code that proves the person choosing Starboard's password is the person who installed
it. The installer prints it, and you can show it again at any time on the server until you have chosen a password.

## Before you begin

- Starboard is installed and running. Read [Install Starboard with the installer](install-with-the-installer.md) or
  [Install Starboard from the ready-made image](install-from-the-ready-made-image.md).
- A terminal open on the server. Read [The terminal: typing commands](../basics/the-terminal.md).

## Steps if you used the installer

1. Look at the last lines the installer printed. The code follows "Setup code (you need it once, to choose your
   password):".
2. If you closed the terminal, open a new one and go to the Starboard folder:

   ```bash
   cd ~/starboard
   ```

3. Show the code. This prints the setup code on its own:

   ```bash
   cat data/setup-token
   ```

   You can also find it in Starboard's log, on the line that starts "No password yet. Open the dashboard and enter this
   setup code:". To show the log:

   ```bash
   docker compose logs starboard
   ```

## Steps if you used the ready-made image

1. Open a terminal on the server.
2. Show Starboard's log:

   ```bash
   docker logs starboard
   ```

3. Find the line "No password yet. Open the dashboard and enter this setup code:". The code is at the end of it.

## Things to note

- The code stays the same when Starboard restarts or updates, until you choose a password. After that it is
  deleted and no longer works.
- Copy the code exactly, with the same capital and small letters. It can include dashes and underscores.
- If you installed with `./install.sh --native`, show the log with `journalctl --user -u starboard` instead.

## If it does not work

- **"No such file or directory":** either you are not in the Starboard folder, or a password has already been
  chosen, so there is no code any more. Run `cd ~/starboard` and try again.
- **A password has already been chosen and you do not know it:** read
  [Reset a forgotten password](reset-a-forgotten-password.md). Resetting makes a new setup code.
- **Starboard says "The setup code is not right":** check you copied the whole code and nothing else, with no space
  at either end. Show it again with the steps here and copy it once more.

## Find out more

- [Create your password and sign in](create-your-password.md)
- [Reset a forgotten password](reset-a-forgotten-password.md)
- [Starboard does not open](starboard-does-not-open.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
