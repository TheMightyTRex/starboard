// One item in the Library (DASH-163): the header (name, meta line, description, progress, a fan of the cover), then
// its list (episodes, reading order, albums, the collection) and About. Read from Reelix one item at a time.

const ITEM_TAB = document.querySelector("[data-library-item]")?.dataset.libraryItem;
const WALL = { films: ["library-films.html", "Films"], tv: ["library-tv.html", "TV"], music: ["library-music.html", "Music"],
  radio: ["library-radio.html", "Radio"], books: ["library-books.html", "Books"], audiobooks: ["library-audiobooks.html", "Audiobooks"] };

// DASH-276, DASH-206: Get it, Follow, Stop following and Delete, through Starboard (Reelix's own routes). The page
// draws itself again with Reelix's answer, and says what was done.
let current = null;
async function act(action, extra = {}, button = null) {
  if (button) { button.disabled = true; button.setAttribute("aria-busy", "true"); }
  try {
    const r = await api(`/api/library/act?tab=${ITEM_TAB}`, { method: "POST", body: { id: current.id, action, ...extra } });
    announce(r.said);
    if (!r.item) { location.href = `/${WALL[ITEM_TAB][0]}`; return; }
    show(r.item, r.said);
  } catch (e) {
    problem(e.message, button);
    if (button) { button.disabled = false; button.removeAttribute("aria-busy"); }
  }
}

// Watched or not watched, from Jellyfin (DASH-276): a toggle button that says its state (aria-pressed) and changes it.
async function markWatched(ids, watched, button) {
  button.disabled = true;
  try {
    const r = await api(`/api/library/watched?tab=${ITEM_TAB}`, { method: "POST", body: { id: current.id, ids, watched } });
    announce(r.said);
    show(r.item, r.said);
  } catch (e) { problem(e.message, button); button.disabled = false; }
}

// Choose a download (DASH-159): what Reelix finds on its sites, best first, with Get this one. One Reelix would
// turn down says why, and can still be taken with Get it anyway.
async function chooseDownload(extra, what) {
  const box = el("div", { class: "stack-2", "aria-live": "polite" }, el("p", { class: "muted", text: "Asking every site. This can take a minute…" }));
  const dialog = confirmDialog({ title: `Choose a download for ${what}`, message: "", confirm: "Close", cancel: "Cancel", fields: [box] });
  const params = new URLSearchParams({ tab: ITEM_TAB, id: String(current.id), ...Object.fromEntries(Object.entries(extra).map(([k, v]) => [k, String(v)])) });
  try {
    const r = await api(`/api/library/releases?${params}`);
    if (!r.releases.length) { box.replaceChildren(el("p", { text: "No site has it at the moment. Reelix keeps looking while it follows it." })); return dialog; }
    box.replaceChildren(el("ul", { class: "rows" }, r.releases.map((x) => {
      const meta = [x.quality, x.size ? formatBytes(x.size) : "", x.seeders != null ? `${x.seeders} seeders` : "", x.site,
        x.age_minutes != null ? (x.age_minutes < 1440 ? "today" : Math.round(x.age_minutes / 1440) === 1 ? "1 day old" : `${Math.round(x.age_minutes / 1440)} days old`) : "", x.languages.join(", ")].filter(Boolean).join(" · ");
      const take = el("button", { type: "button", class: x.accepted ? "btn btn--compact" : "btn btn--quiet btn--compact" },
        x.accepted ? "Get this one" : "Get it anyway", el("span", { class: "visually-hidden", text: ` ${x.title}` }));
      take.addEventListener("click", async () => {
        take.disabled = true;
        try { const g = await api(`/api/library/grab?tab=${ITEM_TAB}`, { method: "POST", body: { guid: x.guid, indexer_id: x.indexer_id, force: !x.accepted, title: x.title } });
          take.replaceWith(chip("Sent", "success")); announce(g.said); toast(g.said); }
        catch (e) { problem(e.message, take); take.disabled = false; }
      });
      return el("li", { class: "row row--no-lead" }, el("div", {},
        el("div", { class: "row__title", text: x.title }), el("div", { class: "row__meta", text: meta }),
        x.why_not.length ? el("div", { class: "row__meta", text: `Reelix would not take it: ${x.why_not.join("; ")}` }) : null),
        el("div", { class: "row__side" }, x.accepted ? null : chip("Turned down", "warning"), take));
    })));
  } catch (e) {
    box.replaceChildren(el("div", { class: "notice", "data-tone": "danger", role: "alert" }, icon("circle-x"),
      el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: "Reelix could not search" }), el("p", { text: e.message }))));
  }
  return dialog;
}

