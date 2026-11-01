// Settings: apps (add, edit, test, order, remove), general, security and updates.

let config = null;
const SEARCHABLE = ["sonarr", "radarr", "lidarr", "readarr"];

function renderServices() {
  const list = $("#service-list");
  list.replaceChildren();
  if (!config.services.length) list.append(el("li", { class: "empty", text: "No apps yet. Add your first one." }));
  config.services.forEach((s, index) => {
    const type = config.types[s.type]?.label || s.type;
    list.append(el("li", { class: "row service-row" },
      el("div", { class: "service-row__main" }, appIcon(s, "app__icon app__icon--small"), el("div", {},
        el("p", { class: "row__title", text: s.name }),
        el("p", { class: "row__meta", text: [type, s.group || "Other", s.background ? "Background service" : null, s.has_api_key ? "API key saved" : null, s.enabled ? null : "Hidden"].filter(Boolean).join(" · ") }))),
      el("div", { class: "row__side" },
        el("button", { type: "button", class: "btn", disabled: index === 0, "aria-label": `Move ${s.name} up`, onclick: () => move(index, -1) }, "↑"),
        el("button", { type: "button", class: "btn", disabled: index === config.services.length - 1, "aria-label": `Move ${s.name} down`, onclick: () => move(index, 1) }, "↓"),
        el("button", { type: "button", class: "btn", onclick: () => openService(s) }, "Edit", el("span", { class: "visually-hidden", text: ` ${s.name}` })),
        el("button", { type: "button", class: "btn btn-danger", onclick: () => removeService(s) }, "Remove", el("span", { class: "visually-hidden", text: ` ${s.name}` })))));
  });
}

async function move(index, by) {
  const ids = config.services.map((s) => s.id);
  [ids[index], ids[index + by]] = [ids[index + by], ids[index]];
  config = await api("/api/services/order", { method: "POST", body: { ids } });
  renderServices();
  announce("Order saved");
}

const pendingRemove = new Set();
async function removeService(s) {
  // Two clicks: the first asks, the second removes. No browser confirm() pop-up.
  if (!pendingRemove.has(s.id)) {
    pendingRemove.add(s.id);
    toast(`Select Remove again to remove ${s.name}`);
    setTimeout(() => pendingRemove.delete(s.id), 6000);
    return;
  }
  pendingRemove.delete(s.id);
  config = await api(`/api/services/${s.id}`, { method: "DELETE" });
  renderServices();
  toast(`Removed ${s.name}`);
}

function serviceFormValues() {
  const f = $("#service-form");
  return {
    id: f.service_id.value || undefined, type: f.type.value, name: f.name.value, url: f.url.value, link: f.link.value, outside_link: f.outside_link.value, icon: f.icon.value,
    api_key: f.api_key.value, group: f.group.value, background: f.background.checked, follows: f.follows.value, description: f.description.value, enabled: f.enabled.checked,
    quality_profile_id: f.quality_profile_id.value || null, root_folder: f.root_folder.value,
    metadata_profile_id: f.metadata_profile_id.value || null, search_on_add: f.search_on_add.checked,
  };
}

// "Choose for me" names the category it will pick, from the app's name or kind.
function guessGroup() {
  const f = $("#service-form");
  const slug = f.name.value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const index = config.category_of[slug] ?? config.category_of[f.type.value] ?? 3;
  const wanted = config.default_groups[index];
  if (config.groups.includes(wanted)) return wanted;
  return config.groups[index] || config.groups[config.groups.length - 1] || "";  // renamed categories keep their place
}

function updateGroupGuess() {
  const first = $("#svc-group").options[0];
  const guess = guessGroup();
  first.textContent = guess ? `Choose for me (${guess})` : "Choose for me";
}

function updateTypeFields() {
  const type = $("#svc-type").value;
  $("#svc-follows-field").hidden = !$("#svc-background").checked;
  $("#svc-search-fields").hidden = !SEARCHABLE.includes(type);
  $("#svc-meta-field").hidden = !["lidarr", "readarr"].includes(type);
  $("#svc-key-field").hidden = ["jellyfin", "link"].includes(type);
}

function setOptions(select, items, value) {
  select.replaceChildren(el("option", { value: "", text: "First in the list" }), ...items.map((i) => el("option", { value: i.value, text: i.label })));
  select.value = value ?? "";
}

