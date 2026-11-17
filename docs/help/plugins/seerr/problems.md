# Seerr: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Seerr, then follow the numbered answer.

```flow
title: Find your answer
start: Seerr is not working as it should
q: What does its tab say?
  Did not start -> 1
  Not supported -> 2
  Active, but something is wrong -> q2
q2: What is wrong?
  Its page does not open -> 3
  Set-up cannot reach Jellyfin -> 4
  Requests are made twice -> 5
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Open its page #open-its-page
4: Give it Jellyfin's address #give-it-jellyfins-address
5: Choose one place for requests #choose-one-place-for-requests
```

## Start it again

Its tab says **Did not start** when Seerr did not start, or stopped answering.

1. On Seerr's tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../seerr/updates.md).
4. Still failing: go to **System**, then **Logs**, and find its name.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of Seerr works with, so Starboard stopped it.

1. Select **Check for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Open its page

Seerr's page is on your home network, at this computer's address and the port Starboard chose for it. The port is not always the usual one: Starboard takes the next free port when that one is in use.

1. Check Seerr's tab says **Active**. Starboard gives it a port only once it is active.
2. Under **Its web page**, read the address, then select **Open Seerr**.
3. Open it from a device on your home network. It does not open from away from home.
4. If it still does not open, deactivate it, activate it again and wait a minute for the app to start.

## Give it Jellyfin's address

Seerr runs in its own container, so it reaches Jellyfin by this computer's name there.

1. In Seerr's set-up, enter Jellyfin's address as `http://host.docker.internal:8096`.
2. Sign in with your Jellyfin account.
3. Check Jellyfin is running: in Starboard, go to **Apps** and check Jellyfin's card.

## Choose one place for requests

Reelix has requests in Starboard too. When people ask in both places, the same film or series can be asked for twice.

1. Choose Seerr or Reelix's **Downloads**, **Requests** as the one place to ask.
2. Tell the people who use your Jellyfin which one to use.

## Report a problem

If none of these helps, tell its maker, with what its tab says: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../seerr/settings.md)
- [Updates](../seerr/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
