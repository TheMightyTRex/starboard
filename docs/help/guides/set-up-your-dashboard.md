[Help centre](../README.md) · Guides

# Set up your dashboard after installing

This guide takes you from a newly installed Starboard to a dashboard that shows all your apps, in your
categories, with the look you want. It is for anyone who has just created their password. It takes about
20 minutes, depending on how many apps you have.

Starboard opens a set-up guide after your first password. It asks the same questions as this guide, one at a
time. You can follow either: this guide also tells you where each choice lives afterwards.

## Before you begin

- Starboard is installed and you can sign in. If not, start with
  [Install Starboard on a Linux computer](install-on-a-linux-computer.md).
- Your media apps are running. If you have none yet, follow
  [Build a media server from nothing](build-a-media-server-from-nothing.md) first.

## The steps at a glance

1. Find the apps already on your server, or add them one at a time.
2. Give each app its API key.
3. Put your apps into categories.
4. Choose a design and display settings.
5. Choose how much Starboard does in the background.
6. Activate alerts.

```mermaid
flowchart LR
    A["1. Add your apps"] --> B["2. Add API keys"]
    B --> C["3. Categories"]
    C --> D["4. Design and display"]
    D --> E["5. Background work"]
    E --> F["6. Alerts"]
```

## Step 1: Find or add your apps

If Starboard has Docker access, it can find the apps on your server for you. Follow
[Search for apps already on your server](../topics/search-for-new-apps.md). Add anything it does not find
with [Add an app](../topics/add-an-app.md).

**It worked when** each app appears on the **Apps** page.

## Step 2: Give each app its API key

An API key lets Starboard read an app's downloads, calendar and queue. Without one, Starboard can only check
whether the app answers. Follow [Find an app's API key](../topics/find-an-api-key.md), then add the key to the
app with [Change or remove an app](../topics/change-or-remove-an-app.md).

**It worked when** **Test connection** in the app's settings says it connected.

## Step 3: Put your apps into categories

Categories are the headings on the **Apps** page, such as Watch or Downloads. Starboard chooses one for each
app, and you can change them. Follow [Organise apps into categories](../topics/organise-categories.md).

## Step 4: Choose a design and display settings

The **Apps** page has five designs. Choose the default for everyone, then make text size, theme and contrast
right for you. Follow [Choose a design for the Apps page](../topics/choose-a-design.md) and
[Change text size, theme and other display settings](../topics/display-and-accessibility.md).

## Step 5: Choose how much Starboard does in the background

On a small server, such as a Raspberry Pi, choose the **Small server** preset. Follow
[Make Starboard use less of your server](../topics/make-starboard-lighter.md).

## Step 6: Activate alerts

Alerts tell your phone when an app stops answering or a disk has a problem. They are inactive until you activate
them. Follow [Activate alerts](../topics/activate-alerts.md).

## What next

- [Back up and restore Starboard's settings](../topics/back-up-settings.md), now that it holds your work.
- [Get told when something goes wrong](get-told-when-something-goes-wrong.md).
- Using Jellyfin? [Set up free Live TV in Jellyfin](../topics/set-up-live-tv.md).

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
