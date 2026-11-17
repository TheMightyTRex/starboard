# Notifications
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Sends Starboard's events to email, Telegram, Discord, Signal, Pushover, ntfy or a webhook, in plain words, and a weekly New this week.

An example Starboard plug-in by TheMightyTRexUK, MIT licence.

## What it may do

- It reads your apps and whether they answer.
- It reads what is downloading.
- It reads your library.
- It reads processor, memory and disk use.
- It reaches your home network and the internet.
- It runs one small container (48 MB of memory at most).

## On the dashboard

- **Notifications**: a status card.
- **Notifications sent**: a list card.

## What wakes it

Starboard sends it these events: `request.available`, `download.failed`, `app.down`, `app.up`, `disk.nearly_full`, `update.available`, `item.added`.
Starboard runs its job **Send New this week on the chosen day** daily at 09:00.

## Settings

### What to send

- **Something someone asked for is ready**: Reelix's or Seerr's requests that become ready to watch.
- **Tell the person who asked too**: By the email address or Telegram chat given for them under People.
- **A download failed**: A download that stops with a problem.
- **An app stops answering, and when it is back**: After two checks in a row with no answer.
- **A disk is nearly full**: At the limit set for alerts in Settings, Alerts, or 90%.
- **An update is ready**: For Starboard, your apps and your plug-ins.
- **New this week**: Films, series and more that arrived in the last 7 days, once a week at 09:00.
- **Send New this week on**: The day New this week is sent, at 09:00.
- **Starboard's address, for links**: Optional, such as http://192.0.2.10:8095. Messages end with Open Starboard and this address.

### Email

- **Send by email**: Activate once the email details are entered and the test arrives.
- **Email server**: Such as smtp.example.com
- **Port**
- **Security**: How the connection to your email server is protected. Your email service says which to use.
- **User name**
- **Password**: An app password where your email service offers one.
- **Send from**: Such as starboard@example.com
- **Send email to**: One address a line.

### Telegram

- **Send by Telegram**: Activate once the bot token and chat are entered and the test arrives.
- **Bot token**: From @BotFather in Telegram.
- **Telegram chat**: One chat id a line. Send your bot a message first, so it may write to you.

### Discord

- **Send by Discord**: Activate once the webhook is filled in and the test arrives.
- **Discord webhook address**: In Discord: the channel's Edit channel, Integrations, Webhooks, Copy webhook URL.

### Signal

- **Send by Signal**: Only if you run signal-cli-rest-api, which sends for a number you registered with it.
- **signal-cli-rest-api address**: Such as http://192.0.2.10:8080
- **Send from number**: The number registered with it, such as +447700900123.
- **Send Signal messages to**: One number or group id a line.

### Pushover

- **Send by Pushover**: Activate once both keys are entered and the test arrives.
- **User key**
- **Application token**: Make an application for Starboard on pushover.net.

### ntfy

- **Send by ntfy**: Activate once the topic is filled in and the test arrives.
- **ntfy server**
- **Topic**: On ntfy.sh anyone who knows the topic can read it, so make it hard to guess.
- **Access token**: Optional, for a server or topic that needs one.

### Webhooks

- **Send to webhooks**: Activate once an address is filled in and the test arrives.
- **Webhook addresses**: One or more, separated by spaces. Each gets title, body and type as JSON, as the Apprise API's notify address takes them.

### People

- **People**: One person a line: the name they use in Reelix or Seerr, a comma, then their email address, or "telegram" and their chat id.

## How it stays light

It has no timer of its own. Starboard sends it each event and runs its daily job, and it rests (stops) 5 minutes after
the last one. A message takes about a second and 14 MB of memory while it runs.

## Secrets

Passwords, tokens, keys and the webhook addresses are secret settings: Starboard never shows them again, and the
plug-in never writes them to its log, its card or its folder. A failed message says only which channel failed and why,
in words such as "it refused the sign-in or token".

## Per person

Under **People**, give one line for each person who asks for things: the name they use in Reelix or Seerr, a comma,
then their email address, or `telegram` and their chat id. When their request is ready, they hear too.

## Signal

Signal has no official way for a server to send messages. If you already run
[signal-cli-rest-api](https://github.com/bbernhard/signal-cli-rest-api) with a number registered, give its address
and that number. Otherwise leave Signal deactivated.

## Updating

Before an update, it finishes any check or message it is part way through and starts no new one, so the update never cuts one short (plug-in API 1.14). What changed in each version is in [CHANGELOG.md](https://github.com/TheMightyTRex/starboard-plugins/blob/main/notifications/CHANGELOG.md), and Starboard shows it before you update.

## Add it

Needs Starboard with plug-in API 1.14 or later; a Starboard with an older plug-in API is offered the version before. In Starboard, go to **Settings**, then **Plug-ins**, then **Catalogue**, and find it under **System**. Or, under **Add one from elsewhere**, give this address:

`https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/notifications/starboard-plugin.json`

Or run `python3 install.py` in this folder.

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
