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

async function searchLibrary(q) {
  libAsked = q;
  const box = $("#lib-found");
  if (q.length < 2) { box.hidden = true; return; }
  const data = await api(`/api/library/search?q=${encodeURIComponent(q)}`);
  if (libAsked !== q || legacyMode) return;
  const total = data.library.reduce((n, g) => n + g.count, 0);
  box.replaceChildren(el("h2", { id: "found-h", text: total ? `In your library, ${total.toLocaleString("en-GB")}` : "In your library" }),
    ...(total ? data.library.map((g) => el("section", { class: "lib-search-group", "aria-label": g.label, "data-kind": g.tab },
      el("h3", {}, g.label, " ", el("span", { class: "muted", text: `(${g.count.toLocaleString("en-GB")})` })),
      el("ul", { class: "rows" }, ...g.items.map((c) => el("li", { class: "row row--opens lib-row" },
        smallCover(c.poster, c.title),
        el("div", {}, el("h4", { class: "row__title" }, el("a", { href: `/${KIND_ITEM[g.tab]}?id=${c.id}`, text: c.title })),
          el("div", { class: "row__meta", text: [c.meta, c.count].filter(Boolean).join(" · ") })),
        el("div", { class: "row__side" }, c.status ? chip(c.status, c.tone) : null)))),
      g.count > g.items.length ? el("a", { href: `/${KIND_PAGE[g.tab]}?q=${encodeURIComponent(q)}`, text: `See all ${g.count.toLocaleString("en-GB")} in ${g.label}` }) : null))
      : [el("p", { class: "muted", text: `Nothing in your library matches "${q}".` })]));
  box.hidden = false;
  $("#lib-start").hidden = true;
  applyFilters();
  return total;
}

const LOOK_KINDS = [["films", "Films"], ["tv", "TV"], ["books", "Books"], ["music", "Music"], ["radio", "Radio"]];

function lookupRow(kind, r) {
  const action = el("button", { type: "button", class: "btn" }, icon(kind === "radio" ? "radio" : "plus"), kind === "radio" ? "Follow" : "Add",
    el("span", { class: "visually-hidden", text: ` ${r.title}` }));
  action.addEventListener("click", () => addPanel(r, action));
  return el("li", { class: "row lib-row" }, smallCover(r.image, r.title),
    el("div", {}, el("h4", { class: "row__title", text: r.year ? `${r.title} (${r.year})` : r.title }),
      el("div", { class: "row__meta", text: r.detail || "" }),
      r.overview ? el("p", { class: "small muted clamp-2 result-overview", text: r.overview }) : null),
    el("div", { class: "row__side" }, action));
}

// Each kind is asked for on its own and shown when it arrives, in a fixed order, so nothing jumps about.
async function lookupReelix(q) {
  lookAsked = q;
  const box = $("#lookup");
  if (q.length < 3) { box.hidden = true; return; }
  box.hidden = false;
  box.setAttribute("aria-busy", "true");
  const heading = el("h2", { text: "Not in your library" });
  const status = el("p", { class: "muted", text: `Looking for "${q}"…` });
  const slots = LOOK_KINDS.map(([kind]) => el("div", { class: "lib-search-group", "data-kind": kind }));
  box.replaceChildren(heading, status, ...slots);
  let found = 0;
  await Promise.all(LOOK_KINDS.map(async ([kind, label], n) => {
    try {
      const data = await api(`/api/library/lookup?q=${encodeURIComponent(q)}&kind=${kind}`);
      if (lookAsked !== q || legacyMode) return;
      const items = data.groups[0]?.items || [];
      found += items.length;
      slots[n].replaceChildren(...data.errors.map((err) => el("p", { class: "small muted" }, icon("info", 16), " ", err.message)),
        ...(items.length ? [el("h3", { text: label }), el("ul", { class: "rows" }, ...items.map((r) => lookupRow(kind, r)))] : []));
    } catch (e) {
      if (lookAsked === q) slots[n].replaceChildren(el("p", { class: "small muted" }, icon("info", 16), " ", `${label}: ${e.message}`));
    }
  }));
  if (lookAsked !== q) return;
  applyFilters();
  heading.textContent = found ? `Not in your library, ${found}` : "Not in your library";
  status.textContent = found ? "" : `Reelix found nothing else for "${q}". Check the spelling or try fewer words.`;
  status.hidden = !found ? false : true;
  box.setAttribute("aria-busy", "false");
  if (legacyMode) box.hidden = true;
  announce(`${found} found that are not in your library`);
}

// Filters on the results (owner, 10 November 2026, DASH-301): where (in your library or not) and which kind. Kept in
// this browser; they hide groups, nothing is searched again.
const FILTER_KEY = "starboard.search-filters";
const FILTER_KINDS = [["all", "Everything"], ["films", "Films"], ["tv", "Series"], ["music", "Music"], ["radio", "Radio"],
  ["books", "Books"], ["audiobooks", "Audiobooks"]];
let searchFilter = { where: "all", kind: "all" };
try { searchFilter = { ...searchFilter, ...JSON.parse(localStorage.getItem(FILTER_KEY) || "{}") }; } catch { searchFilter = { where: "all", kind: "all" }; }

function saveFilter() {
  try { localStorage.setItem(FILTER_KEY, JSON.stringify(searchFilter)); } catch { /* a private window keeps it until reload */ }
}

function applyFilters() {
  const show = (node, on) => { if (node) node.classList.toggle("is-filtered", !on); };
  const bar = $("#search-filters");
  if (bar) bar.hidden = !$("#q").value.trim();
  show($("#lib-found"), searchFilter.where !== "out");
  show($("#lookup"), searchFilter.where !== "in");
  $$("#lib-found [data-kind], #lookup [data-kind]").forEach((g) => {
    const k = g.dataset.kind;
    show(g, searchFilter.kind === "all" || k === searchFilter.kind || (searchFilter.kind === "audiobooks" && k === "books" && !!g.closest("#lookup")));
  });
}

function filterBar() {
  const where = el("fieldset", { class: "segmented" }, el("legend", { class: "visually-hidden", text: "Show" }),
    ...[["all", "All"], ["in", "In your library"], ["out", "Not in your library"]].map(([v, t]) => el("label", {},
      el("input", { type: "radio", name: "sf-where", value: v, checked: searchFilter.where === v }), el("span", { text: t }))));
  // One kind of seven at a time (DASH-309, R4): more than five choices, so a labelled select, not chips that undo
  // each other. Both sit in the page's toolbar, after the search box (R8), not in a bar of their own.
  const kinds = el("select", { class: "select", id: "sf-kind", "aria-label": "Kind" },
    FILTER_KINDS.map(([v, t]) => el("option", { value: v, text: t, selected: searchFilter.kind === v })));
  kinds.addEventListener("change", () => { searchFilter.kind = kinds.value; saveFilter(); applyFilters(); });
  where.addEventListener("change", (e) => { searchFilter.where = e.target.value; saveFilter(); applyFilters(); });
  return el("div", { id: "search-filters", class: "toolbar__row", hidden: true }, where, el("div", { class: "field" }, kinds));
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
  $("#kind-filters").before(filterBar());
  $("#q").addEventListener("input", applyFilters);
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
