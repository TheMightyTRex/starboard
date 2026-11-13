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
// DASH-396 (owner, 13 November 2026: "might need a separate section for each in the settings"): its own level 2 page,
// Settings, General, Discover rows, with one section per area in the Discover menu's order, so topic tabs show one
// area at a time. An area asks Reelix for its rows only when its section is shown (lightweight rule).
const DISCOVER_AREAS = [["films", "Films"], ["tv", "TV"], ["music", "Music"], ["radio", "Radio"], ["books", "Books"], ["audiobooks", "Audiobooks"]];

function drawDiscoverAreas() {
  const box = $("#discover-areas");
  if (!box) return;
  // An old address (?discover=tv) opens that area's section.
  const want = new URLSearchParams(location.search).get("discover");
  if (DISCOVER_AREAS.some(([t]) => t === want) && !location.hash) history.replaceState(null, "", `${location.pathname}#dr-${want}`);
  box.replaceChildren(...onlyParts(box, DISCOVER_AREAS.map(([tab, name]) => discoverAreaSection(tab, name))));
}

function discoverAreaSection(tab, name) {
  const id = `dr-${tab}`;
  const body = el("div", { class: "stack-4", id: `${id}-body` }, el("p", { class: "muted", text: "Asking Reelix…" }));
  const sec = section(id, name, `Which rows Discover, ${name} shows, and their order. Changes apply at once.`, body);
  sec.id = id;  // Discover's pages link here (#dr-tv); the topic tab opens it
  const load = () => drawDiscoverArea(tab, name, body);
  if (!("IntersectionObserver" in window)) load();
  else discoverTopicsReady().then(() => {
    const watch = new IntersectionObserver((seen) => { if (seen.some((x) => x.isIntersecting)) { watch.disconnect(); load(); } }, { rootMargin: "200px" });
    watch.observe(sec);
  });
  return sec;
}

// The sections are watched once the topic tabs have hidden all but one (settings.js draws them after the session
// loads), so only the shown area asks Reelix. With topic tabs deactivated, each asks as it is scrolled to.
let discoverTopics = null;
function discoverTopicsReady() {
  if (discoverTopics) return discoverTopics;
  let off = false;
  try { off = localStorage.getItem("starboard.topic-tabs") === "off"; } catch { /* tabs on */ }
  discoverTopics = new Promise((done) => {
    if (off || $("#topic-tabs")) { done(); return; }
    const seen = new MutationObserver(() => { if ($("#topic-tabs")) { seen.disconnect(); done(); } });
    seen.observe(document.body, { childList: true, subtree: true });
    setTimeout(() => { seen.disconnect(); done(); }, 5000);  // no tabs after all (a page with fewer parts)
  });
  return discoverTopics;
}

async function drawDiscoverArea(tab, name, body, focusId = "") {
  const id = `dr-${tab}`;
  let d;
  try { d = await api(`/api/library/discover-layout?tab=${tab}`); }
  catch (e) {
    body.replaceChildren(emptyState(e.status === 409 ? "Reelix is not added yet" : "The rows did not load",
      e.status === 409 ? "Discover's rows come from Reelix. Add Reelix with its key in Manage apps first." : e.message));
    return;
  }
  const note = savedNote(`${id}-saved`);
  const move = (label, dir) => el("button", { type: "button", class: "icon-btn", "data-move": dir, "aria-label": `Move ${label} ${dir}` }, icon(dir === "up" ? "arrow-up" : "arrow-down"));
  const list = el("ol", { class: "sortable", id: `${id}-list`, "aria-label": `${name}: Discover rows, top first` },
    d.rows.map((r) => {
      const tick = el("input", { type: "checkbox", id: `${id}-row-${r.id.replace(/[^\w-]+/g, "-")}`, checked: r.shown });
      return el("li", { class: r.shown ? "sortable__row" : "sortable__row sortable__row--off", "data-value": r.id },
        el("span", { class: "sortable__handle", "aria-hidden": "true" }, icon("grip-vertical")),
        el("label", { class: "sortable__label check" }, tick, el("span", { class: "check__text", text: r.genre ? `${r.title} (genre)` : r.title })),
        el("span", { class: "sortable__moves" }, move(r.title, "up"), move(r.title, "down")));
    }));
  const save = async (control) => {
    const rows = [...list.children];
    try {
      await api(`/api/library/discover-layout?tab=${tab}`, { method: "POST",
        body: { order: rows.map((r) => r.dataset.value), hidden: rows.filter((r) => !r.querySelector("input").checked).map((r) => r.dataset.value) } });
      reset.disabled = false;
      showSaved(`${id}-saved`, "Saved");
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
  const reset = el("button", { type: "button", class: "btn btn--quiet", id: `${id}-reset`, disabled: !d.changed, text: "Put back the standard rows" });
  reset.addEventListener("click", async () => {
    try {
      await api(`/api/library/discover-layout?tab=${tab}`, { method: "DELETE" });
      await drawDiscoverArea(tab, name, body, `${id}-reset`);
      showSaved(`${id}-saved`, "Standard rows put back");
    } catch (e) { problem(e.message, reset); }
  });
  body.replaceChildren(el("p", { class: "small muted", text: d.rows.some((r) => r.genre) ? "Tick the rows to show. The genre rows, such as Comedy, start unticked. Move them with the arrows, or drag them by the handle." : "Tick the rows to show. Move them with the arrows, or drag them by the handle." }),
    list, el("div", { class: "actions" }, reset, note), el("p", { class: "small" }, el("a", { href: `/discover-${tab}.html`, text: `Open Discover, ${name}` })));
  window.SharedComponents.setupSortables(body);
  if (focusId) document.getElementById(focusId)?.focus();
}

document.addEventListener("DOMContentLoaded", () => setTimeout(drawLibraryViews, 0));
document.addEventListener("DOMContentLoaded", () => setTimeout(drawDiscoverAreas, 0));
