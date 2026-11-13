[Help centre](../README.md) · Comparison tests · reference

# How Starboard compares with other media server stacks

A media server stack is the set of apps that together find, download, organise and play your films, series, music
and books. This page compares Starboard's stack with three popular ones: what each includes and what each can do.
For the measured memory and processor of each, read [Memory and processor](memory-and-processor.md).

## The stacks compared

<table>
<caption>The four media server stacks compared, and the apps in each</caption>
<thead>
<tr><th scope="col">Stack</th><th scope="col">Apps it usually has</th><th scope="col">Containers in the test</th></tr>
</thead>
<tbody>
<tr><th scope="row">Starboard</th><td>Starboard, Reelix (Lite or full), Jellyfin, Audiobookshelf, qBittorrent and NZBGet</td><td>6</td></tr>
<tr><th scope="row">Classic</th><td>Radarr, Sonarr, Lidarr, Readarr, Prowlarr, Jellyseerr or Seerr for requests, Jellyfin, Audiobookshelf, qBittorrent and NZBGet</td><td>10</td></tr>
<tr><th scope="row">Led by a dashboard</th><td>The classic stack, with Homarr or Homepage in front, Jellystat and its database, Unpackerr and Recyclarr</td><td>15</td></tr>
<tr><th scope="row">Plex</th><td>Plex, Tautulli, Overseerr or Seerr, Radarr, Sonarr and Prowlarr, Kometa and the download apps</td><td>not tested</td></tr>
</tbody>
</table>

Bazarr, for subtitles, and Gluetun, for a VPN, are left out of every stack, because most stacks have both.

In Starboard's stack, one app does the work of several. Reelix finds and downloads films, series, music and books,
and handles requests, in place of Radarr, Sonarr, Lidarr, Readarr, Prowlarr and Jellyseerr. Starboard is the
dashboard and runs everything else, so you have one place to look.

## What each stack can do

"Add-on" means another app, which is another container running all the time.

<table>
<caption>What each stack can do, as of 13 November 2026</caption>
<thead>
<tr><th scope="col">Feature</th><th scope="col">Starboard</th><th scope="col">Classic</th><th scope="col">Led by a dashboard</th><th scope="col">Plex</th></tr>
</thead>
<tbody>
<tr><th scope="row">Find and download films, series, music and books</th><td>Yes, in Reelix</td><td>Yes, one app for each</td><td>Yes, one app for each</td><td>Films and series; more with more apps</td></tr>
<tr><th scope="row">Requests, with approval and limits</th><td>Yes, in Reelix, shown in Starboard</td><td>Yes, in Jellyseerr or Seerr</td><td>Yes, in Jellyseerr or Seerr</td><td>Yes, in Overseerr or Seerr</td></tr>
<tr><th scope="row">A dashboard with every app</th><td>Yes, Starboard itself</td><td>Not included</td><td>Yes, in Homarr or Homepage</td><td>Not included</td></tr>
<tr><th scope="row">Install and set up the apps for you</th><td>Yes</td><td>Not included</td><td>Not included</td><td>Not included</td></tr>
<tr><th scope="row">App updates, with a backup first</th><td>Yes</td><td>With an add-on</td><td>With an add-on</td><td>With an add-on</td></tr>
<tr><th scope="row">Alerts when an app stops</th><td>Yes, to ntfy, Gotify or a webhook</td><td>With an add-on</td><td>With an add-on, such as Uptime Kuma</td><td>With an add-on</td></tr>
<tr><th scope="row">Disk health and drive pools</th><td>Yes</td><td>Not included</td><td>Not included</td><td>Not included</td></tr>
<tr><th scope="row">Audiobooks, podcasts and radio</th><td>Yes, with Audiobookshelf and Reelix</td><td>With more apps</td><td>With more apps</td><td>With more apps</td></tr>
<tr><th scope="row">Live TV</th><td>Yes, through a plug-in and Jellyfin</td><td>Through Jellyfin</td><td>Through Jellyfin</td><td>Built into Plex</td></tr>
<tr><th scope="row">Subtitles</th><td>With Bazarr, for now</td><td>With Bazarr</td><td>With Bazarr</td><td>Built into Plex</td></tr>
<tr><th scope="row">Watch statistics</th><td>With Jellystat (Full install)</td><td>With an add-on, such as Jellystat</td><td>With Jellystat</td><td>Built in, or Tautulli</td></tr>
<tr><th scope="row">Skip intros and credits</th><td>Not yet</td><td>With a Jellyfin plug-in</td><td>With a Jellyfin plug-in</td><td>Built into Plex</td></tr>
<tr><th scope="row">Library clean-up rules</th><td>Not yet</td><td>With an add-on, such as Maintainerr</td><td>With an add-on</td><td>With an add-on</td></tr>
<tr><th scope="row">Notifications by email, Telegram or Discord</th><td>Not yet in Starboard; Reelix has some</td><td>In each app, or an add-on</td><td>In each app, or an add-on</td><td>In each app, or an add-on</td></tr>
<tr><th scope="row">Use from away from home without opening your router</th><td>Not yet; a guide covers other ways</td><td>With an add-on</td><td>With an add-on</td><td>Plex Relay, now paid for remote play</td></tr>
</tbody>
</table>

## Things to note

- **The other stacks vary.** Every home sets up its stack in its own way. The apps listed are the usual ones, taken
  from popular guides in 2026, not a rule.
- **Plex was not measured.** Plex and Tautulli were not part of the tests, so there are no measured figures for a
  stack built on Plex.
- **Some apps have changed.** Jellyseerr and Overseerr are being replaced by Seerr. Readarr has no image that can be
  pulled. Watchtower, a common add-on for updates, stopped being maintained in December 2025.
- **What is missing in Starboard** is listed, with what is planned, in
  [What Starboard does not do yet](what-starboard-does-not-do-yet.md).

## Find out more

- [Memory and processor: Starboard against other stacks](memory-and-processor.md)
- [What Starboard does not do yet, and what is planned](what-starboard-does-not-do-yet.md)
- [Everything Starboard does](../topics/everything-starboard-does.md)
- [What Reelix is](../basics/what-is-reelix.md)
- [Move from Radarr, Sonarr and the others to Reelix](../topics/move-your-apps-to-reelix.md)
- [Move from Plex to Jellyfin and Audiobookshelf](../guides/move-from-plex-to-jellyfin.md)
- [Use Starboard away from home safely](../guides/use-starboard-away-from-home.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
