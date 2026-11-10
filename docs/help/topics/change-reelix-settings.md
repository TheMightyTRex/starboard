[Help centre](../README.md) · Apps · how-to

# Change Reelix's settings in Starboard

**Settings**, **Apps**, **Reelix** shows Reelix's own settings, so you do not need Reelix's pages. Reelix keeps
them behind its admin password, so each section asks for it before it opens.

## Before you begin

- Reelix is on your dashboard. [Install apps with Starboard](install-apps.md) adds it, or
  [add your own Reelix](add-an-app.md).
- You know Reelix's admin password. If Starboard set Reelix up, it is the same as your Starboard password.

## Steps

### Open a section

1. Go to **Settings**, then **Apps**, then **Reelix**. The page opens on **Basic settings**, **Sites to
   search** and, in the full version of Reelix, **YouTube and Spotify**.
2. For any other section, activate **Advanced settings**. The sections are in
   [Which settings are where](#which-settings-are-where).
3. In the section, select its **Show** button, such as **Show sites to search**.

   ![Settings, Reelix, with Show sites to search (step 3) outlined](../images/change-reelix-settings-1-show.png)

4. Enter your **Reelix password**, then select **Continue**. If your Reelix admin user is not called `admin`,
   open **Another Reelix user** and enter its name first.

   ![The Enter your Reelix password dialog, with Reelix password (step 4) outlined](../images/change-reelix-settings-2-password.png)

### Change a site, media server or download app

**Sites to search**, **Media servers**, **Download apps**, **Notifications** and **Lists** are lists, with each
one's state.

1. To change one, select **More** (three dots) beside it, then **Change**. To add one, select the button under
   the list, such as **Add a site to search**, then choose one.
2. Change the fields. **More settings** holds the ones most people leave as they are.
3. Select **Test**. Reelix tries the settings and says whether **The test passed**.
4. Select **Save**.

   ![The Change 1337x panel, with Test (step 3) outlined beside Save](../images/change-reelix-settings-3-form.png)

### Change the other settings

- **Basic settings** save each change as soon as you choose it. The TMDB key has its own **Test the key** and
  **Save the key**.
- The other sections are forms. Change the fields, then select **Save**.

## Things to note

### Which settings are where

Shown at first:

- **Basic settings**: the TMDB key, **Picture quality**, **Language** and **Who can ask**.
- **YouTube and Spotify**, in the full version only.
- **Sites to search**. Read [Choose the sites Reelix searches](choose-sites-to-search.md).

Under **Advanced settings**:

- **Media servers**. Read [Connect Reelix to Jellyfin and Audiobookshelf](connect-reelix-to-media-servers.md).
- **Download apps**, **Naming and background work**, **Folders**, **Notifications** and **Lists**.
- **Information**: **Language of details** and **Region**, each chosen from a list.
- **Files**, **Requests**, **People**, **Books** and **Music**.

**Version** says which Reelix runs. Read [Switch between the two versions of Reelix](switch-reelix-version.md).

### Passwords and secrets

- Starboard does not keep Reelix's password. It signs in to Reelix for each change, then signs out. The page
  remembers the password for 5 minutes, so a few changes in a row ask once.
- A secret, such as an API key or a password, shows empty when you change something. Leave it empty to keep
  the one Reelix has. If you change the address, Reelix asks for the secret again.
- **Remove** asks first. Reelix stops using that one and forgets its settings.
- Reelix's warnings show on **Apps**, in Reelix's details and on **System**, each with a link to the section
  that fixes it.

## If it does not work

- **Reelix did not accept that password:** check it and enter it again. If you changed the admin password in
  Reelix, use that one.
- **Too many attempts:** wait 15 minutes, then try again.
- **Reelix is not on your dashboard:** add Reelix first. Read [Add an app](add-an-app.md).
- **Reelix could not be asked:** check that Reelix is running on **Apps**.

## Find out more

- [Choose the sites Reelix searches](choose-sites-to-search.md)
- [Connect Reelix to Jellyfin and Audiobookshelf](connect-reelix-to-media-servers.md)
- [Switch between the two versions of Reelix](switch-reelix-version.md)
- [Update your apps](update-your-apps.md#updates-for-reelix)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
