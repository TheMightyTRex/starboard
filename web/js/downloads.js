// Downloads: the queues of every app in one list. Rows are updated in place every few seconds (renderKeyed), so
// focus and an open download details slide-out stay put. Updates can be paused.

let items = [];
let byKey = new Map();
let filter = null; // a state word, or null for everything
let sort = "attention";
let grouped = false;
let paused = false;
let every = 15; // seconds between updates; Settings, Performance (0: only when you press Check again)
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
  // An app's own state word, such as post_processing, as words: "Post processing" (issue #7).
  const plain = (item.status || "").replace(/[_-]+/g, " ").trim().toLowerCase();
  return STATE_WORDS[item.status] || [plain ? plain[0].toUpperCase() + plain.slice(1) : "Waiting", "neutral"];
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
  if (p.chip) p.chip.replaceWith(next); else p.side.prepend(next); // the state first in row__side, then the percentage (R1)
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

// One state at a time (DASH-309, R4): a segmented control, All first. The poll only changes the counts in place;
// the control is drawn again only when the states change, and focus stays on the chosen one (same ids).
let filterKeys = "";
function renderFilters() {
  const counts = new Map();
  for (const i of items) { const w = words(i)[0]; counts.set(w, (counts.get(w) || 0) + 1); }
  const rank = (n) => { const r = STATE_ORDER.indexOf(n); return r < 0 ? 99 : r; };
  const names = [...counts.keys()].sort((a, b) => rank(a) - rank(b));
  if (filter && !counts.has(filter)) names.push(filter); // keep the chosen one (and focus on it) at 0
  const box = $("#queue-filters");
  box.removeAttribute("role");
  box.removeAttribute("aria-label");
  const options = [["", "All", items.length], ...names.map((n) => [n, n, counts.get(n) || 0])];
  const keys = names.join("|");
  if (keys === filterKeys && box.firstElementChild) {
    options.forEach(([v, w, n], at) => { const span = box.querySelectorAll(".segmented label span")[at]; if (span) span.textContent = `${w} ${n.toLocaleString("en-GB")}`; });
    return;
  }
  filterKeys = keys;
  box.hidden = !names.length;
  box.replaceChildren(names.length ? segmentedFilter({ name: "queue-show", label: "Show only", value: filter || "", options,
    onChange: (v) => { filter = v || null; renderFilters(); renderRows(); } }) : "");
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
  const added = item.added ? new Date(item.added).toLocaleString("en-GB", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "";
  const facts = [["App", item.service_name], ["Download client", item.client], ["State", label], ["Size", item.size ? formatBytes(item.size) : ""],
    ["Time left", timeLeftWords(item.time_left)], ["Added", added], ["Release", item.title]].filter(([, v]) => v);
  body.push(el("dl", { class: "facts" }, facts.flatMap(([k, v]) => [el("dt", { text: k }), el("dd", { text: v })])));
  return body;
}

function detailsFoot(item) {
  const href = appLink(item);
  const out = href ? [el("a", { class: "btn btn--primary", href, target: "_blank", rel: "noopener noreferrer" }, icon("external-link"),
    `Open the queue in ${item.service_name}`, el("span", { class: "visually-hidden", text: " (opens in a new tab)" }))] : [];
  if (item.id == null || !item.service) return out;
  const another = el("button", { type: "button", class: "btn" }, icon("search"), "Find another");
  another.addEventListener("click", () => queueAction(item, "block-search", {
    title: "Block this release and find another?",
    message: `${item.service_name} removes it from ${item.client || "the download client"}, never downloads this release again, and searches for another now.`,
    confirm: "Block and search",
  }));
  const remove = el("button", { type: "button", class: "btn btn--danger" }, icon("trash-2"), "Remove");
  remove.addEventListener("click", () => {
    const block = el("input", { type: "checkbox" });
    queueAction(item, () => (block.checked ? "block" : "remove"), {
      title: "Remove this download?",
      message: `${item.service_name} removes it from the queue and from ${item.client || "the download client"}, with what it has downloaded so far.`,
      fields: [el("label", { class: "check" }, block, el("span", { class: "check__text" }, el("strong", { text: "Block this release" }),
        el("span", { class: "check__hint", text: `So ${item.service_name} does not download it again.` })))],
      confirm: "Remove download", danger: true,
    });
  });
  // DASH-205: a Reelix download stuck at import: try the import again, or ignore it (the files stay where they are).
  const stuck = item.reelix && ["importPending", "importBlocked", "failedPending"].includes(item.status);
  const fix = stuck ? [
    el("button", { type: "button", class: "btn btn--primary", onclick: () => queueAction(item, "import", {
      title: "Try the import again?", message: `Reelix looks at the finished files again and moves them into your library if it can. Read its messages first if it failed before.`,
      confirm: "Try again" }) }, icon("refresh-cw"), "Try the import again"),
    el("button", { type: "button", class: "btn", onclick: () => queueAction(item, "ignore", {
      title: "Ignore this download?", message: `Reelix stops warning about it and leaves the files in ${item.client || "the download client"}'s folder. Nothing is deleted.`,
      confirm: "Ignore" }) }, icon("eye-off"), "Ignore"),
  ] : [];
  // Choose the episode (12 November 2026): a file Reelix refused because its episode number is not one of the
  // series' (broadcast or TVDB numbering against TMDB's).
  const numbering = item.reelix && item.download_id && item.messages.some((m) => /not part of the series/i.test(m));
  const choose = numbering ? [el("button", { type: "button", class: "btn btn--primary", onclick: () => chooseEpisode(item) }, icon("list-checks"), "Choose the episode")] : [];
  // One primary button in view (DASH-309, R9): the first, the thing to do now; the others are plain.
  const all = [...choose, ...fix, ...out, another, remove];
  all.filter((b) => b.classList.contains("btn--primary")).slice(1).forEach((b) => b.classList.remove("btn--primary"));
  return all;
}

async function chooseEpisode(item) {
  const panel = sidePanel({ title: "Choose the episode", wide: true, body: [el("p", { class: "muted", text: "Asking Reelix…" })] });
  let o;
  try { o = await api(`/api/queue/episodes?download_id=${encodeURIComponent(item.download_id)}`); }
  catch (e) { panel.body.replaceChildren(notice("danger", "Reelix could not be asked", e.message)); return; }
  const byId = Object.fromEntries(o.episodes.map((e) => [e.id, e]));
  const label = (e) => `${e.season === 0 ? "Special" : `S${String(e.season).padStart(2, "0")}E${String(e.number).padStart(2, "0")}`} · ${e.title}${e.have ? " · in your library" : ""}`;
  const seasons = [...new Set(o.episodes.map((e) => e.season))];
  const picks = o.files.map((f, n) => {
    const select = el("select", { class: "select", id: `ep-pick-${n}` },
      el("option", { value: "", text: "Leave this file out" }),
      seasons.map((s) => el("optgroup", { label: s === 0 ? "Specials" : `Season ${s}` },
        o.episodes.filter((e) => e.season === s).map((e) => el("option", { value: e.id, text: label(e), selected: e.id === f.guess })))));
    const note = el("p", { class: "small", role: "status" });
    const say = () => {
      const e = byId[select.value];
      note.textContent = !e ? "" : e.have ? "You already have this episode: importing replaces your copy if this one is better. If it is the same episode, remove the download instead." : "Not in your library yet.";
    };
    select.addEventListener("change", say);
    say();
    return { f, select, node: el("div", { class: "stack-2 media-panel-section" },
      titleChip(el("h3", { class: "small", text: f.name }), chip(f.sure ? "Sure" : "Check this", f.sure ? "success" : "warning")),
      el("label", { class: "field__label", for: select.id, text: "Its episode" }), select, note) };
  });
  const go = el("button", { type: "button", class: "btn btn--primary" }, icon("download"), "Import");
  go.addEventListener("click", async () => {
    const choices = picks.filter((p) => p.select.value).map((p) => ({ path: p.f.path, episode_ids: [Number(p.select.value)] }));
    if (!choices.length) { problem("Choose an episode for at least one file", go); return; }
    go.disabled = true;
    try { await api(`/api/queue/episodes?download_id=${encodeURIComponent(item.download_id)}`, { method: "POST", body: { choices } });
      toast("Reelix is importing it"); panel.close(); load({ announceIt: true }); }
    catch (e) { problem(e.message, go); go.disabled = false; }
  });
  panel.body.replaceChildren(
    el("p", { text: `Reelix numbers ${o.series.title}'s episodes as TMDB does, and this download uses another numbering, so Reelix could not tell which episode it is. Check the guess, then import it, or close this and remove the download if you already have the episode.` }),
    ...picks.map((p) => p.node));
  panel.setFoot([go, el("button", { type: "button", class: "btn", "data-closes": true, text: "Cancel" })]);
}

async function queueAction(item, action, dialog) {
  if (!(await confirmDialog(dialog))) return;
  const chosen = typeof action === "function" ? action() : action;
  try {
    await api("/api/queue/action", { method: "POST", body: { service: item.service, id: item.id, action: chosen } });
    toast({ remove: "Removed", block: "Removed and blocked", "block-search": "Blocked. Searching for another",
      import: "Reelix is trying the import again", ignore: "Ignored" }[chosen]);
    load({ announceIt: true });
  } catch (e) { problem(`Not done: ${e.message}`); }
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
    const data = await api(announceIt ? "/api/queue?fresh=1" : "/api/queue");
    const seen = new Map();
    items = data.items.map((i, order) => {
      const base = i.id != null ? `${i.service}|${i.id}` : `${i.service_name}|${i.client}|${i.title}`;
      const n = (seen.get(base) || 0) + 1;
      seen.set(base, n);
      return { ...i, messages: i.messages || [], order, key: n > 1 ? `${base}#${n}` : base };
    });
    byKey = new Map(items.map((i) => [i.key, i]));
    checkedAt = new Date();
    renderSummary();
    // One notice with a title (R5); two in one place become one.
    const n = data.errors.length;
    $("#queue-errors").replaceChildren(...(n ? [notice("warning", n === 1 ? "A download app did not answer" : `${n} download apps did not answer`,
      `${data.errors.map((e) => e.message.replace(/\.?$/, ".")).join(" ")} What ${n === 1 ? "it is" : "they are"} downloading is missing from this list until ${n === 1 ? "it answers" : "they answer"}.`)] : []));
    renderFilters();
    renderRows();
    refreshDetails();
    if (announceIt) announce(`Queue checked: ${items.length} ${items.length === 1 ? "download" : "downloads"}`);
  } catch (e) {
    $("#queue-summary").textContent = e.message;
    if (announceIt) announce(e.message);
  }
}

