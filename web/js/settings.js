// Settings: Manage apps (add, edit, test, order, hide, remove), General, Security, and About and updates.
// Each page has its own start function below; the page's markup says which one runs.

let config = null;
const SEARCHABLE = ["sonarr", "radarr", "lidarr", "readarr"];
const NO_KEY = ["jellyfin", "link"];

// Small helpers ------------------------------------------------------------

// Checks of the password answer 401 when it is wrong. api() in common.js reads 401 as "signed out" and goes to
// Sign in, so these calls keep the page and show the error by the field instead.
async function postKeepingPage(path, body) {
  const res = await fetch(path, {
    method: "POST", credentials: "same-origin",
    headers: { Accept: "application/json", "Content-Type": "application/json", "X-Starboard": "1" },
    body: JSON.stringify(body || {}),
  });
  let data = {};
  try { data = await res.json(); } catch { /* empty */ }
  if (!res.ok) {
    const error = new Error(data.error || `Something went wrong (error ${res.status})`);
    error.status = res.status;
    throw error;
  }
  return data;
}

// A field with its label, hint and an error tied to the control.
let fieldCount = 0;
function field(label, control, { hint, span, short } = {}) {
  if (!control.id) control.id = `field-${++fieldCount}`;
  const hintNode = hint ? el("span", { class: "hint", id: `${control.id}-hint` }, hint) : null;
  const error = el("span", { class: "field-error", id: `${control.id}-error`, hidden: true });
  if (hintNode) control.setAttribute("aria-describedby", hintNode.id);
  control.fieldError = error;
  control.fieldHint = hintNode;
  return el("div", { class: short ? "field field--short" : "field", "data-span": span ? "all" : null },
    el("label", { for: control.id, text: label }), hintNode, control, error);
}

function setError(control, message) {
  const error = control.fieldError;
  const ids = [control.fieldHint?.id];
  if (message) {
    error.replaceChildren(icon("circle-alert"), el("span", { text: message }));
    error.hidden = false;
    control.setAttribute("aria-invalid", "true");
    ids.push(error.id);
  } else {
    error.hidden = true;
    error.replaceChildren();
    control.removeAttribute("aria-invalid");
  }
  const describedBy = ids.filter(Boolean).join(" ");
  if (describedBy) control.setAttribute("aria-describedby", describedBy); else control.removeAttribute("aria-describedby");
}

function switchRow(label, hint, input) {
  input.setAttribute("role", "switch");
  return el("label", { class: "switch" },
    el("span", { class: "check__text" }, el("strong", { text: label }), hint ? el("span", { class: "check__hint", text: hint }) : null), input);
}

// A settings row: label and hint on the left, the control on the right.
function settingRow(label, hint, control, labelId) {
  return el("li", { class: "setting" },
    el("div", { class: "setting__text" }, el("span", { class: "setting__label", id: labelId || null, text: label }), hint ? el("span", { class: "setting__hint" }, hint) : null),
    el("div", { class: "setting__control" }, control));
}

function notice(tone, title, text, action) {
  const icons = { success: "circle-check", warning: "triangle-alert", danger: "circle-alert", info: "info" };
  return el("div", { class: "notice", "data-tone": tone === "info" ? null : tone, role: "status" },
    icon(icons[tone] || "info"), el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: title }), text ? el("p", {}, text) : null), action || null);
}

// One section of a settings page: an h2, a one-line description and its content.
function section(id, title, description, ...content) {
  return el("section", { class: "settings-section", "aria-labelledby": `${id}-h` },
    el("div", { class: "settings-section__head" }, el("h2", { id: `${id}-h`, text: title }), description ? el("p", { class: "small muted" }, description) : null),
    ...content);
}

async function saveGeneral(body, message) {
  config = await api("/api/config/general", { method: "PUT", body });
  if (message) toast(message);
  $$("[data-site-name]").forEach((n) => { n.textContent = config.site_name; });
  return config;
}

// The whole app, as the server wants it back: a blank API key keeps the saved one.
function serviceBody(s, changes = {}) {
  const body = { ...s, ...changes };
  delete body.has_api_key;
  body.api_key = changes.api_key || "";
  if (body.link === body.url) body.link = "";
  return body;
}

// Redraws a list and keeps focus on the same control of the same row (rows carry data-key), so a row that moved
// keeps focus. (renderKeyed in common.js loses rows when render returns a new node for a key it already had.)
function redraw(root, nodes) {
  const focused = document.activeElement;
  const row = root.contains(focused) ? focused.closest("[data-key]") : null;
  const controls = (node) => [...node.querySelectorAll("button, a, input, select")];
  const at = row ? controls(row).indexOf(focused) : -1;
  root.replaceChildren(...nodes);
  if (!row) return;
  const again = [...root.querySelectorAll("[data-key]")].find((n) => n.dataset.key === row.dataset.key);
  (again && at >= 0 ? controls(again)[at] : again)?.focus({ preventScroll: true });
}

// Menu items run after the menu has closed and given focus back to its button, so a dialog returns there.
function later(fn) { setTimeout(fn, 0); }

// Manage apps ---------------------------------------------------------------

let statusById = {};

function sectionKeyOf(s) { return s.background ? "background" : `group:${s.group || ""}`; }

function sectionsOf(services) {
  const shown = services.filter((s) => !s.background);
  const groups = [...config.groups];
  for (const s of shown) if (s.group && !groups.includes(s.group)) groups.push(s.group);
  const out = groups.map((g) => ({ key: `group:${g}`, title: g, items: shown.filter((s) => s.group === g) }));
  out.push({ key: "group:", title: "Other", items: shown.filter((s) => !s.group) });
  out.push({ key: "background", title: "Other services", hint: "Services with no web page. They appear under Apps, Other services.", items: services.filter((s) => s.background) });
  return out.filter((g) => g.items.length);
}

function statusChip(s) {
  if (!s.enabled) return chip("Hidden", "muted");
  const st = statusById[s.id];
  if (!st) return null;
  if (st.state === "up") return chip(s.background ? "Running" : "Connected", "success");
  if (st.state === "down") return chip(s.background ? "Not running" : "Cannot connect", "danger");
  return chip("Not checked", "muted");
}

