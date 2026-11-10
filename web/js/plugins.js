// Settings, Plug-ins (DASH-149): the plug-ins added, Add a plug-in with what it may do shown before anything
// is installed, Turn on and Turn off, Remove (its folder is kept), Stop all plug-ins, and each plug-in's settings,
// drawn by Starboard from its manifest. A plug-in never adds code to this page.

const RISK = { low: ["Low", "success"], medium: ["Medium", "warning"], high: ["High", "danger"] };
const STATE = { installed: ["Added, not running", "muted"], enabled: ["Running", "success"], disabled: ["Turned off", "muted"], failed: ["Did not start", "danger"] };

function pluginPermissions(list) {
  if (!list.length) return el("p", { class: "small", text: "It asks for nothing beyond its own folder." });
  return el("ul", { class: "rows" }, list.map((p) => el("li", { class: "row row--no-lead" },
    el("div", {}, el("div", { class: "row__title", text: p.words }), el("div", { class: "row__meta", text: p.permission })),
    el("div", { class: "row__side" }, chip(...RISK[p.risk])))));
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

function pluginCard(p, redraw) {
  const act = (label, what, primary) => {
    const b = el("button", { type: "button", class: primary ? "btn btn--primary" : "btn" }, label);
    b.addEventListener("click", async () => {
      b.disabled = true;
      try { await api(`/api/plugins/${p.id}/${what}`, { method: "POST" }); toast(`${p.name}: ${what === "enable" ? "running" : "turned off"}`); redraw(); }
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
  const custom = p.settings.filter((s) => s.type === "custom");
  return section(`pl-${p.id}`, `${p.name} ${p.version}`, p.description,
    el("p", {}, chip(...(STATE[p.state] || ["Unknown", "muted"])), p.message ? el("span", { class: "small", text: ` ${p.message}` }) : null),
    el("div", { class: "actions" }, p.state === "enabled" ? act("Turn off", "disable") : act("Turn on", "enable", true), remove),
    el("h3", { text: "What it may do" }), pluginPermissions(p.permissions),
    pluginSettingsForm(p, redraw),
    custom.length ? el("p", { class: "small muted", text: `${custom.map((s) => s.label).join(", ")}: on its own screen, which comes with the next part of plug-ins.` }) : null);
}

function addPluginSection(redraw) {
  const address = el("input", { class: "input", id: "pl-address", type: "url", placeholder: "https://", autocomplete: "off", spellcheck: "false" });
  const seen = el("div", { class: "stack-4", "aria-live": "polite" });
  const look = el("button", { type: "submit", class: "btn btn--primary", text: "See what it does" });
  const form = el("form", { class: "form-stack", novalidate: true },
    field("The plug-in's manifest address", address, { hint: "The https address of its starboard-plugin.json, from the plug-in's own page." }),
    el("div", { class: "actions" }, look));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    setError(address, "");
    let s;
    try { s = await api("/api/plugins/preview", { method: "POST", body: { address: address.value.trim() } }); }
    catch (err) { setError(address, err.message); address.focus(); return; }
    const pw = el("input", { class: "input", type: "password", id: "pl-add-password", autocomplete: "current-password" });
    const add = el("button", { type: "button", class: "btn btn--primary", text: `Add ${s.name || "it"}` });
    add.addEventListener("click", async () => {
      try { await api("/api/plugins/add", { method: "POST", body: { address: address.value.trim(), password: pw.value } }); toast(`${s.name} added. Turn it on when you are ready`); address.value = ""; seen.replaceChildren(); redraw(); }
      catch (err) { problem(err.message, add); }
    });
    seen.replaceChildren(
      el("h3", { text: `${s.name || "This plug-in"} ${s.version || ""}` }), el("p", { text: s.description || "" }),
      el("p", { class: "small", text: [s.author && `By ${s.author}`, s.licence, s.needs.length && `Needs ${s.needs.join(" and ")}`].filter(Boolean).join(" · ") }),
      s.problems.length ? notice("danger", "It cannot be added", s.problems.join(". ")) : null,
      el("h3", { text: "What it may do" }), pluginPermissions(s.permissions),
      s.problems.length ? null : el("div", { class: "form-stack" }, field("Your Starboard password", pw), el("div", { class: "actions" }, add)));
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
    const stopAll = el("button", { type: "button", class: "btn btn--danger", text: "Stop all plug-ins" });
    stopAll.addEventListener("click", async () => {
      if (!await confirmDialog({ title: "Stop all plug-ins?", message: "Every plug-in that runs stops. Their settings stay; turn each on again from its section.", confirm: "Stop all", danger: true })) return;
      try { const o = await api("/api/plugins/stop-all", { method: "POST" }); toast(o.stopped.length ? `Stopped ${o.stopped.join(", ")}` : "Nothing was running"); draw(); }
      catch (err) { problem(err.message, stopAll); }
    });
    holder.replaceChildren(
      r.plugins.length ? section("pl-yours", "Your plug-ins", `${r.plugins.length} added.`, el("div", { class: "actions" }, stopAll)) : null,
      ...r.plugins.map((p) => pluginCard(p, draw)),
      addPluginSection(draw));
  };
  draw();
}

document.addEventListener("DOMContentLoaded", () => { if ($("#plugins-sections")) startPlugins(); });