// Held downloads (DASH-210): releases Reelix found but a delay profile is holding back, in case a better one comes.
// Asked when the page opens, with Check again and when the tab is shown again; not on the queue's timer, as the
// list changes only when a delay ends (lightweight rule). Get it now sends one to the download app; Remove drops it.

function heldWhen(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const time = d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  const days = Math.round((new Date(d.toDateString()) - new Date(new Date().toDateString())) / 86400000);
  if (d <= new Date()) return "Goes at the next check";
  return days === 0 ? `Goes at ${time}` : days === 1 ? `Goes at ${time} tomorrow` : `Goes on ${d.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" })} at ${time}`;
}

function heldRow(h, old) {
  if (old) return old;
  const get = el("button", { type: "button", class: "btn" }, icon("download"), "Get it now",
    el("span", { class: "visually-hidden", text: `: ${h.what || h.release}` }));
  get.addEventListener("click", () => heldAct(h, "grab", get));
  const remove = el("button", { type: "button", class: "btn" }, icon("trash-2"), "Remove",
    el("span", { class: "visually-hidden", text: `: ${h.what || h.release}` }));
  remove.addEventListener("click", () => heldAct(h, "remove", remove));
  // The state first in row__side, then the row's two buttons (DESIGN-SYSTEM section 10).
  return el("li", { class: "row row--no-lead" },
    el("div", {}, el("div", { class: "row__title", text: h.what || h.release }),
      el("div", { class: "row__meta", text: [h.what ? h.release : "", h.quality, h.site].filter(Boolean).join(" · ") }),
      el("div", { class: "row__meta", text: [h.reason, heldWhen(h.release_at)].filter(Boolean).join(" · ") })),
    el("div", { class: "row__side" }, chip("Held", "neutral"), get, remove));
}

