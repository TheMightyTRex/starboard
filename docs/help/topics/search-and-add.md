[Help centre](../README.md) · Everyday use · how-to

# Search for and add films, series, music and books

Search looks in your library first, so you see straight away whether you already have something. Below that,
under **Not in your library**, it lists what Reelix can find, and you add it with one button. Radio shows and
podcasts have **Follow** instead.

## Before you begin

- Reelix is in Starboard with its key. Install apps adds it for you. Read [Install apps](install-apps.md).
- Without Reelix, Search looks in Sonarr, Radarr, Lidarr and Readarr instead. Read [Without Reelix](#without-reelix)
  below.

## Steps

![The Search page with example data before anything is typed, with Search in the side menu (step 1) and Your library with each kind and its count (step 2) outlined](../images/search-and-add-1-start.png)

1. Select **Search** in the side menu. On a phone, select the search button at the top of the screen, or type in
   the search box in the menu. Typing in the search box at the top of any page also opens Search.
2. Before you type, Search shows your library: **Recently added**, then each kind with how many you have, such as
   **Films** and **64 films**. Select a kind to open it in the Library.

![The Search page with example data after typing harbour, with the search box (step 3), In your library (step 4) and an Add button under Not in your library (step 5) outlined](../images/search-and-add-2-results.png)

3. Type at least two letters of the name, such as `harbour`. You do not need to select **Search**: results appear as
   you type.
4. **In your library** lists what you already have, by kind, with whether each one is in your library, wanted or
   not released yet. Select a title to open its page, or **See all** to see every match in the Library.
5. **Not in your library** lists what Reelix finds that you do not have, by kind. Select **Add** beside the one you
   want. For a radio show or podcast, select **Follow**. Read
   [Follow radio shows and podcasts](follow-radio-shows.md).

![The Add panel with example data, with Quality (step 6), Folder (step 7) and Add to Reelix (step 9) outlined](../images/search-and-add-3-add.png)

6. In the panel, choose the **Quality**: how good a copy Reelix looks for.
7. Choose the **Folder** it goes in. Each folder shows the free space on its drive. For a book, choose
   **Ebook**, **Audiobook** or both.
8. Leave **Start looking for it now** on, so Reelix looks for it straight away. Turn it off to add it now and look
   later.
9. Select **Add to Reelix**. The button beside it changes to **Added**, and it appears in the Library within a few
   minutes.

## Things to note

- Each search has its own address, such as `http://192.168.1.20:8095/search.html?q=harbour`, so you can bookmark
  or share a search.
- Searching your library reads Starboard's own list, so it is quick. **Not in your library** asks Reelix, which asks
  sites such as TMDB (The Movie Database) and Open Library, so it can take a few seconds. Each kind appears as soon
  as it is ready.
- Reelix needs a TMDB key to look up some films and series. Without one, Search may say so under
  **Not in your library**. Books, music and radio need no key.
- Covers come through Starboard, so your browser never contacts the image sites.

## Without Reelix

When Starboard has no Reelix with a key, Search looks in every Sonarr, Radarr, Lidarr and Readarr you have added.
Type the name and select **Search**. Select **Add** beside a result, check the **Quality profile**, **Folder** and
**Start searching for it now**, then select **Add to** and the app's name, such as **Add to Radarr**. A result you
already have says **In library**. Read [Add an app](add-an-app.md).

## If it does not work

- **Nothing in your library matches:** check the spelling, or try fewer words. The Library may still be reading
  from Reelix: wait a minute and type again.
- **Reelix found nothing else:** check the spelling, or try fewer words.
- **Reelix cannot look up films until it has a TMDB key:** add a TMDB key to Reelix. Read
  [Change your install](change-your-install.md).
- **Reelix has no folder for this kind yet:** Reelix needs a folder for films, series, books or music before it can
  add one. Run **Install apps** again, or read [Change your install](change-your-install.md).
- **Some results may be missing** (without Reelix): one of your apps did not answer. Select **View apps** to see
  which one. Read [An app shows as not responding](app-not-responding.md).

## Find out more

- [Browse your library](browse-your-library.md)
- [Follow radio shows and podcasts](follow-radio-shows.md)
- [Pause, resume and remove downloads](manage-downloads.md)
- [Find out what is coming up](coming-up.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