function watchedButton(w, label, compact = true) {
  if (!w || !w.ids?.length) return null;
  return el("button", { type: "button", class: compact ? "btn btn--quiet btn--compact" : "btn", "aria-pressed": String(!!w.watched),
    onclick: (e) => markWatched(w.ids, !w.watched, e.currentTarget) },
    icon(w.watched ? "eye" : "eye-off"), w.watched ? "Watched" : "Not watched",
    el("span", { class: "visually-hidden", text: ` ${label}. ${w.watched ? "Select to mark as not watched" : "Select to mark as watched"}` }));
}

function rowList(rows) {
  return el("ul", { class: "rows lib-order" }, ...rows.map((r) => el("li", { class: `row${r.number ? "" : " row--no-lead"}` },
    r.number ? el("span", { class: "lib-order__number", text: r.number }) : null,
    el("div", {},
      el("h3", { class: "row__title" }, r.href ? el("a", { href: r.href, text: r.title }) : r.title),
      el("div", { class: "row__meta", text: [r.date, r.note].filter(Boolean).join(" · ") })),
    el("div", { class: "row__side" }, r.status ? chip(r.status, r.tone) : null,
      r.jf ? watchedButton({ watched: r.watched, ids: [r.jf] }, `${r.number} ${r.title}`) : null,
      r.can_get && r.id ? el("button", { type: "button", class: "btn btn--quiet btn--compact", onclick: (e) => act("get", { scope: "episode", episode: r.id }, e.currentTarget) },
        "Get it", el("span", { class: "visually-hidden", text: ` ${r.number} ${r.title}` })) : null))));
}

// A long list in groups (a series' seasons): one disclosure each, the newest open. One group stays a plain list.
function groupList(list) {
  if (!list.groups || list.groups.length < 2) return rowList(list.rows);
  return el("div", { class: "lib-seasons" }, ...list.groups.map((g) => el("details", { class: "disclosure", open: g.open || null },
    el("summary", {}, el("span", { text: g.heading }), el("span", { class: "disclosure__meta", text: g.meta })),
    el("div", { class: "disclosure__body stack-2" },
      g.missing || g.watched ? el("div", { class: "actions" },
        g.missing ? el("button", { type: "button", class: "btn btn--compact", onclick: (e) => act("get", { scope: "season", season: g.season }, e.currentTarget) },
          `Get the ${g.missing} missing`, el("span", { class: "visually-hidden", text: ` in ${g.heading}` })) : null,
        g.missing ? el("button", { type: "button", class: "btn btn--quiet btn--compact", onclick: () => chooseDownload({ scope: "season", season: g.season }, g.heading) },
          "Choose a download", el("span", { class: "visually-hidden", text: ` for ${g.heading}` })) : null,
        watchedButton(g.watched, g.heading)) : null,
      rowList(g.rows)))));
}

function about(item) {
  return el("div", { class: "stack-4" },
    item.overview ? el("p", { class: "prose", text: item.overview }) : null,
    item.facts.length ? el("dl", { class: "facts" }, ...item.facts.flatMap((f) => [el("dt", { text: f.label }), el("dd", { text: f.value })])) : null);
}

