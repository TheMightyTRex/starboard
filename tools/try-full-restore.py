#!/usr/bin/env python3
"""Tries a full backup, its check and a restore on this server (DASH-381, DASH-387) for real, with Docker and the
helper image, against a scratch folder and one throwaway container, never a real Starboard, its apps or their data:

    python3 tools/try-full-restore.py /mnt/pool/build-cache/tmp/try-full-restore

- A made-up settings folder with two apps; one has an SQLite database in WAL mode and a throwaway container that
  mounts its folder (the helper image, sleeping), so stopping and starting is real. Only containers that mount a
  folder inside the scratch settings folder are ever stopped.
- Makes a full backup: it must say Checked. Then a copy damaged on the disk must be refused.
- Changes the database, leaves a -wal file as an app that was killed would, and restores the first backup: the old
  rows are back, the database passes its integrity check, a full backup of how things were was made first, and the
  container runs again. Then a wrong password and a cut-off file, which must change nothing.
The scratch folder must be under one of Starboard's usual places (/mnt, /srv...). Nothing is removed afterwards except
the throwaway container, so the results can be looked at; move the scratch folder to the holding folder when done.
"""
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from starboard import containers, full_backup as fb, stack  # noqa: E402

PASSWORD = "a made-up backup password"
APP = "starboard-try-restore-app"
results = []


def check(what, ok, detail=""):
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'} {what}{'' if ok or not detail else ': ' + str(detail)}")


def connect(db):
    """Exclusive locking, so WAL mode needs no shared-memory file: a pool of disks (mergerfs) cannot map one."""
    con = sqlite3.connect(db)
    con.execute("PRAGMA locking_mode=EXCLUSIVE")
    return con


def rows(db):
    con = connect(db)
    try:
        return [r[0] for r in con.execute("SELECT title FROM films ORDER BY id")], con.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        con.close()


def wait(read, data):
    for _ in range(1200):
        s = read(data)
        if s.get("state") != "running":
            return s
        time.sleep(0.25)
    return {"state": "timed out"}


def running():
    out = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", APP], capture_output=True, text=True).stdout.strip()
    return out == "true"


