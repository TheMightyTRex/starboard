// The dashboard (DASH-239): the landing page once set up, made of cards in one of four layouts (At a glance by
// default). Edit dashboard adds, removes, sizes and moves cards, and goes back to the layout's own; the choice is
// saved to the account. Light on the server: a card asks only for what it shows, only cards on the dashboard ask,
// nothing is asked while the tab is hidden, and they refresh once a minute. Set-up tasks sits at the top while
// anything is left to set up, and cannot be removed until it is all done.

const CARD_TITLES = {
  setup: "Still to set up", playing: "Now playing", downloads: "Downloads", coming: "Coming up", recent: "Recently added",
  disk: "Disk space", load: "System load", vpn: "VPN", speed: "Transfer speed", health: "Service health",
  requests: "Requests", alerts: "Alerts", links: "Quick links",
};
// A built-in card's shorter name for a size where its own does not fit on one line in the band (DASH-443, measured
// at the default text size and the narrowest desktop width of each size). Every name fits today, so none is needed.
const CARD_SHORT = {};
// Every built-in card's band (DASH-442, owner 15 November 2026): the logo on its left. A card about one app shows that
// app's own logo, the same file as on the Apps page (/api/icons/<app>); a card that combines several apps, or is
// Starboard's own, shows a design system icon on the standard tile. "apps" lists the apps the card's answer comes
// from (an app is its type, and every part of Reelix counts as "reelix"); the logo is theirs when exactly one of them
// is set up. "byType": the server asks by type only (Recently added asks Sonarr, Radarr, Lidarr and Readarr, and
// Reelix's entries at those addresses, not the Reelix link). "first": the first app set up wins, as the server asks
// Seerr before Reelix for requests. "time": the
// band says when it was updated, only for answers the server keeps for 20 seconds or less, so the time is true.
const ARR_APPS = ["reelix", "sonarr", "radarr", "lidarr", "readarr"];
const CARD_BAND = {
  setup: { own: "list-checks" },
  playing: { apps: ["jellyfin"], own: "play", time: true },
  downloads: { apps: ARR_APPS, own: "download", time: true },
  coming: { apps: ARR_APPS, own: "calendar-days" },
  recent: { apps: ARR_APPS, byType: true, own: "sparkles" },
  disk: { own: "hard-drive", time: true },
  load: { own: "cpu", time: true },
  vpn: { apps: ["gluetun"], own: "shield-check", time: true },
  speed: { apps: ["qbittorrent", "nzbget", "sabnzbd"], own: "gauge", time: true },
  health: { own: "heart-pulse", time: true },
  requests: { apps: ["seerr", "reelix"], first: true, own: "inbox", time: true },
  alerts: { own: "bell" },
  links: { own: "link" },
};
const JSON_BAND = { own: "list", time: true };  // a custom card for any service's JSON (DASH-555): its own name, and when it was asked
let services = [];  // the apps set up, from /api/config, for the logos
const LAYOUTS = {
  glance: { name: "At a glance", cards: [["playing", "half"], ["health", "half"], ["downloads", "half"], ["coming", "half"], ["recent", "full"],
    ["disk", "small"], ["load", "small"], ["vpn", "small"], ["alerts", "small"]] },
  watch: { name: "Watch and listen", cards: [["playing", "full"], ["recent", "full"], ["coming", "half"], ["requests", "half"]] },
  downloads: { name: "Downloads and storage", cards: [["downloads", "wide"], ["vpn", "small"], ["speed", "small"], ["disk", "small"],
    ["alerts", "half"], ["load", "half"], ["health", "half"]] },
  compact: { name: "Compact", cards: [["health", "small"], ["downloads", "small"], ["vpn", "small"], ["disk", "small"], ["links", "full"]] },
};
const SIZES = { small: "Small", medium: "Medium", half: "Half", wide: "Wide", full: "Full width" };
let dash = { layout: "glance", cards: null };
let editing = null;  // the cards while Edit dashboard is open
let timer = null;

