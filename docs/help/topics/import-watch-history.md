[Help centre](../README.md) · Jellyfin and Audiobookshelf · how-to

# Import watch history into Jellyfin

Move what everyone watched, and where they stopped, from Plex, Emby or another Jellyfin into your Jellyfin.
At the end, films and episodes show as watched in Jellyfin, with resume points for anything half-watched.

## Before you begin

- Jellyfin is on your dashboard with its API key. Read [Add an app](add-an-app.md) and
  [Find an app's API key](find-an-api-key.md).
- Your films and series are in Jellyfin, or on their way. History is matched to what Jellyfin has.
- You have one of these to read the history from:
  - a copy of Plex's database file, `com.plexapp.plugins.library.db`, for every Plex account;
  - a running Plex server and your Plex token, for your own account only;
  - an Emby server or another Jellyfin server, with an API key from its **Dashboard**, **API keys**, for
    every user;
  - a history file Starboard made before.

## Steps

### Read the history

1. Go to **Settings**, then **Jellyfin**.
2. In **Import watch history**, choose where the history comes from in **Import from**.
3. For a server, type its **Server address**, such as `http://192.168.1.20:32400`, and its
   **Token or API key**.
4. For a file, select it in **File**. For a Plex database, stop Plex before you copy the file, or copy its
   `-wal` file with it.
5. Select **Read the history**.

Starboard shows "Reading the history. This can take a few minutes." When it ends, it shows **History read**
and a table of the accounts it found, with how many films and episodes each one watched.

### Match each account to a Jellyfin user

1. In the table, find **Goes to Jellyfin user** for each account.
2. Choose the Jellyfin user the account belongs to, or **Do not import** to leave it out. For example, the
   Plex account `sam` goes to the Jellyfin user `Sam`.
3. If accounts have the same names in both places, select **Match accounts with the same name** to match
   them all at once.

Each choice saves straight away.

### Apply the history

1. Select **Apply now**.
2. When it ends, the **Applied** column shows how many items each account received.

To keep applying history as new films and episodes arrive in Jellyfin, turn on **Keep applying every
hour**.

## Things to note

- Watched items become watched in Jellyfin, with the date they were watched. Part-watched items
  become a resume point.
- Each item is applied once. If someone marks it unwatched in Jellyfin later, Starboard leaves it alone.
- Films are matched by their TMDB (The Movie Database) or IMDb ID. Episodes are matched by their show's
  TVDB, TMDB or IMDb ID, with the season and episode number.
- After an apply, **Not in Jellyfin yet** lists the films and episodes Starboard could not match, and the
  account each one belongs to. Either they are not in Jellyfin yet, or Jellyfin has no TMDB, IMDb or TVDB
  ID for them. With **Keep applying every hour** on, they are picked up when they arrive.
- A Plex database copy is deleted after Starboard reads it.
- **Keep applying every hour** uses a little of your server each hour. Read
  [Make Starboard use less of your server](make-starboard-lighter.md).

## If it does not work

- **"Not started":** read the reason in the message. The most common one is a missing file or address.
- **"The import did not work":** check the server address and the token or API key, then select
  **Read the history** again.
- **An account has no Jellyfin user to choose:** make the user in Jellyfin first, then open this page again.
- **A film stays in Not in Jellyfin yet:** check in Jellyfin that the film is identified correctly, with a
  TMDB or IMDb ID, then select **Apply now** again.

## Find out more

- [Move from Plex to Jellyfin and Audiobookshelf](../guides/move-from-plex-to-jellyfin.md)
- [Copy listening progress into Audiobookshelf](copy-listening-progress.md)
- [Give every Jellyfin user the same defaults](jellyfin-user-defaults.md)
