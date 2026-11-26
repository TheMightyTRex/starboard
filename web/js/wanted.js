// Wanted (DASH-207): Wanted, and Below quality, for films and episodes, from Reelix. Tick some and act
// on them in the selection bar (DASH-524), or search for everything on the list. A page at a time, with Show more. A film or episode row opens its details in a slide-out (DASH-309, R1: a row that opens).

// 12 November 2026: one page per media type (the level 2 menu), with Wanted and Below quality as tabs.
let WHICH = new URLSearchParams(location.search).get("list") === "cutoff" ? "cutoff" : "missing";
const W_KIND = document.querySelector("[data-wanted-kind]")?.dataset.wantedKind;
const wantedState = { kind: W_KIND || "movie", page: 1, total: 0, items: [], paused: false,
  chosen: new Set(), // ids of the rows ticked for a bulk action (DASH-524, as the download queue's)
  lastPicked: null, // the id last ticked or cleared, for Shift and a tick to take a run of rows
  busy: false };
const W_NOUN = { movie: ["film", "films"], episode: ["episode", "episodes"], album: ["album", "albums"], ebook: ["book", "books"],
  audiobook: ["audiobook", "audiobooks"] };

function wantedTabs() {
  const tabs = [["missing", "Wanted"], ["cutoff", "Below quality"]];
  const list = el("div", { role: "tablist", "aria-label": "Which list" }, tabs.map(([v, t]) => {
    const b = el("button", { type: "button", role: "tab", class: "topic-tabs__tab", "aria-selected": String(v === WHICH), "aria-controls": "wanted-list", text: t });
    b.addEventListener("click", () => {
      WHICH = v;
      $$("[role=tab]", list).forEach((x) => x.setAttribute("aria-selected", String(x === b)));
      const u = new URL(location.href); if (v === "cutoff") u.searchParams.set("list", "cutoff"); else u.searchParams.delete("list");
      history.replaceState(null, "", u);
      wantedLoad();
    });
    return b;
  }));
  list.addEventListener("keydown", (e) => {
    if (!["ArrowLeft", "ArrowRight"].includes(e.key)) return;
    const bs = $$("[role=tab]", list); const i = bs.indexOf(document.activeElement);
    if (i < 0) return;
    e.preventDefault(); const n = bs[(i + (e.key === "ArrowRight" ? 1 : -1) + bs.length) % bs.length]; n.focus(); n.click();
  });
  return el("nav", { class: "topic-tabs", "aria-label": "Which list" }, list);
}

function wantedRow(w) {
  const name = w.detail ? `${w.title}, ${w.detail}` : w.title;
  const pick = el("input", { type: "checkbox", class: "dl-pick__box", value: String(w.id), "aria-label": `Select ${name}` });
  pick.checked = wantedState.chosen.has(w.id);
  pick.disabled = wantedState.busy;
  pick.addEventListener("click", (e) => wantedPick(w.id, pick.checked, e.shiftKey));
  const when = w.date ? new Date(w.date).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "";
  const meta = [w.detail, when, WHICH === "cutoff" && w.quality ? `Has ${w.quality}, wants ${w.cutoff || "better"}` : ""].filter(Boolean).join(" · ");
  const search = el("button", { type: "button", class: "btn btn--quiet btn--compact", onclick: (e) => wantedSearch([w.id], e.currentTarget) },
    icon("search"), "Search", el("span", { class: "visually-hidden", text: ` for ${name}` }));
  // DASH-171: while download hours pause downloads, Download now gets this one straight away.
  const now = wantedState.paused && ["movie", "episode"].includes(wantedState.kind) ? el("button", { type: "button", class: "btn btn--quiet btn--compact", onclick: (e) => downloadNow(w, name, e.currentTarget) },
    icon("zap"), "Download now", el("span", { class: "visually-hidden", text: ` ${name}` })) : null;
  // A film or episode opens its details (the title is the button; the slide-out links to its page). Others link to theirs.
  const opens = ["movie", "episode"].includes(wantedState.kind);
  const words = w.year ? `${w.title} (${w.year})` : w.title;
  const title = opens ? el("button", { type: "button", "aria-haspopup": "dialog", onclick: (e) => wantedDetail(w, name, e.currentTarget) }, words,
    w.detail ? el("span", { class: "visually-hidden", text: `, ${w.detail}` }) : null)
    : w.href ? el("a", { href: w.href, text: words }) : words;
  return el("li", { class: opens ? "row row--opens wanted-row" : "row wanted-row", "data-key": String(w.id) }, el("label", { class: "dl-pick" }, pick),
    el("div", {}, el("h3", { class: "row__title" }, title), el("div", { class: "row__meta", text: meta })),
    el("div", { class: "row__side" }, search, now));
}

