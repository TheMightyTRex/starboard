// Coming up: releases from every app's calendar, as a list by day or as a month calendar. /api/calendar gives
// yesterday and as many days ahead as Settings, General says. The view switch saves the choice to Settings too.
// Filter chips narrow the list in the browser. Each item opens a slide-out; each calendar day opens its day.

let items = [];
let days = 14;
let view = "list";
let status = null; // "Wanted", "In library" or null
let app = null; // an app name or null
let services = new Map(); // app name -> app from /api/config (type for the icon, link for "Open in")
const ICONS = { sonarr: "tv", radarr: "film", lidarr: "music", readarr: "book" };
const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

const dayKey = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const statusWord = (i) => (i.have ? "In library" : "Wanted");
const releases = (n) => `${n} ${n === 1 ? "release" : "releases"}`;

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

// The item's poster or cover; the app's icon when there is none or it does not load.
function cover(i, extra = "") {
  const type = services.get(i.service_name)?.type;
  const box = el("div", { class: `cover ${extra}`.trim(), "aria-hidden": "true" });
  const fallback = () => box.replaceChildren(icon(ICONS[type] || "calendar", extra ? 18 : 24));
  if (i.image) {
    const img = el("img", { src: i.image, alt: "", loading: "lazy", referrerpolicy: "no-referrer" });
    img.addEventListener("error", fallback);
    box.append(img);
  } else fallback();
  return box;
}

function notice(tone, title, text) {
  return el("div", { class: "notice", "data-tone": tone, role: "status" }, icon(tone === "warning" ? "triangle-alert" : "info"),
    el("div", { class: "notice__body" }, title ? el("span", { class: "notice__title", text: title }) : null, text ? el("p", { text }) : null));
}

// Filters ----------------------------------------------------------------

function shown() {
  return items.filter((i) => (!status || statusWord(i) === status) && (!app || i.service_name === app));
}

function chipButton(text, pressed, onclick, iconName) {
  return el("button", { type: "button", class: "filter-chip", "aria-pressed": String(pressed), onclick }, iconName ? icon(iconName) : null, text);
}

// Chips are built once, then their counts and pressed state change in place, so focus stays on the chip.
function renderFilters() {
  const statusBox = $("#status-filters");
  if (!statusBox.children.length) {
    for (const word of ["Wanted", "In library"]) {
      const b = chipButton("", false, () => { status = status === word ? null : word; update(); });
      b.dataset.value = word;
      statusBox.append(b);
    }
    for (const name of [...new Set(items.map((i) => i.service_name))].sort((a, b) => a.localeCompare(b, "en-GB"))) {
      const b = chipButton("", false, () => { app = app === name ? null : name; update(); }, ICONS[services.get(name)?.type] || "calendar");
      b.append(el("span"));
      b.dataset.value = name;
      $("#app-filters").append(b);
    }
  }
  for (const b of statusBox.children) {
    const n = items.filter((i) => statusWord(i) === b.dataset.value && (!app || i.service_name === app)).length;
    b.textContent = `${b.dataset.value}, ${n}`;
    b.setAttribute("aria-pressed", String(status === b.dataset.value));
  }
  for (const b of $("#app-filters").children) {
    const n = items.filter((i) => i.service_name === b.dataset.value && (!status || statusWord(i) === status)).length;
    b.lastChild.textContent = `${b.dataset.value}, ${n}`;
    b.setAttribute("aria-pressed", String(app === b.dataset.value));
  }
  $("#app-filters").hidden = $("#app-filters").children.length < 2;
}

function byDay(list) {
  const out = new Map();
  for (const i of list) {
    const key = dayKey(new Date(i.when));
    if (!out.has(key)) out.set(key, []);
    out.get(key).push(i);
  }
  return out;
}

// List view ----------------------------------------------------------------

function itemRow(i) {
  const { title, sub } = describe(i);
  const button = el("button", { type: "button", onclick: () => openItem(i, button) }, title);
  return el("li", { class: "row row--opens" },
    cover(i, "cover--row"),
    el("div", {}, el("div", { class: "row__title" }, button),
      el("div", { class: "row__meta", text: [sub, hasTime(i) ? timeOf(i) : "", i.service_name].filter(Boolean).join(" · ") })),
    el("div", { class: "row__side" }, chip(statusWord(i), i.have ? "success" : "neutral")));
}

function renderList(list) {
  return [...byDay(list)].map(([key, dayItems]) => {
    const id = `d-${key}`;
    return el("section", { class: "media-section", "aria-labelledby": id },
      el("h2", { class: "group-heading", id, text: dayHeading(new Date(dayItems[0].when)) }),
      el("ul", { class: "rows" }, dayItems.map(itemRow)));
  });
}

// Calendar view --------------------------------------------------------------

