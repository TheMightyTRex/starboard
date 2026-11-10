[Help centre](../README.md) · Before you install · how-to

# Start Starboard on Debian

Debian with no desktop is the lightest system for Starboard, so it suits an older or smaller computer. This page
takes you from Debian 13 on a computer to Starboard's set-up. You finish the set-up in the terminal, or in a
browser on a phone or another computer. It takes about 20 minutes.

## Before you begin

- Debian 13 or later on the computer that will be your server, installed with no desktop and an empty root
  password. To install it, follow [Install Linux on a computer](install-linux.md#steps).
- A computer with at least 2 cores, 2 GB of memory and 20 GB for the system. Read
  [The four systems](what-you-need.md#the-four-systems) for the recommended computer.
- The user name and password you made while installing Debian.

## Steps

1. Sign in to Debian with a monitor and keyboard, or from your own computer with
   [Connect to your server from another computer](connect-with-ssh.md).
2. Check that Debian is online. A network cable is the most reliable. Read
   [Check whether the server is online](connect-to-the-internet.md#check-whether-the-server-is-online).
3. Enter this command and press Enter. A new Debian has `wget` but not `curl`, so this command uses `wget`:

   ```bash
   wget -qO- https://raw.githubusercontent.com/TheMightyTRex/starboard/main/run-first.sh | bash
   ```

4. Press Enter at each question to take the recommended answer. When it asks for your password, enter it and press
   Enter. Nothing shows as you type.
5. At **How do you want to finish setting up?**, press Enter for **Here in the terminal (recommended)**. Read
   [Set up Starboard in the terminal, with no browser](set-up-in-the-terminal.md). To use a browser instead, choose
   **In a browser**, then open the address it shows on a phone or another computer and enter the setup code.

The Run first script installs git and Docker, which a new Debian does not have. Read
[Set up everything with the Run first script](run-first.md#steps) for what each step does.

## If it does not work

- **An error number, or "error: 404":** read [If it does not work](run-first.md#if-it-does-not-work) in the Run
  first article.
- **"sudo: command not found", "is not in the sudoers file" or error RF-16:** a root password was set while
  installing, so your user cannot install software yet. Give it that right, with your user name in place of `sam`:

  ```bash
  su -
  ```

  Enter the root password, then:

  ```bash
  apt install sudo && usermod -aG sudo sam
  ```

  Enter `exit`, sign out and back in, and run the command in step 3 again.
- **"Media change: please insert the disc labeled":** Debian still lists the installer's USB stick as a place to
  get software. Remove it from the list, then run the command in step 3 again:

  ```bash
  sudo sed -i '/cdrom/s/^deb/# deb/' /etc/apt/sources.list
  ```

- **"wget: command not found":** install it, then run the command in step 3 again:

  ```bash
  sudo apt update && sudo apt install wget
  ```

- **"Temporary failure in name resolution", "Network is unreachable" or error RF-11:** Debian is not online. Read
  [Connect to the internet, by cable or Wi-Fi](connect-to-the-internet.md).

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
