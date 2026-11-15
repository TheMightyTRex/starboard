[Help centre](../README.md) · Your server · troubleshooting
<!-- help: fix / storage -->

# A pool drive has failed

When a drive in the pool fails, the pool still works, but the files on that drive are missing. Here is what to do
first and how to get the files back.

```flow
title: Find your answer
start: A pool drive shows Not mounted or Failing
step: Do these first | Pause downloads, keep the drive, check its cable
q: Is the drive back after a restart?
  Yes -> check-disk-health.md
  No -> q2
q2: Which backup do you have?
  A parity drive -> 1
  A copy drive -> 2
  Neither -> 3
1: Rebuild it from the parity drive #with-a-parity-drive
2: Copy the files back #with-a-copy-drive
3: Only that drive's files are lost #with-neither
```

## What happens

- On **System**, **Storage**, **Pool**, the drive shows **Not mounted**.
- On **System**, **Storage**, **Disk health**, the drive shows **Failing** or **Needs attention**, or is not listed.
- Apps report films or episodes as missing.

## What to do first

1. Stop the apps from searching for the missing files again: pause your download apps, or stop Reelix, until the
   drive is back.
2. Do not erase or format the failed drive.
3. Check the cable and the power to the drive, then restart the computer. A loose cable is a common cause.

## With a parity drive

Fit a new drive at least as big as the failed one, and follow the SnapRAID manual's steps to recover a failed disk
(`snapraid fix`). Starboard does not do this step for you yet. Files added since the last nightly check cannot be
rebuilt.

## With a copy drive

Copy the missing folders back from the copy drive, which is a plain readable copy.

## With neither

Only the files on the failed drive are lost; the rest of the pool is fine. A data recovery service may be able to
read the drive.

## Afterwards

- Take the failed drive out of the pool once its files are back. Read
  [Take a drive out of the pool](take-a-drive-out-of-the-pool.md).
- If you have no backup drive, add one. Read [Use a drive as a backup drive](use-a-drive-as-a-backup-drive.md).

## Find out more

- [Check your disks' health](check-disk-health.md)
- [Activate alerts](activate-alerts.md)
- [Use a drive as a backup drive](use-a-drive-as-a-backup-drive.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
