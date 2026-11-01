# Starboard

A fast, accessible dashboard for a home media server. It shows every app and whether it is running, searches
Sonarr, Radarr, Lidarr and Readarr at once and adds what you find, and lists downloads, what is coming up and
how the server is doing.

- **Every page has its own address:** `/index.html` (Apps), `/search.html`, `/downloads.html`,
  `/upcoming.html`, `/system.html`, `/settings.html`. Searches link too: `/search.html?q=dune`.
- **A fixed header on every page**, with search, the main menu (a Menu button on phones) and Display.
- **Five designs:** Health first (the default: apps that are not responding go to the top), Tiles, Shelf,
  Command and Status board. Change the default in Settings; anyone can pick their own in Display.
- **Display and accessibility:** theme (match device, light, dark), text size up to 175%, high contrast,
  reduce motion, underline links and wider text spacing. Built to WCAG 2.2 AA, with 44px controls and the
  Atkinson Hyperlegible Next typeface.
- **No third-party packages.** Python's standard library and plain HTML, CSS and JavaScript.

## Install

You need Docker with the Compose plugin (or Python 3.10+ and systemd for `--native`), and git.

```bash
git clone https://github.com/OWNER/starboard.git
cd starboard
./install.sh
```

The installer prints two addresses: one for this computer and one for phones and other computers on your
home network, plus a one-time setup code. Open either address, enter the code and choose a password (at least
10 characters). Then go to **Settings, Apps** and add your apps. Use `127.0.0.1` and each app's port (for
example `http://127.0.0.1:8989` for Sonarr) as the address the server uses.

### Home network or this computer only

**Settings, Security, Who can open the dashboard** switches between your home network (the default) and this
computer only. The change takes effect at once: Starboard stops listening on the network, so other devices
cannot connect at all. Install with `--local-only` to start that way. The Docker setup uses host networking
so this works (Docker on Linux).

### Free space on the System page

Mount each folder read-only in `compose.yaml` and name it in `.env`:

```yaml
    volumes:
      - /mnt/media:/disks/media:ro
```

```
STARBOARD_DISKS=Media=/disks/media
```

## Update

```bash
./update.sh
```

It backs up `./data` to `./backups`, installs the newest release, and goes back to the version you had (with
your settings restored) if the new one does not start. `./update.sh --check` only checks;
`./update.sh --to v0.1.0` installs a particular release, which is also how you go back.

## Security

- One password (at least 10 characters), hashed with PBKDF2-SHA256 (600,000 rounds). Without Remember me,
  you are signed out when the browser closes, or after a day. Five wrong attempts lock an address out for
  15 minutes. The first password needs the setup code from the installer.
- Sign-in cookies are `HttpOnly` and `SameSite=Strict`. Every change also needs a header only the dashboard's
  own pages send, and a matching `Origin`.
- API keys stay in `./data/config.json` (readable by you only) and are never sent to the browser.
- A strict Content Security Policy: no inline scripts, nothing loaded from other sites except cover images.
- The container runs as your user, read-only, with every Linux capability dropped. It does not need the
  Docker socket.
- Other devices on your home network can open it unless you switch that off in Settings. To use it away from home, put it behind a VPN or a reverse
  proxy with HTTPS (set `STARBOARD_TRUST_PROXY=1` and turn on HTTPS-only cookies in Settings). Do not forward
  the port straight to the internet.

See [SECURITY.md](SECURITY.md) to report a problem.

## Keep your details out of the repository

Settings, API keys, sessions and backups live in `./data`, `./backups` and `.env`, which git ignores. Before
contributing, run `tools/install-hooks.sh`: every commit is then checked for home network addresses, dynamic
DNS names, email addresses, keys and the words you list in `.private-words` (also ignored by git).

## Develop

```bash
STARBOARD_DATA=./data python3 -m starboard     # http://127.0.0.1:8095
python3 -m unittest discover -s tests
python3 tools/apply_shell.py                   # after changing the header or menu
```

The header and Display panel are written into every page by `tools/apply_shell.py`. Design tokens are in
`web/css/tokens.css`; the five designs in `web/css/designs.css`.

## Licence

MIT. Atkinson Hyperlegible Next is under the SIL Open Font Licence (`web/fonts/LICENSE-OFL.txt`).
