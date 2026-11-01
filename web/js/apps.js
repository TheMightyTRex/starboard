// Apps: every app grouped, with its status checked by the server. Some designs add more: Now shows what needs
// you, what is downloading and what is coming; Split view shows one app's details; Health first groups by status.

let config = null;
let statuses = {};
let selectedId = null;
const extra = {};  // queue, calendar and health, fetched once when a design needs them

const design = () => document.documentElement.dataset.design;

function statusChip(s) {
  if (!s) return chip("Checking", "neutral");
  return s.state === "up" ? chip("Running", "success") : chip("Not responding", "danger");
}

function hue(name) {
  let h = 0;
  for (const c of name) h = (h * 31 + c.codePointAt(0)) % 360;
  return h;
}

function appItem(s) {
  const st = statuses[s.id];
  const item = el("li", { class: "app", "data-state": st ? st.state : "checking" },
    el("div", { class: "app__top" },
      el("span", { class: "app__icon", "aria-hidden": "true", text: monogram(s.name) }),
      el("h3", { class: "app__name" }, el("a", { href: s.link, target: "_blank", rel: "noopener noreferrer" }, s.name, el("span", { class: "visually-hidden", text: " (opens in a new tab)" })))),
    s.description ? el("p", { class: "app__desc", text: s.description }) : null,
    el("div", { class: "app__meta" },
      el("span", { class: "app__group-label", text: s.group || "Other" }),
      statusChip(st),
      el("span", { class: "app__version num", text: st && st.version ? `v${st.version}` : "" }),
      el("span", { class: "app__ms num", text: st && st.ms !== undefined ? `${st.ms} ms` : "" })));
  item.style.setProperty("--app-hue", hue(s.name));
  return item;
}

function appList(items, headingId) {
  return el("ul", { class: "apps", "aria-labelledby": headingId },
    el("li", { class: "apps-head", "aria-hidden": "true" }, el("span", { text: "App" }), el("span", { text: "Group" }), el("span", { text: "Status" }), el("span", { text: "Version" }), el("span", { text: "Reply" })),
    items.map(appItem));
}

function groupsOf(services) {
  if (design() === "health") {
    const down = services.filter((s) => statuses[s.id]?.state === "down");
    const checking = services.filter((s) => !statuses[s.id]);
    const up = services.filter((s) => statuses[s.id]?.state === "up");
    return [["Not responding", down], ["Checking", checking], ["Running", up]].filter(([, items]) => items.length);
  }
  const groups = [...config.groups];
  for (const s of services) if (s.group && !groups.includes(s.group)) groups.push(s.group);
  const out = groups.map((g) => [g, services.filter((s) => s.group === g)]);
  out.push(["Other", services.filter((s) => !s.group)]);
  return out.filter(([, items]) => items.length);
}

// Now: three bands from the design system's Home template ------------------

function band(title, id, items, empty) {
  return el("section", { class: "band", "aria-labelledby": id },
    el("h2", { class: "band__title", id, text: title }),
    items.length ? el("ul", { class: "rows" }, items) : el("p", { class: "hint", text: empty }));
}

function renderNow() {
  const box = $("#now-bands");
  if (design() !== "now") { box.hidden = true; return; }
  box.hidden = false;
  const down = config.services.filter((s) => s.enabled && statuses[s.id]?.state === "down");
  const needs = [
    ...down.map((s) => el("li", { class: "row" }, el("div", {}, el("p", { class: "row__title", text: s.name }), el("p", { class: "row__meta", text: statuses[s.id].message || "Not responding" })), el("div", { class: "row__side" }, chip("Not responding", "danger")))),
    ...(extra.health?.items || []).slice(0, 5).map((h) => el("li", { class: "row" }, el("div", {}, el("p", { class: "row__title", text: h.service_name }), el("p", { class: "row__meta", text: h.message })), el("div", { class: "row__side" }, chip("Needs attention", "warning")))),
  ];
  const downloading = (extra.queue?.items || []).filter((i) => i.status === "downloading").slice(0, 5).map((i) => {
    const bar = el("div", { class: "progress", role: "progressbar", "aria-valuenow": String(Math.round(i.progress)), "aria-valuemin": "0", "aria-valuemax": "100", "aria-label": `${i.title}, ${Math.round(i.progress)}%` }, el("span"));
    bar.firstChild.style.width = `${i.progress}%`;
    return el("li", { class: "row" }, el("div", {}, el("p", { class: "row__title", text: i.title }), el("p", { class: "row__meta", text: [i.service_name, i.time_left ? `${i.time_left} left` : ""].filter(Boolean).join(" · ") })), el("div", { class: "row__side" }, el("span", { class: "num", text: `${Math.round(i.progress)}%` })), bar);
  });
  const soon = (extra.calendar?.items || []).filter((i) => !i.have && new Date(i.when) >= new Date(Date.now() - 86400000)).slice(0, 5).map((i) =>
    el("li", { class: "row" }, el("div", {}, el("p", { class: "row__title", text: i.title }), el("p", { class: "row__meta", text: `${formatDate(i.when)} · ${i.detail}` })), el("div", { class: "row__side" }, chip(i.service_name, "neutral"))));
  box.replaceChildren(
    band("Needs you", "band-needs", needs, extra.health ? "Nothing needs you." : "Checking…"),
    band("Happening now", "band-now", downloading, extra.queue ? "Nothing downloading." : "Loading…"),
    band("Coming soon", "band-soon", soon, extra.calendar ? "Nothing due in the next two weeks." : "Loading…"),
    el("p", { class: "band__more" }, el("a", { href: "/downloads.html", text: "All downloads" }), el("a", { href: "/upcoming.html", text: "Everything coming up" })));
}

