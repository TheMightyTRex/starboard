// Settings, Plug-ins (DASH-149): the plug-ins added, Add a plug-in with what it may do shown before anything
// is installed, Activate and Deactivate, Remove (its folder is kept), Deactivate all plug-ins, and each plug-in's settings,
// drawn by Starboard from its manifest. A plug-in never adds code to this page.

const RISK = { low: ["Low", "success"], medium: ["Medium", "warning"], high: ["High", "danger"] };
const STATE = { installed: ["Added, not active", "muted"], enabled: ["Active", "success"], disabled: ["Inactive", "muted"], failed: ["Did not start", "danger"],
  "needs-setup": ["Needs setting up", "warning"], "not-supported": ["Not supported", "danger"] };  // DASH-330
const stateOf = (p) => p.status?.state || p.state;
// An active plug-in that is not answering its health path, or resting after idle stop (DASH-357).
const chipOf = (p) => {
  if (stateOf(p) === "enabled" && p.health && p.health !== "ok") return ["Not answering", "warning"];
  if (stateOf(p) === "enabled" && p.resting?.length) return ["Resting", "muted"];
  return STATE[stateOf(p)] || ["Unknown", "muted"];
};
const healthNote = (p) => {
  if (stateOf(p) !== "enabled") return null;
  if (p.health && p.health !== "ok") return el("div", { class: "notice", "data-tone": "warning", role: "note" }, icon("triangle-alert"),
    el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: "Not answering" }),
      el("p", { text: `It is active, but it is not answering. ${p.health}. Deactivate it and activate it again to restart it.` })));
  if (p.resting?.length) return el("p", { class: "small", text: "Resting: nothing has used it for a while, so it is stopped to save memory. It starts again by itself when Starboard needs it." });
  return null;
};

function pluginPermissions(list) {
  if (!list.length) return el("p", { class: "small", text: "It asks for nothing beyond its own folder." });
  return el("ul", { class: "rows" }, list.map((p) => el("li", { class: "row row--no-lead" },
    el("div", {}, el("div", { class: "row__title", text: p.words }), el("div", { class: "row__meta", text: p.permission })),
    el("div", { class: "row__side" }, chip(...RISK[p.risk])))));
}

// The install warning (owner, 12 November 2026): a slide-out that says the plug-in is added at your own risk, then
// what it can see, change and reach and what it runs, with Install and Cancel. Resolves with the password, or null.
function installWarning(s, { builtin = false, opener, verb = "Install" } = {}) {
  return new Promise((resolve) => {
    const w = s.warning;
    let answer = null;
    const group = (title, ic, items, empty) => el("section", { class: "stack-2", "aria-label": title },
      el("h3", {}, icon(ic), ` ${title}`),
      items.length ? el("ul", { class: "install-warning__list" }, items.map((t) => el("li", { text: t }))) : el("p", { class: "small muted", text: empty }));
    const pw = el("input", { class: "input", type: "password", id: "pl-install-password", autocomplete: "current-password", required: true });
    const install = el("button", { type: "submit", class: "btn btn--primary", form: "pl-install-form" }, `${verb} ${s.name}`);
    const cancel = el("button", { type: "button", class: "btn" }, "Cancel");
    const form = el("form", { id: "pl-install-form", class: "form-stack", novalidate: true },
      field("Your Starboard password", pw, { hint: "To show it is you who is installing it." }));
    const panel = sidePanel({
      title: verb === "Install" ? `Install ${s.name}?` : `${verb} ${s.name} to ${s.version}?`, opener, wide: true,
      onClose: () => resolve(answer),
      body: [
        el("div", { class: "notice", "data-tone": w.risk === "high" ? "danger" : "warning", role: "note" }, icon("triangle-alert"),
          el("div", { class: "notice__body" },
            el("span", { class: "notice__title", text: builtin ? "Installed at your own risk" : "Made by someone else, installed at your own risk" }),
            el("p", { text: (builtin ? "It comes with Starboard, but it still runs on your server with the access below. "
              : "Starboard checks plug-ins and keeps them in a locked-down container, but it cannot vouch for what one does with the access below. ")
              + "Install it only if you trust who made it." }))),
        // The name with the risk on the same line, at the right (owner, 12 November 2026); who made it below.
        el("div", { class: "install-warning__head" }, el("strong", { text: `${s.name} ${s.version || ""}` }),
          w.risk ? chip(`${RISK[w.risk][0]} risk`, RISK[w.risk][1]) : null),
        el("p", { class: "small install-warning__by", text: [s.author && `By ${s.author}`, s.licence, s.homepage].filter(Boolean).join(" · ") }),
        s.description ? el("p", { text: s.description }) : null,
        // An update (DASH-330): what changed, and anything it may do that the installed version may not.
        s.changelog ? el("p", { class: "small" }, el("strong", { text: `New in ${s.version}: ` }), s.changelog) : null,
        s.new_permissions?.length ? el("div", { class: "notice", "data-tone": "warning", role: "note" }, icon("triangle-alert"),
          el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: "This version asks for more" }),
            el("ul", {}, s.permissions.filter((x) => s.new_permissions.includes(x.permission)).map((x) => el("li", { text: `New: ${x.words}` }))))) : null,
        group("It can see", "eye", w.see, "Nothing of yours."),
        group("It can change", "pencil", w.change, "Nothing: it has no folder and no keys."),
        group("It can reach", "globe", w.reach, "Nothing: it runs no containers."),
        w.runs.length ? group("It runs", "server", w.runs, "") : null,
        w.notices?.length ? group("Notices", "info", w.notices, "") : null,
        w.buttons.length ? el("p", { class: "small", text: `Its buttons: ${w.buttons.join(", ")}.` }) : null,
        el("p", { class: "small muted" }, el("strong", { text: "It can never reach " }), w.never),
        form],
      foot: [install, cancel],
    });
    cancel.addEventListener("click", () => panel.close());
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      setError(pw, "");
      if (!pw.value) { setError(pw, "Enter your Starboard password"); pw.focus(); return; }
      answer = pw.value;
      panel.close();
    });
    // Focus stays at the top (the shared slide-out's own start), so the warning is read before the password.
  });
}

// The tester's issues (DASH-284): errors first, each with where, what and how to fix it.
const SEVERITY = { error: ["Error", "danger"], warning: ["Warning", "warning"], info: ["Tip", "muted"] };
const count = (n, one) => `${n} ${one}${n === 1 ? "" : "s"}`;
function testReport(r) {
  const head = r.ok ? notice("success", "Ready to add", `${count(r.warnings, "warning")} and ${count(r.infos, "tip")}.`)
    : notice("danger", `${count(r.errors, "error")} to fix before it can be added`, `${count(r.warnings, "warning")} and ${count(r.infos, "tip")} as well.`);
  const acc = el("div", {}, el("div", { class: "title-chip" }, el("h4", { text: "Accessibility" }),  // DASH-309: the chip on its title's line
    chip(r.accessibility.passed ? "Passed" : "Failed", r.accessibility.passed ? "success" : "danger")),
    el("p", { class: "small", text: `Checked: ${r.accessibility.checked}.` }));
  const list = r.issues.length ? el("ul", { class: "rows" }, r.issues.map((i) => el("li", { class: "row row--no-lead" },
    el("div", {}, el("div", { class: "row__title", text: i.what }), el("div", { class: "row__meta", text: `${i.where} · ${i.area} · Fix: ${i.fix}` })),
    el("div", { class: "row__side" }, chip(...SEVERITY[i.severity]))))) : el("p", { class: "small", text: "No issues found." });
  return el("div", { class: "stack-4" }, head, acc, list);
}

// A plug-in's own settings: switches and choices apply at once and say so beside themselves (settings pattern 2);
// typed settings (words, numbers, keys) are one form with one Save at its foot (pattern 5).
// A plug-in's settings (DASH-307, Settings patterns 2 and 5): one section per group (plug-in API 1.5), the
// ungrouped ones in Settings. Switches, choices, numbers and folders apply at once with a saved note beside them
// (a required number stays in the form, so set-up is one Save); typed text is one form per section with one Save at
// its foot. Returns [{group, body}].
function pluginSettingsGroups(p, redraw) {
  const plain = p.settings.filter((s) => s.type !== "custom");
  if (!plain.length) return [];
  const put = (settings) => api(`/api/plugins/${p.id}/settings`, { method: "PUT", body: { settings } });
  const groups = new Map();
  for (const s of plain) {
    const g = s.group || "";
    if (!groups.has(g)) groups.set(g, []);
    groups.get(g).push(s);
  }
  // Ungrouped settings come first, under Settings.
  const order = [...groups.keys()].sort((x, y) => (x === "" ? -1 : y === "" ? 1 : 0));
  return order.map((g, n) => {
    const tag = `pl-${p.id}-g${n}`;
    const rows = [], typed = [], inputs = {};
    for (const s of groups.get(g)) {
      const id = `pl-${p.id}-${s.key}`;
      const noteId = `${id}-saved`;
      const row = (control) => {  // the saved note sits beside the control (.setting__control .saved-note)
        const li = settingRow(s.label, s.hint, control, `${id}-l`);
        li.querySelector(".setting__control").append(savedNote(noteId));
        return li;
      };
      if (s.type === "switch") {
        const input = el("input", { type: "checkbox", role: "switch", id, checked: !!s.value, "aria-labelledby": `${id}-l` });
        input.addEventListener("change", async () => {
          try { await put({ [s.key]: input.checked }); showSaved(noteId); }
          catch (err) { input.checked = !input.checked; problem(err.message, input); }
        });
        rows.push(row(el("label", { class: "switch" }, input)));
      } else if (s.type === "folder") {  // API 1.3: a folder inside the media folders the plug-in mounts, applied at once
        let was = s.value ?? "";
        const picker = locationPicker({ id, label: s.label, value: was, app: `plugin:${p.id}`, hint: s.hint,
          onChange: async (v) => {
            try { await put({ [s.key]: v }); was = v; showSaved(noteId); }
            catch (err) { picker.input.value = was; picker.refresh(); problem(err.message, picker.input); }
          } });
        rows.push(el("li", { class: "setting setting--location" }, picker.node, savedNote(noteId)));
      } else if (s.type === "choice") {
        const select = el("select", { class: "select", id, "aria-labelledby": `${id}-l` },
          (s.choices || []).map((c) => el("option", { value: c.value, text: c.label, selected: c.value === s.value })));
        let was = select.value;
        select.addEventListener("change", async () => {
          try { await put({ [s.key]: select.value }); was = select.value; showSaved(noteId); }
          catch (err) { select.value = was; problem(err.message, select); }
        });
        rows.push(row(select));
      } else if (s.type === "number" && !s.required) {  // pattern 2: a number applies when you leave it, unit beside it
        const input = el("input", { class: "input", id, type: "number", value: s.value ?? "", min: s.min, max: s.max, "aria-labelledby": `${id}-l` });
        let was = input.value;
        input.addEventListener("change", async () => {
          if (input.value === "" || !input.checkValidity()) { problem(`${s.label}: give a number from ${s.min ?? ""} to ${s.max ?? ""}`.replace("from  to ", ""), input); input.value = was; return; }
          try { await put({ [s.key]: Number(input.value) }); was = input.value; showSaved(noteId); }
          catch (err) { input.value = was; problem(err.message, input); }
        });
        rows.push(row(s.unit ? unitInput(input, s.unit) : input));
      } else {
        const input = el("input", { class: "input", id, type: s.type === "number" ? "number" : s.type === "secret" ? "password" : "text",
          value: s.value ?? "", min: s.min, max: s.max, autocomplete: s.type === "secret" ? "new-password" : "off",
          placeholder: s.type === "secret" && s.set ? "Set. Leave empty to keep it" : "" });
        inputs[s.key] = [s, input];
        if (s.required) { input.required = true; input.setAttribute("aria-required", "true"); }  // DASH-330
        const hint = s.required ? [s.hint, "Needed before it can start."].filter(Boolean).join(" ") : s.hint;
        typed.push(field(s.label, s.unit ? unitInput(input, s.unit) : input, { hint }));
      }
    }
    let form = null;
    if (typed.length) {
      form = el("form", { class: "form-stack", novalidate: true }, typed,
        el("div", { class: "actions" }, el("button", { type: "submit", class: "btn", text: "Save" }), savedNote(`${tag}-saved`)));
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const settings = {};
        for (const [key, [s, input]] of Object.entries(inputs)) settings[key] = s.type === "number" ? Number(input.value) : input.value;
        try {
          await put(settings);
          showSaved(`${tag}-saved`);
          if (p.status?.state === "needs-setup") { announce("Saved. Activate it on State when you are ready"); redraw(); }  // the state may have changed
        }
        catch (err) { problem(err.message, form.querySelector("button[type=submit]")); }
      });
    }
    return { group: g, id: n === 0 && g === "" ? `pl-${p.id}-settings` : tag,
      body: el("div", { class: "stack-4" }, ...[rows.length ? el("ul", { class: "settings-rows" }, rows) : null, form].filter(Boolean)) };
  });
}

