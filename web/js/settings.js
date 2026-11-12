// Settings: Manage apps (add, edit, test, order, hide, remove), General, Security, and Updates (Update settings and
// Releases; Restore is in system-backup.js).
// Each page has its own start function below; the page's markup says which one runs.

let config = null;
const SEARCHABLE = ["sonarr", "radarr", "lidarr", "readarr"];
const NO_KEY = ["link"];

// Small helpers ------------------------------------------------------------

// A field with its label, hint and an error tied to the control.
let fieldCount = 0;
function field(label, control, { hint, span, short, required } = {}) {
  if (!control.id) control.id = `field-${++fieldCount}`;
  if (required) control.required = true;
  const hintNode = hint ? el("span", { class: "hint", id: `${control.id}-hint` }, hint) : null;
  const error = el("span", { class: "field-error", id: `${control.id}-error`, hidden: true });
  if (hintNode) control.setAttribute("aria-describedby", hintNode.id);
  control.fieldError = error;
  control.fieldHint = hintNode;
  return el("div", { class: short ? "field field--short" : "field", "data-span": span ? "all" : null },
    el("label", { for: control.id }, label, control.required ? requiredMark() : null), hintNode, control, error);
}

function setError(control, message) {
  const error = control.fieldError;
  const ids = [control.fieldHint?.id, ...(control.moreHints || [])];
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
function pageSection(id, title, description, ...content) { return section(id, title, description, ...content); }
function section(id, title, description, ...content) {
  return el("section", { class: "settings-section", "aria-labelledby": `${id}-h` },
    el("div", { class: "settings-section__head" }, el("h2", { id: `${id}-h`, text: title }), description ? el("p", { class: "small muted" }, description) : null),
    ...content);
}

// A settings page confirms a save beside its button ("Saved at 16:31"), not in a toast (CONTENT-DESIGN.md).
// The note has a fixed id, so it can be shown after a save that redraws the page.
function savedNote(id) {
  return el("span", { class: "saved-note", id, hidden: true });
}
function showSaved(id, text) {
  const note = document.getElementById(id);
  if (note) window.SharedComponents.savedNote(note, text);
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
  out.push({ key: "background", title: "Other services", hint: "Services with no web page. They appear under System, Apps, Other services.", items: services.filter((s) => s.background) });
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
  } catch (e) { problem(e.message); }
}

async function setShown(s, shown) {
  try {
    const saved = await api("/api/services", { method: "POST", body: serviceBody(s, { enabled: shown }) });
    config = saved.config;
    renderServices();
    announce(shown ? `${s.name} is shown on the dashboard` : `${s.name} is hidden from the dashboard`);
  } catch (e) { problem(e.message); }
}

async function removeService(s, { fromPanel } = {}) {
  const ok = await confirmDialog({
    title: `Remove ${s.name}?`,
    message: `${s.name} leaves the dashboard${SEARCHABLE.includes(s.type) ? " and Search" : ""}. ${s.name} itself, its files and its settings stay as they are. You can add it again at any time.`,
    confirm: `Remove ${s.name}`, danger: true,
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
  } catch (e) { problem(e.message); return false; }
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
  const url = el("input", { class: "input", name: "url", inputmode: "url", placeholder: "http://127.0.0.1:8989", autocomplete: "off" });
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
  const containerField = field("Container", container, { hint: "The container this app runs in, for System, Apps, Updates. Starboard finds it by the app's name unless you choose one.", span: true });
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
        field("Name", name, { required: true }),
        field("Address Starboard uses", url, { required: true, hint: "For an app on this computer, 127.0.0.1 and the app's port, such as http://127.0.0.1:8989. For another computer, its address. Optional for a background service.", span: true }),
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
        switchRow("Background service", "It has no web page, so it is listed under System, Apps, Other services.", bg)),
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
      jellyfin: "Dashboard, API keys. Optional: it adds Jellyfin's state, what is playing and recently added to System",
      audiobookshelf: "Settings, API Keys, for an admin user. Optional: it is needed only to copy listening progress (Settings, Apps, Audiobookshelf)",
      gluetun: "its control server settings. Optional: only if you gave its control server an API key",
      nzbget: "Settings, Security: type its control user name and password as user:password",
      slskd: "Options, web, authentication, API keys (in its slskd.yml)" }[t] || "Settings, General";
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
    if (!url.value.trim() && !bg.checked) { setError(url, "Enter the address Starboard uses to reach the app, such as http://127.0.0.1:8989"); url.focus(); return; }
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
        el("div", { class: "switch-list" }, switchRow("Search as soon as something is added", `Active: ${current.name} looks for ${kind} straight away.`, searchOnAdd))));
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
  $("#usenet-section")?.append(usenetProviders());
  $("#add-service").addEventListener("click", (e) => openService(null, e.currentTarget));
  $("#find-apps").addEventListener("click", (e) => openFinder(e.currentTarget));
  // Other pages link here: ?edit=<app id> opens that app; ?add=background starts a background service.
  const params = new URLSearchParams(location.search);
  const editId = params.get("edit");
  const editing = editId && config.services.find((s) => s.id === editId);
  if (editing) openService(editing, $(`#app-sections [data-key="${CSS.escape(editing.id)}"] .row__title button`));
  else if (editId) { setAddress(null, false); problem("That app is not in your list any more"); }
  else if (params.get("add") === "background") openService(null, $("#add-service"), { background: true });
  else if (params.get("add") === "jellyfin") openService(null, $("#add-service"), { preset: { type: "jellyfin", name: "Jellyfin", url: params.get("url") || "" } });
  else if (params.has("add") || !config.services.length) openService(null, $("#add-service"));
  loadStatus();
}

// General -------------------------------------------------------------------

function countIn(group) { return config.services.filter((s) => s.group === group).length; }
function appsWord(n) { return `${n} ${n === 1 ? "app" : "apps"}`; }

// Categories are saved as a list of names, and each app keeps its category's name. Renaming or removing one
// moves the apps in it in the same save (move_apps).

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

async function saveGroups(groups, message, moveApps = null) {
  try {
    await saveGeneral(moveApps ? { groups, move_apps: moveApps } : { groups }, null);
    renderCategories();
    if (message) announce(message);
    return true;
  } catch (e) { problem(e.message); return false; }
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
    fields: [field("New name", input, { required: true })],
    confirm: "Rename category",
  });
  const to = input.value.trim();
  if (!ok || !to || to === name) return;
  if (config.groups.includes(to)) { problem(`There is already a category called ${to}`); return; }
  if (!(await saveGroups(config.groups.map((g) => (g === name ? to : g)), null, { from: name, to }))) return;
  toast(`Renamed ${name} to ${to}`);
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
    confirm: "Remove category", danger: true,
  });
  if (!ok) return;
  const row = $(`#category-list [data-key="${CSS.escape(name)}"]`);
  const next = row?.nextElementSibling || row?.previousElementSibling;
  if (await saveGroups(others, null, n ? { from: name, to: to.value } : null)) {
    toast(n ? `Removed ${name}. Its apps are now in ${to.value}` : `Removed ${name}`);
    (next?.isConnected ? $(".btn", next) : $("#category-name"))?.focus();
  }
}

function startGeneral() {
  // Dashboard name
  const siteName = el("input", { class: "input", name: "site_name", maxlength: "60", required: true, value: config.site_name });
  const nameForm = el("form", { novalidate: true, class: "inline-save" }, field("Dashboard name", siteName, { required: true }),
    el("button", { type: "submit", class: "btn", text: "Save name" }), savedNote("name-saved"));
  nameForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    setError(siteName, "");
    if (!siteName.value.trim()) { setError(siteName, "Enter a name for the dashboard"); siteName.focus(); return; }
    try {
      await saveGeneral({ site_name: siteName.value });
      showSaved("name-saved");
      document.title = document.title.replace(/ · [^·]*$/, ` · ${config.site_name}`);
    } catch (err) { setError(siteName, err.message); siteName.focus(); }
  });

  // Server name: up to 10 characters, at the start of the level 1 menu
  const serverName = el("input", { class: "input", name: "server_name", maxlength: String(config.server_name_max || 10),
    value: config.server_name || "", autocomplete: "off", spellcheck: "false" });
  const serverForm = el("form", { novalidate: true, class: "inline-save" },
    field("Server name", serverName, { hint: `Up to ${config.server_name_max || 10} characters, such as T-Rex. Shown at the start of the level 1 menu on every page. Leave it empty to show no name.`, short: true }),
    el("button", { type: "submit", class: "btn", text: "Save server name" }), savedNote("server-name-saved"));
  // A count under the box, read with the hint but not announced on every key.
  const max = config.server_name_max || 10;
  const count = el("span", { class: "hint", id: `${serverName.id}-count` });
  const recount = () => { count.textContent = `${serverName.value.length} of ${max} characters`; };
  serverName.after(count);
  serverName.moreHints = [count.id];
  serverName.setAttribute("aria-describedby", `${serverName.fieldHint.id} ${count.id}`);
  serverName.addEventListener("input", recount);
  recount();
  serverForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    setError(serverName, "");
    try {
      await saveGeneral({ server_name: serverName.value });
      showSaved("server-name-saved");
      showServerName(config.server_name);
    } catch (err) { setError(serverName, err.message); serverName.focus(); }
  });

  // Categories
  const newName = el("input", { class: "input", id: "category-name", maxlength: "40", placeholder: "For example: Home", autocomplete: "off" });
  const addForm = el("form", { class: "add-row", novalidate: true }, field("New category", newName, { required: true }),
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
  const uxInput = el("input", { type: "checkbox", role: "switch", "aria-labelledby": "ux-notes-l", checked: config.ux_notes });
  uxInput.addEventListener("change", async () => {
    try {
      await saveGeneral({ ux_notes: uxInput.checked }, uxInput.checked ? "Send feedback activated on every page" : "Send feedback deactivated");
      if (uxInput.checked) await startFeedback(); else stopFeedback();
      renderFeedback();
    } catch (err) { uxInput.checked = !uxInput.checked; problem(err.message); }
  });
  const uxSwitch = el("label", { class: "switch" }, uxInput);
  const cardSwitch = (key, labelId, on, off) => {
    const input = el("input", { type: "checkbox", role: "switch", "aria-labelledby": labelId, checked: config[key] });
    input.addEventListener("change", async () => {
      try { await saveGeneral({ [key]: input.checked }, input.checked ? on : off); }
      catch (err) { input.checked = !input.checked; problem(err.message); }
    });
    return el("label", { class: "switch" }, input);
  };

  // Default design
  // Default design: a choice, so it saves as soon as it changes (the design system's save rule).
  const designForm = el("form", {},
    el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Default design" }),
      el("div", { class: "option-cards option-cards--row" }, Object.entries(DESIGNS).map(([k, [label, help]]) => el("label", { class: "option-card" },
        el("input", { type: "radio", name: "design", value: k, checked: config.design === k }), el("strong", { text: label }), el("small", { text: help }))))));
  designForm.addEventListener("change", async () => {
    const before = config.design;
    try { await saveGeneral({ design: designForm.design.value }, `Default design: ${DESIGNS[designForm.design.value][0]}`); }
    catch (err) { designForm.design.value = before; problem(err.message); }
  });

  // Style (owner, 10 November 2026): the plug-in style this browser uses, and Reset style back to the standard colours.
  const styleSaid = el("p", { "aria-live": "polite" });
  const styleResetBtn = el("button", { type: "button", class: "btn" }, icon("rotate-ccw"), "Reset style");
  const styleChoose = el("button", { type: "button", class: "btn btn--quiet" }, "Choose a style");
  let styleNames = {};
  const styleShow = () => {
    const chosen = readPrefs().style;
    styleSaid.replaceChildren("This browser uses ", el("strong", { text: chosen ? (styleNames[chosen] || "a style from a plug-in that is now off") : "Starboard's standard colours" }), ".");
    styleResetBtn.disabled = !chosen;
  };
  styleResetBtn.addEventListener("click", () => { resetStyle(); styleShow(); });
  styleChoose.addEventListener("click", () => $("[data-display-toggle]")?.click());
  document.addEventListener("stylechange", styleShow);
  addEventListener("storage", styleShow);  // changed in another tab
  api("/api/styles").then((r) => { styleNames = Object.fromEntries(r.styles.map((x) => [x.value, `${x.name}, from ${x.plugin}`])); styleShow(); }).catch(styleShow);
  styleShow();
  const styleForm = el("div", { class: "stack-2" }, styleSaid, el("div", { class: "actions" }, styleResetBtn, styleChoose));

  // Coming up: selects that apply at once.
  const upcomingSelect = (key, labelId, options, message) => {
    const select = el("select", { class: "select", "aria-labelledby": labelId },
      options.map(([value, label]) => el("option", { value: String(value), text: label, selected: String(config[key]) === String(value) })));
    select.addEventListener("change", async () => {
      const before = config[key];
      try { await saveGeneral({ [key]: key === "upcoming_days" ? Number(select.value) : select.value }, message(select.selectedOptions[0].text)); }
      catch (err) { select.value = String(before); problem(err.message); }
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
      } catch (err) { select.value = String(before); problem(err.message); }
    });
    return select;
  };
  const hoursText = (h) => `${String(h).padStart(2, "0")}:00`;
  const hoursOn = el("input", { type: "checkbox", role: "switch", "aria-labelledby": "dh-on-l", checked: config.download_hours.enabled });
  hoursOn.addEventListener("change", async () => {
    try {
      await saveGeneral({ download_hours: { enabled: hoursOn.checked } }, hoursOn.checked
        ? `Download hours activated. Downloads run from ${hoursText(config.download_hours.start)} to ${hoursText(config.download_hours.end)}`
        : "Download hours deactivated. Downloads run at any time");
    } catch (err) { hoursOn.checked = !hoursOn.checked; problem(err.message); }
  });
  const clients = config.services.filter((s) => ["qbittorrent", "sabnzbd"].includes(s.type) && s.has_api_key);

  $("#general-sections").removeAttribute("aria-busy");
  $("#general-sections").replaceChildren(
    section("gn-name", "Names", "The server name shows at the start of the menu. The dashboard name shows in the browser tab and in alerts.", serverForm, nameForm),
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
    el("div", { id: "download-hours" }, section("gn-dh", "Download hours", "Starboard pauses qBittorrent, NZBGet, SABnzbd and Soulseek (slskd) outside these hours, in the server's local time, and starts again only what it paused. Seeding is left alone. These apply at once.",
      clients.length ? null : notice("info", "No download apps yet", "Add qBittorrent, NZBGet, SABnzbd or Soulseek (slskd) with its API key in Manage apps, so Starboard can pause and resume them."),
      el("ul", { class: "settings-rows" },
        settingRow("Only download between set hours", withCost("Inactive: downloads run at any time.", "hours"), el("label", { class: "switch" }, hoursOn), "dh-on-l"),
        settingRow("Start", "Downloads start at this hour.", hoursSelect("start", "dh-start-l"), "dh-start-l"),
        settingRow("End", "Downloads pause at this hour. An end before the start runs overnight.", hoursSelect("end", "dh-end-l"), "dh-end-l")))),
    section("gn-guide", "Set-up guide", "Finds your apps and walks through what Starboard can do. Running it again changes nothing until you press Continue.",
      el("div", { class: "actions" }, el("a", { class: "btn", href: "/setup-guide.html" }, icon("play"), config.setup_guide_done ? "Run the set-up guide again" : "Run the set-up guide"),
        el("a", { class: "btn", href: "/install-apps.html" }, icon("download"), "Install apps"))),
    el("div", { id: "logs" }, section("gn-logs", "Logs", "What Starboard did and every problem it met, on System, Logs. Personal details (passwords, API keys, addresses, names) are removed before anything is written.",
      el("ul", { class: "settings-rows" },
        settingRow("Keep logs for", withCost("Older days are removed once a day.", "logKeep"),
          logPick("lg-keep-l", [[7, "7 days"], [14, "14 days"], [30, "30 days"], [60, "60 days"], [90, "90 days"], [180, "180 days"], [365, "A year"]], config.logs.keep_days,
            (v, t) => saveGeneral({ logs: { keep_days: Number(v) } }, `Logs kept for ${t.toLowerCase()}`)), "lg-keep-l"),
        settingRow("Detailed logging", withCost("For reporting a problem: adds every page request and every call to your apps, and the full detail of errors. Personal details are still removed.", "logDetail"),
          logPick("lg-detail-l", [["off", "Off"], ["day", "For 24 hours"], ["on", "Until I deactivate it"]], config.logs.detail,
            (v, t) => saveGeneral({ logs: { detail: v } }, `Detailed logging: ${t.toLowerCase()}`)), "lg-detail-l")),
      el("div", { class: "actions" }, el("a", { class: "btn", href: "/system-logs.html" }, icon("scroll-text"), "Open the logs")))),
    section("gn-design", "Default design", "Everyone sees this unless they choose their own in Display.", designForm),
    section("gn-style", "Style", "Colours from a plug-in, chosen in Display for this browser only. Reset style goes back to Starboard's standard colours and keeps your other Display choices.", styleForm),
    el("div", { id: "testing" }, section("gn-test", "Send feedback", "Report a problem or suggest something from any page. On unless you deactivate it.",
      el("ul", { class: "settings-rows" },
        settingRow("Send feedback", "Feedback in the side menu, on every page, reports a problem, suggests something or checks a page for accessibility problems. Each report opens as an issue on Starboard's GitHub page, or is saved here. Deactivate it to remove Feedback from the menu.",
          uxSwitch, "ux-notes-l")),
      el("div", { id: "feedback-list" }))));
  renderCategories();
  renderFeedback();
  if (["#categories", "#coming-up", "#download-hours", "#logs", "#testing"].includes(location.hash)) $(location.hash).scrollIntoView();
}

// Reports saved with Save in Starboard (and notes from the older Note an issue button), newest first.
async function renderFeedback() {
  const box = $("#feedback-list");
  if (!box) return;
  if (!config.ux_notes) { box.replaceChildren(); return; }
  let notes;
  try { notes = (await api("/api/ux-notes")).notes; } catch (e) { box.replaceChildren(notice("danger", "Could not load the saved reports", e.message)); return; }
  if (!notes.length) { box.replaceChildren(el("p", { class: "muted", text: "No reports saved in Starboard yet." })); return; }
  const open = notes.filter((n) => n.status !== "fixed").length;
  const download = el("button", { type: "button", class: "btn" }, icon("download"), "Download all");
  download.addEventListener("click", () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(notes, null, 2)], { type: "application/json" }));
    const a = el("a", { href: url, download: `starboard-feedback-${new Date().toISOString().slice(0, 10)}.json` });
    document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  const setStatus = async (n, status) => {
    try { await api("/api/ux-notes/update", { method: "POST", body: { id: n.id, status } }); toast(status === "fixed" ? "Marked fixed" : "Marked open"); renderFeedback(); }
    catch (e) { problem(e.message); }
  };
  const remove = async (n) => {
    if (!(await confirmDialog({ title: "Remove this report?", message: n.title || n.what, confirm: "Remove report", danger: true }))) return;
    try { await api("/api/ux-notes/remove", { method: "POST", body: { id: n.id } }); toast("Report removed"); renderFeedback(); }
    catch (e) { problem(e.message); }
  };
  const row = (n) => {
    const fixed = n.status === "fixed";
    const title = n.title || String(n.what || "").split("\n")[0];
    const meta = [n.page, n.part, n.when && formatDate(n.when, true), fixed ? "Fixed" : "Open"].filter(Boolean).join(" · ");
    const body = n.markdown || n.what || "";
    const details = body && body !== title ? el("details", {}, el("summary", { text: "The full report" }), el("pre", { class: "code-block", text: body })) : null;
    const li = el("li", { class: "row" },
      el("div", { class: "row__text" }, el("div", { class: "row__title", text: title }), el("div", { class: "row__meta", text: meta }), details),
      el("div", { class: "row__side" },
        el("button", { type: "button", class: "btn", onclick: () => setStatus(n, fixed ? "open" : "fixed") }, icon(fixed ? "rotate-ccw" : "check"), fixed ? "Mark open" : "Mark fixed"),
        menuButton(`More actions for ${title}`, [{ label: "Remove", icon: "trash-2", danger: true, onSelect: () => later(() => remove(n)) }])));
    li.dataset.key = n.id;
    return li;
  };
  const list = el("ul", { class: "rows" });
  redraw(list, notes.slice().reverse().map(row));
  box.replaceChildren(
    el("h3", { text: `Saved in Starboard: ${notes.length} ${notes.length === 1 ? "report" : "reports"}, ${open} open` }),
    list, el("div", { class: "actions" }, download));
}

