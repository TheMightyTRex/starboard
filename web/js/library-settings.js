// Settings, General: the Library views saved as defaults (DASH-163), with a reset. Uses settings.js's section helpers.

async function drawLibraryViews() {
  const box = $("#library-views");
  if (!box) return;
  let views = {};
  try { views = (await api("/api/library/views")).views; } catch { return; }
  const names = { films: "Films", tv: "TV", music: "Music", radio: "Radio", books: "Books", audiobooks: "Audiobooks" };
  const sorts = { az: "A to Z", added: "Recently added", year: "Year" };
  const saved = Object.entries(views).filter(([tab, v]) => names[tab] && Object.keys(v).length);
  const words = (v) => [sorts[v.sort || "az"], v.layout === "list" ? "list" : `${v.size || "medium"} covers`, v.chip ? "with a filter" : ""].filter(Boolean).join(", ");
  const note = savedNote("library-views-saved");
  const reset = el("button", { type: "button", class: "btn", disabled: !saved.length, text: "Reset Library views" });
  reset.addEventListener("click", async () => {
    try {
      await api("/api/library/views", { method: "DELETE" });
      await drawLibraryViews();
      $("#library-views button")?.focus();
      showSaved("library-views-saved", "Library views reset");
    } catch (e) { problem(e.message, reset); }
  });
  box.replaceChildren(section("library-views-s", "Library views",
    "How each kind in the Library opens. Save a view with Save this view as default on a Library page.",
    el("ul", { class: "settings-rows" },
      settingRow("Saved views", saved.length ? saved.map(([tab, v]) => `${names[tab]}: ${words(v)}`).join(". ") + "." : "None saved: every kind opens A to Z with medium covers.",
        el("div", { class: "actions" }, reset, note)))));
}

// Discover's rows (DASH-303): which rows each area shows and their order. A sortable list (UX-51) with a tick for
// each row; a change applies at once with the saved note (settings pattern 2). Put back the standard rows undoes it.
const DISCOVER_AREAS = [["films", "Films"], ["tv", "TV"], ["music", "Music"], ["books", "Books"], ["audiobooks", "Audiobooks"], ["radio", "Radio"]];
let discoverArea = new URLSearchParams(location.search).get("discover") || "films";
if (!DISCOVER_AREAS.some(([t]) => t === discoverArea)) discoverArea = "films";

async function drawDiscoverRows(focusId = "") {
  const box = $("#discover-rows");
  if (!box) return;
  const area = el("select", { class: "select", id: "discover-area" }, DISCOVER_AREAS.map(([v, t]) => el("option", { value: v, text: t, selected: v === discoverArea })));
  area.addEventListener("change", () => { discoverArea = area.value; drawDiscoverRows("discover-area"); });
  const body = el("div", { class: "stack-4", id: "discover-rows-body" }, el("p", { class: "muted", text: "Asking Reelix…" }));
  const note = savedNote("discover-rows-saved");
  const sec = section("discover-rows-s", "Discover rows",
    "Which rows each area of Discover shows, and their order. Changes apply at once.",
    el("ul", { class: "settings-rows" }, settingRow("Area", "The Discover page to change.", area)), body);
  sec.id = "discover-rows-s";  // the topic tab keeps its place when the area changes; Discover's pages link here
  box.replaceChildren(sec);
  if (focusId) document.getElementById(focusId)?.focus();
  let d;
  try { d = await api(`/api/library/discover-layout?tab=${discoverArea}`); }
  catch (e) {
    body.replaceChildren(emptyState(e.status === 409 ? "Reelix is not added yet" : "The rows did not load",
      e.status === 409 ? "Discover's rows come from Reelix. Add Reelix with its key in Manage apps first." : e.message));
    return;
  }
  const name = DISCOVER_AREAS.find(([t]) => t === discoverArea)[1];
  const move = (label, dir) => el("button", { type: "button", class: "icon-btn", "data-move": dir, "aria-label": `Move ${label} ${dir}` }, icon(dir === "up" ? "arrow-up" : "arrow-down"));
  const list = el("ol", { class: "sortable", id: "discover-rows-list", "aria-label": `${name}: Discover rows, top first` },
    d.rows.map((r) => {
      const tick = el("input", { type: "checkbox", id: `discover-row-${r.id.replace(/[^\w-]+/g, "-")}`, checked: r.shown });
      return el("li", { class: r.shown ? "sortable__row" : "sortable__row sortable__row--off", "data-value": r.id },
        el("span", { class: "sortable__handle", "aria-hidden": "true" }, icon("grip-vertical")),
        el("label", { class: "sortable__label check" }, tick, el("span", { class: "check__text", text: r.genre ? `${r.title} (genre)` : r.title })),
        el("span", { class: "sortable__moves" }, move(r.title, "up"), move(r.title, "down")));
    }));
  const save = async (control) => {
    const rows = [...list.children];
    try {
      await api("/api/library/discover-layout?tab=" + discoverArea, { method: "POST",
        body: { order: rows.map((r) => r.dataset.value), hidden: rows.filter((r) => !r.querySelector("input").checked).map((r) => r.dataset.value) } });
      reset.disabled = false;
      showSaved("discover-rows-saved", "Saved");
    } catch (e) {
      if (control?.type === "checkbox") { control.checked = true; control.closest(".sortable__row").classList.remove("sortable__row--off"); }
      problem(e.message, control || list);
    }
  };
  list.addEventListener("change", (e) => {
    if (e.target.type !== "checkbox") return;
    e.target.closest(".sortable__row").classList.toggle("sortable__row--off", !e.target.checked);
    save(e.target);
  });
  list.addEventListener("sortable-change", () => save(null));
  const reset = el("button", { type: "button", class: "btn btn--quiet", id: "discover-rows-reset", disabled: !d.changed, text: "Put back the standard rows" });
  reset.addEventListener("click", async () => {
    try {
      await api(`/api/library/discover-layout?tab=${discoverArea}`, { method: "DELETE" });
      await drawDiscoverRows("discover-rows-reset");
      showSaved("discover-rows-saved", "Standard rows put back");
    } catch (e) { problem(e.message, reset); }
  });
  body.replaceChildren(el("p", { class: "small muted", text: d.rows.some((r) => r.genre) ? "Tick the rows to show. The genre rows, such as Comedy, start unticked. Move them with the arrows, or drag them by the handle." : "Tick the rows to show. Move them with the arrows, or drag them by the handle." }),
    list, el("div", { class: "actions" }, reset, note), el("p", { class: "small" }, el("a", { href: `/discover-${discoverArea}.html`, text: `Open Discover, ${name}` })));
  window.SharedComponents.setupSortables(body);
  if (focusId) document.getElementById(focusId)?.focus();
}

document.addEventListener("DOMContentLoaded", () => setTimeout(drawLibraryViews, 0));
document.addEventListener("DOMContentLoaded", () => setTimeout(drawDiscoverRows, 0));
