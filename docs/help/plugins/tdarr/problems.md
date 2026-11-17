# Tdarr: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Tdarr, then follow the numbered answer.

```flow
title: Find your answer
start: Tdarr is not working as it should
q: What does its tab say?
  Did not start -> 1
  Not supported -> 2
  Active, but something is wrong -> q2
  Not active, and bringing in Tdarr failed -> 6
q2: What is wrong?
  Its page does not open -> 3
  Tdarr is not connected yet -> 4
  Nothing is converting -> 5
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Open its page #open-its-page
4: Connect Tdarr #connect-tdarr
5: Check what Tdarr does and when #check-what-tdarr-does-and-when
6: Bring in your Tdarr again #bring-in-your-tdarr-again
```

## Start it again

Its tab says **Did not start** when Tdarr did not start, or stopped answering.

1. On Tdarr's tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../tdarr/updates.md).
4. Still failing: go to **System**, then **Logs**, and find its name.

If your old Tdarr in the main install is still running, it may hold port 8265. The plug-in then takes the next free port, so Starboard's own Tdarr page may not find it until the old one is removed.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of Tdarr works with, so Starboard stopped it.

1. Select **Check for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Open its page

Tdarr's page is on your home network, at this computer's address and the port Starboard chose for it: 8265 when it is free, otherwise the next free port.

1. Check Tdarr's tab says **Active**. Starboard gives it a port only once it is active.
2. Under **Its web page**, read the address, then select **Open Tdarr**.
3. Open it from a device on your home network. It does not open from away from home.
4. If it still does not open, deactivate it, activate it again and wait a minute for Tdarr to start.

## Connect Tdarr

The **Settings** section on its tab says **Tdarr is not connected yet** until Tdarr has a key Starboard keeps.

1. Select **Connect Tdarr**. Tdarr restarts once, and Starboard waits for it.
2. If it says **Tdarr did not answer after restarting. Check it is running in Apps, then try again.**, check Tdarr's tab says **Active**.
3. Select **Connect Tdarr** again.

## Check what Tdarr does and when

On its tab, under **Settings**:

1. Under **What Tdarr does**, check it is **Save space**. **Check files only** changes nothing, and **Off** does nothing.
2. Under **Libraries**, check **Films**, **Series** or both are ticked.
3. Under **When**, **In quiet hours** converts only in Starboard's download hours, or 01:00 to 06:00 when they are not set. Choose **Any time** to start on new files straight away.

**Save space** keeps a new file only when it is smaller, so some files stay as they are.

## Bring in your Tdarr again

**Bring in the Tdarr you already have…** says why it stopped. Your Tdarr is not changed when the copy fails.

- **Deactivate Tdarr first, so nothing writes to its folder while the copy is made**: select **Deactivate**, then try again.
- **Starboard found no Tdarr on this computer (no container called tdarr)**: the main install has no Tdarr to copy. Set the plug-in up as a new Tdarr instead. Read [Install](../tdarr/install.md#set-it-up).
- **Tdarr keeps /app/server in a Docker volume, which Starboard cannot copy. Copy it by hand**: copy those folders into the plug-in's folder in Starboard's data, `data/plugins/tdarr`, yourself.
- **Tdarr has none of the folders this plug-in copies**: there is nothing to bring in. Set it up as a new Tdarr.
- **Starboard could not stop Tdarr for the copy**, or **The copy did not finish**: read the rest of the message, then try again. Go to **System**, then **Logs**, for more.

If the plug-in had made folders of its own already, Starboard puts them beside the copy, named `before-copy` with the date and time, and deletes nothing.

## Report a problem

If none of these helps, tell its maker, with what its tab says: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../tdarr/settings.md)
- [Updates](../tdarr/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
