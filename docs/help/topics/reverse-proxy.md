[Help centre](../README.md) · Security · how-to

# Put Starboard behind a reverse proxy

A reverse proxy is a program that receives visits to your own web address over HTTPS and passes them on to
Starboard. This article shows the settings Starboard needs so it trusts the proxy and answers to your
address. At the end, Starboard opens at an address such as `https://starboard.example.com`.

This is for people who already run, or are ready to set up, a reverse proxy such as Caddy, nginx or Traefik.
If that is new to you, a VPN (virtual private network) is the simpler way to use Starboard away from home.
Read [Use Starboard away from home safely](../guides/use-starboard-away-from-home.md).

## Before you begin

- You have a domain name, and it points at your home internet connection.
- A reverse proxy runs on the server, or on another computer on your home network, and it gets HTTPS
  certificates for your domain.
- You can type commands on the server and edit a file there. Read
  [The terminal: typing commands](../basics/the-terminal.md).

## Steps

1. On the server, go to the Starboard folder and open the `.env` file in a text editor. For example:

   ```bash
   nano ~/starboard/.env
   ```

2. Find these lines and change them, with your own address in place of `starboard.example.com`:

   ```
   STARBOARD_TRUST_PROXY=1
   STARBOARD_ALLOWED_HOSTS=starboard.example.com
   ```

   `STARBOARD_TRUST_PROXY=1` tells Starboard to believe what the proxy says about the visitor and about
   HTTPS. `STARBOARD_ALLOWED_HOSTS` lists the names Starboard answers to, separated by commas.
3. If the proxy runs on another computer, or in its own Docker container, also add its address:

   ```
   STARBOARD_PROXY_ADDRESSES=192.168.1.21
   ```

   Starboard always trusts a proxy on the server itself, so leave this empty in that case.
4. Save the file. In nano, press Ctrl+O, then Enter, then Ctrl+X.
5. Start Starboard again so it reads the new settings. From the Starboard folder, run:

   ```bash
   docker compose up -d
   ```

   If you installed from the ready-made image, there is no `.env` file. Add the same settings to the
   `environment` list in `compose.image.yaml` instead, each on its own line starting with `- `. Then run
   this command from that folder:

   ```bash
   docker compose -f compose.image.yaml up -d
   ```

6. Point your reverse proxy at Starboard on port 8095. With Caddy on the same server, this is the whole
   entry in its Caddyfile:

   ```
   starboard.example.com {
       reverse_proxy 127.0.0.1:8095
   }
   ```

7. Open `https://starboard.example.com` and sign in.
8. When every address you use for Starboard starts with `https`, go to **Settings**, then **Security**. In
   **Sessions**, turn on **Only send the sign-in cookie over HTTPS**.

## Things to note

- Never forward Starboard's port, 8095, straight to the internet from your router. Only the reverse proxy
  should be reachable from outside, and only over HTTPS.
- With **Only send the sign-in cookie over HTTPS** on, you cannot sign in at a plain `http://` address, such
  as `http://192.168.1.20:8095`. Turn it off again if you still use one.
- Set `STARBOARD_TRUST_PROXY=1` only when a proxy sits in front of Starboard. Otherwise, leave it at `0`.
- To answer to every name under your domain, start the entry with a full stop, such as
  `STARBOARD_ALLOWED_HOSTS=.example.com`.
- Starboard needs home network access on if the proxy runs on another computer. Read
  [Choose who can open Starboard](choose-who-can-open-starboard.md).

## If it does not work

- **"Starboard does not answer to the name":** the address is missing from `STARBOARD_ALLOWED_HOSTS`. Add it
  exactly as it appears in the browser, without `https://`, then repeat step 5.
- **You sign in but are sent back to the sign-in page:** **Only send the sign-in cookie over HTTPS** is on
  and the address starts with `http`. Sign in at your `https` address instead, then turn the switch off if
  you still need the plain address.
- **A few wrong passwords lock everyone out, not just one device:** Starboard sees every visit as coming
  from the proxy, because it does not trust it yet. Add the proxy's address to `STARBOARD_PROXY_ADDRESSES`,
  then repeat step 5.

## Find out more

- [Use Starboard away from home safely](../guides/use-starboard-away-from-home.md)
- [Choose who can open Starboard](choose-who-can-open-starboard.md)
- [Addresses and ports](../basics/addresses-and-ports.md)
- [Read the log and report a problem](read-the-log.md)