// In-page tabs: the item's list first, then About. Arrow keys move between them (the tabs pattern).
function tabs(parts) {
  const list = el("div", { class: "lib-tabs", role: "tablist", "aria-label": "Sections" });
  const panels = [];
  parts.forEach((p, n) => {
    const tab = el("button", { type: "button", role: "tab", id: `tab-${p.key}`, "aria-controls": `panel-${p.key}`,
      "aria-selected": String(n === 0), tabindex: n === 0 ? "0" : "-1", text: p.label });
    const panel = el("section", { role: "tabpanel", id: `panel-${p.key}`, "aria-labelledby": `tab-${p.key}`, tabindex: "0", hidden: n !== 0 },
      p.heading && p.heading !== p.label ? el("h2", { class: "lib-panel-heading", text: p.heading }) : null, p.body);
    list.append(tab);
    panels.push(panel);
  });
  const select = (tab) => {
    $$("[role=tab]", list).forEach((t) => {
      const on = t === tab;
      t.setAttribute("aria-selected", String(on));
      t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute("aria-controls")).hidden = !on;
    });
    const part = parts.find((p) => `tab-${p.key}` === tab.id);
    if (part?.onOpen && !part.opened) { part.opened = true; part.onOpen(); }
  };
  list.addEventListener("click", (e) => { const t = e.target.closest("[role=tab]"); if (t) select(t); });
  list.addEventListener("keydown", (e) => {
    const all = $$("[role=tab]", list);
    const at = all.indexOf(document.activeElement);
    const go = { ArrowRight: at + 1, ArrowLeft: at - 1, Home: 0, End: all.length - 1 }[e.key];
    if (go === undefined || at < 0) return;
    e.preventDefault();
    const next = all[(go + all.length) % all.length];
    select(next);
    next.focus();
  });
  return [list, ...panels];
}

// The bar's width is set through the style object: the page's security policy refuses style attributes.
function bar(progress) {
  const span = el("span");
  span.style.width = `${Math.round(100 * progress.have / Math.max(1, progress.total))}%`;
  return span;
}

// DASH-206: a film's or series' quality and folder, in a slide-out (settings pattern 8): two choices and Save.
async function qualityAndFolder(item, opener) {
  let c;
  try { c = await api(`/api/library/change?tab=${ITEM_TAB}&id=${item.id}`); } catch (e) { problem(e.message, opener); return; }
  const profile = el("select", { class: "select", id: "qf-profile" }, c.profiles.map((p) => el("option", { value: p.id, text: p.name, selected: p.id === c.profile_id })));
  const folder = el("select", { class: "select", id: "qf-folder" }, c.folders.map((f) => el("option", { value: f.id,
    text: `${f.path}${f.free != null ? ` (${formatBytes(f.free)} free)` : ""}`, selected: f.id === c.folder_id })));
  const move = el("input", { type: "checkbox", id: "qf-move", checked: true });
  const save = el("button", { type: "submit", class: "btn btn--primary", form: "qf-form", text: "Save" });
  const cancel = el("button", { type: "button", class: "btn", text: "Cancel" });
  const field = (label, control, hint) => el("div", { class: "field" }, el("label", { for: control.id, text: label }),
    hint ? el("span", { class: "hint", text: hint }) : null, control);
  const form = el("form", { class: "form-stack", id: "qf-form", novalidate: true },
    field("Quality", profile, "What Reelix looks for and when it stops upgrading."),
    field("Folder", folder, c.path ? `Now in ${c.path}.` : ""),
    el("label", { class: "check" }, move, el("span", { class: "check__text" }, el("strong", { text: "Move its files to the new folder" }),
      el("span", { class: "check__hint", text: "Otherwise the files stay where they are and Reelix looks in the new folder from now on." }))));
  const start = { profile: profile.value, folder: folder.value };  // only what the person changes is sent
  const panel = sidePanel({ title: `${item.title}: quality and folder`, opener, body: [form], foot: [save, cancel] });
  setTimeout(() => profile.focus(), 0);
  cancel.addEventListener("click", () => panel.close());
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = { id: item.id };
    if (profile.value !== start.profile) body.profile_id = Number(profile.value);
    if (folder.value !== start.folder) { body.folder_id = Number(folder.value); body.move_files = move.checked; }
    if (!body.profile_id && !body.folder_id) { panel.close(); return; }
    save.disabled = true;
    try {
      const r = await api(`/api/library/change?tab=${ITEM_TAB}`, { method: "POST", body });
      panel.close();
      announce(r.said);
      toast(r.said);
      if (r.item) show(r.item);
    } catch (err) { problem(err.message, save); save.disabled = false; }
  });
}