// A picture of a style (DASH-284): a small page drawn by Starboard in the style's own colours, light and dark side
// by side. Colours go in through the style object, which the page's security policy allows.
function stylePicture(look, mode) {
  const c = look[mode];
  const box = el("div", { class: "style-pic", "aria-hidden": "true" },
    el("div", { class: "style-pic__head" }, el("span", { class: "style-pic__logo" }), el("span", { class: "style-pic__line" })),
    el("div", { class: "style-pic__body" },
      el("div", { class: "style-pic__rail" }, el("span"), el("span"), el("span")),
      el("div", { class: "style-pic__card" },
        el("span", { class: "style-pic__title", text: "Jellyfin" }), el("span", { class: "style-pic__muted", text: "Running" }),
        el("span", { class: "style-pic__link", text: "Open" }), el("span", { class: "style-pic__btn", text: "Save" }))));
  const map = { bg: "--p-bg", header: "--p-header", surface_raised: "--p-card", text: "--p-text", text_muted: "--p-muted",
    border: "--p-border", accent: "--p-accent", accent_text: "--p-accent-text", surface_sunken: "--p-rail" };
  for (const [k, v] of Object.entries(map)) box.style.setProperty(v, c[k]);
  box.style.setProperty("--p-radius", `${Math.min(look.radius, 12)}px`);
  box.style.setProperty("--p-font", look.font);
  box.style.setProperty("--p-shadow", look.shadow === "strong" ? `3px 3px 0 ${c.text}` : look.shadow === "soft" ? "0 4px 12px rgb(0 0 0 / 0.18)" : "none");
  return box;
}

// The Styles section: a picture of every style and Use this style, the same choice as Display's Style list.
// Starboard's own style, for the default card in the Styles section: its shape, and its colours from the design
// system palette chosen for it (DASH-388; Teal, tokens.css, unless another is chosen).
const STARBOARD_LOOK = { value: "", name: "Starboard's own style", radius: 8, font: "\"Atkinson Hyperlegible Next\", sans-serif", shadow: "soft" };
function ownLook(all) {
  const p = all[ownColours] || all.teal;
  const pick = (c) => Object.fromEntries(["bg", "header", "surface_raised", "surface_sunken", "text", "text_muted", "border", "accent", "accent_text"]
    .map((k) => [k, c[`color-${k.replace(/_/g, "-")}`]]));
  return { ...STARBOARD_LOOK, light: pick(p.light), dark: pick(p.dark),
    description: `${p.label} colours from the design system, chosen above. Use it to go back from any style, as Reset style does in Display.` };
}

// The Styles section (owner, 12 November 2026: "you need a default option which resets the style"): Starboard's own
// style first, in use whenever no plug-in style is, then each of the plug-in's styles.
function styleGallery(p) {
  const active = p.state === "enabled";
  const grid = el("ul", { class: "style-gallery" });
  let all = { teal: TEAL };
  const draw = () => {
    const OWN = ownLook(all);
    const current = readPrefs().style || "";
    const own = !current;
    const back = el("button", { type: "button", class: own ? "btn btn--primary" : "btn", "aria-pressed": String(own) },
      own ? "In use" : "Use this style", el("span", { class: "visually-hidden", text: `: ${OWN.name}` }));
    back.addEventListener("click", () => {
      if (own) return;
      resetStyle();  // the same as Reset style in Display, which says so
      draw();
      $(`[aria-pressed="true"]`, grid)?.focus();
    });
    const first = el("li", { class: "style-gallery__item" },
      el("div", { class: "style-gallery__pics" }, stylePicture(OWN, "light"), stylePicture(OWN, "dark")),
      el("h4", { text: OWN.name }), el("p", { class: "small", text: OWN.description }), back);
    grid.replaceChildren(first, ...p.looks.map((look) => {
      const chosen = current === look.value;
      const use = el("button", { type: "button", class: chosen ? "btn btn--primary" : "btn", "aria-pressed": String(chosen), disabled: !active },
        chosen ? "In use" : "Use this style", el("span", { class: "visually-hidden", text: `: ${look.name}` }));
      use.addEventListener("click", () => {
        const prefs = { ...readPrefs(), style: chosen ? "" : look.value };
        writePrefs(prefs); applyPrefs(prefs); draw();
        announce(chosen ? "Back to Starboard's own style" : `${look.name} style in use`);
        $(`[aria-pressed="true"]`, grid)?.focus();  // the redraw replaced the button
      });
      return el("li", { class: "style-gallery__item" },
        el("div", { class: "style-gallery__pics" }, stylePicture(look, "light"), stylePicture(look, "dark")),
        el("h4", { text: look.name }), el("p", { class: "small", text: look.description }), use);
    }));
  };
  draw();
  palettes().then((loaded) => { all = loaded; draw(); });
  // Reset style in Display changes it too; a redrawn page has a new gallery, so an old one stops listening.
  const onChange = () => (grid.isConnected ? draw() : document.removeEventListener("stylechange", onChange));
  document.addEventListener("stylechange", onChange);
  return el("div", { class: "stack-4" },
    el("p", { class: "small", text: active ? "Light on the left, dark on the right. Your choice applies to this browser, as in Display. High contrast always wins." : "Activate the plug-in to use its styles." }),
    ownColoursChoice("pl-own"), grid);
}

// A plug-in that stops (deactivated or removed) takes its style with it: this browser goes back to the own style and
// its colours (DASH-388), as Reset style does, rather than keeping a style that is no longer there.
function dropStyleOf(p) {
  if ((readPrefs().style || "").startsWith(`${p.id}.`)) resetStyle();
}

// Activate or Deactivate one plug-in.
function stateButton(p, redraw, primary = false) {
  if (stateOf(p) === "needs-setup") {  // set up first (DASH-330): Activate waits until the required settings are in
    return el("button", { type: "button", class: "btn btn--primary", onclick: () => {
      // The Settings part may be in a topic tab that is not showing: show it, then go to the first empty required field.
      const part = $(`#pl-${p.id}-settings-h`)?.closest("section.settings-section");
      if (part?.classList.contains("topic-off")) $(`#topic-tabs [aria-controls="${part.id}"]`)?.click();
      const fields = part ? $$("input, select, textarea", part).filter((f) => f.type !== "hidden") : [];
      const first = fields.find((f) => (p.status?.missing || []).some((m) => document.querySelector(`label[for="${f.id}"]`)?.textContent.startsWith(m))) || fields[0];
      first?.scrollIntoView({ block: "center" });
      first?.focus();
    } }, "Set it up", el("span", { class: "visually-hidden", text: ` ${p.name}` }));
  }
  const what = p.state === "enabled" ? "disable" : "enable";
  // Primary only on the plug-in's own page: in the Manage list every row would be primary (DASH-309).
  const b = el("button", { type: "button", class: what === "enable" && primary ? "btn btn--primary" : "btn" }, what === "enable" ? "Activate" : "Deactivate",
    el("span", { class: "visually-hidden", text: ` ${p.name}` }));
  b.addEventListener("click", async () => {
    b.disabled = true;
    try {
      await api(`/api/plugins/${p.id}/${what}`, { method: "POST" });
      if (what === "disable") dropStyleOf(p);
      announce(`${p.name} ${what === "enable" ? "activated" : "deactivated"}`); redraw();
    }
    catch (err) { problem(err.message, b); b.disabled = false; }
  });
  return b;
}

// Remove one plug-in, after the password. Its folder is kept.
function removeButton(p, after) {
  const remove = el("button", { type: "button", class: "btn btn--quiet btn--danger" }, `Remove ${p.name}`);
  remove.addEventListener("click", async () => {
    const pw = el("input", { class: "input", type: "password", id: `pl-rm-${p.id}`, autocomplete: "current-password" });
    const ok = await confirmDialog({ title: `Remove ${p.name}?`, danger: true, confirm: "Remove",
      message: "Its containers stop and go, and its API key stops working. Its folder is kept in data/plugins/.removed, for you to delete when you are sure.",
      fields: [el("div", { class: "field" }, el("label", { for: pw.id, text: "Your Starboard password" }), pw)] });
    if (!ok) return;
    try { await api(`/api/plugins/${p.id}/remove`, { method: "POST", body: { password: pw.value } }); dropStyleOf(p); toast(`${p.name} removed`); after(); }
    catch (err) { problem(err.message, remove); }
  });
  return remove;
}

