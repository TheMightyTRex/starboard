# Remote access: Dashboard card
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Remote access adds 1 card you can put on your dashboard. It starts with a band: Remote access's logo and name and a status in words. A footer says when the connection last changed.

## Away from home

When it is connected, it shows the address to use away from home and the way it connects, such as `Away from home: http://<its Tailscale address>:8095 (Tailscale)`. The address is Starboard's, or Jellyfin's when Starboard is not shared. When it is not connected, it says what to do next.

- **How often it updates:** once a minute while the dashboard is open. Remote access itself checks the connection every 10 seconds. Nothing is asked while the browser tab is hidden.
- **Example:** `Away from home: http://<its Tailscale address>:8095 (Tailscale)`

## What the status says

| Status | Means |
|---|---|
| **Connected** | Tailscale or Cloudflare Tunnel is connected, and the card shows the address to use. |
| **Connecting** | Tailscale or Cloudflare Tunnel is starting. |
| **Needs setting up** | **Connect with** is **Nothing yet**. The card says "Not set up: choose Tailscale or Cloudflare Tunnel in its settings". |
| **Needs signing in** | Tailscale is waiting for you to open the sign-in link, shown in **Addresses away from home**. |
| **Needs approving** | Tailscale is waiting for you to approve this computer in Tailscale's admin page, **Machines**. |
| **No apps shared** | Cloudflare Tunnel is connected, but the tunnel has no routes yet. Add a public hostname in Cloudflare's dashboard. |
| **Not connected** | A key or token is missing, wrong or refused, Tailscale or Cloudflare cannot be reached, or it stopped the tunnel to keep your apps safe. The card says which. |

## Add it to your dashboard

1. Select **Edit dashboard**.
2. In **Add a card**, choose **Away from home (Remote access)**.
3. Select **Save**.

Remote access must be added and active first. Read [Install](../remote-access/install.md).

## Find out more

- [Use and change the dashboard, in Starboard's help](../../topics/use-the-dashboard.md)
- [Settings](../remote-access/settings.md)
- [Problems](../remote-access/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
