// Downloads: the queues of every app in one list. Rows are updated in place every 15 seconds (renderKeyed), so
// focus and an open download details slide-out stay put. Updates can be paused.

let items = [];
let byKey = new Map();
let filter = null; // a state word, or null for everything
let sort = "attention";
let grouped = false;
let paused = false;
let timer = null;
let services = new Map(); // app name -> app from /api/config, for "Open in" links
let panel = null;
let panelKey = null;
let checkedAt = null;

const STATE_WORDS = {
  downloading: ["Downloading", "info"], importPending: ["Waiting to import", "neutral"], importing: ["Importing", "info"],
  imported: ["In library", "success"], importBlocked: ["Needs attention", "warning"], failedPending: ["Failed", "danger"], failed: ["Failed", "danger"],
  paused: ["Paused", "muted"], queued: ["Waiting", "neutral"], delay: ["Waiting", "neutral"], completed: ["Downloaded", "success"],
};
// Order of the filter chips, and of "Needs you first".
const STATE_ORDER = ["Needs attention", "Failed", "Downloading", "Importing", "Waiting to import", "Waiting", "Paused", "Downloaded", "In library"];
const SORT_LABEL = { attention: "Needs you first", time: "Time left", title: "Name", queue: "Queue order" };

function words(item) {
  if (item.problem) return ["Needs attention", "warning"];
  return STATE_WORDS[item.status] || [item.status ? item.status[0].toUpperCase() + item.status.slice(1) : "Waiting", "neutral"];
}

// "00:12:00" or "1.02:30:00" (days.hours:minutes:seconds) from the apps, as seconds.
function secondsLeft(text) {
  const m = /^(?:(\d+)\.)?(\d+):(\d+):(\d+)$/.exec(text || "");
  if (!m) return Infinity;
  return (Number(m[1] || 0) * 86400) + Number(m[2]) * 3600 + Number(m[3]) * 60 + Number(m[4]);
}

function timeLeftWords(text) {
  const s = secondsLeft(text);
  if (!Number.isFinite(s)) return "";
  if (s < 60) return "less than a minute left";
  const plural = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  if (d) return `${plural(d, "day")} ${plural(h, "hour")} left`;
  if (h) return `${plural(h, "hour")} ${plural(m, "minute")} left`;
  return `${plural(m, "minute")} left`;
}

function percent(item) { return Math.round(item.progress || 0); }

function notice(tone, title, text, iconName = tone === "danger" ? "circle-x" : tone === "warning" ? "triangle-alert" : "info") {
  return el("div", { class: "notice", "data-tone": tone, role: "status" }, icon(iconName),
    el("div", { class: "notice__body" }, title ? el("span", { class: "notice__title", text: title }) : null, text ? el("p", { text }) : null));
}

function newBar() {
  return el("div", { class: "progress", role: "progressbar", "aria-valuemin": "0", "aria-valuemax": "100" }, el("span"));
}

function setProgress(bar, item, label) {
  const tone = words(item)[1];
  const pct = percent(item);
  if (tone === "warning" || tone === "danger") bar.dataset.tone = tone; else delete bar.dataset.tone;
  bar.setAttribute("aria-valuenow", String(pct));
  bar.setAttribute("aria-label", label);
  bar.firstChild.style.width = `${pct}%`;
  return bar;
}

// Rows ---------------------------------------------------------------------

function buildRow() {
  const button = el("button", { type: "button" });
  button.addEventListener("click", () => openDetails(button.closest("[data-key]").dataset.key, button));
  const meta = el("div", { class: "row__meta" });
  const reason = el("div", { class: "row__meta dl-reason" });
  const pct = el("span", { class: "numeric" });
  const side = el("div", { class: "row__side" }, pct);
  const bar = newBar();
  const li = el("li", { class: "row row--opens row--no-lead" },
    el("div", {}, el("div", { class: "row__title" }, button), meta, reason), side, bar);
  li.parts = { button, meta, reason, pct, side, bar, chip: null };
  return li;
}

