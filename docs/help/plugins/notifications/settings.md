# Notifications: Settings
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Notifications' settings are on its own tab: go to **Settings**, then **Plug-ins**, then **Notifications**. Starboard draws them and keeps them; secrets are never shown again once saved.

## What to send

| Setting | What it does | Default |
|---|---|---|
| **Something someone asked for is ready** | Reelix's or Seerr's requests that become ready to watch. Activated or deactivated. | Activated |
| **Tell the person who asked too** | By the email address or Telegram chat given for them under People. Activated or deactivated. | Activated |
| **A download failed** | A download that stops with a problem. Activated or deactivated. | Activated |
| **An app stops answering, and when it is back** | After two checks in a row with no answer. Activated or deactivated. | Activated |
| **A disk is nearly full** | At the limit set for alerts in Settings, Alerts, or 90%. Activated or deactivated. | Activated |
| **An update is ready** | For Starboard, your apps and your plug-ins. Activated or deactivated. | Activated |
| **New this week** | Films, series and more that arrived in the last 7 days, once a week at 09:00. Activated or deactivated. | Activated |
| **Send New this week on** | The day New this week is sent, at 09:00. One of: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday. | Monday |
| **Starboard's address, for links** | Optional, such as http://192.0.2.10:8095. Messages end with Open Starboard and this address. A web address. | Empty |

## Email

| Setting | What it does | Default |
|---|---|---|
| **Send by email** | Activate once the details below are filled in and the test arrives. Activated or deactivated. | Deactivated |
| **Email server** | Such as smtp.example.com Words. | Empty |
| **Port** | A number from 1 to 65535. | 587 |
| **Security** | How the connection to your email server is protected. Your email service says which to use. One of: STARTTLS (usually port 587), SSL (usually port 465), None (only on your own network). | STARTTLS (usually port 587) |
| **User name** | Words. | Empty |
| **Password** | An app password where your email service offers one. Kept secret by Starboard: it is never shown again. | Empty |
| **Send from** | Such as starboard@example.com Words. | Empty |
| **Send email to** | One address a line. One a line. | Empty |

## Telegram

| Setting | What it does | Default |
|---|---|---|
| **Send by Telegram** | Activate once the details below are filled in and the test arrives. Activated or deactivated. | Deactivated |
| **Bot token** | From @BotFather in Telegram. Kept secret by Starboard: it is never shown again. | Empty |
| **Telegram chat** | One chat id a line. Send your bot a message first, so it may write to you. One a line. | Empty |

## Discord

| Setting | What it does | Default |
|---|---|---|
| **Send by Discord** | Activate once the webhook is filled in and the test arrives. Activated or deactivated. | Deactivated |
| **Discord webhook address** | In Discord: the channel's Edit channel, Integrations, Webhooks, Copy webhook URL. Kept secret by Starboard: it is never shown again. | Empty |

## Signal

| Setting | What it does | Default |
|---|---|---|
| **Send by Signal** | Only if you run signal-cli-rest-api, which sends for a number you registered with it. Activated or deactivated. | Deactivated |
| **signal-cli-rest-api address** | Such as http://192.0.2.10:8080 A web address. | Empty |
| **Send from number** | The number registered with it, such as +447700900123. Words. | Empty |
| **Send Signal messages to** | One number or group id a line. One a line. | Empty |

## Pushover

| Setting | What it does | Default |
|---|---|---|
| **Send by Pushover** | Activate once the keys below are filled in and the test arrives. Activated or deactivated. | Deactivated |
| **User key** | Kept secret by Starboard: it is never shown again. | Empty |
| **Application token** | Make an application for Starboard on pushover.net. Kept secret by Starboard: it is never shown again. | Empty |

## ntfy

| Setting | What it does | Default |
|---|---|---|
| **Send by ntfy** | Activate once the topic is filled in and the test arrives. Activated or deactivated. | Deactivated |
| **ntfy server** | A web address. | https://ntfy.sh |
| **Topic** | On ntfy.sh anyone who knows the topic can read it, so make it hard to guess. Words. | Empty |
| **Access token** | Optional, for a server or topic that needs one. Kept secret by Starboard: it is never shown again. | Empty |

## Webhooks

| Setting | What it does | Default |
|---|---|---|
| **Send to webhooks** | Activate once an address is filled in and the test arrives. Activated or deactivated. | Deactivated |
| **Webhook addresses** | One or more, separated by spaces. Each gets title, body and type as JSON, as the Apprise API's notify address takes them. Kept secret by Starboard: it is never shown again. | Empty |

## People

| Setting | What it does | Default |
|---|---|---|
| **People** | One person a line: the name they use in Reelix or Seerr, a comma, then their email address or telegram and their chat id. One a line. | Empty |

## Buttons

These are on Notifications' tab.

- **Send a test email**, **Send a test to Telegram**, **Send a test to Discord**, **Send a test by Signal**, **Send a test by Pushover**, **Send a test by ntfy** and **Send a test to the webhooks** each send "A test from Starboard" by that one channel, with the details saved, even before you activate it. Starboard says "Test sent by" and the channel, or "Test not sent" and why.
- **Send New this week now** sends New this week straight away, on any day, by every active channel. It says "Sending New this week now. The Notifications card says when it has gone". If nothing arrived in the last 7 days, nothing is sent.

## Things to note

- A setting you change is used for the next message; you do not need to deactivate it first.
- Fill in a channel's details, select its test button, and activate **Send by** that channel only once the test arrives.
- Each message goes by every active channel. One channel failing never stops the others.
- Under **People**, give one line for each person, such as `Sam, sam@example.com` or `Sam, telegram 123456`. The name must be the one they use in Reelix or Seerr. Only email and Telegram can tell a person.
- New this week is sent at 09:00 on the day you choose, once a week. A week with nothing new sends nothing.
- Passwords, tokens, keys and webhook addresses are secret: Starboard never shows them again, and the plug-in never writes them to its log, its cards or its folder.
- On ntfy.sh anyone who knows the topic can read it, so make the topic hard to guess.
- Signal works only if you already run signal-cli-rest-api with a number registered. Otherwise leave **Send by Signal** deactivated.
- Settings are kept when you update or deactivate it, and when you remove it they stay in its folder.

## Find out more

- [Install](../notifications/install.md)
- [Dashboard card](../notifications/dashboard-card.md)
- [Problems](../notifications/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
