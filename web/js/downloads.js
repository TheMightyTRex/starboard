// Downloads: the queues of every app in one list. Rows are updated in place every few seconds (renderKeyed), so
// focus and an open download details slide-out stay put. Updates can be paused.

let items = [];
let byKey = new Map();
let filter = null; // a state word, or null for everything
let sort = "attention";
let grouped = false;
let paused = false;
let every = 15; // seconds between updates; Settings, General, Performance (0: only when you press Check again)
let timer = null;
let services = new Map(); // app name -> app from /api/config, for "Open in" links
let panel = null;
let panelKey = null;
let checkedAt = null;
let attention = null; // the open slide-out of a download that needs attention (DASH-496): { key, data, done }
let panelOpener = null; // the download's name that opened it, for focus to go back to
let unpackTimer = null;
let chosen = new Set(); // keys of the downloads ticked for a bulk action (owner, 21 November 2026)
let lastPicked = null; // the key last ticked or cleared, for Shift and click to tick a run of rows
let bulkRunning = false;

const STATE_WORDS = {
  downloading: STATUS.downloading, importPending: STATUS.waitingToImport, importing: STATUS.importing,
  imported: STATUS.inLibrary, importBlocked: STATUS.needsAttention, failedPending: STATUS.failed, failed: STATUS.failed,
  paused: STATUS.paused, queued: STATUS.waiting, delay: STATUS.waiting, completed: STATUS.downloaded,
};
// Order of the filter chips, and of "Needs you first".
const STATE_ORDER = ["Needs attention", "Failed", "Downloading", "Importing", "Waiting to import", "Waiting", "Paused", "Downloaded", "In library"];
const SORT_LABEL = { attention: "Needs you first", time: "Time left", title: "Name", queue: "Queue order" };

function words(item) {
  if (item.problem) return STATUS.needsAttention;
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
  const pick = el("input", { type: "checkbox", class: "dl-pick__box" });
  pick.addEventListener("click", (e) => pickRow(pick.closest("[data-key]").dataset.key, pick.checked, e.shiftKey));
  const button = el("button", { type: "button" });
  button.addEventListener("click", () => openDetails(button.closest("[data-key]").dataset.key, button));
  const meta = el("div", { class: "row__meta" });
  const reason = el("div", { class: "row__meta dl-reason" });
  const pct = el("span", { class: "numeric" });
  const side = el("div", { class: "row__side" }, pct);
  const bar = newBar();
  const li = el("li", { class: "row row--opens dl-row" }, el("label", { class: "dl-pick" }, pick),
    el("div", {}, el("div", { class: "row__title" }, button), meta, reason), side, bar);
  li.parts = { pick, button, meta, reason, pct, side, bar, chip: null };
  return li;
}

function renderRow(item, old) {
  const li = old || buildRow();
  const p = li.parts;
  const [label, tone] = words(item);
  if (p.button.textContent !== item.title) p.button.textContent = item.title;
  const can = canAct(item);
  p.pick.disabled = !can || bulkRunning;
  p.pick.parentElement.classList.toggle("dl-pick--none", !can);
  p.pick.checked = chosen.has(item.key);
  p.pick.setAttribute("aria-label", `Select ${item.title}`);
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
    if (!empty) { empty = el("p", { id: "queue-empty", class: "empty", tabindex: "-1" }); box.after(empty); }
    empty.textContent = text;
  } else {
    empty?.remove();
  }
  // Only downloads on the list stay ticked: one that left the queue, or that the filter hides, drops out.
  const keys = new Set(shown.filter(canAct).map((i) => i.key));
  for (const k of chosen) if (!keys.has(k)) chosen.delete(k);
  renderSelection(shown);
  $("#queue-count").textContent = filter
    ? `${shown.length} of ${items.length} downloads`
    : `${items.length} ${items.length === 1 ? "download" : "downloads"}`;
}

// Bulk actions (owner, 21 November 2026: "add a bulk selector to the list so can do bulk actions") ------------
// A box on each row and Select all in the toolbar; the selection bar at the foot of the list then offers the
// actions that fit what is ticked. Each download is sent on its own, one after another, as the slide-out does, and
// the bar counts them; then one sentence says what was done. Focus goes to Select all when the bar closes.

function canAct(item) { return item.id != null && !!item.service; }
function stuckItem(item) { return item.reelix && ["importPending", "importBlocked", "failedPending"].includes(item.status); }
function shownItems() { return sorted(items.filter((i) => !filter || words(i)[0] === filter)); }

function pickRow(key, on, range) {
  const list = shownItems().filter(canAct).map((i) => i.key);
  const keys = range && lastPicked && list.includes(lastPicked)
    ? list.slice(Math.min(list.indexOf(lastPicked), list.indexOf(key)), Math.max(list.indexOf(lastPicked), list.indexOf(key)) + 1)
    : [key];
  keys.forEach((k) => (on ? chosen.add(k) : chosen.delete(k)));
  lastPicked = key;
  renderRows();
}

