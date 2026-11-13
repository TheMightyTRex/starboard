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

// Something with nothing in your library yet (wanted, searching, not released) has its cover faded behind a dashed
// outline, as on the series and collection cards (owner, 12 November 2026); its chip still says which.
function posterBox(card, className = "cover") {
  const box = el("div", { class: `${className}${card.have === false ? " is-wanted" : ""}`, "aria-hidden": "true" });
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

// DASH-206, several at once (films and series): a tick on each card while Select several is on.
function tick(card) {
  if (!state.selecting) return null;
  return el("input", { type: "checkbox", class: "lib-tick", value: String(card.id), "aria-label": `Tick ${card.title}`,
    checked: state.ticked?.has(String(card.id)), onchange: (e) => { e.target.checked ? state.ticked.add(e.target.value) : state.ticked.delete(e.target.value); bulkCount(); } });
}

function coverCard(card) {
  return el("li", { class: "media-card lib-card", "data-id": String(card.id) },
    tick(card),
    posterBox(card),
    el("span", { class: "media-card__title" }, el("a", { href: itemHref(card.id), text: card.title })),
    el("span", { class: "media-card__meta", text: [card.meta, card.count].filter(Boolean).join(" · ") }),
    el("span", { class: "lib-card__status" }, statusChip(card)));
}

function listRow(card) {
  return el("li", { class: "row row--opens lib-row", "data-id": String(card.id) },
    tick(card),
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

// One at a time (DASH-309, R4): a segmented control with All first, not filter chips that undo each other.
function renderChips(chips) {
  const box = $("#lib-chips");
  box.hidden = !chips.length;
  box.removeAttribute("role");
  box.removeAttribute("aria-label");
  if (!chips.length) { box.replaceChildren(); return; }
  box.replaceChildren(segmentedFilter({
    name: "lib-chip", label: "Show only", value: state.chip,
    options: [["", "All", state.total], ...chips.map((c) => [c.key, c.label, c.count])],
    onChange: (v) => { state.chip = v || ""; reload(); },
  }));
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

// An opened group (a collection, network, station, series or author) takes over the page's heading: its name, and its
// logo for a network; the back link goes at the top of the page, above the heading, as on every item page (issue #15).
const IN_GROUP = { Collections: "in this collection", Networks: "on this network", Stations: "from this station",
  Series: "in this series", Authors: "by this author", Narrators: "read by this narrator" };
function showGroup() {
  if (!state.group) return;
  const [page, label] = state.by === "authors" ? [`library-${TAB}-authors.html`, "Authors"]
    : state.by === "narrators" && TAB === "audiobooks" ? ["library-audiobooks-narrators.html", "Narrators"]  // DASH-261
      : GROUP_PAGE[TAB] || ["", ""];
  const head = $(".page-head");
  if (page) head.before(el("a", { class: "back-link", href: `/${page}` }, icon("arrow-left"), `All ${label.toLowerCase()}`));
  // A TV network's own page shows its logo beside its name (owner, 10 November 2026), in its own colours, as on the
  // Networks grid; decorative, as the name is written beside it, and left out when the network has none.
  const logo = TAB === "tv" && !state.by
    ? logoTone(el("img", { class: "lib-group-logo", src: `/api/library/network-logo?tab=tv&name=${encodeURIComponent(state.group)}`, alt: "",
      onerror: (e) => e.target.remove() }), state.group, "") : null;
  const h1 = $("h1", head);
  h1.replaceChildren(...[logo, document.createTextNode(state.group)].filter(Boolean));
  h1.classList.toggle("lib-group-title", !!logo);
  const words = NOUN[TAB][1];
  $(".page-head__summary", head).textContent = `${words[0].toUpperCase()}${words.slice(1)} ${IN_GROUP[label] || "in this group"}, A to Z.`;
  document.title = `${state.group} · ${document.title}`;
  if (["films", "audiobooks", "books"].includes(TAB) && !state.by) groupComplete();
}

// An opened collection or series, complete (owner, 12 November 2026): how many you have of how many, every one in
// order with the missing ones as outlines, and Add missing, which adds them all to Reelix.
async function groupComplete() {
  const box = el("section", { class: "group-complete", "aria-label": "The whole collection" }, el("p", { class: "small muted", text: "Looking for the rest…" }));
  $(".page-head").after(box);
  $("#lib-add-missing")?.remove();
  let d;
  try { d = await api(`/api/library/group-detail?tab=${TAB}&group=${encodeURIComponent(state.group)}`); }
  catch (e) { box.replaceChildren(notice("info", "Could not look for the rest", e.message)); return; }
  if (!d.total) { box.remove(); return; }
  const noun = TAB === "films" ? ["film", "films"] : ["book", "books"];
  const add = el("button", { type: "button", class: "btn btn--primary" }, icon("plus"), `Add missing (${d.missing})`);
  add.disabled = !d.missing;
  add.addEventListener("click", async () => {
    const titles = d.items.filter((i) => !i.have && !i.wanted).map((i) => i.title);
    if (!await confirmDialog({ title: `Add ${titles.length} missing ${titles.length === 1 ? noun[0] : noun[1]}?`, confirm: "Add them",
      message: [el("p", { text: TAB === "films" ? "Reelix adds each one with the collection's quality and folder, and starts looking for them."
        : `Reelix adds each one as ${TAB === "books" ? "an ebook" : "an audiobook"} and starts looking for them.` }),
        el("ul", {}, titles.slice(0, 30).map((t) => el("li", { text: t })))] })) return;
    add.disabled = true;
    add.textContent = "Adding…";
    try {
      const out = await api("/api/library/group-missing", { method: "POST", body: { tab: TAB, group: state.group } });
      toast(`Added ${out.added.length}${out.failed.length ? `; ${out.failed.length} could not be found: ${out.failed.join(", ")}` : ""}`);
      box.remove();
      groupComplete();
    } catch (e) { problem(e.message, add); add.disabled = false; add.textContent = `Add missing (${d.missing})`; }
  });
  const ring = el("span", { class: `collection-ring${d.have === d.total ? " is-complete" : ""}`, role: "img", "aria-label": `${d.have} of ${d.total} in your library` },
    el("span", { class: "collection-ring__text", "aria-hidden": "true", text: `${d.have}/${d.total}` }));
  ring.style.setProperty("--done", `${Math.round((d.have / d.total) * 100)}`);
  const strip = el("ol", { class: "group-complete__strip" }, d.items.map((i) => el("li", { class: i.have ? "" : "is-missing" },
    i.poster ? el("img", { src: i.poster, alt: "", loading: "lazy" }) : el("span", { class: "group-complete__blank", "aria-hidden": "true" }),
    el("span", { class: "group-complete__title", text: i.title }),
    el("span", { class: "small muted", text: [i.when, i.have ? "" : i.wanted ? "Wanted" : "Missing"].filter(Boolean).join(" · ") }))));
  // Add missing at the right of the heading's line (issue #14), where a page's own buttons go.
  $(".page-head").append(el("div", { class: "actions", id: "lib-add-missing" }, add));
  box.replaceChildren(
    titleChip(el("p", { class: "group-complete__count", text: `${d.have} of ${d.total} ${d.total === 1 ? noun[0] : noun[1]} in your library` }), ring),
    shelfScroller(strip, "the whole collection"),
    el("p", { class: "small muted", text: `From ${d.source}.` }));
}

// Your own details (DASH-322): a folder no outside source matches comes in with the title, year, description, station
// and picture the person types. Shown only when Reelix has the route for it (RFX-90). The fields open under the
// folder's name when "Use my own details" is chosen, and focus goes to the first one.
const OWN = "own";
const OWN_NAME = { films: "Title", tv: "Title", music: "Artist's name", audiobooks: "Author's name", books: "Author's name", radio: "Show's title" };
const PICTURE_MAX = 5 * 1024 * 1024;
let ownCount = 0;
function ownFields(tab, title, year) {
  const n = ++ownCount;
  const field = (label, control, hint) => el("div", { class: "field" }, el("label", { class: "field__label", for: control.id, text: label }),
    hint ? el("p", { class: "hint", id: `${control.id}-h`, text: hint }) : null, control);
  const name = el("input", { class: "input", id: `own-title-${n}`, type: "text", value: title || "", maxlength: "200", required: true, autocomplete: "off" });
  const when = el("input", { class: "input", id: `own-year-${n}`, type: "text", inputmode: "numeric", maxlength: "4", value: year ? String(year) : "",
    autocomplete: "off", "aria-describedby": `own-year-${n}-h` });
  const about = el("textarea", { class: "textarea", id: `own-about-${n}`, rows: "3", maxlength: "4000" });
  const station = tab === "radio" ? el("input", { class: "input", id: `own-station-${n}`, type: "text", maxlength: "200", autocomplete: "off" }) : null;
  const address = el("input", { class: "input", id: `own-pic-${n}`, type: "url", placeholder: "https://", autocomplete: "off", "aria-describedby": `own-pic-${n}-h` });
  const file = el("input", { class: "input", id: `own-file-${n}`, type: "file", accept: "image/png,image/jpeg,image/webp", "aria-describedby": `own-file-${n}-h` });
  // A plain box around the fields: a stack's own display would show it while hidden.
  const node = el("div", { hidden: true }, el("fieldset", { class: "stack-2" },
    el("legend", { class: "field__label", text: "Your own details" }),
    field(OWN_NAME[tab] || "Title", name), field("Year", when, "Optional. Four numbers, such as 2004."),
    field("Description", about), station ? field("Station", station) : null,
    field("Picture's address", address, "Optional. Reelix keeps its own copy."), field("Or choose a picture", file, "A PNG, JPEG or WebP file up to 5 MB.")));
  const read = (f) => new Promise((resolve, reject) => {
    if (f.size > PICTURE_MAX) { reject(new Error(`${f.name} is larger than 5 MB. Choose a smaller picture`)); return; }
    const r = new FileReader();
    r.onload = () => resolve(r.result);
    r.onerror = () => reject(new Error(`${f.name} could not be read`));
    r.readAsDataURL(f);
  });
  return {
    node,
    show(on) { node.hidden = !on; if (on) name.focus(); },
    async value() {
      return { title: name.value.trim() || title || "", year: when.value.trim(), overview: about.value.trim(), station: station?.value.trim() || "",
        image_url: address.value.trim(), image_data: file.files[0] ? await read(file.files[0]) : "" };
    },
  };
}

// DASH-186: films and series already on disk that Reelix does not know yet. A note above the wall, then a dialog of
// up to 25 folders at a time with Reelix's best match for each; change a doubtful one or untick it, then bring them in.
// Books and audiobooks come in by author folder, music by artist folder (DASH-282).
const BY_FOLDER = { audiobooks: ["author", "authors"], books: ["author", "authors"], music: ["artist", "artists"] };
let ownDetails = false;  // Reelix can bring in a folder with your own details (DASH-322, Reelix RFX-90)
async function importNote() {
  if (!["films", "tv", "audiobooks", "books", "music"].includes(TAB)) return;
  let folders = [];
  try {
    const got = await api(`/api/library/import?tab=${TAB}`);
    folders = got.folders.filter((f) => f.waiting);
    ownDetails = !!got.own;
  } catch { return; }
  if (!folders.length) return;
  const waiting = folders.reduce((n, f) => n + f.waiting, 0);
  const box = el("div", { id: "lib-import" }, el("div", { class: "notice", role: "status" }, icon("folder-input"),
    el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: `${plural(waiting, ["folder", "folders"])} on disk ${waiting === 1 ? "is" : "are"} not in your library yet` }),
      el("p", { text: `In ${folders.map((f) => f.path).join(" and ")}. Starboard can bring them in: Reelix finds each one and adds the files where they are. Nothing is downloaded or moved.` })),
    el("button", { type: "button", class: "btn", onclick: (e) => importDialog(folders[0], 0, 0, e.currentTarget) }, "Bring them in")));
  $(".page-head").after(box);
}

async function importDialog(folder, start = 0, added = 0, button = null) {
  // Reelix looks each folder up (TMDB, Open Library for books, MusicBrainz for music), which can take a while: say so at once.
  const busy = button || $("#lib-import button");
  const label = busy?.textContent;
  if (busy) { busy.disabled = true; busy.textContent = "Finding matches…"; }
  let page;
  try { page = await api("/api/library/import/scan", { method: "POST", body: { root: folder.id, start, tab: TAB } }); }
  catch (e) { problem(e.message); return; }
  finally { if (busy) { busy.disabled = false; busy.textContent = label; } }
  const rows = page.items.map((it) => {
    const pick = el("select", { class: "select", "aria-label": `Match for ${it.name}` },
      it.matches.map((m, i) => el("option", { value: String(m.tmdb_id ?? m.id), text: `${m.title}${m.year ? ` (${m.year})` : ""}${m.detail ? `, ${m.detail}` : ""}${m.already ? ", already in your library" : ""}`, selected: i === 0 })),
      el("option", { value: "", text: it.matches.length ? "None of these" : "No match found" }),
      ownDetails ? el("option", { value: OWN, text: "Use my own details" }) : null);
    // A folder whose match is already in the library (in another folder) is unticked: bringing it in would fail.
    const first = it.matches[0];
    const keep = el("input", { type: "checkbox", checked: (it.sure ?? true) && !!first && !first.already, "aria-label": `Bring in ${it.name}` });
    const said = el("p", { class: "small muted" });
    const own = ownFields(TAB, it.title || it.name, it.year);
    const explain = () => {
      const m = it.matches.find((x) => String(x.tmdb_id ?? x.id) === pick.value);
      said.textContent = m && m.already ? `Already in your library, in the folder ${m.already}. Leave this folder out, or choose another match.` : (it.problem || "");
    };
    pick.addEventListener("change", () => {
      const m = it.matches.find((x) => String(x.tmdb_id ?? x.id) === pick.value);
      keep.checked = pick.value === OWN || (!!m && !m.already);
      own.show(pick.value === OWN);
      explain();
    });
    explain();
    // A row per folder (DASH-309, R7): the tick, the folder and what is wrong with it, then Reelix's match; your own
    // details open under the folder's name when chosen.
    return { it, pick, keep, own, node: el("li", { class: "row" }, keep,
      el("div", {}, el("div", { class: "row__title", text: it.name }), said, own.node), el("div", { class: "row__side" }, pick)) };
  });
  const list = el("ul", { class: "rows", "aria-label": "Folders and their matches" }, rows.map((r) => r.node));
  const end = Math.min(page.start + page.items.length, page.total);
  // A list to check, so a slide-out, not a dialog (DASH-309, R6).
  const ok = await slideOutConfirm({ title: `Bring in ${NOUN[TAB][1]} from disk`, confirm: "Bring in the ticked ones", opener: button || $("#lib-import button"),
    body: [el("p", { text: `Folders ${page.start + 1} to ${end} of ${page.total} in ${folder.path}. Check each match; untick any that are wrong. Unticked folders are left out and not asked about again.` }), list] });
  if (!ok) return;
  const byFolder = !!BY_FOLDER[TAB];
  let items;
  try {
    items = await Promise.all(rows.filter((r) => r.keep.checked && r.pick.value).map(async (r) => (r.pick.value === OWN ? { path: r.it.path, own: await r.own.value() }
      : byFolder ? { path: r.it.path, id: r.pick.value } : { path: r.it.path, tmdb_id: Number(r.pick.value) })));
  } catch (e) { problem(e.message); return; }
  const leave = rows.filter((r) => !r.keep.checked || !r.pick.value).map((r) => r.it.path);
  let out;
  try {
    out = items.length || leave.length ? await api("/api/library/import/run", { method: "POST", body: { root: folder.id, items, leave, tab: TAB } }) : { added: 0, errors: [] };
    if (out.errors.length) problem(out.errors.map((e) => `${e.path}: ${e.message}`).join(". "));
  } catch (e) { problem(e.message); return; }
  added += out.added;
  if (end < page.total) { importDialog(folder, end, added); return; }
  // Said where the note was, so it is seen, not only announced (the wall reloads behind it).
  const what = BY_FOLDER[TAB] || NOUN[TAB];  // books come in by author, music by artist
  const text = added ? `Brought in ${plural(added, what)}. Reelix is reading their files; they show here as it finds them.` : "Nothing was brought in.";
  $("#lib-import")?.replaceChildren(el("div", { class: "notice", "data-tone": added ? "success" : null, role: "status" }, icon(added ? "circle-check" : "info"),
    el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: added ? "Brought in from disk" : "Nothing brought in" }), el("p", { text }))));
  reload();
}