// After an update or a roll back the page is drawn again: show the State topic and put focus on its heading, so the
// person hears the new version and state rather than losing their place.
function focusState(p) {
  // Two frames later: the topic tabs are drawn again in the next frame after the page changes.
  requestAnimationFrame(() => requestAnimationFrame(() => {
    const h = $(`#pl-${p.id}-state-h`);
    const part = h?.closest("section.settings-section");
    if (part?.classList.contains("topic-off")) $(`#topic-tabs [aria-controls="${part.id}"]`)?.click();
    if (h) { h.tabIndex = -1; h.focus(); }
  }));
}

// Update and Roll back (DASH-330): the update shows the same warning as installing, with what is new; both take the
// password. Roll back needs no download: the version before is kept.
function updateButton(p, redraw) {
  const b = el("button", { type: "button", class: "btn btn--primary" }, icon("download"), `Update to ${p.update.version}…`);
  b.addEventListener("click", async () => {
    b.disabled = true;
    try {
      const s = await api(`/api/plugins/${p.id}/update`, { method: "POST", body: { preview: true } });
      const password = await installWarning(s, { opener: b, verb: "Update" });
      if (password === null) return;
      const r = await api(`/api/plugins/${p.id}/update`, { method: "POST", body: { password } });
      announce(r.said);
      toast(r.said);
      await redraw();
      focusState(p);
    } catch (err) { problem(err.message, b); }
    finally { b.disabled = false; }
  });
  return b;
}

function rollbackButton(p, redraw, primary = false) {
  const b = el("button", { type: "button", class: primary ? "btn btn--primary" : "btn" }, icon("undo-2"), `Roll back to ${p.status.previous_version}`);
  b.addEventListener("click", async () => {
    const pw = el("input", { class: "input", type: "password", id: `pl-rb-${p.id}`, autocomplete: "current-password" });
    const ok = await confirmDialog({ title: `Roll back ${p.name} to ${p.status.previous_version}?`, confirm: "Roll back",
      message: `${p.name} goes back to the version you had before, with no download. Version ${p.version} is kept, in case you want it again.`,
      fields: [el("div", { class: "field" }, el("label", { for: pw.id, text: "Your Starboard password" }), pw)] });
    if (!ok) return;
    try {
      const r = await api(`/api/plugins/${p.id}/rollback`, { method: "POST", body: { password: pw.value } });
      announce(r.said);
      toast(r.said);
      await redraw();
      focusState(p);
    } catch (err) { problem(err.message, b); }
  });
  return b;
}

// Update from an address (DASH-357): for a plug-in that is not in a catalogue, such as one from its maker's own
// page. The same warning as installing, with what is new, then the password.
function updateFromAddress(p, redraw) {
  const address = el("input", { class: "input", id: `pl-${p.id}-update-address`, type: "url", placeholder: "https://", autocomplete: "off", spellcheck: "false" });
  const go = el("button", { type: "submit", class: "btn" }, "See what is new");
  const form = el("form", { class: "form-stack", novalidate: true, "aria-labelledby": `pl-${p.id}-update-h` },
    el("h3", { id: `pl-${p.id}-update-h`, text: "Update from an address" }),
    field("Address of the new version", address, { hint: "The https address of its starboard-plugin.json, from the plug-in's own page." }),
    el("div", { class: "actions" }, go));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    setError(address, "");
    const where = address.value.trim();
    if (!where) { setError(address, "Paste the address of the new version"); address.focus(); return; }
    let s;
    try { s = await api(`/api/plugins/${p.id}/update`, { method: "POST", body: { address: where, preview: true } }); }
    catch (err) { setError(address, err.message); address.focus(); return; }
    const password = await installWarning(s, { opener: go, verb: "Update" });
    if (password === null) return;
    try {
      const r = await api(`/api/plugins/${p.id}/update`, { method: "POST", body: { address: where, password } });
      announce(r.said);
      toast(r.said);
      await redraw();
      focusState(p);
    } catch (err) { problem(err.message, go); }
  });
  return form;
}

// What is new (DASH-393, owner, 13 November 2026: "when a plugin gets updated and you go onto its settings page - it
// needs a whats new added to the state page"). After an update, a Roll back or an update from an address, State shows
// the changes between the two versions from the plug-in's own changes (API 1.10): each type's first line, and All
// changes for the rest. Got it is kept on the server, so it is not shown again on any device; focus goes to State.
function whatsNew(p) {
  const w = p.whats_new;
  if (!w) return null;
  const older = w.kind === "older";
  const title = older ? `Back on ${w.to}` : `What is new in ${w.to}`;
  const lead = older ? `${p.name} went back from ${w.from}. ${w.versions.length ? "These changes are not in this version." : ""}`
    : w.from ? `Updated from ${w.from}.` : "";
  // Each type once, with its first line from the newest version that has it, and how many more there are.
  const types = [];
  for (const v of w.versions) for (const s of v.sections) {
    const t = types.find((x) => x.type === s.type);
    if (t) t.more += s.items.length; else types.push({ type: s.type, first: s.items[0], more: s.items.length - 1 });
  }
  const count = w.versions.reduce((n, v) => n + v.sections.reduce((m, s) => m + s.items.length, 0), 0);
  const all = count > types.length ? el("details", { class: "disclosure whats-new__all" },
    el("summary", { text: `All ${count} changes` }),
    el("div", { class: "disclosure__body" }, w.versions.map((v) => el("section", { class: "release-notes", "aria-label": `${p.name} ${v.version}` },
      el("h3", { text: `Version ${v.version}` }), v.date ? el("p", { class: "small muted", text: `Released ${v.date}` }) : null,
      ...v.sections.flatMap((s) => [el("h4", { text: s.type }), el("ul", {}, s.items.map((parts) => el("li", {}, ...changeParts(parts))))]))))) : null;
  const gotIt = el("button", { type: "button", class: "btn btn--quiet" }, "Got it", el("span", { class: "visually-hidden", text: `, hide ${title}` }));
  const box = el("div", { class: "notice whats-new", id: `pl-${p.id}-whats-new`, role: "status" }, icon(older ? "undo-2" : "circle-arrow-up"),
    el("div", { class: "notice__body" },
      el("span", { class: "notice__title", text: title }),
      lead.trim() ? el("p", { text: lead.trim() }) : null,
      types.length ? el("ul", { class: "whats-new__list" }, types.map((t) => el("li", {}, el("strong", { text: `${t.type}: ` }), ...changeParts(t.first),
        t.more ? el("span", { class: "muted", text: ` (and ${t.more} more)` }) : null)))
        : el("p", { text: w.note || "Its maker did not list what changed in this version." }),
      all,
      el("div", { class: "actions" }, gotIt)));
  gotIt.addEventListener("click", async () => {
    gotIt.disabled = true;
    try {
      await api(`/api/plugins/${p.id}/whats-new-seen`, { method: "POST" });
      p.whats_new = null;
      box.remove();
      focusState(p);
    } catch (err) { gotIt.disabled = false; problem(err.message, gotIt); }
  });
  return box;
}

// The words on a plug-in's State line: its version first, built into Starboard too (DASH-360, owner, 12 November 2026:
// "plugins need to show the version number in the state page in settings").
function stateWords(p) {
  const version = p.version ? `Version ${p.version}` : "Version not known";
  if (p.builtin) return `${version}, built into Starboard: it runs on Starboard's own image and updates with Starboard.`;
  return `${version}${p.author ? `, by ${p.author}` : ""}.`;
}

// A plug-in's own page, Settings, Plug-ins, <its name> (DASH-318), laid out like every Settings page (DASH-307):
// its state and its one button at the top, then versions, jobs, styles, settings by group and its screens, then
// its own buttons (Actions), what it may do, and Remove at the foot.
function pluginPage(p, redraw) {
  const said = el("p", { class: "small", role: "status" });  // what a button did, said here rather than in a toast
  const buttons = (p.actions || []).map((a) => {
    const b = el("button", { type: "button", class: "btn", disabled: p.state !== "enabled" }, a.label);
    b.addEventListener("click", async () => {
      b.disabled = true;
      said.textContent = "";
      try { said.textContent = (await api(`/api/plugins/${p.id}/actions/${a.id}`, { method: "POST" })).said; }
      catch (err) { problem(err.message, b); }
      finally { b.disabled = false; }
    });
    return b;
  });
  const custom = p.settings.filter((s) => s.type === "custom");
  const groups = pluginSettingsGroups(p, redraw);
  const st = p.status || {};
  // One sentence and one button for a state that needs something (DASH-330).
  const fix = st.sentence ? el("div", { class: "notice", "data-tone": st.state === "needs-setup" ? "info" : "warning", role: "note" },
    icon(st.state === "needs-setup" ? "info" : "triangle-alert"),
    el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: (STATE[st.state] || ["", ""])[0] }), el("p", { text: st.sentence }))) : null;
  const first = st.action === "rollback" ? rollbackButton(p, redraw, true)
    : st.action === "update" && p.update ? updateButton(p, redraw) : stateButton(p, redraw, true);
  // State (issue #8): the chip at the right of the heading's line, and Activate or Deactivate at the right of the
  // version line under it.
  const stateSec = section(`pl-${p.id}-state`, "State", stateWords(p),
    headChip(...chipOf(p)), fix || healthNote(p) || (p.message ? el("p", { class: "small", text: p.message }) : null));
  const about = $(".settings-section__head > p", stateSec);
  const stateLine = el("div", { class: "state-line" }, about || el("span"), el("div", { class: "actions" }, first));
  if (about) $(".settings-section__head", stateSec).append(stateLine); else stateSec.append(stateLine);
  const news = whatsNew(p);
  if (news) stateSec.append(news);
  return [
    stateSec,
    !p.builtin ? section(`pl-${p.id}-versions`, "Versions",
      p.update ? `Version ${p.update.version} is available.${p.update.changelog ? ` ${p.update.changelog}` : ""}`
        : st.can_roll_back ? `Version ${st.previous_version} is kept, in case this one does not suit you.` : `Version ${p.version}. No newer version is known.`,
      (p.update && st.action !== "update") || (st.can_roll_back && st.action !== "rollback")
        ? el("div", { class: "actions" }, p.update && st.action !== "update" ? updateButton(p, redraw) : null,
          st.can_roll_back && st.action !== "rollback" ? rollbackButton(p, redraw) : null) : null,
      updateFromAddress(p, redraw)) : null,
    p.jobs?.length ? section(`pl-${p.id}-jobs`, "Jobs", "Starboard runs these for it, and lists them in System with when each last ran.",
      el("ul", {}, p.jobs.map((j) => el("li", { text: j }))), el("a", { class: "btn btn--quiet", href: "/system.html#jobs-panel" }, "Open System, Jobs")) : null,
    p.looks?.length ? section(`pl-${p.id}-styles`, "Styles", "Colours for Starboard from this plug-in. Choose one for this browser, as in Display.", styleGallery(p)) : null,
    ...groups.map((g) => section(g.id, g.group || "Settings", "Saved for everyone who uses this Starboard.", g.body)),
    ...custom.map((c) => section(`pl-${p.id}-${c.key}`, c.label, c.hint || "", customScreen(p, c))),
    buttons.length ? section(`pl-${p.id}-actions`, "Actions", p.state === "enabled" ? "Things it can do now, as well as on its own schedule." : "Activate it to use these.",
      el("div", { class: "actions" }, ...buttons), said) : null,
    section(`pl-${p.id}-may`, "What it may do", "What you allowed when you installed it.", pluginPermissions(p.permissions)),
    dangerSection(`pl-${p.id}-remove`, "Remove", "Stops it and takes it off this Starboard. Its folder is kept.",
      el("div", { class: "actions" }, removeButton(p, () => { location.href = "/settings-plugins.html"; })))].filter(Boolean);
}