function serviceMeta(s) {
  const type = config.types[s.type]?.label || s.type;
  const target = s.follows ? config.services.find((x) => x.id === s.follows) : null;
  return [
    s.url ? shortUrl(s.url) : "No address",
    type,
    target ? `follows ${target.name}` : null,
    SEARCHABLE.includes(s.type) ? "searched" : null,
    s.outside_link ? "outside address set" : null,
    s.enabled ? null : "hidden from the dashboard",
  ].filter(Boolean).join(" · ");
}

function serviceRow(s, items, index) {
  const menuItems = [];
  if (index > 0) menuItems.push({ label: "Move up", icon: "arrow-up", onSelect: () => later(() => moveService(s, -1)) });
  if (index < items.length - 1) menuItems.push({ label: "Move down", icon: "arrow-down", onSelect: () => later(() => moveService(s, 1)) });
  menuItems.push(s.enabled
    ? { label: "Hide from the dashboard", icon: "eye-off", onSelect: () => later(() => setShown(s, false)) }
    : { label: "Show on the dashboard", icon: "eye", onSelect: () => later(() => setShown(s, true)) });
  menuItems.push({ label: "Remove", icon: "trash-2", danger: true, onSelect: () => later(() => removeService(s)) });
  return el("li", { class: "row row--opens" },
    appIcon(s, "app-icon"),
    el("div", { class: "row__text" },
      el("div", { class: "row__title" }, el("button", { type: "button", onclick: (e) => openService(s, e.currentTarget) }, s.name)),
      el("div", { class: "row__meta", text: serviceMeta(s) })),
    el("div", { class: "row__side" },
      statusChip(s),
      el("button", { type: "button", class: "btn", onclick: (e) => openService(s, e.currentTarget) }, icon("pencil"), "Edit", el("span", { class: "visually-hidden", text: ` ${s.name}` })),
      menuButton(`More actions for ${s.name}`, menuItems)));
}

function renderServices() {
  const root = $("#app-sections");
  root.removeAttribute("aria-busy");
  const apps = config.services.filter((s) => !s.background).length;
  const bg = config.services.length - apps;
  $("#apps-summary").textContent = config.services.length
    ? `${apps} ${apps === 1 ? "app" : "apps"}${bg ? ` and ${bg} ${bg === 1 ? "service" : "services"}` : ""}, in the order they appear on the dashboard.`
    : "The apps on your dashboard, in the order they appear.";
  if (!config.services.length) {
    root.replaceChildren(el("div", { class: "empty" },
      el("p", { text: "No apps yet. Add the first one, with the address Starboard uses to reach it." }),
      el("button", { type: "button", class: "btn btn--primary", onclick: (e) => openService(null, e.currentTarget) }, icon("plus"), "Add an app")));
    return;
  }
  redraw(root, sectionsOf(config.services).map((g, i) => el("section", { class: "settings-section settings-section--wide", "aria-labelledby": `sec-${i}-h` },
    el("div", { class: "settings-section__head" }, el("h2", { id: `sec-${i}-h`, text: g.title }), g.hint ? el("p", { class: "small muted", text: g.hint }) : null),
    el("ul", { class: "rows" }, g.items.map((s, index) => {
      const row = serviceRow(s, g.items, index);
      row.dataset.key = s.id;
      return row;
    })))));
}

async function loadStatus() {
  try {
    const { items } = await api("/api/status");
    statusById = Object.fromEntries(items.map((i) => [i.id, i]));
    renderServices();
  } catch { /* no status chips */ }
}

async function moveService(s, by) {
  const peers = config.services.filter((x) => sectionKeyOf(x) === sectionKeyOf(s));
  const at = peers.findIndex((x) => x.id === s.id);
  const other = peers[at + by];
  if (!other) return;
  const ids = config.services.map((x) => x.id);
  const i = ids.indexOf(s.id);
  const j = ids.indexOf(other.id);
  [ids[i], ids[j]] = [ids[j], ids[i]];
  try {
    config = await api("/api/services/order", { method: "POST", body: { ids } });
    renderServices();
    announce(`${s.name} moved ${by < 0 ? "up" : "down"}, now ${at + by + 1} of ${peers.length}`);
  } catch (e) { toast(e.message); }
}

async function setShown(s, shown) {
  try {
    const saved = await api("/api/services", { method: "POST", body: serviceBody(s, { enabled: shown }) });
    config = saved.config;
    renderServices();
    announce(shown ? `${s.name} is shown on the dashboard` : `${s.name} is hidden from the dashboard`);
  } catch (e) { toast(e.message); }
}

async function removeService(s, { fromPanel } = {}) {
  const ok = await confirmDialog({
    title: `Remove ${s.name}?`,
    message: `${s.name} leaves the dashboard${SEARCHABLE.includes(s.type) ? " and Search" : ""}. ${s.name} itself, its files and its settings stay as they are. You can add it again at any time.`,
    confirm: `Remove ${s.name}`, cancel: "Keep it", danger: true,
  });
  if (!ok) return false;
  // Focus goes to the next row's name, or to Add an app when that was the last one.
  const row = $(`#app-sections [data-key="${CSS.escape(s.id)}"]`);
  const next = row?.nextElementSibling || row?.previousElementSibling;
  try {
    config = await api(`/api/services/${s.id}`, { method: "DELETE" });
    fromPanel?.close(false);
    renderServices();
    const target = next?.isConnected ? $(".row__title button", next) : $("#add-service");
    target?.focus();
    toast(`Removed ${s.name}`);
    return true;
  } catch (e) { toast(e.message); return false; }
}

// The add and edit slide-out: Connection first, then Adding options for apps that are searched.

function setOptions(select, items, value, first = "First in the list") {
  select.replaceChildren(el("option", { value: "", text: first }), ...items.map((i) => el("option", { value: i.value, text: i.label })));
  select.value = value ?? "";
}

function guessGroup(name, type) {
  const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const index = config.category_of[slug] ?? config.category_of[type] ?? 3;
  const wanted = config.default_groups[index];
  if (config.groups.includes(wanted)) return wanted;
  return config.groups[index] || config.groups[config.groups.length - 1] || "";
}

function setAddress(s, background) {
  const u = new URL(location.href);
  u.searchParams.delete("add");
  u.searchParams.delete("edit");
  if (s) u.searchParams.set("edit", s.id); else if (background) u.searchParams.set("add", "background");
  history.replaceState(null, "", u);
}