// Radio shows already on disk (owner, 10 November 2026): shows in Audiobookshelf's Radio library that Reelix does
// not follow. A note above the wall; when Reelix does not read that library yet, the note says where to connect it.
const FOLLOW_WORDS = { all: ["Every episode", "Old and new: Reelix fills the gaps"], from_now_on: ["New episodes", "From today on"],
  none: ["Only what you have", "Nothing is downloaded"] };
async function radioNote() {
  if (TAB !== "radio") return;
  let s;
  try { s = await api("/api/library/radio-import"); ownDetails = !!s.own; } catch { return; }
  const box = (title, text, action) => el("div", { id: "lib-import" }, el("div", { class: "notice", role: "status" }, icon("folder-input"),
    el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: title }), el("p", { text })), action));
  if (!s.connected) {
    $(".page-head").after(box("Bring in radio shows already on disk", "Reelix does not read Audiobookshelf's Radio library yet, so it cannot see the shows you have. Connect it once in Settings, Reelix, Radio.",
      el("a", { class: "btn", href: "/settings-reelix.html#rx-radio-h" }, "Connect it")));
    return;
  }
  if (!s.waiting) return;
  $(".page-head").after(box(`${plural(s.waiting, ["show", "shows"])} on disk ${s.waiting === 1 ? "is" : "are"} not in your library yet`,
    "In Audiobookshelf's Radio library. Starboard can bring them in: Reelix finds each show on its radio sources and matches your files to its episodes. Nothing is moved.",
    el("button", { type: "button", class: "btn", onclick: (e) => radioDialog(0, 0, "all", e.currentTarget) }, "Bring them in")));
}

