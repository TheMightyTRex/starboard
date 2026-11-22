// Discover by area (owner, 12 November 2026): Films, TV, Music, Radio, Books and Audiobooks, each with its own feeds
// from Reelix as rows of covers. Films and TV have genre chips, Radio its categories; choosing one adds its row at
// the top. A row is asked for only when it comes into view (lightweight rule). Each cover says In your library or
// Wanted, or has Add (Follow for radio), the same slide-out as Search.

const D = document.querySelector("[data-discover]");
const D_TAB = D?.dataset.discover;
const D_WORDS = { films: "films", tv: "series", music: "artists", radio: "shows", books: "books", audiobooks: "audiobooks" };

function dCard(c) {
  const kindWord = c.kind === "radio" ? "Follow" : "Add";
  let side;
  if (c.state === "have") side = chip(...STATUS.inLibrary);
  else if (c.state === "wanted") side = chip(...STATUS.wanted);
  else {
    side = el("button", { type: "button", class: "btn btn--compact" }, icon(c.kind === "radio" ? "radio" : "plus"), kindWord,
      el("span", { class: "visually-hidden", text: ` ${c.title}` }));
    side.addEventListener("click", () => addPanel(c, side));
  }
  return el("li", { class: "discover-card" }, smallCover(c.image, c.title, "cover discover-card__cover"),
    el("h3", { class: "discover-card__title", text: c.title }),
    el("p", { class: "discover-card__meta", text: [c.year, c.detail].filter(Boolean).join(" · ") }),
    el("div", { class: "discover-card__action" }, side));
}

// Filters on the rows (DASH-301; owner, 10 November 2026: "on Search and Discover results, filters"): Show (all, in
// your library, not in your library), year by decade, released or not, and language, with counts, in the page's
// toolbar. They combine and act on every row at once; the choice is remembered for the account on the server, the
// same on each Discover page. Nothing is asked again (lightweight rule): the cards already loaded are hidden or
// shown, and a row that loads later is filtered as it arrives, so the counts are for the rows loaded so far.
const D_NO_FILTERS = { where: "all", decade: "", release: "", language: "" };
let dFilters = { ...D_NO_FILTERS };
let dLoaded = []; // each row loaded so far: { list, items }
const dDecade = (c) => (c.year ? `${Math.floor(Number(c.year) / 10) * 10}s` : "");
const D_FACETS = { where: (c) => (c.state ? "in" : "out"), decade: dDecade, release: (c) => c.fx?.r || "", language: (c) => c.fx?.la || "" };
const dLanguage = (() => {
  let names = null;
  try { names = new Intl.DisplayNames(["en-GB"], { type: "language" }); } catch { names = null; }
  return (code) => { try { return (names && names.of(code)) || code.toUpperCase(); } catch { return code.toUpperCase(); } };
})();

// Does a card pass every filter (leaving out one, to count that one's choices)?
function dPasses(c, skip = "") {
  for (const [key, of] of Object.entries(D_FACETS)) {
    const want = dFilters[key];
    if (key !== skip && want && want !== "all" && of(c) !== want) return false;
  }
  return true;
}

// A row's cards are hidden or shown; a row with cards but none that pass says so, in the row.
function dFilterRow(row) {
  const cards = row.list.querySelectorAll(".discover-card");
  let any = false;
  row.items.forEach((c, n) => { const ok = dPasses(c); any = any || ok; if (cards[n]) cards[n].hidden = !ok; });
  const note = row.list.querySelector(".discover-none");
  if (!any && !note) row.list.append(el("li", { class: "muted small discover-none", text: "Nothing in this row matches the filters." }));
  else if (any) note?.remove();
}

function dApplyFilters() {
  dLoaded = dLoaded.filter((row) => row.list.isConnected); // a genre row taken away is forgotten
  for (const row of dLoaded) {
    dFilterRow(row);
    row.list.scrollLeft = 0;
    row.list.dispatchEvent(new Event("scroll")); // the shelf's arrows follow what is left
  }
}

let dSaveTimer = 0;
function dChanged() {
  clearTimeout(dSaveTimer);
  dSaveTimer = setTimeout(() => api(`/api/library/discover-filters?tab=${D_TAB}`, { method: "POST", body: { filters: dFilters } }).catch(() => { /* kept on this page until it is left */ }), 400);
  dApplyFilters();
  const [shown, all] = dDrawFilters();
  announce(shown === all ? `${all} shown` : `${shown} of ${all} shown`);
}