function openService(s = null, opener = null, { background = false } = {}) {
  const isNew = !s;
  let current = s ? { ...s } : null;

  // Step 1: Connection, and how it shows on the dashboard.
  const type = el("select", { class: "select", name: "type" }, Object.entries(config.types).map(([k, v]) => el("option", { value: k, text: v.label })));
  const name = el("input", { class: "input", name: "name", maxlength: "60", required: true, autocomplete: "off" });
  const url = el("input", { class: "input", name: "url", inputmode: "url", placeholder: "http://sonarr:8989", autocomplete: "off" });
  const key = el("input", { class: "input", name: "api_key", type: "password", autocomplete: "off" });
  const keyHint = el("span", {});
  const keyField = field("API key", key, { hint: keyHint, span: true });
  const testButton = el("button", { type: "button", class: "btn" }, icon("zap"), "Test connection");
  const testResult = el("div", { "aria-live": "polite" });

  const groups = [...config.groups];
  if (s?.group && !groups.includes(s.group)) groups.push(s.group);
  const group = el("select", { class: "select", name: "group" }, el("option", { value: "", text: "Choose for me" }), groups.map((g) => el("option", { value: g, text: g })));
  const iconInput = el("input", { class: "input", name: "icon", maxlength: "300", autocomplete: "off" });
  const desc = el("input", { class: "input", name: "description", maxlength: "200" });
  const link = el("input", { class: "input", name: "link", inputmode: "url", autocomplete: "off" });
  const outside = el("input", { class: "input", name: "outside_link", inputmode: "url", placeholder: "https://", autocomplete: "off" });
  const enabled = el("input", { type: "checkbox", name: "enabled", checked: true });
  const bg = el("input", { type: "checkbox", name: "background" });
  const follows = el("select", { class: "select", name: "follows" }, el("option", { value: "", text: "Nothing" }),
    config.services.filter((x) => !x.background && (!s || x.id !== s.id)).map((x) => el("option", { value: x.id, text: x.name })));
  const followsField = field("Status follows", follows, { hint: "For a service with no address: show the status of the app it works with, such as a VPN that qBittorrent runs through.", span: true });
  const formError = el("div", { role: "alert" });

  const form = el("form", { id: "service-form", novalidate: true },
    el("section", { class: "step-section", "aria-labelledby": "svc-conn-h" },
      el("h3", { id: "svc-conn-h", tabindex: "-1", text: "Connection" }),
      el("div", { class: "form-grid" },
        field("Kind of app", type),
        field("Name", name),
        field("Address Starboard uses", url, { hint: "On Docker, the container name and port, such as http://sonarr:8989. Optional for a background service.", span: true }),
        keyField),
      el("div", { class: "actions" }, testButton),
      testResult),
    el("section", { class: "step-section", "aria-labelledby": "svc-show-h" },
      el("h3", { id: "svc-show-h", text: "On the dashboard" }),
      el("div", { class: "form-grid" },
        field("Category", group, { hint: el("span", {}, "The heading it sits under. Change the list in ", el("a", { href: "/settings-general.html#categories", text: "Settings, General" }), "."), span: true }),
        field("Icon", iconInput, { hint: "A name from the dashboard icons collection, such as sonarr, or an address starting with https://. Leave blank to use the name.", span: true }),
        field("Description", desc, { span: true }),
        field("Address to open in your browser", link, { hint: "Leave blank to use the address Starboard uses. Shown on the card as the home address.", span: true }),
        field("Outside address", outside, { hint: "The address that works away from home, such as your own domain. Optional.", span: true })),
      el("div", { class: "switch-list" },
        switchRow("Show on the dashboard", null, enabled),
        switchRow("Background service", "It has no web page, so it is listed under Apps, Other services.", bg)),
      followsField),
    formError);

  const steps = el("ol", { class: "steps", "aria-label": "Steps" }, el("li", { "aria-current": "step", text: "Connection" }), el("li", { text: "Adding options" }));

  if (s) {
    type.value = s.type; name.value = s.name; url.value = s.url || "";
    link.value = s.link === s.url ? "" : (s.link || "");
    outside.value = s.outside_link || ""; iconInput.value = s.icon || "";
    group.value = s.group || ""; desc.value = s.description || "";
    enabled.checked = s.enabled; bg.checked = !!s.background; follows.value = s.follows || "";
  } else if (background) {
    bg.checked = true;
    type.value = "link";
  }

  const saveButton = el("button", { type: "submit", form: "service-form", class: "btn btn--primary" });
  const cancel = el("button", { type: "button", class: "btn btn--quiet", "data-closes": true, text: "Cancel" });
  const remove = s ? el("button", { type: "button", class: "btn btn--danger" }, icon("trash-2"), "Remove", el("span", { class: "visually-hidden", text: ` ${s.name}` })) : null;

  const updateFields = () => {
    const t = type.value;
    keyField.hidden = NO_KEY.includes(t);
    const where = { qbittorrent: "Options, Web UI, API key (version 5.2 or later)", sabnzbd: "Config, General, API Key" }[t] || "Settings, General";
    keyHint.textContent = `In ${config.types[t]?.label || "the app"}: ${where}.${current?.has_api_key ? " Leave blank to keep the saved key; it is never shown again." : ""}`;
    followsField.hidden = !bg.checked;
    group.options[0].textContent = `Choose for me (${guessGroup(name.value, t) || "the last category"})`;
    steps.hidden = !SEARCHABLE.includes(t);
    saveButton.textContent = SEARCHABLE.includes(t) ? "Save and continue" : (isNew ? "Add app" : "Save app");
  };

  const values = () => ({
    id: current?.id, type: type.value, name: name.value, url: url.value, link: link.value, outside_link: outside.value,
    icon: iconInput.value, api_key: key.value, group: group.value, background: bg.checked, follows: bg.checked ? follows.value : "",
    description: desc.value, enabled: enabled.checked,
    quality_profile_id: current?.quality_profile_id ?? null, root_folder: current?.root_folder || "",
    metadata_profile_id: current?.metadata_profile_id ?? null, search_on_add: current ? current.search_on_add !== false : true,
  });

  const panel = sidePanel({
    title: s ? `Edit ${s.name}` : (background ? "Add a background service" : "Add an app"), wide: true, opener,
    body: [steps, form],
    foot: [saveButton, cancel, remove].filter(Boolean),
    onClose: () => {
      setAddress(null, false);
      // Saving redraws the list, so the button that opened the slide-out may be gone: go to the app's new row.
      if (document.activeElement === document.body || !document.activeElement) {
        const row = current && [...document.querySelectorAll("#app-sections [data-key]")].find((n) => n.dataset.key === current.id);
        (row ? $(".row__title button", row) : $("#add-service"))?.focus();
      }
    },
  });
  setAddress(s, background);
  updateFields();

  type.addEventListener("change", updateFields);
  name.addEventListener("input", updateFields);
  bg.addEventListener("change", updateFields);
  remove?.addEventListener("click", () => removeService(current, { fromPanel: panel }));

  testButton.addEventListener("click", async () => {
    testResult.replaceChildren(el("p", { class: "small muted", text: "Testing…" }));
    try {
      const r = await api("/api/services/test", { method: "POST", body: values() });
      testResult.replaceChildren(r.state === "up"
        ? notice("success", "Connected", `${name.value || "The app"}${r.version ? ` ${r.version}` : ""} answered in ${r.ms} ms.`)
        : notice("danger", "Cannot connect", r.message || "Check the address and the API key."));
    } catch (e) {
      testResult.replaceChildren(notice("danger", "Cannot test yet", e.message));
    }
  });

  // Errors from the server go next to the field they are about.
  const showError = (message) => {
    const m = message || "";
    const target = /name for the app/i.test(m) ? name
      : /address the server uses|reach the app/i.test(m) ? url
        : /browser/i.test(m) ? link
          : /outside address/i.test(m) ? outside
            : /icon/i.test(m) ? iconInput : null;
    if (target) { setError(target, m); target.focus(); } else formError.replaceChildren(notice("danger", "Not saved", m));
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formError.replaceChildren();
    [name, url, link, outside, iconInput].forEach((c) => setError(c, ""));
    if (!name.value.trim()) { setError(name, "Enter a name for the app"); name.focus(); return; }
    if (!url.value.trim() && !bg.checked) { setError(url, "Enter the address Starboard uses to reach the app, such as http://sonarr:8989"); url.focus(); return; }
    saveButton.disabled = true;
    try {
      const saved = await api("/api/services", { method: "POST", body: values() });
      config = saved.config;
      current = config.services.find((x) => x.id === saved.id);
      renderServices();
      if (SEARCHABLE.includes(current.type)) showAddingOptions();
      else { panel.close(); toast(isNew ? `${current.name} added` : `${current.name} saved`); }
    } catch (e) {
      showError(e.message);
    } finally {
      saveButton.disabled = false;
    }
  });

  // Step 2: what Starboard uses when you add something from Search.
  async function showAddingOptions() {
    panel.setTitle(isNew ? `Add ${current.name}` : `Edit ${current.name}`);
    setAddress(current, false);
    steps.replaceChildren(el("li", { "data-done": true, text: "Connection" }), el("li", { "aria-current": "step", text: "Adding options" }));
    const quality = el("select", { class: "select", name: "quality_profile_id" });
    const root = el("select", { class: "select", name: "root_folder" });
    const meta = el("select", { class: "select", name: "metadata_profile_id" });
    const searchOnAdd = el("input", { type: "checkbox", name: "search_on_add", checked: current.search_on_add !== false });
    const kind = { sonarr: "every episode", radarr: "the film", lidarr: "every album", readarr: "every book" }[current.type];
    setOptions(quality, current.quality_profile_id ? [{ value: current.quality_profile_id, label: `Profile ${current.quality_profile_id}` }] : [], current.quality_profile_id);
    setOptions(root, current.root_folder ? [{ value: current.root_folder, label: current.root_folder }] : [], current.root_folder);
    setOptions(meta, current.metadata_profile_id ? [{ value: current.metadata_profile_id, label: `Profile ${current.metadata_profile_id}` }] : [], current.metadata_profile_id);
    const loadState = el("div", { "aria-live": "polite" }, el("p", { class: "small muted", text: `Loading profiles and folders from ${current.name}…` }));
    const metaField = field("Metadata profile", meta);
    metaField.hidden = !["lidarr", "readarr"].includes(current.type);
    const heading = el("h3", { id: "svc-add-h", tabindex: "-1", text: "Adding options" });
    const optionsForm = el("form", { id: "options-form", novalidate: true },
      notice("success", `${current.name} saved`, "Now choose what Starboard uses when you add something from Search."),
      el("section", { class: "step-section", "aria-labelledby": "svc-add-h" },
        heading,
        loadState,
        el("div", { class: "form-grid" }, field("Quality profile", quality), field("Folder", root), metaField),
        el("div", { class: "switch-list" }, switchRow("Search as soon as something is added", `On: ${current.name} looks for ${kind} straight away.`, searchOnAdd))));
    form.replaceWith(optionsForm);
    const saveOptions = el("button", { type: "submit", form: "options-form", class: "btn btn--primary", text: "Save adding options" });
    panel.setFoot([saveOptions, el("button", { type: "button", class: "btn btn--quiet", "data-closes": true, text: "Skip for now" })]);
    heading.focus();
    optionsForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      saveOptions.disabled = true;
      try {
        const saved = await api("/api/services", { method: "POST", body: serviceBody(current, {
          quality_profile_id: quality.value || null, root_folder: root.value,
          metadata_profile_id: meta.value || null, search_on_add: searchOnAdd.checked,
        }) });
        config = saved.config;
        renderServices();
        panel.close();
        toast(`${current.name} saved`);
      } catch (e) {
        loadState.replaceChildren(notice("danger", "Not saved", e.message));
      } finally {
        saveOptions.disabled = false;
      }
    });
    try {
      const opts = await api(`/api/services/${current.id}/options`);
      setOptions(quality, opts.quality_profiles.map((p) => ({ value: p.id, label: p.name })), current.quality_profile_id);
      setOptions(root, opts.root_folders.map((r) => ({ value: r.path, label: r.path })), current.root_folder);
      setOptions(meta, opts.metadata_profiles.map((p) => ({ value: p.id, label: p.name })), current.metadata_profile_id);
      loadState.replaceChildren();
    } catch (e) {
      loadState.replaceChildren(notice("warning", "Could not load the profiles and folders", `${e.message}. Starboard uses the first in each list until you choose.`));
    }
  }
  return panel;
}