function renderRow(item, old) {
  const li = old || buildRow();
  const p = li.parts;
  const [label, tone] = words(item);
  if (p.button.textContent !== item.title) p.button.textContent = item.title;
  p.meta.textContent = [grouped ? "" : item.service_name, item.client, formatBytes(item.size), timeLeftWords(item.time_left)].filter(Boolean).join(" · ");
  p.reason.textContent = item.problem && item.messages.length ? item.messages[0] : "";
  p.reason.hidden = !p.reason.textContent;
  p.pct.textContent = `${percent(item)}%`;
  const next = chip(label, tone);
  if (p.chip) p.chip.replaceWith(next); else p.side.append(next);
  p.chip = next;
  setProgress(p.bar, item, `${item.title}, ${percent(item)}% downloaded`);
  return li;
}

function sorted(list) {
  const rank = (i) => { const r = STATE_ORDER.indexOf(words(i)[0]); return r < 0 ? STATE_ORDER.length : r; };
  const by = {
    attention: (a, b) => rank(a) - rank(b) || b.progress - a.progress || a.order - b.order,
    time: (a, b) => secondsLeft(a.time_left) - secondsLeft(b.time_left) || rank(a) - rank(b) || a.order - b.order,
    title: (a, b) => a.title.localeCompare(b.title, "en-GB"),
    queue: (a, b) => a.order - b.order,
  }[sort];
  return [...list].sort(by);
}