async function radioDialog(start = 0, added = 0, follow = "all", button = null) {
  // Reelix searches its radio sources for each show, which can take a minute: say so at once (owner, 10 November
  // 2026: the button looked as if it did nothing).
  const busy = button || $("#lib-import button");
  const label = busy?.textContent;
  if (busy) { busy.disabled = true; busy.textContent = "Finding your shows…"; }
  announce("Finding your shows on Reelix's radio sources. This can take a minute.");
  let page;
  try { page = await api("/api/library/radio-import/scan", { method: "POST", body: { start } }); }
  catch (e) { problem(e.message); return; }
  finally { if (busy) { busy.disabled = false; busy.textContent = label; } }
  const rows = page.items.map((it) => {
    const pick = el("select", { class: "select", "aria-label": `Match for ${it.title}` },
      it.matches.map((m, i) => el("option", { value: String(i), text: `${m.title}${m.station ? `, ${m.station}` : ""}${m.episodes ? ` (${m.episodes} episodes)` : ""}`, selected: i === 0 })),
      el("option", { value: "", text: it.matches.length ? "None of these" : "No match found" }),
      ownDetails ? el("option", { value: OWN, text: "Use my own details" }) : null);
    // Ticked only for a match with the same title; a near one is shown, unticked, for you to check.
    const keep = el("input", { type: "checkbox", checked: !!it.sure, "aria-label": `Bring in ${it.title}` });
    const own = ownFields("radio", it.title, null);
    pick.addEventListener("change", () => { keep.checked = pick.value !== ""; own.show(pick.value === OWN); });
    const note = it.problem || (it.matches.length && !it.sure ? "Not the same title: check it, then tick it." : "");
    return { it, pick, keep, own, node: el("li", { class: "row" }, keep,
      el("div", {}, el("div", { class: "row__title", text: it.title }),
        el("div", { class: "row__meta", text: [plural(it.files, ["file", "files"]), note].filter(Boolean).join(" · ") }), own.node),
      el("div", { class: "row__side" }, pick)) };
  });
  const name = `radio-follow-${Date.now()}`;
  const gets = el("fieldset", { class: "stack-2" }, el("legend", { class: "field__label", text: "What Reelix gets for each show" }),
    el("div", { class: "option-cards" }, Object.entries(FOLLOW_WORDS).map(([v, [t, h]]) => el("label", { class: "option-card" },
      el("input", { type: "radio", name, value: v, checked: v === follow }), el("strong", { text: t }), el("small", { text: h })))));
  const list = el("ul", { class: "rows", "aria-label": "Radio shows and their matches" }, rows.map((r) => r.node));
  const end = Math.min(page.start + page.items.length, page.total);
  // A list to check and a choice, so a slide-out, not a dialog (DASH-309, R6 and R7).
  const ok = await slideOutConfirm({ title: "Bring in radio shows from disk", confirm: "Bring in the ticked ones", opener: button || $("#lib-import button"),
    body: [el("p", { text: `Shows ${page.start + 1} to ${end} of ${page.total}. Check each match; untick any that are wrong.` }), start ? null : gets, list].filter(Boolean) });
  if (!ok) return;
  if (!start) follow = (gets.querySelector(`input[name="${name}"]:checked`) || {}).value || "all";
  let items;
  try {
    items = await Promise.all(rows.filter((r) => r.keep.checked && r.pick.value !== "").map(async (r) => (r.pick.value === OWN
      ? { key: r.it.key, title: r.it.title, own: await r.own.value() } : { ...r.it.matches[Number(r.pick.value)] })));
  } catch (e) { problem(e.message); return; }
  let out;
  try {
    out = items.length ? await api("/api/library/radio-import/run", { method: "POST", body: { items, follow } }) : { added: 0, errors: [] };
    if (out.errors.length) problem(out.errors.map((e) => `${e.title}: ${e.message}`).join(". "));
  } catch (e) { problem(e.message); return; }
  added += out.added;
  if (end < page.total) { radioDialog(end, added, follow); return; }
  const text = added ? `Brought in ${plural(added, ["show", "shows"])}. Reelix is matching your files to their episodes${follow === "none" ? "" : " and searching for the ones you do not have"}; they show here as it does.` : "Nothing was brought in.";
  $("#lib-import")?.replaceChildren(el("div", { class: "notice", "data-tone": added ? "success" : null, role: "status" }, icon(added ? "circle-check" : "info"),
    el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: added ? "Brought in from disk" : "Nothing brought in" }), el("p", { text }))));
  reload();
}