function startManageApps() {
  // Old links to sections of the single Settings page go to their own pages now.
  const MOVED = { "#general": "/settings-general.html", "#security": "/settings-security.html", "#updates": "/settings-updates.html" };
  if (MOVED[location.hash]) { location.replace(MOVED[location.hash]); return; }
  renderServices();
  $("#add-service").addEventListener("click", (e) => openService(null, e.currentTarget));
  // Other pages link here: ?edit=<app id> opens that app; ?add=background starts a background service.
  const params = new URLSearchParams(location.search);
  const editId = params.get("edit");
  const editing = editId && config.services.find((s) => s.id === editId);
  if (editing) openService(editing, $(`#app-sections [data-key="${CSS.escape(editing.id)}"] .row__title button`));
  else if (editId) { setAddress(null, false); toast("That app is not in your list any more"); }
  else if (params.get("add") === "background") openService(null, $("#add-service"), { background: true });
  else if (params.has("add") || !config.services.length) openService(null, $("#add-service"));
  loadStatus();
}

// General -------------------------------------------------------------------

function countIn(group) { return config.services.filter((s) => s.group === group).length; }
function appsWord(n) { return `${n} ${n === 1 ? "app" : "apps"}`; }

// Categories are saved as a list of names, and each app keeps its category's name. Renaming or removing one
// also moves the apps in it, one save per app.
async function moveApps(from, to) {
  for (const s of config.services.filter((x) => x.group === from)) {
    const saved = await api("/api/services", { method: "POST", body: serviceBody(s, { group: to }) });
    config = saved.config;
  }
}