// A plug-in's own screen (11 November 2026): a managed list the plug-in describes as data, drawn here. Rows grouped
// with a state, Test, Activate or Deactivate, Move and Remove; Add takes an address; Test all checks everything.
const CUSTOM_STATE = { ok: ["Works", "success"], warning: ["Slow", "warning"], problem: ["Not answering", "danger"],
  off: ["Inactive", "muted"], unknown: ["Not tested", "muted"] };
function customScreen(p, s) {
  const box = el("div", { class: "stack-4" }, el("p", { class: "muted", text: "Loading…" }));
  const said = el("p", { class: "small", role: "status" });
  const path = `/api/plugins/${p.id}/custom/${s.key}`;
  // `after`: a bulk switch says what it did in a saved note beside itself (Settings pattern 2), not in the line above.
  const run = async (body, button, after) => {
    if (button) button.disabled = true;
    if (last && body.action !== "dismiss") freeze();
    const key = button && button.dataset.key;  // a row's button: focus goes back to it, drawn again (WCAG 2.4.3)
    try {
      const out = await api(path, { method: "POST", body });
      if (out.said && !after) said.textContent = out.said;
      draw(out);
      if (key) [...box.querySelectorAll("[data-key]")].find((x) => x.dataset.key === key)?.focus();
      if (after) after(out);
    }
    catch (err) { if (button && button.type === "checkbox") button.checked = !button.checked; problem(err.message, button); }
    finally { if (button) button.disabled = false; }
  };
  // Bulk switches (DASH-359): each set the plug-in names (Live TV: each whole list, every channel, regions, sections).
  // A switch is active when every item in it is, or as the plug-in says; changing it applies at once. `sets` are the
  // switches of the level that is open (plug-in API 1.7).
  const bulkPanel = (data, sets) => {
    if (!sets.length) return null;
    const noun = (data.title || "items").toLowerCase();
    const kinds = new Map();
    for (const b of sets) { if (!kinds.has(b.kind)) kinds.set(b.kind, []); kinds.get(b.kind).push(b); }
    const slug = (t) => t.toLowerCase().replace(/[^a-z0-9]+/g, "-");
    const head = `bulk-${p.id}-${s.key}`;
    const row = (b) => {
      const id = `${head}-${slug(b.id)}`;
      const input = el("input", { type: "checkbox", role: "switch", id, checked: typeof b.active === "boolean" ? b.active : b.total > 0 && b.on === b.total,
        "aria-labelledby": `${id}-l`, "aria-describedby": `${id}-h`, "data-key": `bulk:${b.id}` });  // focus comes back to it, drawn again
      const note = el("span", { class: "saved-note", id: `${id}-saved`, hidden: true });
      input.addEventListener("change", () => run({ action: "bulk", id: b.id, value: input.checked ? "on" : "off" }, input, (out) => {
        const again = document.getElementById(`${id}-saved`);
        if (again && out.said) window.SharedComponents.savedNote(again, out.said);
      }));
      return el("li", { class: "setting" },
        el("div", { class: "setting__text" }, el("span", { class: "setting__label", id: `${id}-l`, text: b.label }),
          el("span", { class: "setting__hint", id: `${id}-h`, text: b.hint || `${b.on} of ${b.total} active` })),
        el("div", { class: "setting__control" }, el("label", { class: "switch" }, input), note));
    };
    return el("section", { class: "stack-2", "aria-labelledby": `${head}-h` },
      el("h4", { id: `${head}-h`, text: "Activate or deactivate in bulk" }),
      at ? null : el("p", { class: "small muted", text: `Each switch applies at once. A group of ${noun} shows as active when all of them are.` }),
      ...[...kinds].map(([k, list]) => el("div", { class: "stack-2" }, k ? el("h5", { text: k }) : null,
        el("ul", { class: "settings-rows" }, list.map(row)))));
  };
  const ACTION_WORDS = { test: ["Test", "activity"], toggle: [null, null], remove: ["Remove", "trash-2"], up: ["Move up", "arrow-up"], down: ["Move down", "arrow-down"],
    detach: ["Remove guide", "x"] };
  // Show all, active or inactive items (owner, 12 November 2026: "a filter to the channel list for active and not
  // active channels"), on any list whose rows can be activated; kept while the list is drawn again. `pool` is every
  // item in the open level and the sub menus under it.
  let show = "all";
  let last = null;
  const showFilter = (data, pool) => {
    if (!pool.some((it) => it.actions.includes("toggle"))) return null;
    const noun = (data.title || "items").toLowerCase();
    const count = { all: pool.length, on: pool.filter((it) => it.on).length };
    count.off = count.all - count.on;
    return el("fieldset", { class: "segmented" }, el("legend", { class: "visually-hidden", text: `Show ${noun}` }),
      [["all", "All"], ["on", "Active"], ["off", "Inactive"]].map(([value, label]) => {
        const input = el("input", { type: "radio", name: `show-${p.id}-${s.key}`, id: `show-${p.id}-${s.key}-${value}`, value, checked: value === show });
        input.addEventListener("change", () => {
          show = value;
          stay.clear();
          draw(last);
          document.getElementById(input.id)?.focus();
          announce(`${count[value]} ${noun} shown`);
        });
        return el("label", { for: input.id }, input, el("span", { text: `${label} (${count[value]})` }));
      }));
  };
  // Sub menus (plug-in API 1.7, DASH-361, owner, 12 November 2026: "simplify the channels with sub menus"): the
  // first level lists the menus as rows that open (Settings pattern 8, in place of a slide-out); an opened menu has a
  // back link above its heading (issue #15), its own switches, sub menus and items. Focus goes to the opened menu's
  // heading, and back to its row on return. `at` is the open menu, "" for the first level.
  let at = "";
  const levelHead = `level-${p.id}-${s.key}-h`;
  const go = (id, back) => {
    const from = at;
    at = id;
    draw(last);  // drawn at once, so focus moves now
    (back ? [...box.querySelectorAll("[data-menu]")].find((x) => x.dataset.menu === from) : document.getElementById(levelHead))?.focus();
  };
  // While a filter is on, a change does not move anything (owner, 13 November 2026: "not refresh the page unless I
  // leave it and go back when a filter is active ... I want to do multiple changes at once quickly"): what was shown
  // stays shown, with its new state, until Refresh, a change of filter, or leaving the page.
  const stay = new Set();
  const keep = (it) => stay.has(it.id) || show === "all" || (show === "on" ? it.on : !it.on);
  const itemRows = (data, shown) => {
    const groups = new Map();
    for (const it of shown) { if (!groups.has(it.group)) groups.set(it.group, []); groups.get(it.group).push(it); }
    return [...groups].map(([g, rows]) => el("section", { class: "stack-2", "aria-label": g || data.title },
      g ? el("h4", { text: g }) : null,
      el("ul", { class: "rows" }, rows.flatMap((it) => [el("li", { class: "row row--no-lead" },
        el("div", {}, el("h5", { class: "row__title", text: it.title }),
          el("div", { class: "row__meta", text: [it.detail, it.address].filter(Boolean).join(" · ") })),
        el("div", { class: "row__side" }, chip(...(CUSTOM_STATE[it.state] || CUSTOM_STATE.unknown)),
          it.choice ? (() => {  // a small choice on the row, such as a catalogue's weight (12 November 2026)
            const sel = el("select", { class: "select select--compact", "aria-label": `${it.choice.label}: ${it.title}`, "data-key": `${it.id}:choose` },
              it.choice.options.map(([v, words]) => el("option", { value: v, text: words, selected: v === it.choice.value })));
            sel.addEventListener("change", () => run({ action: "choose", id: it.id, value: sel.value }, sel));
            return el("label", { class: "row-choice" }, el("span", { class: "small", text: it.choice.label }), sel);
          })() : null,
          // Test and Activate or Deactivate as buttons; Move up, Move down and Remove in a More menu, so a row has
          // at most two buttons after its state (DASH-309, section 10).
          it.attach && it.actions.includes("attach") ? attachButton(it) : null,
          ...it.actions.filter((a) => a === "test" || a === "toggle").map((a) => {
            const [label, ic] = a === "toggle" ? [it.on ? "Deactivate" : "Activate", it.on ? "pause" : "play"] : ACTION_WORDS[a];
            const b = el("button", { type: "button", class: "btn btn--quiet btn--compact", "data-key": `${it.id}:${a}` }, ic ? icon(ic) : null, label,
              el("span", { class: "visually-hidden", text: ` ${it.title}` }));
            b.addEventListener("click", () => run({ action: a, id: it.id }, b));
            return b;
          }),
          (() => {
            const more = it.actions.filter((a) => a !== "test" && a !== "toggle" && a !== "attach");
            if (!more.length) return null;
            let menu = null;
            menu = menuButton(`More for ${it.title}`, more.map((a) => ({ label: ACTION_WORDS[a][0], icon: ACTION_WORDS[a][1], danger: a === "remove",
              onSelect: async () => {
                const opener = menu.querySelector("button");
                if (a === "remove" && !(await confirmDialog({ title: `Remove ${it.title}?`, confirm: "Remove", danger: true, message: "You can add it again by its address." }))) return;
                run({ action: a, id: it.id }, opener);
              } })));
            return menu;
          })())), it.attach && opened.has(it.id) ? attachForm(it) : null].filter(Boolean)))));
  };
  // Something added to one item (plug-in API 1.8), such as a guide for a channel list (owner, 13 November 2026): the
  // button opens a small form under the row, an address or a file, and focus goes into it.
  const opened = new Set();
  const attachButton = (it) => {
    const b = el("button", { type: "button", class: "btn btn--quiet btn--compact", "data-key": `${it.id}:attach`, "aria-expanded": String(opened.has(it.id)),
      "aria-controls": `attach-${p.id}-${s.key}-${it.id}` }, icon("calendar-clock"), it.attach.label, el("span", { class: "visually-hidden", text: ` for ${it.title}` }));
    b.addEventListener("click", () => {
      if (opened.has(it.id)) opened.delete(it.id); else opened.add(it.id);
      draw(last);
      (opened.has(it.id) ? document.getElementById(`attach-${p.id}-${s.key}-${it.id}-url`) : [...box.querySelectorAll("[data-key]")].find((x) => x.dataset.key === `${it.id}:attach`))?.focus();
    });
    return b;
  };
  const attachForm = (it) => {
    const a = it.attach;
    const base = `attach-${p.id}-${s.key}-${it.id}`;
    const url = el("input", { class: "input", id: `${base}-url`, type: "url", value: a.value || "", placeholder: a.placeholder || "", autocomplete: "off",
      ...(a.hint ? { "aria-describedby": `${base}-h` } : {}) });
    const save = el("button", { type: "submit", class: "btn btn--primary" }, icon("plus"), a.label);
    const form = el("form", { class: "stack-2" }, el("div", { class: "actions" }, url, save));
    form.addEventListener("submit", (e) => { e.preventDefault(); if (url.value.trim()) { opened.delete(it.id); run({ action: "attach", id: it.id, value: url.value.trim() }, save); } });
    const file = el("input", { class: "input", type: "file", accept: a.accept || "", "aria-label": `Or choose a file: ${a.field}` });
    const send = el("button", { type: "submit", class: "btn" }, icon("upload"), "Upload");
    const fileForm = el("form", { class: "actions" }, file, send);
    fileForm.addEventListener("submit", (e) => { e.preventDefault(); upload(file, send, it.id, () => opened.delete(it.id)); });
    return el("li", { class: "attach-form", id: base, role: "group", "aria-labelledby": `${base}-l` },
      el("label", { class: "field__label", id: `${base}-l`, for: url.id, text: a.field }),
      a.hint ? el("p", { class: "hint", id: `${base}-h`, text: a.hint }) : null, form, fileForm);
  };
  // A chosen file, streamed to the plug-in as it is (DASH-359); `item`: a file for one item, such as its guide.
  const upload = async (file, send, item, done) => {
    const chosen = file.files[0];
    if (!chosen) { problem("Choose a file first", file); return; }
    send.disabled = true;
    loading.start();
    try {
      const res = await fetch(`${path}/file?name=${encodeURIComponent(chosen.name)}${item ? `&id=${encodeURIComponent(item)}` : ""}`,
        { method: "POST", headers: { "X-Starboard": "1", Accept: "application/json" }, credentials: "same-origin", body: chosen });
      let out = {};
      try { out = await res.json(); } catch { /* empty */ }
      if (!res.ok) throw new Error(out.error || `Something went wrong (error ${res.status})`);
      if (done) done();
      if (out.said) said.textContent = out.said;
      draw(out);
      (item ? [...box.querySelectorAll("[data-key]")].find((x) => x.dataset.key === `${item}:attach`) : document.getElementById(file.id))?.focus();
    } catch (err) { problem(err.message, send); }
    finally { send.disabled = false; loading.stop(); }
  };
  // Notices at the top (plug-in API 1.8), such as a list being added: "4 of 13 channels tested", then what came of
  // it, until closed. While one is in progress the screen asks again every 3 seconds.
  let poll = null;
  const noticesOf = (data) => {
    clearTimeout(poll);
    const list = data.notices || [];
    if (list.some((n) => n.progress !== null && n.progress !== undefined)) {
      poll = setTimeout(() => { if (box.isConnected) api(path).then(draw).catch(() => {}); }, 3000);
    }
    return list.map((n) => {
      const close = n.dismiss ? el("button", { type: "button", class: "btn btn--quiet btn--compact", "data-key": `notice:${n.id}` }, "Close",
        el("span", { class: "visually-hidden", text: `: ${n.title}` })) : null;
      close?.addEventListener("click", () => run({ action: "dismiss", id: n.id }, close));
      const bar = n.progress !== null && n.progress !== undefined
        ? el("div", { class: "progress", "data-tone": "warning", role: "progressbar", "aria-valuenow": String(n.progress), "aria-valuemin": "0", "aria-valuemax": "100",
          "aria-label": n.title }, el("span")) : null;
      if (bar) bar.firstChild.style.width = `${n.progress}%`;  // set in script: the page's policy blocks style attributes
      const node = notice(n.tone, n.title, n.text, close);
      if (bar) {
        node.querySelector(".notice__body")?.append(bar);  // under its words, the width of the notice
        node.removeAttribute("role");  // asked again every 3 seconds: not read out each time
      }
      return node;
    });
  };
  // The rows that open the sub menus of one level, grouped by the plug-in's group, each with its state and count.
  const menuRows = (data, kids, under) => {
    const noun = (data.title || "items").toLowerCase();
    const groups = new Map();
    for (const m of kids) { if (!groups.has(m.group)) groups.set(m.group, []); groups.get(m.group).push(m); }
    return [...groups].map(([g, list]) => el("section", { class: "stack-2", "aria-label": g || data.title },
      g ? el("h4", { text: g }) : null,
      el("ul", { class: "rows" }, list.map((m) => {
        const its = under.get(m.id) || [];
        const can = its.filter((it) => it.actions.includes("toggle"));
        const on = can.filter((it) => it.on).length;
        const state = m.active === false ? ["Inactive", "muted"] : !can.length ? null
          : on === can.length ? ["Active", "success"] : on ? ["Partly active", "info"] : ["Inactive", "muted"];
        const open = el("button", { type: "button", "data-menu": m.id }, m.title);
        open.addEventListener("click", () => go(m.id, false));
        return el("li", { class: "row row--no-lead row--opens" },
          el("div", {}, el("h5", { class: "row__title" }, open),
            el("div", { class: "row__meta", text: [m.detail, can.length ? `${on} of ${can.length} active` : its.length ? `${its.length} ${noun}` : ""].filter(Boolean).join(" · ") })),
          el("div", { class: "row__side" }, state ? chip(...state) : null, icon("chevron-right")));
      }))));
  };
  const draw = (data) => {
    last = data;
    if (data.layout === "folds") { drawFolds(data); return; }
    const menus = data.menus || [];
    const byId = new Map(menus.map((m) => [m.id, m]));
    if (!byId.has(at)) at = "";
    // Every item under each menu, its sub menus' too, for the counts on its row and the filter.
    const under = new Map(menus.map((m) => [m.id, []]));
    for (const it of data.items) {
      for (let m = byId.get(it.menu || ""); m; m = byId.get(m.parent)) under.get(m.id).push(it);
    }
    const pool = at ? under.get(at) : data.items;
    const kids = menus.filter((m) => m.parent === at && (show === "all" || (under.get(m.id) || []).some(keep)));
    const shown = data.items.filter((it) => (it.menu || "") === at && keep(it));
    const sets = (data.bulk || []).filter((b) => (b.menu || "") === at);
    const here = byId.get(at);
    const add = !here && data.add ? (() => {
      const id = `add-${p.id}-${s.key}`;
      const input = el("input", { class: "input", id, type: "url", placeholder: data.add.placeholder || "", autocomplete: "off" });
      const addBtn = el("button", { type: "submit", class: "btn btn--primary" }, icon("plus"), data.add.label || "Add");
      const form = el("form", { class: "stack-2" }, el("label", { class: "field__label", for: id, text: data.add.label || "Add" }),
        data.add.hint ? el("p", { class: "hint", text: data.add.hint }) : null, el("div", { class: "actions" }, input, addBtn));
      form.addEventListener("submit", (e) => { e.preventDefault(); if (input.value.trim()) run({ action: "add", value: input.value.trim() }, addBtn); });
      // A file instead of an address (DASH-359): streamed to the plug-in as it is, never read into the page.
      const f = data.add.file;
      if (!f) return form;
      const fileId = `${id}-file`;
      const file = el("input", { class: "input", id: fileId, type: "file", accept: f.accept || "", ...(f.hint ? { "aria-describedby": `${fileId}-h` } : {}) });
      const send = el("button", { type: "submit", class: "btn" }, icon("upload"), "Upload");
      const fileForm = el("form", { class: "stack-2" }, el("label", { class: "field__label", for: fileId, text: f.label }),
        f.hint ? el("p", { class: "hint", id: `${fileId}-h`, text: f.hint }) : null, el("div", { class: "actions" }, file, send));
      fileForm.addEventListener("submit", (e) => { e.preventDefault(); upload(file, send, ""); });
      return el("div", { class: "stack-4" }, form, fileForm);
    })() : null;
    // Test all only where it can test something: a list with rows to test, or one still empty.
    const testAll = !here && (!data.items.length || data.items.some((it) => it.actions.includes("test")))
      ? el("button", { type: "button", class: "btn" }, icon("activity"), "Test all") : null;
    testAll?.addEventListener("click", () => run({ action: "test_all" }, testAll));
    // An opened menu: the back link above its heading, named for where it goes.
    const top = here ? (() => {
      const parent = byId.get(here.parent);
      const back = el("button", { type: "button", class: "back-link back-link--button" }, icon("arrow-left"), `Back to ${parent ? parent.title : data.title || "the list"}`);
      back.addEventListener("click", () => go(here.parent, true));
      const trail = [];  // where it is, such as "In Samsung TV Plus, UK", under its heading
      for (let m = parent; m; m = byId.get(m.parent)) trail.unshift(m.title);
      return [back, el("h3", { id: levelHead, tabindex: "-1", text: here.title }),
        trail.length ? el("p", { class: "small muted", text: `In ${trail.join(", ")}` }) : null,
        here.detail ? el("p", { class: "small muted", text: here.detail }) : null];
    })() : [data.intro ? el("p", { class: "small muted", text: data.intro }) : null];
    const controls = [showFilter(data, pool), testAll, stay.size ? refreshButton() : null].filter(Boolean);
    box.replaceChildren(...[
      ...(here ? [] : noticesOf(data)), ...top, bulkPanel(data, sets),
      controls.length ? el("div", { class: "actions" }, ...controls) : null, said,
      pool.length && !shown.length && !kids.length ? emptyState(show === "on" ? "None active" : "None inactive", "Choose All to see every one.")
        : here && !pool.length && !kids.length ? emptyState(`No ${(data.title || "items").toLowerCase()} here`, null) : null,
      ...menuRows(data, kids, under), ...itemRows(data, shown), add].filter(Boolean));  // replaceChildren writes null as text
  };
  // Sections that fold, each with a table to sort and select from (plug-in API 1.8, DASH-359, owner 13 November
  // 2026: "Build option 1 with 2 in the accordions"). A section is one line until opened: its name, how many are
  // active and its own switch. Search, Show and the filter chips narrow every section at once; ticked items from any
  // section can be activated or deactivated together. Only open sections draw their rows.
  const fold = { open: new Set(), sort: { key: "", dir: 1 }, picked: new Set(), query: "", chips: new Map() };
  const foldBase = `fold-${p.id}-${s.key}`;
  const foldMatch = (it) => {
    if (stay.has(it.id)) return true;
    const q = fold.query.trim().toLowerCase();
    return keep(it) && (!q || [it.title, ...Object.values(it.cells || {})].some((v) => String(v).toLowerCase().includes(q)))
      && [...fold.chips].every(([k, set]) => !set.size || set.has((it.cells || {})[k]));
  };
  const filtering = () => show !== "all" || fold.query.trim() !== "" || [...fold.chips.values()].some((x) => x.size);
  function freeze() {  // everything shown now stays shown after the change
    if (!filtering()) return;
    for (const it of last.items) if ((last.layout === "folds" ? foldMatch : keep)(it)) stay.add(it.id);
  }
  const refresh = (button) => {
    stay.clear();
    button.disabled = true;
    api(path).then((out) => {
      draw(out);
      document.getElementById(button.id)?.focus();
      announce(`Refreshed: ${out.items.filter(out.layout === "folds" ? foldMatch : keep).length} ${(out.title || "items").toLowerCase()} shown`);
    }).catch((err) => problem(err.message, button)).finally(() => { button.disabled = false; });
  };
  const refreshButton = () => {
    const b = el("button", { type: "button", class: "btn", id: `${foldBase}-refresh` }, icon("refresh-cw"), "Refresh",
      stay.size ? el("span", { class: "visually-hidden", text: ": changed ones stay in view until you refresh" }) : null);
    b.addEventListener("click", () => refresh(b));
    return b;
  };
  const drawFolds = (data) => {
    const noun = (data.title || "items").toLowerCase();
    const cols = data.columns || [];
    const ro = data.readonly === true;  // API 1.11 (DASH-402): figures to read, so no ticks, states or buttons
    const match = foldMatch;
    const known = new Set(data.items.map((it) => it.id));
    for (const id of [...fold.picked]) if (!known.has(id)) fold.picked.delete(id);
    const groups = new Map();
    for (const it of data.items) { if (!groups.has(it.group)) groups.set(it.group, []); groups.get(it.group).push(it); }
    const sorted = (rows) => {
      const { key, dir } = fold.sort;
      if (!key) return rows;
      const num = cols.find((c) => c.key === key)?.type === "number";
      return [...rows].sort((a, b) => {
        const x = (a.cells || {})[key] || "", y = (b.cells || {})[key] || "";
        return dir * (num ? Number(x) - Number(y) : x.localeCompare(y, "en-GB"));
      });
    };
    // Search, Show and the chips
    const search = el("input", { class: "input", type: "search", id: `${foldBase}-q`, value: fold.query, placeholder: "Search by name or number", autocomplete: "off" });
    let timer = null;
    search.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        fold.query = search.value;
        stay.clear();
        const at = search.selectionStart;
        drawFolds(data);
        const again = document.getElementById(`${foldBase}-q`);
        again?.focus();
        again?.setSelectionRange(at, at);
        announce(`${data.items.filter(match).length} ${noun} found`);
      }, 250);
    });
    const chipRows = (data.filters || []).map((f) => {
      const values = [...new Set(data.items.map((it) => (it.cells || {})[f.key]).filter(Boolean))];
      const set = fold.chips.get(f.key) || new Set();
      fold.chips.set(f.key, set);
      return el("div", { class: "filter-chips", role: "group", "aria-label": f.label }, el("span", { class: "small muted", text: `${f.label}:` }),
        values.map((v) => {
          const b = el("button", { type: "button", class: "filter-chip", "aria-pressed": String(set.has(v)), id: `${foldBase}-chip-${f.key}-${v.replace(/[^A-Za-z0-9]+/g, "-")}` }, v);
          b.addEventListener("click", () => {
            if (set.has(v)) set.delete(v); else set.add(v);
            stay.clear();
            drawFolds(data);
            document.getElementById(b.id)?.focus();
            announce(`${data.items.filter(match).length} ${noun} shown`);
          });
          return b;
        }));
    });
    // What is ticked, from any section
    const pickedBar = fold.picked.size ? (() => {
      const act = (value, label, ic) => {
        const b = el("button", { type: "button", class: "btn btn--compact", "data-key": `picked:${value}` }, icon(ic), label);
        b.addEventListener("click", () => run({ action: "bulk_ids", ids: [...fold.picked], value }, b).then(() => {
          fold.picked.clear();
          drawFolds(last);
          document.getElementById(`${foldBase}-q`)?.focus();  // the bar has gone: focus to the search, above where it was
        }));
        return b;
      };
      const clear = el("button", { type: "button", class: "btn btn--quiet btn--compact" }, "Clear");
      clear.addEventListener("click", () => { fold.picked.clear(); drawFolds(data); document.getElementById(`${foldBase}-q`)?.focus(); announce("Nothing ticked"); });
      return el("div", { class: "picked-bar", role: "group", "aria-label": `Ticked ${noun}` },
        el("strong", { text: `${fold.picked.size} ticked` }), act("on", "Activate", "play"), act("off", "Deactivate", "pause"), clear);
    })() : null;
    const switchFor = (g) => (data.bulk || []).find((b) => b.fold === g);
    const sections = [...groups].map(([g, rows]) => {
      const shown = rows.filter(match);
      if (!shown.length && (q || show !== "all" || [...fold.chips.values()].some((x) => x.size))) return null;
      const slug = String(g || "other").toLowerCase().replace(/[^a-z0-9]+/g, "-");
      const panelId = `${foldBase}-${slug}`;
      const open = fold.open.has(g);
      const on = rows.filter((it) => it.on).length;
      const toggle = el("button", { type: "button", class: "fold__toggle", "aria-expanded": String(open), "aria-controls": panelId, id: `${panelId}-b` },
        el("span", { class: "fold__name", text: g || "Other" }),
        el("span", { class: "small muted", text: ro ? `${rows.length} ${rows.length === 1 ? "row" : "rows"}${shown.length !== rows.length ? `, ${shown.length} shown` : ""}`
          : `${on} of ${rows.length} active${shown.length !== rows.length ? `, ${shown.length} shown` : ""}` }),
        icon(open ? "chevron-down" : "chevron-right"));
      toggle.addEventListener("click", () => { if (open) fold.open.delete(g); else fold.open.add(g); drawFolds(data); document.getElementById(`${panelId}-b`)?.focus(); });
      const b = switchFor(g);
      const sw = b ? (() => {
        const id = `${panelId}-switch`;
        const input = el("input", { type: "checkbox", role: "switch", id, checked: b.total > 0 && b.on === b.total, "aria-label": `Every channel in ${g}`, "data-key": `bulk:${b.id}` });
        const note = el("span", { class: "saved-note", id: `${id}-saved`, hidden: true });
        input.addEventListener("change", () => run({ action: "bulk", id: b.id, value: input.checked ? "on" : "off" }, input, (out) => {
          const again = document.getElementById(`${id}-saved`);
          if (again && out.said) window.SharedComponents.savedNote(again, out.said);
        }));
        return el("div", { class: "fold__switch" }, note, el("label", { class: "switch" }, input));
      })() : null;
      const head = el("div", { class: "fold__head" }, el("h4", { class: "fold__title" }, toggle), sw);
      if (!open) return el("section", { class: "fold" }, head);
      const all = el("input", { type: "checkbox", "aria-label": `Tick every ${noun.replace(/s$/, "")} shown in ${g}`,
        checked: shown.length > 0 && shown.every((it) => fold.picked.has(it.id)) });
      all.addEventListener("change", () => { for (const it of shown) { if (all.checked) fold.picked.add(it.id); else fold.picked.delete(it.id); } drawFolds(data); });
      const th = (c) => {
        const sortedBy = fold.sort.key === c.key;
        const sb = el("button", { type: "button", class: "sort-btn", id: `${panelId}-sort-${c.key}` }, c.label,
          sortedBy ? icon(fold.sort.dir > 0 ? "arrow-up" : "arrow-down") : null);
        sb.addEventListener("click", () => {
          fold.sort = { key: c.key, dir: sortedBy ? -fold.sort.dir : 1 };
          drawFolds(data);
          document.getElementById(sb.id)?.focus();
        });
        return el("th", { scope: "col", "aria-sort": sortedBy ? (fold.sort.dir > 0 ? "ascending" : "descending") : "none" }, sb);
      };
      const table = el("table", { class: "table table--middle" },
        el("caption", { class: "visually-hidden", text: `${g}: ${noun}` }),
        el("thead", {}, el("tr", {}, ro ? null : el("th", { scope: "col" }, all), ...cols.map(th), ro ? null : el("th", { scope: "col", text: "State" }),
          ro ? null : el("th", { scope: "col" }, el("span", { class: "visually-hidden", text: "Activate or deactivate" })))),
        el("tbody", {}, sorted(shown).map((it) => {
          if (ro) return el("tr", {}, ...cols.map((c, i) => el(i === 0 ? "th" : "td", { ...(i === 0 ? { scope: "row" } : {}), class: c.type === "number" ? "num" : null, text: (it.cells || {})[c.key] || "" })));
          const tick = el("input", { type: "checkbox", "aria-label": `Tick ${it.title}`, checked: fold.picked.has(it.id), "data-key": `${it.id}:pick` });
          tick.addEventListener("change", () => { if (tick.checked) fold.picked.add(it.id); else fold.picked.delete(it.id); drawFolds(data);
            [...box.querySelectorAll("[data-key]")].find((x) => x.dataset.key === `${it.id}:pick`)?.focus(); });
          const btn = it.actions.includes("toggle") ? el("button", { type: "button", class: "btn btn--quiet btn--compact", "data-key": `${it.id}:toggle` },
            icon(it.on ? "pause" : "play"), it.on ? "Deactivate" : "Activate", el("span", { class: "visually-hidden", text: ` ${it.title}` })) : null;
          btn?.addEventListener("click", () => run({ action: "toggle", id: it.id }, btn));
          return el("tr", { class: it.on ? null : "is-off" }, el("td", {}, tick), ...cols.map((c) => el("td", { class: c.type === "number" ? "num" : null, text: (it.cells || {})[c.key] || "" })),
            el("td", {}, chip(...(CUSTOM_STATE[it.state] || CUSTOM_STATE.unknown))), el("td", {}, btn));
        })));
      return el("section", { class: "fold" }, head, el("div", { id: panelId, class: "fold__panel" }, shown.length ? el("div", { class: "table-wrap" }, table)
        : emptyState("None here", "Change the search or filters to see more.")));
    }).filter(Boolean);
    const sets = (data.bulk || []).filter((b) => !b.fold);
    box.replaceChildren(...[
      ...noticesOf(data),
      data.intro ? el("p", { class: "small muted", text: data.intro }) : null, bulkPanel(data, sets),
      el("div", { class: "fold-tools" }, el("label", { class: "visually-hidden", for: search.id, text: `Search ${noun}` }), el("div", { class: "search-field" }, search),
        showFilter(data, data.items), refreshButton()),
      stay.size ? el("p", { class: "small muted", text: `Changed ${noun} stay in view while the filter is on. Select Refresh to show only those that match it now.` }) : null,
      ...chipRows, pickedBar, said,
      sections.length ? el("div", { class: "folds" }, ...sections) : emptyState(`No ${noun} found`, "Change the search or filters to see more.")].filter(Boolean));
  };
  if (p.state !== "enabled") box.replaceChildren(emptyState(`${p.name} is not active`, `Activate it on State to see ${s.label.toLowerCase()}.`));
  else api(path).then(draw).catch((err) => box.replaceChildren(notice("info", `${p.name} did not answer`, err.message)));
  return box;
}