// What Starboard can access: a row per kind of access, with a switch, a link or the installer command.
async function renderAccess() {
  const list = $("#access-rows");
  let items;
  try { items = (await api("/api/access")).items; } catch (e) { list.replaceChildren(el("li", { class: "setting", text: e.message })); return; }
  // On or off as an icon beside the name: a tick or an empty ring (never colour alone), with the word in
  // hidden text and in the tooltip. Rows with a switch show their state in the switch itself.
  const stateIcon = (on) => el("span", { class: "status-icon", "data-tone": on ? "success" : "muted", title: on ? "On" : "Off" },
    icon(on ? "circle-check" : "circle"), el("span", { class: "visually-hidden", text: on ? ", active" : ", inactive" }));
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
        try { await saveGeneral({ [a.setting]: input.checked }, `${a.title} ${input.checked ? "activated" : "deactivated"}`); }
        catch (err) { input.checked = !input.checked; problem(err.message); }
      });
      return row(a, el("label", { class: "switch" }, input), false);
    }
    if (a.change === "installer") {
      const command = `./install.sh ${a.on ? a.off_flag : a.on_flag}`;
      return row(a, el("div", { class: "access-change" },
        el("span", { class: "small", text: a.on ? "To deactivate it, run on the server:" : "To activate it, run on the server:" }),
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
// can keep only what it needs. Idle Starboard: about 16 MB and 0.01% of the processor (docs/TESTING.md).
const COSTS = {
  hours: "Costs about: one small check a minute, under 0.01% of the processor, no extra memory.",
  upcoming: "Costs about: one request to each app when Coming up opens, kept for 10 minutes. Further ahead means a bigger answer, still well under a second.",
  watch: "Costs about: 0.02 seconds of processor per check (every 5 minutes, under 0.01% overall) and under 1 MB of memory for the history. Deactivating it saves that, and keeps nothing running in the background.",
  every: "Every minute costs five times as much as every 5 minutes; every hour, a twelfth.",
  weekly: "Costs about: one message a week. Nothing noticeable.",
  livetv: "Costs about: under 2 seconds of processor a day to refresh the guides, and about a minute once a week (or when a channel list changes) to test every stream, using up to 35 MB more memory while it runs. Nothing in between. Deactivating it saves all of that.",
  white: "Costs about: only when new channels arrive, a second or two per logo and up to 15 MB more memory while it runs. Deactivating it saves that; logos already made stay.",
  importKeep: "Costs about: 1 second of processor and up to 40 MB more memory for about 20 seconds an hour, while it reads your Jellyfin library. Deactivating it saves that; Apply now still works.",
  defaults: "Costs about: two small requests per Jellyfin user an hour. Nothing noticeable.",
  listeningKeep: "Costs about: one reading of your Audiobookshelf library and users an hour, under a second of processor and a few MB more memory while it runs. Deactivating it saves that; Apply now still works.",
  history: "Costs about: one reading of the server's own counters each time, under 0.01% of the processor, and up to 1.5 MB of memory for a day of readings. Inactive: the System charts have no history.",
  scheduleEvery: "Every minute catches a new download straight away; every 5 minutes uses a fifth of the requests.",
  downloadsRefresh: "Each update asks each download app once (shared for 10 seconds). Slower, or off, means fewer requests while Downloads is open.",
  monitorRefresh: "Each reading takes under a thousandth of a second on the server. Slower means fewer readings while Monitor is open.",
  cardNumbers: "Costs about: one small request per app when Apps opens, shared for a minute. Deactivating it saves that.",
  usage: "Costs about: each run reads every file name in your folders (a few minutes for 30 TB, mostly disk reading, under 20 MB of memory), and nothing between runs. Starboard skips the drives inside a pool, so a pool is read once. Every night or every week keeps one sleeping thread; the other choices keep none.",
  spaceLog: "Costs about: one size check of each folder a day, taken when a page or the history asks anyway, and a few kilobytes a year. Nothing noticeable.",
  logKeep: "Costs about: a few kilobytes a day on disk (about 100 KB a month for a quiet server). Nothing in memory.",
  logDetail: "Costs about: one short line per page request and per call to your apps, about 1 to 5 MB a day on a busy dashboard. For 24 hours turns itself off, so it cannot fill the disk.",
  storageRefresh: "Each update checks the size of each folder, under a thousandth of a second. Inactive means only when you open the page or press Check again.",
  posters: "Costs about: a small download per new poster, kept for a week (a few megabytes on disk).",
  icons: "Costs about: one download per app, once.",
};

const USAGE_CHOICES = [["ask", "Only when I press Sort by type"], ["open", "When I open Storage, if over a day old"], ["nightly", "Every night at 3 am"], ["weekly", "Every week, at 3 am"], ["off", "Off"]];
const STORAGE_REFRESH = [[0, "Only when I press Check again"], [60, "Every minute"], [300, "Every 5 minutes"]];

function logPick(labelId, options, value, onChange) {
  const select = el("select", { class: "select", "aria-labelledby": labelId },
    options.map(([v, t]) => el("option", { value: String(v), text: t, selected: String(v) === String(value) })));
  select.addEventListener("change", async () => {
    try { await onChange(select.value, select.selectedOptions[0].text); } catch (e) { problem(e.message); }
  });
  return select;
}

function withCost(hint, key) {
  return el("span", {}, hint, el("span", { class: "setting__cost", text: COSTS[key] }));
}

// Search for new apps ---------------------------------------------------------
// Finds apps on this computer that are not in Manage apps yet, and adds the ones you tick. Used by Manage apps
// (a slide-out) and by the set-up wizard (a step). onAdded gets the server's answer.

// With expect (the keys of apps just started), it looks again until each one it can recognise answers, for up to 4
// minutes: an app opens its port a while after it starts (Radarr and Sonarr can take over a minute).
async function appFinder(onAdded, { expect = null, shown = null } = {}) {
  const box = el("div", { class: "stack-4", "aria-live": "polite" }, el("p", { class: "muted", text: "Looking for apps on this computer…" }));
  let found;
  try {
    found = await api("/api/discover");
    const began = Date.now();
    const missing = () => (expect || []).filter((k) => (found.known || []).includes(k) && !found.items.some((i) => i.key === k));
    while (expect && missing().length && Date.now() - began < 240000) {
      shown?.(`Waiting for the apps to answer: ${found.items.length} found, ${missing().length} still starting…`);
      await new Promise((r) => setTimeout(r, 5000));
      found = await api("/api/discover");
    }
  } catch (e) { box.replaceChildren(notice("danger", "Could not look", e.message)); return { box, add: null }; }
  const fresh = found.items.filter((i) => !i.already);
  const known = found.items.filter((i) => i.already);
  if (!fresh.length) {
    box.replaceChildren(notice("success", "Nothing new found", `Every app Starboard recognises on this computer is already in your list${known.length ? ` (${known.length})` : ""}. Add others by hand with Add an app.`));
    return { box, add: null };
  }
  const picks = fresh.map((i) => {
    const input = el("input", { type: "checkbox", checked: true });
    const label = el("label", { class: "check" }, input, el("span", { class: "check__text" }, el("strong", { text: i.name }),
      el("span", { class: "check__hint", text: [i.url.replace("http://", ""), i.background ? "background service" : "",
        i.needs_key ? (i.can_read_key ? "API key can be read for you" : "needs its API key") : ""].filter(Boolean).join(" · ") })));
    return { i, input, label };
  });
  const anyKey = fresh.some((i) => i.can_read_key);
  const add = async () => {
    const items = picks.filter((p) => p.input.checked).map((p) => ({ ...p.i, read_key: anyKey }));
    if (!items.length) { problem("Tick the apps to add"); return null; }
    const r = await api("/api/discover/add", { method: "POST", body: { items } });
    config = r.config;
    toast(`Added ${r.added.length} ${r.added.length === 1 ? "app" : "apps"}`);
    onAdded?.(r);
    return r;
  };
  box.replaceChildren(...[
    el("p", { text: `Found ${fresh.length} ${fresh.length === 1 ? "app" : "apps"} that ${fresh.length === 1 ? "is" : "are"} not in your list yet${known.length ? `, and ${known.length} you already have` : ""}. Untick any you do not want.` }),
    el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Apps to add" }), el("div", { class: "switch-list" }, picks.map((p) => p.label))),
    anyKey ? el("p", { class: "small muted", text: "Starboard reads each app's API key from its own settings through Docker, so there is nothing to copy. The keys stay on the server." }) : null,
    !found.docker ? el("p", { class: "small muted", text: "With Docker access (./install.sh --docker) Starboard could also read API keys for you and find apps on other ports." }) : null,
  ].filter(Boolean));
  return { box, add, ticked: () => picks.filter((p) => p.input.checked).length };
}

async function openFinder(opener) {
  const go = el("button", { type: "button", class: "btn btn--primary" }, icon("plus"), "Add the ticked apps");
  const panel = sidePanel({ title: "Search for new apps", opener, body: [el("p", { class: "muted", text: "Looking…" })], foot: [go] });
  const finder = await appFinder((r) => {
    renderServices();
    if (r.missing_keys.length) toast(`Added. Give these their API keys in Edit: ${r.missing_keys.join(", ")}`);
  });
  panel.body.replaceChildren(finder.box);
  go.hidden = !finder.add;
  go.addEventListener("click", async () => {
    go.disabled = true;
    try { if (await finder.add()) panel.close(); } catch (e) { problem(e.message); } finally { go.disabled = false; }
  });
}

// One wizard step's content: { nodes, save }. Shared by the set-up guide and the upgrade guide.
async function stepContent(id, root) {
  const types = (t) => config.services.filter((s) => s.enabled !== false && t.includes(s.type));
  let nodes = [];
  let save = async () => true;
  if (id === "install") {
    const have = el("input", { type: "radio", name: "install", checked: true });
    const fresh = el("input", { type: "radio", name: "install" });
    nodes = [el("div", { class: "option-cards" },
      el("label", { class: "option-card" }, have, el("strong", { text: "Use the apps I have" }), el("small", { text: "Starboard looks for them on the next step." })),
      el("label", { class: "option-card" }, fresh, el("strong", { text: "Install apps for me" }),
        el("small", { text: "Choose groups such as Movies, TV, Ebooks and Audiobooks. Starboard writes the files, shows them, and starts the apps when you say. It also offers to bring over what your current apps have." })))];
    save = async () => {
      if (!fresh.checked) return true;
      location.href = "/install-apps.html?from=guide";
      return false;
    };
  } else if (id === "how-to-start") {  // not "start": that is Install apps' Start the apps step, drawn by install.js
    // How to start: the same question, answers and help as the terminal set-up (starboard/start.py).
    const found = await api("/api/setup/start");
    const name = `start-${Date.now()}`;
    const chosen = guideMemory().start || found.recommended;
    const radios = found.choices.map((c) => ({ c, input: el("input", { type: "radio", name, value: c.key, checked: c.key === chosen }) }));
    const file = el("input", { type: "file", class: "input", accept: ".json,application/json", id: "guide-backup-file" });
    const password = el("input", { type: "password", class: "input", autocomplete: "current-password", id: "guide-backup-password" });
    const restoreBox = el("div", { class: "form-stack", hidden: chosen !== "restore" },
      field("Backup file", file, { required: true, hint: "From System, Backup and restore, Download a copy of the settings.", span: true }),
      field("Your Starboard password", password, { required: true, hint: "The one you just chose. Starboard checks it before it restores.", span: true }));
    radios.forEach(({ input }) => input.addEventListener("change", () => { restoreBox.hidden = input.value !== "restore" || !input.checked; }));
    nodes = [found.found.length ? notice("info", "Found on this computer", found.found.join(", ")) : null,
      el("fieldset", {}, el("legend", { class: "visually-hidden", text: "How to start" }),
        el("div", { class: "option-cards" }, radios.map(({ c, input }) => el("label", { class: "option-card" }, input,
          el("strong", { text: c.title + (c.recommended ? " (recommended)" : "") }), el("small", { text: c.about }))))),
      restoreBox,
      el("p", { class: "help-links" }, helpButton("Which one is right for me?", { back: "Back to set-up",
        body: found.choices.map((c) => el("p", {}, el("strong", { text: `${c.title}: ` }), c.help)) }))];
    save = async () => {
      const key = radios.find((r) => r.input.checked)?.input.value || found.recommended;
      if (key === "restore") {
        if (!file.files.length) { showProblemNear(file, "Choose the backup file."); return false; }
        let backup;
        try { backup = JSON.parse(await file.files[0].text()); } catch { showProblemNear(file, "That file is not a Starboard backup."); return false; }
        const done = await api("/api/backup/restore", { method: "POST", body: { backup, password: password.value } });
        config = done.config;
        announce(`Restored: ${done.apps} apps, with your categories, design and alerts.`);
        // DASH-268: the backup's apps are not on this computer: Storage, the VPN's secrets, then Check bring them back.
        remember({ restoreInstall: done.install || null });
      }
      remember({ start: key });
      return true;
    };
  } else if (id === "where") {
    // Storage: the main disk, a separate disk or a pool; the folder is made when the apps start. As the terminal.
    const found = await api("/api/setup/storage");
    const name = `where-${Date.now()}`;
    const mem = guideMemory();
    const chosen = mem.where || found.recommended;
    const folder = el("input", { class: "input", spellcheck: "false", autocomplete: "off", id: "guide-media-folder",
      value: mem.media || (found.choices.find((c) => c.key === chosen) || found.choices[0]).folder });
    const radios = found.choices.map((c) => ({ c, input: el("input", { type: "radio", name, value: c.key, checked: c.key === chosen }) }));
    radios.forEach(({ c, input }) => input.addEventListener("change", () => { if (input.checked) folder.value = c.folder; }));
    nodes = [el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Where your media goes" }),
      el("div", { class: "option-cards" }, radios.map(({ c, input }) => el("label", { class: "option-card" }, input,
        el("strong", { text: c.title + (c.recommended ? " (recommended)" : "") }), el("small", { text: c.about }))))),
      folderField({ input: folder, label: "Media folder", required: true, hint: "Made for you when the apps start. Type it, or choose it with Browse." }).node,
      el("p", { class: "small muted", text: found.help })];
    save = async () => {
      const picked = radios.find((r) => r.input.checked)?.c || found.choices[0];
      if (picked.key === "pool" && !picked.ready) {
        showProblemNear(folder, "The pool helper is not set up yet. Choose another place for now, and make the pool later on System, Storage, Pool.");
        return false;
      }
      remember({ where: picked.key, media: folder.value.trim(), at: "after-apps" });
      await saveHost();
      // DASH-269: Install apps' steps follow in this wizard, with the media folder chosen here (no Folders step).
      if (typeof installFlow !== "function") { location.href = `/install-apps.html?from=guide&media=${encodeURIComponent(folder.value.trim())}`; return false; }
      document.dispatchEvent(new CustomEvent("guide-media", { detail: folder.value.trim() }));
      return true;
    };
  } else if (id === "storage") {
    const p = config.performance;
    const radios = USAGE_CHOICES.map(([v, t]) => ({ v, input: el("input", { type: "radio", name: "usage-every", value: v, checked: p.usage_every === v }), t }));
    const refresh = el("select", { class: "select", id: "guide-st-refresh" }, STORAGE_REFRESH.map(([v, t]) => el("option", { value: String(v), text: t, selected: Number(v) === p.storage_refresh })));
    const daily = el("input", { type: "checkbox", checked: p.space_log !== false });
    nodes = [
      el("fieldset", { class: "stack-2" }, el("legend", { class: "h3", text: "Work out what uses the space" }),
        el("p", { class: "small muted", text: COSTS.usage }),
        el("div", { class: "option-cards" }, radios.map((r) => el("label", { class: "option-card" }, r.input, el("strong", { text: r.t }))))),
      field("Storage page updates", refresh, { hint: "Sizes update by themselves while the page is open, or only when you press Check again." }),
      el("label", { class: "check" }, daily, el("span", { class: "check__text" }, el("strong", { text: "Keep a daily record of used space" }),
        el("span", { class: "check__hint", text: "For the Space used over time chart and when the pool will be full. Nothing noticeable." }))),
    ];
    save = async () => {
      const picked = radios.find((r) => r.input.checked);
      await saveGeneral({ performance: { usage_every: picked ? picked.v : "ask", storage_refresh: Number(refresh.value), space_log: daily.checked } });
      return true;
    };
  } else if (id === "apps") {
    const finder = await appFinder();
    nodes = [finder.box];
    save = async () => (finder.add && finder.ticked() ? !!(await finder.add()) : true);  // nothing ticked: just go on
  } else if (id === "keys") {
    // Starboard reads each key from the app's own files first (owner, 10 November 2026: nothing to type during
    // set-up). A box shows only for an app whose key it could not read.
    let read = { found: [], missing: [] };
    try { read = await api("/api/services/read-keys", { method: "POST", body: {} }); config = read.config; } catch { /* the boxes below still work */ }
    const rows = types(Object.keys(KEY_PLACE)).filter((s) => !s.has_api_key).map((s) => {
      const input = el("input", { class: "input", type: "password", autocomplete: "off", "aria-label": `API key for ${s.name}` });
      return { s, input, node: field(`${s.name} API key`, input, { hint: `In ${s.name}: ${KEY_PLACE[s.type]}.`, span: true }) };
    });
    const got = read.found.length ? notice("success", `Starboard has ${read.found.length === 1 ? "the key" : "the keys"} for ${read.found.join(", ")}`,
      read.found.length === 1 ? "It read it from the app's own settings, so there is nothing to type for it." : "It read them from each app's own settings, so there is nothing to type for them.") : null;
    nodes = rows.length
      ? [got, el("p", { text: `Starboard could not read ${rows.length === 1 ? "this key" : "these keys"} itself, so ${rows.length === 1 ? "it is" : "they are"} asked for here.` }),
        el("div", { class: "form-stack" }, rows.map((r) => r.node)), el("p", { class: "small muted", text: "Leave a box empty to add that key later in Manage apps." })].filter(Boolean)
      : [got || notice("success", "Starboard has every key it needs", "There is nothing to type here.")];
    save = async () => {
      for (const r of rows.filter((x) => x.input.value.trim())) {
        const saved = await api("/api/services", { method: "POST", body: serviceBody(r.s, { api_key: r.input.value.trim() }) });
        config = saved.config;
      }
      return true;
    };
  } else if (id === "jellyfin") {
    const box = (key, label, hint) => {
      const input = el("input", { type: "checkbox", checked: !!config.extras[key] });
      return { key, input, node: el("label", { class: "check" }, input, el("span", { class: "check__text" }, el("strong", { text: label }), el("span", { class: "check__hint", text: hint }))) };
    };
    const picks = [box("livetv", "Live TV channels and guide", "Free channels for Jellyfin's Live TV, with guides. Needs Jellyfin's Live TV folder (./install.sh asks)."),
      box("import_keep", "Bring in watch history", "From Plex, Emby or another Jellyfin. You choose where from in Settings, Apps, Jellyfin."),
      box("defaults", "Defaults for every user", "Live TV opens on the Guide for everyone who has not chosen otherwise.")];
    nodes = [el("div", { class: "switch-list" }, picks.map((x) => x.node))];
    save = async () => {
      await saveGeneral({ extras: Object.fromEntries(picks.map((x) => [x.key, x.input.checked])) });
      if (picks[0].input.checked && !config.livetv_ready) {
        const stack = await api("/api/stack");
        remember({ livetv: `${stack.defaults.config_dir}/jellyfin/iptv` });
        await saveHost();
      }
      return true;
    };
  } else if (id === "hours") {
    const on = el("input", { type: "checkbox", checked: config.download_hours.enabled });
    const hour = (v) => el("select", { class: "select" }, Array.from({ length: 24 }, (_, h) => el("option", { value: String(h), text: `${String(h).padStart(2, "0")}:00`, selected: h === v })));
    const start = hour(config.download_hours.start);
    const end = hour(config.download_hours.end);
    nodes = [el("label", { class: "check" }, on, el("span", { class: "check__text" }, el("strong", { text: "Yes, only download between" }))),
      el("div", { class: "form-grid" }, field("From", start), field("Until", end))];
    save = async () => { await saveGeneral({ download_hours: { enabled: on.checked, start: Number(start.value), end: Number(end.value) } }); return true; };
  } else if (id === "alerts") {
    const kinds = [["", "Not now", "No alerts. Starboard does not watch in the background."], ["ntfy", "ntfy", "A free push service with a phone app; you choose a private topic."],
      ["gotify", "Gotify", "Your own push server."], ["webhook", "A webhook", "Starboard posts JSON to an address you choose."]];
    const name = `alert-${Date.now()}`;
    const radios = kinds.map(([v, t, h]) => {
      const input = el("input", { type: "radio", name, value: v, checked: (config.watch.enabled ? config.watch.channel.kind : "") === v });
      return el("label", { class: "option-card" }, input, el("strong", { text: t }), el("small", { text: h }));
    });
    const url = el("input", { class: "input", inputmode: "url", autocomplete: "off", value: config.watch.channel.url || "", placeholder: "https://ntfy.sh/a-long-private-name" });
    const token = el("input", { class: "input", type: "password", autocomplete: "off" });
    const health = el("input", { type: "checkbox", checked: guideMemory().health !== false });
    nodes = [el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Where alerts go" }), el("div", { class: "option-cards" }, radios)),
      el("div", { class: "form-grid" }, field("Address", url, { span: true }), field("Token (if it needs one)", token, { span: true })),
      el("label", { class: "check" }, health, el("span", { class: "check__text" }, el("strong", { text: "Check each disk's health every 30 minutes" }),
        el("span", { class: "check__hint", text: "A small script reads each disk's health report as root, so Starboard can warn you before a disk fails. It is set up on the server with one command at the end." })))];
    // A restore brought its alerts back: only disk health is asked, as in the terminal (DASH-265).
    const restored = (guideMemory().start || "new") === "restore";
    if (restored) nodes = nodes.slice(2);
    save = async () => {
      const kind = root.querySelector(`input[name="${name}"]:checked`)?.value || "";
      if (!restored) await saveGeneral({ watch: kind ? { enabled: true, channel: { kind, url: url.value, token: token.value } } : { enabled: false } });
      remember({ health: health.checked });
      await saveHost();
      return true;
    };
  } else if (id === "movehow") {
    // DASH-266: the same words as the terminal set-up (web/setup-answers.json).
    const w = (await (await fetch("/setup-answers.json", { cache: "no-cache" })).json()).move;
    const name = `movehow-${Date.now()}`;
    const into = guideMemory().moveInto !== false;
    nodes = [el("fieldset", {}, el("legend", { class: "visually-hidden", text: "What happens to them" }), el("div", { class: "option-cards" },
      [["into", w.into, w.into_about, into], ["keep", w.keep, w.keep_about, !into]].map(([v, t, about, on]) => el("label", { class: "option-card" },
        el("input", { type: "radio", name, value: v, checked: on }), el("strong", { text: t }), el("small", { text: about })))))];
    save = async () => { remember({ moveInto: root.querySelector(`input[name="${name}"]:checked`)?.value === "into" }); return true; };
  } else if (id === "move") {
    // DASH-266: the move itself, the same section as Settings, Your install: move into Reelix, then Starboard runs them.
    nodes = [takeoverSection()];
  } else if (id === "docker") {
    // DASH-139, DASH-267: the same words as the terminal set-up (web/setup-answers.json). For a move, Yes is
    // recommended, because the move needs it; for a new install, No, with what that means.
    const w = (await (await fetch("/setup-answers.json", { cache: "no-cache" })).json()).docker;
    const move = (guideMemory().start || "new") !== "new";
    const name = `docker-${Date.now()}`;
    const chosen = guideMemory().docker;
    const cards = (move ? [["yes", w.yes, true], ["no", w.no, false]] : [["no", w.no, true], ["yes", w.yes, false]]).map(([v, t, rec]) =>
      el("label", { class: "option-card" }, el("input", { type: "radio", name, value: v, checked: chosen === undefined ? rec : (chosen ? v === "yes" : v === "no") }),
        el("strong", { text: t + (rec ? " (recommended)" : "") })));
    nodes = [el("p", { text: w.intro }), el("p", { text: move ? w.move : w.without }),
      el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Docker access" }), el("div", { class: "option-cards" }, cards))];
    save = async () => {
      const yes = root.querySelector(`input[name="${name}"]:checked`)?.value === "yes";
      remember({ docker: yes });
      await saveHost();
      return true;
    };
  } else if (id === "preset") {
    const name = `preset-${Date.now()}`;
    // The recommended preset at the top and marked, as in the terminal set-up.
    const rec = config.preset_recommended || "balanced";
    const order = [rec, ...["small", "balanced", "everything"].filter((k) => k !== rec)];
    const current = config.performance.preset === "custom" ? rec : config.performance.preset;
    const radios = order.map((k) => el("label", { class: "option-card" },
      el("input", { type: "radio", name, value: k, checked: current === k }),
      el("strong", { text: config.presets[k] + (k === rec ? " (recommended)" : "") }), el("small", { text: config.preset_about[k] })));
    nodes = [el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Preset" }), el("div", { class: "option-cards" }, radios))];
    save = async () => { await saveGeneral({ preset: root.querySelector(`input[name="${name}"]:checked`).value }); return true; };
  } else if (id === "names") {
    nodes = [notice("info", "Starboard answers only to names it knows", "It opens at IP addresses (such as this server's), localhost and this computer's own name. If you open it with another name, such as your own domain, add that name to STARBOARD_ALLOWED_HOSTS in .env on the server and run ./update.sh."),
      el("p", { class: "small muted", text: "This stops a trick called DNS rebinding, where a web page reaches Starboard through a name it controls." })];
  }
  return { nodes, save };
}
// The set-up's step names and questions, the same file the terminal set-up reads (web/setup-steps.json), so a step
// is called the same in both.
let STEP_TABLE = null;
async function stepTable() {
  if (!STEP_TABLE) {
    try {
      const r = await fetch("/setup-steps.json", { cache: "no-cache" });
      STEP_TABLE = Object.fromEntries((await r.json()).steps.map((x) => [x.id, x]));
    } catch { STEP_TABLE = {}; }
  }
  return STEP_TABLE;
}
function stepNamed(table, id) {
  const x = table[id] || {};
  return { title: x.title || id, question: x.question || "", help: x.help || "" };
}
// Set-up guide ----------------------------------------------------------------
// What the guide chose, kept while it hands over to Install apps and back (this tab only).
function guideMemory() {
  try { return JSON.parse(sessionStorage.getItem("starboard-guide") || "{}"); } catch { return {}; }
}
function remember(values) {
  try { sessionStorage.setItem("starboard-guide", JSON.stringify({ ...guideMemory(), ...values })); } catch { /* private window */ }
}
// The changes to this computer, for ./install.sh: the same options as the terminal set-up (starboard/start.py).
async function saveHost() {
  const m = guideMemory();
  return api("/api/setup/host", { method: "POST", body: { media: m.media || "", livetv: m.livetv || "", health: m.health !== false, docker: !!m.docker } });
}
function showProblemNear(input, message) {
  problem(message, input);
  input.focus();
}
// The library's wizard: a step list, one question per step, Continue saves it, Back, Skip this step, and Keep the
// defaults and finish at the top. Steps that do not apply (no Jellyfin, no download apps) are left out.
// Opened after the first password, and from Settings, General, Set-up guide.

const KEY_PLACE = {
  sonarr: "Settings, General, API key", radarr: "Settings, General, API key", lidarr: "Settings, General, API key",
  readarr: "Settings, General, API key", prowlarr: "Settings, General, API key", bazarr: "Settings, General, API key",
  qbittorrent: "Options, Web UI, API key (5.2 or later)", sabnzbd: "Config, General, API Key",
  jellyfin: "Dashboard, API keys", seerr: "Settings, General, API key", audiobookshelf: "Settings, API Keys (an admin's key)",
};

function wizardFrame({ root, steps, index, onBack, onSkip, onContinue, continueText = "Continue", busy = false }) {
  const step = steps[index];
  const list = el("ol", { class: "steps steps--collapse", "aria-label": "Steps" }, steps.map((st, i) => el("li", {
    "data-done": i < index ? "" : null, "aria-current": i === index ? "step" : null }, st.title,
    i < index ? el("span", { class: "visually-hidden", text: ", done" }) : i === index ? el("span", { class: "visually-hidden", text: ", current step" }) : null)));
  const short = el("p", { class: "steps__short", text: `Step ${index + 1} of ${steps.length}: ${step.title}` });
  const cont = el("button", { type: "button", class: "btn btn--primary", disabled: busy, onclick: onContinue }, continueText);
  const foot = el("div", { class: "wizard__foot" }, cont,
    index > 0 ? el("button", { type: "button", class: "btn", onclick: onBack }, "Back") : null,
    step.skippable === false ? null : el("button", { type: "button", class: "btn btn--quiet", onclick: onSkip }, "Skip this step"));
  const heading = el("h2", { id: "wiz-h", tabindex: "-1", text: step.question });
  root.replaceChildren(list, short, el("section", { class: "panel", "aria-labelledby": "wiz-h" },
    el("div", { class: "stack-1" }, heading, step.intro ? el("p", { class: "muted", text: step.intro }) : null),
    ...step.nodes.filter((n) => !n?.classList?.contains("help-links")), stepHelp(step), foot));
  return { heading, cont };
}

// The step's help at the bottom of the step, above the buttons (LIBRARY.md, Help links): the step's own help
// ("Which one is right for me?") first, then its article in the help centre (web/setup-steps.json, the same for
// the terminal set-up), in one row.
function stepHelp(step) {
  const links = step.nodes.filter((n) => n?.classList?.contains("help-links")).flatMap((n) => [...n.childNodes]);
  if (step.help) links.push(helpButton("Help with this step", { page: step.help, title: `Help: ${step.question}`, back: "Back to set-up" }));
  return links.length ? el("p", { class: "help-links" }, links) : null;
}

async function startGuide() {
  const root = $("#guide");
  root.removeAttribute("aria-busy");
  const types = (t) => config.services.filter((s) => s.enabled !== false && t.includes(s.type));
  const head = $(".page-head");
  if (!$("#guide-finish", head)) {
    head.append(el("div", { class: "actions" }, el("button", { type: "button", class: "btn btn--quiet", id: "guide-finish", onclick: () => go(steps.length - 1) }, "Keep the defaults and finish")));
  }
  const T = await stepTable();
  let steps = [];
  let index = 0;
  let hasDisks = false;
  try { hasDisks = (await api("/api/system")).disks.length > 0; } catch { /* leave the step out */ }
  let dockerAccess = true;  // asked only when Starboard does not have it (DASH-139, DASH-267)
  try { dockerAccess = !!(await api("/api/stack")).docker; } catch { /* not asked */ }
  // DASH-269: a new install runs Install apps' steps here, in this wizard, with one step count (install.js).
  let flow = null;
  // DASH-266: a move into Reelix runs the same steps, to put Reelix beside the old apps first, unless Reelix is there.
  let reelixThere = config.services.some((x) => x.icon === "reelix");
  try { reelixThere = reelixThere || !!(await api("/api/reelix/move")).sources?.length; } catch { /* as if not */ }
  const moveInto = () => (guideMemory().start || "new") !== "new" && (guideMemory().start || "new") !== "restore" && guideMemory().moveInto !== false;
  const needFlow = () => ((guideMemory().start || "new") === "new" || (moveInto() && !reelixThere) ||
    ((guideMemory().start || "new") === "restore" && !!guideMemory().restoreInstall)) && typeof installFlow === "function";
  const loadFlow = async () => {
    if (!needFlow()) return;
    if (!flow) {
      try { flow = await installFlow({ chosenMedia: guideMemory().media || "" }); } catch (e) { problem(e.message); return; }
    }
    const install = (guideMemory().start || "new") === "restore" ? guideMemory().restoreInstall : null;
    if (install && !flow.fromBackup) {  // the backup's choice; nothing is asked again but the folder and the VPN's secrets
      flow.fromBackup = true;
      Object.assign(flow.state, { apps: new Set(install.apps || []), install: "custom", installApplied: true,
        config_dir: install.config_dir || flow.state.config_dir, puid: install.puid ?? flow.state.puid, pgid: install.pgid ?? flow.state.pgid,
        tz: install.tz || flow.state.tz, reelix_edition: install.reelix_edition || "lite",
        vpn: { provider: install.vpn?.provider || "", type: install.vpn?.type || "wireguard", countries: install.vpn?.countries || "",
          wireguard_addresses: install.vpn?.wireguard_addresses || "" } });
    }
  };
  await loadFlow();
  document.addEventListener("guide-media", (e) => { if (flow) { flow.state.chosenMedia = e.detail; flow.state.data_dir = e.detail; } });

  // The agreed order (DASH-103), the same as the terminal set-up: each thing is decided before what depends on it.
  const build = () => {
    const list = [];
    const start = guideMemory().start || "new";
    list.push({ id: "how-to-start", ...stepNamed(T, "start"), skippable: false,
      intro: "A new media server, the apps you already run, or a backup of Starboard's settings." });
    if (start === "restore") {
      // DASH-265, DASH-268: the backup brought the settings back, so they are not asked again. When its apps are not
      // on this computer, Storage, the VPN (its secrets are not in backups) and Check bring them back.
      const install = guideMemory().restoreInstall;
      if (install && flow) {
        list.push({ id: "where", ...stepNamed(T, "storage"), skippable: false, intro: "The backup's apps go back with their media in this folder." },
          ...flow.before().filter((x) => x.id === "vpn"), ...flow.finish());
      }
      list.push({ id: "alerts", ...stepNamed(T, "alerts"), intro: "Disk health is a change to this computer, so it is asked again." });
      list.push({ id: "finish", ...stepNamed(T, "finish"), skippable: false });
      return list;
    }
    if (start === "new") {
      list.push({ id: "where", ...stepNamed(T, "storage"), skippable: false,
        intro: "Your films, series, books and downloads go in one media folder. Next, choose what your server does." });
      if (flow) {
        // The agreed order (DASH-265): what to set up and its questions, How much it does, then Check and Start.
        list.push(...flow.before(), { id: "preset", ...stepNamed(T, "preset"), intro: "You can change each part in Settings, Performance." },
          ...flow.finish());
      }
    } else {
      list.push({ id: "apps", ...stepNamed(T, "find"),
        intro: "Starboard looked for apps it knows on this computer. Tick the ones to add; you can add others by hand later." });
      if (!dockerAccess) list.push({ id: "docker", ...stepNamed(T, "docker"), skippable: false });  // before anything moves
      list.push({ id: "movehow", ...stepNamed(T, "movehow"), skippable: false });
      if (moveInto()) {
        // Reelix beside the old apps first, when it is not there: the same steps as a new install, without sites (the
        // move brings them); How much it does before Check, then the move (DASH-265, DASH-266).
        const beside = flow && !reelixThere;
        if (beside) list.push(...flow.before().filter((x) => !["sites", "moving"].includes(x.id)));
        list.push({ id: "preset", ...stepNamed(T, "preset"), intro: "You can change each part in Settings, Performance." });
        if (beside) list.push(...flow.finish());
        list.push({ id: "move", ...stepNamed(T, "move"), skippable: false });
      }
    }
    if (types(Object.keys(KEY_PLACE)).some((s) => !s.has_api_key)) {
      list.push({ id: "keys", ...stepNamed(T, "keys"),
        intro: "With its key, Starboard can show an app's queue, calendar, updates and warnings. Each key stays on the server." });
    }
    const coming = (keys) => !!flow && keys.some((k) => flow.state.apps.has(k));  // installed by this set-up
    if (types(["jellyfin"]).length || coming(["jellyfin"])) list.push({ id: "jellyfin", ...stepNamed(T, "extras"), intro: "Each one is inactive until you tick it. All are in Settings, Apps, Jellyfin later." });
    if (types(["qbittorrent", "nzbget", "sabnzbd"]).some((s) => s.has_api_key) || coming(["qbittorrent", "nzbget", "sabnzbd"])) list.push({ id: "hours", ...stepNamed(T, "hours"), intro: "Starboard pauses qBittorrent, NZBGet, SABnzbd and Soulseek (slskd) outside these hours, for example to keep the internet free in the day." });
    list.push({ id: "alerts", ...stepNamed(T, "alerts"), intro: "Starboard checks your apps every few minutes and tells you when one stops answering or a disk has a problem." });
    if (hasDisks) list.push({ id: "storage", ...stepNamed(T, "storage-page"), intro: "Sorting the space by type reads every file, so you choose when it happens. Everything here is also in Settings, Performance." });
    if (!(start === "new" && flow) && !moveInto()) list.push({ id: "preset", ...stepNamed(T, "preset"), intro: "You can change each part in Settings, Performance." });
    if (!dockerAccess && start === "new") list.push({ id: "docker", ...stepNamed(T, "docker"), skippable: false });  // the last question
    list.push({ id: "finish", ...stepNamed(T, "finish"), skippable: false });
    return list;
  };

  // The step after this one, found in the list as it is now: a step can drop out once it is done (the keys step,
  // when no key is missing), and counting on by one would skip the next step (VM test).
  const after = (id, at) => {
    const list = build();
    const here = list.findIndex((x) => x.id === id);
    return go(here >= 0 ? here + 1 : at);
  };
  const go = async (i) => {
    await loadFlow();
    steps = build();
    index = Math.max(0, Math.min(i, steps.length - 1));
    const step = steps[index];
    step.nodes = [el("p", { class: "muted", text: "Loading…" })];
    let save = async () => true;
    let loading = true;  // Continue waits until the step has loaded, so a quick click cannot skip it
    const frame = () => wizardFrame({ root, steps, index, busy: loading,
      continueText: step.id === "finish" ? "Go to Apps" : step.id === "review" && flow?.ids().has("review") ? "Write the files" : "Continue",
      onBack: () => go(index - 1), onSkip: () => after(step.id, index),
      onContinue: async (e) => {
        const button = e.currentTarget;  // the event forgets it once the save has been awaited
        button.disabled = true;
        try { if (await save()) { if (step.id === "finish") location.href = "/index.html"; else after(step.id, index); } }
        catch (err) { problem(err.message); }
        finally { if (button.isConnected) button.disabled = false; }
      } });
    frame();
    $("#guide-summary").textContent = `Step ${index + 1} of ${steps.length} · about 3 minutes · you can change everything later in Settings`;

    let content;
    if (flow && flow.ids().has(step.id)) {
      // An Install apps step: drawn by install.js; it may ask for another step by its id (Change, or after Basics).
      const goTo = (id) => {
        const list = build();
        const want = id === "folders" && !list.some((x) => x.id === "folders") ? "where" : id;  // the guide's Storage chose the folder
        return go(Math.max(0, list.findIndex((x) => x.id === want)));
      };
      content = await installStep(step.id, flow.state, flow.data, flow.apps, goTo);
      if (!content) return;  // drawn again by a newer go()
      if (step.id === "start") {
        const started = content.save;
        content.save = async () => {
          const ok = await started();
          try { config = await api("/api/config"); } catch { /* the next steps use what they have */ }
          return ok;
        };
      }
    } else {
      content = await stepContent(step.id, root);
    }
    if (step.id !== "finish") { step.nodes = content.nodes; save = content.save; }
    if (step.id === "finish") {
      await saveGeneral({ setup_guide_done: true });
      const apps = config.services.filter((s) => !s.background).length;
      const keyless = types(Object.keys(KEY_PLACE)).filter((s) => !s.has_api_key).map((s) => s.name);
      const facts = [
        ["Apps", `${apps} ${apps === 1 ? "app" : "apps"}${keyless.length ? `; still without a key: ${keyless.join(", ")}` : ""}`, "/settings.html"],
        ["Jellyfin extras", ["livetv", "import_keep", "defaults"].filter((k) => config.extras[k]).map((k) => ({ livetv: "Live TV", import_keep: "history import", defaults: "user defaults" })[k]).join(", ") || "None", "/settings-jellyfin.html"],
        ["Download hours", config.download_hours.enabled ? `${String(config.download_hours.start).padStart(2, "0")}:00 to ${String(config.download_hours.end).padStart(2, "0")}:00` : "Off", "/settings-general.html#download-hours"],
        ["Alerts", config.watch.enabled ? `On, to ${config.watch.channel.kind || "nowhere yet"}` : "Off", "/settings-alerts.html"],
        ["How much it does", config.presets[config.performance.preset] || "Custom", "/settings-performance.html"],
      ];
      step.nodes = [el("dl", { class: "facts" }, facts.flatMap(([k, v, href]) => [el("dt", { text: k }),
        el("dd", {}, v, " · ", el("a", { href }, "Change", el("span", { class: "visually-hidden", text: ` ${k.toLowerCase()}` })))]))];
      try {
        const host = await api("/api/setup/host");
        if (host.command && host.starter) {
          const make = el("button", { type: "button", class: "btn btn--primary", "aria-haspopup": "dialog" }, icon("play"), "Make the change now");
          make.addEventListener("click", () => hostChange(make));
          step.nodes.push(el("h3", { text: "One change to the server, made for you" }),
            el("p", { class: "muted", text: "Free space for your media folder, disk health, the Live TV folder and Docker access need the installer on the server. Starboard's helper on the server makes the change, and shows how it goes here, so you do not need to go to the server." }),
            el("div", { class: "actions" }, make));
        } else if (host.command) {
          step.nodes.push(el("h3", { text: "One change to make on the server" }),
            el("p", { class: "muted", text: "Free space for your media folder, disk health, the Live TV folder and Docker access need the installer on the server. In a terminal there, in the Starboard folder, run:" }),
            el("pre", { class: "code-block", text: host.command }), copyButton(host.command, "Copy the command"));
        }
      } catch { /* nothing to change on the server */ }
    }
    loading = false;
    const { heading } = frame();
    heading.focus();
  };
  const mem = guideMemory();
  if (mem.at === "after-apps") {
    remember({ at: "" });
    const list = build();
    go(list.findIndex((s) => s.id === "where") + 1);
  } else {
    go(0);
  }
}

// Upgrade guide -----------------------------------------------------------------
// After an upgrade that brings settings to choose: What is new, one step per choice, Finish. "Remind me later"
// hides the notice in this browser until the next time it opens; "Keep the defaults and finish" ends it now.

async function startUpgrade() {
  const root = $("#upgrade");
  root.removeAttribute("aria-busy");
  const r = await api("/api/releases");
  const p = r.pending;
  const titles = { storage: "Storage", apps: "New apps", keys: "API keys", jellyfin: "Jellyfin", hours: "Download hours", alerts: "Alerts", preset: "How much it does", names: "Names it answers to" };
  const questions = { storage: "How should Storage keep up to date?", apps: "Add apps Starboard can now find?", keys: "Give Starboard their API keys?", jellyfin: "Use Starboard's Jellyfin extras?",
    hours: "Only download at set hours?", alerts: "Get an alert when something stops?", preset: "How much should Starboard do in the background?", names: "Do you open Starboard with another name?" };
  const steps = [{ id: "new", title: "What is new", question: `What is new in ${p.to}` },
    ...p.review.map((id) => ({ id, title: titles[id] || id, question: questions[id] || titles[id] })),
    { id: "done", title: "Finish", question: "Upgrade finished", skippable: false }];
  // In the slide-out (?panel=1), finishing or Remind me later tells the page around it, which closes the slide-out.
  const inPanel = document.documentElement.classList.contains("in-panel");
  const leave = (what) => { if (inPanel) window.parent.postMessage({ starboard: what }, location.origin); else location.href = "/index.html"; };
  const finish = async () => { await api("/api/releases/seen", { method: "POST" }); leave("upgrade-done"); };
  const head = $(".page-head");
  if (!$("#upgrade-later", head)) {
    head.append(el("div", { class: "actions" },
      el("button", { type: "button", class: "btn btn--quiet", id: "upgrade-later", onclick: () => { try { sessionStorage.setItem(`upgrade-later-${p.to}`, "1"); } catch { /* fine */ } leave("upgrade-later"); } }, "Remind me later"),
      el("button", { type: "button", class: "btn btn--quiet", onclick: finish }, "Keep the defaults and finish")));
  }
  const go = async (index) => {
    const step = steps[index];
    let save = async () => true;
    step.nodes = [el("p", { class: "muted", text: "Loading…" })];
    let loading = true;
    const frame = () => wizardFrame({ root, steps, index, busy: loading, continueText: step.id === "done" ? "Go to Apps" : "Continue",
      onBack: () => go(index - 1), onSkip: () => go(index + 1),
      onContinue: async (e) => {
        const button = e.currentTarget;
        button.disabled = true;
        try { if (await save()) { if (step.id === "done") await finish(); else go(index + 1); } } catch (err) { problem(err.message); }
        finally { if (button.isConnected) button.disabled = false; }
      } });
    frame();
    $("#upgrade-summary").textContent = `From ${p.from} to ${p.to} · ${steps.length} steps · ./update.sh saved your settings first`;
    if (step.id === "new") step.nodes = p.releases.slice().reverse().map((rel) => releaseNotes(rel, 3));
    else if (step.id === "done") step.nodes = [el("p", { text: "Everything else carries on as it was. The release notes stay under the version in the footer." })];
    else { const c = await stepContent(step.id, root); step.nodes = c.nodes; save = c.save; }
    loading = false;
    frame().heading.focus();
  };
  if (!p.releases.length) {
    root.replaceChildren(notice("success", "Nothing to do", `Starboard ${r.current} has nothing new to choose.`), el("div", { class: "actions" }, el("a", { class: "btn", href: "/index.html", text: "Go to Apps" })));
    return;
  }
  go(0);
}

// Alerts --------------------------------------------------------------------

function startAlerts() {
  const w = () => config.watch;
  const save = async (body, message) => {
    try { await saveGeneral({ watch: body }, message); return true; } catch (err) { problem(err.message); return false; }
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
    settingRow("Watch in the background", withCost("Checks your apps every few minutes with no page open, keeps their uptime history and sends the alerts below. Inactive: nothing runs in the background.", "watch"),
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
      el("button", { type: "submit", class: "btn", text: "Save where alerts go" }), savedNote("channel-saved"),
      el("button", { type: "button", class: "btn", id: "alert-test", onclick: async (e) => {
        e.currentTarget.disabled = true;
        try { await api("/api/alerts/test", { method: "POST" }); toast("Test alert sent. Check that it arrived."); }
        catch (err) { problem(`Not sent: ${err.message}`); }
        finally { $("#alert-test").disabled = false; }
      } }, icon("send"), "Send a test alert")),
    channelError);
  channelForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    channelError.replaceChildren();
    try {
      await saveGeneral({ watch: { channel: { kind: kind.value, url: url.value, token: token.value } } });
      token.value = "";
      describe();
      showSaved("channel-saved");
    } catch (err) { channelError.replaceChildren(notice("danger", "Not saved", err.message)); }
  });

  // What to alert on
  const a = () => w().alerts;
  const onOff = (key, labelId, words) => switchFor(labelId, a()[key], (on) => save({ alerts: { [key]: on } }, `${words} ${on ? "activated" : "deactivated"}`));
  const alertRows = el("ul", { class: "settings-rows" },
    settingRow("An app stops answering", "After two checks in a row, so a restart does not alert. Another message when it answers again.", onOff("apps_down", "al-down-l", "App alerts"), "al-down-l"),
    settingRow("A disk reports a problem", "From Disk health: a failed health check, or reallocated, pending or uncorrectable sectors.", onOff("disk_problem", "al-disk-l", "Disk alerts"), "al-disk-l"),
    settingRow("A folder gets full", "For the folders on System, Storage.",
      selectFor("al-full-l", [[0, "Off"], [80, "At 80%"], [85, "At 85%"], [90, "At 90%"], [95, "At 95%"]], a().disk_full, (v, t) => save({ alerts: { disk_full: Number(v) } }, `Full folder alerts: ${t.toLowerCase()}`)), "al-full-l"),
    settingRow("A download needs attention", "When it has needed attention for 30 minutes.", onOff("download_stuck", "al-stuck-l", "Download alerts"), "al-stuck-l"),
    settingRow("The server backup fails", "From System, Backup.", onOff("backup_failed", "al-backup-l", "Backup alerts"), "al-backup-l"),
    settingRow("A certificate runs out soon", "For apps with an outside https:// address. Checked once a day.",
      selectFor("al-cert-l", [[0, "Off"], [7, "7 days before"], [14, "14 days before"], [30, "30 days before"]], a().cert_days, (v, t) => save({ alerts: { cert_days: Number(v) } }, `Certificate alerts: ${t.toLowerCase()}`)), "al-cert-l"));

  const weekly = el("ul", { class: "settings-rows" },
    settingRow("Weekly summary", withCost("On Monday morning: how each app did, disk health and how full your folders are. Sent where alerts go.", "weekly"),
      switchFor("al-week-l", w().weekly, (on) => save({ weekly: on }, on ? "Weekly summary activated" : "Weekly summary deactivated")), "al-week-l"),
    // DASH-105: a new Starboard release, at most one message a week, only where your alerts go.
    settingRow("New Starboard release", "One message when a newer Starboard is out, with a link to what is new. At most once a week, and once for each version.",
      switchFor("al-rel-l", w().releases !== false, (on) => save({ releases: on }, on ? "Release messages activated" : "Release messages deactivated")), "al-rel-l"));

  $("#alerts-sections").removeAttribute("aria-busy");
  $("#alerts-sections").replaceChildren(
    section("al-watch", "Watching", "Uptime history on each app's details needs this active.", watching),
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
    try { await saveGeneral({ extras: body }, message); return true; } catch (err) { problem(err.message); return false; }
  };
  const sw = (labelId, checked, onChange, disabled = false) => {
    const input = el("input", { type: "checkbox", role: "switch", "aria-labelledby": labelId, checked, disabled });
    input.addEventListener("change", async () => { if (!(await onChange(input.checked))) input.checked = !input.checked; else startJellyfin(); });
    return el("label", { class: "switch" }, input);
  };
  const runNow = (key, label, text = `Run ${label} now`) => el("button", { type: "button", class: "btn", onclick: async (e) => {
    e.currentTarget.disabled = true;
    try { await api(`/api/extras/${key}/run`, { method: "POST" }); toast(`${label} started`); setTimeout(startJellyfin, 4000); }
    catch (err) { problem(err.message); }
  } }, icon("play"), text);
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

  // Live TV: a plug-in since DASH-285 once it has moved; until then, as before.
  let livePlugin = null;
  try { livePlugin = (await api("/api/plugins")).plugins.find((x) => x.id === "livetv") || null; } catch { /* as before */ }
  const lt = jobs.livetv;
  const address = el("input", { class: "input", inputmode: "url", autocomplete: "off", value: x().livetv_address, placeholder: d.self_url });
  const addressForm = el("form", { class: "inline-save", novalidate: true },
    field("Address Jellyfin uses to reach Starboard", address, { hint: `For channel logos and Pluto streams. Blank: ${d.self_url}. Jellyfin must be able to open it, so Starboard needs home network access on.` }),
    el("button", { type: "submit", class: "btn", text: "Save address" }), savedNote("livetv-address-saved"));
  addressForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (await save({ livetv_address: address.value })) { await startJellyfin(); showSaved("livetv-address-saved"); }
  });
  // Where Jellyfin sees the files (DASH-229): blank lets Starboard work it out for an Install apps stack.
  const jfFolder = el("input", { class: "input", autocomplete: "off", spellcheck: "false", value: x().livetv_jellyfin_folder || "", placeholder: "/config/iptv" });
  const jfFolderForm = el("form", { class: "inline-save", novalidate: true },
    field("Live TV folder as Jellyfin sees it", jfFolder, { hint: "Starboard adds the channels and guides to Jellyfin itself. Blank: Starboard works it out when it installed Jellyfin." }),
    el("button", { type: "submit", class: "btn", text: "Save folder" }), savedNote("livetv-folder-saved"));
  jfFolderForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (await save({ livetv_jellyfin_folder: jfFolder.value })) { showSaved("livetv-folder-saved"); }
  });
  const liveRows = el("ul", { class: "settings-rows" },
    settingRow("Build Live TV channels and guide", withCost(lt.what + ". Free channels only: Samsung TV Plus, Pluto TV and Free-TV, with Sky-style numbers.", "livetv"),
      sw("lt-on-l", x().livetv, (on) => save({ livetv: on }, on ? "Live TV activated" : "Live TV deactivated")), "lt-on-l"),
    settingRow("White channel logos", withCost(d.pillow ? "Turns each logo white on a clear background, with Pillow (open source, credited in About). Inactive: channels keep their own logos." : "Needs Pillow, which this install does not have. Channels keep their own logos.", "white"),
      sw("lt-white-l", x().white_logos && d.pillow, (on) => save({ white_logos: on }, on ? "White logos activated" : "White logos deactivated"), !d.pillow), "lt-white-l"));
  const liveNeeds = lt.needs.length ? notice("warning", "Needs set-up on the server", `Starboard needs ${lt.needs.join(" and ")}. Run ./install.sh and say yes to Live TV.`) : null;
  const liveHelp = el("p", { class: "help-links" }, helpButton("How Jellyfin uses these files", { body: el("p", { text: "With Jellyfin's API key, Starboard adds these to Jellyfin after each run, and leaves your own alone. By hand, in Jellyfin: Dashboard, Live TV. Add a tuner of type M3U for each playlist (channels.m3u, samsung.m3u, pluto.m3u) and an XMLTV guide for each guide file (guide.xml, guide-samsung.xml, guide-pluto.xml), from the folder Jellyfin sees them in." }) }));

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
  const whoPick = el("select", { class: "select", id: "jf-you-pick" },
    el("option", { value: "", text: "Jellyfin's first admin (the one Starboard made)" }),
    users.map((u) => el("option", { value: u, text: u, selected: (config.extras.jellyfin_user || "") === u })));
  whoPick.addEventListener("change", () => saveGeneral({ extras: { jellyfin_user: whoPick.value } }, whoPick.value ? `The Library shows what ${whoPick.value} has watched` : "The Library shows what Jellyfin's first admin has watched"));
  const whose = field("Show what this user has watched", whoPick);
  const mapping = h.accounts.length ? el("div", { class: "table-wrap", "data-stack": true }, el("table", { class: "table" },
    el("caption", { class: "visually-hidden", text: "Accounts and the Jellyfin user each one goes to" }),
    el("thead", {}, el("tr", {}, ["Account", "Films", "Episodes", "Goes to Jellyfin user", "Applied"].map((t) => el("th", { scope: "col", text: t })))),
    el("tbody", {}, h.accounts.map((a) => {
      const pick = el("select", { class: "select", "aria-label": `Jellyfin user for ${a.name}` },
        el("option", { value: "", text: "Do not import" }), users.map((u) => el("option", { value: u, text: u, selected: (a.jellyfin_user || "") === u })));
      pick.addEventListener("change", async () => {
        try { await api("/api/import/mapping", { method: "PUT", body: { mapping: { [a.name]: pick.value } } }); toast(pick.value ? `${a.name} goes to ${pick.value}` : `${a.name} is not imported`); }
        catch (err) { problem(err.message); }
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
    settingRow("Keep applying every hour", withCost("History for films and episodes you do not have yet is applied when they arrive. Inactive: only when you choose Apply now.", "importKeep"),
      sw("im-keep-l", x().import_keep, (on) => save({ import_keep: on }, on ? "History is applied every hour" : "History is applied only when you ask")), "im-keep-l"));

  // Not found
  const last = h.last;
  const missing = last && last.unmatched_count ? section("jf-missing", "Not in Jellyfin yet",
    "Either they are not in Jellyfin yet, or Jellyfin has no TMDB, IMDb or TVDB ID for them. With Keep applying on, they are picked up when they arrive.",
    el("div", { class: "table-wrap", "data-stack": true }, el("table", { class: "table" },
      el("caption", { class: "visually-hidden", text: "Films and episodes not in Jellyfin yet" }),
      el("thead", {}, el("tr", {}, ["Film or episode", "Account"].map((t) => el("th", { scope: "col", text: t })))),
      el("tbody", {}, last.unmatched.map((u) => el("tr", {}, el("th", { scope: "row", "data-label": "Film or episode", text: u.title }),
        el("td", { "data-label": "Account", text: u.account })))))),
    last.unmatched_count > last.unmatched.length ? el("p", { class: "small muted", text: `Showing the first ${last.unmatched.length} of ${last.unmatched_count}.` }) : null) : null;

  // User defaults
  const df = jobs.defaults;
  const defaultRows = el("ul", { class: "settings-rows" },
    settingRow("Give every Jellyfin user the defaults", withCost("Every hour, users who have not chosen otherwise get: Live TV opens on the Guide. New users get it too.", "defaults"),
      sw("df-on-l", x().defaults, (on) => save({ defaults: on }, on ? "User defaults activated" : "User defaults deactivated")), "df-on-l"));

  root.removeAttribute("aria-busy");
  root.replaceChildren(...[
    welcome ? notice("success", "Starboard found Jellyfin", "These are all inactive. Activate what you want; you can change them here at any time.") : null,
    top,
    livePlugin ? section("jf-live", "Live TV", "Free channels and guides for Jellyfin's Live TV.",
      notice("info", "Live TV is a plug-in now", `Its settings, Run Live TV now and its status are in Settings, Plug-ins, Live TV. It is ${livePlugin.state === "enabled" ? "active" : "not active"}. Your channels and guides in Jellyfin are unchanged.`),
      el("div", { class: "actions" }, el("a", { class: "btn", href: "/settings-plugin.html?id=livetv", text: "Open Live TV's settings" })))
    : section("jf-live", "Live TV", "Free channels and guides for Jellyfin's Live TV: guides refreshed daily, channels only when a list changes.", liveNeeds, liveRows, addressForm, jfFolderForm, el("div", { class: "actions" }, jobRun(lt), runNow("livetv", "Live TV")), liveHelp),
    section("jf-import", "Import watch history", "Move what people watched, and where they stopped, from Plex, Emby or another Jellyfin into this Jellyfin.",
      importForm, result, imported, mapping, matchSame ? el("div", { class: "actions" }, matchSame) : null, applyRows,
      el("div", { class: "actions" }, jobRun(jobs.import), h.accounts.length ? runNow("import", "Apply", "Apply now") : null)),
    missing,
    section("jf-defaults", "User defaults", null, defaultRows, el("div", { class: "actions" }, jobRun(df), runNow("defaults", "Defaults"))),
    users.length ? section("jf-you", "Your Jellyfin user",
      "The Library shows what this Jellyfin user has watched, and Mark as watched changes it for them.", whose) : null,
  ].filter(Boolean));
}

// Audiobookshelf ------------------------------------------------------------
// Listening progress from Plex, Jellyfin, Emby or another Audiobookshelf: read it, match each account to an
// Audiobookshelf user, apply. Laid out like Settings, Apps, Jellyfin, Import watch history.

const LISTEN_FROM = [["plex", "A Plex server"], ["jellyfin", "A Jellyfin server"], ["emby", "An Emby server"], ["audiobookshelf", "Another Audiobookshelf"]];
const LISTEN_HINT = {
  plex: "Your Plex token (Plex's help: Finding an authentication token). Only your own account is read, from music libraries with book in their name or that use the Audnexus agent.",
  jellyfin: "An API key from that server's Dashboard, API keys. Every user is read, from audiobooks in a Books library.",
  emby: "An API key from that server's Dashboard, API keys. Every user is read, from audiobooks in a Books library.",
  audiobookshelf: "An admin's API key from that server's Settings, API Keys. Every user is read.",
};

async function startListening() {
  const root = $("#listening-sections");
  let d;
  try { d = await api("/api/listening"); } catch (e) { root.replaceChildren(notice("danger", "Could not load", e.message)); return; }
  const redraw = () => startListening();
  const when = (t) => new Date(t * 1000).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

  // Audiobookshelf itself
  const top = !d.abs
    ? notice("info", "Give Audiobookshelf an admin API key first",
      "In Audiobookshelf: Settings, API Keys, Add API key, for an admin user. Then, in Manage apps, add Audiobookshelf (or edit it) and paste the key. You can read progress before that; applying it needs the key.",
      el("a", { class: "btn", href: "/settings.html" }, "Manage apps"))
    : d.abs_problem ? notice("danger", "Starboard cannot reach Audiobookshelf", `${d.abs_problem}. Check its address and API key in Manage apps.`) : null;

  // Read
  const kind = el("select", { class: "select" }, LISTEN_FROM.map(([v, t]) => el("option", { value: v, text: t })));
  const url = el("input", { class: "input", inputmode: "url", autocomplete: "off" });
  const token = el("input", { class: "input", type: "password", autocomplete: "off" });
  const tokenHint = el("span", {});
  const readError = el("div", { role: "alert" });
  const showHints = () => {
    tokenHint.textContent = LISTEN_HINT[kind.value];
    url.placeholder = { plex: "http://plex:32400", jellyfin: "http://jellyfin:8096", emby: "http://emby:8096", audiobookshelf: "http://audiobookshelf:13378" }[kind.value];
  };
  kind.addEventListener("change", showHints);
  showHints();
  const readButton = el("button", { type: "submit", class: "btn btn--primary", disabled: d.reading }, icon("import"), d.reading ? "Reading…" : "Read the progress");
  const readForm = el("form", { novalidate: true, class: "stack-4" },
    el("div", { class: "form-grid" }, field("Read from", kind, { span: true }), field("Server address", url, { span: true }),
      field("Token or API key", token, { span: true, hint: tokenHint })),
    el("div", { class: "actions" }, readButton), readError);
  const waitForRead = () => { const wait = setInterval(async () => { const now = await api("/api/listening").catch(() => null); if (now && !now.reading) { clearInterval(wait); redraw(); } }, 3000); };
  readForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    readError.replaceChildren();
    try {
      await api("/api/listening/read", { method: "POST", body: { kind: kind.value, url: url.value, token: token.value } });
      toast("Reading the progress. This can take a minute or two.");
      readButton.disabled = true;
      waitForRead();
    } catch (err) { readError.replaceChildren(notice("danger", "Not started", err.message)); }
  });
  if (d.reading) waitForRead();
  const readResult = d.read_result ? notice(d.read_result.ok ? "success" : "danger", d.read_result.ok ? "Progress read" : "Reading did not work", d.read_result.message) : null;
  const imported = d.imported ? el("p", { class: "small muted", text: `${d.source}, read ${when(d.imported)}. ${d.accounts.length} ${d.accounts.length === 1 ? "account" : "accounts"}.` }) : null;

  // Match
  const users = d.abs_users;
  const mapping = d.accounts.length ? el("div", { class: "table-wrap", "data-stack": true }, el("table", { class: "table" },
    el("caption", { class: "visually-hidden", text: "Accounts and the Audiobookshelf user each one goes to" }),
    el("thead", {}, el("tr", {}, ["Account", "Books", "Finished", "Goes to Audiobookshelf user", "Applied"].map((t) => el("th", { scope: "col", text: t })))),
    el("tbody", {}, d.accounts.map((a) => {
      const pick = el("select", { class: "select", "aria-label": `Audiobookshelf user for ${a.name}`, disabled: !users.length },
        el("option", { value: "", text: "Do not copy" }), users.map((u) => el("option", { value: u, text: u, selected: (a.abs_user || "") === u })));
      pick.addEventListener("change", async () => {
        try { await api("/api/listening/mapping", { method: "PUT", body: { mapping: { [a.name]: pick.value } } }); toast(pick.value ? `${a.name} goes to ${pick.value}` : `${a.name} is not copied`); }
        catch (err) { problem(err.message); }
      });
      return el("tr", {}, el("th", { scope: "row", "data-label": "Account", text: a.name }),
        el("td", { "data-label": "Books", class: "numeric", text: String(a.books) }),
        el("td", { "data-label": "Finished", class: "numeric", text: String(a.finished) }),
        el("td", { "data-label": "Goes to" }, pick, a.suggested && !a.abs_user ? el("span", { class: "small muted", text: ` Same name: ${a.suggested}` }) : null),
        el("td", { "data-label": "Applied", class: "numeric", text: String(a.applied) }));
    })))) : null;
  const matchSame = d.accounts.some((a) => a.suggested && !a.abs_user)
    ? el("button", { type: "button", class: "btn", onclick: async () => {
      const m = Object.fromEntries(d.accounts.filter((a) => a.suggested && !a.abs_user).map((a) => [a.name, a.suggested]));
      await api("/api/listening/mapping", { method: "PUT", body: { mapping: m } }); toast("Matched accounts with the same name"); redraw();
    } }, icon("users"), "Match accounts with the same name") : null;

  // Apply
  const keepInput = el("input", { type: "checkbox", role: "switch", "aria-labelledby": "ls-keep-l", checked: config.extras.listening_keep });
  keepInput.addEventListener("change", async () => {
    try { await saveGeneral({ extras: { listening_keep: keepInput.checked } }, keepInput.checked ? "Listening progress applied every hour" : "Listening progress applied only when you ask"); }
    catch (err) { keepInput.checked = !keepInput.checked; problem(err.message); }
  });
  const applyRows = el("ul", { class: "settings-rows" },
    settingRow("Keep applying every hour", withCost("Books that are not in Audiobookshelf yet get their progress once they are scanned in. Inactive: only when you choose Apply now.", "listeningKeep"),
      el("label", { class: "switch" }, keepInput), "ls-keep-l"));
  const applyNow = d.accounts.length ? el("button", { type: "button", class: "btn", disabled: !d.abs || d.job.state === "running", onclick: async (e) => {
    e.currentTarget.disabled = true;
    try {
      await api("/api/extras/listening/run", { method: "POST" });
      toast("Applying listening progress");
      const wait = setInterval(async () => { const now = await api("/api/listening").catch(() => null); if (now && now.job.state !== "running") { clearInterval(wait); redraw(); } }, 3000);
    } catch (err) { problem(err.message); }
  } }, icon("play"), "Apply now") : null;
  const rules = el("p", { class: "help-links" }, helpButton("How Starboard copies progress", { body: [
      el("p", { text: "Each book is matched by its ASIN, then its ISBN, then its title and author, then its folder. A book in several files becomes one position: the earlier files plus the place in the current one. If the two copies differ in length, the position is scaled to fit." }),
      el("p", { text: "Progress a person already has in Audiobookshelf is never changed, and each book is copied once." }),
      el("p", { text: "Audiobookshelf keeps progress per person. Starboard uses the admin key to make a key that acts as each person, writes their progress with it, and deletes it straight away. Any key left behind stops working after 15 minutes." }),
    ] }));

  // Not found
  const last = d.last;
  const missing = last && last.unmatched_count ? section("ls-missing", "Books not found in Audiobookshelf",
    "Either they are not scanned in yet, or their details differ. Check the title, author or ASIN in Audiobookshelf; the next Apply picks them up.",
    el("div", { class: "table-wrap", "data-stack": true }, el("table", { class: "table" },
      el("caption", { class: "visually-hidden", text: "Books not found in Audiobookshelf" }),
      el("thead", {}, el("tr", {}, ["Book", "Author", "Account"].map((t) => el("th", { scope: "col", text: t })))),
      el("tbody", {}, last.unmatched.map((u) => el("tr", {}, el("th", { scope: "row", "data-label": "Book", text: u.title }),
        el("td", { "data-label": "Author", text: u.author || "Unknown" }), el("td", { "data-label": "Account", text: u.account })))))),
    last.unmatched_count > last.unmatched.length ? el("p", { class: "small muted", text: `Showing the first ${last.unmatched.length} of ${last.unmatched_count}.` }) : null) : null;

  root.removeAttribute("aria-busy");
  root.replaceChildren(...[
    top,
    section("ls-copy", "Copy listening progress", "Where everyone is in each audiobook, and what they finished, into Audiobookshelf. Copy it once Audiobookshelf has scanned in your books.",
      readForm, readResult, imported, mapping, matchSame ? el("div", { class: "actions" }, matchSame) : null, applyRows,
      el("div", { class: "actions" }, jobRun(d.job), applyNow), rules),
    missing,
  ].filter(Boolean));
}

// Performance ---------------------------------------------------------------
// Presets set every optional piece of background work at once; changing one by hand makes it Custom.

// small, balanced and everything come from the server (config.preset_about), shared with the terminal set-up.
const PRESET_WORDS = {
  custom: "Your own choices below. Changing anything here or on another Settings page makes it Custom.",
};

async function startPerformance() {
  const root = $("#performance-sections");
  const me = await api("/api/self").catch(() => null);
  const perf = () => config.performance;
  const redraw = () => startPerformance();
  const save = async (body, message) => {
    try { await saveGeneral(body, message); redraw(); return true; } catch (err) { problem(err.message); return false; }
  };
  const sw = (labelId, checked, onChange) => {
    const input = el("input", { type: "checkbox", role: "switch", "aria-labelledby": labelId, checked });
    input.addEventListener("change", async () => { if (!(await onChange(input.checked))) input.checked = !input.checked; });
    return el("label", { class: "switch" }, input);
  };
  const pick = (labelId, options, value, onChange) => {
    const select = el("select", { class: "select", "aria-labelledby": labelId },
      options.map(([v, t]) => el("option", { value: String(v), text: t, selected: String(v) === String(value) })));
    select.addEventListener("change", () => onChange(select.value, select.selectedOptions[0].text));
    return select;
  };

  // Now
  const count = (n, one, many) => `${n} ${n === 1 ? one : many}`;
  const span = (secs) => secs < 3600 ? count(Math.max(1, Math.round(secs / 60)), "minute", "minutes")
    : secs < 172800 ? count(Math.round(secs / 3600), "hour", "hours") : count(Math.round(secs / 86400), "day", "days");
  const threadWords = (names) => {
    const checks = names.filter((n) => /^apps_\d+$/.test(n)).length;
    const requests = names.filter((n) => /process_request_thread/.test(n)).length;
    const own = names.filter((n) => !/^apps_\d+$|process_request_thread|serve_forever|MainThread/.test(n));
    return [`${names.length} threads`, own.length ? `background: ${own.join(", ")}` : "no background work",
      checks ? `${checks} app ${checks === 1 ? "check" : "checks"} waiting` : "", requests ? `${requests} answering ${requests === 1 ? "a page" : "pages"}` : ""].filter(Boolean).join(" · ");
  };
  const now = me ? el("dl", { class: "facts" },
    el("dt", { text: "Memory" }), el("dd", { class: "numeric", text: formatBytes(me.memory) }),
    el("dt", { text: "Processor" }), el("dd", { class: "numeric", text: `${me.cpu_percent < 0.1 ? "under 0.1" : me.cpu_percent < 10 ? me.cpu_percent.toFixed(1) : Math.round(me.cpu_percent)}% on average, over the ${span(me.running_seconds)} since it started` }),
    el("dt", { text: "Running" }), el("dd", { text: threadWords(me.threads) })) : null;

  // Presets
  const presetForm = el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Preset" }),
    el("div", { class: "option-cards option-cards--row" }, ["small", "balanced", "everything", "custom"].map((k) => {
      const input = el("input", { type: "radio", name: "preset", value: k, checked: perf().preset === k });
      input.addEventListener("change", () => { if (k !== "custom") save({ preset: k }, `${config.presets[k]} preset in use`); });
      return el("label", { class: "option-card" }, input, el("strong", { text: k === "custom" ? "Custom" : config.presets[k] }), el("small", { text: k === "custom" ? PRESET_WORDS.custom : config.preset_about[k] }));
    })));

  // Background work
  const w = config.watch;
  const x = config.extras;
  const background = el("ul", { class: "settings-rows" },
    settingRow("System history", withCost("Readings for the charts on System, Overview.", "history"),
      el("div", { class: "inline-save" }, pick("pf-hist-every", [[60, "Every minute"], [300, "Every 5 minutes"], [900, "Every 15 minutes"]], perf().history_every,
        (v, t) => save({ performance: { history_every: Number(v) } }, `History: ${t.toLowerCase()}`)),
        sw("pf-hist-l", perf().history, (on) => save({ performance: { history: on } }, on ? "History activated" : "History deactivated"))), "pf-hist-l"),
    settingRow("Watching and alerts", withCost("Checks your apps with no page open and sends alerts. Where alerts go: Settings, Alerts.", "watch"),
      el("div", { class: "inline-save" }, pick("pf-watch-every", [[1, "Every minute"], [5, "Every 5 minutes"], [10, "Every 10 minutes"], [15, "Every 15 minutes"], [30, "Every 30 minutes"], [60, "Every hour"]], w.every,
        (v, t) => save({ watch: { every: Number(v) } }, `Watching: ${t.toLowerCase()}`)),
        sw("pf-watch-l", w.enabled, (on) => save({ watch: { enabled: on } }, on ? "Watching activated" : "Watching deactivated"))), "pf-watch-l"),
    settingRow("Download hours check", withCost("How often Starboard checks qBittorrent, NZBGet, SABnzbd and Soulseek (slskd) while download hours are active (Settings, General).", "scheduleEvery"),
      pick("pf-sched-l", [[60, "Every minute"], [300, "Every 5 minutes"]], perf().schedule_every,
        (v, t) => save({ performance: { schedule_every: Number(v) } }, `Download hours check: ${t.toLowerCase()}`)), "pf-sched-l"),
    settingRow("Live TV white logos", withCost("Only matters while the Live TV plug-in is active (Settings, Plug-ins).", "white"),
      sw("pf-white-l", x.white_logos, (on) => save({ extras: { white_logos: on } }, on ? "White logos activated" : "White logos deactivated")), "pf-white-l"),
    settingRow("Keep applying imported history", withCost("Settings, Apps, Jellyfin, Import watch history.", "importKeep"),
      sw("pf-imp-l", x.import_keep, (on) => save({ extras: { import_keep: on } }, on ? "History applied every hour" : "History applied only when you ask")), "pf-imp-l"),
    settingRow("Jellyfin user defaults", withCost("Settings, Apps, Jellyfin, User defaults.", "defaults"),
      sw("pf-def-l", x.defaults, (on) => save({ extras: { defaults: on } }, on ? "User defaults activated" : "User defaults deactivated")), "pf-def-l"),
    settingRow("Keep applying listening progress", withCost("Settings, Apps, Audiobookshelf, Copy listening progress.", "listeningKeep"),
      sw("pf-listen-l", x.listening_keep, (on) => save({ extras: { listening_keep: on } }, on ? "Listening progress applied every hour" : "Listening progress applied only when you ask")), "pf-listen-l"),
    settingRow("Work out what uses the space", withCost("Sorts your storage by type (TV, films, books and so on) for the charts on System, Storage.", "usage"),
      pick("pf-usage-l", USAGE_CHOICES, perf().usage_every, (v, t) => save({ performance: { usage_every: v } }, `What uses the space: ${t.toLowerCase()}`)), "pf-usage-l"),
    settingRow("Daily record of used space", withCost("For the Space used over time chart and its forecast on System, Storage.", "spaceLog"),
      sw("pf-space-l", perf().space_log, (on) => save({ performance: { space_log: on } }, on ? "Daily record activated" : "Daily record deactivated")), "pf-space-l"),
    settingRow("Posters on Coming up and the Library", withCost("Inactive: Coming up shows each app's icon, and the Library shows titles on plain tiles.", "posters"),
      sw("pf-post-l", config.show_posters, (on) => save({ show_posters: on }, on ? "Posters activated" : "Posters deactivated")), "pf-post-l"));

  // Pages
  const pages = el("ul", { class: "settings-rows" },
    settingRow("Downloads page updates", withCost("While Downloads is open and in view.", "downloadsRefresh"),
      pick("pf-dl-l", [[0, "Only when I press Check again"], [10, "Every 10 seconds"], [15, "Every 15 seconds"], [30, "Every 30 seconds"], [60, "Every minute"]], perf().downloads_refresh,
        (v, t) => save({ performance: { downloads_refresh: Number(v) } }, `Downloads: ${t.toLowerCase()}`)), "pf-dl-l"),
    settingRow("Storage page updates", withCost("While Storage is open and in view.", "storageRefresh"),
      pick("pf-st-l", STORAGE_REFRESH, perf().storage_refresh, (v, t) => save({ performance: { storage_refresh: Number(v) } }, `Storage: ${t.toLowerCase()}`)), "pf-st-l"),
    settingRow("Monitor page readings", withCost("While Monitor is open and in view.", "monitorRefresh"),
      pick("pf-mon-l", [[2, "Every 2 seconds"], [5, "Every 5 seconds"], [10, "Every 10 seconds"]], perf().monitor_refresh,
        (v, t) => save({ performance: { monitor_refresh: Number(v) } }, `Monitor: ${t.toLowerCase()}`)), "pf-mon-l"),
    settingRow("Numbers on app cards", withCost("Such as 3 in the queue or 120 wanted, on Apps.", "cardNumbers"),
      sw("pf-num-l", perf().card_numbers, (on) => save({ performance: { card_numbers: on } }, on ? "Card numbers activated" : "Card numbers deactivated")), "pf-num-l"));

  root.removeAttribute("aria-busy");
  root.replaceChildren(...[
    now ? section("pf-now", "Starboard now", "Measured on this server while you look.", now) : null,
    section("pf-preset", "Preset", "Sets everything below at once. Features you chose for what they do, such as Live TV and download hours, stay as they are.", presetForm),
    section("pf-bg", "Background work", "Runs with no page open. Each part's thread exists only while it is active.", background),
    section("pf-pages", "While a page is open", "Only while the page is open and in view; a hidden tab asks for nothing.", pages),
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
      ? "Active: phones and other computers on your home network can reach the sign-in page."
      : "Inactive: only the computer Starboard runs on can open it.";
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
        title: "Deactivate access from your home network?",
        message: network.you_are_on_this_computer
          ? el("p", { text: "Phones and other computers lose access straight away. Only this computer, the server, can open Starboard after this." })
          : notice("warning", "You are using another device", "This phone or computer loses access straight away. Only the server itself can open Starboard after this."),
        confirm: "Deactivate network access", danger: true,
      });
      if (!ok) { access.focus(); return; }
      access.checked = false;
    }
    try {
      await saveGeneral({ network_access: want }, want ? "Other devices on your home network can open Starboard now" : "Only this computer can open Starboard now");
      network.network_access = want;
      showNetwork();
      setTimeout(async () => { try { network = await api("/api/network"); showNetwork(); } catch { /* this device lost access */ } }, 1500);
    } catch (e) { access.checked = !want; problem(e.message); }
  });

  // Password
  const current = el("input", { class: "input", type: "password", autocomplete: "current-password", required: true });
  const fresh = el("input", { class: "input", type: "password", autocomplete: "new-password", required: true });
  const again = el("input", { class: "input", type: "password", autocomplete: "new-password", required: true });
  const pwForm = el("form", { novalidate: true },
    el("div", { class: "form-stack" },
      field("Current password", current, { required: true }),
      field("New password", fresh, { required: true }),
      field("Type the new password again", again, { required: true })),
    el("div", { class: "actions" }, el("button", { type: "submit", class: "btn btn--primary", text: "Change password" }), savedNote("password-saved")));
  pwForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    [current, fresh, again].forEach((c) => setError(c, ""));
    if (!current.value) { setError(current, "Enter your current password"); current.focus(); return; }
    if (fresh.value.length < 10) { setError(fresh, `Use at least 10 characters. This one has ${fresh.value.length}.`); fresh.focus(); return; }
    if (fresh.value !== again.value) { setError(again, "The two new passwords are different. Type the new one again."); again.focus(); return; }
    try {
      await api("/api/password", { method: "POST", body: { current: current.value, new: fresh.value } });
      pwForm.reset();
      showSaved("password-saved", "Password changed. Everyone else is signed out");
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
    catch (err) { secure.checked = !secure.checked; problem(err.message); }
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
  // The password again (DASH-280), so a session someone else has cannot sign everyone out.
  everywhere.addEventListener("click", async () => {
    const pw = el("input", { class: "input", type: "password", id: "end-all-password", autocomplete: "current-password", required: true });
    const ok = await confirmDialog({
      title: "Sign out everywhere?",
      message: "Every browser and phone signed in to Starboard is signed out, including this one. Everyone needs the password to sign in again.",
      confirm: "Sign out everywhere", danger: true,
      fields: [el("div", { class: "field" }, el("label", { for: pw.id, text: "Your Starboard password" }), pw)],
    });
    if (!ok) return;
    try { await api("/api/sessions/end-all", { method: "POST", body: { password: pw.value } }); }
    catch (e) { problem(e.message, everywhere); return; }
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
    section("sc-ses", "Sessions", "How long Remember me lasts, and signing out.", daysForm),
    section("sc-keys", "API keys", "For other apps, scripts and AI assistants that read Starboard. Each key only reads, and is shown once.", apiKeys()));
  daysForm.append(
      el("ul", { class: "settings-rows" },
        el("li", { class: "setting" },
          el("div", { class: "setting__text" }, el("span", { class: "setting__label", id: "days-l", text: "Remember me keeps people signed in for" }),
            el("span", { class: "setting__hint", id: "days-h", text: "1 to 90 days. Without Remember me, people are signed out when they close the browser, or after a day." })),
          el("div", { class: "setting__control" }, el("div", { class: "field" },
            el("div", { class: "inline-save" },
              el("div", { class: "input-group days-group" }, days, el("span", { class: "input-group__unit", text: "days" })),
              el("button", { type: "submit", class: "btn" }, "Save", el("span", { class: "visually-hidden", text: " how long" }))),
            daysError))),
        settingRow("Only send the sign-in cookie over HTTPS", el("span", { id: "secure-h", text: "Activate when every address you use starts with https. This applies at once." }), el("label", { class: "switch" }, secure), "secure-l"),
        settingRow("Sign out", "This browser, or every browser and phone at once.", el("div", { class: "actions session-actions" }, signOut, everywhere), "signout-l")));
  showNetwork();
}

// API keys (DASH-274): read-only keys for /api/v1, made with the password and shown once.
function apiKeys() {
  const box = el("div", { class: "stack-4" });
  const list = el("ul", { class: "rows", "aria-live": "polite" });
  const draw = (keys) => list.replaceChildren(...(keys.length ? keys.map((k) => {
    const revoke = el("button", { type: "button", class: "btn btn--quiet btn--compact" }, "Revoke", el("span", { class: "visually-hidden", text: ` ${k.name}` }));
    revoke.addEventListener("click", async () => {
      if (!await confirmDialog({ title: `Revoke ${k.name}?`, message: "Anything using this key stops working at once.", confirm: "Revoke", danger: true })) return;
      try { draw((await api(`/api/keys/${k.id}`, { method: "DELETE" })).keys); toast(`${k.name} revoked`); } catch (e) { problem(e.message, revoke); }
    });
    const meta = [k.scopes.length ? `Reads ${k.scopes.join(", ")}` : "Reads everything", k.expires_at ? `ends ${new Date(k.expires_at).toLocaleDateString()}` : "never ends",
      k.last_used_at ? `last used ${new Date(k.last_used_at).toLocaleString()}` : "not used yet"].join(" · ");
    return el("li", { class: "row row--no-lead" }, el("div", {}, el("div", { class: "row__title", text: k.name }), el("div", { class: "row__meta", text: `${k.prefix}… · ${meta}` })),
      el("div", { class: "row__side" }, revoke));
  }) : [el("li", { class: "empty", text: "No keys yet." })]));
  const name = el("input", { class: "input", id: "key-name", autocomplete: "off", placeholder: "Home Assistant" });
  const ends = el("select", { class: "select", id: "key-ends" }, [["90", "In 90 days"], ["365", "In a year"], ["never", "Never"]].map(([v, t]) => el("option", { value: v, text: t })));
  const pw = el("input", { class: "input", id: "key-password", type: "password", autocomplete: "current-password" });
  const shown = el("div", { "aria-live": "polite" });
  const form = el("form", { class: "form-stack", novalidate: true }, field("Name it after what will use it", name), field("Ends", ends), field("Your Starboard password", pw),
    el("div", { class: "actions" }, el("button", { type: "submit", class: "btn btn--primary", text: "Make a key" })));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const r = await api("/api/keys", { method: "POST", body: { name: name.value, expires_days: ends.value, password: pw.value } });
      pw.value = ""; name.value = "";
      const value = el("input", { class: "input", id: "key-made", readonly: true, value: r.key, spellcheck: "false" });
      const copy = el("button", { type: "button", class: "btn" }, icon("copy"), "Copy");
      copy.addEventListener("click", async () => { try { await navigator.clipboard.writeText(r.key); toast("Key copied"); } catch { value.select(); } });
      shown.replaceChildren(notice("success", "Copy the key now", "Starboard shows it only this once. Send it as Authorization: Bearer, never in an address."),
        field(`${r.item.name}'s key`, value), el("div", { class: "actions" }, copy));
      value.focus(); value.select();
      draw((await api("/api/keys")).keys);
    } catch (err) { problem(err.message, form); }
  });
  api("/api/keys").then((r) => draw(r.keys)).catch((e) => list.replaceChildren(el("li", { class: "empty", text: e.message })));
  box.append(list, shown, form, el("p", { class: "small muted" }, "What the API offers: ", el("a", { href: "/api/v1/openapi.json", text: "the API description (OpenAPI)" }), "."));
  return box;
}