function categoryRow(name, index, list) {
  const n = countIn(name);
  const items = [];
  if (index > 0) items.push({ label: "Move up", icon: "arrow-up", onSelect: () => later(() => moveCategory(index, -1)) });
  if (index < list.length - 1) items.push({ label: "Move down", icon: "arrow-down", onSelect: () => later(() => moveCategory(index, 1)) });
  if (list.length > 1) items.push({ label: "Remove", icon: "trash-2", danger: true, onSelect: () => later(() => removeCategory(name)) });
  return el("li", { class: "row" },
    el("span", { class: "app-icon", "aria-hidden": "true", text: String(index + 1) }),
    el("div", { class: "row__text" }, el("div", { class: "row__title", text: name }), el("div", { class: "row__meta", text: n ? appsWord(n) : "No apps yet" })),
    el("div", { class: "row__side" },
      el("button", { type: "button", class: "btn", onclick: () => renameCategory(name) }, icon("pencil"), "Rename", el("span", { class: "visually-hidden", text: ` ${name}` })),
      menuButton(`More actions for ${name}`, items)));
}

function renderCategories() {
  const groups = config.groups;
  redraw($("#category-list"), groups.map((g, i) => {
    const row = categoryRow(g, i, groups);
    row.dataset.key = g;
    return row;
  }));
  $("#category-add").disabled = groups.length >= 20;
  // Apps can sit in a category that is not in the list (from an older version or a restore). The Apps page
  // shows those after the listed ones; offer to add them so they can be renamed and ordered here.
  const loose = [...new Set(config.services.filter((s) => !s.background && s.group && !groups.includes(s.group)).map((s) => s.group))];
  const box = $("#category-loose");
  box.replaceChildren();
  if (loose.length) {
    const add = el("button", { type: "button", class: "btn btn--compact" }, icon("plus"), loose.length === 1 ? "Add it to the list" : "Add them to the list");
    add.addEventListener("click", async () => {
      if (await saveGroups([...config.groups, ...loose].slice(0, 20), `Added ${loose.join(", ")}`)) $("#category-list .btn")?.focus();
    });
    box.append(notice("info", loose.length === 1 ? "1 more category is in use" : `${loose.length} more categories are in use`,
      `Some apps are in ${loose.join(", ")}, which ${loose.length === 1 ? "is" : "are"} not in this list. The Apps page shows ${loose.length === 1 ? "it" : "them"} after the categories here.`, add));
  }
}

async function saveGroups(groups, message) {
  try {
    await saveGeneral({ groups }, null);
    renderCategories();
    if (message) announce(message);
    return true;
  } catch (e) { toast(e.message); return false; }
}

async function moveCategory(index, by) {
  const groups = [...config.groups];
  [groups[index], groups[index + by]] = [groups[index + by], groups[index]];
  await saveGroups(groups, `${groups[index + by]} moved ${by < 0 ? "up" : "down"}, now ${index + by + 1} of ${groups.length}`);
}

async function renameCategory(name) {
  const input = el("input", { class: "input", maxlength: "40", required: true, value: name, autocomplete: "off" });
  const n = countIn(name);
  const ok = await confirmDialog({
    title: `Rename ${name}`,
    message: n ? `The ${appsWord(n)} in it move with it.` : "No apps are in it yet.",
    fields: [field("New name", input)],
    confirm: "Rename category",
  });
  const to = input.value.trim();
  if (!ok || !to || to === name) return;
  if (config.groups.includes(to)) { toast(`There is already a category called ${to}`); return; }
  if (!(await saveGroups(config.groups.map((g) => (g === name ? to : g))))) return;
  try {
    await moveApps(name, to);
    renderCategories();
    toast(`Renamed ${name} to ${to}`);
  } catch (e) { toast(`Renamed, but some apps were not moved: ${e.message}`); }
  $(`#category-list [data-key="${CSS.escape(to)}"] .btn`)?.focus();
}

async function removeCategory(name) {
  const n = countIn(name);
  const others = config.groups.filter((g) => g !== name);
  const to = el("select", { class: "select" }, others.map((g) => el("option", { value: g, text: g })));
  const ok = await confirmDialog({
    title: `Remove the ${name} category?`,
    message: n ? `${appsWord(n)} ${n === 1 ? "is" : "are"} in ${name}. Choose where ${n === 1 ? "it goes" : "they go"}. The apps themselves are not changed.` : "No apps are in it. Nothing else changes.",
    fields: n ? [field("Move its apps to", to)] : [],
    confirm: "Remove category", cancel: "Keep it", danger: true,
  });
  if (!ok) return;
  const row = $(`#category-list [data-key="${CSS.escape(name)}"]`);
  const next = row?.nextElementSibling || row?.previousElementSibling;
  try {
    if (n) await moveApps(name, to.value);
  } catch (e) { toast(`Not removed: ${e.message}`); return; }
  if (await saveGroups(others)) {
    toast(n ? `Removed ${name}. Its apps are now in ${to.value}` : `Removed ${name}`);
    (next?.isConnected ? $(".btn", next) : $("#category-name"))?.focus();
  }
}

