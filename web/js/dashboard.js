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
    // The wizard (DASH-289): one item at a time; it opens by itself once in each browser session.
    const walk = el("button", { type: "button", class: "btn btn--primary btn--compact", "aria-haspopup": "dialog" }, "Go through them");
    walk.addEventListener("click", () => setupWizard({ opener: walk, onChange: () => draw() }));
    if (!editing) setupWizardOnce(() => draw());
    return el("div", { class: "stack-2" }, el("div", { class: "actions" }, walk), el("ul", { class: "rows" }, todo.map((i) => line(i.title, i.why, i.href.startsWith("http") ? reachableUrl(i.href) : i.href))));
  },
  async playing() {
    const r = await ask("/api/jellyfin");
    if (!r.configured) return empty("Add Jellyfin with its key to see what is playing.", "/settings.html", "Manage apps");
    return r.playing.length ? el("ul", { class: "rows" }, r.playing.slice(0, 5).map((p) => line(p.title || "Something", [p.user, p.device].filter(Boolean).join(" · "))))
      : empty("Nothing is playing.");
  },
  async downloads() {
    const r = await ask("/api/queue");
    const items = r.items || [];
    if (!items.length) return empty("Nothing is downloading.", "/wanted.html", "See what is wanted");
    return el("ul", { class: "rows" }, items.slice(0, 5).map((q) => line(q.title, [`${Math.round(q.progress || 0)}%`, q.time_left].filter(Boolean).join(" · "), "/downloads.html")));
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
    return el("ul", { class: "rows" }, (r.disks || []).slice(0, 4).map((d) => line(d.label || d.path || "Disk",
      d.total ? `${formatBytes(d.free)} free of ${formatBytes(d.total)}` : "", "/system-storage.html")));
  },
  async load() {
    const r = await ask("/api/system");
    const mem = r.memory || {};
    return el("dl", { class: "facts" }, el("dt", { text: "Processor" }), el("dd", { text: r.load ? `${Number(r.load[0] ?? r.load).toFixed(2)} (${r.cpus} cores)` : "Not reported" }),
      el("dt", { text: "Memory" }), el("dd", { text: mem.total ? `${formatBytes(mem.used)} of ${formatBytes(mem.total)}` : "Not reported" }));
  },
  async vpn() {
    const r = await ask("/api/transfer");
    if (!r.vpn?.length) return empty("No VPN on your apps.");
    const v = r.vpn[0];
    return el("div", { class: "stack-2" }, chip(v.running ? "Connected" : "Not connected", v.running ? "success" : "danger"),
      v.country ? el("p", { class: "small", text: [v.country, v.ip].filter(Boolean).join(" · ") }) : null);
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
    return el("div", { class: "stack-2" }, el("p", {}, chip(down.length ? `${down.length} not responding` : "All running", down.length ? "danger" : "success"),
      el("span", { class: "small muted", text: ` ${items.length} apps` })),
      down.length ? el("ul", { class: "rows" }, down.slice(0, 4).map((d) => line(d.name || d.id, d.message || "", "/index.html"))) : null);
  },
  async requests() {
    const r = await ask("/api/requests?pending=1");
    if (!r.configured) return empty("Add Reelix or Seerr to see requests.");
    return r.items.length ? el("ul", { class: "rows" }, r.items.slice(0, 5).map((q) => line(q.title, q.by ? `asked for by ${q.by}` : "", "/downloads-requests.html")))
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

// Cards from active plug-ins (DASH-149): Starboard asks the plug-in and draws the answer itself, as text only.
let pluginCards = {};
const FORMATS = {
  number: (v) => Number(v).toLocaleString("en-GB"),
  bytes: (v) => { let n = Number(v), u = 0; const units = ["bytes", "KB", "MB", "GB", "TB"]; while (n >= 1024 && u < 4) { n /= 1024; u++; } return `${n.toFixed(u ? 1 : 0)} ${units[u]}`; },
  percent: (v) => `${Math.round(Number(v))}%`,
  duration: (v) => { const m = Math.round(Number(v) / 60); return m >= 60 ? `${Math.floor(m / 60)} h ${m % 60} min` : `${m} min`; },
  date: (v) => new Date(Number(v) * 1000).toLocaleDateString("en-GB"),
};
async function pluginCard(id) {
  const [, pid, cid] = id.split(":");
  const r = await api(`/api/plugins/${pid}/cards/${cid}`);
  if (r.problem) return empty(r.problem);
  const d = r.data;
  if (r.type === "stat") return el("p", { class: "dash-stat" }, el("strong", { text: (FORMATS[r.format] || FORMATS.number)(d.value) }),
    d.label ? ` ${d.label}` : null, d.note ? el("span", { class: "small muted", text: ` ${d.note}` }) : null);
  if (r.type === "status") return el("p", {}, chip({ ok: "OK", warning: "Warning", problem: "Problem" }[d.state], { ok: "success", warning: "warning", problem: "danger" }[d.state]),
    d.text ? el("span", { text: ` ${d.text}` }) : null);
  return d.items.length ? el("ul", { class: "rows" }, d.items.map((it) => el("li", { class: "row row--no-lead" }, el("div", {},
    el("div", { class: "row__title" }, it.link ? el("a", { href: it.link, target: "_blank", rel: "noopener noreferrer", text: it.title }) : it.title),
    it.detail ? el("div", { class: "row__meta", text: it.detail }) : null)))) : empty("Nothing to show.");
}

function cardShell(c, i, list) {
  const head = el("div", { class: "dash-card__head" }, el("h2", { class: "dash-card__title", id: `dash-${c.id}-h`, text: CARD_TITLES[c.id] || "Plug-in card" }));
  const body = el("div", { class: "dash-card__body", "aria-live": "polite" }, el("p", { class: "small muted", text: "Asking…" }));
  const card = el("section", { class: `dash-card dash-card--${c.size}`, "aria-labelledby": `dash-${c.id}-h`, "data-card": c.id }, head, body);
  if (editing) {
    const size = el("select", { class: "select select--compact", "aria-label": `Size of ${CARD_TITLES[c.id]}` },
      Object.entries(SIZES).map(([v, t]) => el("option", { value: v, text: t, selected: v === c.size })));
    size.addEventListener("change", () => { list[i].size = size.value; draw(); });
    const move = (by) => { const j = i + by; if (j < 0 || j >= list.length) return; [list[i], list[j]] = [list[j], list[i]]; draw(); $(`[data-card="${c.id}"] button`)?.focus(); };
    head.append(el("div", { class: "dash-card__tools" }, size,
      el("button", { type: "button", class: "icon-btn", "aria-label": `Move ${CARD_TITLES[c.id]} earlier`, disabled: i === 0, onclick: () => move(-1) }, icon("arrow-up")),
      el("button", { type: "button", class: "icon-btn", "aria-label": `Move ${CARD_TITLES[c.id]} later`, disabled: i === list.length - 1, onclick: () => move(1) }, icon("arrow-down")),
      c.id === "setup" ? null : el("button", { type: "button", class: "btn btn--quiet btn--compact", onclick: () => { list.splice(i, 1); draw(); announce(`${CARD_TITLES[c.id]} removed`); } }, "Remove",
        el("span", { class: "visually-hidden", text: ` ${CARD_TITLES[c.id]}` }))));
  }
  return { card, body };
}

async function fill(c, body, card) {
  try {
    const node = c.id.startsWith("plugin:") ? (pluginCards[c.id] ? await pluginCard(c.id) : empty("Its plug-in is not active.")) : await CARDS[c.id]();
    if (node === null && c.id === "setup" && !editing) { card.remove(); return; }  // everything is set up
    body.replaceChildren(node || empty("Nothing to show."));
  } catch (e) {
    body.replaceChildren(empty(e.status === 409 || e.status === 400 ? e.message : "Could not ask."));
  }
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
      dash = cfg.dashboard; editing = null; draw(); toast("Dashboard saved");
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
  try { dash = (await api("/api/config")).dashboard || dash; } catch { /* the default layout */ }
  try {
    for (const c of (await api("/api/plugins/cards")).cards) { pluginCards[c.id] = c; CARD_TITLES[c.id] = `${c.title} (${c.plugin})`; }
  } catch { /* no plug-in cards */ }
  $("#dash-summary").textContent = `${LAYOUTS[dash.layout]?.name || "At a glance"}. Change it with Edit dashboard.`;
  draw();
  // Once a minute while the page is in view; nothing while the tab is hidden.
  const tick = () => { if (!document.hidden && !editing) draw(); };
  timer = setInterval(tick, 60000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) tick(); });
});
