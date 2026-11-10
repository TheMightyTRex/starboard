[Help centre](../README.md) · Before you install · how-to

# Start Starboard on Ubuntu Server

Ubuntu Server has no desktop and gets 5 years of security updates for each LTS release. This page takes you from
Ubuntu Server 26.04 LTS on a computer to Starboard's set-up. You finish the set-up in the terminal, or in a browser
on a phone or another computer. It takes about 20 minutes.

## Before you begin

- Ubuntu Server 26.04 LTS or later on the computer that will be your server, installed with **Install OpenSSH
  server** selected and nothing under **Featured server snaps**. To install it, follow
  [Install Linux on a computer](install-linux.md#steps).
- A computer with at least 2 cores, 3 GB of memory and 20 GB for the system. Read
  [The four systems](what-you-need.md#the-four-systems) for the recommended computer.
- The user name and password you made while installing Ubuntu.

## Steps

1. Sign in to Ubuntu with a monitor and keyboard, or from your own computer with
   [Connect to your server from another computer](connect-with-ssh.md).
2. Check that Ubuntu is online. Read
   [Check whether the server is online](connect-to-the-internet.md#check-whether-the-server-is-online).
3. Enter this command and press Enter:

   ```bash
   curl -fsSL https://raw.githubusercontent.com/TheMightyTRex/starboard/main/run-first.sh | bash
   ```

4. Press Enter at each question to take the recommended answer. When it asks for your password, enter it and press
   Enter. Nothing shows as you type.
5. At **How do you want to finish setting up?**, press Enter for **Here in the terminal (recommended)**. Read
   [Set up Starboard in the terminal, with no browser](set-up-in-the-terminal.md). To use a browser instead, choose
   **In a browser**, then open the address it shows on a phone or another computer and enter the setup code.

Ubuntu installs security updates by itself in the first minutes after it starts. The script waits for them with a
progress bar, then carries on. Read [Set up everything with the Run first script](run-first.md#steps) for what each
step does.

## If it does not work

- **An error number, or "error: 404":** read [If it does not work](run-first.md#if-it-does-not-work) in the Run
  first article.
- **Error RF-12, or "Could not get lock":** Ubuntu's updates took more than 45 minutes. Read
  [RF-12](run-first-errors.md#rf-12).
- **Error RF-10, or "curl: (23)" with a message about `curl.snap`:** curl was installed as a snap, which cannot save
  files where the script needs them. Install the usual curl, then run the command in step 3 again:

  ```bash
  sudo apt install curl
  ```

- **Docker was selected under Featured server snaps while installing Ubuntu:** the Docker snap cannot reach your
  media folders. Remove it, then run the command in step 3 again. The script installs Docker the usual way:

  ```bash
  sudo snap remove docker
  ```

- **The disk is full, or error RF-14, although the drive is much bigger:** Ubuntu's installer gives the system only
  part of the disk at first. Give it the rest:

  ```bash
  sudo lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv
  ```

- **A phone or another computer cannot open Starboard:** the firewall may be active. Allow Starboard's port:

  ```bash
  sudo ufw allow 8095/tcp
  ```

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
