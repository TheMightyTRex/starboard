# Notifications: Dashboard card
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Notifications adds 2 cards you can put on your dashboard. Each starts with a band: Notifications' logo and name and a status in words. A footer says when it last changed.

## Notifications

Shows the last message it sent, when, and by which channels, such as "Mon 09:00, New this week: sent by Email, Telegram". Tests are not counted here.

- **How often it updates:** once an hour while the dashboard is open. Nothing is asked while the browser tab is hidden.
- **Example:** Mon 09:00, New this week: sent by Email, Telegram

## Notifications sent

Shows the last 10 messages, tests included, newest first. Each says when, and which channels sent it or did not and why. Before anything is sent, it says "Nothing sent yet".

- **How often it updates:** once an hour while the dashboard is open. Nothing is asked while the browser tab is hidden.
- **Example:**
  - Ready to watch: Dune (2021): Mon 12 Nov 20:15, sent by Email, Telegram

## What the status says

| Status | Means |
|---|---|
| **OK** | The last message went by every channel it tried. On **Notifications sent**, none of the last 10 failed. |
| **Ready** | A channel is active, but nothing has been sent yet. The card says "Ready to send by" and the channels. |
| **Warning** | Only on **Notifications sent**: some of the last 10 were not sent by a channel. The band says "Not sent", and the list says which. |
| **Needs setting up** | Shown as **No channel active** on the **Notifications** card. No channel is active: "No channel is active. Activate one in Settings, Plug-ins, Notifications." |
| **Problem** | Only on the **Notifications** card, shown as **Last one not sent**: the last message failed by a channel. The card says which and why, such as "Email: the email server refused the user name or password". |

## Add it to your dashboard

1. Select **Edit dashboard**.
2. In **Add a card**, choose the card. Its name ends with (Notifications), such as **Notifications (Notifications)**.
3. Select **Save**.

Notifications must be added and active first. Read [Install](../notifications/install.md).

## Find out more

- [Use and change the dashboard, in Starboard's help](../../topics/use-the-dashboard.md)
- [Settings](../notifications/settings.md)
- [Problems](../notifications/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