// Update settings (the footer's About and updates) ---------------------------------

async function startAbout() {
  const top = $("#version-notice");
  const check = el("input", { type: "checkbox", role: "switch", "aria-labelledby": "check-l", "aria-describedby": "check-h", checked: config.update_check });
  let v = null;
  const showVersion = () => {
    if (!v) return;
    const latest = (v.latest || "").replace(/^v/, "");
    const repo = /^[\w.-]+\/[\w.-]+$/.test(v.repo || "") ? v.repo : "";
    const notes = repo && v.latest ? el("a", { class: "btn", href: `https://github.com/${repo}/releases/tag/${encodeURIComponent(v.latest)}`, target: "_blank", rel: "noopener noreferrer" },
      "Release notes", el("span", { class: "visually-hidden", text: " (opens in a new tab)" })) : null;
    let box;
    if (latest && isNewer(latest, v.current)) box = notice("info", `Version ${latest} is out`, `You have ${v.current}. Read what changed, then run the update command on the server.`, notes);
    else if (latest) box = notice("success", "You have the newest version", `Version ${v.current}.`);
    else if (!repo) box = notice("info", `You have version ${v.current}`, "Starboard cannot look for new versions, because STARBOARD_REPO is not set on the server.");
    else if (!config.update_check) box = notice("info", `You have version ${v.current}`, "Looking for new versions is inactive. Activate it below to see when one is out.");
    else box = notice("info", `You have version ${v.current}`, "GitHub did not answer, so Starboard does not know yet whether a newer version is out.");
    box.classList.add("notice--page");
    top.replaceChildren(box);
    const facts = $("#about-facts");
    facts.replaceChildren(el("dt", { text: "Version" }), el("dd", { class: "numeric", text: v.current }));
    if (v.since) facts.append(el("dt", { text: "Running since" }), el("dd", { text: new Date(v.since * 1000).toLocaleString("en-GB", { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" }) }));
    if (repo) facts.append(el("dt", { text: "Source code" }), el("dd", {}, el("a", { href: `https://github.com/${repo}`, target: "_blank", rel: "noopener noreferrer" }, "Starboard on GitHub", el("span", { class: "visually-hidden", text: " (opens in a new tab)" }))));
  };
  check.addEventListener("change", async () => {
    try {
      await saveGeneral({ update_check: check.checked }, check.checked ? "Starboard looks for new versions" : "Starboard no longer looks for new versions");
      v = await api("/api/version");
      showVersion();
    } catch (e) { check.checked = !check.checked; problem(e.message); }
  });
  $("#update-check-row").replaceChildren(settingRow("Check GitHub for new releases", el("span", { id: "check-h", text: "Active: Starboard checks every 6 hours at most and shows a notice at the top." }), el("label", { class: "switch" }, check), "check-l"));
  $("#update-command").append(copyButton("./update.sh", "the update command"));
  renderAccess();
  try { v = await api("/api/version"); } catch { /* no notice */ }
  showVersion();
}

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
        installed ? el("span", { class: "chip", "data-tone": "success", text: "Installed" }) : null,
        el("span", { class: "release__date", text: rel.date }),
        el("span", { class: "release__counts" }, ...types.map(([key, label, tone]) =>
          el("span", { class: "chip", "data-tone": tone, text: `${rel[key].length} ${label.toLowerCase()}` })))),
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

// Settings, Reelix: which version runs, and switching either way (stack.switch_reelix). Both versions use the same
// settings folder, so the library, users and settings stay. Reelix's own settings are in reelix-settings.js.
async function startReelix() {
  const root = $("#reelix-sections");
  let d;
  try { d = await api("/api/reelix/editions"); } catch (e) { root.replaceChildren(notice("danger", "Could not look", e.message)); root.removeAttribute("aria-busy"); return; }
  const names = Object.fromEntries(d.editions.map((e) => [e.key, e.name]));
  const status = el("div", { class: "stack-2", "aria-live": "polite" });
  let body;
  if (!d.can_switch) {
    body = [notice("info", "Reelix was not installed here by Starboard",
      "Starboard switches the version only for a Reelix that Install apps set up. For your own Reelix, change its image in your Compose file: ghcr.io/themightytrex/reelix:lite, or ghcr.io/themightytrex/reelix:full for YouTube and Spotify downloads.")];
  } else {
    let want = d.editions.find((e) => e.key !== d.current && e.available)?.key || "";
    const now = el("strong", { text: names[d.current] || d.image });
    const cards = el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Version" }),
      el("div", { class: "option-cards" }, d.editions.map((e) => {
        const radio = el("input", { type: "radio", name: "reelix-edition", value: e.key, checked: e.key === d.current, disabled: !e.available && e.key !== d.current });
        radio.addEventListener("change", () => { want = e.key; button.textContent = `Switch to ${names[e.key]}`; button.disabled = e.key === d.current; });
        const note = e.key === d.current ? "In use now" : !e.available ? "Cannot be downloaded at the moment" : e.recommended ? "Recommended" : "";
        return el("label", { class: "option-card" }, radio, el("strong", { text: e.name }), el("small", { text: e.about }), el("small", { class: "muted", text: note }));
      })));
    const password = el("input", { class: "input", type: "password", autocomplete: "current-password", required: true });
    const button = el("button", { type: "submit", class: "btn btn--primary", text: "Switch", disabled: true });
    const form = el("form", { novalidate: true }, el("div", { class: "form-stack" }, cards,
      field("Your password", password, { required: true, hint: "Switching downloads the other version and restarts Reelix, which takes a minute or two." })),
      el("div", { class: "actions" }, button));
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      setError(password, "");
      if (!want || want === d.current) return;
      if (!password.value) { setError(password, "Enter your password"); password.focus(); return; }
      button.disabled = true;
      status.replaceChildren(el("p", { class: "muted", text: `Switching to ${names[want]}…` }));
      let r;
      try { r = await api("/api/reelix/edition", { method: "POST", body: { edition: want, password: password.value } }); }
      catch (err) {
        button.disabled = false;
        status.replaceChildren();
        if (err.status === 401 || err.status === 429) { setError(password, err.message); password.focus(); }
        else status.replaceChildren(notice("danger", "Reelix was not switched", err.message));
        return;
      }
      password.value = "";
      d.current = want;
      now.textContent = names[want];
      $$("[name=reelix-edition]").forEach((x) => { x.closest("label").querySelector("small.muted").textContent = x.value === want ? "In use now" : ""; });
      if (!r.started) {
        status.replaceChildren(notice("info", "One step on the server", "Starboard changed Reelix's version but cannot start apps itself. Run this in a terminal on the server:"),
          el("pre", { class: "code-block", text: r.command }), copyButton(r.command, "Copy the command"));
        return;
      }
      for (;;) {
        await new Promise((res) => setTimeout(res, 3000));
        const j = await api("/api/stack/job").catch(() => ({}));
        if (!j.finished) continue;
        status.replaceChildren(j.ok ? notice("success", `${names[want]} is running`, "Your library, users and settings are as they were.")
          : notice("danger", "Reelix did not start", "The details are below. The old Compose file is kept in data/stack, next to the new one."),
        j.ok ? "" : el("pre", { class: "code-block", text: j.log || "" }));
        if (j.ok) setTimeout(() => startReelix(), 1500);
        return;
      }
    });
    body = [el("p", {}, "Now: ", now), form];
  }
  // A set-up that did not finish (8 November 2026): Reelix's admin account, Starboard's key, folders and download
  // apps, made with the same password as Starboard (reelix_setup.set_up, /api/reelix/setup).
  const setupParts = [];
  if (d.needs_setup) {
    const pw = el("input", { class: "input", type: "password", autocomplete: "current-password", required: true });
    const go = el("button", { type: "submit", class: "btn btn--primary", text: "Finish setting up Reelix" });
    const said = el("div", { class: "stack-2", "aria-live": "polite" });
    const form = el("form", { novalidate: true }, el("div", { class: "form-stack" },
      field("Your password", pw, { required: true, hint: "Reelix's admin account gets the same password as Starboard, so one password opens both. It is used for this and not kept." })),
      el("div", { class: "actions" }, go));
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      setError(pw, "");
      if (!pw.value) { setError(pw, "Enter your password"); pw.focus(); return; }
      go.disabled = true;
      said.replaceChildren(el("p", { class: "muted", text: "Setting up Reelix…" }));
      let r;
      try { r = await api("/api/reelix/setup", { method: "POST", body: { password: pw.value } }); }
      catch (err) {
        go.disabled = false; said.replaceChildren();
        if (err.status === 401 || err.status === 429) { setError(pw, err.message); pw.focus(); }
        else said.replaceChildren(notice("danger", "Reelix is not set up yet", err.message));
        return;
      }
      pw.value = "";
      said.replaceChildren(notice("success", "Reelix is set up", (r.done || []).join(". ")));
      announce("Reelix is set up");
      setTimeout(() => startReelix(), 4000);
    });
    setupParts.push(section("rx-setup", "Finish setting up Reelix", "Reelix runs, but its set-up did not finish: its admin account, Starboard's key, its folders and its download apps.",
      form, said));
  }
  root.replaceChildren(...setupParts,
    section("rx-version", "Version", "Which Reelix runs is part of your install: change it, and the rest of your install, on Settings, Your install.",
      el("p", {}, "Now: ", el("strong", { text: names[d.current] || d.image || "Not installed by Starboard" })),
      el("div", { class: "actions" }, el("a", { class: "btn", href: "/settings-install.html" }, icon("layers"), "Open Your install"))),
    reelixAdminSections());  // sites to search, media servers and download apps (reelix-settings.js)
  root.removeAttribute("aria-busy");
}