// Test a plug-in (DASH-284): for authors, before sharing it. Nothing is added.
function testerSection() {
  const file = el("input", { type: "file", id: "pl-test-file", accept: ".json,application/json", class: "input" });
  const dev = el("input", { type: "checkbox", id: "pl-test-dev" });
  const out = el("div", { "aria-live": "polite" });
  const form = el("form", { class: "form-stack", novalidate: true },
    field("Manifest file to test", file, { hint: "starboard-plugin.json. Accessibility is always tested." }),
    el("label", { class: "check", for: dev.id }, dev, el("span", { text: "Allow images without a digest (testing only: adding a plug-in always needs one)" })),
    el("div", { class: "actions" }, el("button", { type: "submit", class: "btn", text: "Test it" })));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    setError(file, "");
    if (!file.files[0]) { setError(file, "Choose the manifest file"); file.focus(); return; }
    try { out.replaceChildren(testReport(await api("/api/plugins/test", { method: "POST", body: { manifest: await file.files[0].text(), dev: dev.checked } }))); }
    catch (err) { setError(file, err.message); file.focus(); }
  });
  return section("pl-test", "Test a plug-in", "For people who make plug-ins: every issue with how to fix it. The same tests run before any plug-in is added.", form, out);
}

// Plug-ins that ship inside Starboard, such as Live TV (DASH-285): Add asks for the password and activates it.
function builtinSection(list, redraw) {
  const rows = list.filter((b) => !b.added);
  if (!rows.length) return null;
  return section("pl-builtin", "Built into Starboard", "Plug-ins that come with Starboard. Add one only if you want it.",
    el("ul", { class: "rows" }, rows.map((b) => {
      const add = el("button", { type: "button", class: "btn", disabled: !!b.why_not }, `Add ${b.name}`);
      add.addEventListener("click", async () => {
        const password = await installWarning(b, { builtin: true, opener: add });
        if (password === null) return;
        try { await api("/api/plugins/add-builtin", { method: "POST", body: { id: b.id, password } }); announce(`${b.name} installed and active`); redraw(); }
        catch (err) { problem(err.message, add); }
      });
      return el("li", { class: "row row--no-lead" }, el("div", {}, el("div", { class: "row__title", text: b.name }),
        el("div", { class: "row__meta", text: b.why_not ? `${b.description} Not here: ${b.why_not}.` : b.description })),
        el("div", { class: "row__side" }, add));
    })));
}

