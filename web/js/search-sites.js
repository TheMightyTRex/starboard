// Search, Search the sites (DASH-213): a free search across the sites Reelix searches, with Get this one, which sends a
// release straight to the download app (Reelix's raw grab). Its own page under Search, as the design system's section
// 10 says for something people return to and link to. The results are a table (real data compared across columns:
// size, seeders, age). Nothing is searched while typing: each search asks every site, so it waits for Enter or the
// button. The release links stay on the server (starboard/reelix_search.py).

let found = null; // the last answer: { token, results, sites }
const sent = new Map(); // row number -> download app it went to

const ageOf = (iso) => {
  if (!iso) return "";
  const days = Math.floor((Date.now() - new Date(iso)) / 86400000);
  if (days < 1) return "Today";
  if (days < 2) return "Yesterday";
  if (days < 60) return `${days} days`;
  if (days < 730) return `${Math.floor(days / 30)} months`;
  return `${Math.floor(days / 365)} years`;
};

function sortedRows() {
  const site = $("#sites-site").value;
  const rows = found.results.filter((r) => !site || String(r.site_id) === site);
  const by = $("#sites-sort").value;
  const num = (v) => (typeof v === "number" ? v : -1);
  if (by === "seeders") rows.sort((a, b) => num(b.seeders) - num(a.seeders));
  else if (by === "small") rows.sort((a, b) => (a.size ?? Infinity) - (b.size ?? Infinity));
  else if (by === "large") rows.sort((a, b) => num(b.size) - num(a.size));
  else rows.sort((a, b) => String(b.published || "").localeCompare(String(a.published || "")));
  return rows;
}

function getCell(r) {
  if (sent.has(r.n)) return chip(`Sent to ${sent.get(r.n)}`, "success");
  if (!r.can_get) return el("span", { class: "small muted", text: "No link from the site" });
  const btn = el("button", { type: "button", class: "btn btn--compact", "data-get": String(r.n) }, icon("download"), "Get this one",
    el("span", { class: "visually-hidden", text: `: ${r.title}` }));
  btn.addEventListener("click", () => getOne(r, btn));
  return btn;
}

async function getOne(r, btn) {
  btn.disabled = true;
  try {
    const out = await api("/api/reelix/sites/grab", { method: "POST", body: { token: found.token, n: r.n } });
    sent.set(r.n, out.client);
    const cell = btn.closest("td");
    cell.replaceChildren(getCell(r));
    // Focus stays in the row: the row's title, which now says it was sent (WCAG 2.4.3).
    const title = cell.closest("tr").querySelector("th");
    title.setAttribute("tabindex", "-1");
    title.focus();
    announce(`${out.done}: ${r.title}. When it finishes, say what it is on Activity, Downloads.`);
    if (!$("#sites-sent")) {
      $("#sites-said").replaceChildren(el("div", { class: "notice", "data-tone": "success", id: "sites-sent" }, icon("circle-check"),
        el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: "Sent to your download app" }),
          el("p", { text: "It shows on Activity, Downloads. When it finishes, Reelix waits there for you to say which film, episode or book it is." })),
        el("a", { class: "btn", href: "/downloads.html" }, "Open Downloads")));
    }
  } catch (e) {
    btn.disabled = false;
    problem(e.message, btn);
  }
}

function drawTable() {
  const rows = sortedRows();
  $("#sites-count").textContent = `${rows.length} of ${found.results.length}`;
  if (!rows.length) {
    $("#sites-table").replaceChildren(emptyState(found.results.length ? "Nothing from this site" : "Nothing found",
      found.results.length ? "Choose All sites to see the rest." : "Try fewer words, or All instead of one kind. Sites that did not answer are listed below."));
    return;
  }
  const head = ["Release", "Site", "Size", "Seeders", "Age"];
  $("#sites-table").replaceChildren(el("div", { class: "table-wrap", "data-stack": true }, el("table", { class: "table sites-table" },
    el("caption", { class: "visually-hidden", text: `Releases for ${found.q}` }),
    el("thead", {}, el("tr", {}, head.map((h) => el("th", { scope: "col", text: h })), el("th", { scope: "col" }, el("span", { class: "visually-hidden", text: "Get" })))),
    el("tbody", {}, rows.map((r) => el("tr", { "data-key": String(r.n) },
      el("th", { scope: "row", "data-label": "Release" },
        r.info_url ? el("a", { href: r.info_url, target: "_blank", rel: "noopener noreferrer", class: "sites-title" }, r.title,
          el("span", { class: "visually-hidden", text: " (opens the site in a new tab)" })) : el("span", { class: "sites-title", text: r.title }),
        r.flags.length ? el("div", { class: "small muted", text: r.flags.join(" · ") }) : null),
      el("td", { "data-label": "Site", text: r.site }),
      el("td", { "data-label": "Size", class: "num", text: r.size ? formatBytes(r.size) : "Not known" }),
      el("td", { "data-label": "Seeders", class: "num", text: r.protocol === "usenet" ? "Usenet" : r.seeders ?? "Not known" }),
      el("td", { "data-label": "Age", text: ageOf(r.published) || "Not known" }),
      el("td", { "data-label": "Get" }, getCell(r))))))));
}