function renderSelection(shown = shownItems()) {
  const can = shown.filter(canAct);
  const all = $("#select-all");
  if (all) {
    all.disabled = !can.length || bulkRunning;
    all.checked = can.length > 0 && chosen.size === can.length;
    all.indeterminate = chosen.size > 0 && chosen.size < can.length;
    all.closest("label").hidden = !can.length;
  }
  const bar = $("#selection-bar");
  if (!bar || bulkRunning) return;
  const picked = can.filter((i) => chosen.has(i.key));
  const sig = picked.map((i) => `${i.key}:${stuckItem(i)}`).join(",");
  if (bar.dataset.sig === sig) return; // the poll changes nothing here, so focus in the bar stays put
  bar.dataset.sig = sig;
  bar.hidden = !picked.length;
  if (!picked.length) return;
  const stuck = picked.filter(stuckItem);
  const one = picked.length === 1;
  $("#selection-text").textContent = `${plural(picked.length, "download")} selected`;
  const button = (iconName, text, action, cls = "btn") => {
    const b = el("button", { type: "button", class: cls }, icon(iconName), text);
    b.addEventListener("click", action);
    return b;
  };
  const clients = (list) => [...new Set(list.map((i) => i.client).filter(Boolean))];
  const where = (list) => (clients(list).length === 1 ? clients(list)[0] : "the download clients");
  const left = (n) => {
    const rest = picked.length - n;
    if (!rest) return "";
    return rest === 1 ? " The other download is not waiting to import, so it is left as it is."
      : ` The other ${rest} downloads are not waiting to import, so they are left as they are.`;
  };
  const out = [];
  if (stuck.length) {
    out.push(button("refresh-cw", "Try the import again", () => bulkRun(stuck, "import", {
      title: `Try the import again for ${plural(stuck.length, "download")}?`,
      message: `Reelix checks the finished files again and moves them into your library if it can.${left(stuck.length)}`,
      confirm: "Try again" }), "btn btn--primary"));
    out.push(button("eye-off", "Ignore", () => bulkRun(stuck, "ignore", {
      title: `Ignore ${plural(stuck.length, "download")}?`,
      message: `Reelix stops warning about ${stuck.length === 1 ? "it" : "them"} and leaves the files in ${where(stuck)}'s folder. Nothing is deleted.${left(stuck.length)}`,
      confirm: "Ignore" })));
  }
  out.push(button("search", "Find another", () => bulkRun(picked, "block-search", {
    title: one ? "Block this release and find another?" : `Block these ${picked.length} releases and find others?`,
    message: `Each app removes ${one ? "it" : "them"} from ${where(picked)}, never downloads ${one ? "that release" : "those releases"} again, and searches for another now.`,
    confirm: "Block and search" })));
  out.push(button("trash-2", "Remove", () => {
    const block = el("input", { type: "checkbox" });
    bulkRun(picked, () => (block.checked ? "block" : "remove"), {
      title: `Remove ${plural(picked.length, "download")}?`,
      message: `Each app removes ${one ? "it" : "them"} from its queue and from ${where(picked)}, with what ${one ? "it has" : "they have"} downloaded.`,
      fields: [el("label", { class: "check" }, block, el("span", { class: "check__text" }, el("strong", { text: one ? "Block this release" : "Block these releases" }),
        el("span", { class: "check__hint", text: "So the apps do not download them again." })))],
      confirm: one ? "Remove download" : `Remove ${picked.length} downloads`, danger: true });
  }, "btn btn--danger"));
  out.push(button("x", "Clear selection", () => { chosen.clear(); renderRows(); $("#select-all")?.focus(); announce("Selection cleared"); }));
  $("#selection-actions").replaceChildren(...out);
}

const BULK_DONE = { import: ["Reelix is trying the import again for", "The import was not tried again for"],
  ignore: ["Ignored", "Not ignored:"], "block-search": ["Blocked, and searching for others for", "Not blocked:"],
  remove: ["Removed", "Not removed:"], block: ["Removed and blocked", "Not removed:"] };