function addPluginSection(redraw) {
  const address = el("input", { class: "input", id: "pl-address", type: "url", placeholder: "https://", autocomplete: "off", spellcheck: "false" });
  const seen = el("div", { class: "stack-4", "aria-live": "polite" });
  const look = el("button", { type: "submit", class: "btn btn--primary", text: "See what it does" });
  const file = el("input", { type: "file", id: "pl-file", accept: ".json,application/json", class: "input" });
  const form = el("form", { class: "form-stack", novalidate: true },
    field("The plug-in's manifest address", address, { hint: "The https address of its starboard-plugin.json, from the plug-in's own page." }),
    field("Or its manifest file", file, { hint: "starboard-plugin.json from the plug-in's folder. A plug-in's own installer fills this in for you." }),
    el("div", { class: "actions" }, look));
  let given = null; // a manifest from a file, or from a plug-in's installer link (#manifest=...)
  file.addEventListener("change", async () => { given = file.files[0] ? await file.files[0].text() : null; });
  const fromLink = /^#manifest=([A-Za-z0-9_-]+)$/.exec(location.hash);
  if (fromLink) {
    try { given = new TextDecoder().decode(Uint8Array.from(atob(fromLink[1].replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0))); }
    catch { given = null; }
    history.replaceState(null, "", location.pathname);
    if (given) queueMicrotask(() => form.requestSubmit());
  }
  const source = () => (given ? { manifest: given } : { address: address.value.trim() });
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    setError(address, "");
    let s;
    try { s = await api("/api/plugins/preview", { method: "POST", body: source() }); }
    catch (err) { setError(address, err.message); address.focus(); return; }
    const add = el("button", { type: "button", class: "btn btn--primary", text: `Install ${s.name || "it"}…` });
    add.addEventListener("click", async () => {
      const password = await installWarning(s, { opener: add });
      if (password === null) return;
      try { await api("/api/plugins/add", { method: "POST", body: { ...source(), password } }); toast(`${s.name} installed. Activate it when you are ready`); location.href = `/settings-plugin.html?id=${encodeURIComponent(s.id)}`; }
      catch (err) { problem(err.message, add); }
    });
    seen.replaceChildren(...[
      el("h3", { text: `${s.name || "This plug-in"} ${s.version || ""}` }), el("p", { text: s.description || "" }),
      el("p", { class: "small", text: [s.author && `By ${s.author}`, s.licence, s.needs.length && `Needs ${s.needs.join(" and ")}`].filter(Boolean).join(" · ") }),
      el("h3", { text: "What it may do" }), pluginPermissions(s.permissions),
      s.styles.length ? el("p", { class: "small", text: `Styles: ${s.styles.map((x) => x.name).join(", ")}.` }) : null,
      el("h3", { text: "Test results" }), testReport(s.test),
      s.test.ok ? el("div", { class: "actions" }, add) : null].filter(Boolean));
    seen.querySelector("h3")?.focus?.();
  });
  return section("pl-add", "Add one from elsewhere", "By its address or its manifest file. Starboard tests it and shows what it may do before anything is installed.", form, seen);
}

