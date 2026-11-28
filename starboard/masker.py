"""The core masker (DASH-655, release 1 of the AI assistant family): hides what is private in text before an AI tool
reads it.

Every answer an AI tool gets from Starboard passes through here (starboard/mcp.py), so the rule is kept in one place and
tested once. It hides:

- keys, tokens and passwords: Starboard's own keys (sb_...), Bearer and Basic headers, name=value pairs whose name says
  secret, JSON web tokens, and any long run of letters and numbers that looks like a token. These are removed, not
  numbered, so nothing links two of them.
- email addresses
- network addresses: IPv4, IPv6, MAC addresses, host names (home-network, Tailscale and full domain names) and the
  host part of a web address
- folders and files: paths on Linux, macOS and Windows, and the private words below
- the private words Starboard knows (private_words): the site's and the server's names, the computer's name, the names
  of the people who use the apps, folders and disks you added, and library names

What it leaves alone: dates, times, numbers, app names and the words of a message. It never makes a new address or a
guess: each hidden value becomes a short marker such as [address 1], the same marker for the same value inside one
answer, and the values themselves are not kept.

Text is first made plain: Unicode is folded to its everyday form (full-width letters become ordinary ones) and the
invisible and control characters that could split a key to get past a pattern are dropped, so a key written with a
zero-width space in the middle is still found. Each pattern is written to run in linear time on long text.

The result of mask() is (text, counts): counts says how many of each kind were hidden, for the audit log, never the
values.
"""
import re
import unicodedata

LIMIT = 20000  # the most characters of one text that are read; the rest is cut at a space

# Unicode: letters, numbers and ordinary punctuation stay. Format and control characters (zero-width space, joiners,
# bidirectional marks, soft hyphen, tag characters) go, except the line break and the tab.
_INVISIBLE = {n: None for n in list(range(0, 32)) + [127] + list(range(0x80, 0xA0)) if n not in (9, 10)}


def plain(text):
    """text, as ordinary characters: NFKC folded, invisible and control characters dropped (a line break stays)."""
    text = unicodedata.normalize("NFKC", str(text))
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.translate(_INVISIBLE)
    return "".join(c for c in text if c in "\n\t" or unicodedata.category(c) not in ("Cf", "Cc", "Co", "Cs", "Cn"))


# Patterns --------------------------------------------------------------------------------------------------------
# Each is bounded: no nested repeats, and a run of characters is matched in one go.

_SB_KEY = re.compile(r"sb_[a-z]{3,10}_[0-9a-f]{6}_[A-Za-z0-9_-]{8,}")
_BEARER = re.compile(r"(?i)\b(bearer|basic|digest)[ \t]+[A-Za-z0-9._~+/=-]{6,}")
_SECRET_PAIR = re.compile(
    r"(?i)\b([A-Za-z0-9_.-]{0,24}(?:api[_-]?key|apikey|token|password|passwd|passphrase|secret|authorization|auth|cookie|"
    r"session[_-]?id|x-api-key|set-up[ _-]?code|setup[ _-]?code|credential)s?)(\"?[ \t]*[=:][ \t]*\"?)([^\s&,;\"'<>]{1,200})")
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{0,}")
# The start of a key that a well-known service gives out. Written in pieces, so this file does not look like a leaked key to the
# private-details check (tools/check-private.sh).
_PREFIXES = ("(?:sk|pk|rk)[-_]", "g" "hp_", "g" "ho_", "g" "hs_", "g" "hu_", "github" "_pat_", "gl" "pat-", "xo" "x[abprs]-", "AK" "IA", "AS" "IA", "AI" "za", r"ya29\.")
_PREFIXED = re.compile(r"\b(?:" + "|".join(_PREFIXES) + r")[-_.A-Za-z0-9]{8,}")
_LONG = re.compile(r"[A-Za-z0-9_+/=-]{24,}")  # checked by _token_like before it is hidden
_HEXISH = re.compile(r"\b[0-9a-fA-F]{20,}\b")
_EMAIL = re.compile(r"[A-Za-z0-9._%+'-]{1,64}@[A-Za-z0-9-]{1,63}(?:\.[A-Za-z0-9-]{1,63}){1,8}")
_URL = re.compile(r"(?i)\b([a-z][a-z0-9+.-]{1,12}://)([^\s/?#\"'<>]{1,200})")
_IPV4 = re.compile(r"(?<![\w.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\w])(?::\d{1,5})?")
_H = r"[0-9a-fA-F]{1,4}"
_IPV6 = re.compile(rf"(?<![\w:.])(?:(?:{_H}:){{7}}{_H}|(?:{_H}:){{1,7}}:(?:{_H}(?::{_H}){{0,6}})?|::{_H}(?::{_H}){{0,6}})(?!\w|:\w|\.\w)")
_MAC = re.compile(r"(?<![\w:-])(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}(?!\w|[:-]\w)")
_VERSION = re.compile(r"v?\d{1,4}(?:\.\d{1,5}){1,3}(?:[-+][\w.]{1,30})?")
_STATE_WORDS = {"expired", "invalid", "missing", "none", "null", "true", "false", "ok", "failed", "refused", "required", "rejected",
                "denied", "valid", "unknown", "empty", "not", "set", "unset", "off", "on", "disabled", "enabled", "yes", "no"}
