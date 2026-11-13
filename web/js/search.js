// Search every Sonarr, Radarr, Lidarr and Readarr at once, and add what you find from an Add slide-out.

let results = [];
let kind = null; // a kind ("Series", "Film", "Artist", "Author"), or null for everything
let config = null;
const KINDS = { Series: ["Series", "tv"], Film: ["Films", "film"], Artist: ["Music", "music"], Author: ["Books", "book"] };

const resultKey = (r) => `${r.service}|${r.key}`;

function notice(tone, title, text, extra = null) {
  const iconName = { success: "circle-check", warning: "triangle-alert", danger: "circle-x" }[tone] || "info";
  return el("div", { class: "notice", "data-tone": tone, role: "status" }, icon(iconName),
    el("div", { class: "notice__body" }, title ? el("span", { class: "notice__title", text: title }) : null, text ? el("p", { text }) : null), extra);
}

async function getConfig() {
  if (!config) config = await api("/api/config");
  return config;
}

// In the library: the item's own page in its app (from the slug the app gave). Otherwise the app itself.
function appHref(result) {
  const svc = config?.services.find((s) => s.id === result.service);
  if (!svc?.link) return "";
  const base = { sonarr: "/series/", radarr: "/movie/", lidarr: "/artist/", readarr: "/author/" }[svc.type];
  const page = result.in_library && base && /^[\w.-]+$/.test(result.slug || "") ? base + result.slug : "";
  return reachableUrl(svc.link) + page;
}

function cover(r, className) {
  if (r.image) {
    const box = el("div", { class: className });
    const img = el("img", { src: r.image, alt: "", loading: "lazy", referrerpolicy: "no-referrer" });
    img.addEventListener("error", () => { img.remove(); box.textContent = "No cover"; });
    box.append(img);
    return box;
  }
  return el("div", { class: className, text: "No cover" });
}

const titleWithYear = (r) => (r.year ? `${r.title} (${r.year})` : r.title);
const metaLine = (r) => [r.kind, r.detail, r.service_name].filter(Boolean).join(" · ");

// Results ------------------------------------------------------------------

function renderFilters() {
  const box = $("#kind-filters");
  const counts = {};
  for (const r of results) counts[r.kind] = (counts[r.kind] || 0) + 1;
  const kinds = Object.keys(KINDS).filter((k) => counts[k]);
  box.hidden = kinds.length < 2;
  box.removeAttribute("role");
  box.removeAttribute("aria-label");
  // One kind at a time (DASH-309, R4): a segmented control with All first; the radios keep focus.
  if (kind && !counts[kind]) kind = null;
  box.replaceChildren(kinds.length < 2 ? "" : segmentedFilter({ name: "search-kind", label: "Show only", value: kind || "",
    options: [["", "All", results.length], ...kinds.map((k) => [k, KINDS[k][0], counts[k]])],
    onChange: (v) => { kind = v || null; renderResults(); announce(`${shownResults().length} results shown`); } }));
}

function shownResults() { return results.filter((r) => !kind || r.kind === kind); }

function renderRow(r) {
  const side = r.in_library
    ? chip("In library", "success")
    : el("button", { type: "button", class: "btn", onclick: (e) => openPanel(r, e.currentTarget) },
      icon("plus"), "Add", el("span", { class: "visually-hidden", text: ` ${r.title} to ${r.service_name}` }));
  const title = el("button", { type: "button", onclick: (e) => openPanel(r, e.currentTarget) }, titleWithYear(r));
  return el("li", { class: "row row--opens" },
    cover(r, "cover cover--result"),
    el("div", {},
      el("h3", { class: "row__title" }, title),
      el("div", { class: "row__meta", text: metaLine(r) }),
      r.overview ? el("p", { class: "small muted clamp-2 result-overview", text: r.overview }) : null),
    el("div", { class: "row__side" }, side));
}

function renderResults() {
  const shown = shownResults();
  renderKeyed($("#results"), shown, resultKey, (r) => renderRow(r));
  const apps = new Set(results.map((r) => r.service_name)).size;
  $("#search-count").textContent = results.length
    ? `${kind ? `${shown.length} of ` : ""}${results.length} ${results.length === 1 ? "result" : "results"} from ${apps} ${apps === 1 ? "app" : "apps"}`
    : "";
  $("#results-section").hidden = !results.length;
}