function startGeneral() {
  // Dashboard name
  const siteName = el("input", { class: "input", name: "site_name", maxlength: "60", required: true, value: config.site_name });
  const nameForm = el("form", { novalidate: true }, field("Dashboard name", siteName, { short: true }),
    el("div", { class: "actions" }, el("button", { type: "submit", class: "btn btn--primary", text: "Save name" })));
  nameForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    setError(siteName, "");
    if (!siteName.value.trim()) { setError(siteName, "Enter a name for the dashboard"); siteName.focus(); return; }
    try {
      await saveGeneral({ site_name: siteName.value }, "Name saved");
      document.title = document.title.replace(/ · [^·]*$/, ` · ${config.site_name}`);
    } catch (err) { setError(siteName, err.message); siteName.focus(); }
  });

  // Categories
  const newName = el("input", { class: "input", id: "category-name", maxlength: "40", placeholder: "For example: Home", autocomplete: "off" });
  const addForm = el("form", { class: "add-row", novalidate: true }, field("New category", newName),
    el("button", { type: "submit", class: "btn", id: "category-add" }, icon("plus"), "Add category"));
  addForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    setError(newName, "");
    const value = newName.value.trim();
    if (!value) { setError(newName, "Enter a name for the category"); newName.focus(); return; }
    if (config.groups.includes(value)) { setError(newName, `There is already a category called ${value}`); newName.focus(); return; }
    if (await saveGroups([...config.groups, value], `Added ${value}`)) newName.value = "";
  });

  // App cards: switches that apply at once.
  const cardSwitch = (key, labelId, on, off) => {
    const input = el("input", { type: "checkbox", role: "switch", "aria-labelledby": labelId, checked: config[key] });
    input.addEventListener("change", async () => {
      try { await saveGeneral({ [key]: input.checked }, input.checked ? on : off); }
      catch (err) { input.checked = !input.checked; toast(err.message); }
    });
    return el("label", { class: "switch" }, input);
  };

  // Default design
  const designForm = el("form", {},
    el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Default design" }),
      el("div", { class: "option-cards" }, Object.entries(DESIGNS).map(([k, [label, help]]) => el("label", { class: "option-card" },
        el("input", { type: "radio", name: "design", value: k, checked: config.design === k }), el("strong", { text: label }), el("small", { text: help }))))),
    el("div", { class: "actions" }, el("button", { type: "submit", class: "btn btn--primary", text: "Save default design" })));
  designForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    try { await saveGeneral({ design: designForm.design.value }, `Default design saved: ${DESIGNS[designForm.design.value][0]}`); }
    catch (err) { toast(err.message); }
  });

  // Coming up: selects that apply at once.
  const upcomingSelect = (key, labelId, options, message) => {
    const select = el("select", { class: "select", "aria-labelledby": labelId },
      options.map(([value, label]) => el("option", { value: String(value), text: label, selected: String(config[key]) === String(value) })));
    select.addEventListener("change", async () => {
      const before = config[key];
      try { await saveGeneral({ [key]: key === "upcoming_days" ? Number(select.value) : select.value }, message(select.selectedOptions[0].text)); }
      catch (err) { select.value = String(before); toast(err.message); }
    });
    return select;
  };
  const dayChoices = (config.upcoming_days_choices || [7, 14, 30, 60, 90]).map((n) => [n, n === 7 ? "1 week" : n === 14 ? "2 weeks" : `${n} days`]);

  // Download hours: a switch and two selects, each applying at once.
  const hoursList = Array.from({ length: 24 }, (_, h) => [h, `${String(h).padStart(2, "0")}:00`]);
  const hoursSelect = (key, labelId) => {
    const select = el("select", { class: "select", "aria-labelledby": labelId },
      hoursList.map(([h, label]) => el("option", { value: String(h), text: label, selected: config.download_hours[key] === h })));
    select.addEventListener("change", async () => {
      const before = config.download_hours[key];
      try {
        await saveGeneral({ download_hours: { [key]: Number(select.value) } },
          `Downloads now run from ${hoursText(config.download_hours.start)} to ${hoursText(config.download_hours.end)}`);
      } catch (err) { select.value = String(before); toast(err.message); }
    });
    return select;
  };
  const hoursText = (h) => `${String(h).padStart(2, "0")}:00`;
  const hoursOn = el("input", { type: "checkbox", role: "switch", "aria-labelledby": "dh-on-l", checked: config.download_hours.enabled });
  hoursOn.addEventListener("change", async () => {
    try {
      await saveGeneral({ download_hours: { enabled: hoursOn.checked } }, hoursOn.checked
        ? `Download hours on: downloads run from ${hoursText(config.download_hours.start)} to ${hoursText(config.download_hours.end)}`
        : "Download hours off: downloads run at any time");
    } catch (err) { hoursOn.checked = !hoursOn.checked; toast(err.message); }
  });
  const clients = config.services.filter((s) => ["qbittorrent", "sabnzbd"].includes(s.type) && s.has_api_key);

  $("#general-sections").removeAttribute("aria-busy");
  $("#general-sections").replaceChildren(
    section("gn-name", "Dashboard", "Shown in the header and the browser tab.", nameForm),
    el("div", { id: "categories" }, section("gn-cat", "Categories", "The headings apps sit under on the Apps page, in this order. Changes apply at once.",
      el("ul", { class: "rows", id: "category-list" }), el("div", { id: "category-loose" }), addForm)),
    section("gn-card", "App cards", "What everyone sees on each card. These apply at once.",
      el("ul", { class: "settings-rows" },
        settingRow("Home address", "With a copy button.", cardSwitch("show_home_address", "card-home-l", "Cards now show the home address", "Cards no longer show the home address"), "card-home-l"),
        settingRow("Outside address", "With a copy button, when the app has one.", cardSwitch("show_outside_address", "card-out-l", "Cards now show the outside address", "Cards no longer show the outside address"), "card-out-l"))),
    el("div", { id: "coming-up" }, section("gn-up", "Coming up", "What the Coming up page shows. These apply at once.",
      el("ul", { class: "settings-rows" },
        settingRow("View", "List shows releases by day; Calendar shows them on a month. The switch on the page changes this too.",
          upcomingSelect("upcoming_view", "up-view-l", [["list", "List"], ["calendar", "Calendar"]], (t) => `Coming up now opens as ${t === "List" ? "a list" : "a calendar"}`), "up-view-l"),
        settingRow("How far ahead", "Releases from today to this far ahead, plus yesterday's.",
          upcomingSelect("upcoming_days", "up-days-l", dayChoices, (t) => `Coming up now looks ${t} ahead`), "up-days-l")))),
    el("div", { id: "download-hours" }, section("gn-dh", "Download hours", "Starboard pauses qBittorrent and SABnzbd outside these hours, in the server's local time, and starts again only what it paused. Seeding is left alone. These apply at once.",
      clients.length ? null : notice("info", "No download apps yet", "Add qBittorrent or SABnzbd with its API key in Manage apps, so Starboard can pause and resume them."),
      el("ul", { class: "settings-rows" },
        settingRow("Only download between set hours", "Off: downloads run at any time.", el("label", { class: "switch" }, hoursOn), "dh-on-l"),
        settingRow("Start", "Downloads start at this hour.", hoursSelect("start", "dh-start-l"), "dh-start-l"),
        settingRow("End", "Downloads pause at this hour. An end before the start runs overnight.", hoursSelect("end", "dh-end-l"), "dh-end-l")))),
    section("gn-design", "Default design", "Everyone sees this unless they choose their own in Display.", designForm));
  renderCategories();
  if (["#categories", "#coming-up", "#download-hours"].includes(location.hash)) $(location.hash).scrollIntoView();
}

