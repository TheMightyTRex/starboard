[Help centre](../README.md) · Apps · how-to

# Update your apps

**Apps**, **Updates** checks whether each app has a newer version and installs it for you. Each app restarts
for a moment while it updates, and anything that depends on it restarts too.

## Before you begin

- Starboard has Docker access. Without it, the page says **Starboard cannot see your containers**. Read
  [Change what Starboard can access](change-what-starboard-can-access.md), and
  [What Docker is](../basics/what-is-docker.md) if Docker is new to you.
- Your apps run in Docker and were started with Docker Compose.

## Steps

1. Go to **Apps**, then **Updates**. The page lists every app in the same categories as the Apps page, with its
   **Image**, the **Installed** version, the **Latest** version and a **Status**.
2. Select **Check again**. Starboard asks the registry each app comes from, where its downloads live, for a newer version. This
   can take a minute.
3. Read each app's **Status**: **Update available**, **Up to date**, or **Big change: check first**.
4. To update one app, select **Update** for it. To update every app marked **Update available**, select
   **Update all**.
5. Starboard asks you to confirm. Select **Update** and the app's name, or **Update** and the number of apps.
6. Wait while the status shows **Downloading**, then **Installing**. When it shows **Updated**, the app is
   running the new version.

## Things to note

- **Big change: check first** means the first number of the version changes, such as from 4 to 5. A big change
  can need changes to the app's settings. Read the app's own release notes, then select **Update** for it.
  **Update all** leaves these out.
- An app pinned to a version, such as `v1.4.2`, is offered the newest higher version. Starboard copies the
  Compose file before it changes the version in it, and adds `.bak-` and the date to the copy's name.
- Starboard finds each app's container by its name. If it shows **No container found**, edit the app in
  **Settings**, **Manage apps** and choose it in **Container**.
- After an update, Starboard removes the old version's download if nothing else uses it.
- **What the last update did** shows the log of the last update.

### Run a backup before an update

You can make Starboard run a script before it updates an app, such as a database backup. Put a script called
`<service>.sh` in a folder called `starboard-before-update`, inside the folder that holds the app's Compose
file. Replace `<service>` with the app's name in the Compose file. If the script fails, nothing changes.
[Install apps with Starboard](install-apps.md) adds these scripts for you where an app needs one.

## If it does not work

- **Cannot check:** Starboard could not reach the place the image comes from, or the image was built on this
  computer. Try **Check again** later.
- **Update failed:** open **What the last update did** to see why. Fix what it says, then select **Update**
  again. Read [Read the log and report a problem](read-the-log.md) if you need help.

## Find out more

- [Update Starboard](update-starboard.md)
- [Install apps with Starboard](install-apps.md)
- [Back up the whole server](back-up-the-server.md)
- [What Docker is](../basics/what-is-docker.md)
