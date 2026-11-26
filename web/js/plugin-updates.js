// Check for updates now, for plug-ins (owner, 26 November 2026): Starboard reads each plug-in catalogue again, however
// recently it read them, and says when it last did, which ones did not answer and why. Used by the Catalogue, a plug-in's
// Versions tab and Settings, Plug-ins, Manage. Loaded only by those pages: nothing here runs until the button is pressed.

let catalogueSaid = null;  // what the last check said, kept across the page being drawn again: { text, failed: [{name, error}] }

// When the catalogues were last read, in words. read: { read_at (seconds, 0 for never), errors }.
function catalogueReadWords(read) {
  if (!read || !read.read_at) return "The catalogues have not been read since Starboard started.";
  return `The catalogues were last checked ${checkedWhen(read.read_at)}.${read.errors ? ` ${read.errors === 1 ? "One" : read.errors} did not answer.` : ""}`;
}

// The words after a check: what was read, how many plug-ins have a newer version, and what did not answer.
function catalogueCheckWords(got) {
  if (got.too_soon) return got.said;
  const n = got.catalogues.length, u = got.updates || 0;
  const read = `Read ${n} ${n === 1 ? "catalogue" : "catalogues"}.`;
  const found = u ? `${u} ${u === 1 ? "plug-in has" : "plug-ins have"} a newer version.` : "No plug-in has a newer version.";
  const failed = got.catalogues.filter((c) => !c.ok);
  return `${read} ${found}${failed.length ? ` ${failed.length === 1 ? "One catalogue" : `${failed.length} catalogues`} did not answer.` : ""}`;
}

// The button, when the catalogues were last read, and (after a check) what it found. onDone(got) draws the page again;
// the button is drawn again with it, so focus is put back on it, and the words are announced politely.
function catalogueCheck({ read, onDone, id = "pl-check-now", whenId = "" }) {
  // whenId: the page already says when they were read, in the line with that id, so this adds no second one.
  const when = whenId ? null : el("p", { class: "small muted", id: `${id}-when`, text: catalogueReadWords(read) });
  const button = el("button", { type: "button", class: "btn", id, "aria-describedby": whenId || `${id}-when` }, icon("refresh-cw"), "Check for updates now");
  const said = catalogueSaid;
  catalogueSaid = null;
  const out = el("div", { class: "stack-2", id: `${id}-result` });
  if (said) {
    out.append(...[el("p", { class: "small", text: said.text }),
      said.failed.length ? el("ul", { class: "settings-rows", "aria-label": "Catalogues that did not answer" },
        said.failed.map((c) => el("li", { class: "setting" }, el("div", { class: "setting__text" },
          el("span", { class: "setting__label" }, c.name, " ", chip(...STATUS.notResponding)),
          el("span", { class: "setting__hint", text: c.error ? `${c.error.replace(/^That address did not answer: /, "The catalogue did not answer: ")}.`.replace(/\.\.$/, ".") : "" }))))) : null].filter(Boolean));
  }
  button.addEventListener("click", async () => {
    if (button.getAttribute("aria-disabled")) return;
    button.setAttribute("aria-disabled", "true");
    button.lastChild.textContent = "Checking…";
    announce("Reading the plug-in catalogues…");
    let text, failed = [];
    try {
      const got = await api("/api/plugins/catalogue/check", { method: "POST" });
      text = catalogueCheckWords(got);
      failed = got.too_soon ? [] : got.catalogues.filter((c) => !c.ok).map((c) => ({ name: c.name, error: c.error }));
    } catch (e) { text = `Starboard could not check: ${e.message}`; }
    catalogueSaid = { text, failed };
    announce(text);
    if (onDone) await onDone();
    // The page is drawn again with the button: focus stays on it, so it is not lost to the page.
    document.getElementById(id)?.focus();
  });
  return el("div", { class: "stack-2", "data-catalogue-check": "" }, el("div", { class: "actions" }, button), when, out);
}

// The plug-in update list (owner, 26 November 2026), the same on Settings, Plug-ins, Manage and Settings, Updates,
// Plug-ins, and laid out as System, Apps, Updates is: a summary with when it was last checked, Check for updates now and
// Update all, a table with the version you have beside the new one, ticks and Update chosen, What is new, and the result
// said in a live region. The rows come from /api/plugins/updates; the update is the batch Install all updates runs
// (a copy first, a check afterwards, the way back by itself), with the Starboard password asked once.

