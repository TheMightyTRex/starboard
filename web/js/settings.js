// Settings: Manage apps (add, edit, test, order, hide, remove), General, Security, and About and updates.
// Each page has its own start function below; the page's markup says which one runs.

let config = null;
const SEARCHABLE = ["sonarr", "radarr", "lidarr", "readarr"];
const NO_KEY = ["link"];

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

// The app's state as an icon beside its name: a tick, a cross or a dashed circle, never colour alone, with the
// words in hidden text and in the tooltip.
function statusIcon(s) {
  const st = statusById[s.id];
  const [words, tone, name] = !s.enabled ? ["Hidden from the dashboard", "muted", "eye-off"]
    : !st ? ["Checking", "muted", "circle"]
    : st.state === "up" ? [s.background ? "Running" : "Connected", "success", "circle-check"]
    : st.state === "down" ? [s.background ? "Not running" : "Cannot connect", "danger", "circle-x"]
    : ["Not checked", "muted", "circle-help"];
  return el("span", { class: "status-icon", "data-tone": tone, title: words }, icon(name), el("span", { class: "visually-hidden", text: `, ${words}` }));
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
      el("div", { class: "row__title" }, el("button", { type: "button", onclick: (e) => openService(s, e.currentTarget) }, s.name, statusIcon(s))),
      el("div", { class: "row__meta", text: serviceMeta(s) })),
    el("div", { class: "row__side" },
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

function openService(s = null, opener = null, { background = false, preset = null } = {}) {
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
  // Container for Updates: filled from Docker when Starboard has access; otherwise the field stays hidden.
  const container = el("select", { class: "select", name: "container" }, el("option", { value: "", text: "Find it by name" }));
  const containerField = field("Container", container, { hint: "The container this app runs in, for Apps, Updates. Starboard finds it by the app's name unless you choose one.", span: true });
  containerField.hidden = true;
  api("/api/containers").then((d) => {
    if (!d.available) return;
    const names = new Set(d.containers);
    if (s?.container) names.add(s.container);
    container.append(...[...names].sort().map((n) => el("option", { value: n, text: n })));
    container.value = s?.container || "";
    containerField.hidden = false;
  }).catch(() => {});

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
        field("Outside address", outside, { hint: "The address that works away from home, such as your own domain. Optional.", span: true }),
        containerField),
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
  } else if (preset) {
    type.value = preset.type; name.value = preset.name; url.value = preset.url;
  }

  const saveButton = el("button", { type: "submit", form: "service-form", class: "btn btn--primary" });
  const cancel = el("button", { type: "button", class: "btn btn--quiet", "data-closes": true, text: "Cancel" });
  const remove = s ? el("button", { type: "button", class: "btn btn--danger" }, icon("trash-2"), "Remove", el("span", { class: "visually-hidden", text: ` ${s.name}` })) : null;

  const updateFields = () => {
    const t = type.value;
    keyField.hidden = NO_KEY.includes(t);
    const where = { qbittorrent: "Options, Web UI, API key (version 5.2 or later)", sabnzbd: "Config, General, API Key",
      jellyfin: "Dashboard, API keys. Optional: it adds Jellyfin's state, what is playing and recently added to System" }[t] || "Settings, General";
    keyHint.textContent = `In ${config.types[t]?.label || "the app"}: ${where}.${current?.has_api_key ? " Leave blank to keep the saved key; it is never shown again." : ""}`;
    followsField.hidden = !bg.checked;
    group.options[0].textContent = `Choose for me (${guessGroup(name.value, t) || "the last category"})`;
    steps.hidden = !SEARCHABLE.includes(t);
    saveButton.textContent = SEARCHABLE.includes(t) ? "Save and continue" : (isNew ? "Add app" : "Save app");
  };

  const values = () => ({
    id: current?.id, type: type.value, name: name.value, url: url.value, link: link.value, outside_link: outside.value,
    icon: iconInput.value, api_key: key.value, group: group.value, background: bg.checked, follows: bg.checked ? follows.value : "",
    description: desc.value, enabled: enabled.checked, container: container.value,
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
  else if (params.get("add") === "jellyfin") openService(null, $("#add-service"), { preset: { type: "jellyfin", name: "Jellyfin", url: params.get("url") || "" } });
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
    const add = el("button", { type: "button", class: "btn" }, icon("plus"), loose.length === 1 ? "Add it to the list" : "Add them to the list");
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
  const nameForm = el("form", { novalidate: true, class: "inline-save" }, field("Dashboard name", siteName),
    el("button", { type: "submit", class: "btn btn--primary", text: "Save name" }));
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
        settingRow("How far ahead", withCost("Releases from today to this far ahead, plus yesterday's.", "upcoming"),
          upcomingSelect("upcoming_days", "up-days-l", dayChoices, (t) => `Coming up now looks ${t} ahead`), "up-days-l")))),
    el("div", { id: "download-hours" }, section("gn-dh", "Download hours", "Starboard pauses qBittorrent and SABnzbd outside these hours, in the server's local time, and starts again only what it paused. Seeding is left alone. These apply at once.",
      clients.length ? null : notice("info", "No download apps yet", "Add qBittorrent or SABnzbd with its API key in Manage apps, so Starboard can pause and resume them."),
      el("ul", { class: "settings-rows" },
        settingRow("Only download between set hours", withCost("Off: downloads run at any time.", "hours"), el("label", { class: "switch" }, hoursOn), "dh-on-l"),
        settingRow("Start", "Downloads start at this hour.", hoursSelect("start", "dh-start-l"), "dh-start-l"),
        settingRow("End", "Downloads pause at this hour. An end before the start runs overnight.", hoursSelect("end", "dh-end-l"), "dh-end-l")))),
    section("gn-design", "Default design", "Everyone sees this unless they choose their own in Display.", designForm));
  renderCategories();
  if (["#categories", "#coming-up", "#download-hours"].includes(location.hash)) $(location.hash).scrollIntoView();
}