// Settings, Your install: what Starboard installed (Basics, Full install, Everything or your own choice), and changing
// it either way, with the Usenet app and which Reelix (stack.plan_change, /api/install/change). 7 November 2026.
async function startYourInstall() {
  const root = $("#install-sections");
  const facts = (pairs) => el("dl", { class: "facts" }, ...pairs.flatMap(([k, v]) => [el("dt", { text: k }), el("dd", { text: v })]));
  let d;
  try { d = await api("/api/install"); } catch (e) { root.replaceChildren(notice("danger", "Could not look", e.message)); root.removeAttribute("aria-busy"); return; }
  root.removeAttribute("aria-busy");
  const status = el("div", { class: "stack-2", "aria-live": "polite" });
  const how = section("in-how", "How changing works", "The same steps for a bigger install or a smaller one.",
    el("ol", { class: "stack-1" },
      el("li", { text: "Starboard keeps a copy of the set-up file in data/stack, named compose.yaml.before- and the date, so you can go back." }),
      el("li", { text: "It writes the new set-up file, with the same folders, user, time zone and VPN details, and the same passwords it made up before." }),
      el("li", { text: "It downloads the apps being added and starts them. Apps taken away stop and are removed; their settings folders stay, so adding one back later carries on where it left off." }),
      el("li", { text: "From SABnzbd to NZBGet, your Usenet servers move across: address, port, user name, password, connections and SSL. The queue and history do not. From NZBGet to SABnzbd, add your servers in SABnzbd." }),
      el("li", { text: "Reelix is given the new download app in place of the old one, and new apps are added to your dashboard as they answer." }),
      el("li", { text: "Going from the full Reelix to Lite works when Lite is on the same release or newer; Starboard says when it has to wait." })));
  if (!d.written) {
    root.replaceChildren(section("in-now", "Your install", "", notice("info", "Nothing installed by Starboard yet",
      "Install apps sets up your media server. Once it has, this page shows what is installed and changes it."),
      el("div", { class: "actions" }, el("a", { class: "btn btn--primary", href: "/install-apps.html" }, icon("download"), "Install apps"))), takeoverSection(), how);
    return;
  }
  const cur = d.current;
  const names = { basics: "Basics", full: "Full install", all: "Everything", custom: "Your own choice" };
  const editionName = (k) => (d.editions.find((e) => e.key === k) || {}).name || k;
  const usenetName = (k) => (d.usenet_apps.find((u) => u.key === k) || {}).name || "None";
  const want = { install: null, usenet: cur.usenet, reelix_edition: cur.reelix_edition };
  const now = section("in-now", "Your install now", "",
    facts([["Install", names[cur.install] || cur.install], ["Reelix", cur.reelix_edition ? editionName(cur.reelix_edition) : "Not installed"],
      ["Usenet app", usenetName(cur.usenet)], ["Apps", cur.apps.join(", ")], ["Memory when idle", `about ${(cur.memory / 1000).toFixed(1)} GB`]]),
    ...(d.last_change ? [notice("info", "Last change", (d.last_change.notes || []).join(". ") || "Finished")] : []));

  const summary = el("p", { class: "muted", "aria-live": "polite" });
  const describe = () => {
    const parts = [];
    const pick = d.installs.find((i) => i.key === want.install);
    if (pick && !pick.error) {
      if (pick.add.length) parts.push(`adds ${pick.add.join(", ")}`);
      if (pick.remove.length) parts.push(`takes away ${pick.remove.join(", ")}`);
    }
    if (want.usenet && want.usenet !== cur.usenet) parts.push(`uses ${usenetName(want.usenet)} for Usenet in place of ${usenetName(cur.usenet)}`);
    if (want.reelix_edition && want.reelix_edition !== cur.reelix_edition) parts.push(`switches Reelix to ${editionName(want.reelix_edition)}`);
    summary.textContent = parts.length ? `This change ${parts.join("; ")}.` : "Choose a change above.";
    button.disabled = !parts.length;
  };
  const installCards = el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Install" }),
    el("div", { class: "option-cards" }, d.installs.map((i) => {
      const r = el("input", { type: "radio", name: "your-install", id: `your-install-${i.key}`, value: i.key, checked: cur.install === i.key, disabled: !!i.error });
      r.addEventListener("change", () => { want.install = i.key; want.reelix_edition = i.reelix_edition; reelixRadios(); describe(); });
      const lines = i.error ? [i.error] : [i.about,
        cur.install === i.key ? "In use now" : [i.add.length ? `Adds ${i.add.join(", ")}` : "", i.remove.length ? `Takes away ${i.remove.join(", ")}` : ""].filter(Boolean).join(". ") || "Nothing to add or take away",
        `About ${(i.memory / 1000).toFixed(1)} GB of memory`];
      return el("label", { class: "option-card" }, r, el("strong", { text: i.name }), ...lines.map((t) => el("small", { text: t })));
    })));
  const usenetCards = cur.usenet ? el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Usenet app" }),
    el("div", { class: "option-cards option-cards--row" }, d.usenet_apps.map((u) => {
      const r = el("input", { type: "radio", name: "your-usenet", id: `your-usenet-${u.key}`, value: u.key, checked: cur.usenet === u.key });
      r.addEventListener("change", () => { want.usenet = u.key; describe(); });
      return el("label", { class: "option-card" }, r, el("strong", { text: u.name + (u.key === "nzbget" ? " (recommended)" : "") }),
        el("small", { text: u.key === "nzbget" ? "Light on memory and processor." : "More extras; uses more memory." }),
        cur.usenet === u.key ? el("small", { class: "muted", text: "In use now" }) : null);
    }))) : el("p", { class: "muted", text: "No Usenet app is installed. Full install and Everything add NZBGet." });
  const reelixBox = el("div");
  const reelixRadios = () => {
    if (!cur.reelix_edition && !want.install) { reelixBox.replaceChildren(el("p", { class: "muted", text: "Reelix is not installed." })); return; }
    reelixBox.replaceChildren(el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Reelix" }),
      el("div", { class: "option-cards option-cards--row" }, d.editions.map((e) => {
        const r = el("input", { type: "radio", name: "your-reelix", id: `your-reelix-${e.key}`, value: e.key, checked: want.reelix_edition === e.key, disabled: !e.available && e.key !== cur.reelix_edition });
        r.addEventListener("change", () => { want.reelix_edition = e.key; describe(); });
        return el("label", { class: "option-card" }, r, el("strong", { text: e.name }), el("small", { text: e.about }),
          el("small", { class: "muted", text: e.key === cur.reelix_edition ? "In use now" : !e.available ? "Cannot be downloaded at the moment" : "" }));
      }))));
  };
  reelixRadios();

  const password = el("input", { class: "input", type: "password", autocomplete: "current-password", required: true });
  const button = el("button", { type: "submit", class: "btn btn--primary", text: "Change my install", disabled: true });
  const form = el("form", { novalidate: true }, summary, el("div", { class: "form-stack" },
    field("Your password", password, { required: true, hint: "Changing downloads and starts apps, and stops the ones taken away. It takes a few minutes." })),
    el("div", { class: "actions" }, button));
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    setError(password, "");
    if (!password.value) { setError(password, "Enter your password"); password.focus(); return; }
    button.disabled = true;
    status.replaceChildren(el("p", { class: "muted", text: "Writing the new set-up…" }));
    let r;
    try {
      r = await api("/api/install/change", { method: "POST", body: { password: password.value, install: want.install,
        usenet: want.usenet !== cur.usenet ? want.usenet : null, reelix_edition: want.reelix_edition !== cur.reelix_edition ? want.reelix_edition : null } });
    } catch (err) {
      button.disabled = false; status.replaceChildren();
      if (err.status === 401 || err.status === 429) { setError(password, err.message); password.focus(); }
      else status.replaceChildren(notice("danger", "Nothing was changed", err.message));
      return;
    }
    password.value = "";
    if (!r.started) {
      status.replaceChildren(notice("info", "One step on the server", "Starboard wrote the new set-up but cannot start apps itself. Run this in a terminal on the server:"),
        el("pre", { class: "code-block", text: r.command }), copyButton(r.command, "Copy the command"),
        el("p", { class: "muted", text: "Once the apps have started, Starboard finishes off by itself within a minute: it updates the dashboard and Reelix, and moves Usenet servers if you changed the Usenet app. Keep this page open, or come back to it, to see what was done." }));
      // DASH-141: the page shows when the command has run and Starboard is finishing off, then what was done,
      // so it never looks stuck. Starboard writes change-result.json when it has finished (data/stack).
      const waiting = el("div", { class: "meter", role: "status" },
        el("div", { class: "meter__label" }, el("span", { text: "Waiting for the command to be run on the server…" })),
        el("div", { class: "progress progress--busy", role: "progressbar", "aria-label": "Waiting for the command", "aria-valuetext": "Waiting" }, el("span")));
      status.append(waiting);
      const asked = Date.now() / 1000;
      for (let n = 0; n < 720; n++) { // an hour, as long as Starboard waits for the command itself
        await new Promise((res) => setTimeout(res, 5000));
        const d = await api("/api/install").catch(() => null);
        const done = d && d.last_change && d.last_change.finished >= asked;
        if (!done) continue;
        waiting.replaceWith(notice("success", "Your install is changed", (d.last_change.notes || []).join(". ") || "Finished: nothing else needed doing."));
        announce("Your install is changed");
        return;
      }
      waiting.replaceWith(notice("warning", "Not finished yet", "Starboard has not seen the apps start in the last hour. Run the command above on the server, then open this page again."));
      return;
    }
    status.replaceChildren(el("p", { class: "muted", text: "Downloading and starting the apps…" }));
    for (;;) {
      await new Promise((res) => setTimeout(res, 3000));
      const j = await api("/api/stack/job").catch(() => ({}));
      if (!j.finished) continue;
      status.replaceChildren(j.ok ? notice("success", "Your install is changed", "Finishing off: the dashboard and Reelix are being updated. This page shows what was done.")
        : notice("danger", "The apps did not all start", "The details are below. The old set-up file is kept in data/stack."), j.ok ? "" : el("pre", { class: "code-block", text: j.log || "" }));
      if (j.ok) setTimeout(() => startYourInstall(), 20000);
      return;
    }
  });

  root.replaceChildren(now,
    section("in-change", "Change your install", "Bigger or smaller, either way. Apps you added yourself outside Starboard are not touched.", installCards),
    section("in-usenet", "Usenet app", "The app that downloads from Usenet. Your Usenet servers move across from SABnzbd to NZBGet.", usenetCards),
    section("in-reelix", "Reelix", "Reelix, or Reelix with YouTube and Spotify downloads. The library, users and settings stay.", reelixBox),
    section("in-confirm", "Make the change", "", form, status), takeoverSection(), how);
  describe();
}

