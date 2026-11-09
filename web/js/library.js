// The Library walls (DASH-163): every film, series, artist, radio show, book or audiobook in Reelix as covers or a
// list, with search in the tab, filter chips, sort, the A to Z jump list and "Show 40 more". Starboard's server
// keeps a slim index per tab (starboard/library.py), so each request is small.

const TAB = document.querySelector("[data-library]")?.dataset.library;
const ITEM_PAGE = { films: "library-film.html", tv: "library-tv-show.html", music: "library-artist.html", radio: "library-radio-show.html",
  books: "library-book.html", audiobooks: "library-audiobook.html" };
const GROUP_PAGE = { films: ["library-films-collections.html", "Collections"], tv: ["library-tv-networks.html", "Networks"],
  radio: ["library-radio-stations.html", "Stations"], books: ["library-books-series.html", "Series"],
  audiobooks: ["library-audiobooks-series.html", "Series"] };
const NOUN = { films: ["film", "films"], tv: ["series", "series"], music: ["artist", "artists"], radio: ["show", "shows"],
  books: ["book", "books"], audiobooks: ["audiobook", "audiobooks"] };
const PAGE_SIZE = 40;
const params = new URLSearchParams(location.search);
const state = { q: params.get("q") || "", chip: params.get("chip") || "", sort: "az", layout: "covers", size: "medium",
  group: params.get("group") || "", by: params.get("by") || "", start: 0, offset: 0, shown: 0, total: 0, loading: false };
let saved = {};

const plural = (n, [one, many]) => `${n.toLocaleString("en-GB")} ${n === 1 ? one : many}`;
const itemHref = (id) => `/${ITEM_PAGE[TAB]}?id=${encodeURIComponent(id)}`;

function posterBox(card, className = "cover") {
  const box = el("div", { class: className, "aria-hidden": "true" });
  const plain = () => box.replaceChildren(el("span", { class: "lib-cover-title", text: card.title }));
  if (card.poster) {
    const img = el("img", { src: card.poster, alt: "", loading: "lazy", decoding: "async" });
    img.addEventListener("error", plain, { once: true });
    box.append(img);
  } else plain();
  return box;
}

function statusChip(card) {
  return card.status ? chip(card.status, card.tone) : null;
}

function coverCard(card) {
  return el("li", { class: "media-card lib-card" },
    posterBox(card),
    el("span", { class: "media-card__title" }, el("a", { href: itemHref(card.id), text: card.title })),
    el("span", { class: "media-card__meta", text: [card.meta, card.count].filter(Boolean).join(" · ") }),
    el("span", { class: "lib-card__status" }, statusChip(card)));
}

function listRow(card) {
  return el("li", { class: "row row--opens lib-row" },
    posterBox(card, "cover cover--result"),
    el("div", {},
      el("h3", { class: "row__title" }, el("a", { href: itemHref(card.id), text: card.title })),
      el("div", { class: "row__meta", text: [card.meta, card.count].filter(Boolean).join(" · ") })),
    el("div", { class: "row__side" }, statusChip(card)));
}

const letterId = (letter) => (letter === "#" ? "letter-num" : `letter-${letter.toLowerCase()}`);

// Adds cards to the wall, under their letter's heading when sorted A to Z. before: the cards come before the
// ones shown (Show earlier titles), so they go in at the top, last first.
function addCards(cards, before = false) {
  const wall = $("#lib-wall");
  const az = state.sort === "az";
  for (const card of before ? [...cards].reverse() : cards) {
    let group = az ? document.getElementById(`group-${letterId(card.letter)}`) : (before ? wall.firstElementChild : wall.lastElementChild);
    if (!group) {
      group = el("section", { class: "lib-group", id: az ? `group-${letterId(card.letter)}` : null, "aria-labelledby": az ? letterId(card.letter) : null });
      if (az) group.append(el("h2", { class: "wall-letter", id: letterId(card.letter), tabindex: "-1", text: card.letter === "#" ? "#" : card.letter },
        el("span", { class: "visually-hidden", text: card.letter === "#" ? " (titles that start with a number)" : "" })));
      group.append(state.layout === "list" ? el("ul", { class: "rows" }) : el("ul", { class: "media-grid", "data-size": state.size }));
      if (before) wall.prepend(group); else wall.append(group);
    }
    const node = state.layout === "list" ? listRow(card) : coverCard(card);
    if (before) group.querySelector("ul").prepend(node); else group.querySelector("ul").append(node);
  }
}