// What Starboard can access: a row per kind of access, with a switch, a link or the installer command.
async function renderAccess() {
  const list = $("#access-rows");
  let items;
  try { items = (await api("/api/access")).items; } catch (e) { list.replaceChildren(el("li", { class: "setting", text: e.message })); return; }
  // On or off as an icon beside the name: a tick or an empty ring (never colour alone), with the word in
  // hidden text and in the tooltip. Rows with a switch show their state in the switch itself.
  const stateIcon = (on) => el("span", { class: "status-icon", "data-tone": on ? "success" : "muted", title: on ? "On" : "Off" },
    icon(on ? "circle-check" : "circle"), el("span", { class: "visually-hidden", text: on ? ", on" : ", off" }));
  const row = (a, control, withIcon) => {
    const labelId = `acc-${a.key}-l`;
    return el("li", { class: "setting" },
      el("div", { class: "setting__text" },
        el("span", { class: "setting__label", id: labelId }, a.title, withIcon ? stateIcon(a.on) : null),
        el("span", { class: "setting__hint" }, a.what, a.cost ? el("span", { class: "setting__cost", text: `Costs about: ${a.cost[0].toLowerCase()}${a.cost.slice(1)}` }) : null)),
      el("div", { class: "setting__control" }, control));
  };
  list.replaceChildren(...items.map((a) => {
    if (a.change === "setting" && a.setting && a.setting !== "update_check") {
      const input = el("input", { type: "checkbox", role: "switch", "aria-labelledby": `acc-${a.key}-l`, checked: config[a.setting] });
      input.addEventListener("change", async () => {
        try { await saveGeneral({ [a.setting]: input.checked }, `${a.title}: ${input.checked ? "on" : "off"}`); }
        catch (err) { input.checked = !input.checked; toast(err.message); }
      });
      return row(a, el("label", { class: "switch" }, input), false);
    }
    if (a.change === "installer") {
      const command = `./install.sh ${a.on ? a.off_flag : a.on_flag}`;
      return row(a, el("div", { class: "access-change" },
        el("span", { class: "small", text: a.on ? "To turn it off, run on the server:" : "To turn it on, run on the server:" }),
        el("div", { class: "command" }, el("code", { class: "code-block", text: command }), copyButton(command, `the command for ${a.title}`))), true);
    }
    if (a.change === "readme") {
      return row(a, el("span", { class: "small access-change", text: "Set up by hand: see Backup and restore in the README." }), true);
    }
    const where = a.link?.startsWith("#") ? null : a.link;
    return row(a, where ? el("a", { class: "btn", href: where }, a.change === "apps" ? "Manage apps" : "Change it", el("span", { class: "visually-hidden", text: ` for ${a.title}` }))
      : el("span", { class: "small access-change", text: "Use the switch above" }), true);
  }));
  list.removeAttribute("aria-busy");
  if (location.hash === "#access") $("#access").scrollIntoView();
}

