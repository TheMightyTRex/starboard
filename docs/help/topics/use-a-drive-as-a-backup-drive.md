[Help centre](../README.md) · Your server · how-to
<!-- help: use / server -->

# Use a disk as a backup disk

A backup disk is not part of the pool: it protects it. Starboard offers two kinds, parity and copy.

## Which kind

| | Parity, with SnapRAID (recommended) | Copy, with rsync |
|---|---|---|
| Disks needed | One, at least as big as the biggest pool disk | Enough space for the folders copied |
| Protects | Every disk in the pool: one failed disk can be rebuilt | The folders you choose |
| Readable on its own | No: the files are rebuilt from it with the other disks | Yes: a plain copy |
| When | Every night at 02:00 | Every night at 02:00 |
| Files deleted in the pool | Can be got back until the next check | Moved to a dated `.removed` folder on the copy disk |

**Neither is a full backup on its own.** The backup disk is in the same computer, so keep a third copy of what
matters somewhere else. Read [Pools are not backups](../basics/what-is-a-drive-pool.md#pools-are-not-backups).

## Before you begin

- The pool has at least one disk. Read [Add a disk to the pool](add-a-drive-to-the-pool.md).
- For parity, the computer has SnapRAID:

  ```bash
  sudo apt install snapraid
  ```

- Note the last 4 characters of the disk's serial number. A parity disk is always erased first.
- The page erases only a blank disk. If the disk has a partition table or files, you finish in a terminal on the
  server: read [Erase a disk that has files](add-a-drive-to-the-pool.md#erase-a-disk-that-has-files).
- Have your Starboard password ready.

## Steps

1. Go to **System**, then **Storage**, then **Pool**, and select **Add a disk**.
2. Choose the disk, then select **Continue to What it is for**.
3. Under **Use it**, select **Parity disk (recommended backup)** or **Copy disk**.
4. For a copy disk, enter the folders in the pool to copy, with commas between them, such as `media, photos`.
5. Select **Continue to Check**, read the check, then select **Continue to Confirm**.
6. Enter the end of the serial number if the disk is being erased, and your Starboard password.
7. Select **Erase and use as a backup disk**, or **Add the disk**.

The first check runs that night at 02:00. Parity's first check reads every disk and can take many hours.

## Things to note

- **Backup disks** on the Pool page shows the last check and its result, in words.
- If more than 5% of the files were deleted since the last check, the parity check does not run, so they can
  still be got back. Starboard says so. Check the pool; the next night's check then runs as usual.
- Once a week the parity check also re-reads 8% of the files, to find damage early.
- To stop using a backup disk, select **Stop using** beside it. The disk is not erased. Without a parity disk,
  nothing can rebuild a failed pool disk.

## If it does not work

- **Parity disk is not offered:** the disk is smaller than the biggest pool disk, or the pool is empty.
- **Install these first: snapraid:** install SnapRAID, then try again.
- **/etc/snapraid.conf was not written by Starboard:** SnapRAID is already set up by hand on this computer, and
  Starboard leaves it alone.
- **Check failed:** read the message on the Pool page, then [A pool disk has failed](a-pool-drive-has-failed.md).

## Find out more

- [Back up the whole server](back-up-the-server.md)
- [A pool disk has failed](a-pool-drive-has-failed.md)
- [What a disk pool is](../basics/what-is-a-drive-pool.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