// Radio shows and podcasts are followed in Reelix itself: a link to its radio search, with the same words.
async function radioLink(q) {
  const box = $("#radio-search");
  const reelix = (await getConfig().catch(() => ({ services: [] }))).services
    .find((s) => s.icon === "reelix" && s.type === "link" && s.enabled !== false && s.link);
  box.hidden = !reelix;
  if (!reelix) return;
  box.replaceChildren("Looking for a radio show or podcast? ",
    el("a", { href: `${reachableUrl(reelix.link)}/radio/add?term=${encodeURIComponent(q)}`, target: "_blank", rel: "noopener noreferrer" },
      `Search for "${q}" in Reelix radio`, el("span", { class: "visually-hidden", text: " (opens in a new tab)" })), ".");
}

async function runSearch(query) {
  const q = query.trim();
  const summary = $("#search-summary");
  const section = $("#results-section");
  $("#search-errors").replaceChildren();
  if (q.length < 2) { summary.textContent = "Type at least two letters."; announce(summary.textContent); return; }
  const url = new URL(location.href);
  url.searchParams.set("q", q);
  history.replaceState(null, "", url);
  document.title = `${q} · Search · ${document.title.split(" · ").pop()}`;
  summary.textContent = `Searching for "${q}"…`;
  section.setAttribute("aria-busy", "true");
  try {
    const data = await api(`/api/search?q=${encodeURIComponent(q)}`);
    results = data.results;
    kind = null;
    $("#search-errors").replaceChildren(...data.errors.map((err) =>
      notice("warning", "Some results may be missing", err.message, el("a", { class: "btn", href: "/index.html", text: "View apps" }))));
    const text = results.length ? `${results.length} results for "${q}"` : `Nothing found for "${q}". Check the spelling or try fewer words.`;
    summary.textContent = text;
    announce(text);
    renderFilters();
    $("#results").replaceChildren();
    renderResults();
    radioLink(q);
  } catch (e) {
    summary.textContent = e.message;
    announce(e.message);
  } finally {
    section.setAttribute("aria-busy", "false");
  }
}

// Add slide-out ----------------------------------------------------------

function fillSelect(select, items, value, label) {
  select.replaceChildren(...items.map((i) => el("option", { value: i.value, text: i.label })));
  if (value !== undefined && value !== null) select.value = String(value);
  if (!items.length) select.append(el("option", { value: "", text: `No ${label} found in the app` }));
}

function lead(r) {
  return el("div", { class: "side-panel__lead" }, cover(r, "cover"),
    el("div", { class: "media-panel-lead__text" },
      titleChip(el("h3", { text: titleWithYear(r) }), r.in_library ? chip(`In ${r.service_name}`, "success") : chip("Not in library", "muted")),
      el("span", { class: "small muted", text: metaLine(r) })));
}

function openLink(r, primary) {
  const href = appHref(r);
  if (!href) return null;
  return el("a", { class: primary ? "btn btn--primary" : "btn", href, target: "_blank", rel: "noopener noreferrer" },
    icon("external-link"), r.in_library && r.slug ? `Open in ${r.service_name}` : `Open ${r.service_name}`, el("span", { class: "visually-hidden", text: " (opens in a new tab)" }));
}

