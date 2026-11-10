[Help centre](../README.md) · The basics

# What Starboard is

Starboard is a dashboard for a home media server: one place that shows all your media apps, whether each one is
working, and what they are doing. Think of it as the front desk of a hotel. Behind it, many rooms are busy, but
you only need to visit the desk to find out what is going on and to ask for something.

## The problem it solves

A home media server runs several apps. One finds what you want, another downloads it, and another plays it on your
television. Each app has its own address and its own settings. Starboard installs them, sets them up and puts them
all in one place, behind one password.

## What you can do with it

- **Start from your dashboard.** The **Dashboard** shows cards for your apps, downloads and server. Read
  [Use and change the dashboard](../topics/use-the-dashboard.md).
- **Every app at a glance.** The **Apps** page shows each app, and whether it is responding.
- **Search once.** **Search** finds films, series, music and books, and adds what you choose. Read
  [Search for and add films, series, music and books](../topics/search-and-add.md).
- **Follow downloads.** **Activity**, **Downloads** lists what is downloading, and can pause and resume it.
- **What is coming up.** **Discover**, **Coming up** lists new episodes, films and albums due soon.
- **Check the server.** **System** shows free space, disk health, what each app is using and the log.
- **Get alerts.** Starboard can send you a message when an app stops answering or a disk gets full.

For the full list, read [Everything Starboard does](../topics/everything-starboard-does.md).

If these app names are new to you, read [The apps Starboard works with](the-apps.md).

## Find your way around

Starboard's menu has three levels:

1. **The side menu**, beside every page on a computer, has the Starboard logo, **Search** and six sections:
   **Home**, **Library**, **Discover**, **Activity**, **System** and **Settings**. The logo opens the **Apps** page.
   At its foot are the version, **Update** when one is out, and **Feedback**.
2. **The level 1 menu**, along the header, lists the pages in the section you chose. It starts with your
   server's name, if you gave it one in **Settings**, then **General**.
3. **The level 2 menu**, under the level 1 menu, lists a page's own tabs. Only pages with tabs have one.

In this help, a place is written as its path: **Settings**, then **Apps**, then **Jellyfin** means the Settings
section, its Apps page, then the Jellyfin tab.

On a phone, select the **Menu** button in the header. It lists the sections, each with its pages.

The **Library** and a few other places say they come with Reelix. They fill in once Starboard reads Reelix.

## Light on your server

Starboard is built for smaller servers, such as a Raspberry Pi or an old laptop. It uses about 16 MB of memory
while it is idle, and very little of the processor, so your server's power goes to your apps.

**Settings**, then **Performance**, shows what Starboard uses and lets you deactivate each piece of background
work. Read [Make Starboard use less of your server](../topics/make-starboard-lighter.md).

## Safe by default

Starboard asks before it is given any access to your computer, and every kind of access is optional. One
password protects it. Your API keys stay on the server and are never sent to your browser.

By default, only phones and computers on your home network can open it. To use it away from home, read
[Use Starboard away from home safely](../guides/use-starboard-away-from-home.md).

## What this means for Starboard

Starboard does not replace your media apps. It sits in front of them and talks to each one through its API. If
you do not have any media apps yet, Starboard can install them: read
[Install apps with Starboard](../topics/install-apps.md).

## Find out more

- [What a home server is](what-is-a-home-server.md)
- [The apps Starboard works with](the-apps.md)
- [What you need to run Starboard](../topics/what-you-need.md)
- [Install Starboard on a Linux computer](../guides/install-on-a-linux-computer.md)
- [Build a media server from nothing](../guides/build-a-media-server-from-nothing.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
