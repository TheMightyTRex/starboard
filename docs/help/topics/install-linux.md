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

Choose by how you will finish setting up Starboard:

| You will set up | Install | Why |
|---|---|---|
| In the terminal only, or from a phone or laptop | **Debian 13**, with no desktop | The lightest: it leaves the most memory for your apps, and is supported until 2030 |
| In a browser on the server itself | **Linux Mint 22** or **Ubuntu Desktop 24.04** | A desktop that looks familiar, with a browser |
| Either, on a Raspberry Pi | **Raspberry Pi OS Lite, 64-bit** | Follow [Prepare a Raspberry Pi](prepare-a-raspberry-pi.md) instead of this page |

A desktop uses 500 MB to 1.5 GB of memory even when nobody uses it. On a computer with 4 GB of memory or less,
choose Debian and finish set-up from a phone or laptop.

## Steps

1. On your other computer, download the installer file (it ends in `.iso`):
   - Debian 13: the **netinst** file for 64-bit PC (amd64) from [debian.org](https://www.debian.org/download).
   - Linux Mint 22: the **Cinnamon Edition** from [linuxmint.com](https://linuxmint.com/download.php).
   - Ubuntu Desktop 24.04 LTS from [ubuntu.com](https://ubuntu.com/download/desktop).
2. Write the file to the USB stick with [balenaEtcher](https://etcher.balena.io/): select **Flash from file**,
   choose the `.iso` file, choose the USB stick, then select **Flash**. On Windows, [Rufus](https://rufus.ie/)
   also works.
3. Put the USB stick and the network cable in the server computer and power it on. Straight away, press the key
   that opens the start-up menu, often F12, F11, F10 or Esc, and choose the USB stick. If the computer starts its
   old system instead, power it off and try another key.
4. Follow the installer. For Debian:
   - Choose **Install**, not Graphical install, if the mouse does not work.
   - When it asks for a **root password**, leave it empty and select **Continue**. Your own user then gets
     administrator rights through `sudo`, which Starboard's help expects.
   - Choose your user name and a password you will remember. The terminal asks for it later.
   - At **Software selection**, deselect **Debian desktop environment** and **GNOME**, and select only **SSH
     server** and **standard system utilities**. Press the space bar to select or deselect, and Enter to go on.
5. For Linux Mint or Ubuntu Desktop, choose **Install**, then **Erase disk and install**, and choose your user
   name and password. Accept the other suggested answers.
6. When the installer says it has finished, remove the USB stick and let the computer restart.
7. Sign in with your user name and password. On Debian, you see a line ending in `$`: that is the terminal,
   ready for commands.
8. Install the updates that came out after your installer file. It asks for your password:

   ```bash
   sudo apt update && sudo apt upgrade
   ```

   When it asks "Do you want to continue?", type `y` and press Enter.

9. Write down the computer's address on your network, to connect from another computer later:

   ```bash
   hostname -I
   ```

   The first group of four numbers, such as `192.168.1.20`, is its address.

## Things to note

- Give the server the same address every time, so your bookmarks keep working. Most home routers call this an
  address reservation or a static lease.
- After this, Debian needs no monitor or keyboard: connect from your own computer with
  [Connect to your server from another computer](connect-with-ssh.md).
- Avoid Windows for a server: Windows 10 no longer gets security updates, and Docker on Windows runs inside a
  virtual machine that takes extra memory. Read [Can I use Windows or a Mac?](windows-and-mac.md)

## If it does not work

- **The computer never shows the USB stick:** write the stick again, or try another USB port. On some computers,
  the start-up menu only lists the stick after you activate **USB boot** in the computer's own settings, opened
  with F2 or Delete at start-up.
- **"Secure Boot violation" or a similar message:** Debian, Mint and Ubuntu all work with Secure Boot. Write the
  stick again from a freshly downloaded file. If it still happens, deactivate Secure Boot in the computer's own
  settings.
- **Debian finds no network:** check the cable. Debian does not set up Wi-Fi without extra files, and a cable is
  more reliable for a server anyway.
- **"sudo: command not found" or "is not in the sudoers file" on Debian:** you set a root password in Step 4.
  Install Linux again and leave the root password empty.

## Find out more

- [Install Docker](install-docker.md)
- [Connect to your server from another computer](connect-with-ssh.md)
- [The terminal: typing commands](../basics/the-terminal.md)
- [Get Starboard up and running, from a bare computer](../guides/get-up-and-running.md)
