[Help centre](../README.md) · Comparison tests · reference
<!-- help: start / compare -->

# What Starboard does not do

The comparison with other media server stacks found things that other stacks do and Starboard does not. This page
lists them as they are in Starboard 0.20.2.

## Things Starboard does not do

- **Subtitles from Reelix.** Reelix does not get subtitles itself. Bazarr gets them, and every install includes it.
- **Subtitles for items that have none.** Starboard does not make subtitles, for example by speech recognition.
- **One file for each audiobook.** Starboard does not join an audiobook's parts into one file.
- **A calendar feed.** Coming up is a page in Starboard, and it does not give an address for a phone's calendar.
  Reelix has a calendar feed of its own, but Starboard does not show its address yet.
- **Unmanic.** Starboard does not offer Unmanic. To convert films and series to save space, add the Tdarr plug-in.

## Apps Starboard does not include

Some popular apps are not part of Starboard, because they are heavy, are not accessible, or do not fit a home stack:

- **Tube Archivist**, which needs a large search database running all the time.
- **Authentik**, a sign-in service much heavier than the rest of the stack.
- **Poster overlays from Kometa**, because the badges are text inside pictures, which screen readers cannot read.
- **Cross-seeding and private-tracker tools**, because Starboard's stack uses public sites and Usenet.
- **A second dashboard**, such as Homarr. Starboard is the dashboard.

## What to use instead

- For subtitles, use Bazarr, which every install includes.
- For converting files, add the Tdarr plug-in. Read [Add a plug-in](../topics/add-a-plugin.md).
- For notifications by email, Telegram, Discord, Signal or Pushover, add the Notifications plug-in, or
  [turn on Starboard's alerts](../topics/activate-alerts.md) for ntfy, Gotify or a webhook.

## Find out more

- [How Starboard compares with other media server stacks](how-starboard-compares.md)
- [Memory and processor: Starboard against other stacks](memory-and-processor.md)
- [Everything Starboard does](../topics/everything-starboard-does.md)
- [Turn on alerts](../topics/activate-alerts.md)
- [Add a plug-in](../topics/add-a-plugin.md)
- [Use Starboard away from home safely](../guides/use-starboard-away-from-home.md)
- [Back up the whole server](../topics/back-up-the-server.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