function drawAnswers() {
  const failed = found.sites.filter((s) => s.error);
  const list = el("ul", { class: "small" }, found.sites.map((s) => el("li", {
    text: s.error ? `${s.name}: did not answer (${s.error})` : `${s.name}: ${s.count} ${s.count === 1 ? "result" : "results"} in ${s.seconds} s` })));
  $("#sites-answers").replaceChildren(
    failed.length ? notice("warning", `${failed.length} of ${found.sites.length} sites did not answer`,
      `${failed.map((s) => s.name).join(", ")}. Their results are missing. Settings, Reelix, Sites to search shows why.`,
      el("a", { class: "btn", href: "/settings-reelix.html#rx-indexers-h" }, "Sites to search")) : null,
    found.sites.length ? el("details", { class: "disclosure" }, el("summary", { text: "Each site's answer" }), el("div", { class: "disclosure__body" }, list)) : null);
}

function notice(tone, title, text, action) {
  const icons = { success: "circle-check", warning: "triangle-alert", danger: "circle-x", info: "info" };
  return el("div", { class: "notice", "data-tone": tone === "info" ? null : tone, role: "status" }, icon(icons[tone] || "info"),
    el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: title }), text ? el("p", { text }) : null), action || null);
}

async function runSearch() {
  const q = $("#sites-q").value.trim();
  const kind = $("input[name=sites-kind]:checked").value;
  if (q.length < 2) { problem("Type at least 2 letters to search for", $("#sites-q")); $("#sites-q").focus(); return; }
  const url = new URL(location.href);
  url.searchParams.set("q", q);
  if (kind === "all") url.searchParams.delete("kind"); else url.searchParams.set("kind", kind);
  history.replaceState(null, "", url);
  const go = $("#sites-go");
  go.disabled = true;
  $("#sites-results").hidden = false;
  $("#sites-results").setAttribute("aria-busy", "true");
  $("#sites-said").replaceChildren(el("p", { class: "muted", text: "Asking every site. This can take up to a minute." }));
  $("#sites-table").replaceChildren();
  $("#sites-answers").replaceChildren();
  announce("Searching the sites. This can take up to a minute.");
  try {
    found = await api(`/api/reelix/sites/search?q=${encodeURIComponent(q)}&kind=${encodeURIComponent(kind)}`);
    sent.clear();
    const site = $("#sites-site");
    site.replaceChildren(el("option", { value: "", text: "All sites" }),
      ...found.sites.filter((s) => s.count).map((s) => el("option", { value: String(s.id), text: `${s.name} ${s.count}` })));
    $("#sites-refine").hidden = !found.results.length;
    $("#sites-said").replaceChildren();
    drawTable();
    drawAnswers();
    $("#sites-summary").textContent = `Results for "${found.q}"`;
    announce(`${found.results.length} ${found.results.length === 1 ? "result" : "results"} from ${found.sites.length} sites`);
  } catch (e) {
    $("#sites-said").replaceChildren(notice("danger", "The sites could not be searched", e.message));
    $("#sites-results").hidden = true;
  } finally {
    go.disabled = false;
    $("#sites-results").setAttribute("aria-busy", "false");
  }
}

startPage().then(() => {
  const params = new URLSearchParams(location.search);
  const kind = params.get("kind");
  if (kind) { const r = $(`input[name=sites-kind][value="${CSS.escape(kind)}"]`); if (r) r.checked = true; }
  $("#sites-form").addEventListener("submit", (e) => { e.preventDefault(); runSearch(); });
  $("#sites-site").addEventListener("change", drawTable);
  $("#sites-sort").addEventListener("change", drawTable);
  const q = params.get("q");
  if (q) { $("#sites-q").value = q; runSearch(); } else $("#sites-q").focus();
});
