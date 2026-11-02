// Coming up: releases from every app's calendar, by day. /api/calendar gives yesterday and the next two weeks;
// the range control and the filter chips narrow that down in the browser. Each item opens a slide-out.

let items = [];
let range = 14;
let status = null; // "Wanted", "In library" or null
let app = null; // an app name or null
let services = new Map(); // app name -> app from /api/config (type for the icon, link for "Open in")
const ICONS = { sonarr: "tv", radarr: "film", lidarr: "music", readarr: "book" };

const dayKey = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const statusWord = (i) => (i.have ? "In library" : "Wanted");

function startOfToday() { const d = new Date(); d.setHours(0, 0, 0, 0); return d; }

function dayHeading(date) {
  const today = startOfToday();
  const diff = Math.round((new Date(date.getFullYear(), date.getMonth(), date.getDate()) - today) / 86400000);
  const words = date.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });
  return diff === 0 ? `Today, ${words}` : diff === 1 ? `Tomorrow, ${words}` : diff === -1 ? `Yesterday, ${words}` : words;
}

function hasTime(i) { return services.get(i.service_name)?.type === "sonarr"; }
const timeOf = (i) => new Date(i.when).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });

// Sonarr sends the series as the title and "S02E03 · Episode name" as the detail.
function describe(i) {
  const type = services.get(i.service_name)?.type;
  if (type === "sonarr") {
    const [code, ...rest] = i.detail.split(" · ");
    const name = rest.join(" · ");
    return { title: `${i.title} · ${code}`, sub: name ? `"${name}"` : "" };
  }
  if (type === "radarr") return { title: i.title, sub: "Film" };
  return { title: i.title, sub: i.detail };
}

function notice(tone, title, text) {
  return el("div", { class: "notice", "data-tone": tone, role: "status" }, icon(tone === "warning" ? "triangle-alert" : "info"),
    el("div", { class: "notice__body" }, title ? el("span", { class: "notice__title", text: title }) : null, text ? el("p", { text }) : null));
}

// Filters ----------------------------------------------------------------

function inRange(i) {
  const end = startOfToday();
  end.setDate(end.getDate() + range);
  return new Date(i.when) < end;
}

function shown() {
  return items.filter((i) => inRange(i) && (!status || statusWord(i) === status) && (!app || i.service_name === app));
}

function chipButton(text, pressed, onclick, iconName) {
  return el("button", { type: "button", class: "filter-chip", "aria-pressed": String(pressed), onclick }, iconName ? icon(iconName) : null, text);
}

// Chips are built once, then their counts and pressed state change in place, so focus stays on the chip.
function renderFilters() {
  const pool = items.filter(inRange);
  const statusBox = $("#status-filters");
  if (!statusBox.children.length) {
    for (const word of ["Wanted", "In library"]) {
      const b = chipButton("", false, () => { status = status === word ? null : word; update(); });
      b.dataset.value = word;
      statusBox.append(b);
    }
    for (const name of [...new Set(items.map((i) => i.service_name))].sort((a, b) => a.localeCompare(b, "en-GB"))) {
      const label = el("span");
      const b = chipButton("", false, () => { app = app === name ? null : name; update(); }, ICONS[services.get(name)?.type] || "calendar");
      b.append(label);
      b.dataset.value = name;
      $("#app-filters").append(b);
    }
  }
  for (const b of statusBox.children) {
    const n = pool.filter((i) => statusWord(i) === b.dataset.value && (!app || i.service_name === app)).length;
    b.textContent = `${b.dataset.value}, ${n}`;
    b.setAttribute("aria-pressed", String(status === b.dataset.value));
  }
  for (const b of $("#app-filters").children) {
    const n = pool.filter((i) => i.service_name === b.dataset.value && (!status || statusWord(i) === status)).length;
    b.lastChild.textContent = `${b.dataset.value}, ${n}`;
    b.setAttribute("aria-pressed", String(app === b.dataset.value));
  }
  $("#app-filters").hidden = $("#app-filters").children.length < 2;
}

// Days -------------------------------------------------------------------

