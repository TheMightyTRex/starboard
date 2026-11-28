[Help centre](../README.md) · Your server · troubleshooting
<!-- help: fix / storage -->

# A pool disk has failed

When a disk in the pool fails, the pool still works, but the files on that disk are missing. Here is what to do
first and how to get the files back.

```flow
title: Find your answer
start: A pool disk shows Not mounted or Failing
step: Do these first | Pause downloads, keep the disk, check its cable
q: Is the disk back after a restart?
  Yes -> check-disk-health.md
  No -> q2
q2: Which backup do you have?
  A parity disk -> 1
  A copy disk -> 2
  Neither -> 3
1: Rebuild it from the parity disk #with-a-parity-disk
2: Copy the files back #with-a-copy-disk
3: Only that disk's files are lost #with-neither
```

## What happens

- On **System**, **Storage**, **Pool**, the disk shows **Not mounted**.
- On **System**, **Storage**, **Disk health**, the disk shows **Failing** or **Needs attention**, or is not listed.
- Apps report films or episodes as missing.

## What to do first

1. Stop the apps from searching for the missing files again: pause your download apps, or stop Reelix, until the
   disk is back.
2. Do not erase or format the failed disk.
3. Check the cable and the power to the disk, then restart the computer. A loose cable is a common cause.

## With a parity disk

Fit a new disk at least as big as the failed one, and follow the SnapRAID manual's steps to recover a failed disk
(`snapraid fix`). Starboard does not do this step for you yet. Files added since the last nightly check cannot be
rebuilt.

## With a copy disk

Copy the missing folders back from the copy disk, which is a plain readable copy.

## With neither

Only the files on the failed disk are lost; the rest of the pool is fine. A data recovery service may be able to
read the disk.

## Afterwards

- Take the failed disk out of the pool once its files are back. Read
  [Take a disk out of the pool](take-a-drive-out-of-the-pool.md).
- If you have no backup disk, add one. Read [Use a disk as a backup disk](use-a-drive-as-a-backup-drive.md).

## Find out more

- [Check your disks' health](check-disk-health.md)
- [Turn on alerts](activate-alerts.md)
- [Use a disk as a backup disk](use-a-drive-as-a-backup-drive.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