// Settings, Your install: apps someone already runs from their own Compose file (DASH-151, 127 to 129; 8 November
// 2026). Step 1 moves Radarr, Sonarr and the others into Reelix through Reelix's own migrator (reelix_move.py); step 2
// takes the rest over into Starboard's stack, with copies of their settings and a way back (takeover.py).
function takeoverSection() {
  // A step inside this section: an h3 under the section's h2.
  const section = (id, title, description, ...content) => el("div", { class: "stack-2", role: "group", "aria-labelledby": `${id}-h` },
    el("h3", { id: `${id}-h`, text: title }), description ? el("p", { class: "small muted" }, description) : null, ...content);
  const box = el("div", { class: "stack-2", "aria-busy": "true" }, el("p", { class: "muted", text: "Looking for apps you already run…" }));
  const list = (items) => el("ul", { class: "stack-1" }, items.map((t) => el("li", { text: t })));
  const pw = (hint) => { const i = el("input", { class: "input", type: "password", autocomplete: "current-password", required: true }); return [i, field("Your password", i, { required: true, hint })]; };
  // Each step says what happens under its own buttons (owner, 8 November 2026: a message at the end of the section
  // was out of sight). `out` is that step's message area.
  let status = el("div");
  const failed = (input, err, title, out = status) => {
    if (err.status === 401 || err.status === 429) { setError(input, err.message); input.focus(); }
    else { out.replaceChildren(notice("danger", title, err.message)); out.scrollIntoView({ block: "nearest" }); }
  };
  const follow = async (url, done, out = status) => {
    for (;;) {
      await new Promise((res) => setTimeout(res, 3000));
      const j = await api(url).catch(() => ({}));
      if (j.step) out.replaceChildren(el("p", { class: "muted", text: `${j.step}…` }));
      if (j.finished) return done(j);
    }
  };

  const draw = async () => {
    status = el("div", { class: "stack-2", "aria-live": "polite" });
    let t, m;
    try { [t, m] = await Promise.all([api("/api/takeover"), api("/api/reelix/move")]); }
    catch (e) { box.replaceChildren(notice("danger", "Could not look", e.message)); box.removeAttribute("aria-busy"); return; }
    box.removeAttribute("aria-busy");
    const parts = [];

    // A takeover that can still be rolled back: Roll back, or Keep it.
    if (t.record) {
      const when = new Date(t.record.made * 1000).toLocaleString();
      const [p1, p1f] = pw("Rolling back stops the apps Starboard took over and starts your old ones from their own Compose file, on the versions they ran.");
      const back = el("button", { type: "button", class: "btn btn--danger", text: "Roll back" });
      const keep = el("button", { type: "button", class: "btn", text: "Keep it" });
      back.addEventListener("click", async () => {
        if (!p1.value) { setError(p1, "Enter your password"); p1.focus(); return; }
        back.disabled = keep.disabled = true;
        try { await api("/api/takeover/rollback", { method: "POST", body: { password: p1.value } }); }
        catch (err) { back.disabled = keep.disabled = false; failed(p1, err, "Nothing was rolled back"); return; }
        p1.value = "";
        status.replaceChildren(el("p", { class: "muted", text: "Rolling back…" }));
        follow("/api/takeover/job", (j) => {
          status.replaceChildren(notice(j.ok ? "success" : "danger", j.ok ? "Rolled back" : "Rolling back did not finish", (j.notes || []).join(". ")),
            j.ok ? "" : el("pre", { class: "code-block", text: j.log || "" }));
          if (j.ok) { announce("Rolled back"); setTimeout(draw, 5000); }
        });
      });
      keep.addEventListener("click", async () => {
        if (!p1.value) { setError(p1, "Enter your password"); p1.focus(); return; }
        try { await api("/api/takeover/clear", { method: "POST", body: { password: p1.value } }); }
        catch (err) { failed(p1, err, "Nothing was changed"); return; }
        p1.value = ""; announce("Kept"); draw();
      });
      parts.push(notice("info", `Starboard took over ${t.record.containers.length} apps on ${when}`,
        "Your old settings folders, Compose file and app versions are kept, so you can go back. Keep it once everything works: the way back is then put aside, and nothing is deleted."),
        el("div", { class: "form-stack" }, p1f), el("div", { class: "actions" }, back, keep));
      box.replaceChildren(...parts, status);
      return;
    }
    if (t.error) {
      box.replaceChildren(el("p", { class: "muted", text: t.error === "Starboard found no apps here to take over" ? "Starboard found no apps to take over: every app here is Starboard's already." : t.error }));
      return;
    }
    const p = t.plan;

    // Step 1: into Reelix. Reelix has to run first: on a server set up by hand, Install apps adds it (with NZBGet)
    // next to the old apps, which stay as they are.
    const unmoved = p.unmoved || [];
    let step = 1;
    if (!(m.sources && m.sources.length) && unmoved.length) {
      parts.push(section("tk-install", `Step ${step++}: install Reelix`,
        "Reelix takes the place of " + p.unmoved_apps.join(", ") + ". Install it first, so it can read them before they stop.",
        el("p", { text: "In Install apps, choose Full install. Your apps that already run are left as they are, so it adds only the apps you do not have yet, Reelix among them. Then come back here." }),
        el("div", { class: "actions" }, el("a", { class: "btn btn--primary", href: "/install-apps.html" }, icon("download"), "Install apps"))));
    }
    if (m.needs_setup && m.sources && m.sources.length) {
      parts.push(section("tk-setup", `Step ${step}: finish setting up Reelix`,
        "Reelix runs, but its set-up did not finish, so it cannot read your apps yet.",
        el("div", { class: "actions" }, el("a", { class: "btn btn--primary", href: "/settings-reelix.html" }, icon("settings"), "Finish setting up Reelix"))));
      box.replaceChildren(...parts, status);
      return;
    }
    if (m.sources && m.sources.length) {
      step++;
      const last = m.last;
      const lines = [];
      if (last && last.apps) last.apps.forEach((a) => lines.push(`${a.app}: ${a.state === "finished" ? "moved" : `not finished${a.error ? ` (${a.error})` : ""}`}${(a.not_moved || []).length ? `, ${a.not_moved.length} items not moved` : ""}`));
      const [p2, p2f] = pw("Reelix's admin password is the same as Starboard's.");
      const qbit = el("input", { class: "input", type: "password", autocomplete: "off" });
      const hold = el("input", { type: "checkbox", checked: true });
      const preview = el("button", { type: "button", class: "btn", text: "Show what moves" });
      const run = el("button", { type: "button", class: "btn btn--primary", text: "Move them into Reelix" });
      const shown = el("div", { class: "stack-1" });
      const said = el("div", { class: "stack-2", "aria-live": "polite" });
      const body = () => ({ password: p2.value, qbittorrent_password: qbit.value, hold: hold.checked });
      preview.addEventListener("click", async () => {
        if (!p2.value) { setError(p2, "Enter your password"); p2.focus(); return; }
        preview.disabled = true; shown.replaceChildren(el("p", { class: "muted", text: "Asking Reelix…" }));
        try {
          const r = await api("/api/reelix/move/preview", { method: "POST", body: body() });
          shown.replaceChildren(...r.apps.map((a) => {
            if (a.error) return notice("warning", a.app, a.error);
            const made = Object.entries(a.counts).map(([k, v]) => `${k.replace(/_/g, " ")}: ${v.create || 0} new, ${v.existing || 0} there already${v.skip ? `, ${v.skip} not moved` : ""}`);
            return el("details", {}, el("summary", { text: `${a.app}${a.still_missing.length ? ` (${a.still_missing.length} hidden keys still needed)` : ""}` }),
              list(made), a.skipped.length ? el("p", { class: "small muted", text: "Not moved: " + a.skipped.map((s) => `${s.name} (${s.why})`).join("; ") }) : null);
          }));
        } catch (err) { shown.replaceChildren(); failed(p2, err, "Reelix could not show what moves", said); }
        preview.disabled = false;
      });
      run.addEventListener("click", async () => {
        if (!p2.value) { setError(p2, "Enter your password"); p2.focus(); return; }
        run.disabled = preview.disabled = true;
        try { await api("/api/reelix/move/run", { method: "POST", body: body() }); }
        catch (err) { run.disabled = preview.disabled = false; failed(p2, err, "Nothing was moved", said); return; }
        p2.value = ""; qbit.value = "";
        said.replaceChildren(el("p", { class: "muted", text: "Moving your apps into Reelix. Films and series move in a minute or two; Reelix then finds their files, which can take an hour for a big library." }));
        follow("/api/reelix/move/job", (j) => {
          said.replaceChildren(notice(j.ok ? "success" : "warning", j.ok ? "Moved into Reelix" : "Not everything moved", "What moved, and what did not, is listed in step 1."));
          setTimeout(draw, 3000);
        }, said);
      });
      parts.push(section("tk-reelix", `Step ${step - 1}: move them into Reelix`,
        "Reelix reads each app and adds its films, series, music, books, quality profiles, sites to search and requests. The apps themselves do not change.",
        list(m.sources.map((s) => `${s.app}${s.has_key ? "" : " (Starboard cannot read its key)"}`)),
        lines.length ? notice(unmoved.length ? "warning" : "success", "Last move", lines.join(". ")) : null,
        el("div", { class: "form-stack" }, p2f,
          field("qBittorrent's password", qbit, { hint: `Optional. The password qBittorrent's user ${m.qbittorrent_user || "admin"} signs in with, so Reelix can send downloads to qBittorrent. Starboard checks it with qBittorrent first, and keeps it only in Reelix. Leave it empty to add qBittorrent in Reelix yourself.` }),
          el("label", { class: "check" }, hold, el("span", { class: "check__text" }, el("strong", { text: "Hold the sites to search" }),
            el("span", { class: "check__hint", text: "Switched off in Reelix after the move, so only your old apps search until step 2. Switch them on in Settings, Reelix, Sites to search." })))),
        el("div", { class: "actions" }, preview, run), said, shown));
    }

    // Step 2: take over.
    const cfg = el("input", { class: "input", value: p.settings_folder, autocomplete: "off", spellcheck: false });
    const media = el("input", { class: "input", value: p.media_folder, autocomplete: "off", spellcheck: false });
    const [p3, p3f] = pw("This stops your apps for a few minutes while their settings are copied.");
    const ok = el("input", { type: "checkbox" });
    const go = el("button", { type: "button", class: "btn btn--primary", text: "Take over my apps" });
    const takeSaid = el("div", { class: "stack-2", "aria-live": "polite" });
    go.addEventListener("click", async () => {
      if (!p3.value) { setError(p3, "Enter your password"); p3.focus(); return; }
      go.disabled = true;
      takeSaid.replaceChildren(el("p", { class: "muted", text: "Saving the way back, then stopping your apps and copying their settings…" }));
      try { await api("/api/takeover/start", { method: "POST", body: { password: p3.value, install: p.install, usenet: p.usenet, config_dir: cfg.value, media_dir: media.value, unmoved_ok: ok.checked } }); }
      catch (err) { go.disabled = false; takeSaid.replaceChildren(); failed(p3, err, "Nothing was changed", takeSaid); return; }
      p3.value = "";
      follow("/api/takeover/job", (j) => {
        takeSaid.replaceChildren(notice(j.ok ? "success" : "danger", j.ok ? "Starboard runs your apps now" : "Nothing was changed",
          (j.notes || []).join(". ") || (j.ok ? "Finished." : "Your old apps run again as they were.")), j.ok ? "" : el("pre", { class: "code-block", text: j.log || "" }));
        if (j.ok) { announce("Starboard runs your apps now"); setTimeout(draw, 5000); }
      }, takeSaid);
    });
    const keptLines = Object.entries(p.kept).map(([k, v]) => [k, [v.port_map && `ports ${Object.values(v.port_map).join(", ")}`, v.ports && `also ${v.ports.join(", ")}`,
      v.devices && `devices ${v.devices.join(", ")}`, v.volumes && `${v.volumes.length} folders it uses as they are`, v.image && `its own version (${v.image})`,
      v.env && `${v.env.length} of its own settings`, v.vpn === true && "through the VPN", v.vpn === false && "not through the VPN"].filter(Boolean).join(", ")]).map(([k, t]) => `${k}: ${t || "nothing extra"}`);
    parts.push(section("tk-take", `Step ${step}: Starboard runs your apps`,
      `Starboard takes over the apps in ${p.install_name}. Their settings are copied, never moved, and each keeps its port and what it relies on.`,
      el("h4", { text: "Taken over" }), list(p.take.map((a) => a.app)),
      p.replace.length ? el("h4", { text: "Stopped and removed (settings folders stay)" }) : null,
      p.replace.length ? list(p.replace.map((a) => `${a.app}, replaced by ${a.by}${unmoved.includes(a.name) ? " (not moved into Reelix yet)" : ""}`)) : null,
      p.new.length ? el("h4", { text: "Installed new" }) : null, p.new.length ? list(p.new) : null,
      p.leave.length ? el("h4", { text: "Left as they are" }) : null, p.leave.length ? list(p.leave.map((a) => `${a.name}: ${a.why}`)) : null,
      el("details", {}, el("summary", { text: `What each app keeps, and the ${p.copies.length} folders copied` }), list(keptLines),
        list(p.copies.map((c) => `${c.from} to ${c.to}`))),
      ...p.warnings.map((w) => notice("warning", "Before you start", w)),
      el("div", { class: "form-stack" },
        folderField({ input: cfg, label: "Settings folder", hint: `Where the copies go. Not inside ${p.config_base || "your old settings folder"}.` }).node,
        folderField({ input: media, label: "Media folder", hint: "Where your media and downloads are now. Nothing in it is moved." }).node,
        unmoved.length ? el("label", { class: "check" }, ok, el("span", { class: "check__text" }, el("strong", { text: `Stop ${p.unmoved_apps.join(", ")} without moving them into Reelix` }),
          el("span", { class: "check__hint", text: "Only if you do not need what they hold. Their settings folders stay either way." }))) : null,
        p3f),
      el("div", { class: "actions" }, go), takeSaid,
      el("p", { class: "small muted", text: "Before anything stops, Starboard saves the way back: every app's version, your Compose file and Starboard's own set-up files. Roll back appears here afterwards." })));
    box.replaceChildren(...parts, status);
  };
  draw();
  return pageSection("in-takeover", "Apps you already run", "Apps on this server from your own Compose file: moved into Reelix where Reelix replaces them, and run by Starboard from then on, with a way back.", box);
}

