[Help centre](../README.md) · When something is wrong · troubleshooting

# A Live TV channel will not play

When a Live TV channel will not play in Jellyfin, or has no logo, the cause is usually one of four things. Jellyfin
cannot reach Starboard, Jellyfin's FFmpeg refuses the stream, the channel stopped at its source, or Live TV is not
running. These checks find which.

## Steps

1. Go to **Settings**, then **Plug-ins**, and find **Live TV**. Check that it is **Active**. If it says
   **Did not start** or **Inactive**, select **Activate**. The **Live TV** card on the dashboard says whether the
   last run worked.
2. If Pluto TV channels do not play, or channels have no logos, Jellyfin cannot reach Starboard. Starboard serves
   both to Jellyfin. Open **Address Jellyfin uses to reach Starboard** in a browser on the computer Jellyfin runs
   on. If it does not open, change the address, or make Starboard open to your home network. Read
   [Choose who can open Starboard](choose-who-can-open-starboard.md).
3. If Samsung TV Plus channels such as U&Laughs do not play, Jellyfin's FFmpeg is refusing their ad links. When
   Starboard installed Jellyfin, it runs FFmpeg through a small fix file. Run **Install apps** again to put the fix
   back. Read [Install apps with Starboard](install-apps.md).
4. If one channel stopped while others play, it may have stopped at its source. Select **Run Live TV now** in the
   **Live TV** section. Live TV tests every channel and drops the ones that do not play from your connection.
5. In Jellyfin, refresh the guide data, then try the channel again.

## Things to note

- The FFmpeg fix is for Live TV streams only. Your library files and other links play as before.
- The fix is only in a Jellyfin that Starboard installed. A Jellyfin you set up yourself does not have it.
- Without a run, Live TV drops channels that stopped playing once a week.
- Where the plug-in cannot run, Live TV runs inside Starboard instead. Its status and **Run Live TV now** are then
  in **Settings**, **Apps**, **Jellyfin**, **Live TV**.

## If it does not work

- **The installer stops with error IN-34:** Starboard could not put the FFmpeg fix in Jellyfin's settings folder.
  Read [IN-34](run-first-errors.md#in-34).
- **"Last run failed":** read the reason on the card. It often names the setting to change.
- **No channels at all in Jellyfin:** read [Set up free Live TV in Jellyfin](set-up-live-tv.md#add-the-channels-and-guides-in-jellyfin).
- If none of this helps, activate detailed logging and report the problem. Read
  [Read the log and report a problem](read-the-log.md#report-a-problem).

## Find out more

- [Set up free Live TV in Jellyfin](set-up-live-tv.md)
- [The plug-in collection](../basics/plugin-collection.md#live-tv)
- [Addresses and ports](../basics/addresses-and-ports.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
