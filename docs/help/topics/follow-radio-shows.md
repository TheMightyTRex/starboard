[Help centre](../README.md) · Everyday use · how-to

# Follow radio shows and podcasts

Reelix follows radio shows and podcasts for you. It downloads each new episode into the radio folder, and you
listen in Audiobookshelf. Starboard shows what is due in Coming up, and episodes downloading in Downloads.

## Before you begin

- Reelix and Audiobookshelf are installed. **Basics**, **Full install** and **Everything** install both, with
  the radio folder. If you chose the apps yourself, choose **Radio** in **Install apps**. Read
  [Install apps with Starboard](install-apps.md).
- To listen, Audiobookshelf needs a podcast library at the radio folder. Read
  [Listen in Audiobookshelf](#listen-in-audiobookshelf).

## Steps

### Find and follow a show

![The Search page with example data, with Search in the side menu (step 1), the search box (step 2) and Follow beside a radio show under Not in your library (step 3) outlined](../images/follow-radio-shows-1-search-link.png)

1. Select **Search** in the side menu. On a phone, select **Search** in the header.
2. Enter the show's name, such as `Morning Story`. Your library is searched first, so you can check whether you
   follow it already.
3. Under **Not in your library**, **Radio** lists the shows Reelix found. Select **Follow** beside the one you want.
4. In **Get**, choose **Every episode, old and new**, or **New episodes only**.
5. Select **Follow this show**. The button beside it changes to **Following**, and the show appears in **Library**,
   **Radio** within a few minutes. Reelix looks for each episode as it is broadcast.

### Listen in Audiobookshelf

When Starboard sets up Audiobookshelf, it adds a **Radio** podcast library at `/media/radio` for you. If you set
up Audiobookshelf yourself, do this once. After that, every episode Reelix downloads appears in Audiobookshelf.

1. Open Audiobookshelf and sign in as its administrator.
2. Go to **Settings**, then **Libraries**, and select **Add Library**.
3. Enter a name, such as `Radio`, and choose **Podcasts** as the media type.
4. Add the folder `/media/radio`, then select **Create**.

### Check what is due and what is downloading

![The Coming up page with example data, with Discover (step 1), the Reelix filter (step 2) and The Example Hour, Series 4, episode 1, Tides (step 3) outlined](../images/follow-radio-shows-2-coming-up.png)

1. Go to **Discover**, then **Coming up**. Episodes of the shows you follow are listed by the day and time they
   are broadcast, with a radio icon.
2. Optional: to show radio only, select **Reelix**. Select it again to show every app.
3. Select an episode to open its details. **Open in Reelix** opens the show's page in Reelix, in a new tab.

![The Downloads page with example data, with Activity (step 4) and The Example Hour, Lighthouses, downloading in Reelix (step 5) outlined](../images/follow-radio-shows-3-downloads.png)

4. Go to **Activity**, then **Downloads**, then **Queue**.
5. A radio episode shows the show's name and the episode's name, with **Reelix** as its app. Select it to see
   its details, find another copy or remove it, as for any download. Read
   [Pause, resume and remove downloads](manage-downloads.md).

## Bring in shows you already have

Radio shows already in Audiobookshelf's Radio library can come into your library without downloading them again.

1. If **Library**, then **Radio** says Reelix does not read Audiobookshelf's Radio library yet, select **Connect it**.
   In [Settings, Reelix, Radio](change-reelix-settings.md), select **Connect Audiobookshelf's Radio library** and type
   your Reelix password. This is needed once.
2. Back on **Library**, then **Radio**, select **Bring them in**.
3. Choose what Reelix gets for each show: **Every episode** (it fills the gaps), **New episodes** or **Only what you
   have**.
4. Check each match. A show is ticked only when its match has the same title; check any other match before you tick
   it. A show no radio source knows says **No match found**.
5. Select **Bring in the ticked ones**. Reelix matches your files to each show's episodes. Nothing is moved.

## Things to note

- Reelix files each episode in `media/radio`, inside the data folder. Audiobookshelf sees the same folder as
  `/media/radio`.
- Coming up reads the 20 shows Reelix checked most recently. Shows beyond those are still followed and
  downloaded, but Coming up does not list them.
- Every show you follow is in **Library**, **Radio**, with its episodes, newest first. Read
  [Browse your library](browse-your-library.md).
- To change how Reelix follows a show, open it in **Library**, then **Radio**. In **Following**, choose **Every
  episode**, **New episodes from now on** or **Not following**.
- Coming up and Downloads need the key Starboard made when it set up Reelix. A Reelix you added by hand shows no
  radio until you add its API key to the **Reelix** entry in **Settings**, then **Apps**, then **Manage apps**. Read
  [Find an app's API key](find-an-api-key.md).

## If it does not work

- **No Radio under Not in your library:** Starboard has no Reelix with its key. Install Reelix in
  **Install apps**, or add it in **Settings**, then **Apps**, then **Manage apps**.
- **No radio in Coming up:** none of the shows you follow has an episode due in that time. Choose a longer time
  in **How far ahead**. Read [Find out what is coming up](coming-up.md).
- **Episodes download but are not in Audiobookshelf:** check the podcast library's folder is `/media/radio`.
  In Audiobookshelf, select the library, then **Scan**.
- **A warning about Reelix:** Reelix did not answer. Read [An app shows as not responding](app-not-responding.md).

## Find out more

- [Find out what is coming up](coming-up.md)
- [Pause, resume and remove downloads](manage-downloads.md)
- [Install apps with Starboard](install-apps.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
