[Help centre](../README.md) · Your server · how-to

# Check your disks' health

The Disk health page shows each drive's own health report, its temperature and its age. Drives often warn of
trouble weeks before they fail, so a quick look here can save your files.

## Before you begin

- Disk health is set up. Run `./install.sh` again and answer Yes to **Set up Disk health reports?** Read
  [Change what Starboard can access](change-what-starboard-can-access.md).
- The installer asks for your computer's password for this step, because reading a drive's report needs
  administrator rights. You type it in the terminal yourself.
- The computer needs smartmontools, the program that reads the reports. The installer installs it for you if it
  is missing. To install it yourself first, on Ubuntu, Debian and Linux Mint:

  ```bash
  sudo apt install smartmontools
  ```

Once set up, a small job on the server reads every drive every 30 minutes. Starboard only reads the reports it
saves.

## Steps

1. Go to **System**, then **Storage**, then **Disk health**.
2. Read the tiles: how many drives are **To check**, the **Hottest** drive and the **Oldest** drive.
3. Find each drive in the table, most urgent first. Its **Status** is one of these:
   - **Healthy:** nothing to do.
   - **Needs attention:** the drive has counted problems, such as damaged areas.
   - **Failing:** the drive failed its own health check.
   - **Not reported:** the report has no health result.
4. To see everything about one drive, select **SMART report** in its row. SMART (Self-Monitoring, Analysis and
   Reporting Technology) is the drive's own health record.
5. Read the advice in the report, then select **Download the full report** if you want to keep a copy.

### Read the drives now

Select **Read disks now** to ask for new reports straight away. The button says **Reading the disks…**, and the
new reports arrive in about a minute.

## Things to note

- **Temperature:** under 45°C is fine for a hard disk. Hot drives wear out sooner, so check the airflow around
  them.
- **Powered on:** plan to replace a drive after about 5 years.
- **Temperature, last 30 days** in each report is a chart of hourly readings. Starboard takes them while Disk
  health is open, or while it watches in the background.
- **Recent events** lists self-tests and changes, newest first.
- To be told when a drive reports a problem, read [Activate alerts](activate-alerts.md).
- With the ready-made image, Disk health is set up by hand. The README in the Starboard repository explains how.

## If it does not work

- **Disk health is not set up:** answer Yes to **Set up Disk health reports?** in `./install.sh`.
- **No SMART reports yet:** the job has not run yet. Wait up to 30 minutes, then select **Check again**.
- **No Read disks now button:** Starboard cannot ask for a reading. Run `./install.sh` again to set Disk health
  up afresh.
- **Failing:** back up what is on the drive now, and replace it.
- **Needs attention:** back up what is on the drive and plan to replace it. Check again after the next report to
  see if the counts are rising.

## Find out more

- [Check free space and what is using it](check-storage.md)
- [Activate alerts](activate-alerts.md)
- [Back up the whole server](back-up-the-server.md)
- [The terminal: typing commands](../basics/the-terminal.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