// Settings, Plug-ins, Manage (DASH-318): the plug-ins added, each with its state, Settings, Activate or Deactivate
// and Remove; Deactivate all. Adding is on the Catalogue page.
// Plug-ins ticked in the first set-up (DASH-399), such as Audio description: an offer, never an install. On the
// Catalogue (c given) it installs as any other, its permissions shown and the password asked; on Your plug-ins it
// links to the Catalogue. Not now forgets the wish. Focus goes to the page's first heading once the offer has gone.
// Not now says itself where the offer was (Settings pattern 2: no toast on a Settings page), drawn once.
let offerSaid = "";
function setupOffers(r, c, redraw) {
  const said = offerSaid ? [notice("success", offerSaid)] : [];
  offerSaid = "";
  return [...said, ...(r.wanted || []).map((w) => {
    const entry = c ? c.plugins.find((e) => e.id === w.id && e.own) : null;
    const later = el("button", { type: "button", class: "btn btn--quiet btn--compact" }, w.later,
      el("span", { class: "visually-hidden", text: `: ${w.name}` }));
    later.addEventListener("click", async () => {
      later.disabled = true;
      try {
        const o = await api("/api/plugins/wanted", { method: "POST", body: { id: w.id } });
        offerSaid = o.said;
        await redraw();
        const h = $("main h1");
        if (h) { h.tabIndex = -1; h.focus(); }
      } catch (err) { problem(err.message, later); later.disabled = false; }
    });
    let go = null;
    if (!c) go = el("a", { class: "btn btn--compact", href: "/settings-plugins-catalogue.html" }, icon("layout-grid"), "Open the catalogue");
    else if (entry && entry.published && entry.manifest) {
      go = el("button", { type: "button", class: "btn btn--primary btn--compact", text: w.install });
      go.addEventListener("click", async () => {
        go.disabled = true;
        try {
          const s = await api("/api/plugins/preview", { method: "POST", body: { catalogue_id: w.id } });
          if (!s.test.ok) { problem(`${w.name} did not pass Starboard's tests: ${s.test.issues.filter((i) => i.severity === "error").map((i) => i.what).join("; ")}`, go); return; }
          const password = await installWarning(s, { opener: go });
          if (password === null) return;
          await api("/api/plugins/add", { method: "POST", body: { catalogue_id: w.id, password } });
          location.href = `/settings-plugin.html?id=${encodeURIComponent(w.id)}`;
        } catch (err) { problem(err.message, go); }
        finally { go.disabled = false; }
      });
    }
    const text = c && !go ? w.coming : w.text;
    return el("div", { class: "stack-2", "data-offer": w.id }, notice("info", w.title, text, el("div", { class: "actions" }, go, later)));
  })];
}

