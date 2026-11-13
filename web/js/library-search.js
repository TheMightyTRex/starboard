// Search (DASH-162): opens on what you already have (recently added, then each kind with its count), searches your
// library first as you type, then shows what Reelix finds under "Not in your library", with Add, or Follow for radio.
// Without Reelix, the page falls back to searching Sonarr, Radarr, Lidarr and Readarr (search.js).

const KIND_PAGE = { films: "library-films.html", tv: "library-tv.html", music: "library-music.html", radio: "library-radio.html",
  books: "library-books.html", audiobooks: "library-audiobooks.html" };
const KIND_ITEM = { films: "library-film.html", tv: "library-tv-show.html", music: "library-artist.html", radio: "library-radio-show.html",
  books: "library-book.html", audiobooks: "library-audiobook.html" };
const KIND_NAME = { films: ["film", "films"], tv: ["series", "series"], music: ["artist", "artists"], radio: ["show", "shows"],
  books: ["book", "books"], audiobooks: ["audiobook", "audiobooks"] };
let libTyping = 0;
let lookTyping = 0;
let lookAsked = "";
let libAsked = "";
let legacyMode = false; // no Reelix: search.js searches the apps instead

const nCount = (n, [one, many]) => `${n.toLocaleString("en-GB")} ${n === 1 ? one : many}`;

async function drawStart() {
  const box = $("#lib-start");
  const data = await api("/api/library/overview");
  const recent = data.recent.length ? el("section", { class: "media-section", "aria-labelledby": "recent-h" },
    el("h2", { id: "recent-h", text: "Recently added" }),
    el("ul", { class: "media-grid lib-recent", "data-size": "small" }, ...data.recent.slice(0, 8).map((c) => el("li", { class: "media-card lib-card" },
      smallCover(c.poster, c.title, "cover"),
      el("span", { class: "media-card__title" }, el("a", { href: `/${KIND_ITEM[c.tab]}?id=${c.id}`, text: c.title })),
      el("span", { class: "media-card__meta", text: c.meta || "" }))))) : null;
  const kinds = el("section", { class: "media-section", "aria-labelledby": "kinds-h" },
    el("h2", { id: "kinds-h", text: "Your library" }),
    el("ul", { class: "lib-kinds" }, ...data.tabs.map((t) => el("li", {},
      el("a", { href: `/${KIND_PAGE[t.tab]}` }, el("span", { text: t.label }),
        el("strong", { text: t.count === null ? "Reading…" : nCount(t.count, KIND_NAME[t.tab]) }))))));
  box.replaceChildren(...[recent, kinds].filter(Boolean));
  box.hidden = false;
  // Kinds still being read fill in a few seconds later.
  if (data.tabs.some((t) => t.count === null) && !$("#q").value.trim()) setTimeout(() => drawStart().catch(() => {}), 4000);
}

// Results, kept so the filters can draw them again without asking anything (DASH-301, lightweight rule).
let libGroups = [];   // [{tab, label, count, items}] from the Library, each item with its facts (fx)
let lookFound = {};   // kind: [rows] from Reelix's lookups
let lookErrors = {};  // kind: [messages]
let lookDone = false;
const expanded = new Set();  // groups shown in full after Show all
const SHOW_FIRST = 8;

function libRow(g, c) {
  return el("li", { class: "row row--opens lib-row" },
    smallCover(c.poster, c.title),
    el("div", {}, el("h4", { class: "row__title" }, el("a", { href: `/${KIND_ITEM[g.tab]}?id=${c.id}`, text: c.title })),
      el("div", { class: "row__meta", text: [c.meta, c.count].filter(Boolean).join(" · ") })),
    el("div", { class: "row__side" }, c.status ? chip(c.status, c.tone) : null));
}

// "Show all 23": the rest of a group, here, with the same filters; focus goes to the first one added.
function showAllButton(id, n, label, onShow) {
  const b = el("button", { type: "button", class: "btn btn--quiet", id }, `Show all ${n.toLocaleString("en-GB")} in ${label}`);
  b.addEventListener("click", onShow);
  return el("div", { class: "load-more" }, b);
}

