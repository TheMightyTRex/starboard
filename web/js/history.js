// Activity, History (DASH-159): what Reelix found, downloaded, added and removed, newest first, with a filter; and
// the refused list (releases Reelix will not download again), with Take off the list. A page at a time.

const historyState = { which: "all", page: 1, items: 0, total: 0 };

function historyWhen(iso) {
  return iso ? new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "";
}

function historyRow(h) {
  const title = h.what ? (h.href ? el("a", { href: h.href, text: h.what }) : h.what) : h.release;
  const meta = [historyWhen(h.date), h.what ? h.release : "", h.quality, h.where].filter(Boolean).join(" · ");
  return el("li", { class: "row row--no-lead" },
    el("div", {}, el("h3", { class: "row__title" }, title), el("div", { class: "row__meta", text: meta }),
      h.message ? el("div", { class: "row__meta", text: h.message }) : null),
    el("div", { class: "row__side" }, chip(h.event, h.tone)));
}

function refusedRow(b) {
  const off = el("button", { type: "button", class: "btn btn--quiet btn--compact" }, "Take off the list",
    el("span", { class: "visually-hidden", text: ` ${b.release}` }));
  off.addEventListener("click", async () => {
    const ok = await confirmDialog({ title: "Take it off the refused list?", confirm: "Take off",
      message: `Reelix may download ${b.release} again the next time it searches${b.what ? ` for ${b.what}` : ""}.` });
    if (!ok) return;
    off.disabled = true;
    try { toast((await api("/api/reelix-history/refused/take-off", { method: "POST", body: { id: b.id } })).said); historyLoad(); }
    catch (e) { problem(e.message, off); off.disabled = false; }
  });
  return el("li", { class: "row row--no-lead" },
    el("div", {}, el("h3", { class: "row__title" }, b.what ? (b.href ? el("a", { href: b.href, text: b.what }) : b.what) : b.release),
      el("div", { class: "row__meta", text: [historyWhen(b.date), b.what ? b.release : "", b.quality, b.where].filter(Boolean).join(" · ") }),
      b.message ? el("div", { class: "row__meta", text: `Why: ${b.message}` }) : null),
    el("div", { class: "row__side" }, off));
}

async function historyLoad(more = false) {
  const list = $("#history-list");
  if (!more) { historyState.page = 1; historyState.items = 0; list.replaceChildren(el("li", { class: "muted", text: "Asking Reelix…" })); }
  try {
    const refused = historyState.which === "refused";
    const r = await api(refused ? `/api/reelix-history/refused?page=${historyState.page}` : `/api/reelix-history?which=${historyState.which}&page=${historyState.page}`);
    if (!more) list.replaceChildren();
    const added = r.items.map(refused ? refusedRow : historyRow);
    list.append(...added);
    if (more) focusFirstNew(added[0]);
    historyState.items += r.items.length;
    historyState.total = r.total;
    if (!historyState.items) list.replaceChildren(el("li", { class: "empty", text: refused ? "Nothing is on the refused list." : "Nothing has happened yet." }));
    $("#history-more").hidden = historyState.items >= r.total;
    setTimeout(() => announce(more ? `${r.items.length} more shown` : $("#history-summary").textContent), 0);
    $("#history-summary").textContent = refused
      ? `${r.total.toLocaleString("en-GB")} ${r.total === 1 ? "release" : "releases"} Reelix will not download again`
      : "What Reelix found, downloaded, renamed and removed, newest first.";
  } catch (e) {
    list.replaceChildren(el("li", {}, el("div", { class: "notice", role: "status" }, icon("info"),
      el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: "Reelix could not be asked" }), el("p", { text: e.message })))));
  }
}

startPage().then(() => {
  // One of several (DASH-309, R4): a segmented control; the radios keep focus and the arrow keys.
  $("#history-filters").addEventListener("change", (e) => { historyState.which = e.target.value; historyLoad(); });
  $("#history-more").addEventListener("click", () => { historyState.page += 1; historyLoad(true); });
  autoLoadMore($("#history-more"), async () => { const before = historyState.items; historyState.page += 1; await historyLoad(true); return historyState.items - before; }, "more");
  historyLoad();
});

// How much history to keep, and Delete history (owner, 12 November 2026). Reelix keeps its own copy until it can
// delete history; Starboard then shows only what is newer. A setting row with its saved note, and a danger section,
// at the end of the page, so the toolbar stays straight under the heading (DASH-309, R5 and R8; Settings patterns 2
// and 9).
function historyKeep() {
  const choices = [[0, "Everything"], [365, "A year"], [90, "90 days"], [30, "30 days"], [7, "A week"]];
  const select = el("select", { class: "select", id: "history-keep", "aria-labelledby": "history-keep-l" }, choices.map(([v, t]) => el("option", { value: String(v), text: t })));
  const keptNote = el("span", { class: "saved-note", hidden: true });
  const del = el("button", { type: "button", class: "btn btn--danger" }, icon("trash-2"), "Delete history");
  const delNote = el("span", { class: "saved-note", hidden: true });
  select.addEventListener("change", async () => {
    try { await api("/api/reelix-history/keep", { method: "PUT", body: { days: Number(select.value) } }); window.SharedComponents.savedNote(keptNote); historyLoad(); }
    catch (e) { problem(e.message, select); }
  });
  del.addEventListener("click", async () => {
    if (!await confirmDialog({ title: "Delete the history?", confirm: "Delete history", danger: true,
      message: "Everything on this page before now goes. Your films, series, music and books are not touched, and Reelix still knows what it has." })) return;
    del.disabled = true;
    try { window.SharedComponents.savedNote(delNote, (await api("/api/reelix-history/delete", { method: "POST" })).said); historyLoad(); }
    catch (e) { problem(e.message, del); }
    finally { del.disabled = false; del.focus(); }
  });
  const row = (id, label, hint, ...control) => el("ul", { class: "settings-rows" }, el("li", { class: "setting" },
    el("div", { class: "setting__text" }, el("span", { class: "setting__label", id, text: label }), el("span", { class: "setting__hint", text: hint })),
    el("div", { class: "setting__control" }, ...control)));
  const part = (id, title, ...content) => el("section", { class: "settings-section history-keep", "aria-labelledby": `${id}-h` },
    el("div", { class: "settings-section__head" }, el("h2", { id: `${id}-h`, text: title })), ...content);
  const danger = part("history-delete", "Delete history",
    row("history-delete-l", "Delete everything on this page", "Your films, series, music and books are not touched.", del, delNote));
  danger.classList.add("settings-section--danger");
  return { select, nodes: [
    part("history-keeping", "Keeping history", row("history-keep-l", "Keep history for", "Older events leave this page. This applies at once.", select, keptNote)),
    danger] };
}
document.addEventListener("DOMContentLoaded", () => {
  const end = document.querySelector("#history-more")?.closest(".actions");
  if (!end) return;
  const k = historyKeep();
  end.after(...k.nodes);
  api("/api/reelix-history?which=all&page=1").then((c) => { k.select.value = String(c.keep_days || 0); }).catch(() => {});
});