function buildGroup(name) {
  const list = el("ul", { class: "rows" });
  if (!name) {
    list.setAttribute("aria-label", "Queue");
    return el("section", { class: "media-section" }, list);
  }
  const id = `app-${name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
  list.setAttribute("aria-labelledby", id);
  return el("section", { class: "media-section", "aria-labelledby": id }, el("h2", { class: "group-heading", id, text: name }), list);
}

function renderRows() {
  const shown = sorted(items.filter((i) => !filter || words(i)[0] === filter));
  let groups;
  if (grouped) {
    const names = [...new Set(shown.map((i) => i.service_name))].sort((a, b) => a.localeCompare(b, "en-GB"));
    groups = names.map((name) => ({ name, rows: shown.filter((i) => i.service_name === name) }));
  } else {
    groups = [{ name: "", rows: shown }];
  }
  const box = $("#queue");
  // Switching between one list and one list per app starts the sections again.
  if (box.dataset.grouped !== String(grouped)) { box.replaceChildren(); box.dataset.grouped = String(grouped); }
  renderKeyed(box, groups, (g) => `group:${g.name}`, (g, old) => {
    const section = old || buildGroup(g.name);
    renderKeyed($("ul", section), g.rows, (i) => i.key, renderRow);
    return section;
  });
  let empty = $("#queue-empty");
  if (!shown.length) {
    const text = items.length ? `Nothing in the queue is "${filter}" right now.` : "Nothing is downloading. New downloads from your apps appear here.";
    if (!empty) { empty = el("p", { id: "queue-empty", class: "empty" }); box.after(empty); }
    empty.textContent = text;
  } else {
    empty?.remove();
  }
  $("#queue-count").textContent = filter
    ? `${shown.length} of ${items.length} downloads`
    : `${items.length} ${items.length === 1 ? "download" : "downloads"}`;
}

function renderFilters() {
  const counts = new Map();
  for (const i of items) { const w = words(i)[0]; counts.set(w, (counts.get(w) || 0) + 1); }
  const rank = (n) => { const r = STATE_ORDER.indexOf(n); return r < 0 ? 99 : r; };
  const names = [...counts.keys()].sort((a, b) => rank(a) - rank(b));
  if (filter && !counts.has(filter)) names.push(filter); // keep the chosen chip (and focus on it) at 0
  renderKeyed($("#queue-filters"), names, (n) => n, (name, old) => {
    const button = old || el("button", { type: "button", class: "filter-chip", onclick: () => {
      filter = filter === name ? null : name;
      renderFilters();
      renderRows();
    } });
    button.textContent = `${name}, ${counts.get(name) || 0}`;
    button.setAttribute("aria-pressed", String(filter === name));
    return button;
  });
}

function renderSummary() {
  const active = items.filter((i) => words(i)[0] === "Downloading").length;
  const attention = items.filter((i) => i.problem).length;
  const parts = [`${items.length} in the queue`, `${active} downloading`];
  if (attention) parts.push(`${attention} ${attention === 1 ? "needs" : "need"} attention`);
  if (checkedAt) parts.push(`checked at ${checkedAt.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}`);
  if (paused) parts.push("updates paused");
  $("#queue-summary").textContent = parts.join(" · ");
}

// Download details slide-out -------------------------------------------

function appLink(item) {
  const app = services.get(item.service_name);
  return app?.link ? `${reachableUrl(app.link)}/activity/queue` : "";
}

function detailsBody(item) {
  const [label, tone] = words(item);
  const pct = percent(item);
  const done = item.size ? formatBytes(item.size * (item.progress || 0) / 100) : "";
  const body = [
    el("div", { class: "meter" },
      el("div", { class: "meter__label" }, el("span", {}, chip(label, tone)),
        el("span", { class: "numeric", text: item.size ? `${done} of ${formatBytes(item.size)} (${pct}%)` : `${pct}%` })),
      setProgress(newBar(), item, `${pct}% downloaded`)),
  ];
  if (item.problem) {
    body.push(notice("warning", `${item.service_name} needs you to look at this`, item.messages.length
      ? `Read the messages below, then sort it out in the queue in ${item.service_name}.`
      : `${item.service_name} flagged this download without a message. Open the queue in ${item.service_name} to see why.`));
  }
  if (item.messages.length) {
    body.push(el("section", { class: "media-panel-section", "aria-labelledby": "dd-msg-h" },
      el("h3", { id: "dd-msg-h", text: `Messages from ${item.service_name}` }),
      el("ul", { class: "rows" }, item.messages.map((m) => el("li", { class: "row row--no-lead" }, el("div", { class: "row__title", text: m }))))));
  }
  const facts = [["App", item.service_name], ["Download client", item.client], ["State", label], ["Size", item.size ? formatBytes(item.size) : ""],
    ["Time left", timeLeftWords(item.time_left)], ["Release", item.title]].filter(([, v]) => v);
  body.push(el("dl", { class: "facts" }, facts.flatMap(([k, v]) => [el("dt", { text: k }), el("dd", { text: v })])));
  return body;
}

function detailsFoot(item) {
  const href = appLink(item);
  if (!href) return [];
  return [el("a", { class: "btn btn--primary", href, target: "_blank", rel: "noopener noreferrer" }, icon("external-link"),
    `Open the queue in ${item.service_name}`, el("span", { class: "visually-hidden", text: " (opens in a new tab)" }))];
}

function openDetails(key, opener) {
  const item = byKey.get(key);
  if (!item) return;
  panelKey = key;
  panel = sidePanel({
    title: item.title, body: detailsBody(item), foot: detailsFoot(item), opener,
    onClose: () => { panel = null; panelKey = null; },
  });
}

function refreshDetails() {
  if (!panel || !panelKey) return;
  const item = byKey.get(panelKey);
  if (item) {
    panel.body.replaceChildren(...detailsBody(item));
  } else {
    panel.body.replaceChildren(notice("info", "This download has left the queue",
      "The app may have imported it, or it was removed. Close this panel to go back to the queue."));
    panel.setFoot([]);
  }
}

// Loading ------------------------------------------------------------------

async function load({ announceIt = false } = {}) {
  try {
    const data = await api("/api/queue");
    const seen = new Map();
    items = data.items.map((i, order) => {
      const base = `${i.service_name}|${i.client}|${i.title}`;
      const n = (seen.get(base) || 0) + 1;
      seen.set(base, n);
      return { ...i, messages: i.messages || [], order, key: n > 1 ? `${base}#${n}` : base };
    });
    byKey = new Map(items.map((i) => [i.key, i]));
    checkedAt = new Date();
    renderSummary();
    $("#queue-errors").replaceChildren(...data.errors.map((e) => notice("warning", "", e.message)));
    renderFilters();
    renderRows();
    refreshDetails();
    if (announceIt) announce(`Queue checked: ${items.length} ${items.length === 1 ? "download" : "downloads"}`);
  } catch (e) {
    $("#queue-summary").textContent = e.message;
    if (announceIt) announce(e.message);
  }
}

// Download hours ---------------------------------------------------------------

