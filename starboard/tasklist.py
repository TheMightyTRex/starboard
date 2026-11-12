"""The task list a long change shows while it runs (DASH-252, 13 November 2026).

Move them into Reelix, Take over my apps, Roll back and Clear away the old apps each run for minutes in the
background. The page opens a dialog that lists each app or step with its state, says what is happening now, and gives
the result at the end. This holds that list for one job: the job marks each task as it goes, and the page reads a copy.

States: waiting, working, done, failed (did not finish, or not moved), skipped (not started, because an earlier step
stopped). Nothing here runs by itself; it is a few dictionaries behind a lock.
"""
import threading

STATES = ("waiting", "working", "done", "failed", "skipped")


class Tasks:
    def __init__(self, items=()):
        """items: (id, label) pairs, in the order they run."""
        self._lock = threading.Lock()
        self._items = [{"id": i, "label": label, "state": "waiting", "detail": ""} for i, label in items]
        self.now = ""

    def add(self, task_id, label):
        with self._lock:
            if not any(t["id"] == task_id for t in self._items):
                self._items.append({"id": task_id, "label": label, "state": "waiting", "detail": ""})

    def _set(self, task_id, state, detail=None):
        for t in self._items:
            if t["id"] == task_id:
                t["state"] = state
                if detail is not None:
                    t["detail"] = str(detail)[:300]
                return t
        return None

    def start(self, task_id, detail="", now=None):
        """Marks a task working; the tasks before it that were still working are done."""
        with self._lock:
            for t in self._items:
                if t["id"] == task_id:
                    break
                if t["state"] == "working":
                    t["state"] = "done"
            t = self._set(task_id, "working", detail)
            self.now = now if now is not None else (t["label"] if t else self.now)

    def note(self, task_id, detail, now=None):
        """What a working task is doing now, without changing its state."""
        with self._lock:
            self._set(task_id, next((t["state"] for t in self._items if t["id"] == task_id), "working"), detail)
            if now is not None:
                self.now = now

    def done(self, task_id, detail=None):
        with self._lock:
            self._set(task_id, "done", detail)

    def fail(self, task_id, detail=None):
        with self._lock:
            self._set(task_id, "failed", detail)

    def skip(self, task_id, detail=None):
        with self._lock:
            self._set(task_id, "skipped", detail)

    def stop_rest(self, why):
        """After a step stopped: the working one did not finish, the waiting ones did not start, and say why."""
        with self._lock:
            for t in self._items:
                if t["state"] == "working":
                    t["state"] = "failed"
                elif t["state"] == "waiting":
                    t["state"] = "skipped"
                    t["detail"] = why
            self.now = ""

    def finish_all(self):
        """The job ended well: anything still working is done."""
        with self._lock:
            for t in self._items:
                if t["state"] == "working":
                    t["state"] = "done"
            self.now = ""

    def state(self, task_id):
        with self._lock:
            return next((t["state"] for t in self._items if t["id"] == task_id), None)

    def public(self):
        with self._lock:
            return {"tasks": [dict(t) for t in self._items], "now": self.now}


def from_progress(tasks, lines):
    """Marks tasks from a helper script's progress file: each line is the id of the task it has just started, so
    every earlier one is done and the last is working; "<id> failed" marks one that did not finish."""
    for line in lines:
        task_id, _, word = line.strip().partition(" ")
        if word == "failed" and tasks.state(task_id) in ("waiting", "working"):
            tasks.fail(task_id)
        elif task_id and not word and tasks.state(task_id) == "waiting":
            tasks.start(task_id)