_HOST = re.compile(r"(?i)(?<![\w@.-])(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.){1,8}"
                   r"(?:local|lan|home|home\.arpa|localdomain|internal|intranet|corp|private|ts\.net|ts\.net\.|duckdns\.org|"
                   r"no-ip\.\w+|ddns\.net|dyndns\.\w+|myfritz\.net|synology\.me|[a-z]{2,24})(?::\d{1,5})?(?![\w-])")
_UNIX_PATH = re.compile(r"(?<![\w:/.~-])(?:~|\.\.?)?(?:/[^/\n\"'<>|]{0,99}[^/\s\"'<>|](?=/)){1,23}/(?:[^/\n\"'<>|]{1,60}?\.[A-Za-z0-9]{2,5}(?![\w])|[^\s\"'<>|:;,()\[\]{}]{1,120})/?")
_WIN_PATH = re.compile(r"(?i)(?<![\w])[a-z]:[\\/](?:[^\s\\/:*?\"<>|]{1,100}[\\/]){0,23}[^\s\\/:*?\"<>|]{0,100}|\\\\[^\s\\/]{1,63}(?:\\[^\s\\/]{1,100}){1,24}")

# Paths that are addresses inside Starboard or the web, not folders on the computer: left as they are.
_NOT_FOLDERS = ("/api/", "/settings", "/system", "/library", "/downloads.html", "/help/", "/css/", "/js/", "/v1/", "/health", "/status")
# The first part of a folder path on a computer, so a short path such as /mnt/media is found, not just a deep one.
_ROOTS = re.compile(r"(?<![\w:/.~-])(?=/(?:mnt|media|home|data|srv|var|opt|tmp|usr|etc|root|run|volume\d?|volumes|Users|share|config|"
                    r"downloads|movies|tv|music|books|audiobooks|storage|pool|nas|backup|backups|app|library)\b)"
                    r"(?:/[^/\n\"'<>|]{0,99}[^/\s\"'<>|](?=/)){0,23}/(?:[^/\n\"'<>|]{1,60}?\.[A-Za-z0-9]{2,5}(?![\w])|[^\s\"'<>|:;,()\[\]{}]{1,120})/?")

# File extensions that make a dotted word a file name rather than a host: a name such as movie.mkv is not a host.
_FILE_ENDINGS = {"mkv", "mp4", "avi", "mov", "m4v", "m4b", "mp3", "flac", "m4a", "ogg", "opus", "wav", "epub", "pdf", "cbz", "cbr",
                 "srt", "ass", "sub", "nfo", "jpg", "jpeg", "png", "gif", "webp", "svg", "json", "yaml", "yml", "xml", "txt", "log",
                 "py", "js", "css", "html", "htm", "sh", "db", "sqlite", "conf", "cfg", "ini", "env", "zip", "tar", "gz", "rar", "7z",
                 "iso", "bin", "exe", "dll", "md", "csv", "tmp", "bak", "lock", "pid", "so", "rs", "go", "ts", "rb", "php", "c", "h"}
_REAL_ENDINGS = {"com", "net", "org", "io", "co", "uk", "info", "biz", "dev", "app", "xyz", "me", "tv", "us", "de", "fr", "nl", "eu",
                 "ca", "au", "nz", "ie", "es", "it", "se", "no", "dk", "fi", "be", "ch", "at", "pl", "cz", "ru", "cn", "jp", "kr",
                 "in", "br", "mx", "ar", "za", "cloud", "online", "site", "tech", "store", "live", "link", "pro", "name", "club"}


