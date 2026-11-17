# Outside services: Dashboard card
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Outside services adds 2 cards you can put on your dashboard, both called **Outside services**: one line for everything, or a list with each address. Each starts with a band: Outside services' logo and name and a status in words. A footer says when it last changed.

## Outside services, one line

Says whether everything answers. When something does not, it names what is not answering, such as "Not answering: Router, NAS".

- **How often it updates:** once a minute while the dashboard is open. The addresses themselves are checked at **Check every**, 5 minutes by default. Nothing is asked while the browser tab is hidden.
- **Example:** All 4 answer

## Outside services, the list

Shows each address by its name, with "Up" and how long it took to answer, or "Not answering". Each line links to its address. It shows up to 10 lines.

- **How often it updates:** once a minute while the dashboard is open. The addresses themselves are checked at **Check every**. Nothing is asked while the browser tab is hidden.
- **Example:**
  - Router: Up, 4 ms

## What the status says

Both cards say the same.

| Status | Means |
|---|---|
| **OK** | Every address answered at the last check. The time in the band is when that check ended. |
| **Waiting** | There are addresses, but the first check has not finished yet. The one-line card says "Not checked yet". |
| **Needs setting up** | **Addresses to check** is empty. The one-line card says "Add addresses in the plug-in's settings". |
| **Not answering** | Shown as **Problem**: at least one address did not answer at the last check. The card names each one. |

## Add it to your dashboard

1. Select **Edit dashboard**.
2. In **Add a card**, choose **Outside services (Outside services)**. There are two with this name, one for each card: add one, or both.
3. Select **Save**.

Outside services must be added and active first. Read [Install](../outside-services/install.md).

## Find out more

- [Use and change the dashboard, in Starboard's help](../../topics/use-the-dashboard.md)
- [Settings](../outside-services/settings.md)
- [Problems](../outside-services/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