// DASH-209, the item's extras in their own tab, read only when the tab is opened: Refresh, Rescan and Rename (films
// and series), the files on disk with Delete this file, and the item's own history, newest first.
function extras(item) {
  const video = ["films", "tv"].includes(ITEM_TAB);
  const filesBox = el("div", { "aria-busy": "true" });
  const historyBox = el("div", { "aria-busy": "true" });
  const run = async (action, button, extra = {}) => {
    button.disabled = true;
    try {
      const r = await api(`/api/library/extras?tab=${ITEM_TAB}`, { method: "POST", body: { id: item.id, action, ...extra } });
      announce(r.said);
      toast(r.said);
      return true;
    } catch (e) { problem(e.message, button); return false; }
    finally { button.disabled = false; }
  };
  const loadFiles = async () => {
    filesBox.setAttribute("aria-busy", "true");
    try {
      const { files } = await api(`/api/library/extras?tab=${ITEM_TAB}&id=${item.id}&part=files`);
      filesBox.replaceChildren(files.length ? el("ul", { class: "rows lib-files", "aria-label": "Files" }, ...files.map((f) => el("li", { class: "row row--no-lead" },
        el("div", {}, el("h3", { class: "row__title lib-files__name", text: f.name }),
          el("div", { class: "row__meta", text: [formatBytes(f.size), f.quality, f.group].filter(Boolean).join(" · ") })),
        el("div", { class: "row__side" }, el("button", { type: "button", class: "btn btn--quiet btn--compact btn--danger", "aria-label": `Delete ${f.name}`,
          onclick: async (e) => {
            const button = e.currentTarget;  // read before the dialog: currentTarget is empty after an await
            const ok = await confirmDialog({ title: "Delete this file?", danger: true, confirm: "Delete",
              message: `${f.name} is deleted from the disk. Reelix keeps the ${ITEM_TAB === "films" ? "film" : "series"} and looks for it again only if you follow it.` });
            if (ok && await run("delete-file", button, { file_id: f.id })) { await loadFiles(); $("#extras-files-heading").focus(); }
          } }, icon("trash-2"), "Delete")))))
        : el("p", { class: "muted", text: "No files on disk yet." }));
    } catch (e) { filesBox.replaceChildren(el("p", { class: "muted", text: e.message })); }
    filesBox.setAttribute("aria-busy", "false");
  };
  const loadHistory = async () => {
    try {
      const { history } = await api(`/api/library/extras?tab=${ITEM_TAB}&id=${item.id}&part=history`);
      historyBox.replaceChildren(history.length ? el("ul", { class: "rows" }, ...history.map((h) => el("li", { class: "row row--no-lead" },
        el("div", {}, el("h3", { class: "row__title", text: [h.what, h.episode].filter(Boolean).join(", ") }),
          el("div", { class: "row__meta", text: [h.date ? formatDate(h.date, true) : "", h.title, h.where].filter(Boolean).join(" · ") })))))
        : el("p", { class: "muted", text: "Nothing has happened to it yet." }));
    } catch (e) { historyBox.replaceChildren(el("p", { class: "muted", text: e.message })); }
    historyBox.setAttribute("aria-busy", "false");
  };
  const buttons = video ? el("div", { class: "actions" },
    el("button", { type: "button", class: "btn", onclick: (e) => run("refresh", e.currentTarget) }, icon("refresh-cw"), "Refresh"),
    el("button", { type: "button", class: "btn", onclick: (e) => run("rescan", e.currentTarget).then((ok) => ok && loadFiles()) }, icon("hard-drive"), "Rescan the files"),
    el("button", { type: "button", class: "btn", onclick: (e) => renameFiles(item, e.currentTarget, loadFiles) }, icon("pencil"), "Rename the files")) : null;
  const body = el("div", { class: "stack-4" },
    buttons ? el("p", { class: "muted", text: "Refresh reads its details again. Rescan only looks at the files on disk." }) : null, buttons,
    video ? el("section", { class: "stack-2", "aria-labelledby": "extras-files-heading" },
      el("h2", { class: "lib-panel-heading", id: "extras-files-heading", tabindex: "-1", text: "Files" }), filesBox) : null,
    el("section", { class: "stack-2", "aria-labelledby": "extras-history-heading" },
      el("h2", { class: "lib-panel-heading", id: "extras-history-heading", text: "History" }), historyBox));
  return { key: "extras", label: video ? "Files and history" : "History", heading: "", body,
    onOpen: () => { if (video) loadFiles(); loadHistory(); } };
}