function drawFound() {
  const box = $("#lib-found");
  const q = libAsked;
  if (!q || q.length < 2) return;
  const total = libGroups.reduce((n, g) => n + g.count, 0);
  const parts = [];
  let shownAll = 0;
  for (const g of libGroups) {
    const items = g.items.filter((c) => passes(c, "in", g.tab));
    if (!items.length) continue;
    shownAll += items.length;
    const full = expanded.has(`in-${g.tab}`);
    const list = el("ul", { class: "rows" }, ...(full ? items : items.slice(0, SHOW_FIRST)).map((c) => libRow(g, c)));
    parts.push(el("section", { class: "lib-search-group", "aria-label": g.label, "data-kind": g.tab },
      el("h3", {}, g.label, " ", el("span", { class: "muted", text: `(${items.length.toLocaleString("en-GB")})` })),
      list,
      !full && items.length > SHOW_FIRST ? showAllButton(`lib-all-${g.tab}`, items.length, g.label, () => {
        expanded.add(`in-${g.tab}`);
        drawFound();
        $(`#lib-found [data-kind="${g.tab}"] .rows > li:nth-child(${SHOW_FIRST + 1}) a`)?.focus();
      }) : null,
      g.count > g.items.length ? el("a", { href: `/${KIND_PAGE[g.tab]}?q=${encodeURIComponent(q)}`, text: `See all ${g.count.toLocaleString("en-GB")} in ${g.label}` }) : null));
  }
  const heading = shownAll ? `In your library, ${shownAll.toLocaleString("en-GB")}` : "In your library";
  box.replaceChildren(el("h2", { id: "found-h", text: heading }),
    ...(parts.length ? parts : [el("p", { class: "muted", text: total ? "Nothing in your library matches these filters." : `Nothing in your library matches "${q}".` })]));
  box.classList.toggle("is-filtered", filters.where === "out");
}

async function searchLibrary(q) {
  libAsked = q;
  const box = $("#lib-found");
  if (q.length < 2) { box.hidden = true; return; }
  const data = await api(`/api/library/search?q=${encodeURIComponent(q)}`);
  if (libAsked !== q || legacyMode) return;
  libGroups = data.library;
  [...expanded].filter((k) => k.startsWith("in-")).forEach((k) => expanded.delete(k));
  drawFound();
  box.hidden = false;
  $("#lib-start").hidden = true;
  drawFilters();
  return libGroups.reduce((n, g) => n + g.count, 0);
}

const LOOK_KINDS = [["films", "Films"], ["tv", "TV"], ["books", "Books"], ["music", "Music"], ["radio", "Radio"]];

function lookupRow(kind, r) {
  if (r.added) {
    return el("li", { class: "row lib-row" }, smallCover(r.image, r.title),
      el("div", {}, el("h4", { class: "row__title", text: r.year ? `${r.title} (${r.year})` : r.title }), el("div", { class: "row__meta", text: r.detail || "" })),
      el("div", { class: "row__side" }, chip(kind === "radio" ? "Following" : "Added", "success")));
  }
  const action = el("button", { type: "button", class: "btn" }, icon(kind === "radio" ? "radio" : "plus"), kind === "radio" ? "Follow" : "Add",
    el("span", { class: "visually-hidden", text: ` ${r.title}` }));
  action.addEventListener("click", () => addPanel(r, action));
  return el("li", { class: "row lib-row" }, smallCover(r.image, r.title),
    el("div", {}, el("h4", { class: "row__title", text: r.year ? `${r.title} (${r.year})` : r.title }),
      el("div", { class: "row__meta", text: r.detail || "" }),
      r.overview ? el("p", { class: "small muted clamp-2 result-overview", text: r.overview }) : null),
    el("div", { class: "row__side" }, action));
}

