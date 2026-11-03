[Help centre](../README.md) · The basics

# What an API key is

An API key is a long secret code that one app gives another, so the second app can talk to it. It is like a key
to a friend's house that you get copied for someone you trust: they can let themselves in without knowing your
password, and you can change the lock if you need to.

## What API means

API stands for application programming interface. It is the way apps talk to each other, rather than to people.
When you use Sonarr, you see its web page. When Starboard uses Sonarr, it skips the page and asks Sonarr's API
questions directly, such as "what is downloading?" or "add this series".

## Why an app needs a key

Your apps do not answer just anyone. Before Sonarr answers Starboard, it checks that Starboard has Sonarr's API
key. Without the key, Sonarr says no.

Each app makes its own key. A key usually looks like a jumble of 32 letters and numbers, starting something
like `0a1b2c3d4e5f` and carrying on. Never share your real keys in a message or online.

## Where to find a key

Each app keeps its API key in its own settings. In Sonarr, Radarr, Lidarr, Readarr and Prowlarr it is in
**Settings**, then **General**. Other apps keep it elsewhere. Read
[Find an app's API key](../topics/find-an-api-key.md) for every app Starboard works with.

## Keep keys safe

An API key gives control of the app it belongs to, so treat it like a password:

- Paste it only into apps you trust, such as Starboard.
- Do not post it in a forum, a chat or a screenshot when you ask for help.
- If a key gets out, make a new one in the app. The old key stops working, and you paste the new one into Starboard.

## What this means for Starboard

Starboard needs an API key for most apps before it can show their queues, calendars and warnings, or add films and
series to them. When you add an app, Starboard asks for its key and says where to find it.

The keys you give Starboard stay on your server, in a file only you can read. They are never sent to your browser
or anywhere else.

## Find out more

- [Find an app's API key](../topics/find-an-api-key.md)
- [Add an app](../topics/add-an-app.md)
- [Search for apps already on your server](../topics/search-for-new-apps.md)
- [The apps Starboard works with](the-apps.md)