// Advanced settings (DASH-225): every Settings page opens with only its basic settings; one switch at the top shows
// the rest. The choice is saved with Starboard's settings, so it holds on every Settings page and every device.
// The basic settings are the approved table (FULL-INSTALL-AND-APP-SETUP section 3); the sections listed here are the
// advanced ones, marked as each page draws them.
const ADVANCED_SECTIONS = new Set([
  "gn-cat", "gn-card", "gn-up", "gn-logs", "gn-design", "gn-guide",  // General
  "sc-ses",  // Security
  "in-how", "tk",  // Your install
  "rx-mediaservers", "rx-downloadclients", "rx-library", "rx-folders", "rx-information", "rx-files", "rx-requests",
  "rx-notifications", "rx-importlists", "rx-people", "rx-books", "rx-music",  // Reelix
  "jf-defaults", "jf-import", "jf-missing", "jf-you",  // Jellyfin
  "ls-copy", "ls-missing",  // Audiobookshelf
  "al-what", "al-week", "al-watch",  // Alerts
  "pf-bg", "pf-pages", "pf-now",  // Performance
]);

function markAdvanced(root) {
  let hidden = 0;
  $$("section.settings-section", root).forEach((sec) => {
    const id = (sec.getAttribute("aria-labelledby") || "").replace(/-h$/, "");
    if (ADVANCED_SECTIONS.has(id)) { sec.dataset.advanced = ""; hidden += 1; }
  });
  return hidden;
}

