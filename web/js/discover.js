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
  if (c.state === "have") side = chip("In your library", "success");
  else if (c.state === "wanted") side = chip("Wanted", "info");
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

function dRow(r, { open = false } = {}) {
  const list = el("ul", { class: "discover-shelf", "aria-label": r.title }, el("li", { class: "muted small", text: "Loading…" }));
  const sec = el("section", { class: "discover-row", "aria-labelledby": `d-${r.id.replace(/[^a-z0-9]/gi, "-")}` },
    el("div", { class: "discover-row__head" }, el("h2", { id: `d-${r.id.replace(/[^a-z0-9]/gi, "-")}`, text: r.title }),
      r.source ? el("span", { class: "small muted", text: r.source }) : null), shelfScroller(list, r.title));
  const load = async () => {
    try {
      const got = await api(`/api/library/discover-row?tab=${D_TAB}&row=${encodeURIComponent(r.id)}`);
      list.replaceChildren(...(got.items.length ? got.items.map(dCard) : [el("li", { class: "muted small", text: "Nothing here right now." })]));
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
  const picked = el("div", { id: "discover-picked" });
  const chips = d.genres.length ? el("div", { class: "filter-chips discover-genres", role: "group", "aria-label": "Genres" },
    ...d.genres.map((g) => {
      const b = el("button", { type: "button", class: "filter-chip", "aria-pressed": "false" }, g.title);
      b.addEventListener("click", () => {
        const on = b.getAttribute("aria-pressed") !== "true";
        $$(".discover-genres .filter-chip").forEach((x) => x.setAttribute("aria-pressed", "false"));
        b.setAttribute("aria-pressed", String(on));
        picked.replaceChildren(...(on ? [dRow(g, { open: true })] : []));
        if (on) picked.querySelector("h2")?.setAttribute("tabindex", "-1");
      });
      return b;
    })) : null;
  holder.replaceChildren(...[D_TAB === "radio" ? radioFinder(d, picked) : null, chips, picked, ...d.rows.map((r, n) => dRow(r, { open: n < 2 }))].filter(Boolean));
}

// Radio (DASH-339): one search across every source Reelix has switched on, with From radio stations and Podcast
// feeds only; every BBC station in a picker by group; each source's own categories under More categories.
// Choosing a station or a category puts its row at the top, as a genre chip does.
function radioFinder(d, picked) {
  const show = (r) => {
    $$(".discover-genres .filter-chip").forEach((x) => x.setAttribute("aria-pressed", "false"));
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
  const stations = el("input", { type: "checkbox", role: "switch", id: "radio-stations", "aria-labelledby": "radio-stations-l" });
  const feeds = el("input", { type: "checkbox", role: "switch", id: "radio-feeds", "aria-labelledby": "radio-feeds-l" });
  const results = el("div", { class: "radio-results" });
  const said = el("p", { class: "small muted", id: "radio-said" });
  const run = async () => {
    const words = q.value.trim();
    if (words.length < 2) { said.textContent = "Type at least two letters."; announce(said.textContent); return; }
    said.textContent = "Asking every source…";
    try {
      const got = await api(`/api/library/discover-radio-search?tab=radio&q=${encodeURIComponent(words)}${stations.checked ? "&stations=1" : ""}${feeds.checked ? "&feeds=1" : ""}`);
      const list = el("ul", { class: "discover-shelf discover-shelf--wrap", "aria-labelledby": "radio-results-h" }, got.items.map(dCard));
      results.replaceChildren(el("h2", { id: "radio-results-h", text: `Found for “${words}”` }), got.note ? notice("info", "This filter needs a newer Reelix", got.note)
        : got.items.length ? list
        : emptyState("Nothing found", stations.checked || feeds.checked ? "Try again with fewer filters." : "Try other words, or choose a genre or a station below."));
      said.textContent = `${got.items.length} ${got.items.length === 1 ? "show" : "shows"} found`;
      announce(said.textContent);
    } catch (e) { said.textContent = e.message; announce(e.message); }
  };
  const form = el("form", { class: "radio-search", role: "search", "aria-label": "Search radio" },
    el("div", { class: "field" }, el("label", { for: "radio-q", text: "Search every radio source" }),
      el("div", { class: "search-field" }, q, el("button", { type: "submit", class: "btn btn--primary" }, icon("search"), "Search"))),
    el("ul", { class: "settings-rows radio-search__filters" },
      el("li", { class: "setting" }, el("div", { class: "setting__text" }, el("span", { class: "setting__label", id: "radio-stations-l", text: "From radio stations" }),
        el("span", { class: "setting__hint", text: "Only shows a broadcaster makes, such as the BBC, LBC or Times Radio." })),
        el("div", { class: "setting__control" }, el("label", { class: "switch" }, stations))),
      el("li", { class: "setting" }, el("div", { class: "setting__text" }, el("span", { class: "setting__label", id: "radio-feeds-l", text: "Podcast feeds only" }),
        el("span", { class: "setting__hint", text: "Shows with a podcast feed, the simplest to follow." })),
        el("div", { class: "setting__control" }, el("label", { class: "switch" }, feeds)))),
    said);
  form.addEventListener("submit", (e) => { e.preventDefault(); run(); });
  [stations, feeds].forEach((s) => s.addEventListener("change", () => { if (q.value.trim().length >= 2) run(); }));
  const pickers = el("div", { class: "radio-pickers" },
    picker("radio-station", "A BBC station", d.stations, (s) => s.group.replace(/^BBC stations: /, "").replace(/^./, (c) => c.toUpperCase())),
    picker("radio-more", "More categories", d.more, (c) => c.group ? `${c.source}: ${c.group}` : c.source));
  return el("div", { class: "stack-4" }, form, results, pickers);
}

startPage().then((s) => { if (s && D) startDiscover(); });