// DASH-305: a wanted film or episode in full, in a slide-out: picture, story, length, genres, the quality wanted, what
// Reelix last did for it, and See what Reelix can find (every site's releases, best first, with Get this one).
async function wantedDetail(w, name, opener) {
  const body = el("div", { class: "stack-4" }, SharedComponents.wait("Loading what Reelix knows"));
  sidePanel({ title: name, body: [body], opener, wide: true });
  let d;
  try { d = await api(`/api/wanted/detail?kind=${wantedState.kind}&id=${w.id}${w.series_id ? `&series=${w.series_id}` : ""}`); }
  catch (e) { body.replaceChildren(el("p", { text: e.message })); return; }
  const facts = [["Year", d.year], ["Aired", d.aired], ["Length", d.runtime ? `${d.runtime} minutes` : ""], ["Genres", (d.genres || []).join(", ")],
    ["Quality wanted", d.profile]].filter(([, v]) => v);
  const results = el("div", { class: "stack-2", "aria-live": "polite" });
  const find = el("button", { type: "button", class: "btn btn--primary" }, icon("search"), "Find releases");
  find.addEventListener("click", async () => {
    find.disabled = true;
    results.replaceChildren(el("p", { class: "muted", text: "Asking every site. This can take a minute…" }));
    const p = new URLSearchParams(Object.entries(d.releases).map(([k, v]) => [k, String(v)]));
    try {
      const r = await api(`/api/library/releases?${p}`);
      results.replaceChildren(r.releases.length ? el("ul", { class: "rows" }, r.releases.map((x) => {
        const take = el("button", { type: "button", class: x.accepted ? "btn btn--compact" : "btn btn--quiet btn--compact" }, x.accepted ? "Get this one" : "Get it anyway",
          el("span", { class: "visually-hidden", text: ` ${x.title}` }));
        take.addEventListener("click", async () => {
          take.disabled = true;
          try { const g = await api(`/api/library/grab?tab=${d.releases.tab}`, { method: "POST", body: { guid: x.guid, indexer_id: x.indexer_id, force: !x.accepted, title: x.title } });
            // The row says Sent, with focus on it, and the result is said (R5: no toast repeating the chip).
            const sent = chip("Sent", "success");
            sent.setAttribute("tabindex", "-1");
            take.replaceWith(sent); sent.focus(); announce(g.said); }
          catch (e) { problem(e.message, take); take.disabled = false; }
        });
        return el("li", { class: "row row--no-lead" }, el("div", {}, el("div", { class: "row__title", text: x.title }),
          el("div", { class: "row__meta", text: [x.quality, x.size ? formatBytes(x.size) : "", x.seeders != null ? `${x.seeders} seeders` : "", x.site, x.languages.join(", ")].filter(Boolean).join(" · ") }),
          x.why_not.length ? el("div", { class: "row__meta", text: `Reelix would not take it: ${x.why_not.join("; ")}` }) : null),
          el("div", { class: "row__side" }, x.accepted ? null : chip("Not accepted", "warning"), take));
      })) : el("p", { text: "No site has it at the moment. Reelix keeps searching while it is wanted." }));
    } catch (e) { results.replaceChildren(el("p", { text: e.message })); }
    finally { find.disabled = false; }
  });
  body.replaceChildren(
    el("div", { class: "lib-detail" }, d.poster ? el("img", { src: d.poster, alt: "", class: "cover", loading: "lazy", onerror: (e) => e.target.remove() }) : null,
      el("div", { class: "stack-2" }, d.overview ? el("p", { text: d.overview }) : null,
        facts.length ? el("dl", { class: "facts" }, ...facts.flatMap(([k, v]) => [el("dt", { text: k }), el("dd", { text: String(v) })])) : null,
        d.href ? el("a", { href: d.href, text: "Open its page" }) : null)),
    el("h3", { text: "What Reelix last did" }),
    d.history.length ? el("ul", { class: "rows" }, d.history.map((h) => el("li", { class: "row row--no-lead" },
      el("div", {}, el("div", { class: "row__title", text: h.what }), el("div", { class: "row__meta", text: [h.when, h.release].filter(Boolean).join(" · ") })))))
      : el("p", { class: "muted", text: "Nothing yet: Reelix has not found it on any site." }),
    el("div", { class: "actions" }, find), results);
}

