[Help centre](../README.md) · Security · how-to

# Choose who can open Starboard

You can let phones and other computers on your home network open Starboard, or let only the server itself
open it. The change takes effect at once, and Starboard shows the addresses that work.

## Before you begin

- You can sign in to Starboard. If not, read [Create your password and sign in](create-your-password.md).
- If you want to turn access off, sign in on the server itself if you can, at `http://127.0.0.1:8095`.
  A phone or another computer loses access as soon as the switch goes off.

## Steps

1. Go to **Settings**, then **Security**.
2. Find **Who can open the dashboard**.
3. Set the **Phones and other computers on your home network** switch:
   - On: phones and other computers on your home network can reach the sign-in page.
   - Off: only the computer Starboard runs on can open it.
4. If you turned the switch off, Starboard asks **Turn off access from your home network?** Select
   **Turn off network access** to go ahead, or close the dialog to keep things as they are.

Starboard confirms the change. Under the switch it lists the addresses that open it now: **This computer**,
and, when the switch is on, the addresses for **Phones and other computers**. Each one has a button to copy
it.

## Things to note

- With the switch off, Starboard stops listening on your network. Other devices cannot connect at all, not
  even to the sign-in page.
- Home network access is on unless you chose otherwise when you installed. The installer's `--local-only`
  option starts Starboard with it off.
- If the page says **Set by STARBOARD_HOST on the server, so it cannot be changed here**, the address is
  fixed on the server by a setting called `STARBOARD_HOST`. Remove that setting from the server and restart
  Starboard to use the switch again.
- Live TV needs this switch on, because Jellyfin must be able to reach Starboard. Read
  [Set up free Live TV in Jellyfin](set-up-live-tv.md).
- This switch is about your home network only. To open Starboard away from home, read
  [Use Starboard away from home safely](../guides/use-starboard-away-from-home.md).

## If it does not work

- **You turned it off from a phone and now cannot get back in:** open Starboard on the server itself at
  `http://127.0.0.1:8095` and turn the switch back on.
- **The server has no monitor:** SSH (secure shell) can carry Starboard's port to your own computer. Read
  [Connect to your server from another computer](connect-with-ssh.md) first. Then run this command on your
  own computer, with your user name and the server's address in place of `sam` and `192.168.1.20`:

  ```bash
  ssh -L 8095:127.0.0.1:8095 sam@192.168.1.20
  ```

  While it stays connected, open `http://127.0.0.1:8095` in your own computer's browser. Starboard treats
  you as if you were on the server, so you can turn the switch back on. Type `exit` in the terminal when you
  have finished.

## Find out more

- [Open Starboard from a phone or another computer](open-from-another-device.md)
- [Starboard does not open](starboard-does-not-open.md)
- [Put Starboard behind a reverse proxy](reverse-proxy.md)
- [Addresses and ports](../basics/addresses-and-ports.md)
