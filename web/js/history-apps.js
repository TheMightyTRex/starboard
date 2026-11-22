// Activity, History, Across apps (DASH-68): what was added, what failed and what was upgraded across the apps, newest
// first, from Starboard's own small file (the newest 500 entries). Nothing is asked for until this page is opened.

const acrossState = { which: "all", page: 1, items: 0, total: 0 };

function acrossRow(h) {
  const meta = [historyWhenAcross(h.when), h.what.includes(h.app) ? "" : h.app].filter(Boolean).join(" · ");
  return el("li", { class: "row row--no-lead" },
    el("div", {}, el("h3", { class: "row__title", text: h.what || h.app }), el("div", { class: "row__meta", text: meta }),
      h.detail ? el("div", { class: "row__meta", text: h.detail }) : null),
    el("div", { class: "row__side" }, chip(h.event, h.tone)));
}

function historyWhenAcross(iso) {
  return iso ? new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "";
}

const ACROSS_EMPTY = { all: "Nothing has happened yet. Entries arrive as your apps add, fail or upgrade something.",
  added: "Nothing has been added yet.", failed: "Nothing has failed.", upgraded: "Nothing has been upgraded yet." };

async function acrossLoad(more = false) {
  const list = $("#across-list");
  if (!more) { acrossState.page = 1; acrossState.items = 0; list.replaceChildren(el("li", { class: "muted", text: "Reading the history…" })); }
  try {
    const r = await api(`/api/activity-history?which=${acrossState.which}&page=${acrossState.page}`);
    if (!more) list.replaceChildren();
    list.append(...r.items.map(acrossRow));
    acrossState.items += r.items.length;
    acrossState.total = r.total;
    if (!acrossState.items) list.replaceChildren(el("li", { class: "empty", text: ACROSS_EMPTY[acrossState.which] }));
    $("#across-more").hidden = acrossState.items >= r.total;
    const n = r.total.toLocaleString("en-GB");
    $("#across-summary").textContent = `${n} ${r.total === 1 ? "entry" : "entries"}, newest first. Starboard keeps the newest ${r.cap.toLocaleString("en-GB")}.`;
    if (!more) {
      $("#across-notes").hidden = !(r.notes || []).length;
      $("#across-notes").replaceChildren(...(r.notes || []).map((text) => el("div", { class: "notice", role: "status" }, icon("info"),
        el("div", { class: "notice__body" }, el("p", { text })))));
      setTimeout(() => announce($("#across-summary").textContent), 0);  // Show more says its own (UX-52)
    }
  } catch (e) {
    list.replaceChildren(el("li", {}, el("div", { class: "notice", role: "status" }, icon("info"),
      el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: "The history could not be read" }), el("p", { text: e.message })))));
  }
}

// Delete history: a danger section at the end of the page (Settings patterns 2 and 9), as on History.
function acrossDelete() {
  const del = el("button", { type: "button", class: "btn btn--danger" }, icon("trash-2"), "Delete history");
  const note = el("span", { class: "saved-note", hidden: true });
  del.addEventListener("click", async () => {
    if (!await confirmDialog({ title: "Delete the history across apps?", confirm: "Delete history", danger: true,
      message: "Everything on this page goes. Your apps, your library and each app's own history are not touched." })) return;
    del.disabled = true;
    try { window.SharedComponents.savedNote(note, (await api("/api/activity-history/delete", { method: "POST" })).said); acrossLoad(); }
    catch (e) { problem(e.message, del); }
    finally { del.disabled = false; del.focus(); }
  });
  const section = el("section", { class: "settings-section history-keep settings-section--danger", "aria-labelledby": "across-delete-h" },
    el("div", { class: "settings-section__head" }, el("h2", { id: "across-delete-h", text: "Delete history" })),
    el("ul", { class: "settings-rows" }, el("li", { class: "setting" },
      el("div", { class: "setting__text" }, el("span", { class: "setting__label", text: "Delete everything on this page" }),
        el("span", { class: "setting__hint", text: "Your apps and your library are not touched." })),
      el("div", { class: "setting__control" }, del, note))));
  return section;
}

startPage().then(() => {
  // One of several (DASH-309, R4): a segmented control; the radios keep focus and the arrow keys.
  $("#across-filters").addEventListener("change", (e) => { acrossState.which = e.target.value; acrossLoad(); $("#across-more")._loadMore?.reset(); });
  loadMore($("#across-more"), {
    items: () => $$("#across-list > li"),
    load: async () => { const before = acrossState.items; acrossState.page += 1; await acrossLoad(true); return acrossState.items - before; },
  });
  $("#across-more").closest(".actions").after(acrossDelete());
  acrossLoad();
});