const hourText = (h) => `${String(h).padStart(2, "0")}:00`;

function whenText(iso) {
  const d = new Date(iso);
  const time = d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  return d.toDateString() === new Date().toDateString() ? time : `${time} tomorrow`;
}

function renderSchedule(s) {
  const box = $("#schedule");
  box.hidden = !s.enabled && !s.clients.length;
  if (box.hidden) return;
  const hours = `${hourText(s.start)} to ${hourText(s.end)}`;
  const settings = el("a", { href: "/settings-general.html#download-hours", text: "Settings, General" });
  box.dataset.tone = !s.enabled ? "neutral" : s.mode === "run" ? "success" : "warning";
  if (!s.enabled) {
    $("#schedule-chip").replaceChildren(chip("Off", "muted"));
    $("#schedule-text").replaceChildren(`Downloads run at any time. To download only at night, turn on download hours in `, settings, ".");
    $("#schedule-actions").replaceChildren();
    return;
  }
  const running = s.mode === "run";
  $("#schedule-chip").replaceChildren(chip(running ? "Downloading" : "Paused", running ? "success" : "warning"));
  const text = running
    ? (s.reason === "manual" ? `Resumed by you. Back to the hours at ${whenText(s.next_change)}.` : `Inside the hours (${hours}). Pauses at ${whenText(s.next_change)}.`)
    : (s.reason === "manual" ? `Paused by you. Resumes at ${whenText(s.next_change)}.` : `Downloads run ${hours}. Next start ${whenText(s.next_change)}.`);
  $("#schedule-text").replaceChildren(text, s.clients.length ? "" : " No qBittorrent or SABnzbd with an API key is set up yet.");
  const button = (label, iconName, action, primary) => el("button", { type: "button", class: primary ? "btn btn--primary" : "btn", onclick: (e) => scheduleAct(action, e.currentTarget) }, icon(iconName), label);
  $("#schedule-actions").replaceChildren(
    running ? null : button("Resume downloads now", "play", "resume", true),
    running ? button(`Pause downloads until ${hourText(s.start)}`, "pause", "pause") : null,
    s.reason === "manual" ? button("Follow the hours", "clock", "follow") : null);
}

async function loadSchedule() {
  try { renderSchedule(await api("/api/schedule")); } catch { /* the queue works without it */ }
}

async function scheduleAct(action, button) {
  button.disabled = true;
  try {
    const s = await api("/api/schedule", { method: "POST", body: { action } });
    renderSchedule(s);
    const done = { resume: "Downloads resumed", pause: "Downloads paused", follow: "Following the download hours" }[action];
    toast(s.errors?.length ? `${done}, with problems: ${s.errors.join("; ")}` : done);
    $("#schedule-actions .btn")?.focus();
  } catch (e) {
    toast(e.message);
    button.disabled = false;
  }
}

function setPaused(on) {
  paused = on;
  clearInterval(timer);
  timer = on ? null : setInterval(() => { load(); loadSchedule(); }, 15000);
  $("#auto-refresh").setAttribute("aria-pressed", String(on));
  renderSummary();
}

startPage().then(async () => {
  $("#refresh").addEventListener("click", () => load({ announceIt: true }));
  $("#auto-refresh").addEventListener("click", () => {
    setPaused(!paused);
    announce(paused ? "Updates paused" : "Updates resumed, every 15 seconds");
  });
  $("#group-by-app").addEventListener("click", (e) => {
    grouped = !grouped;
    e.currentTarget.setAttribute("aria-pressed", String(grouped));
    renderRows();
  });
  SharedComponents.setup($("#sort-wrap"));
  $("#sort-menu").addEventListener("click", (e) => {
    const item = e.target.closest("[data-sort]");
    if (!item) return;
    sort = item.dataset.sort;
    $("#sort-label").textContent = `Sort: ${SORT_LABEL[sort]}`;
    renderRows();
  });
  try {
    const cfg = await api("/api/config");
    services = new Map(cfg.services.map((s) => [s.name, s]));
  } catch { /* links to the apps are an extra; the queue works without them */ }
  await Promise.all([load(), loadSchedule()]);
  setPaused(false);
});