// Security ------------------------------------------------------------------

async function startSecurity() {
  // Who can open the dashboard
  const access = el("input", { type: "checkbox", role: "switch", "aria-labelledby": "net-l", "aria-describedby": "net-result" });
  const result = el("span", { id: "net-result" });
  const addresses = el("ul", { class: "network-addresses", "aria-label": "Addresses that open Starboard" });
  const forced = el("p", { class: "small muted", hidden: true });
  let network;
  const showNetwork = () => {
    access.checked = network.network_access;
    result.textContent = network.network_access
      ? "On: phones and other computers on your home network can reach the sign-in page."
      : "Off: only the computer Starboard runs on can open it.";
    const rows = [["This computer", `http://localhost:${network.port}`]];
    if (network.network_access) for (const a of network.addresses) rows.push(["Phones and other computers", `http://${a}:${network.port}`]);
    addresses.replaceChildren(...rows.map(([label, u]) => el("li", {}, `${label}: `, el("code", { text: u }))));
    if (network.forced_by) {
      access.disabled = true;
      forced.hidden = false;
      forced.textContent = `Set by ${network.forced_by} on the server, so it cannot be changed here.`;
    }
  };
  try { network = await api("/api/network"); }
  catch { network = { network_access: config.network_access, addresses: [], port: location.port || 80, you_are_on_this_computer: false }; }
  access.addEventListener("change", async () => {
    const want = access.checked;
    if (!want) {
      access.checked = true;
      const ok = await confirmDialog({
        title: "Turn off access from your home network?",
        message: network.you_are_on_this_computer
          ? el("p", { text: "Phones and other computers lose access straight away. Only this computer, the server, can open Starboard after this." })
          : notice("warning", "You are using another device", "This phone or computer loses access straight away. Only the server itself can open Starboard after this."),
        confirm: "Turn off network access", cancel: "Keep it on", danger: true,
      });
      if (!ok) { access.focus(); return; }
      access.checked = false;
    }
    try {
      await saveGeneral({ network_access: want }, want ? "Other devices on your home network can open Starboard now" : "Only this computer can open Starboard now");
      network.network_access = want;
      showNetwork();
      setTimeout(async () => { try { network = await api("/api/network"); showNetwork(); } catch { /* this device lost access */ } }, 1500);
    } catch (e) { access.checked = !want; toast(e.message); }
  });

  // Password
  const current = el("input", { class: "input", type: "password", autocomplete: "current-password", required: true });
  const fresh = el("input", { class: "input", type: "password", autocomplete: "new-password", required: true });
  const again = el("input", { class: "input", type: "password", autocomplete: "new-password", required: true });
  const pwForm = el("form", { novalidate: true },
    el("div", { class: "form-grid" },
      el("div", { "data-span": "all", class: "field--short" }, field("Current password", current)),
      field("New password", fresh),
      field("Type the new password again", again)),
    el("div", { class: "actions" }, el("button", { type: "submit", class: "btn btn--primary", text: "Change password" })));
  pwForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    [current, fresh, again].forEach((c) => setError(c, ""));
    if (!current.value) { setError(current, "Enter your current password"); current.focus(); return; }
    if (fresh.value.length < 10) { setError(fresh, `Use at least 10 characters. This one has ${fresh.value.length}.`); fresh.focus(); return; }
    if (fresh.value !== again.value) { setError(again, "The two new passwords are different. Type the new one again."); again.focus(); return; }
    try {
      await postKeepingPage("/api/password", { current: current.value, new: fresh.value });
      pwForm.reset();
      toast("Password changed. Everyone else is signed out");
    } catch (err) {
      if (err.status === 401 || err.status === 429) { setError(current, err.message); current.focus(); }
      else { setError(fresh, err.message); fresh.focus(); }
    }
  });

  // Sessions
  const days = el("input", { class: "input", inputmode: "numeric", "aria-labelledby": "days-l", "aria-describedby": "days-h", value: String(config.session_days) });
  const daysError = el("span", { class: "field-error", id: "days-e", hidden: true });
  const secure = el("input", { type: "checkbox", role: "switch", "aria-labelledby": "secure-l", "aria-describedby": "secure-h", checked: config.secure_cookies });
  secure.addEventListener("change", async () => {
    try { await saveGeneral({ secure_cookies: secure.checked }, secure.checked ? "The sign-in cookie is now only sent over HTTPS" : "The sign-in cookie is sent over HTTP and HTTPS"); }
    catch (err) { secure.checked = !secure.checked; toast(err.message); }
  });
  const daysForm = el("form", { novalidate: true, id: "session-form" });
  daysForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    daysError.hidden = true;
    days.removeAttribute("aria-invalid");
    days.setAttribute("aria-describedby", "days-h");
    const fail = (m) => {
      daysError.replaceChildren(icon("circle-alert"), el("span", { text: m }));
      daysError.hidden = false;
      days.setAttribute("aria-invalid", "true");
      days.setAttribute("aria-describedby", "days-h days-e");
      days.focus();
    };
    const n = Number(days.value);
    if (!Number.isInteger(n) || n < 1 || n > 90) { fail("Enter a whole number of days from 1 to 90"); return; }
    try { await saveGeneral({ session_days: n }, `Remember me now lasts ${n} ${n === 1 ? "day" : "days"}`); }
    catch (err) { fail(err.message); }
  });
  const everywhere = el("button", { type: "button", class: "btn btn--danger", text: "Sign out everywhere" });
  everywhere.addEventListener("click", async () => {
    const ok = await confirmDialog({
      title: "Sign out everywhere?",
      message: "Every browser and phone signed in to Starboard is signed out, including this one. Everyone needs the password to sign in again.",
      confirm: "Sign out everywhere", cancel: "Stay signed in", danger: true,
    });
    if (!ok) return;
    try { await api("/api/sessions/end-all", { method: "POST" }); } catch { /* signed out anyway */ }
    location.href = "/login.html";
  });
  const signOut = el("button", { type: "button", class: "btn" }, icon("log-out"), "Sign out");
  signOut.addEventListener("click", async () => {
    await api("/api/logout", { method: "POST" }).catch(() => {});
    location.href = "/login.html";
  });

  $("#security-sections").removeAttribute("aria-busy");
  $("#security-sections").replaceChildren(
    section("sc-who", "Who can open the dashboard", "When this is off, only the computer Starboard runs on can open it.",
      el("ul", { class: "settings-rows" },
        settingRow("Phones and other computers on your home network", result, el("label", { class: "switch" }, access), "net-l")),
      addresses, forced),
    section("sc-pw", "Password", "At least 10 characters; a short sentence is easy to remember. You stay signed in here and everyone else is signed out.", pwForm),
    section("sc-ses", "Sessions", "How long Remember me lasts, and signing out.", daysForm));
  daysForm.append(
      el("ul", { class: "settings-rows" },
        el("li", { class: "setting" },
          el("div", { class: "setting__text" }, el("span", { class: "setting__label", id: "days-l", text: "Remember me keeps people signed in for" }),
            el("span", { class: "setting__hint", id: "days-h", text: "1 to 90 days. Without Remember me, people are signed out when they close the browser, or after a day." })),
          el("div", { class: "setting__control" }, el("div", { class: "field" },
            el("div", { class: "input-group days-group" }, days, el("span", { class: "input-group__unit", text: "days" })), daysError))),
        settingRow("Only send the sign-in cookie over HTTPS", el("span", { id: "secure-h", text: "Turn on when every address you use starts with https. This applies at once." }), el("label", { class: "switch" }, secure), "secure-l")),
      el("div", { class: "actions session-actions" },
        el("button", { type: "submit", class: "btn btn--primary", text: "Save how long" }), signOut, everywhere));
  showNetwork();
}