// Split view: list and detail ----------------------------------------------

function renderSplit(services) {
  const root = $("#app-groups");
  if (!selectedId || !services.some((s) => s.id === selectedId)) selectedId = services[0]?.id;
  const list = el("ul", { class: "split__list", "aria-label": "Apps" }, services.map((s) => {
    const st = statuses[s.id];
    return el("li", {}, el("button", {
      type: "button", class: "split__item", "aria-current": s.id === selectedId ? "true" : null,
      onclick: () => { selectedId = s.id; renderApps(); if (matchMedia("(max-width: 899px)").matches) $(".split__detail")?.scrollIntoView({ block: "start" }); },
    }, el("span", { class: "app__icon", "aria-hidden": "true", text: monogram(s.name) }), el("span", { class: "split__name", text: s.name }), statusChip(st)));
  }));
  const s = services.find((x) => x.id === selectedId);
  const st = statuses[s.id];
  const queue = (extra.queue?.items || []).filter((i) => i.service_name === s.name);
  const warnings = (extra.health?.items || []).filter((h) => h.service_name === s.name);
  const facts = [
    ["Status", st ? (st.state === "up" ? "Running" : st.message || "Not responding") : "Checking"],
    ["Version", st?.version || "Not reported"],
    ["Reply time", st?.ms !== undefined ? `${st.ms} ms` : "–"],
    ["Group", s.group || "Other"],
  ];
  if (["sonarr", "radarr", "lidarr", "readarr"].includes(s.type)) facts.push(["In the download queue", extra.queue ? String(queue.length) : "Loading…"]);
  const detail = el("section", { class: "split__detail panel", "aria-labelledby": "split-title" },
    el("div", { class: "app__top" }, el("span", { class: "app__icon", "aria-hidden": "true", text: monogram(s.name) }), el("h2", { id: "split-title", text: s.name })),
    s.description ? el("p", { text: s.description }) : null,
    el("dl", { class: "facts" }, facts.flatMap(([k, v]) => [el("dt", { text: k }), el("dd", { class: "num", text: v })])),
    warnings.length ? el("ul", { class: "rows" }, warnings.map((w) => el("li", { class: "row" }, el("p", { text: w.message }), el("div", { class: "row__side" }, chip("Needs attention", "warning"))))) : null,
    el("div", { class: "actions" }, el("a", { class: "btn btn-primary", href: s.link, target: "_blank", rel: "noopener noreferrer" }, `Open ${s.name}`, el("span", { class: "visually-hidden", text: " (opens in a new tab)" })), el("a", { class: "btn", href: "/settings.html#apps", text: "Edit in Settings" })));
  root.replaceChildren(el("div", { class: "split" }, list, detail));
}

function renderApps() {
  const root = $("#app-groups");
  root.replaceChildren();
  renderNow();
  const services = config.services.filter((s) => s.enabled);
  if (!services.length) {
    root.append(el("div", { class: "empty" },
      el("p", { text: "No apps yet." }),
      el("p", {}, el("a", { href: "/settings.html#apps", text: "Add your first app in Settings" }))));
    $("#apps-summary").textContent = "Add your apps in Settings to see them here.";
    return;
  }
  if (design() === "split") return renderSplit(services);
  groupsOf(services).forEach(([title, items], i) => {
    const headingId = `group-${i}`;
    root.append(el("section", { class: "app-group" }, el("h2", { class: "app-group__title", id: headingId, text: title }), appList(items, headingId)));
  });
}

async function loadExtra() {
  const want = { now: ["queue", "calendar", "health"], split: ["queue", "health"] }[design()] || [];
  const missing = want.filter((k) => !extra[k]);
  if (!missing.length) return;
  await Promise.all(missing.map((k) => api(`/api/${k}`).then((d) => { extra[k] = d; }).catch(() => { extra[k] = { items: [] }; })));
  renderApps();
}

async function checkStatus() {
  const button = $("#check-now");
  button.disabled = true;
  $("#apps-summary").textContent = "Checking your apps…";
  try {
    const { items } = await api("/api/status");
    statuses = Object.fromEntries(items.map((i) => [i.id, i]));
    renderApps();
    const up = items.filter((i) => i.state === "up").length;
    const down = items.length - up;
    const time = new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
    const text = `${up} of ${items.length} running${down ? ` · ${down} not responding` : ""} · checked at ${time}`;
    $("#apps-summary").textContent = text;
    announce(text);
  } catch (e) {
    $("#apps-summary").textContent = e.message;
  } finally {
    button.disabled = false;
  }
}

async function showAttention() {
  try {
    extra.health = extra.health || await api("/api/health");
    const box = $("#attention");
    const serious = extra.health.items.filter((i) => i.level === "error" || i.level === "warning");
    if (!serious.length || design() === "now") { box.hidden = true; return; }
    box.replaceChildren(el("div", { class: "notice", "data-tone": "warning" },
      el("strong", { text: `${serious.length} ${serious.length === 1 ? "warning" : "warnings"} from your apps. ` }),
      el("a", { href: "/system.html#health-title", text: "See what needs attention" })));
    box.hidden = false;
  } catch { /* the System page shows the details */ }
}

startPage().then(async () => {
  config = await api("/api/config");
  renderApps();
  $("#check-now").addEventListener("click", checkStatus);
  document.addEventListener("designchange", () => { renderApps(); loadExtra(); showAttention(); });
  checkStatus();
  showAttention();
  loadExtra();
});