function drawLookSlot(kind, label) {
  const slot = $(`#lookup .lib-search-group[data-kind="${kind}"]`);
  if (!slot) return 0;
  const items = (lookFound[kind] || []).filter((r) => passes(r, "out", kind));
  const full = expanded.has(`out-${kind}`);
  slot.replaceChildren(...(lookErrors[kind] || []).map((m) => el("p", { class: "small muted" }, icon("info", 16), " ", m)),
    ...(items.length ? [el("h3", { text: label }), el("ul", { class: "rows" }, ...(full ? items : items.slice(0, SHOW_FIRST)).map((r) => lookupRow(kind, r))),
      !full && items.length > SHOW_FIRST ? showAllButton(`look-all-${kind}`, items.length, label, () => {
        expanded.add(`out-${kind}`);
        drawLookSlot(kind, label);
        $(`#lookup [data-kind="${kind}"] .rows > li:nth-child(${SHOW_FIRST + 1}) h4`)?.setAttribute("tabindex", "-1");
        $(`#lookup [data-kind="${kind}"] .rows > li:nth-child(${SHOW_FIRST + 1}) h4`)?.focus();
      }) : null] : []));
  return items.length;
}

function drawLookup() {
  const box = $("#lookup");
  if (!box || box.hidden) return;
  let found = 0;
  for (const [kind, label] of LOOK_KINDS) found += drawLookSlot(kind, label);
  const all = Object.values(lookFound).reduce((n, list) => n + list.length, 0);
  const heading = $("#lookup > h2");
  if (heading && lookDone) heading.textContent = found ? `Not in your library, ${found}` : "Not in your library";
  const status = $("#lookup-status");
  if (status && lookDone) {
    status.hidden = !!found;
    status.textContent = all ? "Nothing Reelix found matches these filters." : `Reelix found nothing else for "${lookAsked}". Check the spelling or try fewer words.`;
  }
  box.classList.toggle("is-filtered", filters.where === "in");
}

// Each kind is asked for on its own and shown when it arrives, in a fixed order, so nothing jumps about.
async function lookupReelix(q) {
  lookAsked = q;
  const box = $("#lookup");
  if (q.length < 3) { box.hidden = true; return; }
  box.hidden = false;
  box.setAttribute("aria-busy", "true");
  lookFound = {};
  lookErrors = {};
  lookDone = false;
  [...expanded].filter((k) => k.startsWith("out-")).forEach((k) => expanded.delete(k));
  box.replaceChildren(el("h2", { text: "Not in your library" }), el("p", { class: "muted", id: "lookup-status", text: `Looking for "${q}"…` }),
    ...LOOK_KINDS.map(([kind]) => el("div", { class: "lib-search-group", "data-kind": kind })));
  await Promise.all(LOOK_KINDS.map(async ([kind, label]) => {
    try {
      const data = await api(`/api/library/lookup?q=${encodeURIComponent(q)}&kind=${kind}`);
      if (lookAsked !== q || legacyMode) return;
      lookFound[kind] = data.groups[0]?.items || [];
      lookErrors[kind] = data.errors.map((err) => err.message);
    } catch (e) {
      if (lookAsked !== q) return;
      lookErrors[kind] = [`${label}: ${e.message}`];
    }
    drawLookSlot(kind, label);
  }));
  if (lookAsked !== q) return;
  lookDone = true;
  drawLookup();
  drawFilters();
  box.setAttribute("aria-busy", "false");
  if (legacyMode) box.hidden = true;
  const shown = LOOK_KINDS.reduce((n, [kind]) => n + (lookFound[kind] || []).filter((r) => passes(r, "out", kind)).length, 0);
  announce(`${shown} found that are not in your library`);
}

// Filters on the results (owner, 10 November 2026, DASH-301). Where and kind in the toolbar's first row; the rest
// under More filters: year or decade, genre, status in your library, released or coming soon, followed or not,
// language, rating and, for radio, the source. They combine; each choice shows how many it would leave (counted with
// the other filters on); a filter with nothing to tell apart is left out. Remembered for the account on the server.
// Books and Audiobooks in the kind list are the ebook or audiobook filter. Nothing is searched again.
const FILTER_KINDS = [["all", "Everything"], ["films", "Films"], ["tv", "Series"], ["music", "Music"], ["radio", "Radio"],
  ["books", "Books"], ["audiobooks", "Audiobooks"]];