async function startPlugins() {
  // Plug-in installers open this page with #manifest=...: adding is on the Catalogue page now.
  if (location.hash.startsWith("#manifest=")) { location.replace(`/settings-plugins-catalogue.html${location.hash}`); return; }
  const holder = $("#plugins-sections");
  const draw = async () => {
    let r;
    try { r = await api("/api/plugins"); } catch (e) { holder.replaceChildren(notice("danger", "Could not load the plug-ins", e.message)); return; }
    holder.removeAttribute("aria-busy");
    if (!r.plugins.length) {
      holder.replaceChildren(...setupOffers(r, null, draw), section("pl-yours", "Your plug-ins", "Plug-ins add pages and settings to Starboard.",
        emptyState("No plug-ins yet", "Add one from the catalogue.", el("a", { class: "btn btn--primary", href: "/settings-plugins-catalogue.html" }, icon("layout-grid"), "Open the catalogue"))));
      return;
    }
    const stopAll = el("button", { type: "button", class: "btn btn--danger", text: "Deactivate all plug-ins" });
    stopAll.addEventListener("click", async () => {
      if (!await confirmDialog({ title: "Deactivate all plug-ins?", message: "Every active plug-in is deactivated. Their settings stay; activate each again here.", confirm: "Deactivate all", danger: true })) return;
      try { const o = await api("/api/plugins/stop-all", { method: "POST" }); toast(o.stopped.length ? `Deactivated ${o.stopped.join(", ")}` : "No plug-in was active"); draw(); }
      catch (err) { problem(err.message, stopAll); }
    });
    const active = r.plugins.filter((p) => p.state === "enabled").length;
    holder.replaceChildren(...setupOffers(r, null, draw),
      section("pl-yours", "Your plug-ins", `${r.plugins.length} added, ${active} active. Each one's settings are in its own tab above.`,
        el("ul", { class: "rows" }, r.plugins.map((p) => el("li", { class: "row row--no-lead" },
          el("div", {}, el("h3", { class: "row__title" }, el("a", { href: `/settings-plugin.html?id=${encodeURIComponent(p.id)}`, text: p.name })),
            el("div", { class: "row__meta", text: [`Version ${p.version}`, p.builtin ? "Built into Starboard" : p.author && `By ${p.author}`, p.message].filter(Boolean).join(" · ") })),
          // Three fixed columns, so the chips, Settings and the state button line up from row to row (issue #10).
          el("div", { class: "row__side plugin-row__side" }, el("span", { class: "plugin-row__chips" }, chip(...chipOf(p)), p.update ? chip("Update", "info") : null),
            el("a", { class: "btn btn--quiet btn--compact", href: `/settings-plugin.html?id=${encodeURIComponent(p.id)}` }, icon("settings"), "Settings",
              el("span", { class: "visually-hidden", text: ` for ${p.name}` })),
            stateButton(p, draw))))),
        el("div", { class: "actions" }, el("a", { class: "btn", href: "/settings-plugins-catalogue.html" }, icon("plus"), "Add a plug-in"))),
      dangerSection("pl-all", "All plug-ins at once", "Stops every plug-in, for example while you look into a problem.", el("div", { class: "actions" }, stopAll)));
  };
  draw();
}

// Settings, Plug-ins, Catalogue (DASH-318, owner, 12 November 2026: "in its own menu 2 and needs a description"):
// Starboard's own plug-ins, the Starboard plug-ins collection by kind, any other by its address, and the tester.
async function startCatalogue() {
  const holder = $("#plugins-catalogue");
  const draw = async () => {
    let r, c;
    try { [r, c] = await Promise.all([api("/api/plugins"), api("/api/plugins/catalogue")]); }
    catch (e) { holder.replaceChildren(notice("danger", "Could not load the catalogue", e.message)); return; }
    holder.removeAttribute("aria-busy");
    const ORDER = ["Look", "Accessibility", "Jellyfin", "Downloads", "Network", "Home", "System"];
    const rank = (k) => (ORDER.includes(k) ? ORDER.indexOf(k) : ORDER.length);
    const byKind = (list) => {
      const kinds = new Map();
      for (const e of [...list].sort((a, b) => rank(a.kind) - rank(b.kind) || a.name.localeCompare(b.name))) {
        if (!kinds.has(e.kind)) kinds.set(e.kind, []);
        kinds.get(e.kind).push(e);
      }
      return [...kinds].map(([k, rows]) => el("section", { class: "stack-2", "aria-label": k }, el("h3", { text: k }), el("ul", { class: "rows" }, rows.map(entry))));
    };
    const entry = (e) => {
      let side;
      if (e.added) side = el("a", { class: "btn btn--quiet btn--compact", href: `/settings-plugin.html?id=${encodeURIComponent(e.id)}` }, icon("circle-check"), "Added");
      else if (!e.published || !e.manifest) side = chip("Coming soon", "muted");
      else {
        side = el("button", { type: "button", class: "btn btn--compact" }, icon("plus"), "Install…", el("span", { class: "visually-hidden", text: ` ${e.name}` }));
        side.addEventListener("click", async () => {
          side.disabled = true;
          try {
            const s = await api("/api/plugins/preview", { method: "POST", body: { catalogue_id: e.id } });
            if (!s.test.ok) { problem(`${e.name} did not pass Starboard's tests: ${s.test.issues.filter((i) => i.severity === "error").map((i) => i.what).join("; ")}`, side); return; }
            const password = await installWarning(s, { opener: side });
            if (password === null) return;
            await api("/api/plugins/add", { method: "POST", body: { catalogue_id: e.id, password } });
            location.href = `/settings-plugin.html?id=${encodeURIComponent(e.id)}`;
          } catch (err) { problem(err.message, side); }
          finally { side.disabled = false; }
        });
      }
      return el("li", { class: "row row--no-lead" },
        el("div", {}, el("h4", { class: "row__title", text: e.name }),
          el("div", { class: "row__meta", text: e.description }),
          // Versions for this Starboard only (DASH-330): newer ones that need a newer Starboard are said, not offered.
          e.version || e.hidden ? el("div", { class: "row__meta", text: [e.version ? `Version ${e.version}` : "",
            e.hidden ? `${e.hidden} newer ${e.hidden === 1 ? "version needs" : "versions need"} Starboard's API ${e.hidden_needs}` : ""].filter(Boolean).join(" · ") }) : null),
        el("div", { class: "row__side" }, side));
    };
    holder.replaceChildren(...[
      ...setupOffers(r, c, draw),
      builtinSection(r.builtin || [], draw),
      ...c.catalogues.map((cat, n) => {
        const rows = c.plugins.filter((e) => e.catalogue === cat.name && e.own === cat.own);
        return section(`pl-cat-${n}`, cat.own ? "The Starboard plug-ins collection" : cat.name,
          cat.own ? "Made by TheMightyTRexUK and tested with each Starboard release."
            : `From ${cat.url.split("/")[2]}, added by you. Starboard did not make these: check each one's warning before you install it.`,
          cat.error ? notice("warning", "This catalogue did not answer", `${cat.error}. Showing the list from the last time it did.`) : null,
          rows.length ? byKind(rows) : el("p", { class: "small muted", text: "It lists no plug-ins." }));
      }),
      sourcesSection(c.catalogues, draw),
      addPluginSection(draw), testerSection()].filter(Boolean));
  };
  draw();
}

// Catalogue sources (owner, 12 November 2026): other catalogues added from a link, listed above with their plug-ins.
// Adding a catalogue installs nothing; each plug-in still shows its warning before it is installed.
function sourcesSection(cats, redraw) {
  const input = el("input", { class: "input", id: "pl-cat-address", type: "url", placeholder: "https://", autocomplete: "off", spellcheck: "false" });
  const go = el("button", { type: "submit", class: "btn btn--primary" }, icon("plus"), "Add catalogue");
  const form = el("form", { class: "form-stack", novalidate: true },
    field("Catalogue address", input, { hint: "The https address of a catalogue.json, from the page of the person who made it." }),
    el("div", { class: "actions" }, go,
      el("a", { class: "btn btn--quiet", href: `${($("[data-help-link]")?.getAttribute("href") || "https://themightytrex.github.io/starboard/help/").replace(/(\/help\/).*$/, "$1")}topics/add-a-plugin.html#add-a-catalogue-from-a-link`, target: "_blank", rel: "noopener noreferrer" },
        icon("help-new-tab"), "How to add a catalogue", el("span", { class: "visually-hidden", text: " (opens in a new tab)" }))));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    setError(input, "");
    if (!input.value.trim()) { setError(input, "Paste the catalogue's address"); input.focus(); return; }
    go.disabled = true;
    try { toast((await api("/api/plugins/catalogues", { method: "POST", body: { action: "add", url: input.value.trim() } })).said); redraw(); }
    catch (err) { setError(input, err.message); input.focus(); }
    finally { go.disabled = false; }
  });
  const rows = cats.map((cat) => {
    const side = cat.own ? chip("Always here", "muted") : (() => {
      const b = el("button", { type: "button", class: "btn btn--quiet btn--compact btn--danger" }, icon("trash-2"), "Remove",
        el("span", { class: "visually-hidden", text: ` ${cat.name}` }));
      b.addEventListener("click", async () => {
        if (!await confirmDialog({ title: `Remove ${cat.name}?`, confirm: "Remove", danger: true, message: "Its plug-ins leave the catalogue. Plug-ins you already added from it stay." })) return;
        try { toast((await api("/api/plugins/catalogues", { method: "POST", body: { action: "remove", url: cat.url } })).said); redraw(); }
        catch (err) { problem(err.message, b); }
      });
      return b;
    })();
    return el("li", { class: "row row--no-lead" },
      el("div", {}, el("div", { class: "row__title", text: cat.own ? "The Starboard plug-ins collection" : cat.name }),
        el("div", { class: "row__meta row__meta--wrap", text: [`${cat.count} plug-in${cat.count === 1 ? "" : "s"}`, cat.url, cat.error && "Not answering"].filter(Boolean).join(" · ") })),
      el("div", { class: "row__side" }, side));
  });
  return section("pl-sources", "Catalogue sources", "Where this page finds plug-ins. Add another catalogue by its link; each is read at most once a day.",
    el("ul", { class: "rows" }, rows), form);
}

// Settings, Plug-ins, <a plug-in> (DASH-318): ?id= names it; its name and description become the page's heading.
async function startPluginPage() {
  const holder = $("#plugin-page");
  const id = new URLSearchParams(location.search).get("id") || "";
  const draw = async () => {
    let r;
    try { r = await api("/api/plugins"); } catch (e) { holder.replaceChildren(notice("danger", "Could not load the plug-in", e.message)); return; }
    holder.removeAttribute("aria-busy");
    const p = r.plugins.find((x) => x.id === id);
    if (!p) {
      holder.replaceChildren(notice("info", "That plug-in is not added", "It may have been removed. Manage lists the plug-ins you have."),
        el("div", { class: "actions" }, el("a", { class: "btn", href: "/settings-plugins.html" }, "Manage plug-ins")));
      return;
    }
    $("#plugin-title").textContent = p.name;
    $("#plugin-summary").textContent = p.description || "";
    document.title = document.title.replace(/^[^·]*·/, `${p.name} ·`);
    holder.replaceChildren(...pluginPage(p, draw));
  };
  draw();
}

document.addEventListener("DOMContentLoaded", () => {
  if ($("#plugins-sections")) startPlugins();
  if ($("#plugins-catalogue")) startCatalogue();
  if ($("#plugin-page")) startPluginPage();
});
