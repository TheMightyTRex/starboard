[Help centre](../README.md) · Everyday use · how-to

# Search for and add films, series, music and books

The Search page looks in every Sonarr, Radarr, Lidarr and Readarr you have added, all at once. Choose a result
and select **Add**, and the right app adds it and, if you like, starts looking for it straight away.

## Before you begin

- At least one of Sonarr, Radarr, Lidarr or Readarr is in Starboard. Read [Add an app](add-an-app.md).
- Optional: each app has its adding options chosen, so Starboard knows which quality profile and folder to
  use. Read the section on adding options in [Add an app](add-an-app.md).

## Steps

1. Go to **Discover**, then **Search**. You can also type in the search box in the header, **Search films, series, music and
   books**, on any page.
2. In the search box, type at least two letters of the name, such as `Harbour Street`.
3. Select **Search**. Starboard lists the results, with how many came from each app.
4. Optional: to see only one kind, select a filter such as **Films** or **Series**. Select it again to see
   everything. The filters appear when the results hold more than one kind.
5. Find the one you want. Each result shows its cover, its kind, its year and the app it would go to. A
   result you already have says **In library**.
6. Select **Add** beside the result. A side panel opens, called **Add** and the name.
7. Check the choices in the panel. They start with the adding options you chose for that app:
   - **Quality profile**: how good a copy the app looks for.
   - **Folder**: where it goes, with the free space on that drive.
   - **Metadata profile**: for music and books only.
   - **Start searching for it now**: on, the app looks for it straight away.
8. Select **Add to** and the app's name, such as **Add to Radarr**. Starboard shows **Added to Radarr**.
9. Select **Back to results** to add something else, or **View downloads** to follow the download.

## Things to note

- Starboard searches only the apps that have **Show on the dashboard** active. Read
  [Change or remove an app](change-or-remove-an-app.md).
- Changes you make in the **Add** panel apply to this one item only. To change what every new item uses, edit
  the app and change its **Adding options**.
- If you deactivate **Start searching for it now**, the app keeps the item but does not look for it. Start the
  search later in the app itself.
- Each search has its own address, such as `http://192.168.1.20:8095/search.html?q=harbour`, so you can bookmark
  or share a search.
- Covers in the results come from the sites your apps use, such as TMDB (The Movie Database).

## If it does not work

- **Type at least two letters:** the search needs two letters or more. Type more of the name.
- **Nothing found:** check the spelling, or try fewer words.
- **Some results may be missing:** one of your apps did not answer. Select **View apps** to see which one. Read
  [An app shows as not responding](app-not-responding.md).
- **Could not load the profiles and folders** in the **Add** panel: the app did not send its lists. Close the
  panel, check the app is running, and try again.
- **Not finding it at all:** the right app may not be in Starboard yet. Select **Add another app to search** on
  the Search page, or read [Add an app](add-an-app.md).

## Find out more

- [Pause, resume and remove downloads](manage-downloads.md)
- [Find out what is coming up](coming-up.md)
- [Approve or decline requests](approve-requests.md)
- [The apps Starboard works with](../basics/the-apps.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
