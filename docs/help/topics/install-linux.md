[Help centre](../README.md) · Before you install · how-to

# Install Linux on a computer

Put Linux on the computer that will be your server, from a USB stick. At the end the computer starts Linux by
itself and you can sign in with your own user name and password. It takes about 45 minutes, most of it waiting.

## Before you begin

- The computer you will use as the server, big enough for what you want. Read
  [What you need to run Starboard](what-you-need.md).
- A USB stick of 8 GB or more. Everything on it is erased.
- Another computer to download Linux and write the USB stick.
- A monitor, keyboard and network cable for the server, for this hour only.
- Anything you want to keep from the server computer, copied somewhere else. Installing Linux erases its disk.

## Choose which Linux

Starboard supports four systems, in the version named here or any later one. Choose by how you will use the server:

| You want | Install | Why |
|---|---|---|
| A screen on the server, and the set-up in its browser | **Linux Mint 22.3 (recommended)** | A desktop that looks familiar; the set-up opens in its browser by itself |
| No screen: the set-up in the terminal, or from a phone or laptop | **Debian 13** | The lightest: it leaves the most memory for your apps |
| No screen, with 5 years of updates | **Ubuntu Server 26.04 LTS** | Long support, and many guides online |
| A Raspberry Pi | **Raspberry Pi OS (64-bit)** | Follow [Prepare a Raspberry Pi](prepare-a-raspberry-pi.md) instead of this page |

A desktop uses 500 MB to 1.5 GB of memory even when nobody uses it. On a computer with 4 GB of memory or less,
choose Debian and finish set-up from a phone or laptop. Read [The four systems](what-you-need.md#the-four-systems)
for the minimum and recommended computer for each.

## Steps

1. On your other computer, download the installer file (it ends in `.iso`):
   - Linux Mint 22.3: the **Cinnamon Edition** from [linuxmint.com](https://linuxmint.com/download.php).
     [Linux Mint's installation guide](https://linuxmint-installation-guide.readthedocs.io/en/latest/) shows
     every step with pictures.
   - Debian 13: the **netinst** file for 64-bit PC (amd64) from [debian.org](https://www.debian.org/download).
     [Debian's installation guide](https://www.debian.org/releases/trixie/installmanual) explains every question.
   - Ubuntu Server 26.04 LTS from [ubuntu.com](https://ubuntu.com/download/server).
     [Ubuntu's guide to installing Ubuntu Server](https://ubuntu.com/tutorials/install-ubuntu-server) shows every
     step.
2. Write the file to the USB stick with [balenaEtcher](https://etcher.balena.io/): select **Flash from file**,
   choose the `.iso` file, choose the USB stick, then select **Flash**. On Windows, [Rufus](https://rufus.ie/)
   also works.
3. Put the USB stick and the network cable in the server computer and power it on. Straight away, press the key
   that opens the start-up menu, often F12, F11, F10 or Esc, and choose the USB stick. If the computer starts its
   old system instead, power it off and try another key.
4. Follow the installer. For Debian:
   - Choose **Install**, not Graphical install, if the mouse does not work.
   - When it asks for a **root password**, leave it empty and select **Continue**. Your own user then gets
     administrator rights through `sudo`.
   - Choose your user name and a password you will remember. The terminal asks for it later.
   - At **Software selection**, deselect **Debian desktop environment** and **GNOME**, and select only **SSH
     server** and **standard system utilities**. Press the space bar to select or deselect, and Enter to go on.
5. For Linux Mint, choose **Install Linux Mint**, then **Erase disk and install Linux Mint**, and choose your user
   name and password. Accept the other suggested answers.
   For Ubuntu Server, select **Install OpenSSH server**, select nothing under **Featured server snaps**, and choose
   your user name and password. Accept the other suggested answers.
6. When the installer says it has finished, remove the USB stick and let the computer restart.
7. Sign in with your user name and password. On Debian and Ubuntu Server, a line ending in `$` appears: that is
   the terminal, ready for commands. On Linux Mint, open a terminal from **Menu**, **Terminal**.
8. Install the updates that came out after your installer file. It asks for your password:

   ```bash
   sudo apt update && sudo apt upgrade
   ```

   When it asks "Do you want to continue?", enter `y` and press Enter.

9. Write down the computer's address on your network, to connect from another computer later:

   ```bash
   hostname -I
   ```

   The first group of four numbers, such as `192.168.1.20`, is its address.

## Things to note

- Give the server the same address every time, so your bookmarks keep working. Most home routers call this an
  address reservation or a static lease.
- After this, Debian and Ubuntu Server need no monitor or keyboard: connect from your own computer with
  [Connect to your server from another computer](connect-with-ssh.md).
- Next, start Starboard with the page for your system: [Start Starboard on Linux Mint](start-on-linux-mint.md),
  [on Debian](start-on-debian.md) or [on Ubuntu Server](start-on-ubuntu-server.md).
- Avoid Windows for a server: Windows 10 no longer gets security updates, and Docker on Windows runs inside a
  virtual machine that takes extra memory. Read [Can I use Windows or a Mac?](windows-and-mac.md)

## If it does not work

- **The computer never shows the USB stick:** write the stick again, or try another USB port. On some computers,
  the start-up menu only lists the stick after you activate **USB boot** in the computer's own settings, opened
  with F2 or Delete at start-up.
- **"Secure Boot violation" or a similar message:** Linux Mint, Debian and Ubuntu all work with Secure Boot. Write the
  stick again from a freshly downloaded file. If it still happens, deactivate Secure Boot in the computer's own
  settings.
- **The server is not online after installing:** follow
  [Connect to the internet, by cable or Wi-Fi](connect-to-the-internet.md).
- **Debian finds no network:** check the cable. Debian does not set up Wi-Fi without extra files, and a cable is
  more reliable for a server anyway.
- **"sudo: command not found" or "is not in the sudoers file" on Debian:** you set a root password in step 4.
  Give your user the right to use `sudo` with
  [If it does not work](start-on-debian.md#if-it-does-not-work) in Start Starboard on Debian, or install Linux
  again and leave the root password empty.

## Find out more

- [Connect to the internet, by cable or Wi-Fi](connect-to-the-internet.md)
- [Connect to your server from another computer](connect-with-ssh.md)
- [The terminal: typing commands](../basics/the-terminal.md)
- [Set up everything with the Run first script](run-first.md)
- [Get Starboard up and running, from a bare computer](../guides/get-up-and-running.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
