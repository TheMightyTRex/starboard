// Wanted (DASH-207): Missing, and Below the quality wanted, for films and episodes, from Reelix. Tick some and
// search for them, or search for everything on the list. A page at a time, with Show more.

const WHICH = document.querySelector("[data-wanted]")?.dataset.wanted || "missing";
const wantedState = { kind: "movie", page: 1, total: 0, items: [] };

function wantedRow(w) {
  const box = el("input", { type: "checkbox", value: String(w.id), "aria-label": `Tick ${w.title}${w.detail ? `, ${w.detail}` : ""}` });
  const when = w.date ? new Date(w.date).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "";
  const meta = [w.detail, when, WHICH === "cutoff" && w.quality ? `Has ${w.quality}, wants ${w.cutoff || "better"}` : ""].filter(Boolean).join(" · ");
  const search = el("button", { type: "button", class: "btn btn--quiet btn--compact", onclick: (e) => wantedSearch([w.id], e.currentTarget) },
    icon("search"), "Search", el("span", { class: "visually-hidden", text: ` for ${w.title}${w.detail ? `, ${w.detail}` : ""}` }));
  return el("li", { class: "row" }, box,
    el("div", {}, el("h3", { class: "row__title" }, w.href ? el("a", { href: w.href, text: w.year ? `${w.title} (${w.year})` : w.title }) : w.title),
      el("div", { class: "row__meta", text: meta })),
    el("div", { class: "row__side" }, search));
}

async function wantedLoad(more = false) {
  const list = $("#wanted-list");
  if (!more) { wantedState.page = 1; wantedState.items = []; list.replaceChildren(el("li", { class: "muted", text: "Asking Reelix…" })); }
  try {
    const r = await api(`/api/wanted?which=${WHICH}&kind=${wantedState.kind}&page=${wantedState.page}`);
    wantedState.total = r.total;
    wantedState.items.push(...r.items);
    if (!more) list.replaceChildren();
    list.append(...r.items.map(wantedRow));
    if (!wantedState.items.length) list.replaceChildren(el("li", { class: "empty", text: WHICH === "missing" ? "Nothing is missing." : "Everything is at the quality wanted." }));
    const noun = wantedState.kind === "movie" ? ["film", "films"] : ["episode", "episodes"];
    $("#wanted-summary").textContent = `${r.total.toLocaleString("en-GB")} ${r.total === 1 ? noun[0] : noun[1]}${WHICH === "missing" ? " missing" : " below the quality wanted"}`;
    $("#wanted-more").hidden = wantedState.items.length >= r.total;
    $("#wanted-all").disabled = !r.total;
  } catch (e) {
    list.replaceChildren(el("li", {}, el("div", { class: "notice", "data-tone": e.status === 400 ? null : "danger", role: "status" }, icon("info"),
      el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: "Reelix could not be asked" }), el("p", { text: e.message })))));
  }
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
    toast(r.said);
    $$("#wanted-list input[type=checkbox]").forEach((b) => { b.checked = false; });
    wantedTicked();
  } catch (e) { problem(e.message, button); }
  finally { if (button) button.disabled = false; }
}

function wantedTicked() {
  const n = $$("#wanted-list input[type=checkbox]:checked").length;
  $("#wanted-ticked").disabled = !n;
  $("#wanted-ticked span").textContent = n ? `Search for the ${n} ticked` : "Search for the ticked ones";
}

startPage().then(() => {
  $$('input[name="wanted-kind"]').forEach((r) => r.addEventListener("change", () => { wantedState.kind = r.value; wantedLoad(); wantedTicked(); }));
  $("#wanted-list").addEventListener("change", wantedTicked);
  $("#wanted-ticked").addEventListener("click", (e) => wantedSearch($$("#wanted-list input[type=checkbox]:checked").map((b) => Number(b.value)), e.currentTarget));
  $("#wanted-all").addEventListener("click", (e) => wantedSearch([], e.currentTarget));
  $("#wanted-more").addEventListener("click", () => { wantedState.page += 1; wantedLoad(true); });
  wantedLoad();
});