const cardsOf = (d) => (d.cards || LAYOUTS[d.layout].cards.map(([id, size]) => ({ id, size })));
const ago = (iso) => (iso ? new Date(iso).toLocaleString("en-GB", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "");
const line = (title, meta, href) => el("li", { class: "row row--no-lead" }, el("div", {},
  el("div", { class: "row__title" }, href ? el("a", { href, text: title }) : title), meta ? el("div", { class: "row__meta", text: meta }) : null));
const empty = (text, href, label) => el("p", { class: "small muted" }, text, href ? [" ", el("a", { href, text: label })] : null);

// Each card: what it asks for, and what it shows. One answer can serve several cards on the page (shared).
const SOURCES = {};
const ask = (url) => (SOURCES[url] ||= api(url).finally(() => setTimeout(() => { delete SOURCES[url]; }, 5000)));
const CARDS = {
  async setup() {
    const r = await ask("/api/setup/left");
    const todo = r.items.filter((i) => !i.done && !i.ignored);
    if (!todo.length) return null;
    // The wizard (DASH-289): one item at a time; it opens only from Go through them (owner, 12 November 2026).
    // One primary in view (DASH-309, R9): while the dashboard is edited, Save is the primary button.
    const walk = el("button", { type: "button", class: editing ? "btn btn--compact" : "btn btn--primary btn--compact", "aria-haspopup": "dialog" }, "Go through them");
    walk.addEventListener("click", () => setupWizard({ opener: walk, onChange: () => { walkBack = true; draw(); } }));
    if (!editing) setupWizardOnce(() => draw());
    // Its button sits at the right of the card's band (owner, 15 November 2026).
    return { node: el("ul", { class: "rows" }, todo.map((i) => line(i.title, i.why, i.href.startsWith("http") ? reachableUrl(i.href) : i.href))), action: walk };
  },
  async playing() {
    const r = await ask("/api/jellyfin");
    if (!r.configured) {  // the words follow the media server in use (DASH-565)
      const ms = await ask("/api/media-server").catch(() => null);
      if (ms && !ms.active) return empty("Choose a media server to show what is playing here.", "/settings-jellyfin.html", "Choose a media server");
      return empty(`Add ${ms?.name || "your media server"} with its key to show what is playing here.`, "/settings.html", "Manage apps");
    }
    return r.playing.length ? el("ul", { class: "rows" }, r.playing.slice(0, 5).map((p) => line(p.title || "Something", [p.user, p.device].filter(Boolean).join(" · "))))
      : empty("Nothing is playing.");
  },
  async downloads() {
    const r = await ask("/api/queue");
    const items = r.items || [];
    if (!items.length) return empty("Nothing is downloading.", "/wanted-films.html", "Open Wanted");
    return band(["Downloading", "info"], el("ul", { class: "rows" }, items.slice(0, 5).map((q) => line(q.title, [`${Math.round(q.progress || 0)}%`, q.time_left].filter(Boolean).join(" · "), "/downloads.html"))));
  },
  async coming() {
    const r = await ask("/api/calendar");
    const items = (r.items || []).filter((i) => new Date(i.when) >= new Date(Date.now() - 864e5)).slice(0, 6);
    return items.length ? el("ul", { class: "rows" }, items.map((i) => line(i.title, [i.detail, ago(i.when)].filter(Boolean).join(" · "), "/upcoming.html")))
      : empty("Nothing coming up in the next days.");
  },
  async recent() {
    const r = await ask("/api/recent");
    const items = (r.items || []).slice(0, 8);
    return items.length ? el("ul", { class: "rows" }, items.map((i) => line(i.title, [i.detail, ago(i.when)].filter(Boolean).join(" · ")))) : empty("Nothing added this week.");
  },
  async disk() {
    const r = await ask("/api/system");
    const disks = r.disks || [];
    // The same words and limits as System, Storage: Full at 98% used, Nearly full at 90%; nothing to say otherwise.
    const used = (d) => (d.total ? 100 * (d.total - d.free) / d.total : 0);
    const most = Math.max(0, ...disks.map(used));
    return band(most >= 98 ? ["Full", "danger"] : most >= 90 ? ["Nearly full", "warning"] : null,
      el("ul", { class: "rows" }, disks.slice(0, 4).map((d) => line(d.label || d.path || "Disk",
        d.total ? `${formatBytes(d.free)} free of ${formatBytes(d.total)}` : "", "/system-storage.html"))));
  },
  async load() {
    const r = await ask("/api/system");
    const mem = r.memory || {};
    return el("dl", { class: "facts" }, el("dt", { text: "Processor" }), el("dd", { text: r.load ? `${Number(r.load[0] ?? r.load).toFixed(2)} (${r.cpus} cores)` : "Not reported" }),
      el("dt", { text: "Memory" }), el("dd", { text: mem.total ? `${formatBytes(mem.used)} of ${formatBytes(mem.total)}` : "Not reported" }));
  },
  async vpn() {
    const r = await ask("/api/transfer");
    if (!r.vpn?.length) {
      // DASH-440: downloading without a VPN is a choice, so a quiet state with the way to add one, never an error.
      let st = null;
      try { st = await ask("/api/downloads/vpn-state"); } catch { /* the plain words below */ }
      if (!st?.downloads) return empty("No VPN on your apps.");
      // A VPN is installed but its state could not be read (Docker did not answer): never say No VPN then.
      if (st.on) return band(["Not known", "muted"], el("p", { class: "small muted", text: "Downloads are set to go through the VPN. Starboard could not read its state a moment ago." }));
      return band(["No VPN", "muted"], el("div", { class: "stack-2" },  // the chip in the band, as every card (DASH-442)
        el("p", { class: "small muted", text: "Downloads use your home internet address." }),
        el("p", { class: "small" }, el("a", { href: "/settings-downloads.html", text: "Add a VPN" }))));
    }
    const v = r.vpn[0];
    return band(v.running ? ["Connected", "success"] : ["Not connected", "danger"],  // in the band (DASH-442; DASH-309's title line)
      el("div", { class: "stack-2" }, v.country ? el("p", { class: "small", text: [v.country, v.ip].filter(Boolean).join(" · ") }) : null));
  },
  async speed() {
    const r = await ask("/api/transfer");
    if (!r.clients?.length) return empty("No download app with its key yet.");
    return el("ul", { class: "rows" }, r.clients.map((c) => line(c.name, `Down ${c.down_text || "0"} · Up ${c.up_text || "0"}`)));
  },
  async health() {
    const [r, cfg] = await Promise.all([ask("/api/status"), ask("/api/config")]);
    const names = Object.fromEntries((cfg.services || []).map((x) => [x.id, x.name]));
    const items = (r.items || []).map((i) => ({ ...i, name: names[i.id] || i.id }));
    const down = items.filter((i) => i.state === "down");
    return band(down.length ? STATUS.notResponding : STATUS.running, el("div", { class: "stack-2" },
      // The chip holds no number (DASH-309, R3): how many is in the line under it.
      el("p", { class: "small muted", text: down.length ? `${down.length} of ${items.length} apps not responding` : `${items.length} apps` }),
      down.length ? el("ul", { class: "rows" }, down.slice(0, 4).map((d) => line(d.name || d.id, d.message || "", "/index.html"))) : null));
  },
  async requests() {
    const r = await ask("/api/requests?pending=1");
    if (!r.configured) return empty("Add Reelix or Seerr to show requests here.");
    return r.items.length ? band(["Pending", "neutral"], el("ul", { class: "rows" }, r.items.slice(0, 5).map((q) => line(q.title, q.by ? `asked for by ${q.by}` : "", "/downloads-requests.html"))))
      : empty("Nothing waiting for approval.");
  },
  async alerts() {
    const r = await ask("/api/logs?level=problems");
    const items = (r.entries || []).slice(-5).reverse();
    return items.length ? el("ul", { class: "rows" }, items.map((e) => line(e.message || e.text || "", ago(e.time ? new Date(e.time * 1000).toISOString() : ""), "/system-logs.html")))
      : empty("No problems lately.");
  },
  async links() {
    const cfg = await ask("/api/config");
    const apps = (cfg.services || []).filter((x) => x.enabled !== false && x.link && !x.background).slice(0, 16);
    return el("div", { class: "dash-links" }, apps.map((a) => el("a", { class: "btn btn--quiet", href: reachableUrl(a.link), target: "_blank", rel: "noopener noreferrer" },
      a.name, el("span", { class: "visually-hidden", text: " (opens in a new tab)" }))));
  },
};

// A custom card for any service's JSON (DASH-555): Starboard asks its address when the card is shown (the server keeps the
// answer for the card's refresh time), and draws the chosen fields as keys and values. The text is never treated as HTML.
async function jsonCard(id) {
  let r;
  try { r = await api(`/api/json-cards/${id}/answer`); } catch (e) {
    if (e.status === 404) return empty("This custom card was removed. Take it off the dashboard with Edit dashboard.");
    throw e;
  }
  if (r.problem) return band(STATUS.notWorking, empty(r.problem, "/apps-services.html#custom-cards-h", "Check it in Other services"));
  const worst = { ok: STATUS.healthy, warning: STATUS.needsAttention, problem: STATUS.notWorking }[r.state] || null;
  const rows = r.items.flatMap((it) => {
    const st = { ok: STATUS.healthy, warning: STATUS.needsAttention, problem: STATUS.notWorking }[it.state];
    return [el("dt", { text: it.label }), el("dd", {}, it.value, it.unit ? ` ${it.unit}` : null, st ? " " : null, st ? chip(st[0], st[1]) : null)];
  });
  return { ...band(worst, el("dl", { class: "facts" }, rows)), asked: r.asked * 1000 };
}

// Cards from active plug-ins (DASH-149): Starboard asks the plug-in and draws the answer itself, as text only.
let pluginCards = {};
const FORMATS = {
  number: (v) => Number(v).toLocaleString("en-GB"),
  bytes: (v) => { let n = Number(v), u = 0; const units = ["bytes", "KB", "MB", "GB", "TB"]; while (n >= 1024 && u < 4) { n /= 1024; u++; } return `${n.toFixed(u ? 1 : 0)} ${units[u]}`; },
  percent: (v) => `${Math.round(Number(v))}%`,
  duration: (v) => { const m = Math.round(Number(v) / 60); return m >= 60 ? `${Math.floor(m / 60)} h ${m % 60} min` : `${m} min`; },
  date: (v) => new Date(Number(v) * 1000).toLocaleDateString("en-GB"),
};
// A card's own refresh time (plug-in API 1.14, owner 14 November 2026): the answer's refresh_seconds, never under
// 10 seconds. Cards due together are asked in one request, and nothing is asked while the tab is hidden.
const OWN_FLOOR = 10;
const ownTimes = new Map();  // card id -> {every (seconds), at (when it was last drawn)}
async function pluginCard(id, given) {
  const [, pid, cid] = id.split(":");
  const r = given || await api(`/api/plugins/${pid}/cards/${cid}`);
  if (r.refresh_seconds) ownTimes.set(id, { every: Math.max(OWN_FLOOR, Number(r.refresh_seconds) || 0), at: Date.now() });
  else ownTimes.delete(id);
  drawBandSide(id, r);
  if (r.problem) return empty(r.problem);
  const d = r.data;
  if (r.type === "stat") return el("p", { class: "dash-stat" }, el("strong", { text: (FORMATS[r.format] || FORMATS.number)(d.value) }),
    d.label ? ` ${d.label}` : null, d.note ? el("span", { class: "small muted", text: ` ${d.note}` }) : null);
  // A status card's state is the band's chip (API 1.14), unless the answer gave its own status as well.
  if (r.type === "status") return el("div", {}, d.status ? el("p", { class: "small", text: STATE_BAND[d.state]?.[0] }) : null,
    d.text ? el("p", { text: d.text }) : null);
  if (r.type === "guide") return guideCard(d);
  if (r.type === "sparkline") return sparklineCard(d);
  return d.items.length ? el("ul", { class: "rows" }, d.items.map((it) => el("li", { class: "row row--no-lead" }, el("div", {},
    el("div", { class: "row__title" }, it.link ? el("a", { href: it.link, target: "_blank", rel: "noopener noreferrer" }, it.title, el("span", { class: "visually-hidden", text: " (opens in a new tab)" })) : it.title),
    it.detail ? el("div", { class: "row__meta", text: it.detail }) : null)))) : empty("Nothing to show.");
}

// The card band (plug-in API 1.14, DASH-428, design 2 "band with status"): every plug-in card has a grey band with
// its logo, the plug-in's name as the heading, and at the right a status chip and when it last updated. The chip and
// the time each start with hidden words ("Status: ", "Updated "), so each makes sense to a screen reader on its own.
const STATE_BAND = { ok: STATUS.healthy, warning: STATUS.needsAttention, problem: STATUS.notWorking };
// A title for each size (plug-in API 1.15, DASH-443, owner 15 November 2026): a card that gives one for its size has
// that title alone as its heading, on one line (the manifest check keeps it short enough); the plug-in's name follows
// for screen readers when the title does not say it. A size it left out shows the plug-in's name and the card's title.
function pluginBand(c) {
  const info = pluginCards[c.id] || {};
  const name = info.plugin || "Plug-in";
  const own = info.titles?.[c.size];
  const sub = !own && info.title && info.title !== name ? info.title : "";
  const heading = own
    ? [own, own.toLowerCase().includes(name.toLowerCase()) ? null : el("span", { class: "visually-hidden", text: `, ${name}` })]
    : [name, sub ? el("span", { class: "card-band__sub" }, el("span", { class: "visually-hidden", text: ", " }), sub) : null];
  return el("div", { class: "card-band" }, pluginLogo({ name, logo: info.logo }, { compact: true }),
    el("h2", { class: "card-band__title dash-card__title", id: `dash-${c.id}-h` }, ...heading),
    el("span", { class: "card-band__side" }));
}

function drawBandSide(id, r) {
  const d = r.data || {};
  const [words, tone] = d.status_label ? [d.status_label, d.tone || "neutral"] : r.type === "status" && STATE_BAND[d.state] ? STATE_BAND[d.state] : [];
  bandSide($(`[data-card="${id}"] .card-band__side`), words, tone, (d.updated || r.asked || 0) * 1000);
}

// The band's right-hand side, the same for plug-in and built-in cards: a status chip, then when it was updated.
// The band's right-hand side, the same for plug-in and built-in cards: the status chip (and a card's own button), with
// when the card was updated in a small footer, so the band stays on one line (owner, 16 November 2026, design B).
function bandSide(side, words, tone, when, action) {
  if (!side) return;
  const card = side.closest(".dash-card");
  side.replaceChildren(...[
    words ? el("span", { class: "chip", "data-tone": tone }, icon(CHIP_ICONS[tone] || "circle", 14),
      el("span", { class: "visually-hidden", text: "Status: " }), el("span", { class: "chip__words", text: words })) : null,
    action || null].filter(Boolean));
  card?.querySelector(":scope > .card-foot")?.remove();
  if (card && when) {
    card.append(el("div", { class: "card-foot" },
      el("time", { class: "card-band__time", datetime: new Date(when).toISOString(), "data-at": String(when) },
        el("span", { text: "Updated " }), el("span", { text: timeAgo(when) }))));
  }
}

// A built-in card's answer with something to say in its band (DASH-442): a state chip, from the shared vocabulary,
// never a number (DESIGN-SYSTEM.md, Chips). Cards with nothing to say return their node alone.
const band = (chipOf, node) => ({ node, chip: chipOf });

// The logo for a built-in card (CARD_BAND): the one app's own icon, or the card's design system icon on the tile.
const appOf = (s) => (s.icon === "reelix" ? "reelix" : s.type);
function cardLogo(id) {
  const b = CARD_BAND[id] || (id.startsWith("json:") ? JSON_BAND : {});
  const on = services.filter((s) => s.enabled !== false && (b.apps || []).includes(b.byType ? s.type : appOf(s)));
  const kinds = [...new Set(on.map(appOf))];
  const app = b.first ? b.apps.find((k) => kinds.includes(k)) : kinds.length === 1 ? kinds[0] : null;
  const s = app && on.find((x) => appOf(x) === app);
  // Decorative either way: the card's name is beside it. data-app says whose logo it is (or "starboard").
  const logo = s ? appIcon(s, "app-icon app-icon--compact") : el("span", { class: "app-icon app-icon--compact", "aria-hidden": "true" }, icon(b.own || "layout-dashboard"));
  logo.dataset.app = s ? app : "starboard";
  return logo;
}
function builtinBand(c) {
  return el("div", { class: "card-band" }, cardLogo(c.id),
    el("h2", { class: "card-band__title dash-card__title", id: `dash-${c.id}-h`, text: CARD_SHORT[c.id]?.[c.size] || CARD_TITLES[c.id] || "Card" }),
    el("span", { class: "card-band__side" }));
}

// The band's time is kept in words as it ages, without asking the plug-in again; it is not a live region.
function ageBandTimes() {
  for (const t of document.querySelectorAll(".card-band__time[data-at]")) t.lastElementChild.textContent = timeAgo(Number(t.dataset.at));
}

// A guide card (plug-in API 1.8, DASH-359, owner 13 November 2026): what is on now on each channel, how far through
// it is and what is next, such as Live TV's On TV now.
function guideCard(d) {
  const hm = (t) => new Date(t * 1000).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  const now = Date.now() / 1000;
  if (!d.items.length) return empty(d.note || "Nothing on now.");
  return el("div", { class: "stack-2" }, d.note ? el("p", { class: "small muted", text: d.note }) : null,
    el("ul", { class: "rows guide-card" }, d.items.map((it) => {
      const pct = it.start && it.stop && it.stop > it.start ? Math.max(0, Math.min(100, Math.round(100 * (now - it.start) / (it.stop - it.start)))) : null;
      const bar = pct === null ? null : el("div", { class: "progress", role: "progressbar", "aria-valuenow": String(pct), "aria-valuemin": "0", "aria-valuemax": "100",
        "aria-label": `${it.now}: ${pct}% through` }, el("span"));
      if (bar) bar.firstChild.style.width = `${pct}%`;  // set in script: the page's policy blocks style attributes
      return el("li", { class: "row row--no-lead" }, el("div", { class: "guide-card__item" },
        el("div", { class: "row__title" }, el("span", { class: "guide-card__num", text: it.number }), ` ${it.channel}`),
        el("div", { text: it.now + (it.start && it.stop ? `, ${hm(it.start)} to ${hm(it.stop)}` : "") }),
        bar,
        it.next ? el("div", { class: "row__meta", text: `Next: ${it.next}${it.next_start ? ` at ${hm(it.next_start)}` : ""}` }) : null));
    })));
}

// A sparkline card (plug-in API 1.17), such as Advanced dashboard's response times: one row a series with its title,
// a small line, then the latest, lowest and highest value in words, which Starboard works out (summary), and the
// plug-in's detail. The line is decoration for sighted people: hidden from screen readers, who get the words. It is
// drawn in currentColor with no fill and no animation, so it follows light, dark, high contrast and forced colours.
const SPARK_NS = "http://www.w3.org/2000/svg";
function sparkLine(points) {
  const w = 96, h = 24, pad = 2;
  const known = points.filter((p) => p !== null);
  const low = Math.min(...known), high = Math.max(...known);
  const x = (i) => (points.length === 1 ? w / 2 : (i * w) / (points.length - 1));
  const y = (v) => (high === low ? h / 2 : pad + ((high - v) * (h - 2 * pad)) / (high - low));
  // Broken at each gap (null): one path segment for each run of points, a dot for a point on its own.
  let d = "", run = false;
  points.forEach((p, i) => {
    if (p === null) { run = false; return; }
    d += `${run ? "L" : "M"}${x(i).toFixed(2)} ${y(p).toFixed(2)}`;
    if (!run && (i === points.length - 1 || points[i + 1] === null)) d += "h0";
    run = true;
  });
  const svg = document.createElementNS(SPARK_NS, "svg");
  for (const [k, v] of Object.entries({ class: "spark-card__line", viewBox: `0 0 ${w} ${h}`, preserveAspectRatio: "none",
    "aria-hidden": "true", focusable: "false" })) svg.setAttribute(k, v);
  const path = document.createElementNS(SPARK_NS, "path");
  for (const [k, v] of Object.entries({ d, fill: "none", stroke: "currentColor", "stroke-width": "2", "stroke-linecap": "round",
    "stroke-linejoin": "round", "vector-effect": "non-scaling-stroke" })) path.setAttribute(k, v);
  svg.append(path);
  return svg;
}
function sparklineCard(d) {
  if (!d.series.length) return empty(d.note || "Nothing to show.");
  return el("div", { class: "stack-2" },
    el("ul", { class: "rows spark-card" }, d.series.map((s) => el("li", { class: "row row--no-lead" }, el("div", { class: "spark-card__item" },
      el("div", { class: "row__title", text: s.title }),
      s.points.some((p) => p !== null) ? sparkLine(s.points) : null,
      el("div", { class: "spark-card__words", text: s.summary }),
      s.detail ? el("div", { class: "row__meta", text: s.detail }) : null)))),
    d.note ? el("p", { class: "small muted", text: d.note }) : null);
}

// A card's name for its size, in Edit dashboard's tools: a plug-in card's own title for that size (API 1.15) or a
// built-in card's shorter name for it (CARD_SHORT), else its usual name.
function nameFor(c) {
  const p = pluginCards[c.id];
  if (p?.titles?.[c.size]) return `${p.titles[c.size]} (${p.plugin})`;
  return CARD_SHORT[c.id]?.[c.size] || CARD_TITLES[c.id];
}

function cardShell(c, i, list) {
  // Every card is drawn with the band: plug-in cards since API 1.14, built-in cards since DASH-442. The head under it
  // holds only the tools while the dashboard is edited.
  const head = el("div", { class: "dash-card__head" });
  const body = el("div", { class: "dash-card__body" }, el("p", { class: "small muted", text: "Asking…" }));
  const card = el("section", { class: `dash-card dash-card--${c.size} has-band`, "aria-labelledby": `dash-${c.id}-h`, "data-card": c.id },
    c.id.startsWith("plugin:") ? pluginBand(c) : builtinBand(c), editing ? head : null, body);
  if (editing) {
    const size = el("select", { class: "select", "aria-label": `Size of ${nameFor(c)}` },
      Object.entries(SIZES).map(([v, t]) => el("option", { value: v, text: t, selected: v === c.size })));
    // The card is drawn again at its new size, with its title for that size; focus stays on its size list.
    size.addEventListener("change", () => { list[i].size = size.value; draw(); $(`[data-card="${c.id}"] .dash-card__tools select`)?.focus(); });
    const move = (by) => { const j = i + by; if (j < 0 || j >= list.length) return; [list[i], list[j]] = [list[j], list[i]]; draw(); $(`[data-card="${c.id}"] button`)?.focus(); };
    head.append(el("div", { class: "dash-card__tools" }, size,
      el("button", { type: "button", class: "icon-btn", "aria-label": `Move ${nameFor(c)} earlier`, disabled: i === 0, onclick: () => move(-1) }, icon("arrow-up")),
      el("button", { type: "button", class: "icon-btn", "aria-label": `Move ${nameFor(c)} later`, disabled: i === list.length - 1, onclick: () => move(1) }, icon("arrow-down")),
      c.id === "setup" ? null : el("button", { type: "button", class: "btn btn--quiet btn--compact", onclick: () => { list.splice(i, 1); draw(); announce(`${nameFor(c)} removed`); } }, "Remove",
        el("span", { class: "visually-hidden", text: ` ${nameFor(c)}` }))));
  }
  return { card, body };
}

// The wizard draws the dashboard again as it closes, so Go through them is a new button by the time the slide-out
// would give focus back; it gets focus here once drawn, unless the person has moved on (DASH-443).
let walkBack = false;
function focusWalk(button) {
  if (!walkBack || $("#side-panel")) return;
  walkBack = false;
  const at = document.activeElement;
  if (!at || at === document.body || at.closest('[data-card="setup"]')) button.focus();
}

async function fill(c, body, card) {
  try {
    const plugin = c.id.startsWith("plugin:");
    const out = plugin ? (pluginCards[c.id] ? await pluginCard(c.id) : empty("Its plug-in is not active."))
      : c.id.startsWith("json:") ? await jsonCard(c.id.slice(5)) : await CARDS[c.id]();
    if (out === null && c.id === "setup" && !editing) { card.remove(); return; }  // everything is set up
    const node = out && !(out instanceof Node) ? out.node : out;
    body.replaceChildren(node || empty("Nothing to show."));
    if (!plugin) bandSide(card.querySelector(".card-band__side"), out?.chip?.[0], out?.chip?.[1], (CARD_BAND[c.id] || (c.id.startsWith("json:") ? JSON_BAND : null))?.time ? (out?.asked || Date.now()) : 0, out?.action);
    if (out?.action && c.id === "setup") focusWalk(out.action);
  } catch (e) {
    body.replaceChildren(empty(e.status === 409 || e.status === 400 ? e.message : "Could not ask."));
  }
}

// Cards with their own time that are due, asked together and drawn in place; the rest of the page is left alone.
let ownBusy = false;
async function ownTick() {
  if (document.hidden || editing || ownBusy) return;
  const now = Date.now();
  const due = [...ownTimes].filter(([id, t]) => now - t.at >= t.every * 1000 - 500 && $(`[data-card="${id}"]`)).map(([id]) => id);
  if (!due.length) return;
  ownBusy = true;
  try {
    const { answers } = await api(`/api/plugins/cards/answers?ids=${encodeURIComponent(due.join(","))}`);
    for (const id of due) {
      const body = $(`[data-card="${id}"] .dash-card__body`);
      if (body && answers[id]) body.replaceChildren(await pluginCard(id, answers[id]));
    }
  } catch { /* asked again at the next tick */ }
  finally { ownBusy = false; }
}

function draw() {
  const grid = $("#dash");
  const list = editing || [{ id: "setup", size: "full" }, ...cardsOf(dash).filter((c) => c.id !== "setup")];
  const drawn = list.map((c, i) => ({ c, ...cardShell(c, i, list) }));
  grid.replaceChildren(...drawn.map((d) => d.card));
  grid.setAttribute("aria-busy", "false");
  drawn.forEach((d) => fill(d.c, d.body, d.card));
  drawEditBar();
}

function drawEditBar() {
  const bar = $("#dash-edit");
  const actions = $("#dash-actions");
  if (!editing) {
    bar.hidden = true;
    actions.replaceChildren(el("button", { type: "button", class: "btn", onclick: startEdit }, icon("pencil"), "Edit dashboard"));
    return;
  }
  actions.replaceChildren();
  const layout = el("select", { class: "select", id: "dash-layout" }, Object.entries(LAYOUTS).map(([k, l]) => el("option", { value: k, text: l.name, selected: k === editing.layout })));
  layout.addEventListener("change", () => { editing.layout = layout.value; editing.splice(0, editing.length, { id: "setup", size: "full" }, ...LAYOUTS[layout.value].cards.map(([id, size]) => ({ id, size }))); draw(); });
  const missing = Object.keys(CARD_TITLES).filter((k) => !editing.some((c) => c.id === k));
  const add = el("select", { class: "select", id: "dash-add" }, el("option", { value: "", text: "Add a card…" }), missing.map((k) => el("option", { value: k, text: CARD_TITLES[k] })));
  add.addEventListener("change", () => { if (add.value) { editing.push({ id: add.value, size: "half" }); draw(); announce(`${CARD_TITLES[add.value]} added at the end`); } });
  const reset = el("button", { type: "button", class: "btn btn--quiet" }, "Back to the layout's own");
  reset.addEventListener("click", () => { editing.splice(0, editing.length, { id: "setup", size: "full" }, ...LAYOUTS[editing.layout].cards.map(([id, size]) => ({ id, size }))); editing.own = true; draw(); });
  const save = el("button", { type: "button", class: "btn btn--primary" }, "Save");
  save.addEventListener("click", async () => {
    const cards = editing.filter((c) => c.id !== "setup").map(({ id, size }) => ({ id, size }));
    const own = JSON.stringify(cards) === JSON.stringify(LAYOUTS[editing.layout].cards.map(([id, size]) => ({ id, size })));
    try {
      const cfg = await api("/api/config/general", { method: "PUT", body: { dashboard: { layout: editing.layout, cards: own ? null : cards } } });
      dash = cfg.dashboard; editing = null; draw();
      // A saved note beside Edit dashboard, which gets focus as Save goes (DASH-309, R5: not a toast).
      const edit = $("#dash-actions button");
      const note = el("span", { class: "saved-note", hidden: true });
      $("#dash-actions").append(note);
      window.SharedComponents.savedNote(note);
      edit?.focus();
      $("#dash-summary").textContent = `${LAYOUTS[dash.layout].name}. Change it with Edit dashboard.`;
    } catch (e) { problem(e.message, save); }
  });
  const cancel = el("button", { type: "button", class: "btn" }, "Cancel");
  cancel.addEventListener("click", () => { editing = null; draw(); });
  bar.hidden = false;
  bar.replaceChildren(el("div", { class: "dash-edit stack-2" },
    el("p", { class: "small", text: "Change the layout, add cards, or size and move each one. Nothing changes until you save." }),
    el("div", { class: "dash-edit__row" },
      el("div", { class: "field" }, el("label", { class: "field__label", for: "dash-layout", text: "Layout" }), layout),
      el("div", { class: "field" }, el("label", { class: "field__label", for: "dash-add", text: "Add a card" }), add)),
    el("div", { class: "actions" }, save, cancel, reset)));
}

function startEdit() {
  editing = [{ id: "setup", size: "full" }, ...cardsOf(dash).filter((c) => c.id !== "setup").map((c) => ({ ...c }))];
  editing.layout = dash.layout;
  draw();
  $("#dash-layout")?.focus();
}

startPage().then(async (session) => {
  if (!session) return;
  try { const cfg = await ask("/api/config"); dash = cfg.dashboard || dash; services = cfg.services || []; } catch { /* the default layout */ }
  try {
    for (const c of (await api("/api/json-cards")).cards) CARD_TITLES[`json:${c.id}`] = c.name;  // nothing is asked of any service
  } catch { /* no custom cards */ }
  try {
    for (const c of (await api("/api/plugins/cards")).cards) { pluginCards[c.id] = c; CARD_TITLES[c.id] = `${c.title} (${c.plugin})`; }
  } catch { /* no plug-in cards */ }
  $("#dash-summary").textContent = `${LAYOUTS[dash.layout]?.name || "At a glance"}. Change it with Edit dashboard.`;
  draw();
  bringInBanner($(".page-head"));  // DASH-455: a copy of media you already have, while it runs
  // Once a minute while the page is in view; nothing while the tab is hidden.
  const tick = () => { if (!document.hidden && !editing) draw(); };
  timer = setInterval(tick, 60000);
  setInterval(() => { ownTick(); if (!document.hidden) ageBandTimes(); }, OWN_FLOOR * 1000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) tick(); });
});