// About and updates -----------------------------------------------------------

async function startAbout() {
  const top = $("#version-notice");
  const check = el("input", { type: "checkbox", role: "switch", "aria-labelledby": "check-l", "aria-describedby": "check-h", checked: config.update_check });
  let v = null;
  const showVersion = () => {
    if (!v) return;
    const latest = (v.latest || "").replace(/^v/, "");
    const repo = /^[\w.-]+\/[\w.-]+$/.test(v.repo || "") ? v.repo : "";
    const notes = repo && v.latest ? el("a", { class: "btn btn--compact", href: `https://github.com/${repo}/releases/tag/${encodeURIComponent(v.latest)}`, target: "_blank", rel: "noopener noreferrer" },
      "Release notes", el("span", { class: "visually-hidden", text: " (opens in a new tab)" })) : null;
    let box;
    if (latest && latest !== v.current) box = notice("info", `Version ${latest} is out`, `You have ${v.current}. Read what changed, then run the update command on the server.`, notes);
    else if (latest) box = notice("success", "You have the newest version", `Version ${v.current}.`);
    else if (!repo) box = notice("info", `You have version ${v.current}`, "Starboard cannot look for new versions, because STARBOARD_REPO is not set on the server.");
    else if (!config.update_check) box = notice("info", `You have version ${v.current}`, "Looking for new versions is off. Turn it on below to see when one is out.");
    else box = notice("info", `You have version ${v.current}`, "GitHub did not answer, so Starboard does not know yet whether a newer version is out.");
    box.classList.add("notice--page");
    top.replaceChildren(box);
    const facts = $("#about-facts");
    facts.replaceChildren(el("dt", { text: "Version" }), el("dd", { class: "numeric", text: v.current }));
    if (repo) facts.append(el("dt", { text: "Source code" }), el("dd", {}, el("a", { href: `https://github.com/${repo}`, target: "_blank", rel: "noopener noreferrer" }, "Starboard on GitHub", el("span", { class: "visually-hidden", text: " (opens in a new tab)" }))));
  };
  check.addEventListener("change", async () => {
    try {
      await saveGeneral({ update_check: check.checked }, check.checked ? "Starboard looks for new versions" : "Starboard no longer looks for new versions");
      v = await api("/api/version");
      showVersion();
    } catch (e) { check.checked = !check.checked; toast(e.message); }
  });
  $("#update-check-row").replaceChildren(settingRow("Check GitHub for new releases", el("span", { id: "check-h", text: "On: Starboard checks every 6 hours at most and shows a notice at the top." }), el("label", { class: "switch" }, check), "check-l"));
  $("#update-command").append(copyButton("./update.sh", "the update command"));
  try { v = await api("/api/version"); } catch { /* no notice */ }
  showVersion();
}

startPage().then(async (session) => {
  if (!session) return;
  try { config = await api("/api/config"); } catch (e) { toast(e.message); return; }
  if ($("#app-sections")) startManageApps();
  if ($("#general-sections")) startGeneral();
  if ($("#security-sections")) startSecurity();
  if ($("#version-notice")) startAbout();
});
