[Help centre](../README.md) · Comparison tests · reference

# What Starboard does not do yet, and what is planned

The comparison with other media server stacks found a few things other stacks do that Starboard does not do yet.
This page lists them, with what is planned. Nothing here has a date, and the order may change.

## What is planned, in order

The comparison ranked these by how useful each is, and by how light it is: an idea that uses nothing between uses
comes before one that must run all the time.

1. **Plug-ins that can change things.** Today a plug-in can read your downloads and library, but cannot change
   them. The plan is a few narrow permissions, such as pausing a download or moving an item to the holding folder,
   each shown to you before you add the plug-in, and none that can delete. Several of the ideas below wait on this.
2. **Notifications to more places**, such as email, Telegram, Discord, Signal and Pushover, including "your request
   is ready" and a weekly "new this week" message to the household. Today Starboard sends alerts to ntfy, Gotify or a
   webhook.
3. **Recommended Jellyfin plug-ins in Starboard's settings**, starting with skipping intros and credits, and
   Playback Reporting.
4. **Using Starboard from away from home without opening your router**, through Tailscale or Cloudflare Tunnel.
5. **Copies of your backups off this computer**, to a USB disk, another computer or a cloud folder, checked after
   each copy.
6. **Library clean-up rules**, such as "watched by everyone and older than 90 days". Items would go to the holding
   folder, never straight to deletion, and you would see the list first.
7. **Lighter watch statistics**, from Jellyfin's own Playback Reporting, so a Full install would no longer need
   Jellystat and its database.
8. **Tidying downloads**: flagging files of a dangerous type, and clearing stalled downloads.
9. **Subtitles in Reelix**, so you would no longer need Bazarr, and later a choice to make subtitles by speech
   recognition for items that have none.
10. **A choice to prefer audio description**, the sound track that describes what is happening for blind and
    partially sighted viewers. No other stack found offers this.

After these, the ideas being looked at are: following YouTube channels, Navidrome for music apps, a lighter
invitation page in place of Wizarr, merging audiobook parts into one file, Unmanic as a lighter choice than Tdarr,
and a calendar feed for phones.

## What Starboard does not plan to do

Some popular apps are left out on purpose, because they are heavy, are not accessible, or do not fit a home stack:

- **Tube Archivist**, which needs a large search database to run all the time.
- **Authentik**, a sign-in service much heavier than the rest of the stack.
- **Poster overlays from Kometa**, because the badges are text inside pictures that screen readers cannot read.
- **Cross-seeding and private-tracker tools**, because Starboard's stack uses public sites and Usenet.
- **A second dashboard**, such as Homarr, beside Starboard. Starboard is the dashboard.

## What you can do today

- For subtitles, keep Bazarr, which every install includes.
- For watch statistics, use Jellystat, part of the Full install.
- For skipping intros, add a Jellyfin plug-in in Jellyfin's own dashboard.
- For notifications, [activate Starboard's alerts](../topics/activate-alerts.md), and set up Reelix's
  notifications in **Settings**, **Apps**, **Reelix**, **Notifications**
  ([Change Reelix's settings in Starboard](../topics/change-reelix-settings.md)).

## Find out more

- [How Starboard compares with other media server stacks](how-starboard-compares.md)
- [Memory and processor: Starboard against other stacks](memory-and-processor.md)
- [Everything Starboard does](../topics/everything-starboard-does.md)
- [Activate alerts](../topics/activate-alerts.md)
- [Add a plug-in](../topics/add-a-plugin.md)
- [Use Starboard away from home safely](../guides/use-starboard-away-from-home.md)
- [Back up the whole server](../topics/back-up-the-server.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