const NO_FILTERS = { where: "all", kind: "all", decade: "", genre: "", status: [], release: "", followed: "", language: "", rating: "", source: "", more: false };
let filters = { ...NO_FILTERS, status: [] };
const STATUS_WORDS = [["have", "Have it"], ["missing", "Missing"], ["downloading", "Downloading"], ["below", "Below the quality wanted"]];
const languageName = (() => {
  let names = null;
  try { names = new Intl.DisplayNames(["en-GB"], { type: "language" }); } catch { names = null; }
  return (code) => { try { return (names && names.of(code)) || code.toUpperCase(); } catch { return code.toUpperCase(); } };
})();
const decadeOf = (y) => `${Math.floor(Number(y) / 10) * 10}s`;
// One-of-several facets: what each item says for it.
const FACETS = {
  decade: { label: "Year", any: "Any year", of: (fx) => (fx.y ? [decadeOf(fx.y)] : []), sort: (a, b) => b.localeCompare(a) },
  genre: { label: "Genre", any: "Any genre", of: (fx) => fx.g || [] },
  release: { label: "Released", of: (fx) => (fx.r ? [fx.r] : []) },
  followed: { label: "Followed", of: (fx) => [fx.fo ? "yes" : "no"] },
  language: { label: "Language", any: "Any language", of: (fx) => (fx.la ? [fx.la] : []), words: languageName },
  rating: { label: "Rating", any: "Any rating", of: (fx) => (fx.ce ? [fx.ce] : []) },
  source: { label: "Radio source", any: "Any source", of: (fx) => (fx.so ? [fx.so] : []) },
};
const extraOn = () => Object.keys(FACETS).filter((k) => filters[k]).length + (filters.status.length ? 1 : 0);

function kindOk(kind, where) {
  const k = filters.kind;
  return k === "all" || k === kind || (k === "audiobooks" && kind === "books" && where === "out");
}

// Does an item pass every filter (leaving out one, to count that one's choices)?
function passes(item, where, kind, skip = "") {
  if (skip !== "where" && filters.where !== "all" && filters.where !== where) return false;
  if (skip !== "kind" && !kindOk(kind, where)) return false;
  const fx = item.fx || {};
  for (const [key, f] of Object.entries(FACETS)) {
    if (key !== skip && filters[key] && !f.of(fx).includes(filters[key])) return false;
  }
  if (skip !== "status" && filters.status.length && !filters.status.some((s) => (fx.s || []).includes(s))) return false;
  return true;
}

function everything() {
  return [...libGroups.flatMap((g) => g.items.map((item) => ({ item, where: "in", kind: g.tab }))),
    ...Object.entries(lookFound).flatMap(([kind, list]) => list.map((item) => ({ item, where: "out", kind })))];
}

function tally(key, of) {
  const out = new Map();
  for (const x of everything()) {
    if (!passes(x.item, x.where, x.kind, key)) continue;
    for (const v of of(x)) out.set(v, (out.get(v) || 0) + 1);
  }
  return out;
}

function valuesOf(f) {
  const out = new Set();
  for (const x of everything()) for (const v of f.of(x.item.fx || {})) out.add(v);
  return out;
}

let saveTimer = 0;
function saveFilters() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => api("/api/library/search-filters", { method: "POST", body: { filters } }).catch(() => { /* kept on this page until it is left */ }), 400);
}

function changed() {
  saveFilters();
  drawFound();
  drawLookup();
  drawFilters();
  const shown = everything().filter((x) => passes(x.item, x.where, x.kind)).length;
  const all = everything().length;
  announce(shown === all ? `${shown} shown` : `${shown} of ${all} shown`);
}

// A short visible name before a group of chips or a segmented control in More filters; screen readers hear the
// group's own name (its legend or aria-label), so this one is not read twice.
function labelled(words, control) {
  return el("div", { class: "search-filter-group" }, el("span", { class: "search-filter-group__label", "aria-hidden": "true", text: words }), control);
}

