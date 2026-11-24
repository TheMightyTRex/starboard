"""A health line on the Reelix app card (DASH-559; owner, 23 November 2026, from a look at Dashbrr's Prowlarr summary):
"3 of 40 sites failing", with a link to the page that lists them.

Which Reelix call gives the numbers (checked in the Reelix source, crates/reelix-api and reelix-providers):
- GET /api/v1/system/health, with the manager key Starboard already holds, names each site that is backed off after
  failures ("Indexer X is unavailable due to failures until ...") or misconfigured, and says when all of them are
  unavailable or none is on. It does not say how many sites there are, and it answers 503 when a check is an error.
- GET /api/v1/indexers/stats and GET /api/v1/indexers give every site and its failure count, but need Reelix's admin
  rights; the manager key is refused (403), so Starboard cannot ask in the background.
So the failing sites come from /system/health when the card refreshes, and the total from the last time the admin
password was used on Settings, Reelix, Sites to search (kept in data/reelix-sites.json, trusted for a week, as
reelix_direct_health does for direct downloads). Without a total the line says "3 sites failing". When Reelix does not
answer, or answers with anything unexpected, there is no line at all rather than a wrong number. Nothing here changes
Reelix or its interface, and nothing is asked more often than the card refreshes (once a minute at most).
"""
import json
import os
import re
import time
import urllib.error

from . import jsonhttp, services

FILE = "reelix-sites.json"
KEEP_FOR = 7 * 86400
PAGE = "/settings-reelix.html#rx-indexers"
FAILING = re.compile(r"^Indexer (.+) is (?:unavailable due to failures|misconfigured)")


def _path(data_dir):
    return os.path.join(data_dir, FILE)


def record(data_dir, items):
    """Keeps how many sites Reelix has, from the listing the admin password just read. Written only when it changed."""
    if not data_dir or not isinstance(items, list):
        return
    mine = [i for i in items if isinstance(i, dict)]
    now = {"total": len(mine), "enabled": sum(1 for i in mine if i.get("enabled", True))}
    old = read(data_dir, now=0, any_age=True)
    if old and (old.get("total"), old.get("enabled")) == (now["total"], now["enabled"]) and time.time() - old.get("at", 0) < 86400:
        return
    tmp = _path(data_dir) + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({**now, "at": time.time()}, f)
        os.replace(tmp, _path(data_dir))
    except OSError:
        pass


def read(data_dir, now=None, any_age=False):
    try:
        with open(_path(data_dir), encoding="utf-8") as f:
            got = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(got, dict) or not isinstance(got.get("enabled"), int):
        return {}
    if not any_age and (now or time.time()) - float(got.get("at") or 0) > KEEP_FOR:
        return {}
    return got


def _health(reelix):
    """Reelix's checks, or None when it did not answer in the way expected. A 503 still carries the report."""
    url = reelix["url"].rstrip("/") + "/system/health"
    try:
        answer = jsonhttp.request(url, headers={"X-Api-Key": reelix["api_key"]}, timeout=services.TIMEOUT, limit=2_000_000)
    except urllib.error.HTTPError as e:
        if e.code != 503:
            return None
        try:
            answer = json.loads(e.read(2_000_000))
        except (OSError, ValueError):
            return None
    except (OSError, ValueError):
        return None
    checks = answer.get("checks") if isinstance(answer, dict) else None
    return checks if isinstance(checks, list) else None


def words(checks, enabled):
    """The line for one set of Reelix's checks and the number of sites on at the last look (or None), or None for
    nothing to say."""
    mine = [c for c in checks if isinstance(c, dict) and c.get("source") == "indexers"]
    messages = [str(c.get("message") or "") for c in mine]
    failing = {m.group(1) for m in map(FAILING.match, messages) if m}
    if any(m.startswith("No indexers are enabled") for m in messages):
        return "No sites to search are turned on"
    everything = any(m.startswith("All indexers are unavailable") for m in messages)
    if enabled is not None and (len(failing) > enabled or enabled < 1):
        enabled = None  # the sites changed since the last look: a total that cannot be right is left out
    if everything:
        return f"All {enabled} sites failing" if enabled else "All sites failing"
    n = len(failing)
    if n:
        return f"{n} of {enabled} sites failing" if enabled else f"{n} {'site' if n == 1 else 'sites'} failing"
    if enabled:
        return f"{enabled} {'site' if enabled == 1 else 'sites'} to search, none failing"
    return None


def line(services_list, data_dir):
    """{service id: {"text", "href"}} for the Reelix card, or {} when there is nothing to say."""
    out = {}
    for reelix in services.reelix_native(services_list):
        checks = _health(reelix)
        if checks is None:
            continue
        seen = read(data_dir) if data_dir else {}
        text = words(checks, seen.get("enabled") if seen else None)
        if text:
            out[reelix["id"]] = {"text": text, "href": PAGE}
    return out