// Drawn again after each change and each row that loads, as the counts change; focus goes back to the control that
// had it (the same ids). A filter with nothing to tell apart is left out, unless it is on, so it can be taken off.
function dDrawFilters() {
  const bar = $("#discover-filters");
  const cards = dLoaded.filter((r) => r.list.isConnected).flatMap((r) => r.items);
  const shown = cards.filter((c) => dPasses(c)).length;
  if (!bar) return [shown, cards.length];
  const had = document.activeElement && bar.contains(document.activeElement) ? document.activeElement.id : "";
  const tally = (key) => {
    const out = new Map();
    for (const c of cards) { const v = D_FACETS[key](c); if (v && dPasses(c, key)) out.set(v, (out.get(v) || 0) + 1); }
    return out;
  };
  const known = (key) => new Set(cards.map(D_FACETS[key]).filter(Boolean));
  const total = (key) => cards.filter((c) => dPasses(c, key)).length;
  const select = (key, label, any, words = (v) => v, sort = (a, b) => words(a).localeCompare(words(b))) => {
    const values = [...known(key)].sort(sort);
    if (values.length < 2 && !dFilters[key]) return null;
    if (dFilters[key] && !values.includes(dFilters[key])) values.push(dFilters[key]);
    const counts = tally(key);
    const pick = el("select", { class: "select", id: `df-${key}` }, [["", any], ...values.map((v) => [v, `${words(v)} ${(counts.get(v) || 0).toLocaleString("en-GB")}`])]
      .map(([v, t]) => el("option", { value: v, text: t, selected: v === dFilters[key] })));
    pick.addEventListener("change", () => { dFilters[key] = pick.value; dChanged(); });
    return el("div", { class: "field lib-field" }, el("label", { class: "visually-hidden", for: `df-${key}`, text: label }), pick);
  };
  const where = tally("where"), release = tally("release");
  const on = Object.keys(D_NO_FILTERS).some((k) => dFilters[k] !== D_NO_FILTERS[k]);
  const clear = on ? el("button", { type: "button", class: "btn btn--quiet", id: "df-clear" }, icon("x"), "Clear filters") : null;
  clear?.addEventListener("click", () => { dFilters = { ...D_NO_FILTERS }; dChanged(); $("#df-where-all")?.focus(); });
  bar.replaceChildren(el("div", { class: "toolbar__row" }, ...[
    segmentedFilter({ name: "df-where", label: "Show", value: dFilters.where,
      options: [["all", "All", total("where")], ["in", "In your library", where.get("in") || 0], ["out", "Not in your library", where.get("out") || 0]],
      onChange: (v) => { dFilters.where = v; dChanged(); } }),
    select("decade", "Year", "Any year", (v) => v, (a, b) => b.localeCompare(a)),
    known("release").size > 1 || dFilters.release ? segmentedFilter({ name: "df-release", label: "Released", value: dFilters.release,
      options: [["", "All", total("release")], ["released", "Released", release.get("released") || 0], ["coming", "Not released", release.get("coming") || 0]],
      onChange: (v) => { dFilters.release = v || ""; dChanged(); } }) : null,
    select("language", "Language", "Any language", dLanguage),
    clear,
    el("div", { class: "toolbar__end" }, el("span", { class: "toolbar__count", id: "discover-count",
      text: shown === cards.length ? `${cards.length.toLocaleString("en-GB")} shown` : `${shown.toLocaleString("en-GB")} of ${cards.length.toLocaleString("en-GB")} shown` })),
  ].filter(Boolean)));
  bar.hidden = !cards.length;
  if (had) document.getElementById(had)?.focus();
  return [shown, cards.length];
}