async function openPanel(r, opener) {
  await getConfig().catch(() => null);
  const key = resultKey(r);
  const focusRow = () => {
    // The Add button is gone once added: go back to the same result's title.
    if (!opener.isConnected) $(`#results [data-key="${CSS.escape(key)}"] .row__title button`)?.focus();
  };
  if (r.in_library) {
    const link = openLink(r, true);
    sidePanel({
      title: r.title, opener, onClose: focusRow,
      body: [lead(r), r.overview ? el("p", { text: r.overview }) : null,
        notice("success", `Already in ${r.service_name}`, `Manage it in ${r.service_name}.`)].filter(Boolean),
      foot: link ? [link] : [],
    });
    return;
  }

  const ids = { q: "add-quality", f: "add-root", m: "add-meta", s: "add-search", e: "add-error" };
  const quality = el("select", { class: "select", id: ids.q, name: "quality_profile_id" }, el("option", { text: "Loading…" }));
  const root = el("select", { class: "select", id: ids.f, name: "root_folder" }, el("option", { text: "Loading…" }));
  const meta = el("select", { class: "select", id: ids.m, name: "metadata_profile_id" });
  const metaField = el("div", { class: "field", hidden: true }, el("label", { for: ids.m, text: "Metadata profile" }), meta);
  const search = el("input", { type: "checkbox", id: ids.s, name: "search", checked: true });
  const error = el("p", { class: "field-error", id: ids.e, role: "alert" });
  const submit = el("button", { type: "submit", form: "add-form", class: "btn btn--primary", disabled: true }, icon("plus"), `Add to ${r.service_name}`);
  const form = el("form", { id: "add-form", class: "media-panel-section", "aria-labelledby": "add-options-h", novalidate: true },
    el("h3", { id: "add-options-h", text: `Add to ${r.service_name}` }),
    el("div", { class: "field" }, el("label", { for: ids.q, text: "Quality profile" }), quality),
    el("div", { class: "field" }, el("label", { for: ids.f, text: "Folder" }), root),
    metaField,
    el("label", { class: "check", for: ids.s }, search, el("span", { class: "check__text", text: "Start searching for it now" })),
    error);
  const cancel = el("button", { type: "button", class: "btn btn--quiet", "data-closes": true, text: "Cancel" });
  const panel = sidePanel({
    title: `Add ${r.title}`, opener, onClose: focusRow,
    body: [lead(r), r.overview ? el("p", { text: r.overview }) : null, form].filter(Boolean),
    foot: [submit, cancel],
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    submit.disabled = true;
    error.textContent = "";
    try {
      const done = await api("/api/add", {
        method: "POST",
        body: {
          service: r.service, key: r.key,
          options: {
            quality_profile_id: Number(quality.value) || null,
            root_folder: root.value || null,
            metadata_profile_id: Number(meta.value) || null,
            search: search.checked,
          },
        },
      });
      r.in_library = true;
      renderResults();
      const link = openLink(r, false);
      form.replaceWith(notice("success", `Added to ${done.service_name}`,
        search.checked
          ? `${done.service_name} is searching for ${done.title} now. Follow it on Downloads.`
          : `${done.title} is in ${done.service_name}. It searches when you ask it to.`,
        link));
      $(".side-panel__lead .chip", panel.layer)?.replaceWith(chip(`In ${done.service_name}`, "success"));
      const back = el("button", { type: "button", class: "btn btn--primary", "data-closes": true }, "Back to results");
      panel.setFoot([back, el("a", { class: "btn", href: "/downloads.html" }, icon("download"), "View downloads")]);
      back.focus();
      toast(`Added ${done.title} to ${done.service_name}`);
    } catch (e) {
      error.textContent = e.message;
      submit.disabled = false;
    }
  });

  try {
    const svc = config?.services.find((s) => s.id === r.service) || {};
    const opts = await api(`/api/services/${encodeURIComponent(r.service)}/options`);
    fillSelect(quality, opts.quality_profiles.map((p) => ({ value: p.id, label: p.name })), svc.quality_profile_id ?? opts.quality_profiles[0]?.id, "quality profiles");
    fillSelect(root, opts.root_folders.map((f) => ({ value: f.path, label: f.free ? `${f.path} (${formatBytes(f.free)} free)` : f.path })), svc.root_folder || opts.root_folders[0]?.path, "folders");
    metaField.hidden = !opts.metadata_profiles.length;
    fillSelect(meta, opts.metadata_profiles.map((p) => ({ value: p.id, label: p.name })), svc.metadata_profile_id ?? opts.metadata_profiles[0]?.id, "metadata profiles");
    search.checked = svc.search_on_add !== false;
    submit.disabled = false;
  } catch (e) {
    error.textContent = `${e.message}. Close this panel and try again.`;
  }
}

// Without Reelix, library-search.js hands the page to this search of Sonarr, Radarr, Lidarr and Readarr.
window.legacySearchStart = () => {
  $("#search-more").hidden = false;
  $("#search-summary").textContent = "Find a series, film, artist or author and add it to the right app.";
  $("#search-form").addEventListener("submit", (e) => { e.preventDefault(); runSearch($("#q").value); });
  const q = new URLSearchParams(location.search).get("q");
  if (q) { $("#q").value = q; runSearch(q); } else { $("#q").focus(); }
  getConfig().catch(() => null);
};