// Rename the files (DASH-209): a slide-out with each name now and after, and Rename only when something changes.
async function renameFiles(item, opener, after) {
  let changes;
  try { ({ changes } = await api(`/api/library/extras?tab=${ITEM_TAB}&id=${item.id}&part=rename`)); } catch (e) { problem(e.message, opener); return; }
  const rename = el("button", { type: "button", class: "btn btn--primary", text: "Rename", disabled: !changes.length });
  const cancel = el("button", { type: "button", class: "btn", text: changes.length ? "Cancel" : "Close" });
  const body = changes.length ? [el("p", { text: `${changes.length} ${changes.length === 1 ? "file changes" : "files change"} to match your naming settings.` }),
    el("ul", { class: "rows lib-rename" }, ...changes.map((c) => el("li", { class: "row row--no-lead" }, el("div", {},
      el("div", { class: "row__meta", text: `Now: ${c.now}` }), el("div", { class: "row__title", text: `After: ${c.after}` })))))]
    : [el("p", { text: "Every file already matches your naming settings. Nothing to rename." })];
  const panel = sidePanel({ title: `Rename the files of ${item.title}`, opener, body, foot: [rename, cancel], wide: true });
  setTimeout(() => (changes.length ? rename : cancel).focus(), 0);
  cancel.addEventListener("click", () => panel.close());
  rename.addEventListener("click", async () => {
    rename.disabled = true;
    try {
      const r = await api(`/api/library/extras?tab=${ITEM_TAB}`, { method: "POST", body: { id: item.id, action: "rename", file_ids: changes.map((c) => c.file_id) } });
      panel.close();
      announce(r.said);
      toast(r.said);
      setTimeout(after, 1500);
    } catch (e) { problem(e.message, rename); rename.disabled = false; }
  });
}

async function removeItem(item, button) {
  const files = el("input", { type: "checkbox", id: "delete-files" });
  const ok = await confirmDialog({ title: `Delete ${item.title}?`, danger: true, confirm: "Delete",
    message: `Reelix stops following it and takes it out of your library.`,
    fields: item.can?.has_file ? [el("label", { class: "check" }, files, el("span", { class: "check__text" }, el("strong", { text: "Delete its files too" }),
      el("span", { class: "check__hint", text: "They go to Reelix's recycle bin when it has one; otherwise they cannot be brought back." })))] : [] });
  if (ok) act("delete", { delete_files: files.checked }, button);
}

// Change match (owner, 11 November 2026): search for what it really is, choose it, and Starboard moves it in Reelix
// (the files stay where they are; if Reelix will not take the new match, the old one is put back).
async function changeMatch(item, button) {
  const search = el("input", { class: "input", type: "search", id: "match-q", value: item.title || "", autocomplete: "off" });
  const results = el("div", { class: "stack-2", "aria-live": "polite" });
  let chosen = null;
  const find = async () => {
    results.replaceChildren(el("p", { class: "muted", text: "Searching…" }));
    try {
      const r = await api(`/api/library/match?tab=${ITEM_TAB}&q=${encodeURIComponent(search.value.trim())}`);
      const name = `match-${Date.now()}`;
      results.replaceChildren(r.results.length ? el("fieldset", { class: "stack-2" }, el("legend", { class: "visually-hidden", text: "Matches" }),
        el("div", { class: "option-cards" }, r.results.map((m) => el("label", { class: "option-card" },
          el("input", { type: "radio", name, value: m.key, onchange: () => { chosen = m.key; } }),
          el("strong", { text: `${m.title}${m.year ? ` (${m.year})` : ""}` }),
          el("small", { text: [m.detail, m.in_library ? "Already in your library" : ""].filter(Boolean).join(". ") }))))) :
        el("p", { class: "muted", text: "Nothing found. Try other words." }));
    } catch (e) { results.replaceChildren(notice("danger", "Search did not work", e.message)); }
  };
  const go = el("button", { type: "button", class: "btn" }, icon("search"), "Search");
  go.addEventListener("click", find);
  search.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); find(); } });
  find();
  const ok = await confirmDialog({ title: `Change what ${item.title} is matched to`, confirm: "Use this match",
    message: el("p", { text: "Search, then choose the right one. Its files stay where they are; Reelix reads them again under the new match." }),
    fields: [el("div", { class: "stack-2" }, el("label", { class: "field__label", for: "match-q", text: "Search for" }),
      el("div", { class: "actions" }, search, go)), results] });
  if (!ok) return;
  if (!chosen) { problem("Choose one of the matches first", button); return; }
  button.disabled = true;
  try {
    const out = await api(`/api/library/match?tab=${ITEM_TAB}`, { method: "POST", body: { id: current.id, key: chosen } });
    toast(out.said);
    if (out.id && String(out.id) !== String(current.id)) { const u = new URL(location.href); u.searchParams.set("id", out.id); location.replace(u); }
    else location.reload();
  } catch (e) { problem(e.message, button); }
  finally { button.disabled = false; }
}