async function bulkRun(list, action, dialog) {
  if (bulkRunning || !(await confirmDialog(dialog))) return;
  const chosenAction = typeof action === "function" ? action() : action;
  const bar = $("#selection-bar");
  const text = $("#selection-text");
  bulkRunning = true;
  bar.setAttribute("aria-busy", "true");
  bar.querySelectorAll("button").forEach((b) => { b.disabled = true; });
  renderRows();
  const failed = [];
  for (const [n, item] of list.entries()) {
    text.textContent = `Working on ${n + 1} of ${list.length}…`;
    try {
      await api("/api/queue/action", { method: "POST", body: { service: item.service, id: item.id, action: chosenAction } });
      chosen.delete(item.key);
    } catch (e) { failed.push(`${item.title}: ${e.message}`); }
  }
  bulkRunning = false;
  bar.removeAttribute("aria-busy");
  delete bar.dataset.sig;
  const done = list.length - failed.length;
  const [yes, no] = BULK_DONE[chosenAction];
  const said = [done ? `${yes} ${plural(done, "download")}.` : "", failed.length ? `${no} ${plural(failed.length, "download")}.` : ""].filter(Boolean).join(" ");
  await load();
  // Focus: the bar's first button while some are still ticked; otherwise Select all, or the empty queue's words.
  const all = $("#select-all");
  if (!bar.hidden) $("button", bar)?.focus();
  else if (all && !all.closest("label").hidden) all.focus();
  else $("#queue-empty")?.focus();
  if (failed.length) problem(`${said} ${failed.join(" ")}`); else toast(said);
  announce(said);
}