function openService(s = null) {
  const f = $("#service-form");
  f.reset();
  $("#service-title").textContent = s ? `Edit ${s.name}` : "Add an app";
  $("#svc-error").textContent = "";
  $("#svc-test-result").textContent = "";
  $("#svc-type").replaceChildren(...Object.entries(config.types).map(([k, v]) => el("option", { value: k, text: v.label })));
  const groups = [...config.groups];
  if (s?.group && !groups.includes(s.group)) groups.push(s.group);
  $("#svc-group").replaceChildren(el("option", { value: "", text: "Choose for me" }), ...groups.map((g) => el("option", { value: g, text: g })));
  updateGroupGuess();
  $("#svc-follows").replaceChildren(el("option", { value: "", text: "Nothing" }),
    ...config.services.filter((x) => !x.background && (!s || x.id !== s.id)).map((x) => el("option", { value: x.id, text: x.name })));
  setOptions(f.quality_profile_id, s?.quality_profile_id ? [{ value: s.quality_profile_id, label: `Profile ${s.quality_profile_id}` }] : [], s?.quality_profile_id);
  setOptions(f.root_folder, s?.root_folder ? [{ value: s.root_folder, label: s.root_folder }] : [], s?.root_folder);
  setOptions(f.metadata_profile_id, s?.metadata_profile_id ? [{ value: s.metadata_profile_id, label: `Profile ${s.metadata_profile_id}` }] : [], s?.metadata_profile_id);
  if (s) {
    f.service_id.value = s.id; f.type.value = s.type; f.name.value = s.name; f.url.value = s.url;
    f.link.value = s.link === s.url ? "" : s.link;
    f.outside_link.value = s.outside_link || "";
    f.icon.value = s.icon || "";
    f.background.checked = !!s.background;
    f.follows.value = s.follows || ""; f.group.value = s.group || ""; f.description.value = s.description || "";
    f.enabled.checked = s.enabled; f.search_on_add.checked = s.search_on_add !== false;
    f.api_key.placeholder = s.has_api_key ? "Saved (leave empty to keep)" : "";
  } else {
    f.service_id.value = ""; f.api_key.placeholder = "";
  }
  updateTypeFields();
  $("#service-dialog").showModal();
}

async function loadServiceOptions() {
  const f = $("#service-form");
  const result = $("#svc-test-result");
  if (!f.service_id.value) { result.textContent = "Save the app first, then load its profiles and folders."; return; }
  result.textContent = "Loading…";
  try {
    const opts = await api(`/api/services/${f.service_id.value}/options`);
    const keep = serviceFormValues();
    setOptions(f.quality_profile_id, opts.quality_profiles.map((p) => ({ value: p.id, label: p.name })), keep.quality_profile_id);
    setOptions(f.root_folder, opts.root_folders.map((r) => ({ value: r.path, label: r.path })), keep.root_folder);
    setOptions(f.metadata_profile_id, opts.metadata_profiles.map((p) => ({ value: p.id, label: p.name })), keep.metadata_profile_id);
    result.textContent = "Profiles and folders loaded.";
  } catch (e) {
    result.textContent = e.message;
  }
}

async function testService() {
  const result = $("#svc-test-result");
  result.textContent = "Testing…";
  try {
    const r = await api("/api/services/test", { method: "POST", body: serviceFormValues() });
    result.textContent = r.state === "up" ? `Connected${r.version ? `, version ${r.version}` : ""} (${r.ms} ms).` : r.message;
  } catch (e) {
    result.textContent = e.message;
  }
}

async function saveService(event) {
  event.preventDefault();
  const error = $("#svc-error");
  error.textContent = "";
  try {
    const saved = await api("/api/services", { method: "POST", body: serviceFormValues() });
    config = saved.config;
    const wasNew = !$("#service-form").service_id.value;
    $("#service-form").service_id.value = saved.id;
    renderServices();
    if (wasNew && SEARCHABLE.includes($("#svc-type").value)) {
      $("#service-title").textContent = "App saved. Choose what to use when adding";
      await loadServiceOptions();
      return;
    }
    $("#service-dialog").close();
    toast("App saved");
  } catch (e) {
    error.textContent = e.message;
  }
}

function renderGeneral() {
  const f = $("#general-form");
  if (f) {
    f.site_name.value = config.site_name;
    f.groups.value = config.groups.join(", ");
    f.show_home_address.checked = config.show_home_address;
    f.show_outside_address.checked = config.show_outside_address;
    const box = $("#default-design");
    box.replaceChildren(...Object.entries(DESIGNS).map(([k, [label, help]]) => el("label", { class: "design-option" },
      el("input", { type: "radio", name: "design", value: k, checked: config.design === k }), el("span", { text: label }), el("small", { text: help }))));
  }
  const s = $("#session-form");
  if (s) {
    s.session_days.value = config.session_days;
    s.secure_cookies.checked = config.secure_cookies;
  }
  if ($("#update-check")) $("#update-check").checked = config.update_check;
}

