[Help centre](../README.md) · Before you install · how-to

# Start Starboard on Raspberry Pi OS

A Raspberry Pi 4 or 5 makes a small, quiet media server that uses little power. This page takes you from Raspberry
Pi OS (64-bit) on a Pi to Starboard's set-up, with one command. With the desktop version, the set-up opens in the
Pi's browser; with Lite, you finish it in the terminal or from a phone or another computer. It takes about 30
minutes.

## Before you begin

- Raspberry Pi OS (64-bit), the Trixie release or later. Write it to a card or drive with
  [Raspberry Pi Imager](https://www.raspberrypi.com/software/), following
  [Raspberry Pi's getting started guide](https://www.raspberrypi.com/documentation/computers/getting-started.html)
  or [Prepare a Raspberry Pi](prepare-a-raspberry-pi.md). Choose a **64-bit** system: Starboard's apps need it.
- A Raspberry Pi big enough for a media server:

  | | Minimum | Recommended |
  |---|---|---|
  | Raspberry Pi | Raspberry Pi 4 with 4 GB of memory | Raspberry Pi 5 with 8 GB of memory |
  | Start-up drive | A microSD card of 32 GB | A USB or NVMe SSD, which lasts much longer than a card |
  | Media | A USB drive | A USB drive of 1 TB or more, with its own power |
  | Power | The official Raspberry Pi power supply | The same |

  A Raspberry Pi 3 or Zero 2 W runs Starboard on its own, but not a whole media server.
- The user name and password you chose in Raspberry Pi Imager.

## Steps

1. Connect the Pi to the internet. With a network cable, or with the Wi-Fi you set in Imager, it connects by itself.
   Otherwise, on the desktop select the network icon and choose your network; on Lite, read
   [Connect to the internet, by cable or Wi-Fi](connect-to-the-internet.md).
2. Open a terminal. On the desktop, select the **Terminal** icon. On Lite, sign in with a monitor and keyboard on the Pi, or from
   your own computer with [Connect to your server from another computer](connect-with-ssh.md).
3. Type this command and press Enter:

   ```bash
   curl -fsSL https://raw.githubusercontent.com/TheMightyTRex/starboard/main/run-first.sh | bash
   ```

4. Press Enter at each question to take the recommended answer. When it asks for your password, type it and press
   Enter. Nothing shows as you type.
5. **Finish setting up:**
   - **With the desktop:** press Enter for **In a browser (recommended)**. The Pi's browser opens Starboard's set-up
     page with the setup code filled in.
   - **With Lite, or over SSH:** press Enter for **Here in the terminal (recommended)**. Read
     [Set up Starboard in the terminal, with no browser](set-up-in-the-terminal.md).

## Things to note

- On a Pi with 2 GB of memory or less, choose the **Small server** preset when the set-up asks
  **How much Starboard does**. Read [Make Starboard use less of your server](make-starboard-lighter.md).
- Keep media on a USB drive, not the microSD card. Cards wear out quickly with constant writing.

## If it does not work

- **Apps will not start, and `uname -m` shows `armv7l` rather than `aarch64`:** the 32-bit system is installed.
  Write **Raspberry Pi OS (64-bit)** with Raspberry Pi Imager and start again.
- **"Could not get lock" or "Waiting for cache lock":** Raspberry Pi OS installs updates in the first minutes after
  it starts. Wait 10 minutes, then select **Try again**.
- **"Updating the list of software did not finish", and the details say "is not signed" or "SHA1 is not considered
  secure":** the signing key of Raspberry Pi's own software source is older than the checks in Debian 13 allow. Type
  `sudo apt install raspberrypi-archive-keyring`. If that fails too, write a newer Raspberry Pi OS with Raspberry Pi
  Imager. Then select **Try again**.
- **The Pi restarts or slows down while Docker downloads, or a lightning bolt shows on the monitor:** the power
  supply is too weak. Use the official Raspberry Pi power supply, and give a USB drive its own power.
- **Downloads are very slow, or files go missing:** the microSD card is too slow or wearing out. Start the Pi from an
  SSD instead.
- **You cannot find the Pi on the network:** on the Pi, type `hostname -I` for its address, or use the name you gave
  it in Imager, such as `starboard-pi.local`.
- **"error: 404":** the address was typed with a difference. Copy and paste the command instead.

## Find out more

- [Prepare a Raspberry Pi](prepare-a-raspberry-pi.md)
- [Install Starboard on a Raspberry Pi](../guides/install-on-a-raspberry-pi.md)
- [What you need to run Starboard](what-you-need.md)