function labelledSelect(id, label, options, value, onChange) {
  const select = el("select", { class: "select", id }, options.map(([v, t]) => el("option", { value: v, text: t, selected: v === value })));
  select.addEventListener("change", () => onChange(select.value));
  return el("div", { class: "field lib-field" }, el("label", { class: "visually-hidden", for: id, text: label }), select);
}

// Drawn again after each change, as the counts change; focus goes back to the control that had it (same ids).
function drawFilters() {
  const bar = $("#search-filters");
  if (!bar) return;
  const had = document.activeElement && bar.contains(document.activeElement) ? document.activeElement.id : "";
  const where = tally("where", (x) => [x.where]);
  const kinds = tally("kind", (x) => (x.kind === "books" && x.where === "out" ? ["books", "audiobooks"] : [x.kind]));
  const kindTotal = [...everything()].filter((x) => passes(x.item, x.where, x.kind, "kind")).length;
  const first = [
    segmentedFilter({ name: "sf-where", label: "Show", value: filters.where,
      options: [["all", "All", (where.get("in") || 0) + (where.get("out") || 0)], ["in", "In your library", where.get("in") || 0], ["out", "Not in your library", where.get("out") || 0]],
      onChange: (v) => { filters.where = v; changed(); } }),
    labelledSelect("sf-kind", "Kind", FILTER_KINDS.map(([v, t]) => [v, `${t} ${(v === "all" ? kindTotal : kinds.get(v) || 0).toLocaleString("en-GB")}`]),
      filters.kind, (v) => { filters.kind = v; changed(); }),
  ];
  const on = extraOn();
  const more = el("button", { type: "button", class: "btn", id: "sf-more", "aria-expanded": String(!!filters.more), "aria-controls": "sf-more-row" },
    icon("sliders-horizontal"), on ? `More filters, ${on} on` : "More filters");
  more.addEventListener("click", () => { filters.more = !filters.more; saveFilters(); drawFilters(); $("#sf-more")?.focus(); });
  // The rest, each only when the results have something to tell apart (or it is on, so it can be taken off).
  const rest = [];
  for (const key of ["decade", "genre", "language", "rating", "source"]) {
    const f = FACETS[key];
    const counts = tally(key, (x) => f.of(x.item.fx || {}));
    const known = valuesOf(f);  // every value in the results, so the list does not change as other filters change
    if (known.size < 2 && !filters[key]) continue;
    const values = [...known].sort(f.sort || ((a, b) => String(f.words ? f.words(a) : a).localeCompare(String(f.words ? f.words(b) : b))));
    if (filters[key] && !known.has(filters[key])) values.push(filters[key]);
    rest.push(labelledSelect(`sf-${key}`, f.label, [["", f.any], ...values.map((v) => [v, `${f.words ? f.words(v) : v} ${(counts.get(v) || 0).toLocaleString("en-GB")}`])],
      filters[key], (v) => { filters[key] = v; changed(); }));
  }
  const status = tally("status", (x) => x.item.fx?.s || []);
  if (valuesOf({ of: (fx) => fx.s || [] }).size || filters.status.length) {
    rest.push(labelled("Status", el("div", { class: "filter-chips", role: "group", "aria-label": "Status in your library" }, STATUS_WORDS.map(([v, words]) => {
      const pressed = filters.status.includes(v);
      const b = el("button", { type: "button", class: "filter-chip", id: `sf-status-${v}`, "aria-pressed": String(pressed), "data-ready": "1" },
        `${words} ${(status.get(v) || 0).toLocaleString("en-GB")}`);
      b.addEventListener("click", () => {
        filters.status = pressed ? filters.status.filter((x) => x !== v) : [...filters.status, v];
        changed();
      });
      return b;
    }))));
  }
  for (const [key, choices] of [["release", [["", "All"], ["released", "Released"], ["coming", "Coming soon"]]],
    ["followed", [["", "All"], ["yes", "Followed"], ["no", "Not followed"]]]]) {
    const counts = tally(key, (x) => FACETS[key].of(x.item.fx || {}));
    if (valuesOf(FACETS[key]).size < 2 && !filters[key]) continue;
    const all = everything().filter((x) => passes(x.item, x.where, x.kind, key)).length;
    rest.push(labelled(FACETS[key].label, segmentedFilter({ name: `sf-${key}`, label: FACETS[key].label, value: filters[key],
      options: choices.map(([v, t]) => [v, t, v ? counts.get(v) || 0 : all]), onChange: (v) => { filters[key] = v || ""; changed(); } })));
  }
  if (on) {
    const clear = el("button", { type: "button", class: "btn btn--quiet", id: "sf-clear" }, icon("x"), "Clear these filters");
    clear.addEventListener("click", () => {
      filters = { ...filters, decade: "", genre: "", status: [], release: "", followed: "", language: "", rating: "", source: "" };
      changed();
      $("#sf-more")?.focus();
    });
    rest.push(clear);
  }
  const row = el("div", { class: "toolbar__row search-more-filters", id: "sf-more-row", hidden: !filters.more },
    ...(rest.length ? rest : [el("p", { class: "small muted", text: "These results have nothing more to filter by." })]));
  bar.replaceChildren(el("div", { class: "toolbar__row" }, ...first, more), row);
  bar.hidden = !$("#q").value.trim();
  const shown = everything().filter((x) => passes(x.item, x.where, x.kind)).length;
  const all = everything().length;
  $("#search-count").textContent = all ? (shown === all ? `${all.toLocaleString("en-GB")} found` : `${shown.toLocaleString("en-GB")} of ${all.toLocaleString("en-GB")} shown`) : "";
  if (had) document.getElementById(had)?.focus();
}

