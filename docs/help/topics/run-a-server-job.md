[Help centre](../README.md) · Your server · how-to

# Run a server job

Server jobs are tasks that run on the server itself, such as a check of every app and service. Starboard lists
them on System, Overview, shows how each one went, and lets you start one with **Run now**.

## Before you begin

- A job runner is set up on the server, by hand. Starboard does not run jobs itself: it only asks, and the
  runner does the work.
- Starboard knows the runner's folder, set with `STARBOARD_JOBS_DIR`. To use **Run now**, Starboard must be
  allowed to write in that folder's `requests` folder. Both are explained in
  [Back up the whole server](back-up-the-server.md#how-it-works), which uses the same folder.

## Steps

1. Go to **System**, then **Overview**.
2. Find **Server jobs**. Each job shows its name, a short summary and when it last finished.
3. Read the job's state:
   - **Finished:** it ran and finished.
   - **Failed:** it ran and something went wrong.
   - **Running:** it is running now.
   - **Waiting to start:** Starboard has asked, and the runner has not started it yet.
   - **Not run yet:** it has no result yet.
4. To run a job now, select **Run now** beside it. The state changes to **Waiting to start**, then **Running**.
5. Wait. The page checks again every 5 seconds while a job runs, and shows the result when it finishes.
6. If the job wrote a report, select **What it found** to read it.

## Things to note

- **Run now** cannot be selected while the job is waiting or running.
- Starboard lists every job the runner reports, apart from the backups. Backups have their own page: **System**,
  then **Backup and restore**.
- **Server jobs** appears only when the runner has reported at least one job.

## If it does not work

- **No Server jobs on the Overview page:** the runner is not set up, or has not reported a job yet. Check
  `STARBOARD_JOBS_DIR` in `.env`.
- **No Run now button:** Starboard cannot write in the `requests` folder. Give it permission to write there,
  then restart Starboard.
- **Not started** and a message: Starboard could not ask for the job. Read the message, then try again.
- **Failed:** select **What it found** to read what went wrong.

## Find out more

- [Back up the whole server](back-up-the-server.md)
- [Activate alerts](activate-alerts.md)
- [Read the log and report a problem](read-the-log.md)
- [The terminal: typing commands](../basics/the-terminal.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
