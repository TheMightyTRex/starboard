[Help centre](../README.md) · Jellyfin and Audiobookshelf · how-to

# Copy listening progress into Audiobookshelf

Copy where everyone is in each audiobook, and what they have finished, from Plex, Jellyfin, Emby or another
Audiobookshelf into your Audiobookshelf. At the end, each person carries on from where they stopped.

## Before you begin

- Audiobookshelf has scanned in your books. Progress is matched to the books it has.
- Audiobookshelf is in **Manage apps** with an admin user's API key. In Audiobookshelf, go to **Settings**,
  **API Keys**, then **Add API key**, for an admin user. Then add the key to the app in Starboard. Read
  [Change or remove an app](change-or-remove-an-app.md).
- Each person has a user in Audiobookshelf.
- You have the address of the server to copy from, and one of these:
  - for Plex: your Plex token, which reads your own account only;
  - for Jellyfin or Emby: an API key from its **Dashboard**, **API keys**, which reads every user;
  - for another Audiobookshelf: an admin's API key from its **Settings**, **API Keys**, which reads every
    user.

## Steps

### Read the progress

1. Go to **Settings**, then **Apps**, then **Audiobookshelf**.
2. In **Copy listening progress**, choose where the progress comes from in **Read from**.
3. Enter the **Server address**, such as `http://192.168.1.20:8096`, and the **Token or API key**.
4. Select **Read the progress**.

Starboard shows "Reading the progress. This can take a minute or two." When it ends, it shows **Progress
read** and a table of the accounts it found, with how many books each one has started and finished.

### Match each account to an Audiobookshelf user

1. In the table, find **Goes to Audiobookshelf user** for each account.
2. Choose the Audiobookshelf user the account belongs to, or **Do not copy** to leave it out. For example,
   the Jellyfin account `alex` goes to the Audiobookshelf user `Alex`.
3. If accounts have the same names in both places, select **Match accounts with the same name**.

Each choice saves straight away.

### Apply the progress

1. Select **Apply now**.
2. When it ends, the **Applied** column shows how many books each account received.

To keep applying progress as new books are scanned in, activate **Keep applying every hour**.

## Things to note

- Progress a person already has in Audiobookshelf is never changed, and each book is copied once.
- Books are matched by their ASIN (Amazon's book number), then their ISBN, then their title and author, then
  their folder. **How Starboard copies progress** on the page says the same.
- A book in several files becomes one position. If the two copies are different lengths, the position is
  scaled to fit.
- From Plex, Starboard reads music libraries with "book" in their name, or that use the Audnexus agent. From
  Jellyfin or Emby, it reads audiobooks in a Books library.
- Audiobookshelf keeps progress for each person separately. To write it, Starboard makes a short-lived key
  for each person and deletes it straight after. Any key left behind stops working after 15 minutes.

## If it does not work

- **"Give Audiobookshelf an admin API key first":** add the key, as in
  [Before you begin](#before-you-begin). You can read progress before that, but not apply it.
- **"Starboard cannot reach Audiobookshelf":** check its address and API key in **Manage apps**. Read
  [An app shows as not responding](app-not-responding.md).
- **"Reading did not work":** check the server address and the token or API key, then select **Read the
  progress** again.
- **Books not found in Audiobookshelf:** Starboard could not match these books. Either they are not scanned in
  yet, or their details differ. Check the title, author or ASIN in Audiobookshelf. The next apply picks them up.

## Find out more

- [Import watch history into Jellyfin](import-watch-history.md)
- [Move from Plex to Jellyfin and Audiobookshelf](../guides/move-from-plex-to-jellyfin.md)
- [What an API key is](../basics/what-is-an-api-key.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
