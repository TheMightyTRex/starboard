// Search every Sonarr, Radarr, Lidarr and Readarr at once, and add what you find.

let results = [];
let kind = "All";
let adding = null;
const KIND_LABEL = { All: "All", Series: "Series", Film: "Films", Artist: "Artists", Author: "Authors" };

function renderFilters() {
  const box = $("#kind-filters");
  box.replaceChildren();
  if (!results.length) return;
  const counts = { All: results.length };
  for (const r of results) counts[r.kind] = (counts[r.kind] || 0) + 1;
  for (const k of Object.keys(KIND_LABEL)) {
    if (!counts[k]) continue;
    box.append(el("button", {
      type: "button", class: "filter-chip", "aria-pressed": String(kind === k),
      onclick: () => { kind = k; renderFilters(); renderResults(); },
    }, `${KIND_LABEL[k]}, ${counts[k]}`));
  }
}

function renderResults() {
  const list = $("#results");
  list.replaceChildren();
  const shown = results.filter((r) => kind === "All" || r.kind === kind);
  for (const r of shown) {
    const cover = r.image
      ? el("img", { class: "result__cover", src: r.image, alt: `Cover of ${r.title}`, loading: "lazy", referrerpolicy: "no-referrer" })
      : el("div", { class: "result__cover", text: "No cover" });
    const action = r.in_library
      ? chip(`In ${r.service_name}`, "success")
      : el("button", { type: "button", class: "btn btn--primary", onclick: () => openAdd(r) }, `Add to ${r.service_name}`, el("span", { class: "visually-hidden", text: `: ${r.title}` }));
    list.append(el("li", { class: "result" }, cover,
      el("div", { class: "result__body" },
        el("h2", { class: "result__title" }, r.title, r.year ? el("span", { class: "summary", text: ` (${r.year})` }) : null),
        el("p", { class: "result__meta" }, chip(r.kind === "Film" ? "Film" : r.kind, "info"), r.detail ? el("span", { text: r.detail }) : null),
        r.overview ? el("p", { class: "result__overview", text: r.overview }) : null,
        el("div", { class: "actions" }, action))));
  }
}

async function runSearch(query) {
  const q = query.trim();
  const summary = $("#search-summary");
  const list = $("#results");
  $("#search-errors").replaceChildren();
  if (q.length < 2) { summary.textContent = "Type at least two letters."; return; }
  const url = new URL(location.href);
  url.searchParams.set("q", q);
  history.replaceState(null, "", url);
  document.title = `${q} · Search · ${document.title.split(" · ").pop()}`;
  summary.textContent = `Searching for “${q}”…`;
  list.setAttribute("aria-busy", "true");
  try {
    const data = await api(`/api/search?q=${encodeURIComponent(q)}`);
    results = data.results;
    kind = "All";
    for (const err of data.errors) $("#search-errors").append(el("p", { class: "notice", "data-tone": "warning", text: err.message }));
    const text = results.length ? `${results.length} results for “${q}”` : `Nothing found for “${q}”. Check the spelling or try fewer words.`;
    summary.textContent = text;
    announce(text);
    renderFilters();
    renderResults();
  } catch (e) {
    summary.textContent = e.message;
  } finally {
    list.setAttribute("aria-busy", "false");
  }
}

function fillSelect(select, items, value, label) {
  select.replaceChildren(...items.map((i) => el("option", { value: i.value, text: i.label })));
  if (value !== undefined && value !== null) select.value = String(value);
  if (!items.length) select.append(el("option", { value: "", text: `No ${label} found in the app` }));
}

async function openAdd(result) {
  adding = result;
  const dialog = $("#add-dialog");
  $("#add-title").textContent = `Add ${result.title}`;
  $("#add-intro").textContent = `Adds to ${result.service_name}.`;
  $("#add-error").textContent = "";
  $("#add-submit").disabled = true;
  dialog.showModal();
  try {
    const cfg = await api("/api/config");
    const svc = cfg.services.find((s) => s.id === result.service) || {};
    const opts = await api(`/api/services/${result.service}/options`);
    fillSelect($("#add-quality"), opts.quality_profiles.map((p) => ({ value: p.id, label: p.name })), svc.quality_profile_id ?? opts.quality_profiles[0]?.id, "quality profiles");
    fillSelect($("#add-root"), opts.root_folders.map((r) => ({ value: r.path, label: r.free ? `${r.path} (${formatBytes(r.free)} free)` : r.path })), svc.root_folder || opts.root_folders[0]?.path, "folders");
    $("#add-meta-field").hidden = !opts.metadata_profiles.length;
    fillSelect($("#add-meta"), opts.metadata_profiles.map((p) => ({ value: p.id, label: p.name })), svc.metadata_profile_id ?? opts.metadata_profiles[0]?.id, "metadata profiles");
    $("#add-search").checked = svc.search_on_add !== false;
    $("#add-submit").disabled = false;
  } catch (e) {
    $("#add-error").textContent = e.message;
  }
}

async function submitAdd(event) {
  event.preventDefault();
  if (!adding) return;
  const button = $("#add-submit");
  button.disabled = true;
  $("#add-error").textContent = "";
  try {
    const done = await api("/api/add", {
      method: "POST",
      body: {
        service: adding.service, key: adding.key,
        options: {
          quality_profile_id: Number($("#add-quality").value) || null,
          root_folder: $("#add-root").value || null,
          metadata_profile_id: Number($("#add-meta").value) || null,
          search: $("#add-search").checked,
        },
      },
    });
    adding.in_library = true;
    $("#add-dialog").close();
    renderResults();
    toast(`Added ${done.title} to ${done.service_name}`);
  } catch (e) {
    $("#add-error").textContent = e.message;
  } finally {
    button.disabled = false;
  }
}

startPage().then(() => {
  wireDialog($("#add-dialog"));
  $("#add-form").addEventListener("submit", submitAdd);
  $("#search-form").addEventListener("submit", (e) => { e.preventDefault(); runSearch($("#q").value); });
  const q = new URLSearchParams(location.search).get("q");
  if (q) { $("#q").value = q; runSearch(q); } else { $("#q").focus(); }
});