async function wantedLoad(more = false) {
  const list = $("#wanted-list");
  if (!more) { wantedState.page = 1; wantedState.items = []; wantedState.chosen.clear(); wantedState.lastPicked = null; list.replaceChildren(el("li", { class: "muted", text: "Asking Reelix…" })); }
  try {
    const r = await api(`/api/wanted?which=${WHICH}&kind=${wantedState.kind}&page=${wantedState.page}`);
    wantedState.total = r.total;
    wantedState.items.push(...r.items);
    if (!more) list.replaceChildren();
    const added = r.items.map(wantedRow);
    list.append(...added);
    if (!wantedState.items.length) list.replaceChildren(el("li", { class: "empty", id: "wanted-empty", tabindex: "-1", text: WHICH === "missing" ? "Nothing is wanted." : "Everything is at the quality wanted." }));
    const noun = W_NOUN[wantedState.kind] || ["item", "items"];
    $("#wanted-summary").textContent = `${r.total.toLocaleString("en-GB")} ${r.total === 1 ? noun[0] : noun[1]}${WHICH === "missing" ? " wanted" : " below quality"}`;
    if (!more) announce($("#wanted-summary").textContent);  // Show more says its own (SharedComponents.loadMore)
    $("#wanted-more").hidden = wantedState.items.length >= r.total;
    $("#wanted-all").disabled = !r.total;
  } catch (e) {
    wantedState.items = [];
    list.replaceChildren(el("li", {}, notice(e.status === 400 ? "info" : "danger", "Reelix could not be asked", e.message)));
  }
  wantedSelection();
}

async function wantedSearch(ids, button) {
  if (!ids.length) {
    const ok = await confirmDialog({ title: "Search for everything on this list?", confirm: "Search all",
      message: `Reelix searches for all ${wantedState.total.toLocaleString("en-GB")} a few at a time, so the sites are not overloaded. It can take a while for a long list.` });
    if (!ok) return;
  }
  if (button) button.disabled = true;
  try {
    const r = await api("/api/wanted/search", { method: "POST", body: { which: WHICH, kind: wantedState.kind, ids } });
    // A search started happens elsewhere and later, so it stays a toast (section 10, Toasts).
    toast(r.said);
    return true;
  } catch (e) { problem(e.message, button); return false; }
  finally { if (button) button.disabled = false; }
}

