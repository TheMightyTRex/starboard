[Help centre](../README.md) · Before you install · how-to

# Connect to the internet from the terminal

Check that your server is online, and connect it by network cable or Wi-Fi, by typing commands in its terminal. You
need this on a server with no desktop, where there is no network icon to select. At the end, the server can reach the
internet and you are ready to run the Run first script.

## Before you begin

- Linux is installed on the server. Read [Install Linux on a computer](install-linux.md).
- A terminal open on the server itself, with a monitor and keyboard. Read
  [The terminal: typing commands](../basics/the-terminal.md).
- For Wi-Fi: your Wi-Fi network's name and password.
- Some commands below have quotes `"` and other symbols in them. If a symbol is not where you expect on your
  keyboard, read
  [Symbols that are in different places on different keyboards](../basics/the-terminal.md#symbols-that-are-in-different-places-on-different-keyboards).

## Check whether the server is online

1. Type this command and press Enter:

   ```bash
   ping -c 3 debian.org
   ```

2. Read what it prints:
   - **Lines that end in a time, such as `time=14.2 ms`, and "0% packet loss":** the server is online. You do not need
     the rest of this page.
   - **"Temporary failure in name resolution" or "Network is unreachable":** the server is not online. Carry on
     below.

## Connect with a network cable (recommended)

A cable is faster and more reliable than Wi-Fi for a server.

1. Plug the cable into the server and into your router.
2. Wait 10 seconds, then check again with the `ping` command above. Most systems connect a cable by themselves.
3. **Debian with no desktop, if it is still not online:** Debian sets up only the network it saw while it was being
   installed. List the server's network connections:

   ```bash
   ip -br link
   ```

   The cable's connection has a name such as `enp3s0` or `eno1`: not `lo`, and not a name starting with `wl`, which
   is Wi-Fi.
4. Add it to Debian's network settings, with your connection's name in place of `enp3s0` in both places. It asks for
   your password:

   ```bash
   printf 'allow-hotplug enp3s0\niface enp3s0 inet dhcp\n' | sudo tee -a /etc/network/interfaces
   ```

5. Start it, again with your connection's name:

   ```bash
   sudo ifup enp3s0
   ```

6. Check again with the `ping` command above.

## Connect with Wi-Fi on Linux Mint, Ubuntu Desktop, Fedora or Raspberry Pi OS

These use a program called NetworkManager, which you control with the `nmcli` command.

1. List the Wi-Fi networks the server can see:

   ```bash
   nmcli device wifi list
   ```

2. Connect to yours, with its name in place of `My network`. Keep the quotes:

   ```bash
   nmcli --ask device wifi connect "My network"
   ```

3. When it asks for the password, type it and press Enter. Nothing shows as you type.
4. Check again with the `ping` command above. The server connects by itself every time it starts.

## Connect with Wi-Fi on Ubuntu Server

Ubuntu Server keeps its network settings in a file. If you set up Wi-Fi while installing Ubuntu, it is set up
already.

1. Find the Wi-Fi connection's name. It starts with `wl`, such as `wlan0` or `wlp2s0`:

   ```bash
   ip -br link
   ```

2. Open a new settings file. It asks for your password:

   ```bash
   sudo nano /etc/netplan/60-wifi.yaml
   ```

3. Type these lines, with your connection's name, your network's name and its password in place of `wlan0`,
   `My network` and `my-wifi-password`. The spaces at the start of each line matter: use spaces, not Tab:

   ```text
   network:
     version: 2
     wifis:
       wlan0:
         dhcp4: true
         access-points:
           "My network":
             password: "my-wifi-password"
   ```

4. Save the file: press **Ctrl** and **O**, then **Enter**, then **Ctrl** and **X** to close it.
5. Keep the password private to the administrator, then apply the settings:

   ```bash
   sudo chmod 600 /etc/netplan/60-wifi.yaml
   ```

   ```bash
   sudo netplan apply
   ```

6. Check again with the `ping` command above.

## Wi-Fi on Debian with no desktop

A minimal Debian has no Wi-Fi tools unless you set up Wi-Fi while installing it. Connect a network cable for now, as
above, then install NetworkManager:

```bash
sudo apt install network-manager
```

After that, the Wi-Fi steps for Linux Mint and the others work on Debian too. Keep the cable plugged in until Wi-Fi
works.

## Things to note

- For a server, a network cable is better: Wi-Fi is slower, drops out more often, and can slow down films that are
  playing on other devices.
- Give the server the same address every time, so your bookmarks keep working. Most routers call this an address
  reservation or a static lease.

## If it does not work

- **`ping` works with `1.1.1.1` but not with `debian.org`:** the server is online but cannot look up names. Restart
  it and try again; if it still fails, check the DNS setting on your router.
- **`nmcli: command not found`:** this Linux does not use NetworkManager. Use the steps for your Linux above.
- **"No Wi-Fi device found" or no name starting with `wl`:** the server has no Wi-Fi, or its Wi-Fi needs extra files.
  Use a network cable.
- **"Error: Connection activation failed: Secrets were required":** the password was not right. Run the connect
  command again and type it carefully.

## Find out more

- [Install Linux on a computer](install-linux.md)
- [Set up everything with the Run first script](run-first.md)
- [Connect to your server from another computer](connect-with-ssh.md)
- [Get Starboard up and running, from a bare computer](../guides/get-up-and-running.md)