startPage().then(async () => {
  if (!TAB) return;
  importNote();
  radioNote();
  try { saved = (await api("/api/library/views")).views[TAB] || {}; } catch { saved = {}; }
  applyView(saved);
  showGroup();
  setUpBulk();
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
  $("#lib-chips").addEventListener("change", () => setTimeout(updateSaveButton));
  $("#lib-more button").addEventListener("click", async () => {
    const before = $$("#lib-wall li").length;
    await load();
    $$("#lib-wall li")[before]?.querySelector("a")?.focus();
  });
  autoLoadMore($("#lib-more button"), async () => {  // DASH-277: the next lot as you near the end, focus left alone
    if (state.loading) return 0;
    const before = $$("#lib-wall li").length;
    await load();
    return $$("#lib-wall li").length - before;
  }, NOUN[TAB][1]);
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
      // A saved note where the button was (R5: not a toast); the button goes, so focus goes to the search.
      const note = $("#lib-save-note") || el("span", { class: "saved-note", id: "lib-save-note", hidden: true });
      $("#lib-actions").prepend(note);
      window.SharedComponents.savedNote(note, `Saved as how ${NOUN[TAB][1]} open. Reset it in Settings, General.`);
      updateSaveButton();
      $("#lib-q").focus();
    } catch (err) { toast(err.message, { tone: "danger" }); }
  });
  await reload();
  updateSaveButton();
});

