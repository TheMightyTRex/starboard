"""Settings, Reelix, Folders (DASH-194): the library folders for each kind, with free space, and Add and Remove after
set-up (today they are fixed by Install apps). Folders are as Reelix sees them inside its container (/data/media/...).
Removing a folder takes it out of Reelix only; the files stay on disk."""
import re

from .reelix_setup import FOLDERS

KINDS = {"movies": "Films", "tv": "Series", "ebooks": "Books", "audiobooks": "Audiobooks", "music": "Music", "radio": "Radio"}


def _items(answer):
    return answer.get("items") if isinstance(answer, dict) else answer or []


def listing(reelix):
    out = []
    seen = set()
    for group, path, extra, _ in FOLDERS:
        if path in seen and path != "/bookrootfolders" and path != "/rootfolders":
            continue
        try:
            _, found = reelix.call("GET", path)
        except Exception:  # noqa: BLE001  a Reelix without that kind (an older one): nothing to show for it
            continue
        for f in _items(found):
            kind = f.get("media_kind") or f.get("kind")
            want = list(extra.values())[0]
            if kind and kind != want:
                continue
            out.append({"id": f.get("id"), "kind": group, "kind_name": KINDS[group], "path": f.get("path", ""),
                        "free": f.get("free_space"), "ok": f.get("accessible", True)})
        seen.add(path)
    return {"folders": out, "kinds": [{"value": k, "label": v} for k, v in KINDS.items()]}


def change(reelix, action, body):
    group = str(body.get("kind", ""))
    spec = next((f for f in FOLDERS if f[0] == group), None)
    if not spec:
        raise ValueError("Choose what the folder is for")
    _, path, extra, _ = spec
    if action == "add":
        folder = str(body.get("path", "")).strip().rstrip("/")
        if not re.match(r"^/[A-Za-z0-9 ._/()'&+-]{1,250}$", folder) or ".." in folder:
            raise ValueError("Type the folder as Reelix sees it, starting with /, such as /data/media/films-4k")
        reelix.call("POST", path, {"path": folder, **extra})
        done = f"Added {folder} for {KINDS[group].lower()}"
    else:
        folder_id = int(body.get("id") or 0)
        reelix.call("DELETE", f"{path}/{folder_id}", ok=(200, 204))
        done = f"Took a {KINDS[group].lower()} folder out of Reelix; its files stay on disk"
    return {**listing(reelix), "done": done}
