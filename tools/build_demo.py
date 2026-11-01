#!/usr/bin/env python3
"""Builds one self-contained HTML page that shows the Apps page in all five designs, with made-up sample data.

Used to review designs without a server: python3 tools/build_demo.py  ->  demo-build/starboard-designs.html
"""

import base64
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from apply_shell import shell  # noqa: E402

WEB = ROOT / "web"

SAMPLE = r"""
// Sample data only: these are not anyone's real apps.
const SAMPLE_SERVICES = [
  ["jellyfin", "Jellyfin", "Watch and listen", "Films, TV and music on every screen", "10.11.2", 18],
  ["audiobookshelf", "Audiobookshelf", "Watch and listen", "Audiobooks and podcasts, with your place remembered", "2.30.0", 22],
  ["seerr", "Seerr", "Requests", "Ask for films and series; they download automatically", "2.7.3", 41],
  ["wizarr", "Wizarr", "Requests", "Invite links for new viewers", "", null],
  ["sonarr", "Sonarr", "Downloads", "Finds and downloads TV series", "4.0.16", 14],
  ["radarr", "Radarr", "Downloads", "Finds and downloads films", "6.0.4", 15],
  ["lidarr", "Lidarr", "Downloads", "Finds and downloads music", "3.1.0", 12],
  ["readarr", "Readarr", "Downloads", "Finds and downloads books", "0.4.18", 16],
  ["prowlarr", "Prowlarr", "Downloads", "Manages the indexers the others search", "2.1.5", 11],
  ["qbittorrent", "qBittorrent", "Downloads", "Torrent downloads", "5.1.2", 9],
  ["bazarr", "Bazarr", "Tools", "Subtitles for films and series", "1.5.3", 27],
  ["jellystat", "Jellystat", "Tools", "Who watched what, and when", "1.1.6", 33],
];
const SAMPLE_CONFIG = {
  site_name: "Starboard", design: "tiles", groups: ["Watch and listen", "Requests", "Downloads", "Tools"],
  services: SAMPLE_SERVICES.map(([id, name, group, description]) => ({ id, name, group, description, enabled: true, link: "#" })),
};
api = async (path) => {
  await new Promise((r) => setTimeout(r, 250));
  if (path === "/api/session") return { signed_in: true, site_name: "Starboard", design: "tiles", version: "0.1.0" };
  if (path === "/api/config") return SAMPLE_CONFIG;
  if (path === "/api/health") return { items: [{ service_name: "Radarr", level: "warning", message: "Indexers unavailable due to failures: one indexer" }], errors: [] };
  if (path === "/api/status") return { items: SAMPLE_SERVICES.map(([id, , , , version, ms]) => (ms === null
    ? { id, state: "down", message: "Cannot reach Wizarr" } : { id, state: "up", version, ms })) };
  if (path === "/api/queue") return { errors: [], items: [
    { service_name: "Sonarr", title: "Example Series S02E05 1080p", status: "downloading", progress: 64, size: 1.4e9, time_left: "00:12:40", client: "qBittorrent", messages: [] },
    { service_name: "Radarr", title: "Example Film (2024) 2160p", status: "downloading", progress: 21, size: 1.8e10, time_left: "01:40:00", client: "SABnzbd", messages: [] },
    { service_name: "Lidarr", title: "Example Artist - Example Album (2025) FLAC", status: "paused", progress: 90, size: 4.1e8, time_left: "", client: "qBittorrent", messages: [] },
  ] };
  if (path === "/api/calendar") {
    const day = (n) => new Date(Date.now() + n * 86400000).toISOString();
    return { errors: [], items: [
      { service_name: "Sonarr", title: "Example Series", detail: "S02E06 · The Next One", when: day(1), have: false },
      { service_name: "Radarr", title: "Example Film", detail: "Film", when: day(4), have: false },
      { service_name: "Readarr", title: "Example Novel", detail: "Example Author", when: day(9), have: false },
    ] };
  }
  throw new Error("Not available in the demo");
};

// The design switcher shown at the top of the demo only.
document.addEventListener("DOMContentLoaded", () => {
  const bar = $("#design-switcher");
  const desc = $("#design-description");
  const pick = (key) => {
    const prefs = { ...readPrefs(), design: key };
    writePrefs(prefs);
    applyPrefs(prefs);
    $$("button", bar).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.design === key)));
    desc.textContent = DESIGNS[key][1];
  };
  Object.entries(DESIGNS).forEach(([key, [label]], i) => bar.append(el("button", {
    type: "button", class: "filter", "data-design": key, onclick: () => pick(key),
  }, `${i + 1}. ${label}`)));
  pick(DESIGNS[readPrefs().design] ? readPrefs().design : "tiles");
  $$("#main-nav a, .brand").forEach((a) => a.addEventListener("click", (e) => {
    e.preventDefault();
    toast(`In the dashboard this opens ${a.getAttribute("href").replace("/", "")}`);
  }));
  $$("form[role=search]").forEach((f) => f.addEventListener("submit", (e) => {
    e.preventDefault();
    toast("In the dashboard this searches Sonarr, Radarr, Lidarr and Readarr at once");
  }));
});
"""

SWITCHER = """<section class="panel" aria-labelledby="design-switcher-title">
  <div class="panel__head">
    <h2 id="design-switcher-title">Design ideas</h2>
    <p class="hint">The same Apps page in each design, with sample apps. 1 to 5 are the first ideas; 6 to 9 are alternatives to Calm. Display (top right) has the accessibility settings.</p>
  </div>
  <div class="filters" id="design-switcher" role="group" aria-label="Design"></div>
  <p id="design-description" aria-live="polite"></p>
</section>"""


def main():
    font = base64.b64encode((WEB / "fonts/atkinson-hyperlegible-next.woff2").read_bytes()).decode()
    css = "\n".join((WEB / "css" / name).read_text() for name in ("tokens.css", "app.css", "designs.css"))
    css = css.replace('url("../fonts/atkinson-hyperlegible-next.woff2")', f'url("data:font/woff2;base64,{font}")')
    page = (WEB / "index.html").read_text()
    body = re.search(r"<main.*?</main>", page, re.S).group(0)
    body = body.replace('<div class="page">', '<div class="page">\n' + SWITCHER, 1)
    js = (WEB / "js/common.js").read_text() + SAMPLE + (WEB / "js/apps.js").read_text()
    html = f"""<title>Starboard designs</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
{css}
</style>
<div class="page-apps">
{shell("index.html")}
{body}
</div>
<script>
{js}
</script>
"""
    out = ROOT / "demo-build" / "starboard-designs.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