// Several at once (DASH-206): Select several shows a tick on each film or series and a bar with Follow, Stop
// following and Delete for the ticked ones. Not sticky (the header is the only sticky part).
function bulkCount() {
  const n = state.ticked.size;
  const said = $("#lib-bulk-count");
  if (said) said.textContent = n ? `${n} ticked` : "Tick the ones to change";
  $$("#lib-bulk [data-needs-ticks]").forEach((b) => { b.disabled = !n; });
}

function setUpBulk() {
  if (!["films", "tv"].includes(TAB)) return;
  state.ticked = new Set();
  const start = el("button", { type: "button", class: "btn btn--quiet", id: "lib-select", "aria-pressed": "false" }, icon("list-checks"), "Select several");
  $("#lib-actions")?.append(start);  // with Save this view, in the page head: not a filter, so not in the toolbar (R8)
  const run = async (action, button) => {
    let deleteFiles = false;
    if (action === "delete") {
      const files = el("input", { type: "checkbox", id: "bulk-files" });
      const ok = await confirmDialog({ title: `Delete ${state.ticked.size} from your library?`, confirm: "Delete", danger: true,
        message: "Reelix stops tracking them. Their files stay unless you tick below.",
        fields: [el("label", { class: "check" }, files, el("span", { class: "check__text", text: "Delete their files too" }))] });
      if (!ok) return;
      deleteFiles = files.checked;
    }
    button.disabled = true;
    try {
      const r = await api(`/api/library/bulk?tab=${TAB}`, { method: "POST", body: { ids: [...state.ticked], action, delete_files: deleteFiles } });
      announce(r.said);
      toast(r.said);
      state.ticked.clear();
      stop();
      start.focus();  // the bar has gone: focus goes back to Select several
      reload();
    } catch (e) { problem(e.message, button); }
    finally { button.disabled = false; }
  };
  const bar = el("div", { class: "lib-bulk", id: "lib-bulk", role: "region", "aria-label": "Change several", hidden: true },
    el("span", { id: "lib-bulk-count", "aria-live": "polite" }),
    el("button", { type: "button", class: "btn", "data-needs-ticks": "", onclick: (e) => run("follow", e.currentTarget) }, "Follow"),
    el("button", { type: "button", class: "btn", "data-needs-ticks": "", onclick: (e) => run("unfollow", e.currentTarget) }, "Stop following"),
    el("button", { type: "button", class: "btn btn--danger", "data-needs-ticks": "", onclick: (e) => run("delete", e.currentTarget) }, icon("trash-2"), "Delete"),
    el("button", { type: "button", class: "btn btn--quiet", onclick: () => { stop(); start.focus(); } }, "Done"));
  $("#lib-wall").before(bar);
  const redraw = () => {
    $$("#lib-wall li[data-id]").forEach((li) => {
      li.querySelector(".lib-tick")?.remove();
      const card = { id: li.dataset.id, title: li.querySelector("a")?.textContent || "" };
      const box = tick(card);
      if (box) li.prepend(box);
    });
  };
  const stop = () => { state.selecting = false; start.setAttribute("aria-pressed", "false"); bar.hidden = true; redraw(); };
  start.addEventListener("click", () => {
    state.selecting = !state.selecting;
    start.setAttribute("aria-pressed", String(state.selecting));
    bar.hidden = !state.selecting;
    redraw();
    bulkCount();
    if (state.selecting) $("#lib-wall .lib-tick")?.focus();
  });
}

