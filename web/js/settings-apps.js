// Settings, Apps, Manage apps: the list of apps, adding, editing, testing, ordering, hiding and removing them.

const SEARCHABLE = ["sonarr", "radarr", "lidarr", "readarr"];

const NO_KEY = ["link"];
// Plex and Emby (DASH-566): the address each one usually has, which also names the new app after its kind until it is typed over.
const MEDIA_ADDRESS = { plex: "http://127.0.0.1:32400", emby: "http://127.0.0.1:8096" };

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
// words in hidden text and in the design system's tooltip on hover (no Tab stop of its own: it sits inside the name's button, which reads the words).
function statusIcon(s) {
  const st = statusById[s.id];
  const [words, tone, name] = !s.enabled ? ["Hidden from the dashboard", "muted", "eye-off"]
    : !st ? ["Checking", "muted", "circle"]
    : st.state === "up" ? [s.background ? "Running" : "Connected", "success", "circle-check"]
    : st.state === "down" ? [s.background ? "Not running" : "Cannot connect", "danger", "circle-x"]
    : ["Not checked", "muted", "circle-help"];
  return el("span", { class: "status-icon", "data-tone": tone, "data-tooltip": words }, icon(name), el("span", { class: "visually-hidden", text: `, ${words}` }));
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
  menuItems.push({ label: "Restart", icon: "rotate-ccw", onSelect: () => later(() => restartService(s)) });
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

// Restart (owner, 12 November 2026): stops the app's container and starts it again. For Gluetun, the apps that use
// its network restart after it. Focus goes back to the app's name, and the result is said.
async function restartService(s) {
  const ok = await confirmDialog({
    title: `Restart ${s.name}?`,
    message: `${s.name} stops and starts again, which takes a few seconds. Its settings and files stay as they are, and anything it was doing carries on once it is back.${s.type === "gluetun" ? " The apps that use its VPN connection restart after it." : ""}`,
    confirm: `Restart ${s.name}`,
  });
  if (!ok) return;
  const focusRow = () => $(`#app-sections [data-key="${CSS.escape(s.id)}"] .row__title button`)?.focus();
  announce(`Restarting ${s.name}`);
  try {
    const r = await api(`/api/services/${s.id}/restart`, { method: "POST" });
    toast(r.said);
    announce(r.said);
    await loadStatus();
  } catch (e) { problem(e.message); }
  focusRow();
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

// Sign in with Plex's own link code (DASH-595). Returns { node, pin(), stop() }. The page asks the server for the answer every
// two seconds only while it is open and visible; Cancel, a closed panel, a page that is left or the code running out all stop it.
function plexLinkBox({ onApproved, onReset, focusSave }) {
  const POLL = 2000;
  let pin = null, timer = null, until = 0, running = false;
  const start = el("button", { type: "button", class: "btn" }, icon("link"), "Sign in with Plex");
  const out = el("div", { "aria-live": "polite" });
  const cancel = el("button", { type: "button", class: "btn btn--quiet" }, "Cancel");
  const node = el("div", { class: "plex-link", "data-span": "all", hidden: true },
    el("p", { class: "small muted", text: "Sign in with Plex's own link code, or paste the token in the Plex token field. The token stays on this server and is never shown again." }),
    el("div", { class: "actions" }, start), out);

  const stop = (said = null) => {
    clearTimeout(timer);
    removeEventListener("pagehide", stop);
    if (running && pin) api(`/api/plex/link/${pin}/cancel`, { method: "POST" }).catch(() => {});
    running = false;
    if (said !== null) out.replaceChildren(said);
    start.hidden = false;
  };
  const again = (words) => { stop(notice("warning", words, "Select Sign in with Plex to get a new code, or paste the token.")); onReset(); start.focus(); };

  const poll = async () => {
    if (!running) return;
    if (Date.now() >= until) { again("The code ran out"); return; }
    if (!document.hidden) {
      try {
        const r = await api(`/api/plex/link/${pin}`);
        if (!running) return;
        if (r.state === "approved") {
          running = false;
          stop(notice("success", "Signed in with Plex", "Press Save to keep it. Starboard never shows the token."));
          onApproved();
          focusSave();
          return;
        }
        if (r.state !== "waiting") { again(r.state === "cancelled" ? "Sign-in cancelled" : "The code ran out"); return; }
      } catch (e) { /* a missed answer: ask again at the next turn, until the time is up */ }
    }
    timer = setTimeout(poll, POLL);
  };

  start.addEventListener("click", async () => {
    start.disabled = true;
    try {
      const r = await api("/api/plex/link", { method: "POST" });
      pin = r.id; running = true; until = Date.now() + r.expires_in * 1000;
      start.hidden = true;
      out.replaceChildren(el("div", { class: "notice", role: "status" }, icon("info"), el("div", { class: "notice__body" },
        el("span", { class: "notice__title", text: "Approve this code in Plex" }),
        el("p", {}, "Go to ", el("a", { href: r.link, target: "_blank", rel: "noopener noreferrer", text: "plex.tv/link" }), " and enter the code ",
          el("strong", { class: "plex-code", text: r.code.split("").join(" ") }), `. It works for ${Math.round(r.expires_in / 60)} minutes. Starboard waits here.`), cancel)));
      addEventListener("pagehide", stop);
      cancel.onclick = () => { stop(notice("info", "Sign-in cancelled", "Select Sign in with Plex to start again, or paste the token.")); start.focus(); };
      cancel.focus();
      timer = setTimeout(poll, POLL);
    } catch (e) {
      out.replaceChildren(notice("danger", "No code from Plex", e.message));
    } finally { start.disabled = false; }
  });
  return { node, pin: () => pin, stop: () => { if (running) stop(); } };
}

function openService(s = null, opener = null, { background = false, preset = null } = {}) {
  const isNew = !s;
  let current = s ? { ...s } : null;

  // Step 1: Connection, and how it shows on the dashboard.
  const type = el("select", { class: "select", name: "type" }, Object.entries(config.types).map(([k, v]) => el("option", { value: k, text: v.label })));
  const name = el("input", { class: "input", name: "name", maxlength: "60", required: true, autocomplete: "off" });
  const url = el("input", { class: "input", name: "url", inputmode: "url", placeholder: "http://127.0.0.1:8096", autocomplete: "off" });
  const key = el("input", { class: "input", name: "api_key", type: "password", autocomplete: "off" });
  const keyHint = el("span", {});
  const keyField = field("API key", key, { hint: keyHint, span: true });
  const keyLabel = keyField.querySelector("label");
  const testButton = el("button", { type: "button", class: "btn" }, icon("zap"), "Test connection");
  const testResult = el("div", { "aria-live": "polite" });
  // Plex's own link code (DASH-595): an owner's choice beside pasting the token. Starboard asks plex.tv for a code, shows it with
  // plex.tv/link and asks for the answer every two seconds while this panel is open. The token never reaches this page.
  const plexLink = plexLinkBox({ onApproved: () => { linked = true; key.value = ""; key.disabled = true; key.placeholder = "Signed in with Plex"; testButton.disabled = false; },
    onReset: () => { linked = false; key.disabled = false; key.placeholder = ""; }, focusSave: () => saveButton.focus() });
  let linked = false;

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
        field("Address Starboard uses", url, { required: true, hint: "For an app on this computer, 127.0.0.1 and the app's port, such as http://127.0.0.1:8096 for Jellyfin. For another computer, its address. Optional for a background service.", span: true }),
        plexLink.node,
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
    s && /calibre/i.test(`${s.name} ${s.icon || ""}`) && typeof phoneApps === "function"
      ? el("section", { class: "step-section", "aria-labelledby": "svc-phone-h" }, el("h3", { id: "svc-phone-h", text: "Read on your phone" }), phoneApps("h4")) : null,
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
    plexLink.node.hidden = t !== "plex";
    if (t !== "plex") plexLink.stop();
    const where = { qbittorrent: "Options, Web UI, API key (version 5.2 or later)", sabnzbd: "Config, General, API Key",
      jellyfin: "Dashboard, API keys. Optional: it adds Jellyfin's state, what is playing and recently added to System",
      audiobookshelf: "Settings, API Keys, for an admin user. Optional: it is needed only to copy listening progress (Settings, Apps, Audiobookshelf)",
      gluetun: "its control server settings. Optional: only if you gave its control server an API key",
      nzbget: "Settings, Security: enter its control user name and password as user:password",
      slskd: "Options, web, authentication, API keys (in its slskd.yml)",
      emby: "Dashboard, Advanced, API Keys, then New API Key. It adds Emby's state, what is playing and recently added to the dashboard, Library and Activity",
      plex: "paste it here, or use Sign in with Plex and leave this blank. To find it, open any item in the Plex web app, then Get Info, then View XML, and copy what follows X-Plex-Token= in the address. It adds Plex's state, what is playing and recently added to the dashboard, Library and Activity" }[t] || "Settings, General";
    keyLabel.firstChild.textContent = t === "plex" ? "Plex token" : "API key";
    url.placeholder = MEDIA_ADDRESS[t] || "http://127.0.0.1:8096";
    if (isNew && (!name.value || name.dataset.auto)) {
      if (MEDIA_ADDRESS[t]) { name.value = config.types[t].label; name.dataset.auto = "1"; } else if (name.dataset.auto) { name.value = ""; delete name.dataset.auto; }
    }
    keyHint.textContent = `In ${config.types[t]?.label || "the app"}: ${where}.${current?.has_api_key ? " Leave blank to keep the saved key; it is never shown again." : ""}`;
    followsField.hidden = !bg.checked;
    group.options[0].textContent = `Choose for me (${guessGroup(name.value, t) || "the last category"})`;
    steps.hidden = !SEARCHABLE.includes(t);
    saveButton.textContent = SEARCHABLE.includes(t) ? "Save and continue" : (isNew ? "Add app" : "Save app");
  };

  const values = () => ({
    id: current?.id, type: type.value, name: name.value, url: url.value, link: link.value, outside_link: outside.value,
    icon: iconInput.value, api_key: key.value, plex_pin: linked && !key.value ? plexLink.pin() : undefined, group: group.value, background: bg.checked, follows: bg.checked ? follows.value : "",
    description: desc.value, enabled: enabled.checked, container: container.value,
    quality_profile_id: current?.quality_profile_id ?? null, root_folder: current?.root_folder || "",
    metadata_profile_id: current?.metadata_profile_id ?? null, search_on_add: current ? current.search_on_add !== false : true,
  });

  const panel = sidePanel({
    title: s ? `Edit ${s.name}` : (background ? "Add a background service" : "Add an app"), wide: true, opener,
    body: [steps, form],
    foot: [saveButton, cancel, remove].filter(Boolean),
    onClose: () => {
      plexLink.stop();  // nothing is asked of plex.tv once the panel is closed
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
  name.addEventListener("input", () => { delete name.dataset.auto; updateFields(); });
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
    const wrong = [];
    if (!name.value.trim()) wrong.push([name, "Enter a name for the app"]);
    if (!url.value.trim() && !bg.checked) wrong.push([url, "Enter the address Starboard uses to reach the app, such as http://127.0.0.1:8096"]);
    formErrors(form, wrong);
    [link, outside, iconInput].forEach((c) => setError(c, ""));
    if (wrong.length) return;
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
        el("div", { class: "switch-list" }, switchRow("Search as soon as something is added", `Active: ${current.name} searches for ${kind} straight away.`, searchOnAdd))));
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
  else if (["plex", "emby"].includes(params.get("add"))) openService(null, $("#add-service"), { preset: { type: params.get("add"), name: config.types[params.get("add")].label, url: params.get("url") || "" } });
  else if (params.has("add") || !config.services.length) openService(null, $("#add-service"));
  loadStatus();
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