function advancedSwitch() {
  const main = $("main .page") || $("main");
  if (!main || $("#advanced-switch") || !$$("[id$='-sections'], #reelix-sections", main).length) return;
  const input = el("input", { type: "checkbox", role: "switch", id: "advanced-switch", checked: !!config.settings_advanced });
  const note = el("p", { class: "small muted", id: "advanced-note" });
  const apply = () => {
    document.body.classList.toggle("show-advanced", input.checked);
    const n = $$("[data-advanced]", main).length;
    const text = input.checked ? "Showing every setting. Your choice is saved for every Settings page."
      : n ? `${n} more ${n === 1 ? "section is" : "sections are"} under Advanced settings.` : "";
    if (note.textContent !== text) note.textContent = text;  // only a real change, or the watcher below would loop
  };
  input.addEventListener("change", async () => {
    apply();
    try { await saveGeneral({ settings_advanced: input.checked }); } catch (e) { problem(e.message); }
  });
  const box = el("div", { class: "advanced-toggle stack-1" },
    switchRow("Advanced settings", "Shows everything each app can change.", input), note);
  ($(".page-head", main) || main.firstElementChild).after(box);
  // Sections are drawn as their data arrives: mark each one as it appears, and keep the note's count right.
  new MutationObserver((changes) => {
    if (changes.every((c) => box.contains(c.target))) return;  // the switch's own note changing is not a new section
    markAdvanced(main);
    apply();
  }).observe(main, { childList: true, subtree: true });
  markAdvanced(main);
  apply();
}

