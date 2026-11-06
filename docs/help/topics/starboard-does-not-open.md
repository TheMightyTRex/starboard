[Help centre](../README.md) · When something is wrong · troubleshooting

# Starboard does not open

If your browser cannot open Starboard, work through these checks in order. Most of the time Starboard is not
running, the address is wrong, or Starboard is set to open on the server only.

## Before you begin

- You can type commands on the server, at its keyboard or over SSH (secure shell). Read
  [The terminal: typing commands](../basics/the-terminal.md) and
  [Connect to your server from another computer](connect-with-ssh.md).

## Steps

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

3. Check the address. It is the server's address, a colon and the port, such as
   `http://192.168.1.20:8095`. It starts with `http`, not `https`, unless you set up a reverse proxy. On the
   server itself, use `http://127.0.0.1:8095`.
4. Check the port. Starboard uses port 8095 unless you chose another when you installed. The `.env` file in
   the Starboard folder shows it on the line `STARBOARD_PORT`.
5. Try on the server itself, at `http://127.0.0.1:8095`. If it opens there but not on a phone, carry on to
   the next step.
6. Check that other devices are allowed in. On the server, go to **Settings**, then **Security**, and check
   that **Phones and other computers on your home network** is active. If the server has no monitor,
   [Choose who can open Starboard](choose-who-can-open-starboard.md) explains how to reach the setting from
   your own computer.
7. Check the server's firewall. A firewall is a program that blocks connections the server has not allowed.
   On Ubuntu, Debian and Linux Mint, this command shows whether ufw (a common firewall) is on:

   ```bash
   sudo ufw status
   ```

   If it says "Status: active" and port 8095 is not listed, allow it:

   ```bash
   sudo ufw allow 8095/tcp
   ```

8. If it still does not open, read Starboard's own messages:

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
  access is inactive. Follow step 6 on the server.
- If the page says "Starboard does not answer to the name", you used a name Starboard does not know. Use the
  server's address, such as `http://192.168.1.20:8095`, or read
  [Put Starboard behind a reverse proxy](reverse-proxy.md).
- If you installed with the installer's `--native` option, Starboard runs without Docker. Instead of step 1,
  check it with this command:

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