// What is new in one plug-in's waiting update (a slide-out, read from its new manifest only when pressed).
async function pluginWhatsNew(t, opener) {
  const pid = t.id.split(":")[1];
  const panel = sidePanel({ title: `What is new in ${t.name} ${t.latest}`, opener, wide: true, body: [el("p", { class: "muted", role: "status", text: "Reading the notes…" })] });
  let s;
  try { s = await api(`/api/plugins/${encodeURIComponent(pid)}/update`, { method: "POST", body: { preview: true } }); }
  catch (e) { panel.setBody([notice("danger", "Starboard could not read the notes", e.message)]); return; }
  const notes = s.whats_new?.length
    ? s.whats_new.map((v) => el("section", { class: "release-notes" }, el("h3", { text: `Version ${v.version}${v.date ? `, ${v.date}` : ""}` }),
      ...v.sections.flatMap((sec) => [el("h4", { text: sec.type }), el("ul", {}, sec.items.map((x) => el("li", {}, ...changeParts(x))))])))
    : [el("p", { text: s.changelog || "Its maker did not list what changed in this version." })];
  const perms = s.new_permissions?.length
    ? [notice("warning", "New permissions", `Version ${s.version} asks for more than ${s.from}: ${s.new_permissions.join(", ")}. Update it on its own page, where each one is explained.`),
      el("p", {}, el("a", { class: "btn", href: `/settings-plugin.html?id=${encodeURIComponent(pid)}` }, "Open its page"))] : [];
  panel.setBody([...perms, ...notes]);
}

const PLUGIN_UPDATE_WAIT = "Waits for you";

// A plug-in's status cell, the same on every page: Update available, New permissions (words and a shape) and Waits for you,
// then what the new permissions are and what is new.
function pluginStatus(t, { extraChips = [] } = {}) {
  if (!t.update_available) return t.can_roll_back ? [chip(...STATUS.upToDate), el("div", { class: "small muted", text: `Version ${t.roll_back_to} is kept for Roll back` })] : chip(...STATUS.upToDate);
  const perms = t.new_permissions?.length ? t.new_permissions.map((p) => `${p.words} (${p.risk} risk)`).join("; ") : "";
  const parts = [chip(...STATUS.updateAvailable), perms ? chip("New permissions", "warning", "triangle-alert") : null,
    t.held ? chip(PLUGIN_UPDATE_WAIT, "muted", "pause") : null, ...extraChips].filter(Boolean);
  const words = [perms ? `New permissions: ${perms}.` : "", t.held ? `${t.held}.` : "", t.note].filter(Boolean).join(" ");
  return [el("div", { class: "chips" }, parts), words ? el("div", { class: "small muted", text: words }) : null];
}

