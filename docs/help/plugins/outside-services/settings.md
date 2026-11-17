# Outside services: Settings
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Outside services' settings are on its own tab: go to **Settings**, then **Plug-ins**, then **Outside services**. Starboard draws them and keeps them; secrets are never shown again once saved.

## Settings

| Setting | What it does | Default |
|---|---|---|
| **Addresses to check** | One each, such as http://192.0.2.1 or https://example.org. Give a name first if you like: Router http://192.0.2.1 One a line. | Empty |
| **Check every** | A number from 1 to 60 minutes. | 5 minutes |

Outside services has no buttons. Select **Save** to keep **Addresses to check**. **Check every** is saved when you leave the box.

## Things to note

- **Addresses to check:** the last word on each line is the address, and any words before it are its name on the cards, such as `Router http://192.0.2.1`. Without a name, the address is shown.
- It checks the first 20 addresses. The list card shows up to 10.
- **What counts as answering:** it opens each address and waits up to 8 seconds. Any answer counts, even a sign-in page or "not found", unless it is a server error (500 or higher).
- A change to **Addresses to check** is used at the next check.
- A change to **Check every** is used the next time Outside services starts. To use it now, select **Deactivate**, then **Activate**.
- Settings are kept when you update or deactivate it, and when you remove it they stay in its folder.

## Find out more

- [Install](../outside-services/install.md)
- [Dashboard card](../outside-services/dashboard-card.md)
- [Problems](../outside-services/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