// What a setting costs on the server, measured on a home server in November 2026 (an 8-core processor, about
// 10,000 films and episodes). Shown under each switch that uses processor time or memory, so a small server
// can keep only what it needs. Idle Starboard: about 19 MB and 0.01% of the processor.
const COSTS = {
  hours: "Costs about: one small check a minute, under 0.01% of the processor, no extra memory.",
  upcoming: "Costs about: one request to each app when Coming up opens, kept for 10 minutes. Further ahead means a bigger answer, still well under a second.",
  watch: "Costs about: 0.02 seconds of processor per check (every 5 minutes, under 0.01% overall) and under 1 MB of memory for the history. Off saves that, and keeps nothing running in the background.",
  every: "Every minute costs five times as much as every 5 minutes; every hour, a twelfth.",
  weekly: "Costs about: one message a week. Nothing noticeable.",
  livetv: "Costs about: under 2 seconds of processor a day to refresh the guides, and about a minute once a week (or when a channel list changes) to test every stream, using up to 35 MB more memory while it runs. Nothing in between. Off saves all of that.",
  white: "Costs about: only when new channels arrive, a second or two per logo and up to 15 MB more memory while it runs. Off saves that; logos already made stay.",
  importKeep: "Costs about: 1 second of processor and up to 40 MB more memory for about 20 seconds an hour, while it reads your Jellyfin library. Off saves that; Apply now still works.",
  defaults: "Costs about: two small requests per Jellyfin user an hour. Nothing noticeable.",
};

function withCost(hint, key) {
  return el("span", {}, hint, el("span", { class: "setting__cost", text: COSTS[key] }));
}

// Alerts --------------------------------------------------------------------