function head(item) {
  const fan = item.poster ? el("div", { class: "cover-fan lib-fan", "aria-hidden": "true" },
    el("img", { src: item.poster, alt: "", decoding: "async", onerror: (e) => e.target.closest(".cover-fan")?.remove() })) : null;
  const can = item.can || {};
  // DASH-158: how Reelix follows a radio show, changed here.
  const follow = ITEM_TAB === "radio" && item.following ? (() => {
    const pick = el("select", { class: "select", id: "radio-follow", "aria-label": "Following" },
      [["all", "Every episode"], ["from_now_on", "New episodes from now on"], ["none", "Not following"]].map(([v, t]) =>
        el("option", { value: v, text: t, selected: item.following === v })));
    pick.addEventListener("change", () => act(pick.value === "none" ? "unfollow" : "follow", { scope: pick.value }, pick));
    return el("label", { class: "series-head__follow" }, el("span", { class: "field__label", text: "Following" }), pick);
  })() : null;
  // DASH-319: how many of a podcast's newest episodes to keep (older ones are deleted by Reelix). A button that
  // opens a choice and Save, so moving through the choices with the arrow keys does nothing until Save.
  const keepLabel = (v) => (v === "all" ? "Every episode" : `The newest ${v}`);
  const keep = ITEM_TAB === "radio" && item.keep ? el("button", { type: "button", class: "btn", id: "radio-keep",
    onclick: async (e) => {
      const button = e.currentTarget;
      const choices = ["all", ...item.keep.choices];
      const radios = choices.map((v) => el("input", { type: "radio", name: "keep", value: String(v), checked: String(item.keep.value) === String(v) }));
      const group = el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Keep" }),
        ...choices.map((v, n) => el("label", { class: "check" }, radios[n], el("span", { class: "check__text", text: keepLabel(v) }))));
      const ok = await confirmDialog({ title: `How many episodes of ${item.title} to keep`, confirm: "Save",
        message: "With a number, Reelix deletes the files of older episodes and does not download them again.", fields: [group] });
      const chosen = radios.find((r) => r.checked)?.value;
      if (ok && chosen && chosen !== String(item.keep.value)) act("keep", { scope: chosen }, button);
    } }, "Keep: ", keepLabel(item.keep.value)) : null;
  const actions = [
    can.get ? el("button", { type: "button", class: "btn btn--primary", onclick: (e) => act("get", {}, e.currentTarget) },
      icon("download"), ITEM_TAB === "tv" ? "Get the missing episodes" : "Get it") : null,
    item.listen ? newTabLink(item.listen.href, item.listen.label, { className: "btn btn--primary" }) : null,
    follow,
    keep,
    item.can ? el("button", { type: "button", class: "btn", "aria-pressed": String(!!can.follow),
      onclick: (e) => act(can.follow ? "unfollow" : "follow", {}, e.currentTarget) }, can.follow ? "Stop following" : "Follow") : null,
    ITEM_TAB === "films" && !can.has_file ? el("button", { type: "button", class: "btn", onclick: () => chooseDownload({ scope: "item" }, item.title) },
      icon("list"), "Choose a download") : null,
    watchedButton(item.watched, item.title, false),
    can.change ? el("button", { type: "button", class: "btn btn--quiet", onclick: (e) => qualityAndFolder(item, e.currentTarget) },
      icon("sliders-horizontal"), "Quality and folder") : null,
    item.open ? newTabLink(item.open.href, item.open.label, { className: "btn btn--quiet" }) : null,
    ["films", "tv", "radio", "audiobooks", "books"].includes(ITEM_TAB) ? el("button", { type: "button", class: "btn btn--quiet",
      onclick: (e) => changeMatch(item, e.currentTarget) }, icon("refresh-cw"), "Change match") : null,
    can.delete ? el("button", { type: "button", class: "btn btn--quiet btn--danger", onclick: (e) => removeItem(item, e.currentTarget) }, "Delete") : null,
  ].filter(Boolean);
  return el("header", { class: "series-head" },
    el("div", { class: "series-head__text" },
      el("h1", { class: "series-head__name wordmark", text: item.title }),
      el("p", { class: "series-head__meta" }, ...item.meta.map((m) => item.network_logo && m === item.network_logo.name
        ? el("span", { class: "series-head__network" }, logoTone(el("img", { src: item.network_logo.src, alt: "", onerror: (e) => e.target.remove() }), item.network_logo.name, item.network_logo.tone), el("span", { text: m }))
        : el("span", { text: m })), item.status ? chip(item.status, item.tone) : null),
      item.overview ? el("p", { class: "series-head__desc clamp-3", text: item.overview }) : null,
      item.progress ? el("div", { class: "series-head__progress" }, el("span", { text: item.progress.text }),
        el("div", { class: "progress", role: "progressbar", "aria-label": item.progress.text, "aria-valuenow": String(Math.round(100 * item.progress.have / Math.max(1, item.progress.total))),
          "aria-valuemin": "0", "aria-valuemax": "100" }, bar(item.progress))) : null,
      actions.length ? el("div", { class: "series-head__actions" }, ...actions) : null),
    fan);
}

