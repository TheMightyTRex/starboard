[Help centre](../README.md) · The basics
<!-- help: use / server -->

# What a disk pool is

A disk pool joins several disks into one folder. Instead of films on one disk and series on another, the apps
find one folder, `/mnt/pool`, with everything in it. It is like a bookcase made of several shelves: you find a
book on the bookcase, not on a particular shelf.

## How Starboard makes one

Starboard uses mergerfs, a small program that shows the disks' folders as one. Each disk stays a normal disk
with its own files on it, so:

- disks can be different sizes, and can be added one at a time;
- each disk can still be read on its own, in any Linux computer;
- if a disk fails, only the files on that disk are missing, not the whole pool.

New files go to the disk with the most free space. Balancing moves whole folders between disks to even them out:
read [Balance the files](../topics/balance-the-files.md).

## Pools are not backups

A pool keeps one copy of each file. A **backup disk** protects the pool:

- **Parity** (SnapRAID) works out, every night, what is needed to rebuild any one failed disk. One parity disk
  protects all the others.
- **A copy** (rsync) is a second, readable copy of the folders you choose.

Both are in the same computer, so keep a third copy of what matters somewhere else: three copies, on two kinds of
storage, one away from home (the 3-2-1 rule). To choose between parity and a copy, read
[Use a disk as a backup disk](../topics/use-a-drive-as-a-backup-drive.md#which-kind).

## Other ways to make a pool

- **Unraid** and **a NAS's own pool** (such as Synology): the pool is made by that system, and Starboard shows
  it.
- **ZFS** and **Btrfs**: file systems that join disks themselves, with their own copies or parity. They need
  disks of the same size and more memory. Starboard leaves them alone.

## Find out more

- [Add a disk to the pool](../topics/add-a-drive-to-the-pool.md)
- [Balance the files](../topics/balance-the-files.md)
- [Use a disk as a backup disk](../topics/use-a-drive-as-a-backup-drive.md)
- [Check your disks' health](../topics/check-disk-health.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