function query(extra = {}) {
  const p = new URLSearchParams({ tab: TAB, sort: state.sort, offset: String(state.offset), limit: String(PAGE_SIZE) });
  if (state.q) p.set("q", state.q);
  if (state.chip) p.set("chip", state.chip);
  if (state.group) p.set("group", state.group);
  if (state.by) p.set("by", state.by);
  for (const [k, v] of Object.entries(extra)) p.set(k, v);
  return `/api/library/wall?${p}`;
}

function renderChips(chips) {
  const box = $("#lib-chips");
  box.hidden = !chips.length;
  box.replaceChildren(...chips.map((c) => el("button", {
    type: "button", class: "filter-chip", "aria-pressed": String(state.chip === c.key), "data-chip": c.key,
    onclick: (e) => {
      state.chip = state.chip === c.key ? "" : c.key;
      reload().then(() => e.currentTarget.isConnected && e.currentTarget.focus());
    },
  }, `${c.label}, ${c.count.toLocaleString("en-GB")}`)));
}

function renderCount() {
  const noun = NOUN[TAB];
  const filtered = state.q || state.chip || state.group;
  const showing = Math.min(state.offset, state.shown) - state.start;
  $("#lib-earlier").hidden = state.start <= 0;
  $("#lib-count").textContent = state.shown
    ? `Showing ${showing.toLocaleString("en-GB")} of ${filtered ? `${plural(state.shown, noun)} found (${state.total.toLocaleString("en-GB")} in all)` : plural(state.total, noun)}`
    : "";
  const more = $("#lib-more");
  more.hidden = state.offset >= state.shown;
  $("#lib-more-count").textContent = `Showing ${showing.toLocaleString("en-GB")} of ${state.shown.toLocaleString("en-GB")}`;
}

function renderLetters(letters) {
  const nav = $("#lib-az");
  nav.hidden = state.sort !== "az" || !state.shown;
  if (!nav.hidden) window.SharedComponents.azJump(nav, new Set(letters));
}

function showNotice(data) {
  const box = $("#lib-notice");
  box.replaceChildren();
  if (data.error) {
    box.append(el("div", { class: "notice", "data-tone": "warning", role: "status" }, icon("triangle-alert"),
      el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: "Showing what Starboard read last time" }),
        el("p", { text: `${data.error}. Starboard tries again in a few minutes.` }))));
  }
}

function empty(text, extra = null) {
  return el("div", { class: "empty" }, el("p", { text }), extra);
}

async function load(extra = {}) {
  state.loading = true;
  $("#lib-wall").setAttribute("aria-busy", "true");
  try {
    const fresh = state.offset === 0 || Boolean(extra.until);
    const data = await api(query(extra));
    state.shown = data.shown;
    state.total = data.total;
    if (fresh) {
      $("#lib-wall").replaceChildren();
      state.start = data.offset;
      state.offset = data.offset;
      renderChips(data.chips);
      renderLetters(data.letters);
      showNotice(data);
    }
    addCards(data.items);
    state.offset += data.items.length;
    renderCount();
    if (!data.shown) {
      const clear = state.q || state.chip ? el("button", { type: "button", class: "btn", text: "Clear the search and filters", onclick: () => {
        state.q = ""; state.chip = ""; $("#lib-q").value = ""; reload();
      } }) : null;
      $("#lib-wall").replaceChildren(empty(state.total
        ? "Nothing matches. Check the spelling, or clear the search and filters."
        : `There are no ${NOUN[TAB][1]} in Reelix yet. Find them with Search, then add them.`, clear ||
        el("a", { class: "btn", href: "/search.html" }, icon("search"), "Search")));
    }
    return data;
  } catch (e) {
    if (e.status === 409) {
      $("#lib-wall").replaceChildren(empty("Starboard shows your library from Reelix. Add Reelix with its key first.",
        el("a", { class: "btn btn--primary", href: "/settings.html" }, "Manage apps")));
      $("#lib-az").hidden = true;
    } else {
      $("#lib-wall").replaceChildren(el("div", { class: "notice", "data-tone": "danger", role: "alert" }, icon("circle-x"),
        el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: "The library could not be read" }), el("p", { text: e.message }))));
    }
    return null;
  } finally {
    state.loading = false;
    $("#lib-wall").setAttribute("aria-busy", "false");
  }
}