function dRow(r, { open = false } = {}) {
  const list = el("ul", { class: "discover-shelf", "aria-label": r.title }, el("li", { class: "muted small", text: "Loading…" }));
  const sec = el("section", { class: "discover-row", "aria-labelledby": `d-${r.id.replace(/[^a-z0-9]/gi, "-")}` },
    el("div", { class: "discover-row__head" }, el("h2", { id: `d-${r.id.replace(/[^a-z0-9]/gi, "-")}`, text: r.title }),
      r.source ? el("span", { class: "small muted", text: r.source }) : null), shelfScroller(list, r.title));
  const load = async () => {
    try {
      const got = await api(`/api/library/discover-row?tab=${D_TAB}&row=${encodeURIComponent(r.id)}`);
      list.replaceChildren(...(got.items.length ? got.items.map(dCard) : [el("li", { class: "muted small", text: "Nothing here right now." })]));
      if (got.items.length) { const row = { list, items: got.items }; dLoaded.push(row); dFilterRow(row); dDrawFilters(); }
      requestAnimationFrame(() => list.dispatchEvent(new Event("scroll")));  // the shelf shows its arrows now there is more
    } catch (e) { list.replaceChildren(el("li", {}, notice("info", "This row did not load", e.message))); }
  };
  if (open || !("IntersectionObserver" in window)) load();
  else {
    const watch = new IntersectionObserver((seen) => { if (seen.some((s) => s.isIntersecting)) { watch.disconnect(); load(); } }, { rootMargin: "300px" });
    watch.observe(sec);
  }
  return sec;
}

async function startDiscover() {
  const holder = $("#discover-rows");
  let d;
  try { d = await api(`/api/library/discover?tab=${D_TAB}`); }
  catch (e) { holder.removeAttribute("aria-busy"); holder.replaceChildren(notice("danger", "Discover did not load", e.message)); return; }
  holder.removeAttribute("aria-busy");
  dFilters = { ...D_NO_FILTERS, ...(d.filters || {}) };
  const filterBar = el("div", { class: "toolbar" }, el("div", { id: "discover-filters", class: "search-filters", role: "group", "aria-label": "Filter every row", hidden: true }));
  const picked = el("div", { id: "discover-picked" });
  // Genres are filter chips that can be on together (DASH-309, R4), in a toolbar: each genre pressed puts its row at
  // the top, in the chips' order. Focus stays on the chip; the change is said.
  const shownGenres = new Set();
  picked.addEventListener("genres-clear", () => shownGenres.clear());
  const showGenres = () => {
    picked.replaceChildren(...d.genres.filter((g) => shownGenres.has(g)).map((g) => dRow(g, { open: true })));
    dDrawFilters(); // a genre taken away takes its cards out of the counts
    picked.querySelectorAll("h2").forEach((h) => h.setAttribute("tabindex", "-1"));
  };
  // A genre ticked as a row in Settings (DASH-395) is on the page already, so it has no chip as well.
  const asRows = new Set(d.rows.map((r) => r.id));
  d.genres = d.genres.filter((g) => !asRows.has(g.id));
  const chips = d.genres.length ? el("div", { class: "toolbar" }, el("div", { class: "toolbar__row" },
    el("div", { class: "filter-chips discover-genres", role: "group", "aria-label": "Genres" },
      ...d.genres.map((g) => {
        const b = el("button", { type: "button", class: "filter-chip", "aria-pressed": "false" }, g.title);
        b.addEventListener("click", () => {
          const on = b.getAttribute("aria-pressed") !== "true";
          if (on) shownGenres.add(g); else shownGenres.delete(g);
          b.setAttribute("aria-pressed", String(on));
          showGenres();
          announce(on ? `${g.title} shown at the top` : `${g.title} taken away`);
        });
        return b;
      })))) : null;
  holder.replaceChildren(...[D_TAB === "radio" ? radioFinder(d, picked) : null, filterBar, chips, picked, ...d.rows.map((r, n) => dRow(r, { open: n < 2 }))].filter(Boolean));
}

