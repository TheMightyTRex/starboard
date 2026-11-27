# Maintainerr: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Maintainerr, then follow the numbered answer.

```flow
title: Find your answer
start: Maintainerr is not working as it should
q: What does its tab say?
  Did not start -> 1
  Needs an update -> 2
  Active, but something is wrong -> q2
q2: What is wrong?
  Its page does not open -> 3
  It cannot reach Jellyfin or Seerr -> 4
  A rule removes nothing -> 5
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Open its page #open-its-page
4: Give it its keys #give-it-its-keys
5: Give the rule an action #give-the-rule-an-action
```

## Start it again

Its tab says **Did not start** when Maintainerr did not start, or stopped answering.

1. On Maintainerr's tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../maintainerr/updates.md).
4. Still failing: go to **System**, then **Logs**, and find its name.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of Maintainerr works with, so Starboard stopped it.

1. Select **Check for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Open its page

Maintainerr's page is on your home network, at this computer's address and the port Starboard chose for it. The port is not always the usual one: Starboard takes the next free port when that one is in use.

1. Check Maintainerr's tab says **Active**. Starboard gives it a port only once it is active.
2. Under **Its web page**, read the address, then select **Open Maintainerr**.
3. Open it from a device on your home network. It does not open from away from home.
4. If it still does not open, deactivate it, activate it again and wait a minute for the app to start.

## Give it its keys

Starboard gives Maintainerr no key, so it reaches Jellyfin and Seerr only with keys you make.

1. In Jellyfin, go to **Dashboard**, then **API keys**, and make a key for Maintainerr.
2. In Maintainerr, add Jellyfin with that key. Jellyfin is on this computer, at `http://host.docker.internal:8096`.
3. If you use Seerr, make a key in Seerr's own settings and add it in Maintainerr too.

## Give the rule an action

A rule only lists what it finds until you give it an action. That is on purpose, so nothing goes by mistake.

1. In Maintainerr, open the rule and check what it finds.
2. When you are sure, give it an action that removes.
3. Check Maintainerr has its keys for Jellyfin, and for Seerr if the action goes through Seerr.

## Report a problem

If none of these helps, tell its maker, with what its tab says: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../maintainerr/settings.md)
- [Updates](../maintainerr/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