def _token_like(s):
    """True for a run that is more likely a key than a word: it mixes digits with letters, or letters of both cases, or
    has no vowel pattern of a word, or is simply very long."""
    if len(s) >= 40:
        return True
    has_digit = any(c.isdigit() for c in s)
    has_lower = any(c.islower() for c in s)
    has_upper = any(c.isupper() for c in s)
    mixed = has_digit + has_lower + has_upper
    # a long run made of one kind of letters and dashes, such as a long hyphenated phrase, is words
    return mixed >= 2 and not re.fullmatch(r"[A-Za-z]+(?:-[A-Za-z]+){2,}", s)


class Masker:
    """One masking job. Make one for each answer; its markers are numbered within that answer only."""

    def __init__(self, words=()):
        self.keep_version = False  # mask_value sets it for a field that holds a version (version, current, latest)
        self.counts = {}
        self._seen = {}
        # Longest first, so a folder name that holds a shorter one is hidden whole.
        clean = {plain(w).strip() for w in words if w}
        self._words = sorted((w for w in clean if len(w) >= 3 and w.lower() not in _COMMON), key=len, reverse=True)[:200]
        self._word_re = re.compile("|".join(re.escape(w) for w in self._words), re.I) if self._words else None

    def _mark(self, kind, value):
        """[address 1]: the same value gets the same number inside this answer. The value is not kept beyond a
        lookup in this dict, which goes with the Masker."""
        key = (kind, value.lower())
        if key not in self._seen:
            self._seen[key] = 1 + sum(1 for k in self._seen if k[0] == kind)
        self.counts[kind] = self.counts.get(kind, 0) + 1
        return f"[{kind} {self._seen[key]}]"

    def _gone(self, kind):
        self.counts[kind] = self.counts.get(kind, 0) + 1
        return f"[{kind} removed]"

    def mask(self, text):
        text = plain(text)
        if len(text) > LIMIT:  # cut at a space, so a key is never cut in half and left as a stub
            text = text[:LIMIT].rsplit(None, 1)[0] + " [cut]"
        if not text:
            return ""
        if self.keep_version and _VERSION.fullmatch(text.strip()):  # a field named version holds a number such as 9.11.0.1, which is not an address
            return text
        if self._word_re:  # first, before a pattern can split a private name
            text = self._word_re.sub(lambda m: self._mark("name", m.group(0)), text)
        text = _SB_KEY.sub(lambda m: self._gone("key"), text)
        text = _BEARER.sub(lambda m: f"{m.group(1)} " + self._gone("key"), text)
        text = _JWT.sub(lambda m: self._gone("key"), text)
        text = _PREFIXED.sub(lambda m: self._gone("key"), text)
        text = _SECRET_PAIR.sub(self._pair, text)
        text = _URL.sub(self._url, text)
        text = _EMAIL.sub(lambda m: self._mark("email", m.group(0)), text)
        text = _MAC.sub(lambda m: self._mark("address", m.group(0)), text)
        text = _IPV4.sub(lambda m: self._ip(m, text), text)
        text = _IPV6.sub(lambda m: m.group(0) if m.group(0) == "::1" else self._mark("address", m.group(0)), text)
        text = _WIN_PATH.sub(lambda m: self._mark("path", m.group(0)), text)
        text = _ROOTS.sub(self._path, text)
        text = _UNIX_PATH.sub(self._path, text)
        text = _HOST.sub(self._host, text)
        text = _HEXISH.sub(lambda m: self._gone("key"), text)
        text = _LONG.sub(lambda m: self._gone("key") if _token_like(m.group(0)) else m.group(0), text)
        return text

    def _pair(self, m):
        name, glue, value = m.group(1), m.group(2), m.group(3)
        if value.startswith("[") or (value.lower().strip("\"'.") in _STATE_WORDS and not re.search(r"(?i)pass|secret|key", name)):
            return m.group(0)
        return f"{name}{glue}" + self._gone("secret")

    def _ip(self, m, whole):
        value = m.group(0)
        if value.split(":")[0] in ("127.0.0.1", "0.0.0.0"):
            return value
        before = whole[max(0, m.start() - 9):m.start()].lower()
        if before.endswith(("v", "version ", "ver ", "ver. ")):  # 3.0.8.1 after "version" is a version, not an address
            return value
        return self._mark("address", value)

    def _url(self, m):
        scheme, rest = m.group(1), m.group(2)
        if rest.startswith("["):  # already hidden
            return m.group(0)
        hostport = rest.rsplit("@", 1)[-1]
        host = hostport.split(":")[0]
        if host.lower() in ("localhost", "127.0.0.1") and "@" not in rest:
            return m.group(0)
        return scheme + self._mark("host", host)

    def _path(self, m):
        value = m.group(0)
        if value.startswith(_NOT_FOLDERS) or value in ("/", "//"):
            return value
        return self._mark("path", value.rstrip("/"))

    def _host(self, m):
        value = m.group(0)
        bare = value.split(":")[0].rstrip(".")
        last = bare.rsplit(".", 1)[-1].lower()
        if value.startswith("[") or last in _FILE_ENDINGS:
            return value
        if bare.lower() == "starboard" or last.isdigit():
            return value
        special = last in ("local", "lan", "home", "arpa", "localdomain", "internal", "intranet", "corp", "private", "net", "org", "com") \
            or bare.lower().endswith((".ts.net", ".duckdns.org", ".ddns.net", ".synology.me", ".myfritz.net"))
        if special or last in _REAL_ENDINGS:
            return self._mark("address", bare + (":" + value.split(":")[1] if ":" in value else ""))
        return value


