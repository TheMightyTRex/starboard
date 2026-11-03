[Help centre](../README.md) · Before you install · how-to

# Prepare a Raspberry Pi

Raspberry Pi Imager writes Raspberry Pi OS onto a microSD card and sets it up so that you can reach the Pi
from your own computer, with no screen or keyboard on the Pi. At the end, the Pi starts on your home network,
ready for [Connect to your server from another computer](connect-with-ssh.md).

## Before you begin

- A microSD card of 16 GB or more, and a computer with a card reader. Everything on the card is erased.
- The name and password of your Wi-Fi, unless the Pi will use a network cable.
- Check your Pi is big enough in [What you need to run Starboard](what-you-need.md).

## Steps

1. On your computer, download and install Raspberry Pi Imager from raspberrypi.com/software (opens the
   Raspberry Pi website).
2. Put the microSD card in your computer and open Raspberry Pi Imager.
3. For the device, choose your Raspberry Pi model.
4. For the operating system, choose **Raspberry Pi OS (64-bit)**. On a Pi 3 or Zero 2 W you can choose
   **Raspberry Pi OS Lite (64-bit)** from **Raspberry Pi OS (other)**: it has no desktop, which leaves more
   memory for your apps.
5. For the storage, choose your microSD card. Check it is the card, not another drive.
6. When Imager asks whether to apply OS customisation settings, choose **Edit settings**.
7. Fill in the settings:
   - **Hostname:** a short name for the Pi, such as `starboard-pi`. You use it to find the Pi later.
   - **Username and password:** the account you sign in to the Pi with. Write the password down somewhere
     safe.
   - **Wireless LAN:** your Wi-Fi name and password, and your country. Leave it empty if you use a cable.
   - On the **Services** tab, turn on **Enable SSH** and choose **Use password authentication**.
8. Save the settings, choose **Yes** to apply them, and confirm that the card may be erased.
9. When Imager says it has finished, take the card out, put it in the Pi and connect the power.

The Pi takes a few minutes to start the first time. It is ready when its green light stops flashing
steadily.

## Things to note

- Imager's labels change between versions. If a label here is not on your copy, look for the same idea:
  the device, the system, the card, then the customisation settings.
- A network cable is more reliable than Wi-Fi for a server, and faster for media.

## Find out more

- [Connect to your server from another computer](connect-with-ssh.md)
- [Install Starboard on a Raspberry Pi](../guides/install-on-a-raspberry-pi.md)
- [What a home server is](../basics/what-is-a-home-server.md)