async function reload() {
  state.offset = 0;
  state.start = 0;
  const url = new URL(location.href);
  for (const k of ["q", "chip"]) { if (state[k]) url.searchParams.set(k, state[k]); else url.searchParams.delete(k); }
  history.replaceState(null, "", url);
  const data = await load();
  if (data) announce($("#lib-count").textContent);
}

function applyView(view) {
  state.sort = view.sort || "az";
  state.layout = view.layout || "covers";
  state.size = view.size || "medium";
  if (!params.has("chip")) state.chip = view.chip || "";
  $("#lib-sort").value = state.sort;
  $$('input[name="lib-layout"]').forEach((r) => { r.checked = r.value === state.layout; });
  $("#lib-size").value = state.size;
  $("#lib-size-field").hidden = state.layout === "list";
}

function currentView() {
  return { sort: state.sort, layout: state.layout, size: state.size, chip: state.chip };
}

function sameView(a, b) {
  return ["sort", "layout", "size", "chip"].every((k) => (a[k] || "") === (b[k] || ""));
}

function updateSaveButton() {
  const isDefault = sameView(currentView(), { sort: "az", layout: "covers", size: "medium", chip: "", ...saved });
  $("#lib-save").hidden = isDefault;
}

function showGroup() {
  if (!state.group) return;
  const [page, label] = state.by === "authors" ? [`library-${TAB}-authors.html`, "Authors"] : GROUP_PAGE[TAB] || ["", ""];
  $("#lib-group").hidden = false;
  $("#lib-group").replaceChildren(el("h2", { text: state.group }),
    page ? el("a", { class: "back-link", href: `/${page}` }, icon("arrow-left"), `All ${label.toLowerCase()}`) : null);
  document.title = `${state.group} · ${document.title}`;
}

// DASH-186: films and series already on disk that Reelix does not know yet. A note above the wall, then a dialog of
// up to 25 folders at a time with Reelix's best match for each; change a doubtful one or untick it, then bring them in.
async function importNote() {
  if (!["films", "tv"].includes(TAB)) return;
  let folders = [];
  try { folders = (await api(`/api/library/import?tab=${TAB}`)).folders.filter((f) => f.waiting); } catch { return; }
  if (!folders.length) return;
  const waiting = folders.reduce((n, f) => n + f.waiting, 0);
  const box = el("div", { id: "lib-import" }, el("div", { class: "notice", role: "status" }, icon("folder-input"),
    el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: `${plural(waiting, ["folder", "folders"])} on disk ${waiting === 1 ? "is" : "are"} not in your library yet` }),
      el("p", { text: `In ${folders.map((f) => f.path).join(" and ")}. Starboard can bring them in: Reelix finds each one and adds the files where they are. Nothing is downloaded or moved.` })),
    el("button", { type: "button", class: "btn", onclick: () => importDialog(folders[0]) }, "Bring them in")));
  $(".page-head").after(box);
}

async function importDialog(folder, start = 0, added = 0) {
  let page;
  try { page = await api("/api/library/import/scan", { method: "POST", body: { root: folder.id, start } }); }
  catch (e) { problem(e.message); return; }
  const rows = page.items.map((it) => {
    const pick = el("select", { class: "select", "aria-label": `Match for ${it.name}` },
      it.matches.map((m, i) => el("option", { value: String(m.tmdb_id), text: `${m.title}${m.year ? ` (${m.year})` : ""}`, selected: i === 0 })),
      el("option", { value: "", text: it.matches.length ? "None of these" : "No match found" }));
    const keep = el("input", { type: "checkbox", checked: it.matches.length > 0, "aria-label": `Bring in ${it.name}` });
    pick.addEventListener("change", () => { keep.checked = !!pick.value; });
    return { it, pick, keep, node: el("tr", {}, el("td", {}, keep), el("th", { scope: "row", text: it.name }),
      el("td", {}, pick, it.problem ? el("p", { class: "small muted", text: it.problem }) : null)) };
  });
  const table = el("div", { class: "table-wrap" }, el("table", { class: "table table--middle" },
    el("caption", { class: "visually-hidden", text: "Folders and their matches" }),
    el("thead", {}, el("tr", {}, el("th", { scope: "col" }, el("span", { class: "visually-hidden", text: "Bring in" })),
      el("th", { scope: "col", text: "Folder" }), el("th", { scope: "col", text: "Reelix's match" }))),
    el("tbody", {}, rows.map((r) => r.node))));
  const end = Math.min(page.start + page.items.length, page.total);
  const ok = await confirmDialog({ title: `Bring in ${NOUN[TAB][1]} from disk`, confirm: "Bring in the ticked ones",
    message: el("div", { class: "stack-2" }, el("p", { text: `Folders ${page.start + 1} to ${end} of ${page.total} in ${folder.path}. Check each match; untick any that are wrong.` })),
    fields: [table] });
  if (!ok) return;
  const items = rows.filter((r) => r.keep.checked && r.pick.value).map((r) => ({ path: r.it.path, tmdb_id: Number(r.pick.value) }));
  let out;
  try {
    out = items.length ? await api("/api/library/import/run", { method: "POST", body: { root: folder.id, items } }) : { added: 0, errors: [] };
    if (out.errors.length) problem(out.errors.map((e) => `${e.path}: ${e.message}`).join(". "));
  } catch (e) { problem(e.message); return; }
  added += out.added;
  if (end < page.total) { importDialog(folder, end, added); return; }
  // Said where the note was, so it is seen, not only announced (the wall reloads behind it).
  const text = added ? `Brought in ${plural(added, NOUN[TAB])}. Reelix is reading their files; they show here as it finds them.` : "Nothing was brought in.";
  $("#lib-import")?.replaceChildren(el("div", { class: "notice", "data-tone": added ? "success" : null, role: "status" }, icon(added ? "circle-check" : "info"),
    el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: added ? "Brought in from disk" : "Nothing brought in" }), el("p", { text }))));
  reload();
}