async function downloadNow(w, name, button) {
  const ok = await confirmDialog({ title: `Download ${name} now?`, confirm: "Download now",
    message: "Download hours have paused downloads. Reelix searches for this one now, and it downloads as soon as it is found while everything else stays paused. Then downloads pause again until the hours start." });
  if (!ok) return;
  button.disabled = true;
  try { toast((await api("/api/downloads/now", { method: "POST", body: { kind: wantedState.kind, id: w.id, title: name } })).said); }
  catch (e) { problem(e.message, button); button.disabled = false; }
}

// Bulk actions (DASH-524; owner, 22 November 2026: "I want the same bulk selections on Activity > Wanted"): the
// download queue's pattern (downloads.js). A box on each row and Select all in the toolbar; the selection bar at the
// foot of the list offers what the rows offer one at a time (Search, and Download now while download hours pause
// downloads) and Stop following, which asks first as it takes the rows off the list. Focus goes to Select all, or to
// the empty list's words, when the bar closes. Only the rows shown so far can be ticked; a new list starts clear.

function wantedNoun(n) {
  const [one, many] = W_NOUN[wantedState.kind] || ["item", "items"];
  return `${n.toLocaleString("en-GB")} ${n === 1 ? one : many}`;
}
function wantedName(w) { return w.detail ? `${w.title}, ${w.detail}` : w.title; }

function wantedPick(id, on, range) {
  const st = wantedState;
  const list = st.items.map((i) => i.id);
  const from = list.indexOf(st.lastPicked), to = list.indexOf(id);
  const ids = range && from >= 0 && to >= 0 ? list.slice(Math.min(from, to), Math.max(from, to) + 1) : [id];
  ids.forEach((i) => (on ? st.chosen.add(i) : st.chosen.delete(i)));
  st.lastPicked = id;
  wantedSelection();
}

function wantedSelection() {
  const st = wantedState;
  const n = st.chosen.size, total = st.items.length;
  $$("#wanted-list .dl-pick__box").forEach((b) => { b.checked = st.chosen.has(Number(b.value)); b.disabled = st.busy; });
  const all = $("#select-all");
  all.disabled = !total || st.busy;
  all.checked = total > 0 && n === total;
  all.indeterminate = n > 0 && n < total;
  all.closest("label").hidden = !total;
  const bar = $("#selection-bar");
  if (st.busy) return;
  const sig = `${n}:${st.paused}`;
  if (bar.dataset.sig === sig) return; // the same choice of actions: the buttons stay, and so does focus on them
  bar.dataset.sig = sig;
  bar.hidden = !n;
  if (!n) return;
  $("#selection-text").textContent = `${wantedNoun(n)} selected`;
  const button = (iconName, text, action, cls = "btn") => {
    const b = el("button", { type: "button", class: cls }, icon(iconName), text);
    b.addEventListener("click", () => action(b));
    return b;
  };
  $("#selection-actions").replaceChildren(...[
    button("search", "Search", wantedBulkSearch, "btn btn--primary"),
    st.paused && ["movie", "episode"].includes(st.kind) ? button("zap", "Download now", wantedBulkNow) : null,
    button("eye-off", "Stop following", wantedBulkStop),
    button("x", "Clear selection", () => { wantedClear(); announce("Selection cleared"); })].filter(Boolean));
}

// The bar closes: focus goes to Select all, or to the empty list's words when nothing is left to tick.
function wantedClear() {
  wantedState.chosen.clear();
  wantedSelection();
  const all = $("#select-all");
  if (!all.closest("label").hidden) all.focus(); else $("#wanted-empty")?.focus();
}

function wantedBusy(on) {
  const bar = $("#selection-bar");
  wantedState.busy = on;
  if (on) bar.setAttribute("aria-busy", "true"); else { bar.removeAttribute("aria-busy"); delete bar.dataset.sig; }
  $$("button", bar).forEach((b) => { b.disabled = on; });
  wantedSelection();
}

function wantedChosen() { return wantedState.items.filter((i) => wantedState.chosen.has(i.id)); }

async function wantedBulkSearch(button) {
  if (await wantedSearch([...wantedState.chosen], button)) wantedClear();
}

