# Checkrr: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Checkrr, then follow the numbered answer.

```flow
title: Find your answer
start: Checkrr is not working as it should
q: What does its tab say?
  Did not start -> 1
  Not supported -> 2
  Active, but something is wrong -> q2
q2: What is wrong?
  The card lists bad files -> 3
  It has not checked yet -> 4
  A file I know is damaged passed -> 5
  Its page does not open -> 6
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Replace a bad file #replace-a-bad-file
4: Start a check #start-a-check
5: Know what it checks #know-what-it-checks
6: Open its page #open-its-page
```

## Start it again

Its tab says **Did not start** when Checkrr did not start, or stopped answering.

1. On Checkrr's tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../checkrr/updates.md).
4. If you changed its settings file, `checkrr.yaml`, a mistake there stops it starting. Undo your change, or move the file out of its folder so Starboard writes a new one at the next start.
5. Still failing: go to **System**, then **Logs**, and find its name.

If the card says **No answer from** and its name, it did not answer in 3 seconds. Check that it is **Active** on its tab, then wait a minute.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of Checkrr works with, so Starboard stopped it.

1. Select **Check for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Replace a bad file

Checkrr changed nothing: the file is where it was. Replace it yourself.

1. On Checkrr's tab, open **Files that failed the check**. Each row has the file, its folder and Checkrr's reason.
2. Play the file in Jellyfin to check it is damaged. "not recognized" means its start is not a film or episode Checkrr knows.
3. In Reelix, search for the film or episode again and choose a new copy. When Reelix brings the new one in, it replaces the old file: it moves the old one to Reelix's recycle bin when **Recycle bin folder** is set in Reelix's settings, and otherwise deletes it for good. Set the recycle bin first to keep the old file.
4. Select **Check now** on Checkrr's tab. A replaced file drops off the list once it passes.

To take a damaged film out of the library without deleting it, the Library clean-up plug-in moves it to the holding folder.

## Start a check

The card says "Not checked yet" until the first Sunday night after you add it.

1. On Checkrr's tab, select **Check now** and confirm.
2. The card's status changes to **Scanning**. A large library takes hours the first time.

## Know what it checks

Checkrr reads the start of each file and asks FFprobe to read it. That finds files whose start is damaged, files that are not media at all and videos with no sound. A file cut short part way through can pass. Read [Settings](../checkrr/settings.md).

## Open its page

Checkrr's page is on your home network, at this computer's address and the port Starboard chose for it. The port is not always 8585: Starboard takes the next free port when that one is in use.

1. Check Checkrr's tab says **Active**. Starboard gives it a port only once it is active.
2. Under **Its web page**, read the address, then select **Open Checkrr**.
3. Open it from a device on your home network. It does not open from away from home.

## Report a problem

If none of these helps, tell its maker, with what its tab and the card say: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../checkrr/settings.md)
- [Updates](../checkrr/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
