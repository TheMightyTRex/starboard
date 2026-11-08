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

document.addEventListener("DOMContentLoaded", () => setTimeout(drawLibraryViews, 0));
