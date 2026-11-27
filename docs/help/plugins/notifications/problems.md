# Notifications: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Notifications, then follow the numbered answer.

```flow
title: Find your answer
start: Notifications is not working as it should
q: What does its tab say?
  Failed or Not answering -> 1
  Needs an update -> 2
  Active, but messages do not arrive -> q2
q2: What does the card or test say?
  No channel active -> 3
  Refused the sign-in or token -> 4
  Could not be reached or not found -> 5
  Fill in or Add first -> 6
  Sent, but nothing arrived -> 7
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Activate a channel #activate-a-channel
4: Check the sign-in or token #check-the-sign-in-or-token
5: Check the address #check-the-address
6: Fill in the missing details #fill-in-the-missing-details
7: Check what it sends and to whom #check-what-it-sends-and-to-whom
```

## Start it again

1. On Notifications' tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../notifications/updates.md).
4. Still failing: go to **System**, then **Logs**, and find its name.

It rests 5 minutes after the last message, and Starboard wakes it for the next event. Resting is not a problem.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of Notifications works with, so Starboard stopped it.

1. Select **Check for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Activate a channel

"No channel is active. Activate one in Settings, Plug-ins, Notifications." means it has nowhere to send.

1. Go to **Settings**, then **Plug-ins**, then **Notifications**.
2. Fill in the details for one way to send, such as **Email**, and select **Save**.
3. Select its test button, such as **Send a test email**.
4. When the test arrives, activate **Send by** that channel.

## Check the sign-in or token

"it refused the sign-in or token", or "the email server refused the user name or password", means the service did not accept what you gave.

- **Email:** check **User name** and **Password**. Where your email service offers an app password, use one.
- **Telegram:** check **Bot token**, from @BotFather in Telegram.
- **Pushover:** check **User key** and **Application token**.
- **ntfy:** check **Access token**, for a server or topic that needs one.

Secret settings are never shown again, so enter the whole value again, select **Save**, and select the test button.

## Check the address

"it could not be reached" or "the address or chat was not found" means it got no answer, or the service did not know the address or chat.

- **Email:** check **Email server**, **Port** and **Security**. Your email service says which to use: usually STARTTLS on port 587, or SSL on port 465.
- **Telegram:** check **Telegram chat**, one chat id a line, and send your bot a message first, so it may write to you.
- **Discord:** copy the webhook address again from the channel's **Edit channel**, **Integrations**, **Webhooks**.
- **Signal**, **ntfy** and **Webhooks:** check the address is right and that the service is running.

Then select the test button again.

## Fill in the missing details

A test that says "Fill in" and some details, then "first", or "Add" and a setting, means a detail that channel needs is empty.

- **Email** needs **Email server**, **Send from** and at least one address in **Send email to**.
- **Telegram** needs **Bot token** and a chat id in **Telegram chat**.
- **Signal** needs **signal-cli-rest-api address**, **Send from number** and **Send Signal messages to**.
- **Pushover** needs **User key** and **Application token**. **ntfy** needs **Topic**. **Discord** and **Webhooks** need an address.

## Check what it sends and to whom

When the card says a message was sent but nobody saw it:

- Check that kind is activated under **What to send**. A deactivated kind is not sent and not listed.
- For email, check the junk or spam folder of each address in **Send email to**.
- For the person who asked, check **Tell the person who asked too** is activated, and that their line under **People** uses the name they use in Reelix or Seerr, such as `Sam, sam@example.com` or `Sam, telegram 123456`.
- For New this week, it is sent at 09:00 on the day in **Send New this week on**. A week with nothing new sends nothing. Select **Send New this week now** to try it.

## Report a problem

If none of these helps, tell its maker, with what its tab and the cards say: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../notifications/settings.md)
- [Updates](../notifications/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
