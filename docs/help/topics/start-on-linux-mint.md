[Help centre](../README.md) · Before you install · how-to

# Start Starboard on Linux Mint

Linux Mint is the recommended system for Starboard: it has a desktop that looks familiar, and the set-up opens in
its browser by itself. This page takes you from Linux Mint 22.3 on a computer to Starboard's set-up page, with one
command. It takes about 20 minutes, most of it waiting for downloads.

## Before you begin

- Linux Mint 22.3 or later, installed on the computer that will be your server. To install it, download the
  **Cinnamon Edition** from [Linux Mint's download page](https://linuxmint.com/download.php) and follow
  [Linux Mint's installation guide](https://linuxmint-installation-guide.readthedocs.io/en/latest/), or read
  [Install Linux on a computer](install-linux.md).
- A computer big enough for a media server:

  | | Minimum | Recommended |
  |---|---|---|
  | Processor | 64-bit, 2 cores | 4 cores; an Intel processor from 2018 or later converts video best |
  | Memory | 4 GB | 8 GB |
  | Disk for the system | 40 GB | An SSD of 120 GB or more |
  | Media | Space on the same disk | A separate drive of 1 TB or more |

- The password you sign in to Linux Mint with.

## Steps

1. Connect to the internet. With a network cable, Linux Mint connects by itself. For Wi-Fi, select the network icon
   in the panel and choose your network. Read
   [Connect to the internet, by cable or Wi-Fi](connect-to-the-internet.md).
2. Open a terminal: select **Menu**, type `terminal` and select **Terminal**. Pressing **Ctrl**, **Alt** and **T**
   together also opens one.
3. Copy this command, paste it into the terminal with **Ctrl**, **Shift** and **V**, and press Enter:

   ```bash
   curl -fsSL https://raw.githubusercontent.com/TheMightyTRex/starboard/main/run-first.sh | bash
   ```

4. Press Enter at each question to take the recommended answer. When it asks for your password, type it and press
   Enter. Nothing shows as you type.
5. **Finish setting up:** press Enter for **In a browser (recommended)**. Firefox opens Starboard's set-up page with
   the setup code filled in. Read [Create your password and sign in](create-your-password.md).

The Run first script installs Docker from Linux Mint's own software sources, so it stays up to date with the rest of
Linux Mint. Read [Set up everything with the Run first script](run-first.md) for what each step does.

## Things to note

- Keep the computer on and stop it going to sleep: select **Menu**, **Power Management**, and set **Put the computer
  to sleep when inactive** to **Never**.
- After the script allows your user to use Docker, sign out and back in once, so `docker` commands work in new
  terminals too.

## If it does not work

- **"Command 'curl' not found":** use the same command with `wget`, which Linux Mint includes:

  ```bash
  wget -qO- https://raw.githubusercontent.com/TheMightyTRex/starboard/main/run-first.sh | bash
  ```

- **"Could not get lock" or "Waiting for cache lock":** the Update Manager is installing updates, which often
  happens just after Linux Mint is installed. Wait for it to finish, then select **Try again**.
- **"error: 404":** the address was typed with a difference. Copy and paste the command instead.
- **The browser does not open:** open Firefox yourself and go to the address the terminal shows, then type the setup
  code it shows.
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
