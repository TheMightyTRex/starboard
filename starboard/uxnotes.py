"""Feedback: reports sent with Snaglist's Send feedback button and saved in Starboard, and notes from the older
Note an issue button (the shared library's ux-notes.js), which stay listed.

Only while Settings, General, Testing, Send feedback is on. Kept in data/ux-notes.json (0600), so whoever fixes
them can read the file on the server. No thread of its own; nothing runs unless a report is added or changed.
"""

import json
import os
import secrets
import threading
from datetime import datetime, timezone

from .config import ConfigError

MAX_NOTES = 1000
FIELDS = {  # what a note may hold, and how long each part may be
    "page": 500, "title": 200, "screen": 20, "theme": 40, "text": 20, "design": 20, "app": 60, "version": 40,
    "browser": 300, "when": 40, "part": 200, "selector": 500, "what": 4000,
}
KINDS = ("Layout", "Words", "Behaviour", "Accessibility", "Looks", "Other")
SEVERITY = ("minor", "in-the-way", "stops-me")
STATUS = ("open", "fixed")
MAX_REPORT = 512 * 1024  # a Snaglist report with steps and the part's HTML; far larger is not a report
MAX_MARKDOWN = 30000
MAX_KEPT_REPORT = 200 * 1024  # the full report is kept only up to this size; the Markdown always is


class UxNotes:
    def __init__(self, data_dir):
        self.path = os.path.join(data_dir, "ux-notes.json")
        self.lock = threading.Lock()

    def list(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                notes = json.load(f)
            return notes if isinstance(notes, list) else []
        except (OSError, ValueError):
            return []

    def _write(self, notes):
        tmp = self.path + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(notes, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.path)

    def add(self, incoming):
        note = {k: str(incoming.get(k) or "")[:n] for k, n in FIELDS.items()}
        if not note["what"].strip():
            raise ConfigError("Say what is wrong")
        note["kind"] = incoming.get("kind") if incoming.get("kind") in KINDS else "Other"
        note["severity"] = incoming.get("severity") if incoming.get("severity") in SEVERITY else "in-the-way"
        note["zoom"] = float(incoming.get("zoom") or 1) if isinstance(incoming.get("zoom"), (int, float)) else 1
        note["display"] = [str(d)[:20] for d in incoming.get("display") or [] if isinstance(d, str)][:8]
        note["status"] = "open"
        note["id"] = secrets.token_hex(4)
        with self.lock:
            notes = self.list()
            if len(notes) >= MAX_NOTES:
                raise ConfigError(f"There are already {MAX_NOTES} notes: remove some first")
            notes.append(note)
            self._write(notes)
        return note

    def add_report(self, body):
        """A Snaglist report: {title, markdown, report}. Snaglist has already taken out personal details."""
        report = body.get("report") if isinstance(body.get("report"), dict) else {}
        markdown = str(body.get("markdown") or "")[:MAX_MARKDOWN]
        if not markdown.strip():
            raise ConfigError("The report is empty")
        page = report.get("page") if isinstance(report.get("page"), dict) else {}
        element = report.get("element") if isinstance(report.get("element"), dict) else {}
        note = {
            "source": "snaglist", "id": secrets.token_hex(4), "status": "open",
            "when": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "title": str(body.get("title") or "Feedback")[:200],
            "type": str(report.get("type") or "")[:40],
            "severity": str(report.get("severity") or "")[:40],
            "page": str(page.get("path") or "")[:500],
            "part": str(element.get("component") or element.get("name") or "")[:200],
            "version": str(report.get("version") or "")[:40],
            "markdown": markdown,
        }
        if len(json.dumps(report)) <= MAX_KEPT_REPORT:
            note["report"] = report
        with self.lock:
            notes = self.list()
            if len(notes) >= MAX_NOTES:
                raise ConfigError(f"There are already {MAX_NOTES} reports: remove some first")
            notes.append(note)
            self._write(notes)
        return note

    def update(self, note_id, status):
        if status not in STATUS:
            raise ConfigError("Choose open or fixed")
        with self.lock:
            notes = self.list()
            for n in notes:
                if n.get("id") == note_id:
                    n["status"] = status
                    self._write(notes)
                    return n
        raise ConfigError("That note is not there any more")

    def remove(self, note_id):
        with self.lock:
            notes = self.list()
            kept = [n for n in notes if n.get("id") != note_id]
            if len(kept) != len(notes):
                self._write(kept)