startPage().then(async () => {
  if (!TAB) return;
  importNote();
  try { saved = (await api("/api/library/views")).views[TAB] || {}; } catch { saved = {}; }
  applyView(saved);
  showGroup();
  $("#lib-q").value = state.q;
  let typing = 0;
  $("#lib-q").addEventListener("input", () => {
    clearTimeout(typing);
    typing = setTimeout(() => { state.q = $("#lib-q").value.trim(); reload(); }, 250);
  });
  $("#lib-search").addEventListener("submit", (e) => { e.preventDefault(); clearTimeout(typing); state.q = $("#lib-q").value.trim(); reload(); });
  $("#lib-sort").addEventListener("change", () => { state.sort = $("#lib-sort").value; updateSaveButton(); reload(); });
  $$('input[name="lib-layout"]').forEach((r) => r.addEventListener("change", () => {
    state.layout = r.value;
    $("#lib-size-field").hidden = state.layout === "list";
    updateSaveButton();
    reload();
  }));
  $("#lib-size").addEventListener("change", () => {
    state.size = $("#lib-size").value;
    $$("#lib-wall .media-grid").forEach((g) => { g.dataset.size = state.size; });
    updateSaveButton();
  });
  $("#lib-chips").addEventListener("click", () => setTimeout(updateSaveButton));
  $("#lib-more button").addEventListener("click", async () => {
    const before = $$("#lib-wall li").length;
    await load();
    $$("#lib-wall li")[before]?.querySelector("a")?.focus();
  });
  $("#lib-az").addEventListener("az-jump", async (e) => {
    if (state.loading) return;
    await load({ until: e.detail.letter });
    window.SharedComponents.azGo($("#lib-az"), e.detail.letter);
  });
  $("#lib-earlier button").addEventListener("click", async () => {
    if (state.loading || state.start <= 0) return;
    state.loading = true;
    try {
      const from = Math.max(0, state.start - PAGE_SIZE);
      const data = await api(query({ offset: String(from), limit: String(state.start - from) }));
      const first = $("#lib-wall li");
      addCards(data.items, true);
      state.start = from;
      renderCount();
      // Focus goes to the first of the titles just added, so reading carries on upwards.
      const all = $$("#lib-wall li");
      all[all.indexOf(first) - data.items.length]?.querySelector("a")?.focus();
    } catch (err) { toast(err.message, { tone: "danger" }); } finally { state.loading = false; }
  });
  $("#lib-save").addEventListener("click", async () => {
    try {
      saved = (await api("/api/library/views", { method: "POST", body: { tab: TAB, view: currentView() } })).views[TAB] || {};
      updateSaveButton();
      toast(`Saved as how ${NOUN[TAB][1]} open. Reset it in Settings, General`);
      $("#lib-q").focus();
    } catch (err) { toast(err.message, { tone: "danger" }); }
  });
  await reload();
  updateSaveButton();
});
