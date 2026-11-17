[Help centre](../README.md) · Guides
<!-- help: start / install -->

# Set up your dashboard after installing

This guide takes you from a new password to a working media server with the default install: Starboard and
Reelix Lite, with the apps they need to find, download and play your films, series, books, audiobooks, music and
radio. It takes about 20 minutes, most of it waiting for downloads.

This page covers the default install, **Basics**. More apps are in [Add more apps](#add-more-apps), and what you
can change later is in [More options](#more-options).

## Before you begin

- Starboard is installed and you have chosen your password. If not, start with
  [Quick start: one command sets up everything](quick-start.md).
- An account with a VPN (virtual private network) provider is recommended. Downloads go through it, so your
  internet provider and other people sharing torrents cannot tell what you download or find your home internet address.
  You can continue without one and add it later: read [Download without a VPN](../topics/download-without-a-vpn.md).
- Optional: a free TMDB key from themoviedb.org, for film and series posters. You can add it later.

## What the default install has

| App | What it does |
|---|---|
| Starboard | The dashboard: installs, watches and updates the other apps |
| Reelix Lite | Finds, downloads and sorts your films, series, books, audiobooks, music and radio, and takes requests |
| Jellyfin | Plays films, series and music on your television, phone and computer |
| Audiobookshelf | Plays audiobooks and podcasts, keeping your place |
| qBittorrent | Downloads torrents for Reelix |
| NZBGet | Downloads from Usenet for Reelix, once you have a Usenet provider |
| Gluetun | Sends the downloads through your VPN |
| Bazarr | Finds subtitles for your films and series |

Reelix needs at least one download app, and the download apps go through the VPN when you have one. Starboard installs these apps
and connects them to each other for you. Read [The apps Starboard works with](../basics/the-apps.md) for more about
each one.

## The steps at a glance

1. Answer the set-up guide, keeping what it suggests.
2. Start the apps.
3. Finish what is still to set up.
4. Open the dashboard.

```flow
title: The default set-up, in four steps
start: You chose your password
step: Answer the set-up guide | New install, then Basics
step2: Start the apps | A few minutes
step3: Finish what is still to set up | Go through them
end: Open the dashboard
```

## Step 1: Answer the set-up guide

After your password, Starboard opens its set-up guide, **Set up Starboard**. Keep the answer it suggests on each
step, with these few to fill in:

- **How to start:** **New install (recommended)**.
- **Storage:** the media folder it suggests.
- **What to set up:** **Basics (recommended)**.
- **VPN:** **Use my VPN account (recommended)**, then your VPN provider and the details from its website. Without a
  VPN account, choose **Continue without a VPN** and read the warning first.
- **Usenet:** **Not now: torrents are enough for now**, unless you have a Usenet provider.
- **Sites to search:** tick at least one of Reelix's built-in sites. None needs an account.
- **Films and series:** paste your TMDB key, or leave it empty to add it later.

Read [Install apps with Starboard](../topics/install-apps.md) for each of these steps. You can change every answer
later: read [More options](#more-options).

**It worked when** the **Check** step lists your answers. Enter **Your Starboard password** and select **Write the
files**.

## Step 2: Start the apps

On **Start**, select **Start the apps**. Starboard downloads and starts each app and counts them, such as "5 of 7
installed". The first time takes several minutes.

**It worked when** Starboard shows **The apps are running**. The set-up guide then asks a few last questions, such
as **Download hours** and **Alerts and disk health**. Keep its suggestions, then select **Go to Apps**.

## Step 3: Finish what is still to set up

**Still to set up**, on the dashboard and on the **Apps** page, lists anything left, such as finishing Jellyfin's
set-up. Select **Go through them** and take each item in turn. Follow
[Finish what is still to set up](../topics/finish-setting-up.md).

**It worked when** **Still to set up** is no longer on the dashboard.

## Step 4: Open the dashboard

Go to **Home**, then **Dashboard**. It shows your apps, what is playing and what is downloading. Then find
something to watch: follow [Search for and add films, series, music and books](../topics/search-and-add.md).

**It worked when** no app on **System**, then **Apps**, says **Not responding**.

## Add more apps

The default install is complete on its own. Add these only when you want what they do.

- **An app Starboard offers,** such as Jellystat for watch statistics, Kavita for reading ebooks, Wizarr for
  invitations or Tdarr for smaller files: go to **System**, then **Apps**, then **Install apps**, and select **Add**
  beside it under **You can add**. Read [Install apps with Starboard](../topics/install-apps.md).
- **A bigger install,** Full install or Everything, or the version of Reelix with YouTube and Spotify downloads:
  read [Basics, Full install and Everything](../topics/install-types.md), then
  [Change your install](../topics/change-your-install.md).
- **An app you already run yourself,** such as Plex: read
  [Search for apps already on your server](../topics/search-for-new-apps.md) or [Add an app](../topics/add-an-app.md),
  then give it its API key with [Find an app's API key](../topics/find-an-api-key.md).
- **An existing set-up with Sonarr, Radarr, Prowlarr or Seerr:** Reelix does their work, so a new install does not
  have them. Read [Move from Radarr, Sonarr and the others to Reelix](../topics/move-your-apps-to-reelix.md).
- **A plug-in,** such as free Live TV in Jellyfin: read [Add a plug-in](../topics/add-a-plugin.md) and
  [Set up free Live TV in Jellyfin](../topics/set-up-live-tv.md).

## More options

The default install works with all of these as they are. Change them when you want to.

- **Dashboard cards and layouts:** [Use and change the dashboard](../topics/use-the-dashboard.md).
- **Categories on the Apps page:** [Organise apps into categories](../topics/organise-categories.md).
- **Designs, text size, theme and contrast:** [Choose a design for the Apps page](../topics/choose-a-design.md) and
  [Change text size, theme and other display settings](../topics/display-and-accessibility.md).
- **How much Starboard does in the background,** such as the **Small server** preset for a Raspberry Pi:
  [Make Starboard use less of your server](../topics/make-starboard-lighter.md).
- **Alerts on your phone:** [Activate alerts](../topics/activate-alerts.md).
- **Download hours:** [Download only at certain hours](../topics/set-download-hours.md).
- **API keys by hand,** for an app Starboard did not install: [Find an app's API key](../topics/find-an-api-key.md),
  then [Change or remove an app](../topics/change-or-remove-an-app.md#change-an-apps-details).
- **Reelix's sites and settings:** [Choose the sites Reelix searches](../topics/choose-sites-to-search.md) and
  [Change Reelix's settings in Starboard](../topics/change-reelix-settings.md).
- **The set-up guide again:** go to **Settings**, then **General**, then **Names and apps**, activate **More
  settings**, and select **Run the set-up guide again** under **Set-up guide**. Nothing changes until you select **Continue**.

## What next

- [Back up and restore Starboard's settings](../topics/back-up-settings.md), now that it holds your work.
- [Open Starboard from a phone or another computer](../topics/open-from-another-device.md).
- [Get told when something goes wrong](get-told-when-something-goes-wrong.md).
- [What is in each Settings page](../topics/find-a-setting.md).

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
