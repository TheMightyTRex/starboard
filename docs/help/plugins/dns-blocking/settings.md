# Ad blocking: Settings
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Ad blocking's settings are on its own tab: go to **Settings**, then **Plug-ins**, then **Ad blocking**. Starboard draws them and keeps them; secrets are never shown again once saved.

## Settings

| Setting | What it does | Default |
|---|---|---|
| **Which one** | One of: Pi-hole, AdGuard Home. | Pi-hole |
| **Its address** | Such as http://192.0.2.2 for Pi-hole, or http://192.0.2.2:3000 for AdGuard Home. A web address. | Empty |
| **User name** | AdGuard Home only. Words. | Empty |
| **Password** | Pi-hole's web password, or AdGuard Home's. Kept by Starboard. Kept secret by Starboard: it is never shown again. | Empty |

Ad blocking has no buttons. **Which one** is saved as soon as you choose it. The other settings are saved when you select **Save** in that section.

## Things to note

- A setting you change is used straight away, the next time the card asks; you do not need to deactivate it first.
- **Pi-hole:** Ad blocking uses the way Pi-hole 6 answers. It signs in with the password for each look at the numbers and signs out again straight after. **User name** is not used.
- **AdGuard Home:** it signs in with **User name** and **Password** each time it asks.
- It only reads the numbers. It never changes what Pi-hole or AdGuard Home blocks.
- Settings are kept when you update or deactivate it, and when you remove it they stay in its folder.

## Find out more

- [Install](../dns-blocking/install.md)
- [Dashboard card](../dns-blocking/dashboard-card.md)
- [Problems](../dns-blocking/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