let heldShown = false;
async function loadHeld() {
  let d;
  try { d = await api("/api/held"); } catch { return; }
  const box = $("#held-section");
  // Shown once there is something held; it stays (saying nothing is held) after the last one goes, so focus has
  // somewhere to land.
  heldShown = heldShown || (d.available && d.items.length > 0);
  box.hidden = !heldShown;
  if (!heldShown) return;
  const n = d.items.length;
  $("#held-summary").textContent = n
    ? `${n} ${n === 1 ? "release is" : "releases are"} held back by a delay profile, in case a better one comes. Each goes to the download app by itself at the time shown.`
    : "Nothing is held back now.";
  renderKeyed($("#held"), d.items, (h) => h.id, heldRow);
}

async function heldAct(h, action, button) {
  if (action === "remove" && !(await confirmDialog({ title: "Remove this held download?",
    message: `Reelix forgets ${h.release}. Nothing is downloaded, and Reelix may find it again at its next search.`, confirm: "Remove", danger: true }))) return;
  const rows = $$("#held > li");
  const at = rows.findIndex((r) => r.dataset.key === String(h.id));
  button.disabled = true;
  try {
    const out = await api(action === "grab" ? `/api/held/${h.id}/grab` : `/api/held/${h.id}`, { method: action === "grab" ? "POST" : "DELETE" });
    await loadHeld();
    // Focus goes to the same place in the list (the next row's first button), or to the heading when it is empty.
    const left = $$("#held > li");
    const to = left.length ? $("button", left[Math.min(at, left.length - 1)]) : $("#held-h");
    to?.focus();
    if (action === "grab") {
      toast(`${out.said}. It shows in the queue once the download app has it`);
      load();
    } else announce(`Removed. ${left.length ? `${left.length} still held` : "Nothing is held back now"}.`);
  } catch (e) {
    button.disabled = false;
    problem(e.message, button);
  }
}

