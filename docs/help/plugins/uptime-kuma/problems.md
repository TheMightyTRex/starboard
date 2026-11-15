# Uptime Kuma: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Uptime Kuma, then follow the numbered answer.

```flow
title: Find your answer
start: Uptime Kuma is not working as it should
q: What does its tab say?
  Did not start -> 1
  Not supported -> 2
  Active, but something is wrong -> q2
q2: What is wrong?
  Its page does not open -> 3
  A check of this computer fails -> 4
  A status page does not open away from home -> 5
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Open its page #open-its-page
4: Check this computer by its name #check-this-computer-by-its-name
5: Share a status page #share-a-status-page
```

## Start it again

Its tab says **Did not start** when Uptime Kuma did not start, or stopped answering.

1. On Uptime Kuma's tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../uptime-kuma/updates.md).
4. Still failing: go to **System**, then **Logs**, and look for its name.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of Uptime Kuma works with, so Starboard stopped it.

1. Select **Look for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Open its page

Uptime Kuma's page is on your home network, at this computer's address and the port Starboard chose for it. The port is not always the usual one: Starboard takes the next free port when that one is in use.

1. Check Uptime Kuma's tab says **Active**. Starboard gives it a port only once it is active.
2. Under **Its web page**, read the address, then select **Open Uptime Kuma**.
3. Open it from a device on your home network. It does not open from away from home.
4. If it still does not open, deactivate it, activate it again and wait a minute for the app to start.

## Check this computer by its name

Uptime Kuma runs in its own container, so `localhost` there is Uptime Kuma itself, not this computer.

1. In Uptime Kuma, open the check.
2. Use `host.docker.internal` for this computer, with the port of the service you check.
3. For other computers, use their address on your home network.

## Share a status page

Uptime Kuma's status pages are on your home network only. Starboard does not share them.

1. To open them away from home, add the [Remote access](../remote-access/install.md) plug-in, or share them yourself.

## Report a problem

If none of these helps, tell its maker, with what its tab says: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../uptime-kuma/settings.md)
- [Updates](../uptime-kuma/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