async function wantedBulkStop() {
  const list = wantedChosen(), one = list.length === 1;
  const ok = await confirmDialog({ title: `Stop following ${wantedNoun(list.length)}?`, confirm: "Stop following",
    message: `Reelix stops searching for ${one ? "it" : "them"}, so ${one ? "it leaves" : "they leave"} this list. Nothing is deleted, and you can follow ${one ? "it" : "them"} again in the Library.` });
  if (!ok) return;
  wantedBusy(true);
  $("#selection-text").textContent = "Working…";
  let said = "", failed = "";
  try { said = (await api("/api/wanted/stop", { method: "POST", body: { kind: wantedState.kind, ids: list.map((i) => i.id) } })).said; }
  catch (e) { failed = e.message; }
  wantedBusy(false);
  if (failed) { $("button", $("#selection-bar"))?.focus(); window.SharedComponents.toast.error(failed.replace(/\.$/, "")); return; }
  await wantedLoad(); // a new list, so nothing is ticked and the bar has closed
  wantedClear();
  toast(said);
}

// Download now for several (DASH-171): one at a time, as each is a search of its own, counted in the bar.
async function wantedBulkNow() {
  const list = wantedChosen(), one = list.length === 1;
  const ok = await confirmDialog({ title: `Download ${wantedNoun(list.length)} now?`, confirm: "Download now",
    message: `Download hours have paused downloads. Reelix searches for ${one ? "this one" : "these"} now, and ${one ? "it downloads" : "they download"} as soon as ${one ? "it is" : "they are"} found while everything else stays paused. Then downloads pause again until the hours start.` });
  if (!ok) return;
  wantedBusy(true);
  const failed = [];
  for (const [n, w] of list.entries()) {
    $("#selection-text").textContent = `Working on ${n + 1} of ${list.length}…`;
    try {
      await api("/api/downloads/now", { method: "POST", body: { kind: wantedState.kind, id: w.id, title: wantedName(w) } });
      wantedState.chosen.delete(w.id);
    } catch (e) { failed.push(`${wantedName(w)}: ${e.message}`); }
  }
  wantedBusy(false);
  const done = list.length - failed.length;
  const said = [done ? `Reelix is searching for ${wantedNoun(done)} now.` : "", failed.length ? `Not started: ${wantedNoun(failed.length)}.` : ""].filter(Boolean).join(" ");
  // Focus: the bar's first button while some are still ticked; otherwise Select all.
  if (failed.length) { $("button", $("#selection-bar"))?.focus(); window.SharedComponents.toast.error(`${said} ${failed.join(" ")}`.replace(/\.$/, "")); }
  else { wantedClear(); toast(said); }
}

function wantedSelectAll() {
  const all = $("#select-all"), st = wantedState;
  if (all.checked) st.items.forEach((i) => st.chosen.add(i.id)); else st.chosen.clear();
  st.lastPicked = null;
  wantedSelection();
  announce(all.checked ? `${wantedNoun(st.chosen.size)} selected` : "Selection cleared");
}

startPage().then(async () => {
  try { wantedState.paused = (await api("/api/schedule")).mode === "pause"; } catch { wantedState.paused = false; }
  if (W_KIND) $(".page-head")?.after(wantedTabs());
  $("#select-all").addEventListener("change", wantedSelectAll);
  $("#wanted-all").addEventListener("click", (e) => wantedSearch([], e.currentTarget));
  // Show more, and more by itself near the end (DASH-277, UX-52): the button moves focus to the first new row.
  loadMore($("#wanted-more"), {
    items: () => $$("#wanted-list > li"),
    said: (n) => `${n} more shown, ${wantedState.items.length} of ${wantedState.total}`,
    load: async () => { const before = wantedState.items.length; wantedState.page += 1; await wantedLoad(true); return wantedState.items.length - before; },
  });
  wantedLoad();
});
