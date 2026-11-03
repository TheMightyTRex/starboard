[Help centre](../README.md) · Apps · reference

# Find an app's API key

Each app keeps its API key in its own settings. This article lists where to find it in the apps Starboard
works with. Copy the key, then paste it into the **API key** field when you
[add an app](add-an-app.md).

## Before you begin

- The app is running and you can open its web page.
- If an API key is new to you, read [What an API key is](../basics/what-is-an-api-key.md).

## Where each app keeps its key

| App | Where to look in the app |
|---|---|
| Sonarr | **Settings**, then **General**, **API Key** |
| Radarr | **Settings**, then **General**, **API Key** |
| Lidarr | **Settings**, then **General**, **API Key** |
| Readarr | **Settings**, then **General**, **API Key** |
| Prowlarr | **Settings**, then **General**, **API Key** |
| Bazarr | **Settings**, then **General**, **API Key** |
| Seerr, Jellyseerr or Overseerr | **Settings**, then **General**, **API Key** |
| SABnzbd | **Config**, then **General**, **API Key** |
| qBittorrent | **Options**, then **Web UI**, **API key**. This needs qBittorrent 5.2 or later. |
| Jellyfin | **Dashboard**, then **API keys**. Make a new key and name it Starboard. |
| Audiobookshelf | **Settings**, then **API Keys**, signed in as an admin user. |

The hint under the **API key** field in Starboard repeats where to look for the kind of app you chose.

## Steps

1. Open the app's own web page.
2. Go to the place the table names for that app.
3. Copy the key. Some apps have a copy button beside it; otherwise select the whole key and copy it.
4. In Starboard, paste the key into **API key** and select **Test connection**.

## Things to note

- Jellyfin and Audiobookshelf keys are optional. Jellyfin's key adds what is playing and what was added to
  **System**. Audiobookshelf's key is needed only to
  [copy listening progress](copy-listening-progress.md).
- **Other app** has no API key. Starboard only checks that its page answers.
- With Docker access, **Search for new apps** can read the keys of Sonarr, Radarr, Lidarr, Readarr, Prowlarr,
  SABnzbd and Seerr for you. Read [Search for apps already on your server](search-for-new-apps.md).
- Treat an API key like a password. Anyone with it can control that app.
- Menu names can differ a little between versions of an app. If you cannot find the key, look in the app's
  general or security settings.

## Find out more

- [Add an app](add-an-app.md)
- [What an API key is](../basics/what-is-an-api-key.md)
- [The apps Starboard works with](../basics/the-apps.md)
