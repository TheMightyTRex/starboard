// Discover, On demand history (owner, 11 November 2026, DASH-324): what you started watching in On demand, newest
// first, with a Films or Series filter. Add to wanted puts the film or series in Reelix (searching for it) so it comes
// into your own library; Remove takes it out of the history.

let odKind = "all";
const plural = (n, [one, many]) => `${n.toLocaleString("en-GB")} ${n === 1 ? one : many}`;
const notice = (tone, title, text) => el("div", { class: "notice", "data-tone": tone === "info" ? null : tone, role: "status" },
  icon(tone === "danger" ? "circle-x" : "info"), el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: title }), el("p", { text })));

function odRow(it) {
  const when = it.last ? `Last watched ${new Date(it.last.replace(" ", "T")).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}` : "";
  const meta = [it.kind === "movie" ? "Film" : "Series", it.year, it.episode ? `up to ${it.episode}` : "", when].filter(Boolean).join(" · ");
  const want = it.in_library
    ? (it.href ? el("a", { class: "btn btn--quiet btn--compact", href: it.href }, icon("library"), "In your library") : chip("In your library", "success"))
    : el("button", { type: "button", class: "btn btn--compact", onclick: (e) => odWant(it, e.currentTarget), disabled: !it.key },
      icon("plus"), "Add to wanted", el("span", { class: "visually-hidden", text: ` ${it.title}` }));
  const forget = el("button", { type: "button", class: "btn btn--quiet btn--compact", onclick: (e) => odForget(it, e.currentTarget) },
    icon("x"), "Remove", el("span", { class: "visually-hidden", text: ` ${it.title} from the history` }));
  const cover = el("div", { class: "cover cover--result", "aria-hidden": "true" },
    it.poster ? el("img", { src: it.poster, alt: "", loading: "lazy", onerror: (e) => e.target.remove() }) : el("span", { class: "lib-cover-title", text: it.title }));
  return el("li", { class: "row lib-row" }, cover,
    el("div", {}, el("h2", { class: "row__title", text: it.title }), el("div", { class: "row__meta", text: meta })),
    el("div", { class: "row__side" }, want, forget));
}

async function odLoad() {
  const list = $("#od-list");
  try {
    const r = await api(`/api/ondemand/history?kind=${odKind}`);
    $("#od-summary").textContent = r.items.length
      ? `${plural(r.items.length, odKind === "movie" ? ["film", "films"] : odKind === "series" ? ["series", "series"] : ["title", "titles"])} you started watching in On demand.`
      : "What you started watching in On demand.";
    list.replaceChildren(...(r.items.length ? r.items.map(odRow)
      : [el("li", { class: "empty", text: odKind === "all" ? "Nothing watched in On demand yet." : "Nothing of this kind watched yet." })]));
  } catch (e) {
    list.replaceChildren(el("li", {}, notice(e.status === 404 ? "info" : "danger", "On demand history is not available", e.message)));
  }
}

async function odWant(it, button) {
  button.disabled = true;
  try { toast((await api("/api/ondemand/history/want", { method: "POST", body: { kind: it.kind, id: it.id } })).said); odLoad(); }
  catch (e) { problem(e.message, button); button.disabled = false; }
}

async function odForget(it, button) {
  const ok = await confirmDialog({ title: `Remove ${it.title} from the history?`, confirm: "Remove",
    message: "On demand stops keeping it in its library at the next weekly update, unless a catalogue still lists it." });
  if (!ok) return;
  button.disabled = true;
  try { toast((await api("/api/ondemand/history/forget", { method: "POST", body: { id: it.id } })).said); odLoad(); }
  catch (e) { problem(e.message, button); button.disabled = false; }
}

startPage().then(() => {
  $$('input[name="od-kind"]').forEach((r) => r.addEventListener("change", () => { odKind = r.value; odLoad(); }));
  odLoad();
});
