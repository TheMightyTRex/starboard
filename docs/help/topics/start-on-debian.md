[Help centre](../README.md) · Before you install · how-to

# Start Starboard on Debian

Debian with no desktop is the lightest system for Starboard: it leaves the most memory for your apps, so it suits an
older or smaller computer. This page takes you from Debian 13 on a computer to Starboard's set-up, with one command.
You finish the set-up in the terminal, or in a browser on a phone or another computer. It takes about 20 minutes.

## Before you begin

- Debian 13 or later, installed with no desktop. Download the **netinst** file for 64-bit PC (amd64) from
  [Debian's download page](https://www.debian.org/download), and follow
  [Debian's installation guide](https://www.debian.org/releases/trixie/installmanual), or read
  [Install Linux on a computer](install-linux.md). While installing:
  - leave the **root password** empty, so your own user can install software with `sudo`;
  - at **Software selection**, choose only **SSH server** and **standard system utilities**.
- A computer big enough for a media server:

  | | Minimum | Recommended |
  |---|---|---|
  | Processor | 64-bit, 2 cores | 4 cores; an Intel processor from 2018 or later converts video best |
  | Memory | 2 GB | 4 GB or more |
  | Disk for the system | 20 GB | An SSD of 64 GB or more |
  | Media | Space on the same disk | A separate drive of 1 TB or more |

- The user name and password you made while installing Debian.

## Steps

1. Sign in to Debian with a monitor and keyboard, or from your own computer with
   [Connect to your server from another computer](connect-with-ssh.md).
2. Check Debian is online, and connect it if not. A network cable is the most reliable. Read
   [Connect to the internet, by cable or Wi-Fi](connect-to-the-internet.md).
3. Type this command and press Enter. Debian includes `wget`, so this command uses it:

   ```bash
   wget -qO- https://raw.githubusercontent.com/TheMightyTRex/starboard/main/run-first.sh | bash
   ```

4. Press Enter at each question to take the recommended answer. When it asks for your password, type it and press
   Enter. Nothing shows as you type.
5. **Finish setting up:** press Enter for **Here in the terminal (recommended)**, and answer the set-up questions.
   Read [Set up Starboard in the terminal, with no browser](set-up-in-the-terminal.md). To use a browser instead,
   choose **In a browser**, then open the address it shows on a phone or another computer and type the setup code.

The Run first script installs git and Docker, which a new Debian does not have. Read
[Set up everything with the Run first script](run-first.md) for what each step does.

## If it does not work

- **"sudo: command not found" or "is not in the sudoers file":** a root password was set while installing, so your
  user cannot install software yet. Give it that right, with your user name in place of `sam`:

  ```bash
  su -
  ```

  Type the root password, then:

  ```bash
  apt install sudo && usermod -aG sudo sam
  ```

  Type `exit`, then sign out and back in, and run the command in step 3 again.
- **"Media change: please insert the disc labeled":** Debian still lists the installer's USB stick as a place to
  get software. Remove it from the list, then run the command in step 3 again:

  ```bash
  sudo sed -i '/cdrom/s/^deb/# deb/' /etc/apt/sources.list
  ```

- **"wget: command not found":** install it, then run the command in step 3 again:

  ```bash
  sudo apt update && sudo apt install wget
  ```

- **"Temporary failure in name resolution" or "Network is unreachable":** Debian is not online. Read
  [Connect to the internet, by cable or Wi-Fi](connect-to-the-internet.md).
- **"error: 404":** the address was typed with a difference. Copy and paste the command instead.

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
