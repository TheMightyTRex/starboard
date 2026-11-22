# Themearr: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Themearr, then follow the numbered answer.

```flow
title: Find your answer
start: Themearr is not working as it should
q: What does its tab say?
  Did not start -> 1
  Not supported -> 2
  Active, but something is wrong -> q2
q2: What is wrong?
  The card says No Reelix -> 3
  The card says Needs a RapidAPI key -> 4
  A film has no tune -> 5
  Its page asks for a token -> 6
  Its page does not open -> 7
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Add Reelix to Starboard #add-reelix-to-starboard
4: Add a RapidAPI key #add-a-rapidapi-key
5: Find why a film has no tune #find-why-a-film-has-no-tune
6: Sign in to Themearr #sign-in-to-themearr
7: Open its page #open-its-page
```

## Start it again

Its tab says **Did not start** when Themearr did not start, or stopped answering.

1. On Themearr's tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../themearr/updates.md).
4. Still failing: go to **System**, then **Logs**, and find its name.

If the card says **No answer from** and its name, it did not answer in 3 seconds. Check that it is **Active** on its tab, then wait a minute.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of Themearr works with, so Starboard stopped it.

1. Select **Check for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Add Reelix to Starboard

The card says "Starboard has no Reelix key to give yet: add Reelix in Settings, Apps."

1. Go to **Settings**, then **Apps**.
2. Add Reelix, or check it has its API key.
3. Wait up to 2 minutes: Starboard gives Themearr Reelix's address and key by itself.

If the card says "Themearr did not take Reelix's address and key", check Reelix is running, then wait 2 minutes for it to try again.

## Add a RapidAPI key

Themearr fetches tunes through the youtube-mp36 service on RapidAPI, and needs a key for it.

1. Make a RapidAPI account and subscribe to youtube-mp36. Its free plan has a monthly limit.
2. On Themearr's tab, under **Fetching theme tunes**, enter the **RapidAPI key** and **RapidAPI user name**, and select **Save**.
3. Wait up to 2 minutes. The card's status changes to **OK**.

When the monthly limit runs out, Themearr waits and tries again later by itself. Its own page, under **System**, then **Health**, says so.

## Find why a film has no tune

1. Check the film is in Reelix and has its file. Themearr skips films Reelix has not downloaded yet.
2. Wait 15 minutes: Themearr reads Reelix's films every 15 minutes.
3. Open Themearr's page and find the film. Its search may have found no tune: choose one, or paste the address of a tune to use.
4. In Themearr's page, **System**, then **Health**, says when a folder is missing or read only, or the RapidAPI limit ran out.
5. If its logs say "unresolved path", the film is not in your `movies` folder. Themearr finds films only there.

Film posters may be missing on Themearr's page: Reelix does not give Radarr's posters yet. The tunes are fetched all the same.

## Sign in to Themearr

Themearr's own page asks for an access token once in each web browser.

1. On Themearr's tab, open **Sign in to Themearr**.
2. Copy the access token.
3. Paste it into the **Access token** box on Themearr's page.

The token is made by Starboard for this install. Keep it private: anyone with it can change Themearr.

## Open its page

Themearr's page is on your home network, at this computer's address and the port Starboard chose for it. The port is not always 8080: Starboard takes the next free port when that one is in use.

1. Check Themearr's tab says **Active**. Starboard gives it a port only once it is active.
2. Under **Its web page**, read the address, then select **Open Themearr**.
3. Open it from a device on your home network. It does not open from away from home.
4. If it still does not open, deactivate it, activate it again and wait a minute for the app to start.

## Report a problem

If none of these helps, tell its maker, with what its tab and the card say: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../themearr/settings.md)
- [Updates](../themearr/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
