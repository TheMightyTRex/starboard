[Help centre](../README.md) · Apps · how-to

# Copy settings from one app to another

**Copy app settings** copies tags, quality settings, folders, download clients and naming from one Sonarr,
Radarr or Lidarr into another. Use it to set up a new app next to an old one, or a second copy such as a 4K
Radarr. You see what will change before anything is copied.

## Before you begin

- Both apps are in **Manage apps**, each with its API key. Read [Add an app](add-an-app.md).
- Both apps are the same kind and the same major version, such as two Radarr version 5.
- You have the passwords of any download clients the old app uses, such as qBittorrent.

## Steps

1. Go to **Settings**, then **Apps**, then **Manage apps**, and select **Copy app settings**.
2. In **Copy from**, choose the old app. In **Copy to**, choose the new one.
3. Under **What to copy**, tick the parts you want. **Naming** and **Media management** are unticked to start
   with, because they replace the new app's settings.
4. Select **Check what will be copied**. For each part, Starboard lists every item as **Will be added**,
   **Already there** or **Will be replaced**.
5. Under **Passwords the old app keeps hidden**, type each download client's password. Leave one empty to add
   that client inactive.
6. Select **Copy**. Starboard shows **Copied**, with what it did, or **Copied, with problems**, with what went
   wrong.

## Things to note

- Nothing already in the new app is changed or removed. An item that is already there by name is left as it is.
  **Naming** and **Media management** are the exception: copying them replaces the new app's.
- **Root folders** must exist inside the new app's container.
- Indexers (the sites your apps search) are not copied. Add the new app in Prowlarr instead, in **Settings**,
  **Apps**, which keeps them in step.
- A download client added inactive needs its password typed in the new app before it works.

## If it does not work

- **Add the new app first:** Starboard needs two apps of the same kind, each with its API key. Add the second
  one in [Add an app](add-an-app.md).
- **Copy only between the same major version:** update the older app first. Read
  [Update your apps](update-your-apps.md).
- **Give the app its API key in Manage apps first:** edit the app and paste its key. Read
  [Find an app's API key](find-an-api-key.md).

## Find out more

- [Install apps with Starboard](install-apps.md)
- [Move Starboard to a new computer](../guides/move-starboard-to-a-new-computer.md)
- [The apps Starboard works with](../basics/the-apps.md)