function selectAll() {
  const all = $("#select-all");
  const can = shownItems().filter(canAct);
  if (all.checked) can.forEach((i) => chosen.add(i.key)); else chosen.clear();
  lastPicked = null;
  renderRows();
  announce(all.checked ? `${plural(can.length, "download")} selected` : "Selection cleared");
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

function detailsBody(item, { brief = false } = {}) {
  const [label, tone] = words(item);
  const pct = percent(item);
  const done = item.size ? formatBytes(item.size * (item.progress || 0) / 100) : "";
  const body = [
    el("div", { class: "meter" },
      el("div", { class: "meter__label" }, el("span", {}, chip(label, tone)),
        el("span", { class: "numeric", text: item.size ? `${done} of ${formatBytes(item.size)} (${pct}%)` : `${pct}%` })),
      setProgress(newBar(), item, `${pct}% downloaded`)),
  ];
  if (item.problem && !brief) {
    body.push(notice("warning", `${item.service_name} needs a decision from you`, item.messages.length
      ? `Read its messages, then sort it out in the queue in ${item.service_name}.`
      : `${item.service_name} flagged this download without a message. Open the queue in ${item.service_name} to find out why.`));
  }
  if (item.messages.length && !brief) {
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
      title: "Try the import again?", message: `Reelix checks the finished files again and moves them into your library if it can. Read its messages first if it failed before.`,
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
  const panel = sidePanel({ title: "Choose the episode", wide: true, opener: panelOpener || document.activeElement, body: [el("p", { class: "muted", text: "Asking Reelix…" })] });
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
  panelOpener = opener;
  stopUnpackWatch();
  attention = needsYou(item) ? { key, data: null, done: false } : null;
  panel = sidePanel({
    title: item.title, wide: !!attention, opener,
    // What is wrong and what to do come straight after the progress, before the facts (reading order).
    body: attention ? (([meter, ...rest]) => [meter, attentionLoading(item), ...rest])(detailsBody(item, { brief: true })) : detailsBody(item),
    foot: attention ? attentionFoot(item) : detailsFoot(item),
    onClose: () => { panel = null; panelKey = null; attention = null; stopUnpackWatch(); },
  });
  if (attention) loadAttention(item);
}

function refreshDetails() {
  if (!panel || !panelKey) return;
  const item = byKey.get(panelKey);
  if (attention) {
    // The slide-out of a download that needs attention is drawn from its own answer (loadAttention), so the
    // queue's timer never redraws it under the person's focus. Only its leaving the queue is said here.
    if (!item && !attention.done && !attention.busy) attentionGone(null);
    return;
  }
  if (item) {
    panel.body.replaceChildren(...detailsBody(item));
  } else {
    panel.body.replaceChildren(notice("info", "This download has left the queue",
      "The app may have imported it, or it was removed. Close this panel to go back to the queue."));
    panel.setFoot([]);
  }
}

// A download that needs attention (DASH-496) ---------------------------------------------------------------
// Owner, 19 November 2026: "For needs attention - I want a slide out with a list of things to do with the file
// including delete". Selecting its name opens a wider slide-out; Starboard then asks the app, once, what is wrong
// and reads the download folder (GET /api/queue/item), and lists every action that fits, each with one line on
// what happens. Results are said in the live region and shown in the slide-out; focus stays on the button that was
// pressed, or moves to the result when the download has left the queue. Nothing here runs on the queue's timer.


function needsYou(item) {
  return item.problem || ["failed", "failedPending", "importBlocked"].includes(item.status);
}

function attentionLoading(item) {
  return el("div", { id: "attention", class: "stack-4", "aria-busy": "true" },
    el("p", { class: "muted", text: `Asking ${item.service_name} what is wrong and reading the download folder…` }));
}

function attentionFoot(item) {
  const href = appLink(item);
  return href ? [el("a", { class: "btn", href, target: "_blank", rel: "noopener noreferrer" }, icon("external-link"),
    `Open the queue in ${item.service_name}`, el("span", { class: "visually-hidden", text: " (opens in a new tab)" }))] : [];
}

async function loadAttention(item, { said = "" } = {}) {
  const key = item.key;
  let d;
  try {
    d = await api(`/api/queue/item?service=${encodeURIComponent(item.service)}&id=${encodeURIComponent(item.id)}`);
  } catch (e) {
    if (!attention || attention.key !== key) return;
    const box = $("#attention");
    box?.removeAttribute("aria-busy");
    box?.replaceChildren(notice("danger", "Starboard could not ask about this download", e.message), ...attentionList(item, null));
    return;
  }
  if (!attention || attention.key !== key || attention.done) return;
  attention.data = d;
  renderAttention(item, d);
  if (said) announce(said);
  else announce(`${d.diagnosis[0].title}. ${plural(d.actions.length, "action")} to choose from.`);
}

function renderAttention(item, d) {
  // Focus stays on the same action when the list is drawn again (after Try the import again or an unpack).
  const kept = document.activeElement?.closest?.("#attention") ? document.activeElement.dataset.action : null;
  const parts = [];
  d.diagnosis.forEach((x, n) => parts.push(el("div", { class: "notice", "data-tone": x.tone },
    icon(x.tone === "danger" ? "circle-x" : "triangle-alert"),
    el("div", { class: "notice__body" }, el(n === 0 ? "h3" : "span", { class: "notice__title", text: x.title }), el("p", { text: x.text })))));
  if (d.unpack?.state === "running") parts.push(unpackNotice(d.unpack));
  // What is wrong, then what can be done, then the details behind it (reading order).
  parts.push(...attentionList(item, d));
  parts.push(filesSection(d));
  if (d.messages.length) {
    parts.push(el("section", { class: "stack-2", "aria-labelledby": "na-msg-h" },
      el("h3", { id: "na-msg-h", text: `What ${item.service_name} says` }),
      el("ul", { class: "rows" }, d.messages.map((m) => el("li", { class: "row row--no-lead" }, el("div", { class: "row__meta", text: m }))))));
  }
  const box = $("#attention");
  if (!box) return;
  box.removeAttribute("aria-busy");
  box.replaceChildren(...parts);
  // The action used may have gone (Unpack, once unpacked): the suggested one takes focus instead.
  if (kept) ($(`#attention [data-action="${kept}"]`) || $(`#attention [data-action="${d.suggest}"]`))?.focus();
}

function filesSection(d) {
  const head = el("h3", { id: "na-files-h", text: "In the download folder" });
  if (!d.summary) {
    return el("section", { class: "stack-2", "aria-labelledby": "na-files-h" }, head,
      el("p", { class: "muted", text: d.folder_problem || "The download folder could not be read." }));
  }
  const s = d.summary;
  const SHOWN = 30;
  const rows = d.files.slice(0, SHOWN).map((f) => el("li", { class: "row row--no-lead" },
    el("div", {}, el("div", { class: "row__title", text: f.name.split("/").pop() }),
      f.parts > 1 || f.name.includes("/") ? el("div", { class: "row__meta", text: [f.parts > 1 ? `${f.parts} parts` : "",
        f.name.includes("/") ? `in ${f.name.split("/").slice(0, -1).join("/")}` : ""].filter(Boolean).join(", ").replace(/^in/, "In") }) : null),
    el("div", { class: "row__side" }, el("span", { class: "tag file-kind", "data-kind": f.kind, text: f.kind_words }),
      el("span", { class: "numeric", text: f.size_words }))));
  const more = d.files.length > SHOWN ? el("p", { class: "small muted", text: `And ${plural(d.files.length - SHOWN, "more file")}.` }) : null;
  return el("section", { class: "stack-2", "aria-labelledby": "na-files-h" }, head,
    el("p", { text: s.files ? `${plural(s.files, "file")}, ${s.total_words}. ${s.words}` : s.words }),
    d.path ? el("p", { class: "small muted" }, "Folder: ", el("code", { text: d.path })) : null,
    rows.length ? el("ul", { class: "rows", "aria-label": "Files in the download folder" }, rows) : null, more);
}

function attentionDefs(item, d) {
  const s = d?.summary;
  const space = s ? `${plural(s.files, "file")} (${s.total_words})` : "what it downloaded";
  const what = { episode: "episode", "radio episode": "episode", film: "film", book: "book", album: "album" }[d?.kind] || "download";
  const app = item.service_name;
  return {
    unpack: { label: "Unpack the archives, then import", icon: "archive-restore", group: "fix", run: (b) => startUnpack(item, b),
      hint: `Unpacks ${plural(d?.archives?.to_unpack || 0, "archive")} into the same folder, archives inside archives too, then Reelix imports what is inside. The archives stay until you delete the download.` },
    "choose-episode": { label: "Choose the episode", icon: "list-checks", group: "fix", run: () => chooseEpisode(item),
      hint: "Tell Reelix which episode each file is, then it imports them." },
    "choose-film": { label: "Choose the film", icon: "film", group: "fix", run: () => chooseFilm(item),
      hint: "Tell Reelix which film in your library this is, then it imports it." },
    import: { label: "Try the import again", icon: "refresh-cw", group: "fix", run: (b) => attentionAction(item, "import", null, b),
      hint: `${app} checks the files again and imports the ${what} if it can.` },
    "block-search": { label: "Find another", icon: "search", group: "fix", hint: `Deletes this download, adds the release to the blocklist and searches for another ${what} now.`,
      run: (b) => attentionAction(item, "block-search", { title: "Find another release?", confirm: "Delete and find another", danger: true,
        message: `${app} deletes ${space}, adds this release to the blocklist so it is never downloaded again, and searches for another now. This cannot be undone.` }, b) },
    ignore: { label: "Ignore", icon: "eye-off", group: "remove", hint: `Takes it off the list and notes in ${app}'s history that you chose to ignore it. The files stay where they are.`,
      run: (b) => attentionAction(item, "ignore", { title: "Ignore this download?", confirm: "Ignore",
        message: `${app} stops warning about it and leaves the files in ${item.client || "the download client"}'s folder. Nothing is deleted.` }, b) },
    "remove-keep": { label: "Remove from the list and keep the files", icon: "folder", group: "remove",
      hint: `Takes it off the list. The files stay in the download folder, and ${item.client || "the download client"} keeps them, so you can use them yourself.`,
      run: (b) => attentionAction(item, "remove-keep", { title: "Remove it from the list?", confirm: "Remove and keep the files",
        message: `${app} stops tracking this download. Its files stay in the download folder; nothing is deleted.` }, b) },
    delete: { label: "Remove and delete the files", icon: "trash-2", group: "remove", danger: true, run: (b) => deleteFiles(item, d, false, b),
      hint: s ? `Removes it and deletes ${space} from the download folder. Asks first.` : "Removes it and has the download client delete what it downloaded. Asks first." },
    "delete-block": { label: "Remove, delete and add to the blocklist", icon: "ban", group: "remove", danger: true, run: (b) => deleteFiles(item, d, true, b),
      hint: "For a fake or harmful release, such as an .exe posing as an episode: deletes the files and never downloads this release again. Asks first." },
  };
}

function attentionList(item, d) {
  const defs = attentionDefs(item, d);
  const ids = d ? d.actions : (item.reelix ? ["import", "block-search", "ignore", "remove-keep", "delete", "delete-block"] : ["block-search", "remove-keep", "delete", "delete-block"]);
  const suggest = d?.suggest;
  const list = (group) => ids.filter((id) => defs[id]?.group === group).map((id) => {
    const a = defs[id];
    const hintId = `na-hint-${id}`;
    const cls = a.danger ? "btn btn--danger" : id === suggest ? "btn btn--primary" : "btn";
    const b = el("button", { type: "button", class: cls, "data-action": id, "aria-describedby": hintId }, icon(a.icon), a.label);
    b.addEventListener("click", () => { if (b.getAttribute("aria-disabled") !== "true") a.run(b); });
    return el("li", { class: "action-list__item" }, b,
      el("p", { class: "action-list__hint", id: hintId, text: id === suggest ? `Suggested. ${a.hint}` : a.hint }));
  });
  const fix = list("fix"), remove = list("remove");
  const groups = [
    fix.length ? el("section", { class: "stack-2", "aria-labelledby": "na-fix-h" }, el("h3", { id: "na-fix-h", text: "Fix it" }), el("ul", { class: "action-list" }, fix)) : null,
    el("section", { class: "stack-2", "aria-labelledby": "na-rm-h" }, el("h3", { id: "na-rm-h", text: "Take it off the list" }), el("ul", { class: "action-list" }, remove)),
  ].filter(Boolean);
  // The group with the suggested action comes first, so it is the first thing after what is wrong (a program: delete).
  return defs[suggest]?.group === "remove" ? groups.reverse() : groups;
}

// While an action runs, the queue's own update must not say the download has gone before the action's answer does.
function busy(button, on) {
  if (attention) attention.busy = on;
  if (!button) return;
  if (on) { button.setAttribute("aria-disabled", "true"); button.setAttribute("aria-busy", "true"); }
  else { button.removeAttribute("aria-disabled"); button.removeAttribute("aria-busy"); }
}

const DONE_WORDS = { import: "Reelix is trying the import again", ignore: "Ignored. The files stay where they are",
  "block-search": "Deleted and on the blocklist. Searching for another", "remove-keep": "Removed from the list. The files stay where they are" };

async function attentionAction(item, action, dialog, button) {
  if (dialog && !(await confirmDialog(dialog))) return;
  busy(button, true);
  try {
    await api("/api/queue/action", { method: "POST", body: { service: item.service, id: item.id, action } });
  } catch (e) {
    busy(button, false);
    problem(`Not done: ${e.message}`, button);
    return;
  }
  busy(button, false);
  toast(DONE_WORDS[action]);
  load();
  if (action === "import") {
    announce(DONE_WORDS[action]);
    setTimeout(() => { if (attention?.key === item.key) loadAttention(item, { said: "Checked again after the import" }); }, 4000);
    return;
  }
  attentionGone(`${DONE_WORDS[action]}.`);
}

// The download has left the queue: the result takes the slide-out's place and gets focus, so nothing is lost.
function attentionGone(words) {
  if (!panel || !attention) return;
  attention.done = true;
  stopUnpackWatch();
  const result = el("div", { class: "notice", "data-tone": words ? "success" : "info", tabindex: "-1", id: "na-result" },
    icon(words ? "circle-check" : "info"),
    el("div", { class: "notice__body" }, el("h3", { class: "notice__title", text: words ? "Done" : "This download has left the queue" }),
      el("p", { text: words || "The app may have imported it, or it was removed. Close this panel to go back to the queue." })));
  panel.body.replaceChildren(result);
  panel.setFoot([el("button", { type: "button", class: "btn", "data-closes": true, text: "Back to the queue" })]);
  result.focus();
  if (words) announce(words);
}

async function deleteFiles(item, d, block, button) {
  const s = d?.summary;
  const names = (d?.files || []).slice(0, 5).map((f) => el("li", { text: f.parts > 1 ? `${f.name} and its ${f.parts - 1} other parts` : f.name }));
  const more = d && d.files.length > 5 ? el("li", { text: `and ${plural(d.files.length - 5, "more")}` }) : null;
  const message = [
    el("p", { text: s && s.files
      ? `This deletes ${plural(s.files, "file")} from the download folder and frees ${s.total_words}. It cannot be undone.`
      : `${item.client || "The download client"} deletes what it downloaded. Starboard could not read the folder, so it cannot say how much space this frees. It cannot be undone.` }),
    names.length ? el("ul", { class: "small" }, names, more) : null,
    d?.path ? el("p", { class: "small muted" }, "Folder: ", el("code", { text: d.path })) : null,
    block ? el("p", { text: `${item.service_name} also adds this release to the blocklist, so it is never downloaded again, and does not search for another.` }) : null,
  ].filter(Boolean);
  const ok = await confirmDialog({ title: block ? "Delete the files and block this release?" : "Delete the files of this download?",
    message, confirm: block ? "Delete and block" : "Delete the files", danger: true });
  if (!ok) return;
  busy(button, true);
  announce("Deleting the files…");
  let out;
  try {
    out = await api("/api/queue/item/delete", { method: "POST", body: { service: item.service, id: item.id, block } });
  } catch (e) {
    busy(button, false);
    problem(`Not deleted: ${e.message}`, button);
    return;
  }
  toast(out.words, out.left.length ? { tone: "warning" } : {});
  load();
  attentionGone(out.words);
}

// Unpacking runs on the server; the slide-out asks how it is going every 2 seconds while it is open, and only then.
function unpackNotice(job) {
  return el("div", { class: "notice", id: "na-unpack" }, icon("archive-restore"),
    el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: "Unpacking" }),
      el("p", { text: job.words || "Unpacking the archives" }), el("div", { class: "progress progress--busy", "aria-hidden": "true" }, el("span"))));
}