// Settings, Downloads (DASH-226): the VPN (provider, connection, countries, key), the Usenet provider's server with
// Test, and where download hours are. The same words as the set-ups (web/setup-answers.json).
async function startDownloadsSettings() {
  const root = $("#downloads-sections");
  let d;
  try { d = await api("/api/downloads/settings"); } catch (e) { root.replaceChildren(notice("danger", "Could not look", e.message)); root.removeAttribute("aria-busy"); return; }
  const words = await (await fetch("/setup-answers.json", { cache: "no-cache" })).json();
  const parts = [];
  if (d.vpn.on) {
    const provider = el("input", { class: "input", value: d.vpn.provider, spellcheck: "false", autocomplete: "off", id: "dl-vpn-provider" });
    const type = el("select", { class: "select", id: "dl-vpn-type" }, [["wireguard", "WireGuard"], ["openvpn", "OpenVPN"]].map(([v, t]) => el("option", { value: v, text: t, selected: d.vpn.type === v })));
    const countries = el("input", { class: "input", value: d.vpn.countries, placeholder: "such as Netherlands", id: "dl-vpn-countries" });
    const key = el("input", { class: "input", type: "password", autocomplete: "off", id: "dl-vpn-key" });
    const address = el("input", { class: "input", autocomplete: "off", placeholder: "ends with /32", id: "dl-vpn-address" });
    const user = el("input", { class: "input", autocomplete: "off", id: "dl-vpn-user" });
    const password = el("input", { class: "input", type: "password", autocomplete: "current-password", id: "dl-vpn-pw" });
    // Only the fields for the chosen connection, as in the set-ups.
    const addressField = field("WireGuard address", address, { hint: "Only when it changed; leave it empty to keep it." });
    const userField = field("OpenVPN user name", user, { hint: "Leave it empty to keep the one there is." });
    const showType = () => { addressField.hidden = type.value !== "wireguard"; userField.hidden = type.value !== "openvpn"; };
    type.addEventListener("change", showType);
    showType();
    const save = el("button", { type: "button", class: "btn btn--primary" }, "Save and restart the VPN");
    const said = el("div", { "aria-live": "polite" });
    save.addEventListener("click", async () => {
      if (!password.value) { setError(password, "Enter your Starboard password"); password.focus(); return; }
      save.disabled = true;
      const vpn = { provider: provider.value.trim().toLowerCase(), type: type.value, countries: countries.value.trim() };
      if (type.value === "wireguard") Object.assign(vpn, { wireguard_private_key: key.value.trim(), wireguard_addresses: address.value.trim() });
      else Object.assign(vpn, { openvpn_user: user.value.trim(), openvpn_password: key.value.trim() });
      try {
        const r = await api("/api/downloads/vpn", { method: "POST", body: { password: password.value, vpn } });
        password.value = ""; key.value = "";
        said.replaceChildren(notice("success", "Saved", r.said), ...(r.command ? [el("pre", { class: "code-block", text: r.command })] : []));
      } catch (e) { said.replaceChildren(notice("danger", "Not saved", e.message)); }
      finally { save.disabled = false; }
    });
    parts.push(section("dl-vpn", "VPN", "Downloads go through your VPN, so your internet provider sees only the VPN.",
      el("div", { class: "form-stack" },
        field("VPN provider", provider, { hint: "As Gluetun's list writes it, such as surfshark or protonvpn." }), field("Connection", type),
        field("Countries", countries, { hint: "Optional. A nearby country is fastest." }),
        field(d.vpn.has_secret ? "New WireGuard key or OpenVPN password" : "WireGuard key or OpenVPN password", key, { hint: d.vpn.has_secret ? "Leave it empty to keep the one there is." : "" }),
        addressField, userField,
        field("Your Starboard password", password, { required: true, hint: "Saving restarts the VPN, and the apps that go through it, for a moment." })),
      el("div", { class: "actions" }, save), said));
  }
  if (d.usenet.app) {
    const w = words.usenet;
    const inputs = { host: el("input", { class: "input", id: "dl-u-host", autocomplete: "off", spellcheck: "false" }), ssl: el("input", { type: "checkbox", checked: true }),
      port: el("input", { class: "input", inputmode: "numeric", value: "563", id: "dl-u-port" }), username: el("input", { class: "input", id: "dl-u-user", autocomplete: "off" }),
      password: el("input", { class: "input", type: "password", id: "dl-u-pw", autocomplete: "new-password" }), connections: el("input", { class: "input", inputmode: "numeric", value: "8", id: "dl-u-conn" }) };
    const server = () => ({ host: inputs.host.value.trim(), ssl: inputs.ssl.checked, port: inputs.port.value.trim(), username: inputs.username.value.trim(),
      password: inputs.password.value, connections: inputs.connections.value.trim() });
    const said = el("div", { "aria-live": "polite" });
    const test = el("button", { type: "button", class: "btn" }, w.test);
    test.addEventListener("click", async () => {
      said.replaceChildren(el("p", { class: "small muted", text: "Testing…" }));
      const r = await api("/api/setup/test-usenet", { method: "POST", body: { server: server() } });
      said.replaceChildren(r.ok ? notice("success", "It works", r.message) : notice("danger", "It did not work", r.message));
    });
    const add = el("button", { type: "button", class: "btn btn--primary" }, `Add it to ${d.usenet.app}`);
    add.addEventListener("click", async () => {
      add.disabled = true;
      try { said.replaceChildren(notice("success", "Saved", (await api("/api/downloads/usenet", { method: "POST", body: { server: server() } })).said)); }
      catch (e) { said.replaceChildren(notice("danger", "Not saved", e.message)); }
      finally { add.disabled = false; }
    });
    parts.push(section("dl-usenet", "Usenet provider", `${d.usenet.app} downloads from your Usenet provider's server.`,
      el("p", { class: "small", text: d.usenet.servers.length ? `In ${d.usenet.app} now: ${d.usenet.servers.join(", ")}.` : `${d.usenet.app} has no server yet.` }),
      el("div", { class: "form-stack" }, el("p", { class: "small muted", text: w.server_intro }),
        field(w.host, inputs.host, { hint: w.host_hint }), el("label", { class: "check" }, inputs.ssl, el("span", { text: w.ssl })),
        field(w.port, inputs.port, { hint: w.port_hint }), field(w.username, inputs.username), field(w.password, inputs.password),
        field(w.connections, inputs.connections, { hint: w.connections_hint })),
      el("div", { class: "actions" }, add, test), said));
  }
  parts.push(section("dl-hours", "Download hours", "When downloads run, so the internet stays free for everything else.",
    el("p", {}, config.download_hours.enabled ? `On: ${String(config.download_hours.start).padStart(2, "0")}:00 to ${String(config.download_hours.end).padStart(2, "0")}:00. ` : "Off. ",
      el("a", { href: "/settings-general.html#download-hours", text: "Change download hours" }))));
  if (!d.vpn.on && !d.usenet.app) parts.unshift(notice("info", "Nothing to set here yet", "Your install has no VPN and no Usenet app. Add them in Settings, Your install."));
  root.replaceChildren(...parts);
  root.removeAttribute("aria-busy");
}

startPage().then(async (session) => {
  if (!session) return;
  if ($("#releases-list")) { startReleases(session.repo); return; }
  try { config = await api("/api/config"); } catch (e) { problem(e.message); return; }
  advancedSwitch();
  if ($("#app-sections")) startManageApps();
  if ($("#general-sections")) startGeneral();
  if ($("#security-sections")) startSecurity();
  if ($("#alerts-sections")) startAlerts();
  if ($("#jellyfin-sections")) startJellyfin();
  if ($("#listening-sections")) startListening();
  if ($("#performance-sections")) startPerformance();
  if ($("#reelix-sections")) startReelix();
  if ($("#install-sections")) startYourInstall();
  if ($("#downloads-sections")) startDownloadsSettings();
  if ($("#guide")) startGuide();
  if ($("#upgrade")) startUpgrade();
  if ($("#install") && typeof startInstall === "function") startInstall();
  if ($("#copy-sections") && typeof startCopy === "function") startCopy();
  if ($("#version-notice")) startAbout();
  if ($("#general-sections")) {  // DASH-277: long lists load more by themselves, or wait for Show more
    const input = el("input", { type: "checkbox", role: "switch", id: "infinite-scroll", checked: config.infinite_scroll !== false });
    input.addEventListener("change", () => saveGeneral({ infinite_scroll: input.checked },
      input.checked ? "Long lists load more as you near the end" : "Long lists wait for Show more"));
    const box = section("gn-scroll", "Long lists", "The Library, Wanted and History.",
      el("ul", { class: "settings-rows" }, el("li", { class: "setting" }, switchRow("Load more as you scroll",
        "Off: a Show more button at the end instead. With Reduce motion on, the button is always used.", input))));
    const sections = $("#general-sections");
    const wait = new MutationObserver(() => { if (sections.childElementCount && !$("#gn-scroll-h")) { sections.append(box); wait.disconnect(); } });
    wait.observe(sections, { childList: true });
  }
  if ($("#reelix-auto-row")) {  // DASH-263: automatic Reelix updates, off until switched on
    const input = el("input", { type: "checkbox", role: "switch", id: "reelix-auto", checked: !!config.reelix_auto_update });
    input.addEventListener("change", () => saveGeneral({ reelix_auto_update: input.checked },
      input.checked ? "Starboard installs new Reelix versions by itself" : "Reelix updates wait for you, on Apps, Updates"));
    $("#reelix-auto-row").replaceChildren(el("li", { class: "setting" }, switchRow("Install Reelix updates automatically",
      "Needs Docker access. Off: Apps, Updates says when there is one, and you choose.", input)));
  }
  $("#usenet-rights")?.append(usenetRights());
});

// Make the change now (owner, 10 November 2026): the set-up's change to the server, made by the Run first window,
// with its output live in a slide-out and a progress bar. The Starboard password first: only someone who knows it
// can change the server. Nobody can type commands into the server from here; the window runs only the installer.
async function hostChange(opener) {
  const input = el("input", { class: "input", id: "host-password", type: "password", autocomplete: "current-password", required: true });
  const err = el("span", { class: "field-error", id: "host-password-error", hidden: true });
  for (;;) {
    const asked = confirmDialog({ title: "Make the change to the server", message: "Starboard's helper on the server runs the installer with your answers. Type your Starboard password to go ahead.",
      confirm: "Make the change", fields: [el("div", { class: "field" }, el("label", { for: input.id, text: "Your Starboard password" }), input, err)] });
    input.focus();
    if (!(await asked)) return;
    try { await api("/api/setup/host/apply", { method: "POST", body: { password: input.value } }); break; }
    catch (e) { err.textContent = e.status === 401 ? "That password is not right. Check Caps Lock and try again." : e.message; err.hidden = false; input.setAttribute("aria-invalid", "true"); input.value = ""; }
  }
  const bar = el("span");  // its width is set from here (a style property), which the content policy allows
  bar.style.width = "0%";
  const meter = el("div", { class: "progress", role: "progressbar", "aria-label": "Changing the server", "aria-valuemin": "0", "aria-valuemax": "100", "aria-valuenow": "0" }, bar);
  const now = el("p", { "aria-live": "polite", text: "Waiting for the helper on the server…" });
  const out = el("pre", { class: "code-block host-output", tabindex: "0", "aria-label": "What the installer says", hidden: true });
  const close = el("button", { type: "button", class: "btn", text: "Close" });
  const panel = sidePanel({ title: "Changing the server", opener, wide: true, body: [el("div", { class: "stack-4" }, now, meter, out)], foot: [close] });
  close.addEventListener("click", () => panel.close());
  let lost = 0;
  let same = "", since = Date.now();  // a step that does not move for 10 minutes has stopped (VM test N1)
  const tick = async () => {
    if (!document.body.contains(panel.layer)) return;
    let p;
    try { p = await api("/api/setup/host/progress"); lost = 0; }
    catch { lost += 1; now.textContent = "Starboard is starting again with its new settings…"; setTimeout(tick, 3000); return; }  // Docker access restarts it
    const shown = p.of ? Math.round(((p.n || 0) - (p.state === "running" ? 1 : 0)) / p.of * 100) : 0;
    out.hidden = !p.log;  // shown once the installer has said something
    if (p.log && out.textContent !== p.log) { out.textContent = p.log; out.scrollTop = out.scrollHeight; }
    if (p.state === "finished") {
      bar.style.width = "100%"; meter.setAttribute("aria-valuenow", "100");
      now.replaceChildren(notice("success", "The change is made", "Everything the set-up asked for on the server is done. You can close this."));
      close.classList.add("btn--primary");
      return;
    }
    if (p.state === "needs-password") {
      // The set-up helper never uses sudo: disk health is left for one command on the server.
      bar.style.width = "100%"; meter.setAttribute("aria-valuenow", "100");
      const cmd = "cd ~/starboard && ./install.sh --disk-health";
      now.replaceChildren(notice("warning", "One part needs the server's password", "Everything else is done. Disk health needs sudo, which Starboard never uses itself. Run this once in a terminal on the server:"),
        el("pre", { class: "code-block", text: cmd }), copyButton(cmd, "Copy the command"));
      return;
    }
    if (p.state === "failed") {
      now.replaceChildren(notice("danger", "The change stopped", "What the installer said is below. Run first's window on the server shows it too, and the help has each error number."));
      return;
    }
    const where = `${p.state}|${p.n}|${p.name}|${(p.log || "").length}`;
    if (where !== same) { same = where; since = Date.now(); }
    if (p.state === "running" && Date.now() - since > 10 * 60 * 1000) {
      now.replaceChildren(notice("danger", "The change has stopped", "Nothing has happened for 10 minutes. What the installer said is below. Select Make the change now again, or run ./install.sh in the Starboard folder on the server."));
      return;
    }
    bar.style.width = `${Math.max(3, Math.min(97, shown))}%`; meter.setAttribute("aria-valuenow", String(Math.max(0, shown)));
    now.textContent = p.state === "running" && p.name ? `Step ${p.n} of ${p.of}: ${p.name}` : p.window === false ? "Starboard's helper on the server is not answering. Run first or ./install.sh starts it again." : "Waiting for the helper on the server…";
    if (/sudo|password for/i.test((p.log || "").slice(-300))) now.textContent += " The Run first window on the server is asking for the server's password.";
    setTimeout(tick, 2000);
  };
  tick();
}