_COMMON = {"the", "and", "app", "apps", "data", "home", "media", "movies", "music", "books", "tv", "film", "films", "series",
           "library", "server", "plex", "jellyfin", "emby", "reelix", "sonarr", "radarr", "lidarr", "readarr", "prowlarr",
           "seerr", "starboard", "docker", "downloads", "download", "config", "local", "none", "true", "false", "null", "test"}


# Fields whose text is a version number, which may look like an address (9.11.0.1) and is not one.
VERSION_FIELDS = {"version", "current", "latest", "roll_back_to", "from", "to", "app_version", "starboard_version"}


def mask(text, words=()):
    """(masked text, counts) for one text."""
    m = Masker(words)
    return m.mask(text), m.counts


def mask_value(value, words=(), drop=None, masker=None):
    """The same for any JSON value: every string is masked, a key of a dict that says it is a secret is dropped, and
    a number, true, false or null stays. Returns (value, counts). `drop`: a pattern for names of fields to drop."""
    m = masker or Masker(words)

    def go(v, depth=0, field=""):
        if depth > 12:
            return "[too deep]"
        if isinstance(v, str):
            m.keep_version = field in VERSION_FIELDS
            try:
                return m.mask(v)
            finally:
                m.keep_version = False
        if isinstance(v, dict):
            return {m.mask(str(k))[:80]: go(x, depth + 1, str(k)) for k, x in v.items() if not (drop and drop.search(str(k)))}
        if isinstance(v, (list, tuple)):
            return [go(x, depth + 1, field) for x in v]
        return v

    return go(value), m.counts


def private_words(app):
    """The names Starboard knows are private to this server: the site's and the server's names, the computer's name,
    the people who use the apps, and the folders, disks and libraries it was given. Read from the saved settings only;
    nothing is fetched."""
    import socket
    d = app.config.data
    words = [d.get("site_name", ""), d.get("server_name", ""), socket.gethostname(), getattr(app, "machine_name", "") or ""]
    for s in d.get("services", []):
        for k in ("root", "folder", "library", "path", "library_name", "media_folder", "download_folder"):
            if isinstance(s.get(k), str):
                words.append(s[k])
        words.append(str(s.get("url", "")))
        for r in s.get("roots") or []:
            words.append(r if isinstance(r, str) else str((r or {}).get("path", "")))
    for p in d.get("people") or []:
        if isinstance(p, dict):
            words += [p.get("name", ""), p.get("username", ""), p.get("email", "")]
    for dk in getattr(app, "disks", None) or []:
        words += [str(dk.get("label", "")) if isinstance(dk, dict) else str(dk), str(dk.get("path", "")) if isinstance(dk, dict) else ""]
    for key in ("disks", "folders", "locations", "libraries"):
        v = d.get(key)
        if isinstance(v, list):
            for x in v:
                words += [x] if isinstance(x, str) else [str(x.get(n, "")) for n in ("name", "label", "path") if isinstance(x, dict)]
        elif isinstance(v, dict):
            words += [str(a) for a in v.keys()] + [str(b) for b in v.values() if isinstance(b, str)]
    seen, out = set(), []
    for w in words:
        w = str(w or "").strip()
        if len(w) >= 3 and w.lower() not in seen and w.lower() not in _COMMON and not w.lower().startswith(("http://", "https://")):
            seen.add(w.lower())
            out.append(w)
    return out
