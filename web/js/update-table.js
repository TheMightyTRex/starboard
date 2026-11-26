// The one layout for every list of updates (owner, 26 November 2026: System, Apps, Updates is the standard): a table with
// the item, the version you have beside the new one, its status and what you can do, ticks with Update chosen in a
// selection bar, and one line that says when it was last checked and how many updates wait. Used by Apps, Updates,
// Settings, Updates and Settings, Updates, Plug-ins (and Manage). Loaded only by those pages.

// "Last checked at 14:02 · 3 updates available". checkedAt: seconds, or 0 for never; names: what is waiting (optional);
// missed: what could not be checked, in words (optional); extra: more facts to add after a dot.
function updateSummary({ checkedAt = 0, restored = false, count = 0, names = [], missed = [], extra = [] }) {
  const parts = [checkedAt ? `Last checked ${checkedWhen(checkedAt, restored)}` : "Not checked yet"];
  if (checkedAt || count) {
    const n = count ? `${count} ${count === 1 ? "update" : "updates"} available${names.length ? `: ${names.join(", ")}` : ""}` : "everything is up to date";
    parts.push(n);
  }
  if (missed.length) parts.push(`Could not check: ${missed.join(" ")}`);
  return [...parts, ...extra].join(" · ");
}

// The first cell: an optional tick, an optional picture, the name (a link when href is given) and a second line.
function updateName({ tick = null, picture = null, name, href = "", sub = null, id = "" }) {
  return el("div", { class: "updates-app" }, tick, picture,
    el("div", {}, href ? el("a", { href, text: name, ...(id ? { id } : {}) }) : el("strong", { text: name, ...(id ? { id } : {}) }), sub));
}

// rows: [{ id, key, name (a node), extra: { <key>: node }, installed, latest, status, actions, thId }]. extra: [{ key, label }]
// are the columns between the name and Installed (Apps has Image).
function updateTable({ caption, nameLabel = "Name", extra = [], rows }) {
  const keys = ["app", ...extra.map((c) => c.key), "installed", "latest", "status", "actions"];
  return el("div", { class: "table-wrap", "data-stack": true },
    el("table", { class: `table updates-table${extra.length ? "" : " updates-table--plugins"}` },
      el("caption", { class: "visually-hidden", text: caption }),
      el("colgroup", {}, keys.map((c) => el("col", { class: `updates-table__${c}` }))),
      el("thead", {}, el("tr", {}, [nameLabel, ...extra.map((c) => c.label), "Installed", "Latest", "Status"].map((h) => el("th", { scope: "col", text: h })),
        el("th", { scope: "col" }, el("span", { class: "visually-hidden", text: "Actions" })))),
      el("tbody", {}, rows.map((r) => el("tr", { "data-key": r.key || r.id },
        el("th", { scope: "row", "data-label": nameLabel, ...(r.thId ? { id: r.thId, tabindex: "-1" } : {}) }, r.name),
        ...extra.map((c) => el("td", { "data-label": c.label }, r.extra?.[c.key] ?? "")),
        el("td", { "data-label": "Installed" }, r.installed ?? ""),
        el("td", { "data-label": "Latest" }, r.latest ?? ""),
        el("td", { "data-label": "Status" }, r.status),
        el("td", { "data-label": "Actions" }, Array.isArray(r.actions) ? el("div", { class: "actions" }, r.actions.filter(Boolean)) : r.actions))))));
}

// A tick for a row, named for a screen reader.
function updateTick(id, name, chosen, onChange, disabled = false) {
  const box = el("input", { type: "checkbox", id: `choose-${id}`, class: "updates-choose", "aria-label": `Choose ${name}`, checked: chosen.has(id), disabled });
  box.addEventListener("change", () => { if (box.checked) chosen.add(id); else chosen.delete(id); onChange(); });
  return box;
}

// The selection bar: "N chosen", Update chosen and Clear. set(n, busy) says the count in a polite live region.
function updateSelectionBar({ id, onUpdate, onClear }) {
  const text = el("span", { class: "selection-bar__text", id: `${id}-text`, "aria-live": "polite", text: "0 chosen" });
  const go = el("button", { type: "button", class: "btn", id: `${id}-go`, disabled: true }, icon("circle-arrow-up"), "Update chosen");
  const clear = el("button", { type: "button", class: "btn btn--quiet", text: "Clear" });
  go.addEventListener("click", () => onUpdate(go));
  clear.addEventListener("click", onClear);
  const node = el("div", { class: "selection-bar", id, role: "region", "aria-label": "Chosen updates", hidden: true }, text, go, clear);
  return { node, set(n, busy = false) { node.hidden = !n; text.textContent = `${n} chosen`; go.disabled = busy || !n; } };
}