function renderDays() {
  const root = $("#calendar");
  const list = shown();
  const byDay = new Map();
  for (const i of list) {
    const key = dayKey(new Date(i.when));
    if (!byDay.has(key)) byDay.set(key, []);
    byDay.get(key).push(i);
  }
  root.replaceChildren(...[...byDay].map(([key, dayItems]) => {
    const id = `d-${key}`;
    const heading = dayHeading(new Date(dayItems[0].when));
    return el("section", { class: "media-section", "aria-labelledby": id },
      el("h2", { class: "group-heading", id, text: heading }),
      el("ul", { class: "rows" }, dayItems.map((i) => {
        const { title, sub } = describe(i);
        const button = el("button", { type: "button", onclick: () => openItem(i, button) }, title);
        return el("li", { class: "row row--opens row--no-lead" },
          el("div", {}, el("div", { class: "row__title" }, button),
            el("div", { class: "row__meta", text: [sub, hasTime(i) ? timeOf(i) : "", i.service_name].filter(Boolean).join(" · ") })),
          el("div", { class: "row__side" }, chip(statusWord(i), i.have ? "success" : "neutral")));
      })));
  }));
  if (!list.length) {
    root.append(el("p", { class: "empty", text: items.length
      ? "Nothing matches these filters. Turn a filter off to see more."
      : "Nothing is due in the next two weeks. New episodes, films, albums and books from your apps appear here." }));
  }
  const rangeWords = range === 7 ? "this week" : "the next two weeks";
  const wanted = list.filter((i) => !i.have).length;
  $("#calendar-summary").textContent = list.length
    ? `${list.length} ${list.length === 1 ? "release" : "releases"} in ${rangeWords} · ${wanted} wanted · ${list.length - wanted} already in the library`
    : `Nothing due in ${rangeWords}.`;
}

function update() {
  renderFilters();
  renderDays();
}

// Item slide-out -----------------------------------------------------------

function openItem(i, opener) {
  const { title, sub } = describe(i);
  const date = new Date(i.when);
  const day = dayHeading(date);
  const svc = services.get(i.service_name);
  const past = date < new Date();
  const facts = [
    [svc?.type === "sonarr" ? "Airs" : "Released", hasTime(i) ? `${day} at ${timeOf(i)}` : day],
    ["App", i.service_name],
    ["Status", i.have ? "In the library" : past
      ? `Wanted. ${i.service_name} has not found it yet.`
      : `Wanted. ${i.service_name} searches for it when it comes out.`],
  ];
  const link = svc?.link
    ? el("a", { class: "btn btn--primary", href: `${reachableUrl(svc.link)}/calendar`, target: "_blank", rel: "noopener noreferrer" },
      icon("external-link"), `Open the calendar in ${i.service_name}`, el("span", { class: "visually-hidden", text: " (opens in a new tab)" }))
    : null;
  sidePanel({
    title: day.replace(/^(Today|Tomorrow|Yesterday), /, ""), opener,
    body: [
      el("div", { class: "side-panel__lead" },
        el("div", { class: "cover", "aria-hidden": "true" }, icon(ICONS[svc?.type] || "calendar", 24)),
        el("div", { class: "media-panel-lead__text" },
          el("h3", { text: title }),
          chip(statusWord(i), i.have ? "success" : "neutral"),
          sub ? el("span", { class: "small muted", text: sub }) : null)),
      el("dl", { class: "facts" }, facts.flatMap(([k, v]) => [el("dt", { text: k }), el("dd", { text: v })])),
    ],
    foot: link ? [link] : [],
  });
}

startPage().then(async () => {
  try {
    const [data, cfg] = await Promise.all([api("/api/calendar"), api("/api/config").catch(() => ({ services: [] }))]);
    services = new Map(cfg.services.map((s) => [s.name, s]));
    // The API starts yesterday, so last night's episode that is still wanted shows too.
    const yesterday = startOfToday();
    yesterday.setDate(yesterday.getDate() - 1);
    items = data.items.filter((i) => new Date(i.when) >= yesterday);
    $("#calendar-errors").replaceChildren(...data.errors.map((e) => notice("warning", "", e.message)));
    $$("#range input").forEach((r) => r.addEventListener("change", () => { range = Number(r.value); update(); }));
    update();
  } catch (e) {
    $("#calendar-summary").textContent = e.message;
  }
});
