[Help centre](../README.md) · Backup and restore · how-to

# Back up the whole server

Starboard can start a backup of your whole server and list the files it made, on **System**, **Backup**. The backup itself is done by a job you set up on the server, so Starboard never needs to read the
server's files.

This article is for confident readers. You write a small script, set up a systemd service and change
Docker's settings. If that is new to you, start with
[Back up and restore Starboard's settings](back-up-settings.md), which needs none of it.

## Before you begin

- You installed Starboard with the installer, and you can use `sudo` on the server.
- You know what you want to back up, such as each app's settings folder, and where to keep the backups.
- You have read [What Docker is](../basics/what-is-docker.md) and
  [The terminal: typing commands](../basics/the-terminal.md).

## How it works

Starboard and the job talk through two folders on the server:

| Setting | What the folder is for | How Starboard sees it |
|---|---|---|
| `STARBOARD_JOBS_DIR` | Holds a `requests` folder and the job's result files | Read-only, except `requests`, which it can write to |
| `STARBOARD_BACKUP_DIR` | Where the job saves its backup files | Read-only |

1. When you select **Back up the server now**, Starboard creates an empty file in `requests`. It is named
   `backup`, or `backup-with-prompt` when **Include a rebuild prompt** is active.
2. Your job notices the file, removes it and makes the backup.
3. While it works and when it finishes, the job writes `backup.json` (or `backup-with-prompt.json`) in the
   jobs folder. Starboard reads it to show the result.

The result file is JSON (a simple text format for data) with these fields:

| Field | What to put in it |
|---|---|
| `status` | `running`, `done` or `failed` |
| `started` | When the backup started, in seconds since 1 January 1970 (the output of `date +%s`) |
| `finished` | When it finished, in the same form |
| `summary` | One sentence about the result, shown on the page |

Starboard lists files in the backup folder that end in `.zip`, `.tar`, `.tar.gz`, `.tgz`, `.gz`, `.7z`,
`.dump`, `.sql` or `.md`.

## Steps

1. Make the folders. This example uses `/srv/starboard-jobs` and `/srv/backups`:

   ```bash
   sudo mkdir -p /srv/starboard-jobs/requests /srv/backups
   ```

2. Give your user the `requests` folder, so Starboard, which runs as your user, can write to it:

   ```bash
   sudo chown "$USER" /srv/starboard-jobs/requests
   ```

3. Write the job's script. This command opens a new file in a text editor:

   ```bash
   sudo nano /usr/local/bin/starboard-backup.sh
   ```

   Paste this example, and change the folders after `tar -czf` to the ones you want to back up:

   ```bash
   #!/usr/bin/env bash
   # An example to start from: one archive of the folders listed after tar -czf.
   set -u
   JOBS=/srv/starboard-jobs
   OUT=/srv/backups
   for name in backup backup-with-prompt; do
     [ -f "$JOBS/requests/$name" ] || continue
     rm -f "$JOBS/requests/$name"
     started=$(date +%s)
     printf '{"status": "running", "started": %s}\n' "$started" > "$JOBS/$name.json"
     if tar -czf "$OUT/server-$(date +%Y-%m-%d-%H%M).tar.gz" /etc /srv/appdata; then
       status=done; summary="Saved /etc and /srv/appdata"
     else
       status=failed; summary="tar stopped with an error"
     fi
     printf '{"status": "%s", "started": %s, "finished": %s, "summary": "%s"}\n' \
       "$status" "$started" "$(date +%s)" "$summary" > "$JOBS/$name.json"
   done
   ```

   Save the file: press Ctrl+O, then Enter, then Ctrl+X.
4. Let the script run:

   ```bash
   sudo chmod +x /usr/local/bin/starboard-backup.sh
   ```

5. Make a systemd service that runs the script. Open a new file:

   ```bash
   sudo nano /etc/systemd/system/starboard-backup.service
   ```

   Paste this and save:

   ```
   [Unit]
   Description=Starboard server backup

   [Service]
   Type=oneshot
   ExecStart=/usr/local/bin/starboard-backup.sh
   ```

6. Make a systemd path unit, which starts the service when a request file appears. Open a new file:

   ```bash
   sudo nano /etc/systemd/system/starboard-backup.path
   ```

   Paste this and save:

   ```
   [Unit]
   Description=Start the Starboard server backup when asked

   [Path]
   PathExists=/srv/starboard-jobs/requests/backup
   PathExists=/srv/starboard-jobs/requests/backup-with-prompt

   [Install]
   WantedBy=multi-user.target
   ```

7. Activate the path unit:

   ```bash
   sudo systemctl daemon-reload
   ```

   ```bash
   sudo systemctl enable --now starboard-backup.path
   ```

8. Show the folders to Starboard. In the Starboard folder, open `compose.override.yaml` (create it if it is
   not there):

   ```bash
   nano compose.override.yaml
   ```

   Add these lines. If the file already has a `volumes` list, add only the three lines that start with `-`:

   ```yaml
   services:
     starboard:
       volumes:
         - /srv/starboard-jobs:/jobs:ro
         - /srv/starboard-jobs/requests:/jobs/requests
         - /srv/backups:/backups:ro
   ```

9. Open the `.env` file in the same folder and set the two folders as Starboard sees them:

   ```
   STARBOARD_JOBS_DIR=/jobs
   STARBOARD_BACKUP_DIR=/backups
   ```

10. Start Starboard again so it reads the changes:

    ```bash
    docker compose up -d
    ```

11. Go to **System**, then **Backup**, and select **Back up the server now**.

The status shows **Starting**, then **Backing up now**, then **Complete** or **Failed**. The page checks
again every 5 seconds while the backup runs. The new file appears in the list under it.

## Things to note

- Starboard cannot restore the whole server. To restore, copy the files back on the server yourself, or
  follow the rebuild prompt.
- With **Include a rebuild prompt** on, your job can also save `REBUILD-PROMPT.md` next to the backup: steps
  an AI assistant with a shell can follow to rebuild the server. The example script does not write one.
- Select a backup in the list to see its details, then **Download** to save it. Starboard asks for your
  password first, because a server backup can hold API keys and private files.
- The backups sit on the same server. If its disk fails, they go with it, so copy the newest one to another
  disk or computer.
- If you set only `STARBOARD_BACKUP_DIR`, the page lists the backups but says it cannot start one.
- Your job can also write `included` and `unreadable` (lists of what went in and what could not be read),
  `exit` (its exit code) and `runs` (earlier results). Starboard shows them when they are there.
- The same `requests` folder can run other jobs, such as a server check. Read
  [Run a server job](run-a-server-job.md).
- If you installed from the ready-made image, add the `volumes` lines and the two settings to
  `compose.image.yaml` instead. Write each setting in its `environment` list as `- STARBOARD_JOBS_DIR=/jobs`.

## If it does not work

- **The page says "No server backup job is set up":** Starboard did not get the two settings. Check `.env`,
  then repeat step 10.
- **"The requests folder is not writable":** repeat step 2, and check the `requests` line in
  `compose.override.yaml` does not end in `:ro`.
- **The status stays on Starting:** the path unit is not running. Check it with this command:

  ```bash
  systemctl status starboard-backup.path
  ```

- **The status shows Failed:** read the job's own messages with this command:

  ```bash
  journalctl -u starboard-backup.service
  ```

## Find out more

- [Back up and restore Starboard's settings](back-up-settings.md)
- [Run a server job](run-a-server-job.md)
- [Change what Starboard can access](change-what-starboard-can-access.md)
- [What a home server is](../basics/what-is-a-home-server.md)