function pluginUpdatesArea({ mount, full = false }) {
  let data = null, batch = null;
  const chosen = new Set();
  const summaryId = "plu-summary", live = el("div", { class: "visually-hidden", role: "status", "aria-live": "polite", id: "plu-live" });
  const result = el("div", { class: "stack-2", id: "plu-result" });
  const batchBox = el("div", { id: "plu-batch" });
  const ready = () => data.items.filter((t) => t.update_available);
  const goes = (t) => t.update_available && !t.held;  // what Update all takes: not a plug-in that waits for you

  const table = () => {
    if (!data.items.length) return emptyState("No plug-ins to update", "Plug-ins you add from the catalogue are listed here.", el("a", { class: "btn", href: "/settings-plugins-catalogue.html" }, "Open the catalogue"));
    return updateTable({ caption: "Updates for your plug-ins", nameLabel: "Plug-in", rows: data.items.map((t) => {
      const page = `/settings-plugin.html?id=${encodeURIComponent(t.id.split(":")[1])}`;
      const acts = [];
      if (t.update_available) {
        const b = el("button", { type: "button", class: "btn btn--compact" }, "What is new", el("span", { class: "visually-hidden", text: ` in ${t.name}` }));
        b.addEventListener("click", () => pluginWhatsNew(t, b));
        acts.push(b);
        if (t.held) acts.push(el("a", { class: "btn btn--compact btn--primary", href: page }, "Update on its page", el("span", { class: "visually-hidden", text: `: ${t.name}` })));
      }
      if (full && t.can_roll_back) {
        const r = el("button", { type: "button", class: "btn btn--compact" }, icon("undo-2"), `Roll back to ${t.roll_back_to}`, el("span", { class: "visually-hidden", text: `: ${t.name}` }));
        r.addEventListener("click", () => rollBack(t, r));
        acts.push(r);
      }
      return { id: t.id, name: updateName({ tick: goes(t) ? updateTick(t.id, t.name, chosen, bar, !!batch?.running()) : null,
        picture: pluginLogo({ name: t.name, logo: t.logo }, { compact: true }), name: t.name, href: page, sub: systemChip(t.system) ? el("div", {}, systemChip(t.system)) : null }),
        installed: t.current || "Not known", latest: t.update_available ? t.latest : "", status: pluginStatus(t), actions: acts };
    }) });
  };

  const rollBack = async (t, opener) => {
    const pid = t.id.split(":")[1];
    try {
      const r = await updateWithPassword({ title: `Roll back ${t.name} to ${t.roll_back_to}?`, confirm: "Roll back",
        steps: [`${t.name} goes back to the version you had before, with no download.`, `Version ${t.current} is kept, in case you want it again.`],
        send: (password) => api(`/api/plugins/${encodeURIComponent(pid)}/rollback`, { method: "POST", body: { password } }) });
      if (!r) { opener?.focus(); return; }
      const job = taskJob({ title: `Rolling ${t.name} back to ${t.roll_back_to}`, url: r.job, failedWord: "Stopped here", returnTo: "plu-h" });
      job.open();
      const j = await job.follow((x) => ({ title: x.title, text: x.text }));
      await load();
      draw();
      announce(`${j.title || "Roll back finished"}. ${j.text || ""}`);
    } catch (e) { problem(e.message, opener); }
  };

  const chosenBar = updateSelectionBar({ id: "plu-chosen", onUpdate: (b) => batch.install(b, [...chosen]), onClear: () => { chosen.clear(); draw(); announce("None chosen"); } });
  const bar = () => chosenBar.set(chosen.size, !!batch?.running());

  const summaryText = () => updateSummary({ checkedAt: data.read.read_at, count: ready().length,
    extra: ready().some((t) => t.held) ? [`${ready().filter((t) => t.held).length} waiting for you`] : [] });

  const head = () => {
    const n = ready().filter(goes).length;
    const all = el("button", { type: "button", class: "btn btn--primary", id: "plu-update-all", "aria-haspopup": "dialog", disabled: !n || !!batch?.running() },
      icon("circle-arrow-up"), n ? `Update all (${n})` : "Update all");
    all.addEventListener("click", () => batch.install(all));
    return [el("div", { class: "actions" }, catalogueCheck({ read: data.read, onDone: reload, id: "plu-check", whenId: summaryId }), all),
      el("p", { class: "small muted", id: summaryId, text: summaryText() })];
  };

  const autoSection = () => {
    const a = data.auto;
    const input = el("input", { type: "checkbox", id: "plu-auto", checked: a.active });
    input.addEventListener("change", async () => {
      try { await saveGeneral({ [a.key]: input.checked }, true); a.active = input.checked; announce(`Plug-ins ${input.checked ? "update by themselves" : "wait for you"}.`); }
      catch (e) { input.checked = !input.checked; problem(e.message, input); }
    });
    const last = a.last ? ` Last checked ${timeAgo(a.last.at * 1000)}: ${a.last.runs.length ? a.last.runs.map((r) => `${r.name} ${(RUN_WORDS[r.state] || RUN_WORDS.failed)[0].toLowerCase()}`).join(", ") : "nothing to update"}.` : "";
    return el("section", { class: "settings-section", "aria-labelledby": "plu-auto-h" },
      el("div", { class: "settings-section__head" }, el("h2", { id: "plu-auto-h", text: "Update by themselves" }),
        el("p", { class: "small muted", text: `Plug-ins that ask for new permissions never update by themselves. They update in ${data.hours_words}, set in Settings, Updates.` })),
      el("ul", { class: "settings-rows" }, el("li", { class: "setting" },
        switchRow("Plug-ins: update by themselves", `Deactivated: they wait for you, and you are told when an update is ready.${last}`, input),
        el("dl", { class: "facts small" }, el("dt", { text: "Copy first" }), el("dd", { text: a.safety.copy }),
          el("dt", { text: "Checked by" }), el("dd", { text: a.safety.check }), el("dt", { text: "Way back" }), el("dd", { text: a.safety.back })))));
  };

  const historySection = () => el("section", { class: "settings-section", "aria-labelledby": "plu-history-h" },
    el("div", { class: "settings-section__head" }, el("h2", { id: "plu-history-h", text: "History" }),
      el("p", { class: "small muted", text: "The last plug-in updates and roll backs, by you or by themselves, with what each said." })),
    el("ul", { class: "settings-rows", "aria-labelledby": "plu-history-h" }, (data.recent.length ? data.recent : [null]).map((r) => {
      if (!r) return el("li", { class: "setting" }, el("div", { class: "setting__text" }, el("span", { class: "setting__hint", text: "No plug-in has been updated yet." })));
      const [word, tone] = RUN_WORDS[r.state] || RUN_WORDS.failed;
      const change = r.action === "rollback" ? `Back to ${r.to}` : r.from && r.to ? `${r.from} to ${r.to}` : r.to || "";
      return el("li", { class: "setting" }, el("div", { class: "setting__text" },
        el("span", { class: "setting__label" }, r.name, " ", chip(word, tone)),
        el("span", { class: "setting__hint", text: [change, `${r.action === "rollback" ? "rolled back" : "updated"} ${byWords(r.by)}`, r.started_at ? timeAgo(Date.parse(r.started_at)) : ""].filter(Boolean).join(" · ") }),
        r.said ? el("span", { class: "setting__hint", text: r.said }) : null));
    })));

  const load = async () => { data = await api("/api/plugins/updates"); };
  const draw = () => {
    const had = document.activeElement?.id;
    const sections = [el("section", { class: "settings-section", "aria-labelledby": "plu-h" },
      el("div", { class: "settings-section__head" }, el("h2", { id: "plu-h", tabindex: "-1", text: full ? "Ready to update" : "Plug-in updates" }),
        el("p", { class: "small muted", text: "Each update keeps a copy of the plug-in first, checks the new version afterwards and goes back by itself if it does not answer. Nothing changes without your Starboard password." })),
      ...head(), result, batchBox, table(),
      chosenBar.node,
      live)];
    if (full) sections.push(autoSection(), historySection());
    else sections.push(el("p", { class: "small muted" }, "The setting for updating by themselves, and the history of updates, are in ", el("a", { href: "/settings-updates-plugins.html", text: "Updates, Plug-ins" }), "."));
    mount.replaceChildren(...sections);
    const b = batch.node();
    if (b) batchBox.replaceChildren(b);
    bar();
    if (had && document.getElementById(had)) document.getElementById(had).focus();
  };
  const reload = async () => { try { await load(); } catch { return; } draw(); };
  batch = updateBatchPanel({ mount: batchBox, result, kinds: ["plugin"], ready: () => ready().filter(goes).length,
    onSettled: async () => { chosen.clear(); await reload(); },
    onClosed: () => { batchBox.replaceChildren(); draw(); const h = document.getElementById("plu-h"); h?.focus(); announce("Install all updates closed."); } });
  return load().then(async () => {
    if (!full && !data.items.length) { mount.replaceChildren(); return; }  // Manage with no plug-ins says so itself
    draw();
    const latest = (await api("/api/updates").catch(() => null))?.batch;  // a batch that began earlier is shown again
    if (latest) batch.show(latest);
  }).catch((e) => { mount.replaceChildren(notice("danger", "Could not list the plug-in updates", e.message)); });
}

document.addEventListener("DOMContentLoaded", () => {
  if ($("#plugin-updates") && $("#plugin-updates").closest("main").querySelector("h1")?.textContent === "Plug-in updates") {
    pluginUpdatesArea({ mount: $("#plugin-updates"), full: true }).then(() => $("#plugin-updates").removeAttribute("aria-busy"));
  }
});
