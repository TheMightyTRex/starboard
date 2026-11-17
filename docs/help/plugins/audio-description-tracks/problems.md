# Audio description tracks: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Audio description tracks, then follow the numbered answer.

```flow
title: Find your answer
start: Audio description tracks is not working as it should
q: What does its tab say?
  Failed or Not answering -> 1
  Not supported -> 2
  Active, but a file is not added -> q2
q2: What does the file say?
  Lengths differ -> 3
  No match or Choose the title -> 4
  Out of reach -> 5
  Cannot read or Not added -> 6
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Find a track for your cut #find-a-track-for-your-cut
4: Rename the file or choose the title #rename-the-file-or-choose-the-title
5: Move the film into the media folder #move-the-film-into-the-media-folder
6: Check the file plays #check-the-file-plays
```

## Start it again

1. On Audio description tracks' tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../audio-description-tracks/updates.md).
4. Still failing: go to **System**, then **Logs**, and find its name.

It rests after 10 minutes with nothing to do, and Starboard wakes it when it is needed. Resting is not a problem.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of Audio description tracks works with, so Starboard stopped it.

1. Select **Check for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Find a track for your cut

**Lengths differ** says how much longer or shorter the track is than your film. A description track is made for one cut of a film. A difference of more than a few seconds almost always means your copy is another cut: an extended edition, a director's cut, different studio logos at the start, or a broadcast with its own credits.

- Select **Search AudioVault for** and the title, and find a track for your cut.
- Or line the track up yourself with [describealign](https://pypi.org/project/describealign/), then put the result in the folder.
- If the difference is only a little more than **How close the lengths must be**, raise that setting, up to 30 seconds, then choose the title again in **Film or episode** on **Description tracks to add**, so it checks again.

## Rename the file or choose the title

**No match** means nothing in Jellyfin matches the file's name, such as "No film called Dune is in Jellyfin". **Choose the title** means more than one title could match.

- For **Choose the title**, choose the right one in **Film or episode** on **Description tracks to add**.
- For **No match**, rename the file as the film and its year, such as `Dune (2021).mp3`, or a series with its episode, such as `Slow Horses S01E03.mp3`. Then select **Check the folder now**.
- If it says the series is in Jellyfin but not that episode, check the series and episode numbers in the name.

## Move the film into the media folder

**Out of reach** means the film is not in the movies or tv folder of Starboard's media folder, so the plug-in cannot reach it to add a track.

1. Move the film into the movies folder, or the series into the tv folder, of Starboard's media folder.
2. Wait for Jellyfin to scan its library.
3. Choose the title again in **Film or episode**.

## Check the file plays

- **Cannot read** means the file could not be read as sound. Check that it plays on your computer, then put it in the folder again.
- **Cannot read film** means the film's length could not be read, so the track was not added. Check that the film plays in Jellyfin.
- **Not added** shows what went wrong, such as "Starboard has no Jellyfin key to give yet: add Jellyfin in Settings, Apps". Add Jellyfin in **Settings**, then **Apps**, then select **Check the folder now**.
- "The last check did not finish" on the page shows the error from the last check. Select **Check the folder now** to try again.
- "No audio-description folder yet" means the folder is missing. Select **Deactivate**, then **Activate**: Starboard makes it.

An upload must be up to 60 MB. For a larger file, put it in the audio-description folder in your media folder.

## Report a problem

If none of these helps, tell its maker, with what its tab and the file say: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../audio-description-tracks/settings.md)
- [Updates](../audio-description-tracks/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