// One table per month, weeks from Monday. Days outside the window are greyed out.
function renderCalendar(list) {
  const groups = byDay(list);
  const first = startOfToday();
  first.setDate(first.getDate() - 1);
  const last = startOfToday();
  last.setDate(last.getDate() + days);
  const todayKey = dayKey(startOfToday());
  const months = [];
  for (let m = new Date(first.getFullYear(), first.getMonth(), 1); m <= last; m = new Date(m.getFullYear(), m.getMonth() + 1, 1)) {
    const name = m.toLocaleDateString("en-GB", { month: "long", year: "numeric" });
    const id = `m-${m.getFullYear()}-${m.getMonth() + 1}`;
    const inMonth = list.filter((i) => { const d = new Date(i.when); return d.getFullYear() === m.getFullYear() && d.getMonth() === m.getMonth(); }).length;
    const start = new Date(m);
    start.setDate(1 - ((m.getDay() + 6) % 7)); // back to Monday
    const rows = [];
    for (let d = new Date(start); d.getMonth() === m.getMonth() || d < m; ) {
      const cells = [];
      const weekStart = new Date(d);
      for (let w = 0; w < 7; w++, d.setDate(d.getDate() + 1)) cells.push(dayCell(new Date(d), m, first, last, groups, todayKey));
      // Only weeks with a day inside the window: no rows of greyed-out days after it ends.
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekEnd.getDate() + 6);
      if (weekEnd >= first && weekStart <= last) rows.push(el("tr", {}, cells));
    }
    months.push(el("section", { class: "media-section calendar-month", "aria-labelledby": id },
      el("h2", { class: "group-heading", id, text: `${name} · ${releases(inMonth)}` }),
      el("table", { class: "calendar" },
        el("caption", { class: "visually-hidden", text: `Releases in ${name}` }),
        el("thead", {}, el("tr", {}, WEEKDAYS.map((w) => el("th", { scope: "col" }, el("span", { class: "calendar__long", text: w }), el("abbr", { class: "calendar__short", title: w, text: w.slice(0, 3) }))))),
        el("tbody", {}, rows))));
  }
  return months;
}

function dayCell(d, month, first, last, groups, todayKey) {
  const key = dayKey(d);
  const dayItems = groups.get(key) || [];
  const outside = d.getMonth() !== month.getMonth();
  const cell = el("td", { "data-label": dayHeading(d) });
  if (outside || d < first || d > last) cell.dataset.outside = "";
  if (key === todayKey) cell.setAttribute("aria-current", "date");
  cell.append(el("span", { class: "calendar__day numeric", text: String(d.getDate()) }));
  if (outside || !dayItems.length) {
    cell.dataset.empty = "";
    return cell;
  }
  const words = dayHeading(d);
  const { title } = describe(dayItems[0]);
  const button = el("button", { type: "button", class: "btn btn--compact calendar__open", onclick: () => openDay(d, dayItems, button) },
    releases(dayItems.length), el("span", { class: "visually-hidden", text: ` on ${words}` }));
  cell.append(
    el("div", { class: "calendar__covers" }, dayItems.slice(0, 3).map((i) => cover(i, "cover--mini"))),
    el("div", { class: "calendar__titles small clamp-2", text: dayItems.length > 1 ? `${title} and ${dayItems.length - 1} more` : title }),
    button);
  return cell;
}

function openDay(d, dayItems, opener) {
  const wanted = dayItems.filter((i) => !i.have).length;
  sidePanel({
    title: d.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" }), opener,
    body: [
      el("p", { class: "small muted", text: `${releases(dayItems.length)} · ${wanted} wanted` }),
      el("ul", { class: "rows" }, dayItems.map((i) => {
        const { title, sub } = describe(i);
        const svc = services.get(i.service_name);
        return el("li", { class: "row" },
          cover(i, "cover--row"),
          el("div", {}, el("div", { class: "row__title", text: title }),
            el("div", { class: "row__meta", text: [sub, hasTime(i) ? timeOf(i) : "", i.service_name].filter(Boolean).join(" · ") }),
            el("div", { class: "actions" }, chip(statusWord(i), i.have ? "success" : "neutral"),
              svc?.link ? el("a", { class: "btn", href: `${reachableUrl(svc.link)}/calendar`, target: "_blank", rel: "noopener noreferrer" },
                icon("external-link"), `Open in ${i.service_name}`, el("span", { class: "visually-hidden", text: " (opens in a new tab)" })) : null)));
      })),
    ],
  });
}

// Both views ---------------------------------------------------------------

function renderDays() {
  const root = $("#calendar");
  const list = shown();
  root.dataset.view = view;
  root.replaceChildren(...(view === "calendar" ? renderCalendar(list) : renderList(list)));
  const ahead = days === 7 ? "this week" : `the next ${days} days`;
  if (!list.length) {
    const empty = el("p", { class: "empty", text: items.length
      ? "Nothing matches these filters. Turn a filter off to see more."
      : `Nothing is due in ${ahead}. New episodes, films, albums and books from your apps appear here.` });
    if (view === "calendar") root.prepend(empty); else root.append(empty);
  }
  const wanted = list.filter((i) => !i.have).length;
  $("#calendar-summary").textContent = list.length
    ? `${releases(list.length)} in ${ahead} · ${wanted} wanted · ${list.length - wanted} already in the library`
    : `Nothing due in ${ahead}.`;
}

function update() {
  renderFilters();
  renderDays();
}

// The switch changes the view at once, then saves it as the setting in Settings, General.
async function chooseView(next) {
  view = next;
  renderDays();
  try {
    await api("/api/config/general", { method: "PUT", body: { upcoming_view: next } });
  } catch (e) {
    toast(`The view changed here but was not saved: ${e.message}`);
  }
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
        cover(i),
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
    days = cfg.upcoming_days || 14;
    view = cfg.upcoming_view === "calendar" ? "calendar" : "list";
    $$("#view input").forEach((r) => {
      r.checked = r.value === view;
      r.addEventListener("change", () => chooseView(r.value));
    });
    // The API starts yesterday, so last night's episode that is still wanted shows too.
    const yesterday = startOfToday();
    yesterday.setDate(yesterday.getDate() - 1);
    const end = startOfToday();
    end.setDate(end.getDate() + days + 1);
    items = data.items.filter((i) => new Date(i.when) >= yesterday && new Date(i.when) < end);
    $("#calendar-errors").replaceChildren(...data.errors.map((e) => notice("warning", "", e.message)));
    update();
  } catch (e) {
    $("#calendar-summary").textContent = e.message;
  }
});
