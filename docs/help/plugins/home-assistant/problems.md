# Home Assistant: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with the Home Assistant plug-in from what its tab or its card says, then follow the numbered answer.

```flow
title: Find your answer
start: The Home card is not working as it should
q: What does its tab say?
  Failed or Not answering -> 1
  Not supported -> 2
  Active, but the card is wrong -> q2
q2: What does the card say?
  Needs setting up -> 3
  No answer from Home Assistant -> 4
  Warning when all is well -> 5
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Finish setting it up #finish-setting-it-up
4: Check the address, token and ids #check-the-address-token-and-ids
5: Change the warning states #change-the-warning-states
```

## Start it again

1. On the plug-in's tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../home-assistant/updates.md).
4. Still failing: go to **System**, then **Logs**, and find its name.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of the Home Assistant plug-in works with, so Starboard stopped it.

1. Select **Check for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Finish setting it up

The card says "Add the address, a token and what to show in the plug-in's settings". It needs all three.

1. Go to **Settings**, then **Plug-ins**, then **Home Assistant**.
2. Fill in **Home Assistant's address**, **Long-lived access token** and **What to show**. Read [Install](../home-assistant/install.md) for where to make the token.
3. Select **Save**.

## Check the address, token and ids

The plug-in asked Home Assistant and got no usable answer, or did not answer Starboard within 3 seconds.

1. Open **Home Assistant's address** in your browser, and check Home Assistant opens.
2. Check each id in **What to show** is exactly as Home Assistant shows it. One wrong id stops the whole card.
3. If the token was deleted in Home Assistant, make a new one and paste it in **Long-lived access token**. A saved token is never shown, so pasting it again is the only way to be sure.
4. If Home Assistant is slow to answer, show fewer things: it asks for each one in turn, and Starboard waits only 3 seconds for the card.
5. Select **Save**, then wait a minute for the card to ask again.

## Change the warning states

The card says **Warning** when any thing is in a state from **Warn when any is**, `on, open, unlocked` by default. A light that is on counts too.

1. Go to **Settings**, then **Plug-ins**, then **Home Assistant**.
2. In **Warn when any is**, keep only the states that should warn you, separated by commas.
3. Select **Save**.

Or take the things you do not need warnings for out of **What to show**.

## Report a problem

If none of these helps, tell its maker, with what its tab and the card say: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../home-assistant/settings.md)
- [Updates](../home-assistant/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