async function saveGeneral(body, message) {
  try {
    config = await api("/api/config/general", { method: "PUT", body });
    renderGeneral();
    toast(message);
    $$("[data-site-name]").forEach((n) => { n.textContent = config.site_name; });
  } catch (e) {
    toast(e.message);
  }
}

let network = null;
let confirmLocalOnly = false;

async function showNetwork() {
  try {
    network = await api("/api/network");
  } catch { return; }
  $("#network-access").checked = network.network_access;
  $("#network-forced").hidden = !network.forced_by;
  if (network.forced_by) {
    $("#network-forced").textContent = `Set by ${network.forced_by} on the server, so it cannot be changed here.`;
    $("#network-access").disabled = true;
    $("#network-save").disabled = true;
  }
  const list = $("#network-addresses");
  list.replaceChildren();
  const rows = [["This computer", `http://localhost:${network.port}`]];
  if (network.network_access) for (const a of network.addresses) rows.push(["Phones and other computers", `http://${a}:${network.port}`]);
  for (const [label, url] of rows) list.append(el("p", {}, `${label}: `, el("code", { text: url })));
}

async function saveNetwork(event) {
  event.preventDefault();
  const want = $("#network-access").checked;
  if (!want && network && !network.you_are_on_this_computer && !confirmLocalOnly) {
    confirmLocalOnly = true;
    $("#network-warning").hidden = false;
    return;
  }
  confirmLocalOnly = false;
  $("#network-warning").hidden = true;
  await saveGeneral({ network_access: want }, want ? "Other devices on your network can now open it" : "Only this computer can open it now");
  setTimeout(showNetwork, 1500);
}

async function showUpdates() {
  try {
    const v = await api("/api/version");
    const line = $("#version-line");
    line.replaceChildren(`You have version ${v.current}. `);
    if (v.latest && v.latest.replace(/^v/, "") !== v.current) line.append(chip(`Version ${v.latest.replace(/^v/, "")} is available`, "info"));
    else if (v.latest) line.append(chip("Up to date", "success"));
    else if (!v.repo) line.append("Set STARBOARD_REPO to check for new releases.");
  } catch { /* leave the placeholder */ }
}

// Old links to sections of the single Settings page go to their own pages now.
const MOVED = { "#general": "/settings-general.html", "#security": "/settings-security.html", "#updates": "/settings-updates.html" };
if (location.pathname.endsWith("/settings.html") && MOVED[location.hash]) location.replace(MOVED[location.hash]);

const on = (selector, event, handler) => { const node = $(selector); if (node) node.addEventListener(event, handler); };

startPage().then(async () => {
  config = await api("/api/config");
  renderGeneral();

  if ($("#service-list")) {  // Apps
    renderServices();
    wireDialog($("#service-dialog"));
    on("#add-service", "click", () => openService());
    on("#svc-type", "change", () => { updateTypeFields(); updateGroupGuess(); });
    on("#svc-name", "input", updateGroupGuess);
    on("#svc-background", "change", updateTypeFields);
    on("#svc-test", "click", testService);
    on("#svc-load-options", "click", loadServiceOptions);
    on("#service-form", "submit", saveService);
    if (!config.services.length) openService();
  }

  on("#general-form", "submit", (e) => {
    e.preventDefault();
    const f = e.target;
    saveGeneral({
      site_name: f.site_name.value, groups: f.groups.value.split(","), design: f.design.value,
      show_home_address: f.show_home_address.checked, show_outside_address: f.show_outside_address.checked,
    }, "General settings saved");
  });

  if ($("#network-form")) {  // Security
    showNetwork();
    on("#network-form", "submit", saveNetwork);
    on("#network-access", "change", () => { confirmLocalOnly = false; $("#network-warning").hidden = true; });
  }
  on("#session-form", "submit", (e) => {
    e.preventDefault();
    saveGeneral({ session_days: Number(e.target.session_days.value), secure_cookies: e.target.secure_cookies.checked }, "Session settings saved");
  });
  on("#password-form", "submit", async (e) => {
    e.preventDefault();
    const f = e.target;
    $("#password-error").textContent = "";
    try {
      await api("/api/password", { method: "POST", body: { current: f.current.value, new: f.new.value } });
      f.reset();
      toast("Password changed. Everyone else is signed out");
    } catch (err) {
      $("#password-error").textContent = err.message;
    }
  });
  on("#end-all", "click", async () => {
    await api("/api/sessions/end-all", { method: "POST" });
    location.href = "/login.html";
  });

  if ($("#version-line")) {  // Updates
    showUpdates();
    on("#update-check", "change", (e) => saveGeneral({ update_check: e.target.checked }, "Saved"));
  }
});