function stopUnpackWatch() {
  clearTimeout(unpackTimer);
  unpackTimer = null;
}

async function startUnpack(item, button) {
  busy(button, true);
  let job;
  try {
    job = await api("/api/queue/item/unpack", { method: "POST", body: { service: item.service, id: item.id } });
  } catch (e) {
    busy(button, false);
    problem(`Not unpacked: ${e.message}`, button);
    return;
  }
  announce("Unpacking the archives. This can take a few minutes for a large download.");
  $("#na-unpack")?.remove();
  $("#attention")?.prepend(unpackNotice(job));
  watchUnpack(item, button);
}

function watchUnpack(item, button) {
  stopUnpackWatch();
  unpackTimer = setTimeout(async () => {
    if (!attention || attention.key !== item.key) return;
    let job;
    try { job = await api(`/api/queue/item/unpack?service=${encodeURIComponent(item.service)}&id=${encodeURIComponent(item.id)}`); }
    catch { watchUnpack(item, button); return; }
    if (job.state === "running") {
      const words = $("#na-unpack p");
      if (words && words.textContent !== job.words) words.textContent = job.words;
      watchUnpack(item, button);
      return;
    }
    busy(button, false);
    $("#na-unpack")?.remove();
    if (job.state === "done") { toast(job.words.split(". ")[0], { detail: job.words.split(". ").slice(1).join(". ") }); load(); }
    else problem(job.words, button);
    loadAttention(item, { said: job.words });
  }, 2000);
}