function show(item, said = "") {
  current = item;
  const box = $("#item");
  const open = $("[role=tab][aria-selected=true]", box)?.id;
  const parts = item.lists.filter((l) => l.rows.length).map((l) => ({ key: l.key, label: l.label, heading: l.heading, body: groupList(l) }));
  parts.push({ key: "about", label: "About", heading: "", body: about(item) });
  if (ITEM_TAB === "films") parts.unshift(parts.pop()); // a film opens on About, then its collection
  if (ITEM_TAB !== "radio") parts.push(extras(item));
  const note = said ? el("div", { class: "notice", "data-tone": "success", role: "status" }, icon("circle-check"),
    el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: said }))) : null;
  box.replaceChildren(head(item), ...(note ? [note] : []), ...(parts.length > 1 ? tabs(parts) : [parts[0].body]));
  if (open) document.getElementById(open)?.click();  // the same tab stays open after a change
  box.setAttribute("aria-busy", "false");
}

startPage().then(async () => {
  const [wallPage, wallLabel] = WALL[ITEM_TAB];
  const box = $("#item");
  const id = new URLSearchParams(location.search).get("id") || "";
  $("#item-back").replaceChildren(icon("arrow-left"), wallLabel);
  $("#item-back").href = `/${wallPage}`;
  if (!/^\d{1,12}$/.test(id)) {
    // Every page has one h1, an error page too (ACCESSIBILITY.md).
    box.replaceChildren(el("h1", { class: "visually-hidden", text: wallLabel }),
      emptyState("Nothing chosen", "That page needs an item from the Library.", el("a", { class: "btn btn--primary", href: `/${wallPage}`, text: `Open ${wallLabel}` })));
    box.setAttribute("aria-busy", "false");
    return;
  }
  try {
    const item = await api(`/api/library/item?tab=${ITEM_TAB}&id=${id}`);
    document.title = `${item.title} · ${document.title}`;
    show(item);
  } catch (e) {
    box.setAttribute("aria-busy", "false");
    box.replaceChildren(el("h1", { class: "visually-hidden", text: wallLabel }), el("div", { class: "notice", "data-tone": e.status === 409 ? "info" : "danger", role: "alert" },
      icon(e.status === 409 ? "info" : "circle-x"),
      el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: e.status === 502 ? "Reelix did not find it" : "This page could not be read" }),
        el("p", { text: e.message }))));
  }
});
