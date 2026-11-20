// Settings, Updates, Releases.

// Settings, Updates, Releases: each release in its own accordion, newest first, the installed one open, with a count
// for each type of change (design system, Releases).
const RELEASE_TYPES = [["added", "Added", "success"], ["changed", "Changed", "info"], ["deprecated", "Deprecated", "muted"],
  ["removed", "Removed", "muted"], ["fixed", "Fixed", "warning"], ["security", "Security", "danger"]];

async function startReleases(repo) {
  const list = $("#releases-list");
  let r;
  try { r = await api("/api/releases"); } catch (e) { list.removeAttribute("aria-busy"); $("#releases-summary").textContent = e.message; return; }
  const latest = String(r.latest || "").replace(/^v/, "");
  const newer = isNewer(r.latest, r.current);
  $("#releases-summary").textContent = newer
    ? `You have version ${r.current}. Version ${latest} is out: Update settings says how to update.`
    : `You have version ${r.current}${r.latest ? ", the newest" : ""}. ${r.all.length} releases.`;
  list.replaceChildren(...r.all.map((rel) => {
    const types = RELEASE_TYPES.filter(([key]) => rel[key]?.length);
    const installed = rel.version === r.current;
    return el("details", { class: "disclosure release", open: installed || null },
      el("summary", {},
        el("h3", { text: `Version ${rel.version}` }),
        installed ? chip("Installed", "success") : null,
        el("span", { class: "release__date", text: rel.date }),
        // Counts are words in the meta line, not chips (DASH-309, R3: a chip never holds a number).
        el("span", { class: "release__counts small muted", text: types.map(([key, label]) => `${rel[key].length} ${label.toLowerCase()}`).join(", ") })),
      el("div", { class: "disclosure__body" },
        ...types.map(([key, label]) => el("section", { class: "release__type", "data-type": key },
          el("h4", { text: label }),
          el("ul", {}, rel[key].map(([title, sentence]) => el("li", {}, el("strong", { text: `${title}. ` }), sentence))))),
        el("div", { class: "release__type", "data-type": "settings" },
          el("h4", { text: "Your settings and the way back" }), el("p", { text: rel.settings })),
        repo ? el("p", { class: "small" }, el("a", { href: `https://github.com/${repo}/releases/tag/v${rel.version}`, target: "_blank", rel: "noopener noreferrer" },
          `Version ${rel.version} on GitHub`, el("span", { class: "visually-hidden", text: " (opens in a new tab)" }))) : null));
  }));
  list.removeAttribute("aria-busy");
  const toggle = el("button", { type: "button", class: "btn btn--quiet", text: "Open all" });
  const all = () => $$("#releases-list details");
  const label = () => { toggle.textContent = all().every((d) => d.open) ? "Close all" : "Open all"; };
  toggle.addEventListener("click", () => { const open = !all().every((d) => d.open); all().forEach((d) => { d.open = open; }); label(); });
  all().forEach((d) => d.addEventListener("toggle", label));
  $(".releases-head").append(toggle);
  label();
}