// Choose the film (DASH-496): which film in the library a download is, through Reelix's manual import.
async function chooseFilm(item) {
  const fp = sidePanel({ title: "Choose the film", wide: true, opener: panelOpener, body: [el("p", { class: "muted", text: "Asking Reelix…" })] });
  const base = `/api/queue/item/film?service=${encodeURIComponent(item.service)}&id=${encodeURIComponent(item.id)}`;
  const search = el("input", { type: "search", class: "input", id: "film-q", autocomplete: "off" });
  const results = el("fieldset", { class: "stack-2" }, el("legend", { class: "field__label", text: "Films in your library" }));
  const status = el("p", { class: "small muted", role: "status" });
  const draw = (o) => {
    results.replaceChildren(el("legend", { class: "field__label", text: "Films in your library" }),
      ...(o.films.length ? o.films.map((f, n) => el("label", { class: "check" },
        el("input", { type: "radio", name: "film-pick", value: f.id, checked: f.id === o.guess || (!o.guess && n === 0) }),
        el("span", { class: "check__text" }, el("strong", { text: `${f.title}${f.year ? ` (${f.year})` : ""}` }),
          el("span", { class: "check__hint", text: f.have ? "In your library already: importing replaces your copy if this one is better" : "Not in your library yet" }))))
        : [el("p", { class: "muted", text: "No film in your library matches. Search for another title, or add the film in Search first." })]));
    status.textContent = `${plural(o.films.length, "film")} found`;
  };
  let o;
  try { o = await api(base); }
  catch (e) { fp.body.replaceChildren(notice("danger", "Reelix could not be asked", e.message)); return; }
  search.value = o.query;
  const find = el("button", { type: "submit", class: "btn" }, icon("search"), "Search");
  const form = el("form", { class: "inline-save", role: "search" }, search, find);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    try { draw(await api(`${base}&q=${encodeURIComponent(search.value)}`)); } catch (err) { problem(err.message, find); }
  });
  draw(o);
  const go = el("button", { type: "button", class: "btn btn--primary" }, icon("download"), "Import");
  go.addEventListener("click", async () => {
    const picked = $('input[name="film-pick"]:checked', results);
    if (!picked) { problem("Choose a film", go); return; }
    busy(go, true);
    try {
      await api(base.replace(/\?.*/, ""), { method: "POST", body: { service: item.service, id: item.id, movie_id: Number(picked.value) } });
      toast("Reelix is importing it"); fp.close(); load({ announceIt: true });
    } catch (err) { busy(go, false); problem(err.message, go); }
  });
  fp.body.replaceChildren(
    el("p", { text: "Reelix could not tell which film this download is. Choose the film, then Reelix imports the file to it." }),
    o.files.length ? el("ul", { class: "rows", "aria-label": "Files it imports" }, o.files.map((f) => el("li", { class: "row row--no-lead" },
      el("div", { class: "row__title", text: f.name }), el("div", { class: "row__side numeric", text: f.size_words })))) : null,
    el("div", { class: "field" }, el("label", { class: "field__label", for: "film-q", text: "Find the film in your library" }), form),
    status, results);
  fp.setFoot([go, el("button", { type: "button", class: "btn", "data-closes": true, text: "Cancel" })]);
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