// Radio (DASH-339): one search across every source Reelix has switched on, with From radio stations and Podcast
// feeds only; every BBC station in a picker by group; each source's own categories under More categories.
// Choosing a station or a category puts its row at the top, as a genre chip does.
function radioFinder(d, picked) {
  const show = (r) => {
    $$(".discover-genres .filter-chip").forEach((x) => x.setAttribute("aria-pressed", "false"));
    picked.dispatchEvent(new Event("genres-clear"));
    picked.replaceChildren(dRow(r, { open: true }));
    const h = picked.querySelector("h2");
    if (h) { h.setAttribute("tabindex", "-1"); h.focus(); }
  };
  const picker = (id, label, items, groupOf) => {
    if (!items?.length) return null;
    const groups = new Map();
    for (const it of items) { const g = groupOf(it); if (!groups.has(g)) groups.set(g, []); groups.get(g).push(it); }
    const select = el("select", { class: "select", id }, el("option", { value: "", text: "Choose…" }),
      ...[...groups].map(([g, list]) => el("optgroup", { label: g }, list.map((it) => el("option", { value: it.id, text: it.title })))));
    const go = el("button", { type: "button", class: "btn" }, "Show");
    go.addEventListener("click", () => { const it = items.find((x) => x.id === select.value); if (it) show(it); });
    select.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); go.click(); } });
    return el("div", { class: "field radio-picker" }, el("label", { for: id, text: label }), el("div", { class: "radio-picker__row" }, select, go));
  };
  const q = el("input", { class: "input", id: "radio-q", type: "search", autocomplete: "off", placeholder: "A show, a presenter or a subject" });
  // Two filters that can be on together: filter chips in the search's toolbar (DASH-309, R4), not switches.
  const filterChip = (id, words) => {
    const b = el("button", { type: "button", class: "filter-chip", id, "aria-pressed": "false", "aria-describedby": "radio-filters-hint" }, words);
    b.addEventListener("click", () => { b.setAttribute("aria-pressed", String(b.getAttribute("aria-pressed") !== "true")); if (q.value.trim().length >= 2) run(); });
    return b;
  };
  const stations = filterChip("radio-stations", "From radio stations");
  const feeds = filterChip("radio-feeds", "Podcast feeds only");
  const on = (b) => b.getAttribute("aria-pressed") === "true";
  const results = el("div", { class: "radio-results" });
  const said = el("p", { class: "small muted", id: "radio-said" });
  const run = async () => {
    const words = q.value.trim();
    if (words.length < 2) { said.textContent = "Type at least two letters."; announce(said.textContent); return; }
    said.textContent = "Asking every source…";
    try {
      const got = await api(`/api/library/discover-radio-search?tab=radio&q=${encodeURIComponent(words)}${on(stations) ? "&stations=1" : ""}${on(feeds) ? "&feeds=1" : ""}`);
      const list = el("ul", { class: "discover-shelf discover-shelf--wrap", "aria-labelledby": "radio-results-h" }, got.items.map(dCard));
      results.replaceChildren(el("h2", { id: "radio-results-h", text: `Found for “${words}”` }), got.note ? notice("info", "This filter needs a newer Reelix", got.note)
        : got.items.length ? list
        : emptyState("Nothing found", on(stations) || on(feeds) ? "Try again with fewer filters." : "Try other words, or choose a genre or a station."));
      said.textContent = `${got.items.length} ${got.items.length === 1 ? "show" : "shows"} found`;
      announce(said.textContent);
    } catch (e) { said.textContent = e.message; announce(e.message); }
  };
  const form = el("form", { class: "radio-search", role: "search", "aria-label": "Search radio" },
    el("div", { class: "field" }, el("label", { for: "radio-q", text: "Search every radio source" }),
      el("div", { class: "search-field" }, q, el("button", { type: "submit", class: "btn btn--primary" }, icon("search"), "Search"))),
    el("div", { class: "toolbar__row radio-search__filters" },
      el("div", { class: "filter-chips", role: "group", "aria-label": "Only" }, stations, feeds)),
    el("p", { class: "small muted", id: "radio-filters-hint", text: "From radio stations: only shows a broadcaster makes, such as the BBC, LBC or Times Radio. Podcast feeds only: shows with a podcast feed, which Reelix follows with the fewest steps." }),
    said);
  form.addEventListener("submit", (e) => { e.preventDefault(); run(); });
  const pickers = el("div", { class: "radio-pickers" },
    picker("radio-station", "A BBC station", d.stations, (s) => s.group.replace(/^BBC stations: /, "").replace(/^./, (c) => c.toUpperCase())),
    picker("radio-more", "More categories", d.more, (c) => c.group ? `${c.source}: ${c.group}` : c.source));
  return el("div", { class: "stack-4" }, form, results, pickers);
}

startPage().then((s) => { if (s && D) startDiscover(); });
