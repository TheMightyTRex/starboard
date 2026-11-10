[Help centre](../README.md) · Before you install · how-to

# Start Starboard on Raspberry Pi OS

A Raspberry Pi 4 or 5 makes a small, quiet media server that uses little power. This page takes you from Raspberry
Pi OS (64-bit) on a Pi to Starboard's set-up. With the desktop version, the set-up opens in the Pi's browser. With
Lite, you finish it in the terminal or from a phone or another computer. It takes about 30 minutes.

## Before you begin

- Raspberry Pi OS (64-bit), the Trixie release or later, on the Pi's card or drive. To write it, follow
  [Prepare a Raspberry Pi](prepare-a-raspberry-pi.md#steps). Starboard's apps need the **64-bit** system.
- A Raspberry Pi 4 with 4 GB of memory or more, with the official power supply. A Raspberry Pi 5 with 8 GB,
  starting from an SSD, is recommended. Read
  [Raspberry Pi and other small devices](what-you-need.md#raspberry-pi-and-other-small-devices).
- The user name and password you chose in Raspberry Pi Imager.

## Steps

1. Connect the Pi to the internet. With a network cable, or with the Wi-Fi you set in Imager, it connects by
   itself. Otherwise read [Connect to the internet, by cable or Wi-Fi](connect-to-the-internet.md).
2. Open a terminal. On the desktop, select the **Terminal** icon. On Lite, sign in with a monitor and keyboard on
   the Pi, or from your own computer with [Connect to your server from another computer](connect-with-ssh.md).
3. Enter this command and press Enter:

   ```bash
   curl -fsSL https://raw.githubusercontent.com/TheMightyTRex/starboard/main/run-first.sh | bash
   ```

4. Press Enter at each question to take the recommended answer. When it asks for your password, enter it and press
   Enter. Nothing shows as you type.
5. At **How do you want to finish setting up?**:
   - **With the desktop:** press Enter for **In a browser (recommended)**. The Pi's browser opens Starboard's set-up
     page with the setup code filled in.
   - **With Lite, or over SSH:** press Enter for **Here in the terminal (recommended)**. Read
     [Set up Starboard in the terminal, with no browser](set-up-in-the-terminal.md).

Raspberry Pi OS installs updates in the first minutes after it starts. The script waits for them with a progress
bar, then carries on. Read [Set up everything with the Run first script](run-first.md#steps) for what each step
does.

## Things to note

- On a Pi with 1 GB of memory or less, choose the **Small server** preset when the set-up asks **How much it does**.
  Read [Make Starboard use less of your server](make-starboard-lighter.md).
- Keep media on a USB drive, not the microSD card. Cards wear out quickly with constant writing.

## If it does not work

- **An error number, or "error: 404":** read [If it does not work](run-first.md#if-it-does-not-work) in the Run
  first article.
- **Error RF-12, or "Could not get lock":** the updates took more than 45 minutes. Read
  [RF-12](run-first-errors.md#rf-12).
- **Apps will not start, and `uname -m` shows `armv7l` rather than `aarch64`:** the 32-bit system is installed.
  Write **Raspberry Pi OS (64-bit)** with Raspberry Pi Imager and start again.
- **Error RF-13, and the details say "is not signed" or "SHA1 is not considered secure":** the signing key of
  Raspberry Pi's own software source is older than Debian 13 allows. Enter
  `sudo apt install raspberrypi-archive-keyring`, then select **Try again**. If that fails too, write a newer
  Raspberry Pi OS with Raspberry Pi Imager.
- **The Pi restarts or slows down while Docker downloads, or a lightning bolt shows on the monitor:** the power
  supply is too weak. Use the official Raspberry Pi power supply, and give a USB drive its own power.
- **Downloads are very slow, or files go missing:** the microSD card is too slow or wearing out. Start the Pi from an
  SSD instead.
- **You cannot find the Pi on the network:** on the Pi, enter `hostname -I` for its address, or use the name you
  gave it in Imager, such as `starboard-pi.local`.

## Find out more

- [Prepare a Raspberry Pi](prepare-a-raspberry-pi.md)
- [Install Starboard on a Raspberry Pi](../guides/install-on-a-raspberry-pi.md)
- [What you need to run Starboard](what-you-need.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
