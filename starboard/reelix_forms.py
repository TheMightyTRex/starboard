"""Settings, Reelix, advanced sections drawn from one table (DASH-193, 195, 197): Information, Files and Requests, and
the book and music settings. Each field is one of Reelix's own settings (GET and PUT /settings/...), with a label and
a hint in plain words. Only the fields listed here are read and changed; everything else Reelix keeps is sent back as
it was. Reelix keeps these behind its admin password (reelix_admin.py)."""

LANGUAGE = r"^[a-z]{2}(-[A-Z]{2})?$"
FORMS = {
    "information": ("/settings/metadata", "Information", "Where Reelix finds details about films and series.", [
        ("language", "Language of details", "Titles and descriptions in this language, such as en-GB.", "text", LANGUAGE),
        ("region", "Region", "Release dates and certificates for this country, such as GB.", "text", r"^[A-Z]{2}$"),
        ("tvdb_api_key", "TheTVDB key", "Optional. Only for series TheTVDB knows better.", "secret", None),
        ("tvdb_pin", "TheTVDB PIN", "Optional. Only with a subscriber key.", "secret", None),
    ]),
    "files": ("/settings/mediamanagement", "Files", "How Reelix moves finished downloads into your library.", [
        ("import_mode", "How finished files move in", "A hard link adds the file without a copy, so torrents keep sharing.", "select",
         [("hardlink_or_copy", "Hard link, or copy when it cannot (recommended)"), ("copy", "Always copy"), ("move", "Move")]),
        ("minimum_free_space_mb", "Space to keep free (MB)", "Reelix stops adding files when a library folder has less free than this.", "number", (0, 10 ** 7)),
        ("recycle_bin_path", "Recycle bin folder", "Deleted and replaced files go here. Empty deletes them for good.", "text", r"^(/[^\x00]*)?$"),
        ("recycle_bin_retention_days", "Days to keep recycled files", "0 keeps them for ever.", "number", (0, 3650)),
        ("delete_empty_folders", "Delete empty folders", "After the last file in a folder is deleted.", "bool", None),
        ("unmonitor_deleted", "Stop following what you delete", "When a file is deleted outside Reelix, Reelix stops looking for it.", "bool", None),
        ("import_extra_files", "Bring in extra files", "Subtitles and other files that come with a download.", "bool", None),
        ("extra_file_extensions", "Extra file types", "Separated by commas, such as srt, nfo.", "list", None),
        ("analyze_video_files", "Read each file's details", "Resolution, sound and length, during scans.", "bool", None),
    ]),
    "requests": ("/settings/requests", "Requests", "What happens when someone asks for something.", [
        ("search_on_approve", "Search as soon as it is approved", None, "bool", None),
        ("partial_requests", "Ask for single seasons", "People can ask for some seasons of a series, not all.", "bool", None),
        ("enable_4k_movie", "4K films can be asked for", None, "bool", None),
        ("enable_4k_series", "4K series can be asked for", None, "bool", None),
        ("minimum_availability", "When a film counts as out", None, "select",
         [("released", "When it is released to buy or stream (recommended)"), ("in_cinemas", "When it is in cinemas"), ("announced", "When it is announced")]),
        ("movie_quota_limit", "Films each person can ask for", "Empty for no limit.", "optional_number", (1, 1000)),
        ("movie_quota_days", "In how many days (films)", None, "number", (1, 365)),
        ("tv_quota_limit", "Series each person can ask for", "Empty for no limit.", "optional_number", (1, 1000)),
        ("tv_quota_days", "In how many days (series)", None, "number", (1, 365)),
    ]),
    "books": ("/settings/books", "Books", "How Reelix handles books and audiobooks.", [
        ("metadata_language", "Language of book details", "Such as en.", "text", r"^([a-z]{2,3})?$"),
        ("write_metadata", "Write details into the files", "Never into files that are still sharing.", "bool", None),
        ("write_covers", "Save covers", None, "bool", None),
    ]),
    "music": ("/settings/music", "Music", "How Reelix handles albums.", [
        ("write_tags", "Write tags into the files", "Never into files that are still sharing.", "bool", None),
        ("embed_cover", "Put the cover inside each file", None, "bool", None),
        ("save_cover_file", "Save the cover as a file too", None, "bool", None),
        ("preferred_release_countries", "Countries to prefer", "Separated by commas, such as GB, US.", "list", None),
        ("preferred_formats", "Formats to prefer", "Separated by commas, such as Digital Media, CD.", "list", None),
    ]),
}
MASK = "********"


def _shown(kind, value):
    if kind == "secret":
        return MASK if value else ""
    if kind == "list":
        return ", ".join(str(x) for x in value or [])
    return value


def open_form(reelix, name):
    if name not in FORMS:
        raise ValueError("Not something Starboard changes")
    path, title, about, fields = FORMS[name]
    _, current = reelix.call("GET", path)
    current = current or {}
    return {"name": name, "title": title, "about": about,
            "fields": [{"key": k, "label": label, "hint": hint or "", "type": kind,
                        "choices": [{"value": v, "label": t} for v, t in rule] if kind == "select" else None,
                        "value": _shown(kind, current.get(k))} for k, label, hint, kind, rule in fields]}


def _clean(kind, rule, label, value):
    import re
    if kind == "bool":
        return bool(value)
    if kind in ("number", "optional_number"):
        if kind == "optional_number" and value in ("", None):
            return None
        try:
            n = int(value)
        except (TypeError, ValueError):
            raise ValueError(f"{label} is a whole number") from None
        if not rule[0] <= n <= rule[1]:
            raise ValueError(f"{label} is a number from {rule[0]} to {rule[1]}")
        return n
    if kind == "select":
        if value not in [v for v, _ in rule]:
            raise ValueError(f"Choose one of the choices for {label.lower()}")
        return value
    if kind == "list":
        items = [x.strip() for x in str(value or "").split(",") if x.strip()]
        if any(len(x) > 40 or any(c in x for c in "\r\n") for x in items) or len(items) > 50:
            raise ValueError(f"{label}: short words, separated by commas")
        return items
    text = str(value or "").strip()
    if len(text) > 300 or any(c in text for c in "\r\n"):
        raise ValueError(f"{label} is one line")
    if rule and not re.match(rule, text):
        raise ValueError(f"Check {label.lower()}: it is not in the form it needs")
    return text or None


def save_form(reelix, name, values):
    """Saves the fields given; a secret left as it was shown (or empty) keeps the one Reelix has."""
    if name not in FORMS:
        raise ValueError("Not something Starboard changes")
    path, _, _, fields = FORMS[name]
    _, current = reelix.call("GET", path)
    out = dict(current or {})
    for k, label, _, kind, rule in fields:
        if k not in (values or {}):
            continue
        v = values[k]
        if kind == "secret":
            if v in ("", MASK, None):
                continue
            v = str(v).strip()
            if len(v) > 200 or any(c in v for c in "\r\n "):
                raise ValueError(f"Check {label.lower()}")
            out[k] = v
            continue
        out[k] = _clean(kind, rule, label, v)
    reelix.call("PUT", path, out)
    return open_form(reelix, name)
