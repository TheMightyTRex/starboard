// Settings, Plug-ins (DASH-149): the plug-ins added, Add a plug-in with what it may do shown before anything
// is installed, Activate and Deactivate, Remove (its folder is kept), Deactivate all plug-ins, and each plug-in's settings,
// drawn by Starboard from its manifest. A plug-in never adds code to this page.

const RISK = { low: ["Low", "success"], medium: ["Medium", "warning"], high: ["High", "danger"] };
const STATE = { installed: ["Added, not active", "muted"], enabled: ["Active", "success"], disabled: ["Inactive", "muted"], failed: ["Did not start", "danger"] };

function pluginPermissions(list) {
  if (!list.length) return el("p", { class: "small", text: "It asks for nothing beyond its own folder." });
  return el("ul", { class: "rows" }, list.map((p) => el("li", { class: "row row--no-lead" },
    el("div", {}, el("div", { class: "row__title", text: p.words }), el("div", { class: "row__meta", text: p.permission })),
    el("div", { class: "row__side" }, chip(...RISK[p.risk])))));
}

// The install warning (owner, 12 November 2026): a slide-out that says the plug-in is added at your own risk, then
// what it can see, change and reach and what it runs, with Install and Cancel. Resolves with the password, or null.
function installWarning(s, { builtin = false, opener } = {}) {
  return new Promise((resolve) => {
    const w = s.warning;
    let answer = null;
    const group = (title, ic, items, empty) => el("section", { class: "stack-2", "aria-label": title },
      el("h3", {}, icon(ic), ` ${title}`),
      items.length ? el("ul", { class: "install-warning__list" }, items.map((t) => el("li", { text: t }))) : el("p", { class: "small muted", text: empty }));
    const pw = el("input", { class: "input", type: "password", id: "pl-install-password", autocomplete: "current-password", required: true });
    const install = el("button", { type: "submit", class: "btn btn--primary", form: "pl-install-form" }, `Install ${s.name}`);
    const cancel = el("button", { type: "button", class: "btn" }, "Cancel");
    const form = el("form", { id: "pl-install-form", class: "form-stack", novalidate: true },
      field("Your Starboard password", pw, { hint: "To show it is you who is installing it." }));
    const panel = sidePanel({
      title: `Install ${s.name}?`, opener, wide: true,
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
        group("It can see", "eye", w.see, "Nothing of yours."),
        group("It can change", "pencil", w.change, "Nothing: it has no folder and no keys."),
        group("It can reach", "globe", w.reach, "Nothing: it runs no containers."),
        w.runs.length ? group("It runs", "server", w.runs, "") : null,
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
  const acc = el("p", {}, chip(r.accessibility.passed ? "Accessibility passed" : "Accessibility failed", r.accessibility.passed ? "success" : "danger"),
    el("span", { class: "small", text: ` Checked: ${r.accessibility.checked}.` }));
  const list = r.issues.length ? el("ul", { class: "rows" }, r.issues.map((i) => el("li", { class: "row row--no-lead" },
    el("div", {}, el("div", { class: "row__title", text: i.what }), el("div", { class: "row__meta", text: `${i.where} · ${i.area} · Fix: ${i.fix}` })),
    el("div", { class: "row__side" }, chip(...SEVERITY[i.severity]))))) : el("p", { class: "small", text: "No issues found." });
  return el("div", { class: "stack-4" }, head, acc, list);
}

function pluginSettingsForm(p, redraw) {
  const plain = p.settings.filter((s) => s.type !== "custom");
  if (!plain.length) return null;
  const inputs = {};
  const rows = plain.map((s) => {
    let input;
    const id = `pl-${p.id}-${s.key}`;
    if (s.type === "switch") input = el("input", { type: "checkbox", id, checked: !!s.value });
    else if (s.type === "choice") input = el("select", { class: "select", id }, (s.choices || []).map((c) => el("option", { value: c, text: c, selected: c === s.value })));
    else input = el("input", { class: "input", id, type: s.type === "number" ? "number" : s.type === "secret" ? "password" : "text",
      value: s.value ?? "", min: s.min, max: s.max, autocomplete: s.type === "secret" ? "new-password" : "off",
      placeholder: s.type === "secret" && s.set ? "Set. Leave empty to keep it" : "" });
    inputs[s.key] = [s, input];
    return field(s.unit ? `${s.label} (${s.unit})` : s.label, input, { hint: s.hint });
  });
  const form = el("form", { class: "form-stack", novalidate: true }, rows, el("div", { class: "actions" }, el("button", { type: "submit", class: "btn btn--primary", text: "Save" })));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const settings = {};
    for (const [key, [s, input]] of Object.entries(inputs)) {
      settings[key] = s.type === "switch" ? input.checked : s.type === "number" ? Number(input.value) : input.value;
    }
    try { await api(`/api/plugins/${p.id}/settings`, { method: "PUT", body: { settings } }); toast(`${p.name}: saved`); redraw(); }
    catch (err) { problem(err.message, form); }
  });
  return form;
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
function styleGallery(p) {
  const active = p.state === "enabled";
  const grid = el("ul", { class: "style-gallery" });
  const draw = () => {
    const current = readPrefs().style || "";
    grid.replaceChildren(...p.looks.map((look) => {
      const chosen = current === look.value;
      const use = el("button", { type: "button", class: chosen ? "btn btn--primary" : "btn", "aria-pressed": String(chosen), disabled: !active },
        chosen ? "In use" : "Use this style", el("span", { class: "visually-hidden", text: `: ${look.name}` }));
      use.addEventListener("click", () => {
        const prefs = { ...readPrefs(), style: chosen ? "" : look.value };
        writePrefs(prefs); applyPrefs(prefs); draw();
        announce(chosen ? "Back to Starboard's own style" : `${look.name} style in use`);
      });
      return el("li", { class: "style-gallery__item" },
        el("div", { class: "style-gallery__pics" }, stylePicture(look, "light"), stylePicture(look, "dark")),
        el("h4", { text: look.name }), el("p", { class: "small", text: look.description }), use);
    }));
  };
  draw();
  return el("div", { class: "stack-4" },
    el("p", { class: "small", text: active ? "Light on the left, dark on the right. Your choice applies to this browser, as in Display. High contrast always wins." : "Activate the plug-in to use its styles." }),
    grid);
}

// Activate or Deactivate one plug-in.
function stateButton(p, redraw) {
  const what = p.state === "enabled" ? "disable" : "enable";
  const b = el("button", { type: "button", class: what === "enable" ? "btn btn--primary" : "btn" }, what === "enable" ? "Activate" : "Deactivate",
    el("span", { class: "visually-hidden", text: ` ${p.name}` }));
  b.addEventListener("click", async () => {
    b.disabled = true;
    try { await api(`/api/plugins/${p.id}/${what}`, { method: "POST" }); toast(`${p.name} ${what === "enable" ? "activated" : "deactivated"}`); redraw(); }
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
    try { await api(`/api/plugins/${p.id}/remove`, { method: "POST", body: { password: pw.value } }); toast(`${p.name} removed`); after(); }
    catch (err) { problem(err.message, remove); }
  });
  return remove;
}

// A plug-in's own page, Settings, Plug-ins, <its name> (DASH-318), laid out like every Settings page (DASH-307):
// its state and buttons at the top, then its styles, settings and screens, what it may do, and Remove at the foot.
function pluginPage(p, redraw) {
  const buttons = (p.actions || []).map((a) => {
    const b = el("button", { type: "button", class: "btn", disabled: p.state !== "enabled" }, a.label);
    b.addEventListener("click", async () => {
      b.disabled = true;
      try { toast((await api(`/api/plugins/${p.id}/actions/${a.id}`, { method: "POST" })).said); }
      catch (err) { problem(err.message, b); }
      finally { b.disabled = false; }
    });
    return b;
  });
  const custom = p.settings.filter((s) => s.type === "custom");
  const form = pluginSettingsForm(p, redraw);
  return [
    section(`pl-${p.id}-state`, "State", p.builtin ? "Built into Starboard: it runs on Starboard's own image and updates with Starboard." : `Version ${p.version}${p.author ? `, by ${p.author}` : ""}.`,
      el("p", {}, chip(...(STATE[p.state] || ["Unknown", "muted"])), p.message ? el("span", { class: "small", text: ` ${p.message}` }) : null),
      el("div", { class: "actions" }, stateButton(p, redraw), ...buttons)),
    p.looks?.length ? section(`pl-${p.id}-styles`, "Styles", "", styleGallery(p)) : null,
    form ? section(`pl-${p.id}-settings`, "Settings", "Saved for everyone who uses this Starboard.", form) : null,
    ...custom.map((c) => section(`pl-${p.id}-${c.key}`, c.label, c.hint || "", customScreen(p, c))),
    section(`pl-${p.id}-may`, "What it may do", "What you allowed when you installed it.", pluginPermissions(p.permissions)),
    section(`pl-${p.id}-remove`, "Remove", "Stops it and takes it off this Starboard. Its folder is kept.",
      el("div", { class: "actions" }, removeButton(p, () => { location.href = "/settings-plugins.html"; })))].filter(Boolean);
}

// A plug-in's own screen (11 November 2026): a managed list the plug-in describes as data, drawn here. Rows grouped
// with a state, Test, Turn on or off, Move and Remove; Add takes an address; Test all checks everything at once.
const CUSTOM_STATE = { ok: ["Works", "success"], warning: ["Slow", "warning"], problem: ["Not answering", "danger"],
  off: ["Off", "muted"], unknown: ["Not tested", "muted"] };
function customScreen(p, s) {
  const box = el("div", { class: "stack-4", "aria-live": "polite" }, el("p", { class: "muted", text: "Loading…" }));
  const said = el("p", { class: "small", role: "status" });
  const path = `/api/plugins/${p.id}/custom/${s.key}`;
  const run = async (body, button) => {
    if (button) button.disabled = true;
    try { const out = await api(path, { method: "POST", body }); if (out.said) { said.textContent = out.said; toast(out.said); } draw(out); }
    catch (err) { problem(err.message, button); }
    finally { if (button) button.disabled = false; }
  };
  const ACTION_WORDS = { test: ["Test", "activity"], toggle: [null, null], remove: ["Remove", "trash-2"], up: ["Move up", "arrow-up"], down: ["Move down", "arrow-down"] };
  const draw = (data) => {
    const groups = new Map();
    for (const it of data.items) { if (!groups.has(it.group)) groups.set(it.group, []); groups.get(it.group).push(it); }
    const add = data.add ? (() => {
      const id = `add-${p.id}-${s.key}`;
      const input = el("input", { class: "input", id, type: "url", placeholder: data.add.placeholder || "", autocomplete: "off" });
      const go = el("button", { type: "submit", class: "btn btn--primary" }, icon("plus"), data.add.label || "Add");
      const form = el("form", { class: "stack-2" }, el("label", { class: "field__label", for: id, text: data.add.label || "Add" }),
        data.add.hint ? el("p", { class: "hint", text: data.add.hint }) : null, el("div", { class: "actions" }, input, go));
      form.addEventListener("submit", (e) => { e.preventDefault(); if (input.value.trim()) run({ action: "add", value: input.value.trim() }, go); });
      return form;
    })() : null;
    const testAll = el("button", { type: "button", class: "btn" }, icon("activity"), "Test all");
    testAll.addEventListener("click", () => run({ action: "test_all" }, testAll));
    box.replaceChildren(
      data.intro ? el("p", { class: "small muted", text: data.intro }) : null,
      el("div", { class: "actions" }, testAll), said,
      ...[...groups].map(([g, rows]) => el("section", { class: "stack-2", "aria-label": g || data.title },
        g ? el("h4", { text: g }) : null,
        el("ul", { class: "rows" }, rows.map((it) => el("li", { class: "row row--no-lead" },
          el("div", {}, el("h5", { class: "row__title", text: it.title }),
            el("div", { class: "row__meta", text: [it.detail, it.address].filter(Boolean).join(" · ") })),
          el("div", { class: "row__side" }, chip(...(CUSTOM_STATE[it.state] || CUSTOM_STATE.unknown)),
            it.choice ? (() => {  // a small choice on the row, such as a catalogue's weight (12 November 2026)
              const sel = el("select", { class: "select select--compact", "aria-label": `${it.choice.label}: ${it.title}` },
                it.choice.options.map(([v, words]) => el("option", { value: v, text: words, selected: v === it.choice.value })));
              sel.addEventListener("change", () => run({ action: "choose", id: it.id, value: sel.value }, sel));
              return el("label", { class: "row-choice" }, el("span", { class: "small", text: it.choice.label }), sel);
            })() : null,
            ...it.actions.map((a) => {
              const [label, ic] = a === "toggle" ? [it.on ? "Turn off" : "Turn on", it.on ? "pause" : "play"] : ACTION_WORDS[a];
              const b = el("button", { type: "button", class: "btn btn--quiet btn--compact" }, ic ? icon(ic) : null, label,
                el("span", { class: "visually-hidden", text: ` ${it.title}` }));
              b.addEventListener("click", async () => {
                if (a === "remove" && !(await confirmDialog({ title: `Remove ${it.title}?`, confirm: "Remove", message: "You can add it again by its address." }))) return;
                run({ action: a, id: it.id }, b);
              });
              return b;
            }))))))),
      ...(add ? [add] : []));
  };
  if (p.state !== "enabled") box.replaceChildren(el("p", { class: "small muted", text: `${s.label}: activate ${p.name} to see it.` }));
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
    el("label", { class: "check", for: dev.id }, dev, el("span", { text: "Allow images without a digest (while you develop it)" })),
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
      const add = el("button", { type: "button", class: "btn btn--primary", disabled: !!b.why_not }, `Add ${b.name}`);
      add.addEventListener("click", async () => {
        const password = await installWarning(b, { builtin: true, opener: add });
        if (password === null) return;
        try { await api("/api/plugins/add-builtin", { method: "POST", body: { id: b.id, password } }); toast(`${b.name} installed and active`); redraw(); }
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
async function startPlugins() {
  // Plug-in installers open this page with #manifest=...: adding is on the Catalogue page now.
  if (location.hash.startsWith("#manifest=")) { location.replace(`/settings-plugins-catalogue.html${location.hash}`); return; }
  const holder = $("#plugins-sections");
  const draw = async () => {
    let r;
    try { r = await api("/api/plugins"); } catch (e) { holder.replaceChildren(notice("danger", "Could not load the plug-ins", e.message)); return; }
    holder.removeAttribute("aria-busy");
    if (!r.plugins.length) {
      holder.replaceChildren(section("pl-yours", "Your plug-ins", "None added yet.",
        el("div", { class: "actions" }, el("a", { class: "btn btn--primary", href: "/settings-plugins-catalogue.html" }, icon("layout-grid"), "Open the catalogue"))));
      return;
    }
    const stopAll = el("button", { type: "button", class: "btn btn--danger", text: "Deactivate all plug-ins" });
    stopAll.addEventListener("click", async () => {
      if (!await confirmDialog({ title: "Deactivate all plug-ins?", message: "Every active plug-in is deactivated. Their settings stay; activate each again here.", confirm: "Deactivate all", danger: true })) return;
      try { const o = await api("/api/plugins/stop-all", { method: "POST" }); toast(o.stopped.length ? `Deactivated ${o.stopped.join(", ")}` : "No plug-in was active"); draw(); }
      catch (err) { problem(err.message, stopAll); }
    });
    const active = r.plugins.filter((p) => p.state === "enabled").length;
    holder.replaceChildren(
      section("pl-yours", "Your plug-ins", `${r.plugins.length} added, ${active} active. Each one's settings are in its own tab above.`,
        el("ul", { class: "rows" }, r.plugins.map((p) => el("li", { class: "row row--no-lead" },
          el("div", {}, el("h3", { class: "row__title" }, el("a", { href: `/settings-plugin.html?id=${encodeURIComponent(p.id)}`, text: p.name })),
            el("div", { class: "row__meta", text: [`Version ${p.version}`, p.builtin ? "Built into Starboard" : p.author && `By ${p.author}`, p.message].filter(Boolean).join(" · ") })),
          el("div", { class: "row__side" }, chip(...(STATE[p.state] || ["Unknown", "muted"])),
            el("a", { class: "btn btn--quiet btn--compact", href: `/settings-plugin.html?id=${encodeURIComponent(p.id)}` }, icon("settings"), "Settings",
              el("span", { class: "visually-hidden", text: ` for ${p.name}` })),
            stateButton(p, draw), removeButton(p, draw)))))),
      section("pl-all", "All plug-ins at once", "Stops every plug-in, for example while you look into a problem.", el("div", { class: "actions" }, stopAll)));
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
    const ORDER = ["Look", "Jellyfin", "Downloads", "Network", "Home", "System"];
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
            const s = await api("/api/plugins/preview", { method: "POST", body: { address: e.manifest } });
            if (!s.test.ok) { problem(`${e.name} did not pass Starboard's tests: ${s.test.issues.filter((i) => i.severity === "error").map((i) => i.what).join("; ")}`, side); return; }
            const password = await installWarning(s, { opener: side });
            if (password === null) return;
            await api("/api/plugins/add", { method: "POST", body: { address: e.manifest, password } });
            toast(`${e.name} installed. Activate it on its own tab when you are ready`);
            location.href = `/settings-plugin.html?id=${encodeURIComponent(e.id)}`;
          } catch (err) { problem(err.message, side); }
          finally { side.disabled = false; }
        });
      }
      return el("li", { class: "row row--no-lead" },
        el("div", {}, el("h4", { class: "row__title", text: e.name }),
          el("div", { class: "row__meta", text: e.description })),
        el("div", { class: "row__side" }, side));
    };
    holder.replaceChildren(...[
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
        if (!await confirmDialog({ title: `Remove ${cat.name}?`, confirm: "Remove", message: "Its plug-ins leave the catalogue. Plug-ins you already added from it stay." })) return;
        try { toast((await api("/api/plugins/catalogues", { method: "POST", body: { action: "remove", url: cat.url } })).said); redraw(); }
        catch (err) { problem(err.message, b); }
      });
      return b;
    })();
    return el("li", { class: "row row--no-lead" },
      el("div", {}, el("div", { class: "row__title", text: cat.own ? "The Starboard plug-ins collection" : cat.name }),
        el("div", { class: "row__meta", text: [`${cat.count} plug-in${cat.count === 1 ? "" : "s"}`, cat.url, cat.error && "Not answering"].filter(Boolean).join(" · ") })),
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
