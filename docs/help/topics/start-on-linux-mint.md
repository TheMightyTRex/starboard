[Help centre](../README.md) · Before you install · how-to

# Start Starboard on Linux Mint

Linux Mint is the recommended system for Starboard: its desktop looks familiar, and the set-up opens in its browser
by itself. This page takes you from Linux Mint 22.3 on a computer to Starboard's set-up page. It takes about 20
minutes, most of it waiting for downloads.

## Before you begin

- Linux Mint 22.3 or later on the computer that will be your server. To install it, follow
  [Install Linux on a computer](install-linux.md#steps).
- A computer with at least 2 cores, 4 GB of memory and 40 GB for the system. Read
  [The four systems](what-you-need.md#the-four-systems) for the recommended computer.
- The password you sign in to Linux Mint with.

## Steps

1. Connect to the internet. With a network cable, Linux Mint connects by itself. For Wi-Fi, read
   [Connect with Wi-Fi on a desktop](connect-to-the-internet.md#connect-with-wi-fi-on-a-desktop).
2. Open a terminal: select **Menu**, enter `terminal` and select **Terminal**. **Ctrl**, **Alt** and **T** together
   also open one.
3. Copy this command, paste it into the terminal with **Ctrl**, **Shift** and **V**, and press Enter:

   ```bash
   curl -fsSL https://raw.githubusercontent.com/TheMightyTRex/starboard/main/run-first.sh | bash
   ```

4. Press Enter at each question to take the recommended answer. When it asks for your password, enter it and press
   Enter. Nothing shows as you type.
5. At **How do you want to finish setting up?**, press Enter for **In a browser (recommended)**. Firefox opens
   Starboard's set-up page with the setup code filled in. Read
   [Create your password and sign in](create-your-password.md).

On Linux Mint, the Run first script installs Docker from Linux Mint's own software sources. Read
[Set up everything with the Run first script](run-first.md#steps) for what each step does.

## Things to note

- Stop the computer going to sleep: select **Menu**, **Power Management**, and set **Put the computer to sleep when
  inactive** to **Never**.
- Soon after Linux Mint is installed, the Update Manager often installs updates. The script waits for them with a
  progress bar, then carries on by itself.

## If it does not work

- **An error number, a 404 or "Command 'curl' not found":** read
  [If it does not work](run-first.md#if-it-does-not-work) in the Run first article.
- **Error RF-12, or "Could not get lock":** the Update Manager took more than 45 minutes. Read
  [RF-12](run-first-errors.md#rf-12).
- **The browser does not open:** open Firefox and go to the address the terminal shows, then enter the setup code
  it shows.
- **A phone or another computer cannot open Starboard:** the firewall may be active. Allow Starboard's port:

  ```bash
  sudo ufw allow 8095/tcp
  ```

- **"permission denied" from a `docker` command in a new terminal:** sign out and back in once.

## Find out more

- [Set up everything with the Run first script](run-first.md)
- [What you need to run Starboard](what-you-need.md)
- [Open Starboard from a phone or another computer](open-from-another-device.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