def main(scratch):
    scratch = os.path.abspath(scratch)
    if os.path.exists(scratch) and os.listdir(scratch):
        sys.exit(f"{scratch} is not empty: give a new folder")
    data, config, backups = (os.path.join(scratch, d) for d in ("starboard-data", "config", "backups"))
    for d in (data + "/stack", data + "/plugins/styles", config + "/films", config + "/notes", config + "/films/cache"):
        os.makedirs(d)
    with open(data + "/stack/.env", "w", encoding="utf-8") as f:
        f.write(f"CONFIG_DIR={config}\nDATA_DIR={scratch}/media\nPUID={os.getuid()}\nPGID={os.getgid()}\n")
    with open(data + "/plugins/styles/settings.json", "w", encoding="utf-8") as f:
        f.write('{"colour": "as backed up"}')
    with open(data + "/config.json", "w", encoding="utf-8") as f:
        f.write('{"schema": 1, "site_name": "Made-up server", "services": []}')
    with open(config + "/notes/notes.txt", "w", encoding="utf-8") as f:
        f.write("as backed up")
    with open(config + "/films/cache/thumb.bin", "wb") as f:
        f.write(os.urandom(4096))
    db = config + "/films/films.db"
    con = connect(db)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE films (id INTEGER PRIMARY KEY, title TEXT, filler BLOB)")
    con.executemany("INSERT INTO films (title, filler) VALUES (?, ?)", [(f"Made-up film {n}", os.urandom(200_000)) for n in range(1, 13)])
    con.commit()
    con.close()
    before = rows(db)[0]

    subprocess.run(["docker", "rm", "-f", APP], capture_output=True)
    made = subprocess.run(["docker", "run", "-d", "--name", APP, "--network", "none", "--memory", "32m", "-v", f"{config}/films:/config",
                           "--entrypoint", "sh", containers.HELPER_IMAGE, "-c", "trap exit TERM; sleep 3600 & wait"], capture_output=True, text=True)
    if made.returncode:
        sys.exit(f"The throwaway container did not start: {made.stderr.strip()}")
    applied = []
    try:
        with mock.patch.object(stack, "host_folder", lambda d: os.path.join(data, "stack")):
            # 1. Make one: checked.
            t = time.time()
            fb.start(data, "0.26.0", PASSWORD, backups, False, site_name="Made-up server", keep=5)
            first = wait(fb.status, data)
            check("a full backup is made", first.get("state") == "done", first.get("error"))
            print(f"     took {time.time() - t:.1f} s, {first.get('size', 0) / 1e6:.1f} MB")
            listed = fb.with_checked(data, fb.found(backups))
            check("the list says Checked", len(listed) == 1 and bool(listed[0]["checked"]), listed)
            check("the container runs again after the backup", running())

            # 2. A copy damaged on the disk as it is written is refused, and the first one stays.
            real = fb._helper

            def damaging(script, binds, timeout=7200):
                out = real(script, binds, timeout)
                if "cp /w/" in script and ".part" in script:
                    newest = max((f for f in os.listdir(backups) if f.endswith(".starboard")), key=lambda f: os.path.getmtime(os.path.join(backups, f)))
                    with open(os.path.join(backups, newest), "r+b") as f:
                        f.seek(-3, os.SEEK_END)
                        f.write(b"\x00\x01\x02")
                return out
            time.sleep(1.1)
            with mock.patch.object(fb, "_helper", damaging):
                fb.start(data, "0.26.0", PASSWORD, backups, False, keep=1)
                bad = wait(fb.status, data)
            check("a copy that does not read back is reported", bad.get("state") == "failed" and "did not read back" in (bad.get("error") or ""), bad.get("error"))
            left = sorted(os.listdir(backups))
            check("it is set aside and the older backup stays", len([f for f in left if f.endswith(".starboard")]) == 1
                  and len([f for f in left if f.endswith(".part")]) == 1, left)

            # 3. Things change; the app is killed with pages still in its -wal file.
            con = connect(db)
            con.execute("PRAGMA wal_autocheckpoint=0")
            con.execute("DELETE FROM films WHERE id > 3")
            con.execute("UPDATE films SET title = 'Changed since the backup'")
            con.commit()
            for ext in ("-wal", ""):  # as left by a process that never closed the database
                shutil.copyfile(db + ext, db + ext + ".kept")
            con.close()
            for ext in ("", "-wal"):
                os.replace(db + ext + ".kept", db + ext)
            check("before the restore there is a -wal file beside the database", os.path.getsize(db + "-wal") > 0)
            with open(config + "/notes/notes.txt", "w", encoding="utf-8") as f:
                f.write("changed since")
            with open(data + "/plugins/styles/settings.json", "w", encoding="utf-8") as f:
                f.write('{"colour": "changed since"}')

            # 4. A wrong password changes nothing.
            try:
                fb.start_restore(data, "0.26.0", first["file"], "not the backup password", lambda raw: 0)
                check("a wrong backup password is refused", False)
            except fb.BackupError as e:
                check("a wrong backup password is refused", "does not open" in str(e), e)
            check("and nothing was stopped or changed", running() and open(config + "/notes/notes.txt", encoding="utf-8").read() == "changed since")

            # 5. Restore the first backup.
            time.sleep(1.1)
            t = time.time()
            fb.start_restore(data, "0.26.0", first["file"], PASSWORD, lambda raw: applied.append(raw) or 0, "Made-up server")
            done = wait(fb.restore_status, data)
            check("the restore finishes", done.get("state") == "done", done.get("error"))
            print(f"     took {time.time() - t:.1f} s")
            got, integrity = rows(db)
            check("the database is as it was in the backup", got == before, got[:3])
            check("and passes its integrity check", integrity == "ok", integrity)
            check("the other app's file and the plug-in setting are back", open(config + "/notes/notes.txt", encoding="utf-8").read() == "as backed up"
                  and "as backed up" in open(data + "/plugins/styles/settings.json", encoding="utf-8").read())
            check("the cache, which is in no backup, was left alone", os.path.getsize(config + "/films/cache/thumb.bin") == 4096)
            check("Starboard's settings were handed to the settings restore", bool(applied) and applied[0].get("site_name") == "Made-up server")
            check("a full backup of how things were was made first", bool(done.get("safety")) and os.path.isfile(done["safety"]) and done["safety"] != first["file"])
            check("the backup that was restored is still in the folder", os.path.isfile(first["file"]))
            check("the container runs again", running())
            check("files are owned by the person, not root", os.stat(db).st_uid == os.getuid())

            # 6. A cut-off file changes nothing.
            cut = os.path.join(backups, "starboard-full-2020-01-01-000000.starboard")
            shutil.copyfile(done["safety"], cut)
            with open(cut, "r+b") as f:
                f.truncate(os.path.getsize(cut) - 100)
            with open(config + "/notes/notes.txt", "w", encoding="utf-8") as f:
                f.write("changed again")
            time.sleep(1.1)
            fb.start_restore(data, "0.26.0", cut, PASSWORD, lambda raw: applied.append("cut") or 0)
            failed = wait(fb.restore_status, data)
            check("a cut-off backup is refused", failed.get("state") == "failed" and "cut short" in (failed.get("error") or ""), failed.get("error"))
            check("and nothing changed, with the container running again", open(config + "/notes/notes.txt", encoding="utf-8").read() == "changed again"
                  and rows(db)[0] == before and "cut" not in applied and running())
    finally:
        subprocess.run(["docker", "rm", "-f", APP], capture_output=True)
    print(f"\n{sum(results)} passed, {len(results) - sum(results)} failed. The scratch folder is {scratch}")
    return 0 if all(results) else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
