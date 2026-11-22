[Help centre](../README.md) · When something is wrong · troubleshooting
<!-- help: fix / starboard -->

# Starboard does not open

If your browser cannot open Starboard, find what happens on the chart, then follow its numbered answer. Most of the
time Starboard is not running, the address is wrong, or Starboard is set to open on the server only.

```flow
title: Find your answer
start: Starboard does not open in the browser
q: Is Starboard running? | docker compose ps says Up
  No, or you do not know -> 1
  Yes -> q2
q2: Does it open on the server, at 127.0.0.1:8095?
  No -> 2
  Yes, but not on a phone -> q3
q3: What does the phone or other computer show?
  Only the computer it runs on is allowed -> 3
  Nothing loads -> 4
1: Start Starboard #start-starboard
  Still does not open -> 5
2: Check the address and port #check-the-address-and-port
  Still does not open -> 5
3: Let other devices in #let-other-devices-in
4: Open the port in the firewall #open-the-port-in-the-firewall
  Still does not open -> 5
5: Read Starboard's own messages #read-starboards-own-messages
```

## Before you begin

- You can type commands on the server, at its keyboard or over SSH (secure shell). Read
  [The terminal: entering commands](../basics/the-terminal.md) and
  [Connect to your server from another computer](connect-with-ssh.md).

## Start Starboard

1. Check that Starboard is running. On the server, go to the Starboard folder:

   ```bash
   cd ~/starboard
   ```

   Then list its container:

   ```bash
   docker compose ps
   ```

   Starboard is running if the `starboard` line says "Up". If you installed from the ready-made image, use
   this command instead:

   ```bash
   docker compose -f compose.image.yaml ps
   ```

2. If it is not running, start it:

   ```bash
   docker compose up -d
   ```

   With the ready-made image, use this command instead:

   ```bash
   docker compose -f compose.image.yaml up -d
   ```

## Check the address and port

1. Check the address. It is the server's address, a colon and the port, such as
   `http://192.168.1.20:8095`. It starts with `http`, not `https`, unless you set up a reverse proxy. On the
   server itself, use `http://127.0.0.1:8095`.
2. Check the port. Starboard uses port 8095 unless you chose another when you installed. The `.env` file in
   the Starboard folder shows it on the line `STARBOARD_PORT`.
3. Try on the server itself, at `http://127.0.0.1:8095`. If it opens there but not on a phone, carry on with
   [Let other devices in](#let-other-devices-in).

## Let other devices in

On the server, go to **Settings**, then **Security**, and check that **Phones and other computers on your home
network** is active. If the server has no monitor, read
[Choose who can open Starboard](choose-who-can-open-starboard.md) to reach the setting from your own computer.

## Open the port in the firewall

A firewall is a program that blocks connections the server has not allowed. On Ubuntu, Debian and Linux Mint, this
command shows whether ufw, a common firewall, is active:

```bash
sudo ufw status
```

If it says "Status: active" and port 8095 is not listed, allow it:

```bash
sudo ufw allow 8095/tcp
```

## Read Starboard's own messages

If it still does not open, read Starboard's own messages:

```bash
docker compose logs starboard
```

With the ready-made image, use this command instead:

```bash
docker logs starboard
```

The last lines usually say what went wrong.

## Things to note

- The phone or computer must be on the same home network as the server. Mobile data and guest Wi-Fi networks
  cannot reach it.
- If the page says "This dashboard only accepts connections from the computer it runs on", home network
  access is inactive. Follow [Let other devices in](#let-other-devices-in) on the server.
- If the page says "Starboard does not answer to the name", you used a name Starboard does not know. Use the
  server's address, such as `http://192.168.1.20:8095`, or read
  [Put Starboard behind a reverse proxy](reverse-proxy.md).
- If you installed with the installer's `--native` option, Starboard runs without Docker. Instead of
  [Start Starboard](#start-starboard), check it with this command:

  ```bash
  systemctl --user status starboard
  ```

## If it does not work

Copy the last lines of `docker compose logs starboard` and open an issue, as described in
[Read the log and report a problem](read-the-log.md). Remove anything private before you post it.

## Find out more

- [Addresses and ports](../basics/addresses-and-ports.md)
- [Open Starboard from a phone or another computer](open-from-another-device.md)
- [What Docker is](../basics/what-is-docker.md)
- [Reset a forgotten password](reset-a-forgotten-password.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