function startAlerts() {
  const w = () => config.watch;
  const save = async (body, message) => {
    try { await saveGeneral({ watch: body }, message); return true; } catch (err) { toast(err.message); return false; }
  };
  const switchFor = (labelId, checked, onChange) => {
    const input = el("input", { type: "checkbox", role: "switch", "aria-labelledby": labelId, checked });
    input.addEventListener("change", async () => { if (!(await onChange(input.checked))) input.checked = !input.checked; });
    return el("label", { class: "switch" }, input);
  };
  const selectFor = (labelId, options, value, onChange) => {
    const select = el("select", { class: "select", "aria-labelledby": labelId },
      options.map(([v, label]) => el("option", { value: String(v), text: label, selected: String(value) === String(v) })));
    let before = select.value;
    select.addEventListener("change", async () => { if (await onChange(select.value, select.selectedOptions[0].text)) before = select.value; else select.value = before; });
    return select;
  };

  // Watching
  const watching = el("ul", { class: "settings-rows" },
    settingRow("Watch in the background", withCost("Checks your apps every few minutes with no page open, keeps their uptime history and sends the alerts below. Off: nothing runs in the background.", "watch"),
      switchFor("al-on-l", w().enabled, (on) => save({ enabled: on }, on ? "Watching in the background" : "No longer watching in the background")), "al-on-l"),
    settingRow("How often", withCost("Each check is a few small requests. Every 5 minutes is plenty for a home server.", "every"),
      selectFor("al-every-l", [[1, "Every minute"], [5, "Every 5 minutes"], [10, "Every 10 minutes"], [15, "Every 15 minutes"], [30, "Every 30 minutes"], [60, "Every hour"]], w().every,
        (v, t) => save({ every: Number(v) }, `Checks ${t.toLowerCase()}`)), "al-every-l"));

  // Where alerts go
  const kind = el("select", { class: "select", name: "kind" },
    [["", "Nowhere yet"], ["ntfy", "ntfy"], ["gotify", "Gotify"], ["webhook", "A webhook (JSON)"]].map(([v, t]) => el("option", { value: v, text: t, selected: w().channel.kind === v })));
  const url = el("input", { class: "input", name: "url", inputmode: "url", autocomplete: "off", placeholder: "https://ntfy.sh/your-topic", value: w().channel.url });
  const token = el("input", { class: "input", name: "token", type: "password", autocomplete: "off" });
  const tokenHint = el("span", {});
  const urlHint = el("span", {});
  const describe = () => {
    urlHint.textContent = { ntfy: "The topic's full address, such as https://ntfy.sh/a-long-private-name.", gotify: "Your Gotify server's address.", webhook: "Starboard posts JSON: title, message, level and source." }[kind.value] || "Choose a kind first.";
    tokenHint.textContent = `Optional for ntfy and webhooks; Gotify needs an application token.${w().channel.has_token ? " Leave blank to keep the saved one; it is never shown again." : ""}`;
  };
  kind.addEventListener("change", describe);
  describe();
  const channelError = el("div", { role: "alert" });
  const channelForm = el("form", { novalidate: true },
    el("div", { class: "form-grid" }, field("Send alerts to", kind), field("Address", url, { hint: urlHint, span: true }), field("Token", token, { hint: tokenHint, span: true })),
    el("div", { class: "actions" },
      el("button", { type: "submit", class: "btn btn--primary", text: "Save where alerts go" }),
      el("button", { type: "button", class: "btn", id: "alert-test", onclick: async (e) => {
        e.currentTarget.disabled = true;
        try { await api("/api/alerts/test", { method: "POST" }); toast("Test alert sent. Check that it arrived."); }
        catch (err) { toast(`Not sent: ${err.message}`); }
        finally { $("#alert-test").disabled = false; }
      } }, icon("send"), "Send a test alert")),
    channelError);
  channelForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    channelError.replaceChildren();
    try {
      await saveGeneral({ watch: { channel: { kind: kind.value, url: url.value, token: token.value } } }, "Saved where alerts go");
      token.value = "";
      describe();
    } catch (err) { channelError.replaceChildren(notice("danger", "Not saved", err.message)); }
  });

  // What to alert on
  const a = () => w().alerts;
  const onOff = (key, labelId, words) => switchFor(labelId, a()[key], (on) => save({ alerts: { [key]: on } }, `${words}: ${on ? "on" : "off"}`));
  const alertRows = el("ul", { class: "settings-rows" },
    settingRow("An app stops answering", "After two checks in a row, so a restart does not alert. Another message when it answers again.", onOff("apps_down", "al-down-l", "App alerts"), "al-down-l"),
    settingRow("A disk reports a problem", "From Disk health: a failed health check, or reallocated, pending or uncorrectable sectors.", onOff("disk_problem", "al-disk-l", "Disk alerts"), "al-disk-l"),
    settingRow("A folder gets full", "For the folders on System, Storage.",
      selectFor("al-full-l", [[0, "Off"], [80, "At 80%"], [85, "At 85%"], [90, "At 90%"], [95, "At 95%"]], a().disk_full, (v, t) => save({ alerts: { disk_full: Number(v) } }, `Full folder alerts: ${t.toLowerCase()}`)), "al-full-l"),
    settingRow("A download needs attention", "When it has needed attention for 30 minutes.", onOff("download_stuck", "al-stuck-l", "Download alerts"), "al-stuck-l"),
    settingRow("The server backup fails", "From System, Backup and restore.", onOff("backup_failed", "al-backup-l", "Backup alerts"), "al-backup-l"),
    settingRow("A certificate runs out soon", "For apps with an outside https:// address. Checked once a day.",
      selectFor("al-cert-l", [[0, "Off"], [7, "7 days before"], [14, "14 days before"], [30, "30 days before"]], a().cert_days, (v, t) => save({ alerts: { cert_days: Number(v) } }, `Certificate alerts: ${t.toLowerCase()}`)), "al-cert-l"));

  const weekly = el("ul", { class: "settings-rows" },
    settingRow("Weekly summary", withCost("On Monday morning: how each app did, disk health and how full your folders are. Sent where alerts go.", "weekly"),
      switchFor("al-week-l", w().weekly, (on) => save({ weekly: on }, on ? "Weekly summary on" : "Weekly summary off")), "al-week-l"));

  $("#alerts-sections").removeAttribute("aria-busy");
  $("#alerts-sections").replaceChildren(
    section("al-watch", "Watching", "Uptime history on each app's details needs this on.", watching),
    section("al-where", "Where alerts go", "ntfy, Gotify or a webhook. Starboard keeps the token on the server.", channelForm),
    section("al-what", "What to alert on", "Each alert is sent once, and again only after it has cleared.", alertRows),
    section("al-week", "Weekly summary", null, weekly));
}

