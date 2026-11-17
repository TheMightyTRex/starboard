# VPN check: Dashboard card
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

VPN check adds 1 card you can put on your dashboard. Each starts with a band: VPN check's logo and name and a status in words. A footer says when it last changed.

## VPN

Shows the public address and place your downloads come from through your VPN, and how long the answer took, such as "198.51.100.23 in Amsterdam, NL, 120 ms". It asks ipinfo.io, through the VPN, every 15 minutes or as often as **Check every** says.

- **How often it updates:** once a minute while the dashboard is open. Nothing is asked while the browser tab is hidden.
- **Example:** 198.51.100.23 in the Netherlands

## What the status says

| Status | Means |
|---|---|
| **Protected** | The last check worked through the VPN, and the address is not your home address. |
| **Waiting** | Shown as **Checking soon**. It has not checked yet. The card says "Not checked yet". |
| **Warning** | Shown as **No answer**. No check has worked for more than 3 times **Check every**. The card says "No answer through the VPN since" and the time of the last one that worked, then what went wrong. |
| **Problem** | Shown as **Home address showing** when the VPN shows the address in **Your home's public address**: "The VPN shows your home address, 203.0.113.7. Downloads are not hidden." Before its first check works, **Problem** with what went wrong. |

**When it last changed** is when the last check worked.

## Add it to your dashboard

1. Select **Edit dashboard**.
2. In **Add a card**, choose the card. Its name ends with (VPN check), such as **VPN (VPN check)**.
3. Select **Save**.

VPN check must be added and active first. Read [Install](../vpn-check/install.md).

## Find out more

- [Use and change the dashboard, in Starboard's help](../../topics/use-the-dashboard.md)
- [Settings](../vpn-check/settings.md)
- [Problems](../vpn-check/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
