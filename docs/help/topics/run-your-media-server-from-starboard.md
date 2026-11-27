[Help centre](../README.md) · Jellyfin and Audiobookshelf · how-to
<!-- help: use / media -->

# Run your media server from Starboard

Starboard can do the everyday jobs of Jellyfin, Plex and Emby, so you seldom need to open the server's own dashboard. What it
can do comes from what each server's own interface allows. Where a server cannot do a job through that interface, or where
Starboard does not do it yet, the page says so and links to the server's own page.

## Before you begin

- Add the media server in **Manage apps** with its address and key, and make it the one in use. Read
  [Choose your media server](choose-your-media-server.md).
- Starboard reads the server only when you ask. Opening the page asks it nothing.

## Read and run the server

1. Go to **Settings**, then **Apps**, then the tab named for your media server.
2. Find **Administration**. It has a part for each thing the server lets Starboard do.
3. Select the button of the part you want, such as **Read the libraries**. Starboard asks the server and shows the answer.
4. To act, use the buttons in the list:
   - **Scan** beside a library asks the server to check for new and changed files. **Scan every library** does all of them.
   - **Refresh everything** asks you first, because the server reads every file and picture again and this can take a long time.
   - **Run now** beside a scheduled task starts it at once.
   - **Show the end** beside a log file shows its last 300 lines.
5. Starboard says what it asked in a message under the heading. Each change is written to the audit log in **Settings**, **Security**.

## What each part shows

| Part | Jellyfin | Emby | Plex |
|---|---|---|---|
| Libraries | Name, kind and folders | Name, kind and folders | Name, kind, folders and number of items |
| Scheduled tasks | Name, group, when it runs and its last result | The same | The maintenance tasks, and whether each is on |
| Activity | Sign-ins, plays and changes | The same | What was watched, and by whom |
| Logs | The server's log files | The same | Not offered: Plex makes logs as a zip file in its own page |

## Where each job is done

The last part of **Administration**, **Where each job is done**, is a table of every administration job the server has. Each row is one of
four things:

- **In Starboard:** you can do it here.
- **Not in Starboard yet:** Starboard can do it through the server's interface, but has not been built to. Use the server's page, which the row links to.
- **In the server's own page:** it needs something Starboard cannot reach, such as a paid licence, so you do it in the server.
- **Not possible:** the server gives no way to do it through its interface. For Plex, people and sharing, remote access and devices are
  held by plex.tv, the Plex account service, which a person signs in to themselves.

Some jobs need a paid licence: hardware video conversion and Live TV need Emby Premiere or Plex Pass.

## If something goes wrong

- **The server did not answer:** check that it is running and that its address and key are right in **Manage apps**, then select the button again.
- **A part is missing:** the server does not give Starboard that part. **What each can do** on the same tab says why.
- **Plex or Emby behaves differently from this page:** Starboard has only tried these calls against recorded answers from each server's
  documented interface, not against a real Plex or Emby. Say so on the Starboard Discord support server.

## Find out more

- [Choose your media server](choose-your-media-server.md)
- [Move to another media server](move-to-another-media-server.md)
- [Add the people who use your apps](add-the-people-who-use-your-apps.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