// Jellyfin ------------------------------------------------------------------
// Live TV, watch history import and user defaults: switches that apply at once, each job's last run, Run now.

const JOB_STATE = { running: ["Running", "info"], done: ["Last run worked", "success"], failed: ["Last run failed", "danger"] };

function jobRun(job) {
  const when = job.finished ? new Date(job.finished * 1000).toLocaleString("en-GB", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "";
  const [words, tone] = JOB_STATE[job.state] || ["Not run yet", "muted"];
  return el("div", { class: "job-run" }, chip(words, tone),
    el("span", { class: "small muted", text: [when, job.summary].filter(Boolean).join(" · ") }));
}

async function startJellyfin() {
  const root = $("#jellyfin-sections");
  let d;
  try { d = await api("/api/extras"); } catch (e) { root.replaceChildren(notice("danger", "Could not load", e.message)); return; }
  const jobs = Object.fromEntries(d.jobs.map((j) => [j.key, j]));
  const x = () => config.extras;
  const save = async (body, message) => {
    try { await saveGeneral({ extras: body }, message); return true; } catch (err) { toast(err.message); return false; }
  };
  const sw = (labelId, checked, onChange, disabled = false) => {
    const input = el("input", { type: "checkbox", role: "switch", "aria-labelledby": labelId, checked, disabled });
    input.addEventListener("change", async () => { if (!(await onChange(input.checked))) input.checked = !input.checked; else startJellyfin(); });
    return el("label", { class: "switch" }, input);
  };
  const runNow = (key, label) => el("button", { type: "button", class: "btn", onclick: async (e) => {
    e.currentTarget.disabled = true;
    try { await api(`/api/extras/${key}/run`, { method: "POST" }); toast(`${label} started`); setTimeout(startJellyfin, 4000); }
    catch (err) { toast(err.message); }
  } }, icon("play"), `Run ${label} now`);
  const welcome = new URLSearchParams(location.search).has("welcome");
  const jfMissing = !d.history.jellyfin;

  // Jellyfin itself
  let top = null;
  if (jfMissing) {
    const found = await api("/api/jellyfin/detect").catch(() => null);
    top = notice("info", found?.found ? `Starboard found Jellyfin ${found.found.version} at ${found.found.url}` : "Add Jellyfin first",
      found?.found && !found.in_apps
        ? "Add it in Manage apps with its API key (in Jellyfin: Dashboard, API keys). Live TV works without the key; the import and user defaults need it."
        : "In Manage apps, give your Jellyfin app its API key (in Jellyfin: Dashboard, API keys). Live TV works without it.",
      el("a", { class: "btn", href: found?.found && !found.in_apps ? `/settings.html?add=jellyfin&url=${encodeURIComponent(found.found.url)}` : "/settings.html" }, "Manage apps"));
  }

  // Live TV
  const lt = jobs.livetv;
  const address = el("input", { class: "input", inputmode: "url", autocomplete: "off", value: x().livetv_address, placeholder: d.self_url });
  const addressForm = el("form", { class: "inline-save", novalidate: true },
    field("Address Jellyfin uses to reach Starboard", address, { hint: `For channel logos and Pluto streams. Blank: ${d.self_url}. Jellyfin must be able to open it, so Starboard needs home network access on.` }),
    el("button", { type: "submit", class: "btn btn--primary", text: "Save address" }));
  addressForm.addEventListener("submit", async (e) => { e.preventDefault(); if (await save({ livetv_address: address.value }, "Address saved")) startJellyfin(); });
  const liveRows = el("ul", { class: "settings-rows" },
    settingRow("Build Live TV channels and guide", withCost(lt.what + ". Free channels only: Samsung TV Plus, Pluto TV and Free-TV, with Sky-style numbers.", "livetv"),
      sw("lt-on-l", x().livetv, (on) => save({ livetv: on }, on ? "Live TV on" : "Live TV off")), "lt-on-l"),
    settingRow("White channel logos", withCost(d.pillow ? "Turns each logo white on a clear background, with Pillow (open source, credited in About). Off: channels keep their own logos." : "Needs Pillow, which this install does not have. Channels keep their own logos.", "white"),
      sw("lt-white-l", x().white_logos && d.pillow, (on) => save({ white_logos: on }, on ? "White logos on" : "White logos off"), !d.pillow), "lt-white-l"));
  const liveNeeds = lt.needs.length ? notice("warning", "Needs set-up on the server", `Starboard needs ${lt.needs.join(" and ")}. Run ./install.sh and say yes to Live TV.`) : null;
  const liveHelp = el("details", { class: "disclosure" }, el("summary", { text: "How Jellyfin uses these files" }),
    el("div", { class: "disclosure__body" }, el("p", { text: "In Jellyfin: Dashboard, Live TV. Add a tuner of type M3U for each playlist (channels.m3u, samsung.m3u, pluto.m3u) and an XMLTV guide for each guide file (guide.xml, guide-samsung.xml, guide-pluto.xml), from the folder Jellyfin sees them in." })));

  // Import watch history
  const h = d.history;
  const kind = el("select", { class: "select" }, [["plexdb", "A Plex database file"], ["plex", "A Plex server"], ["emby", "An Emby server"], ["jellyfin", "Another Jellyfin server"], ["json", "A history file Starboard made before"]]
    .map(([v, t]) => el("option", { value: v, text: t })));
  const url = el("input", { class: "input", inputmode: "url", autocomplete: "off", placeholder: "http://plex:32400" });
  const token = el("input", { class: "input", type: "password", autocomplete: "off" });
  const file = el("input", { type: "file", class: "input" });
  const urlField = field("Server address", url, { span: true });
  const tokenHint = el("span", {});
  const fileHint = el("span", {});
  const tokenField = field("Token or API key", token, { span: true, hint: tokenHint });
  const fileField = field("File", file, { span: true, hint: fileHint });
  const importError = el("div", { role: "alert" });
  const showFields = () => {
    const isFile = ["plexdb", "json"].includes(kind.value);
    urlField.hidden = tokenField.hidden = isFile;
    fileField.hidden = !isFile;
    tokenHint.textContent = kind.value === "plex" ? "Your Plex token (Plex's help: Finding an authentication token). Only your own account's history is read." : "An API key from that server's Dashboard, API keys. Every user's history is read.";
    fileHint.textContent = kind.value === "plexdb" ? "A copy of com.plexapp.plugins.library.db from the Plex server (stop Plex first, or copy it with its -wal file). Every account's history is read; the copy is deleted after reading." : "history.json from an earlier import, or plex-watched.json from the old launcher.";
    url.placeholder = kind.value === "plex" ? "http://plex:32400" : "http://emby:8096";
  };
  kind.addEventListener("change", showFields);
  const importForm = el("form", { novalidate: true, class: "stack-4" },
    el("div", { class: "form-grid" }, field("Import from", kind, { span: true }), urlField, tokenField, fileField),
    el("div", { class: "actions" }, el("button", { type: "submit", class: "btn btn--primary" }, icon("import"), "Read the history")), importError);
  showFields();
  importForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    importError.replaceChildren();
    try {
      if (["plexdb", "json"].includes(kind.value)) {
        if (!file.files[0]) throw new Error("Choose a file first");
        const r = await fetch(`/api/import/upload?kind=${kind.value}`, { method: "POST", headers: { "X-Starboard": "1" }, body: file.files[0] });
        if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || "The upload did not work");
      } else {
        await api("/api/import", { method: "POST", body: { kind: kind.value, url: url.value, token: token.value } });
      }
      toast("Reading the history. This can take a few minutes.");
      const wait = setInterval(async () => { const now = await api("/api/extras"); if (!now.importing) { clearInterval(wait); startJellyfin(); } }, 3000);
    } catch (err) { importError.replaceChildren(notice("danger", "Not started", err.message)); }
  });
  const users = h.jellyfin_users;
  const mapping = h.accounts.length ? el("div", { class: "table-wrap", "data-stack": true }, el("table", { class: "table" },
    el("caption", { class: "visually-hidden", text: "Accounts and the Jellyfin user each one goes to" }),
    el("thead", {}, el("tr", {}, ["Account", "Films", "Episodes", "Goes to Jellyfin user", "Applied"].map((t) => el("th", { scope: "col", text: t })))),
    el("tbody", {}, h.accounts.map((a) => {
      const pick = el("select", { class: "select", "aria-label": `Jellyfin user for ${a.name}` },
        el("option", { value: "", text: "Do not import" }), users.map((u) => el("option", { value: u, text: u, selected: (a.jellyfin_user || "") === u })));
      pick.addEventListener("change", async () => {
        try { await api("/api/import/mapping", { method: "PUT", body: { mapping: { [a.name]: pick.value } } }); toast(pick.value ? `${a.name} goes to ${pick.value}` : `${a.name} is not imported`); }
        catch (err) { toast(err.message); }
      });
      return el("tr", {}, el("th", { scope: "row", "data-label": "Account", text: a.name }),
        el("td", { "data-label": "Films", class: "numeric", text: String(a.films) }),
        el("td", { "data-label": "Episodes", class: "numeric", text: String(a.episodes) }),
        el("td", { "data-label": "Goes to" }, pick, a.suggested && !a.jellyfin_user ? el("span", { class: "small muted", text: ` Same name: ${a.suggested}` }) : null),
        el("td", { "data-label": "Applied", class: "numeric", text: String(a.applied) }));
    })))) : null;
  const matchSame = h.accounts.some((a) => a.suggested && !a.jellyfin_user)
    ? el("button", { type: "button", class: "btn", onclick: async () => {
      const m = Object.fromEntries(h.accounts.filter((a) => a.suggested && !a.jellyfin_user).map((a) => [a.name, a.suggested]));
      await api("/api/import/mapping", { method: "PUT", body: { mapping: m } }); toast("Matched accounts with the same name"); startJellyfin();
    } }, icon("users"), "Match accounts with the same name") : null;
  const imported = h.imported ? el("p", { class: "small muted", text: `${h.source}, read ${new Date(h.imported).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}. ${h.accounts.length} ${h.accounts.length === 1 ? "account" : "accounts"}.` }) : null;
  const result = d.import_result ? notice(d.import_result.ok ? "success" : "danger", d.import_result.ok ? "History read" : "The import did not work", d.import_result.message) : null;
  const applyRows = el("ul", { class: "settings-rows" },
    settingRow("Keep applying every hour", withCost("History for films and episodes you do not have yet is applied when they arrive. Off: only when you choose Apply now.", "importKeep"),
      sw("im-keep-l", x().import_keep, (on) => save({ import_keep: on }, on ? "History is applied every hour" : "History is applied only when you ask")), "im-keep-l"));

  // User defaults
  const df = jobs.defaults;
  const defaultRows = el("ul", { class: "settings-rows" },
    settingRow("Give every Jellyfin user the defaults", withCost("Every hour, users who have not chosen otherwise get: Live TV opens on the Guide. New users get it too.", "defaults"),
      sw("df-on-l", x().defaults, (on) => save({ defaults: on }, on ? "User defaults on" : "User defaults off")), "df-on-l"));

  root.removeAttribute("aria-busy");
  root.replaceChildren(...[
    welcome ? notice("success", "Starboard found Jellyfin", "These are all off. Turn on what you want; you can change them here at any time.") : null,
    top,
    section("jf-live", "Live TV", "Free channels and guides for Jellyfin's Live TV: guides refreshed daily, channels only when a list changes.", liveNeeds, liveRows, addressForm, el("div", { class: "actions" }, jobRun(lt), runNow("livetv", "Live TV")), liveHelp),
    section("jf-import", "Import watch history", "Move what people watched, and where they stopped, from Plex, Emby or another Jellyfin into this Jellyfin.",
      importForm, result, imported, mapping, matchSame ? el("div", { class: "actions" }, matchSame) : null, applyRows,
      el("div", { class: "actions" }, jobRun(jobs.import), h.accounts.length ? runNow("import", "Apply") : null)),
    section("jf-defaults", "User defaults", null, defaultRows, el("div", { class: "actions" }, jobRun(df), runNow("defaults", "Defaults"))),
  ].filter(Boolean));
}