// Copy issues for an AI helper (DASH-434): every download that needs attention or failed, with all its details, as
// Markdown with a short prompt at the top. Gathered only when a button is pressed, never on the timer (lightweight
// rule). The result is said in the live region ("Copied 3 issues") and shown under the heading; focus stays on the
// button that was pressed.

let exporting = false;
const issueWords = (n) => `${n} ${n === 1 ? "issue" : "issues"}`;

function exportBox(tone, title, text, extra = []) {
  // No role here: the live region says it once, so a screen reader does not hear it twice.
  const box = $("#issues-export");
  box.hidden = false;
  box.replaceChildren(el("div", { class: "notice", "data-tone": tone },
    icon(tone === "success" ? "circle-check" : tone === "warning" ? "triangle-alert" : "info"),
    el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: title }), text ? el("p", { text }) : null, ...extra)));
}

function exportPreview(markdown, open = false) {
  const pre = el("pre", { class: "code-block", tabindex: "0", "aria-label": "The issues, as Markdown", text: markdown });
  const details = el("details", { class: "disclosure" }, el("summary", { text: "Show what was copied" }), pre);
  details.open = open;
  return details;
}

async function issuesExport(how, button) {
  if (exporting) return;
  exporting = true;
  button.setAttribute("aria-busy", "true");
  announce("Gathering the issues…");
  try {
    const out = await api("/api/queue/issues?fresh=1");
    const missed = out.errors.length ? ` ${out.errors.length === 1 ? "One app" : `${out.errors.length} apps`} did not answer, so ${out.errors.length === 1 ? "its" : "their"} downloads are not included.` : "";
    if (!out.count) {
      const box = $("#issues-export");
      box.hidden = false;
      box.replaceChildren(emptyState("No issues to copy", `Nothing in the queue needs attention or failed right now.${missed}`));
      announce(`No issues to copy. Nothing in the queue needs attention or failed.${missed}`);
      return;
    }
    if (how === "download") {
      const stamp = out.generated_at.replace(/[-:]/g, "").replace("T", "-").slice(0, 13);
      const url = URL.createObjectURL(new Blob([out.markdown], { type: "text/markdown;charset=utf-8" }));
      const a = el("a", { href: url, download: `starboard-download-issues-${stamp}.md` });
      document.body.append(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      exportBox("success", `Downloaded ${issueWords(out.count)} as Markdown`,
        `Attach the file to a chat with an AI helper, such as Claude, or open it to read it first. Keys, passwords and private addresses are taken out.${missed}`);
      announce(`Downloaded ${issueWords(out.count)} as Markdown`);
      return;
    }
    if (await copyText(out.markdown)) {
      exportBox("success", `Copied ${issueWords(out.count)} for an AI helper`,
        `Paste them into a chat with an AI helper, such as Claude. It starts with a short prompt saying what to do. Keys, passwords and private addresses are taken out; read it before you send it.${missed}`,
        [exportPreview(out.markdown)]);
      announce(`Copied ${issueWords(out.count)}`);
    } else {
      exportBox("warning", "The browser did not let Starboard copy",
        "Select the text of the issues and copy it, or use Download as Markdown.", [exportPreview(out.markdown, true)]);
      announce("Not copied. The issues are on the page, to copy by hand");
    }
  } catch (e) {
    problem(`The issues could not be gathered: ${e.message}`, button);
  } finally {
    exporting = false;
    button.removeAttribute("aria-busy");
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

// Downloading without a VPN (DASH-440): a quiet reminder, with the way to add one, that can be hidden for 90 days.
// Never a notification. The words are the set-ups' (web/setup-answers.json, novpn).
async function loadVpnReminder() {
  let st;
  try { st = await api("/api/downloads/vpn-state"); } catch { return; }
  $("#vpn-reminder")?.remove();
  if (!st.reminder) return;
  const w = (await setupWords()).novpn;
  const hide = el("button", { type: "button", class: "btn btn--quiet btn--compact" }, w.hide);
  const box = el("div", { id: "vpn-reminder", class: "notice", "data-tone": "muted" }, icon("info"),
    el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: w.reminder_title }), el("p", { text: w.reminder }),
      el("p", {}, el("a", { href: "/settings-downloads.html", text: w.add }))),
    hide);
  hide.addEventListener("click", async () => {
    hide.disabled = true;
    try {
      await api("/api/downloads/vpn-reminder", { method: "POST", body: {} });
      box.remove();
      const h1 = $("main h1");
      if (h1) { h1.tabIndex = -1; h1.focus(); }
      announce("Hidden for 90 days");
    } catch (e) { problem(e.message, hide); hide.disabled = false; }
  });
  $("#transfer").before(box);
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
      `${v.name}${where ? `: ${where}` : ""}${v.port ? `, forwarded port ${v.port}` : v.running && v.from !== "container" ? ", no forwarded port" : ""}`,
      v.running ? "success" : "danger", v.running ? null : "Downloads may stop"));
  }
  for (const e of t.errors) tiles.push(stat(STATUS.notResponding[0], e.message, STATUS.notResponding[1]));
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
  const settings = el("a", { href: "/settings-downloads-hours.html", text: "Settings, Downloads, Download hours" });
  box.dataset.tone = !s.enabled ? "neutral" : s.mode === "run" ? "success" : "warning";
  if (!s.enabled) {
    $("#schedule-chip").replaceChildren(chip(...STATUS.inactive));
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
  // Every few seconds (Settings, General, Performance) while the tab is in view; a hidden tab asks nothing and catches up
  // when shown again.
  timer = on || !every ? null : setInterval(() => { if (!document.hidden) { load(); loadSchedule(); loadTransfer(); } }, every * 1000);
  $("#auto-refresh").setAttribute("aria-pressed", String(on));
  renderSummary();
}

startPage().then(async () => {
  bringInBanner($(".page-head"));  // DASH-455: a copy of media you already have, while it runs
  $("#refresh").addEventListener("click", () => { load({ announceIt: true }); loadTransfer(true); loadHeld(); });
  $("#copy-issues").addEventListener("click", (e) => issuesExport("copy", e.currentTarget));
  $("#download-issues").addEventListener("click", (e) => issuesExport("download", e.currentTarget));
  $("#auto-refresh").addEventListener("click", () => {
    setPaused(!paused);
    announce(paused ? "Updates paused" : every ? `Updates resumed, every ${every} seconds` : "Updates only when you press Check again");
  });
  $("#select-all").addEventListener("change", selectAll);
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
  loadVpnReminder();
  loadRecent();
  setPaused(false);
  document.addEventListener("visibilitychange", () => { if (!document.hidden && !paused) { load(); loadSchedule(); loadTransfer(); loadHeld(); } });
});
