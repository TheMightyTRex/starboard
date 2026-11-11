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
  // DASH-171: while download hours pause downloads, Download now gets this one straight away.
  const name = w.detail ? `${w.title}, ${w.detail}` : w.title;
  const now = wantedState.paused ? el("button", { type: "button", class: "btn btn--quiet btn--compact", onclick: (e) => downloadNow(w, name, e.currentTarget) },
    icon("zap"), "Download now", el("span", { class: "visually-hidden", text: ` ${name}` })) : null;
  const more = el("button", { type: "button", class: "btn btn--quiet btn--compact", onclick: (e) => wantedDetail(w, name, e.currentTarget) },
    icon("info"), "Details", el("span", { class: "visually-hidden", text: ` for ${name}` }));
  return el("li", { class: "row" }, box,
    el("div", {}, el("h3", { class: "row__title" }, w.href ? el("a", { href: w.href, text: w.year ? `${w.title} (${w.year})` : w.title }) : w.title),
      el("div", { class: "row__meta", text: meta })),
    el("div", { class: "row__side" }, more, search, now));
}

// DASH-305: a wanted film or episode in full, in a slide-out: picture, story, length, genres, the quality wanted, what
// Reelix last did for it, and See what Reelix can find (every site's releases, best first, with Get this one).
async function wantedDetail(w, name, opener) {
  const body = el("div", { class: "stack-4" }, el("p", { class: "muted", text: "Loading…" }));
  sidePanel({ title: name, body: [body], opener, wide: true });
  let d;
  try { d = await api(`/api/wanted/detail?kind=${wantedState.kind}&id=${w.id}${w.series_id ? `&series=${w.series_id}` : ""}`); }
  catch (e) { body.replaceChildren(el("p", { text: e.message })); return; }
  const facts = [["Year", d.year], ["Aired", d.aired], ["Length", d.runtime ? `${d.runtime} minutes` : ""], ["Genres", (d.genres || []).join(", ")],
    ["Quality wanted", d.profile]].filter(([, v]) => v);
  const results = el("div", { class: "stack-2", "aria-live": "polite" });
  const find = el("button", { type: "button", class: "btn btn--primary" }, icon("search"), "See what Reelix can find");
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
            take.replaceWith(chip("Sent", "success")); toast(g.said); }
          catch (e) { problem(e.message, take); take.disabled = false; }
        });
        return el("li", { class: "row row--no-lead" }, el("div", {}, el("div", { class: "row__title", text: x.title }),
          el("div", { class: "row__meta", text: [x.quality, x.size ? formatBytes(x.size) : "", x.seeders != null ? `${x.seeders} seeders` : "", x.site, x.languages.join(", ")].filter(Boolean).join(" · ") }),
          x.why_not.length ? el("div", { class: "row__meta", text: `Reelix would not take it: ${x.why_not.join("; ")}` }) : null),
          el("div", { class: "row__side" }, x.accepted ? null : chip("Turned down", "warning"), take));
      })) : el("p", { text: "No site has it at the moment. Reelix keeps looking while it is wanted." }));
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

async function downloadNow(w, name, button) {
  const ok = await confirmDialog({ title: `Download ${name} now?`, confirm: "Download now",
    message: "Download hours have paused downloads. Reelix searches for this one now, and it downloads as soon as it is found while everything else stays paused. Then downloads pause again until the hours start." });
  if (!ok) return;
  button.disabled = true;
  try { toast((await api("/api/downloads/now", { method: "POST", body: { kind: wantedState.kind, id: w.id, title: name } })).said); }
  catch (e) { problem(e.message, button); button.disabled = false; }
}

function wantedTicked() {
  const n = $$("#wanted-list input[type=checkbox]:checked").length;
  $("#wanted-ticked").disabled = !n;
  $("#wanted-ticked span").textContent = n ? `Search for the ${n} ticked` : "Search for the ticked ones";
}

startPage().then(async () => {
  try { wantedState.paused = (await api("/api/schedule")).mode === "pause"; } catch { wantedState.paused = false; }
  $$('input[name="wanted-kind"]').forEach((r) => r.addEventListener("change", () => { wantedState.kind = r.value; wantedLoad(); wantedTicked(); }));
  $("#wanted-list").addEventListener("change", wantedTicked);
  $("#wanted-ticked").addEventListener("click", (e) => wantedSearch($$("#wanted-list input[type=checkbox]:checked").map((b) => Number(b.value)), e.currentTarget));
  $("#wanted-all").addEventListener("click", (e) => wantedSearch([], e.currentTarget));
  $("#wanted-more").addEventListener("click", () => { wantedState.page += 1; wantedLoad(true); });
  autoLoadMore($("#wanted-more"), async () => { const before = wantedState.items.length; wantedState.page += 1; await wantedLoad(true); return wantedState.items.length - before; }, "more");
  wantedLoad();
});