function applyFilters() {
  const bar = $("#search-filters");
  if (bar) bar.hidden = !$("#q").value.trim();
}

function filterBar() {
  return el("div", { id: "search-filters", class: "search-filters", hidden: true });
}

async function loadFilters() {
  try {
    const saved = (await api("/api/library/search-filters")).filters || {};
    filters = { ...NO_FILTERS, ...saved, status: Array.isArray(saved.status) ? saved.status : [] };
  } catch { filters = { ...NO_FILTERS, status: [] }; }
}

function remember(q) {
  const url = new URL(location.href);
  if (q) url.searchParams.set("q", q); else url.searchParams.delete("q");
  history.replaceState(null, "", url);
}

function runBoth(q, now = false) {
  clearTimeout(libTyping);
  clearTimeout(lookTyping);
  remember(q);
  if (!q) {
    $("#lib-found").hidden = true;
    $("#lookup").hidden = true;
    $("#lib-start").hidden = false;
    $("#search-summary").textContent = "Your library first, then what Reelix can add.";
    return;
  }
  libTyping = setTimeout(() => searchLibrary(q).then((n) => {
    if (n !== undefined) { $("#search-summary").textContent = `Results for "${q}"`; if (now) announce(`${n} in your library`); }
  }).catch(() => {}), now ? 0 : 200);
  lookTyping = setTimeout(() => lookupReelix(q), now ? 0 : 900);
}

startPage().then(async () => {
  const q = new URLSearchParams(location.search).get("q") || "";
  const submit = (e) => { if (!legacyMode) { e.preventDefault(); e.stopImmediatePropagation(); runBoth($("#q").value.trim(), true); } };
  const typed = () => { if (!legacyMode) runBoth($("#q").value.trim()); };
  $("#search-form").addEventListener("submit", submit);
  $("#q").addEventListener("input", typed);
  $("#search-form").closest(".toolbar").append(filterBar());
  $("#q").addEventListener("input", applyFilters);
  await loadFilters();
  if (q) { $("#q").value = q; runBoth(q, true); } else $("#q").focus();
  try {
    await drawStart();
    if ($("#q").value.trim()) $("#lib-start").hidden = true;
  } catch (e) {
    if (e.status === 409) { // no Reelix: search the apps as before
      legacyMode = true;
      $("#search-form").removeEventListener("submit", submit);
      $("#lib-found").hidden = true;
      $("#lookup").hidden = true;
      window.legacySearchStart?.();
      return;
    }
    $("#lib-start").replaceChildren(el("p", { class: "field-error", text: e.message }));
    $("#lib-start").hidden = false;
  }
});
