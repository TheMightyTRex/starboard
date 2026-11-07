[Help centre](../README.md) · Your server · how-to

# Check free space and what is using it

The Storage page shows how full each of your folders or drives is, and can sort the space by type, such as TV,
films and books. Use it to see how much room is left before a drive fills up.

## Before you begin

Starboard can only see the folders you gave it. Give them in one of these ways:

- **With the installer:** run `./install.sh` again and answer Yes to **Choose folders to show?** Type each
  folder as a name and a path, such as `Media=/mnt/media`. Press Enter on an empty line to finish. Read
  [Change what Starboard can access](change-what-starboard-can-access.md).
- **By hand:** add the folders to `compose.override.yaml` in the Starboard folder. The README in that folder
  shows how, under "Your own folders and disks".
- **With the ready-made image:** take the `#` off the Storage lines in `compose.image.yaml`. Read
  [Install Starboard from the ready-made image](install-from-the-ready-made-image.md).

Starboard reads these folders but never changes them.

## Steps

1. Go to **System**, then **Storage**.
2. Read the tiles: **Total space**, how much is **Used**, and how many folders are over 90% full.
3. Find each folder in the list, fullest first. Each one says **Healthy**, **Nearly full** or **Not found**.
4. Select a folder to see its path, its file system, and how much is used and free.

### Sort the space by type

1. On the Storage page, find **What is using the space**.
2. Select **Sort by type now**. The button says **Sorting by type…** while Starboard reads the folders.
3. Wait. A large drive can take a few minutes. The charts then show the space by type, with free space.

To sort again later, select **Sort by type again**.

## Things to note

- Sorting by type reads every file name in your folders, so it runs only when you choose. To run it on a
  schedule, go to **Settings**, then **Performance**, and change **Work out what uses the space**. Besides
  **Only when I press Sort by type**, you can choose **When I open Storage, if over a day old**, **Every night
  at 3 am**, **Every week, at 3 am** or **Off**.
- **Space used over time** needs **Daily record of used space** active in **Settings**, then
  **Performance**. It shows a forecast of when the space runs out.
- **Drives in the pool** lists each drive in a pool, fullest first, when several drives are joined into one.
- **Drives in this computer** lists every drive and where it is used. It needs Disk health set up. Read
  [Check your disks' health](check-disk-health.md).
- A file shared by a download and the library counts once, for the library.
- A drive with a Windows file system, such as NTFS, is marked as slower on Linux.

## If it does not work

- **No folders set up yet:** Starboard has no folders to show. Give it some as in "Before you begin".
- **Starboard cannot find this folder:** the folder is missing, or not shared with Starboard. Check the path,
  then run `./install.sh` again or check `compose.override.yaml`.
- **Sorting by type is inactive:** **Work out what uses the space** is set to **Off**. Change it in **Settings**,
  then **Performance**.
- **Nearly full:** free some space or add a drive before it fills. Downloads stop when there is no room. To be
  told before this happens, read [Activate alerts](activate-alerts.md).

## Find out more

- [Check your disks' health](check-disk-health.md)
- [Make Starboard use less of your server](make-starboard-lighter.md)
- [Change what Starboard can access](change-what-starboard-can-access.md)
- [What a home server is](../basics/what-is-a-home-server.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
