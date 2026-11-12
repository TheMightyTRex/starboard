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
        el("p", {}, el("strong", { text: `${s.name} ${s.version || ""}` }), el("br"),
          el("span", { class: "small", text: [s.author && `By ${s.author}`, s.licence, s.homepage].filter(Boolean).join(" · ") }),
          w.risk ? el("span", {}, " ", chip(`${RISK[w.risk][0]} risk`, RISK[w.risk][1])) : null),
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
    pw.focus();
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
  return el("div", { class: "stack-4" }, el("h3", { text: "Styles" }),
    el("p", { class: "small", text: active ? "Light on the left, dark on the right. Your choice applies to this browser, as in Display. High contrast always wins." : "Activate the plug-in to use its styles." }),
    grid);
}

function pluginCard(p, redraw) {
  const act = (label, what, primary) => {
    const b = el("button", { type: "button", class: primary ? "btn btn--primary" : "btn" }, label);
    b.addEventListener("click", async () => {
      b.disabled = true;
      try { await api(`/api/plugins/${p.id}/${what}`, { method: "POST" }); toast(`${p.name} ${what === "enable" ? "activated" : "deactivated"}`); redraw(); }
      catch (err) { problem(err.message, b); b.disabled = false; }
    });
    return b;
  };
  const remove = el("button", { type: "button", class: "btn btn--quiet btn--danger" }, `Remove ${p.name}`);
  remove.addEventListener("click", async () => {
    const pw = el("input", { class: "input", type: "password", id: `pl-rm-${p.id}`, autocomplete: "current-password" });
    const ok = await confirmDialog({ title: `Remove ${p.name}?`, danger: true, confirm: "Remove",
      message: "Its containers stop and go, and its API key stops working. Its folder is kept in data/plugins/.removed, for you to delete when you are sure.",
      fields: [el("div", { class: "field" }, el("label", { for: pw.id, text: "Your Starboard password" }), pw)] });
    if (!ok) return;
    try { await api(`/api/plugins/${p.id}/remove`, { method: "POST", body: { password: pw.value } }); toast(`${p.name} removed`); redraw(); }
    catch (err) { problem(err.message, remove); }
  });
  // Its buttons, from the manifest (such as Run Live TV now): Starboard asks the plug-in and shows its answer.
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
  return section(`pl-${p.id}`, `${p.name} ${p.version}`, p.description,
    el("p", {}, chip(...(STATE[p.state] || ["Unknown", "muted"])), p.message ? el("span", { class: "small", text: ` ${p.message}` }) : null),
    el("div", { class: "actions" }, p.state === "enabled" ? act("Deactivate", "disable") : act("Activate", "enable", true), ...buttons, remove),
    p.builtin ? el("p", { class: "small muted", text: "Built into Starboard: it runs on Starboard's own image and updates with Starboard." }) : null,
    p.looks?.length ? styleGallery(p) : null,
    el("h3", { text: "What it may do" }), pluginPermissions(p.permissions),
    pluginSettingsForm(p, redraw),
    ...custom.map((s) => customScreen(p, s)));
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
      add);
  };
  if (p.state !== "enabled") box.replaceChildren(el("p", { class: "small muted", text: `${s.label}: activate ${p.name} to see it.` }));
  else api(path).then(draw).catch((err) => box.replaceChildren(notice("info", `${p.name} did not answer`, err.message)));
  return el("div", { class: "stack-2" }, el("h3", { text: s.label }), s.hint ? el("p", { class: "small muted", text: s.hint }) : null, box);
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
      try { await api("/api/plugins/add", { method: "POST", body: { ...source(), password } }); toast(`${s.name} installed. Activate it when you are ready`); address.value = ""; given = null; seen.replaceChildren(); redraw(); }
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
  return section("pl-add", "Add a plug-in", "Starboard shows what a plug-in may do before anything is installed. Plug-ins never get the Docker socket, the host network or other apps' settings.", form, seen);
}

async function startPlugins() {
  const holder = $("#plugins-sections");
  const draw = async () => {
    let r;
    try { r = await api("/api/plugins"); } catch (e) { holder.replaceChildren(notice("danger", "Could not load the plug-ins", e.message)); return; }
    holder.removeAttribute("aria-busy");
    const stopAll = el("button", { type: "button", class: "btn btn--danger", text: "Deactivate all plug-ins" });
    stopAll.addEventListener("click", async () => {
      if (!await confirmDialog({ title: "Deactivate all plug-ins?", message: "Every active plug-in is deactivated. Their settings stay; activate each again from its section.", confirm: "Deactivate all", danger: true })) return;
      try { const o = await api("/api/plugins/stop-all", { method: "POST" }); toast(o.stopped.length ? `Deactivated ${o.stopped.join(", ")}` : "No plug-in was active"); draw(); }
      catch (err) { problem(err.message, stopAll); }
    });
    holder.replaceChildren(...[
      r.plugins.length ? section("pl-yours", "Your plug-ins", `${r.plugins.length} added.`, el("div", { class: "actions" }, stopAll)) : null,
      ...r.plugins.map((p) => pluginCard(p, draw)),
      builtinSection(r.builtin || [], draw), addPluginSection(draw), testerSection()].filter(Boolean));
  };
  draw();
}

document.addEventListener("DOMContentLoaded", () => { if ($("#plugins-sections")) startPlugins(); });
