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
    list.append(...r.items.map(refused ? refusedRow : historyRow));
    historyState.items += r.items.length;
    historyState.total = r.total;
    if (!historyState.items) list.replaceChildren(el("li", { class: "empty", text: refused ? "Nothing is on the refused list." : "Nothing has happened yet." }));
    $("#history-more").hidden = historyState.items >= r.total;
    $("#history-summary").textContent = refused
      ? `${r.total.toLocaleString("en-GB")} ${r.total === 1 ? "release" : "releases"} Reelix will not download again`
      : "What Reelix found, downloaded, renamed and removed, newest first.";
  } catch (e) {
    list.replaceChildren(el("li", {}, el("div", { class: "notice", role: "status" }, icon("info"),
      el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: "Reelix could not be asked" }), el("p", { text: e.message })))));
  }
}

startPage().then(() => {
  $$("#history-filters button").forEach((b) => b.addEventListener("click", () => {
    historyState.which = b.dataset.which;
    $$("#history-filters button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    historyLoad();
  }));
  $("#history-more").addEventListener("click", () => { historyState.page += 1; historyLoad(true); });
  historyLoad();
});
