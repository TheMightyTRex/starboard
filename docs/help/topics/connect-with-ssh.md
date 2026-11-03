[Help centre](../README.md) · Before you install · how-to

# Connect to your server from another computer

SSH (secure shell) lets you type commands on your server from your own computer, as if you were sitting at
it. You need it for a server with no screen, such as a Raspberry Pi. At the end, your terminal is connected to
the server and every command you type runs there.

## Before you begin

- The server is powered on and connected to your home network.
- SSH is activated for it. On a Raspberry Pi you did this in [Prepare a Raspberry Pi](prepare-a-raspberry-pi.md).
- You know the server's name (hostname) or address, and the user name and password you chose.

## Steps

1. Open a terminal on your own computer. On Windows 10 or 11, open **Terminal** or **PowerShell** from the
   Start menu. On a Mac, open **Terminal** from Applications, Utilities. On Linux, see
   [The terminal: typing commands](../basics/the-terminal.md).
2. Type this command, with your user name and the server's name in place of `sam` and `starboard-pi`, then
   press Enter:

   ```bash
   ssh sam@starboard-pi.local
   ```

3. The first time, SSH asks whether you trust this computer and shows a long code. Type `yes` and press
   Enter.
4. Type the server's password and press Enter. Nothing appears while you type: that is normal.

You are connected when the terminal shows the server's name before the cursor, such as
`sam@starboard-pi:~ $`.

To disconnect, type `exit` and press Enter. To connect again, repeat steps 1, 2 and 4.

## If it does not work

- **"Could not resolve hostname":** your computer cannot find the server by name. Use its address instead,
  for example `ssh sam@192.168.1.20`. Your router's settings page lists each device and its address.
- **"Connection refused" or it waits and gives up:** the server is still starting, or SSH is not activated.
  Wait a few minutes and try again.
- **"Permission denied":** the user name or password is wrong. Check them, including capital letters.

## Find out more

- [Addresses and ports](../basics/addresses-and-ports.md)
- [Install Starboard on a Raspberry Pi](../guides/install-on-a-raspberry-pi.md)
