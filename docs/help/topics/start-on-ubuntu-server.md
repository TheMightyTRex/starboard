[Help centre](../README.md) · Before you install · how-to

# Start Starboard on Ubuntu Server

Ubuntu Server has no desktop and gets 5 years of security updates for each LTS release. This page takes you from
Ubuntu Server 26.04 LTS on a computer to Starboard's set-up, with one command. You finish the set-up in the
terminal, or in a browser on a phone or another computer. It takes about 20 minutes.

## Before you begin

- Ubuntu Server 26.04 LTS or later, installed on the computer that will be your server. Download it from
  [Ubuntu's server download page](https://ubuntu.com/download/server) and follow
  [Ubuntu's guide to installing Ubuntu Server](https://ubuntu.com/tutorials/install-ubuntu-server), or read
  [Install Linux on a computer](install-linux.md). While installing:
  - select **Install OpenSSH server**, so you can connect from your own computer;
  - at **Featured server snaps**, select nothing. Starboard installs Docker itself, and the Docker snap does not
    work with it.
- A computer big enough for a media server:

  | | Minimum | Recommended |
  |---|---|---|
  | Processor | 64-bit, 2 cores | 4 cores; an Intel processor from 2018 or later converts video best |
  | Memory | 3 GB | 8 GB |
  | Disk for the system | 20 GB | An SSD of 64 GB or more |
  | Media | Space on the same disk | A separate drive of 1 TB or more |

- The user name and password you made while installing Ubuntu.

## Steps

1. Sign in to Ubuntu with a monitor and keyboard, or from your own computer with
   [Connect to your server from another computer](connect-with-ssh.md).
2. Check Ubuntu is online, and connect it if not. Read
   [Connect to the internet, by cable or Wi-Fi](connect-to-the-internet.md).
3. Type this command and press Enter:

   ```bash
   curl -fsSL https://raw.githubusercontent.com/TheMightyTRex/starboard/main/run-first.sh | bash
   ```

4. Press Enter at each question to take the recommended answer. When it asks for your password, type it and press
   Enter. Nothing shows as you type.
5. **Finish setting up:** press Enter for **Here in the terminal (recommended)**, and answer the set-up questions.
   Read [Set up Starboard in the terminal, with no browser](set-up-in-the-terminal.md). To use a browser instead,
   choose **In a browser**, then open the address it shows on a phone or another computer and type the setup code.

Read [Set up everything with the Run first script](run-first.md) for what each step does.

## If it does not work

- **"Could not get lock" or "Waiting for cache lock":** Ubuntu installs security updates by itself in the first
  minutes after it starts. Wait 10 minutes, then select **Try again**.
- **"curl: (23) client returned ERROR on write", with a message about `curl.snap`:** curl was installed as a snap,
  which cannot save files where the script needs them. Install the usual curl, then run the command again:

  ```bash
  sudo apt install curl
  ```

- **Docker was selected under Featured server snaps while installing Ubuntu:** the Docker snap cannot reach your
  media folders. Remove it, then run the command in step 3 again. The script installs Docker the usual way:

  ```bash
  sudo snap remove docker
  ```

- **The disk is full, although the drive is much bigger:** Ubuntu's installer gives the system only part of the disk
  at first. Give it the rest:

  ```bash
  sudo lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv
  ```

- **A phone or another computer cannot open Starboard:** the firewall may be active. Allow Starboard's port:

  ```bash
  sudo ufw allow 8095/tcp
  ```

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
