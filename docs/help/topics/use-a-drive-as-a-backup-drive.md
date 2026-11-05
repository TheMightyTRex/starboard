[Help centre](../README.md) · Your server · how-to

# Use a drive as a backup drive

A backup drive is not part of the pool: it protects it. Starboard offers two kinds, parity and copy.

## Which kind

| | Parity, with SnapRAID (recommended) | Copy, with rsync |
|---|---|---|
| Drives needed | One, at least as big as the biggest pool drive | Enough space for the folders copied |
| Protects | Every drive in the pool: one failed drive can be rebuilt | The folders you choose |
| Readable on its own | No: the files are rebuilt from it with the other drives | Yes: a plain copy |
| When | Every night at 02:00 | Every night at 02:00 |
| Files deleted in the pool | Can be got back until the next check | Moved to a dated `.removed` folder on the copy drive |

**Neither is a full backup on its own.** The backup drive is in the same computer, so a fire, theft or power surge
can take it too. Keep a third copy of what matters somewhere else: three copies, on two kinds of storage, one
away from home (the 3-2-1 rule).

## Before you begin

- The pool has at least one drive. Read [Add a drive to the pool](add-a-drive-to-the-pool.md).
- For parity, the computer has SnapRAID:

  ```bash
  sudo apt install snapraid
  ```

- Note the last 4 characters of the drive's serial number. A parity drive is always erased first.
- Have your Starboard password ready.

## Steps

1. Go to **System**, then **Storage**, then **Pool**, and select **Add a drive**.
2. Choose the drive, then select **Continue to What it is for**.
3. Under **Use it**, select **Parity drive** or **Copy drive**.
4. For a copy drive, type the folders in the pool to copy, with commas between them, such as `media, photos`.
5. Select **Continue to Check**, read the check, then select **Continue to Confirm**.
6. Type the end of the serial number if it is being erased, and your Starboard password.
7. Select **Erase and use as a backup drive**, or **Add the drive**.

The first check runs that night at 02:00. Parity's first check reads every drive and can take many hours.

## Things to note

- The **Backup drives** panel on the Pool page shows the last check and its result, in words.
- If more than 5% of the files were deleted since the last check, the parity check does not run, so they can
  still be got back. Starboard says so. Check the pool, then the next night's check runs as usual.
- Once a week the parity check also re-reads 8% of the files, to find damage early.
- To stop using a backup drive, select **Stop using** beside it. The drive is not erased.

## If it does not work

- **Parity drive is not offered:** the drive is smaller than the biggest pool drive, or the pool is empty.
- **Install these first: snapraid:** install SnapRAID, then try again.
- **/etc/snapraid.conf was not written by Starboard:** SnapRAID is already set up by hand on this computer, and
  Starboard leaves it alone.
- **Check failed:** read the message on the Pool page, then [A pool drive has failed](a-pool-drive-has-failed.md).

## Find out more

- [Back up the whole server](back-up-the-server.md)
- [A pool drive has failed](a-pool-drive-has-failed.md)
- [What a drive pool is](../basics/what-is-a-drive-pool.md)