// Speeds and the VPN: one tile per download client and per Gluetun, refreshed with the queue.

function stat(value, label, tone, words) {
  return el("div", { class: "stat", "data-tone": tone || null },
    el("span", { class: "stat__value num", text: value }),
    el("span", { class: "stat__label" }, label, words ? el("span", { class: "small" }, " · ", chip(words, tone)) : null));
}

async function loadTransfer(fresh = false) {
  let t;
  try { t = await api(fresh ? "/api/transfer?fresh=1" : "/api/transfer"); } catch { return; }
  const tiles = [];
  for (const c of t.clients) {
    if (c.kind === "torrent") tiles.push(stat(c.down_text, `${c.name}: downloading, sending ${c.up_text}`));
    else tiles.push(stat(c.paused ? "Paused" : c.down_text, `${c.name}${c.count ? `: ${c.count} in the queue, ${c.left} left` : ""}`, c.paused ? "warning" : null));
  }
  for (const v of t.vpn) {
    const where = [v.city, v.country].filter(Boolean).join(", ");
    tiles.push(stat(v.running ? "Connected" : "Not connected",
      `${v.name}${where ? `: ${where}` : ""}${v.port ? `, forwarded port ${v.port}` : v.running ? ", no forwarded port" : ""}`,
      v.running ? "success" : "danger", v.running ? null : "Downloads may stop"));
  }
  for (const e of t.errors) tiles.push(stat("Not answering", e.message, "danger"));
  $("#transfer").hidden = !tiles.length;
  $("#transfer").replaceChildren(...tiles);
  // DASH-304: NZBGet's unpacking paused, so finished downloads wait and nothing reaches the library.
  const held = t.clients.filter((c) => c.post_paused);
  $("#unpack-paused")?.remove();
  if (held.length) {
    const c = held[0];
    const go = el("button", { type: "button", class: "btn" }, icon("play"), "Resume unpacking");
    go.addEventListener("click", async () => {
      go.disabled = true;
      try { toast((await api(`/api/transfer/${c.id}/resume-unpacking`, { method: "POST" })).said); loadTransfer(true); }
      catch (err) { problem(err.message, go); go.disabled = false; }
    });
    $("#transfer").before(el("div", { id: "unpack-paused", class: "notice", "data-tone": "warning", role: "status" }, icon("triangle-alert"),
      el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: `${c.name} is not unpacking` }),
        el("p", { text: `Its unpacking is paused, so ${c.waiting_unpack ? `${c.waiting_unpack} finished ${c.waiting_unpack === 1 ? "download waits" : "downloads wait"}` : "finished downloads wait"} and nothing new reaches your library. Downloading follows your download hours as before.` })),
      go));
  }
}