// Security ------------------------------------------------------------------

async function startSecurity() {
  // Who can open the dashboard
  const access = el("input", { type: "checkbox", role: "switch", "aria-labelledby": "net-l", "aria-describedby": "net-result" });
  const result = el("span", { id: "net-result" });
  const addresses = el("dl", { class: "facts facts--addresses", "aria-label": "Addresses that open Starboard" });
  const forced = el("p", { class: "small muted", hidden: true });
  let network;
  const showNetwork = () => {
    access.checked = network.network_access;
    result.textContent = network.network_access
      ? "On: phones and other computers on your home network can reach the sign-in page."
      : "Off: only the computer Starboard runs on can open it.";
    const rows = [["This computer", `http://localhost:${network.port}`]];
    if (network.network_access) for (const a of network.addresses) rows.push(["Phones and other computers", `http://${a}:${network.port}`]);
    addresses.replaceChildren(...rows.flatMap(([label, u]) => [el("dt", { text: label }), el("dd", {}, el("code", { text: u }), copyButton(u, `the address for ${label.toLowerCase()}`))]));
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
    el("div", { class: "form-stack" },
      field("Current password", current),
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
            el("div", { class: "inline-save" },
              el("div", { class: "input-group days-group" }, days, el("span", { class: "input-group__unit", text: "days" })),
              el("button", { type: "submit", class: "btn btn--primary" }, "Save", el("span", { class: "visually-hidden", text: " how long" }))),
            daysError))),
        settingRow("Only send the sign-in cookie over HTTPS", el("span", { id: "secure-h", text: "Turn on when every address you use starts with https. This applies at once." }), el("label", { class: "switch" }, secure), "secure-l"),
        settingRow("Sign out", "This browser, or every browser and phone at once.", el("div", { class: "actions session-actions" }, signOut, everywhere), "signout-l")));
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
  renderAccess();
  try { v = await api("/api/version"); } catch { /* no notice */ }
  showVersion();
}

startPage().then(async (session) => {
  if (!session) return;
  try { config = await api("/api/config"); } catch (e) { toast(e.message); return; }
  if ($("#app-sections")) startManageApps();
  if ($("#general-sections")) startGeneral();
  if ($("#security-sections")) startSecurity();
  if ($("#alerts-sections")) startAlerts();
  if ($("#jellyfin-sections")) startJellyfin();
  if ($("#version-notice")) startAbout();
});
