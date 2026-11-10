[Help centre](../README.md) · Apps · how-to

# Update your apps

**System**, **Apps**, **Updates** checks whether each app has a newer version, and installs it for you. Each app
restarts for a moment while it updates, and so does anything that depends on it.

## Before you begin

- Starboard has Docker access. Without it, the page says **Starboard cannot see your containers**. Read
  [Change access with the installer](change-what-starboard-can-access.md#change-access-with-the-installer), and
  [What Docker is](../basics/what-is-docker.md) if Docker is new to you.
- Your apps run in Docker and were started with Docker Compose.

## Steps

1. Go to **System**, then **Apps**, then **Updates**. The page lists each app's **Image**, **Installed**
   version, **Latest** version and **Status**.
2. Select **Check**, or **Check again** after the first check. Starboard asks where each app's downloads come
   from whether there is a newer version. This can take a minute.
3. Read each app's **Status**: **Update available**, **Up to date** or **Big change: check first**.
4. To update one app, select **Update** for it. To update every app marked **Update available**, select
   **Update all**.
5. Starboard asks you to confirm. Select **Update** and the app's name, or **Update** and the number of apps.
6. Wait while the status shows **Downloading**, then **Installing**. **Updated** means the app is running the
   new version.

## Things to note

- **Big change: check first** means the first number of the version changes, such as from 4 to 5. The app's
  settings may need changes. Read the app's own release notes, then select **Update** for it. **Update all**
  leaves these out.
- **Newer build** in **Latest** means there is a newer build with the same version number.
- An app pinned to a version, such as `v1.4.2`, is offered the newest higher version. Starboard keeps a copy of
  the Compose file first, with `.bak-` in its name.
- Starboard finds each app's container by its name. If it shows **No container found**, edit the app in
  **Settings**, **Apps**, **Manage apps** and choose it in **Container**.
- After an update, Starboard removes the old version's download if nothing else uses it.
- **What the last update did** shows the log of the last update.

### Updates for Reelix

Reelix is updated here like any other app. Its updates come from TheMightyTRex's Reelix, the Lite or full version
that Starboard installed. Reelix never updates itself.

- To have Starboard install new Reelix versions for you, go to **Settings**, then **Updates**, then **Update
  settings**. Under **Reelix updates**, activate **Install Reelix updates automatically**. It is inactive until
  you activate it, and needs Docker access.
- Starboard then updates Reelix once a day at most. It saves Reelix's settings first, and goes back to the
  version before if the new one is not healthy.

### What is new in Reelix

Starboard reads Reelix's own changelog, so you can read what an update brings.

- Before you update, select **What is new** beside **Update** in Reelix's row. A panel lists the changes in each
  version between the installed one and the newest, under **Added**, **Changed**, **Fixed** and other headings.
- After Reelix is updated, a notice on **Apps** and on **Updates** says **Reelix is updated to** and the new
  version. Select **What is new** for the changes, or select the close button to hide the notice.
- The notice appears once **Updates** or **Manage apps** has been opened after the update. That is when Starboard
  reads each container's version.
- Starboard downloads the changelog from GitHub only when you open **What is new**, and keeps it for 6 hours.

### Run a backup before an update

Starboard can run a script before it updates an app, such as a database backup. Put a script called
`<service>.sh` in a folder called `starboard-before-update`, inside the folder that holds the app's Compose file.
Replace `<service>` with the app's name in the Compose file. If the script fails, nothing changes.
[Install apps with Starboard](install-apps.md) adds these scripts for you where an app needs one.

## If it does not work

- **Cannot check:** Starboard could not reach the place the image comes from, or the image was built on this
  computer. Try **Check again** later.
- **Update failed:** open **What the last update did** to find out why. Fix what it says, then select
  **Update** again. If you need help, read [Report a problem](read-the-log.md#report-a-problem).

## Find out more

- [Update Starboard](update-starboard.md)
- [Install apps with Starboard](install-apps.md)
- [Switch between the two versions of Reelix](switch-reelix-version.md)
- [Back up the whole server](back-up-the-server.md)
- [What Docker is](../basics/what-is-docker.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