// Finished this week: the newest imports from each app's history. Loaded once when the page opens.

async function loadRecent() {
  try {
    const data = await api("/api/recent");
    const box = $("#recent-section");
    box.hidden = false;
    const byApp = {};
    for (const r of data.items) byApp[r.service_name] = (byApp[r.service_name] || 0) + 1;
    $("#recent-summary").textContent = data.items.length
      ? `The newest ${data.items.length}: ${Object.entries(byApp).map(([a, n]) => `${n} from ${a}`).join(", ")}.`
      : "Nothing finished in the last 7 days.";
    $("#recent").replaceChildren(...data.items.map((r) => el("li", { class: "row row--no-lead" },
      el("div", {}, el("div", { class: "row__title", text: r.title }),
        el("div", { class: "row__meta", text: [r.detail, r.quality, r.service_name].filter(Boolean).join(" · ") })),
      el("div", { class: "row__side small muted", text: new Date(r.when).toLocaleString("en-GB", { weekday: "short", hour: "2-digit", minute: "2-digit" }) }))));
  } catch { /* the queue works without it */ }
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
    $("#schedule-text").replaceChildren(`Downloads run at any time. To download only at night, activate download hours in `, settings, ".");
    $("#schedule-actions").replaceChildren();
    return;
  }
  const running = s.mode === "run";
  $("#schedule-chip").replaceChildren(chip(running ? "Downloading" : "Paused", running ? "success" : "warning"));
  const text = running
    ? (s.reason === "manual" ? `Resumed by you. Back to the hours at ${whenText(s.next_change)}.` : `Inside the hours (${hours}). Pauses at ${whenText(s.next_change)}.`)
    : (s.reason === "manual" ? `Paused by you. Resumes at ${whenText(s.next_change)}.` : `Downloads run ${hours}. Next start ${whenText(s.next_change)}.`);
  // DASH-171: what downloads now, outside the hours, and why.
  const now = !running && s.now?.length ? ` Downloading now, outside the hours, because you chose Download now: ${s.now.map((n) => n.title || "one item").join(", ")}.` : "";
  $("#schedule-text").replaceChildren(text + now, s.clients.length ? "" : " No qBittorrent, NZBGet or SABnzbd with an API key is set up yet.");
  const button = (label, iconName, action, primary) => el("button", { type: "button", class: primary ? "btn btn--primary" : "btn", onclick: (e) => scheduleAct(action, e.currentTarget) }, icon(iconName), label);
  $("#schedule-actions").replaceChildren(...[
    running ? null : button("Resume downloads now", "play", "resume", true),
    running ? button(`Pause downloads until ${hourText(s.start)}`, "pause", "pause") : null,
    s.reason === "manual" ? button("Follow the hours", "clock", "follow") : null].filter(Boolean));
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
    (s.errors?.length ? problem : toast)(s.errors?.length ? `${done}, with problems: ${s.errors.join("; ")}` : done);
    $("#schedule-actions .btn")?.focus();
  } catch (e) {
    problem(e.message);
    button.disabled = false;
  }
}

function setPaused(on) {
  paused = on;
  clearInterval(timer);
  // Every few seconds (Settings, Performance) while the tab is in view; a hidden tab asks nothing and catches up
  // when shown again.
  timer = on || !every ? null : setInterval(() => { if (!document.hidden) { load(); loadSchedule(); loadTransfer(); } }, every * 1000);
  $("#auto-refresh").setAttribute("aria-pressed", String(on));
  renderSummary();
}

startPage().then(async () => {
  $("#refresh").addEventListener("click", () => { load({ announceIt: true }); loadTransfer(true); loadHeld(); });
  $("#auto-refresh").addEventListener("click", () => {
    setPaused(!paused);
    announce(paused ? "Updates paused" : every ? `Updates resumed, every ${every} seconds` : "Updates only when you press Check again");
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
    every = cfg.performance?.downloads_refresh ?? 15;
  } catch { /* links to the apps are an extra; the queue works without them */ }
  await Promise.all([load(), loadSchedule(), loadTransfer()]);
  loadHeld();
  loadRecent();
  setPaused(false);
  document.addEventListener("visibilitychange", () => { if (!document.hidden && !paused) { load(); loadSchedule(); loadTransfer(); loadHeld(); } });
});
