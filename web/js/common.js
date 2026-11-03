// Shared by every page: display settings, the header, the API helper and small DOM helpers.
// Data from the server is always written with textContent, never as HTML.

const PREF_KEY = "starboard.display";
const DEFAULT_PREFS = { theme: "system", text: "100", contrast: false, motion: "device", underline: false, spacing: false, design: "" };
const DESIGNS = {
  health: ["Health first", "Apps that are not responding at the top, with a coloured edge for status."],
  tiles: ["Tiles", "A grid of cards with a description, like a launcher."],
  shelf: ["Shelf", "An icon rail on the left and one app per row."],
  command: ["Command", "Search first, with apps as a compact icon grid."],
  board: ["Status board", "A dense table for checking everything at a glance."],
};

function readPrefs() {
  try { return { ...DEFAULT_PREFS, ...JSON.parse(localStorage.getItem(PREF_KEY) || "{}") }; }
  catch { return { ...DEFAULT_PREFS }; }
}
function writePrefs(prefs) {
  try { localStorage.setItem(PREF_KEY, JSON.stringify(prefs)); } catch { /* private window: settings last until reload */ }
}

let serverDesign = "health";

function applyPrefs(prefs = readPrefs()) {
  const root = document.documentElement;
  if (prefs.theme === "system") root.removeAttribute("data-theme"); else root.setAttribute("data-theme", prefs.theme);
  const dark = prefs.theme === "dark" || (prefs.theme === "system" && matchMedia("(prefers-color-scheme: dark)").matches);
  root.classList.toggle("is-dark", dark);
  root.classList.remove("pref-text-125", "pref-text-150", "pref-text-175");
  if (prefs.text !== "100") root.classList.add(`pref-text-${prefs.text}`);
  root.classList.toggle("pref-contrast", !!prefs.contrast);
  root.classList.toggle("pref-motion", prefs.motion === "on");
  root.classList.toggle("pref-motion-off", prefs.motion === "off");
  root.classList.toggle("pref-underline", !!prefs.underline);
  root.classList.toggle("pref-spacing", !!prefs.spacing);
  const design = DESIGNS[prefs.design] ? prefs.design : serverDesign;
  if (root.dataset.design !== design) {
    root.dataset.design = design;
    document.dispatchEvent(new CustomEvent("designchange", { detail: design }));
  }
}
applyPrefs();
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => applyPrefs());

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) if (c !== null && c !== undefined && c !== false) node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  return node;
}

// Status chip (shared library, style B): the state's icon, then its words. Pass an icon for the state, or
// the tone's default is used.
const CHIP_ICONS = { success: "circle-check", info: "info", warning: "triangle-alert", danger: "circle-x", muted: "minus", neutral: "clock" };
function chip(text, tone, iconName) {
  const name = iconName || CHIP_ICONS[tone] || "circle";
  return el("span", { class: "chip", "data-tone": tone }, icon(name, 14), el("span", { text }));
}

async function api(path, { method = "GET", body } = {}) {
  const opts = { method, headers: { Accept: "application/json" }, credentials: "same-origin" };
  if (method !== "GET") {
    opts.headers["X-Starboard"] = "1";
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body || {});
  }
  const res = await fetch(path, opts);
  let data = {};
  try { data = await res.json(); } catch { /* empty */ }
  // 401 means signed out, except a password check that was wrong (reason "password"): that stays on the page.
  if (res.status === 401 && data.reason !== "password" && !location.pathname.startsWith("/login")) {
    location.href = "/login.html?next=" + encodeURIComponent(location.pathname + location.search);
    throw new Error("Sign in first");
  }
  if (!res.ok) {
    const error = new Error(data.error || `Something went wrong (error ${res.status})`);
    error.status = res.status;
    throw error;
  }
  return data;
}

// The shared toast (option C): a card in the corner, up to three stacked. Its icons come from Starboard's sprite
// file. A message of two sentences becomes a title and a line of detail, and the title loses its full stop
// (CONTENT-DESIGN.md: "Name saved", not "Name saved."). Problems use the info tone, never the success tick.
window.SharedComponentsSprite = "/icons/sprite.svg";
function toast(message, options = {}) {
  let title = String(message), detail = options.detail;
  const split = title.indexOf(". ");
  if (!detail && split > 0) { detail = title.slice(split + 2); title = title.slice(0, split); }
  title = title.replace(/\.$/, "");
  return window.SharedComponents.toast(title, { ...options, detail });
}
function problem(message) {
  return toast(message, { tone: "info" });
}

function announce(message) {
  const node = $("#announcer");
  if (node) { node.textContent = ""; setTimeout(() => { node.textContent = message; }, 50); }
}

function formatBytes(n) {
  if (!n) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB", "PB"];
  const i = Math.min(Math.floor(Math.log(n) / Math.log(1024)), units.length - 1);
  return `${(n / 1024 ** i).toFixed(i >= 3 ? 1 : 0)} ${units[i]}`;
}

function formatDate(iso, withTime = false) {
  const d = new Date(iso);
  const opts = { weekday: "short", day: "numeric", month: "long" };
  if (withTime) Object.assign(opts, { hour: "2-digit", minute: "2-digit" });
  return d.toLocaleString("en-GB", opts);
}

function monogram(name) {
  const words = String(name).replace(/[^\p{L}\p{N} ]/gu, "").split(/\s+/).filter(Boolean);
  return ((words[0] || "?")[0] + (words[1] ? words[1][0] : (words[0] || "")[1] || "")).toUpperCase();
}

// Addresses and copying ----------------------------------------------------

// An app saved as http://127.0.0.1:8989 is only reachable from the server itself. Swap in the name this browser
// used to reach Starboard, so links and copied addresses work from a phone too.
function reachableUrl(url) {
  try {
    const u = new URL(url);
    if (["127.0.0.1", "localhost", "[::1]", "0.0.0.0"].includes(u.hostname) && !["127.0.0.1", "localhost", "[::1]"].includes(location.hostname)) {
      u.hostname = location.hostname;
    }
    return u.href.replace(/\/$/, "");
  } catch { return url; }
}

function shortUrl(url) {
  return url.replace(/^https?:\/\//, "").replace(/\/$/, "");
}

// The clipboard API needs HTTPS or localhost; on a home network address the old copy command still works.
async function copyText(text) {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch { /* fall through */ }
  const area = el("textarea", { class: "visually-hidden", readonly: true, "aria-hidden": "true" });
  area.value = text;
  document.body.append(area);
  area.select();
  let ok = false;
  try { ok = document.execCommand("copy"); } catch { ok = false; }
  area.remove();
  return ok;
}

const COPY_ICON = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>'; // Lucide copy

function copyButton(text, label) {
  const button = el("button", { type: "button", class: "copy-btn", "aria-label": `Copy ${label}`, title: `Copy ${label}` });
  button.innerHTML = COPY_ICON; // a fixed icon from this file, never data
  button.addEventListener("click", async (e) => {
    e.preventDefault();
    e.stopPropagation();
    const ok = await copyText(text);
    (ok ? toast : problem)(ok ? `Copied ${label}` : `Could not copy. The address is ${text}`);
  });
  return button;
}

// The app's own icon, fetched and kept by the server; its initials when there is none.
function appIcon(s, className = "app-icon") {
  const box = el("span", { class: `${className} has-image`, "aria-hidden": "true" });
  const img = el("img", { src: `/api/icons/${encodeURIComponent(s.id)}?v=${encodeURIComponent(s.icon || "")}`, alt: "", loading: "lazy", decoding: "async" });
  img.addEventListener("error", () => { img.remove(); box.classList.remove("has-image"); box.textContent = monogram(s.name); });
  box.append(img);
  return box;
}

// Icons from the shared sprite (web/icons/sprite.svg). Decoration only: the words beside them carry the meaning.
function icon(name, size = 18) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("class", size >= 20 ? "i i-lg" : "i");
  svg.setAttribute("width", size); svg.setAttribute("height", size);
  svg.setAttribute("aria-hidden", "true"); svg.setAttribute("focusable", "false");
  const use = document.createElementNS(ns, "use");
  use.setAttribute("href", `/icons/sprite.svg#i-${name}`);
  svg.append(use);
  return svg;
}

// Slide-out: details of one thing, or editing it, without leaving the list (shared library: .side-panel).
// sidePanel({ title, body: [nodes], foot: [nodes], wide, opener, onClose }) -> { layer, body, foot, close, setTitle }
// It opens at once; focus moves to Close and goes back to the opener when it closes. Only one is open at a time.
function sidePanel({ title, body = [], foot = [], wide = false, opener = document.activeElement, onClose } = {}) {
  $("#side-panel")?.closeLayer?.(false);
  $("#side-panel")?.remove();
  const heading = el("h2", { class: "panel-header__title", id: "side-panel-title", text: title });
  const close = el("button", { type: "button", class: "icon-btn", "data-closes": true, "aria-label": `Close ${title}` }, icon("x", 20));
  const bodyNode = el("div", { class: "side-panel__body" }, body);
  const footNode = el("div", { class: "side-panel__foot" }, foot);
  footNode.hidden = !foot.length;
  const layer = el("div", { class: "side-panel-layer", id: "side-panel" },
    el("div", { class: "side-panel-backdrop" }),
    el("aside", { class: wide ? "side-panel side-panel--wide" : "side-panel", role: "dialog", "aria-modal": "true", "aria-labelledby": "side-panel-title" },
      el("div", { class: "panel-header" }, heading, close), bodyNode, footNode));
  document.body.append(layer);
  const shut = SharedComponents.openLayer(layer, opener instanceof HTMLElement ? opener : null, () => { layer.remove(); onClose?.(); });
  return {
    layer, body: bodyNode, foot: footNode, close: shut,
    setTitle(text) { heading.textContent = text; close.setAttribute("aria-label", `Close ${text}`); },
    setFoot(nodes) { footNode.replaceChildren(...nodes); footNode.hidden = !nodes.length; },
  };
}

// Confirm dialog: a decision that must be made before going on. Says what will happen; resolves true or false.
// confirmDialog({ title, message: string or [nodes], confirm: "Remove", danger: true, fields: [nodes] })
function confirmDialog({ title, message, confirm = "Continue", cancel = "Cancel", danger = false, fields = [] }) {
  return new Promise((resolve) => {
    const id = `confirm-${Date.now()}`;
    const form = el("form", { method: "dialog" },
      el("div", { class: "panel-header" },
        el("h2", { class: "panel-header__title", id, text: title }),
        el("button", { type: "button", class: "icon-btn", value: "cancel", "data-dialog-close": true, "aria-label": `Close ${title}` }, icon("x", 20))),
      el("div", { class: "dialog__body" }, typeof message === "string" ? el("p", { text: message }) : message, fields),
      el("div", { class: "dialog__foot" },
        el("button", { type: "submit", value: "ok", class: danger ? "btn btn--primary btn--danger" : "btn btn--primary", text: confirm }),
        el("button", { type: "submit", value: "cancel", formnovalidate: true, class: "btn", text: cancel })));
    const dialog = el("dialog", { class: "dialog", "aria-labelledby": id }, form);
    const opener = document.activeElement;
    let result = false;
    form.addEventListener("submit", (e) => { result = e.submitter?.value === "ok"; });
    $("[data-dialog-close]", form).addEventListener("click", () => dialog.close());
    dialog.addEventListener("close", () => { dialog.remove(); if (opener?.isConnected) opener.focus(); resolve(result); });
    document.body.append(dialog);
    dialog.showModal();
  });
}

// Menu button: a button that opens a short list of actions (More actions). items: [{ label, icon, onSelect, danger }]
let menuCount = 0;
function menuButton(label, items, { iconName = "ellipsis", text = "" } = {}) {
  const id = `menu-${++menuCount}`;
  const button = el("button", { type: "button", class: text ? "btn" : "icon-btn", "aria-haspopup": "menu", "aria-controls": id, "aria-label": text ? null : label },
    icon(iconName), text ? el("span", { text }) : null);
  const menu = el("div", { class: "menu", role: "menu", id, "aria-label": label },
    items.map((item) => el("button", { type: "button", role: "menuitem", class: item.danger ? "is-danger" : null, onclick: () => item.onSelect() },
      item.icon ? icon(item.icon) : null, el("span", { text: item.label }))));
  const wrap = el("div", { class: "menu-wrap" }, button, menu);
  queueMicrotask(() => SharedComponents.setup(wrap));
  return wrap;
}

// Lists that redraw (every 15 seconds on Downloads) keep focus: rows are matched by key, changed in place,
// added or removed, so the row or button you are on is still there afterwards.
// renderKeyed(list, items, key, render) where render(item, oldNode) returns the row node (reuse oldNode if you can).
function renderKeyed(list, items, key, render) {
  const old = new Map([...list.children].map((n) => [n.dataset.key, n]));
  const focused = document.activeElement;
  const focusedRow = list.contains(focused) ? focused.closest("[data-key]") : null;
  const focusPath = focusedRow ? [...focusedRow.querySelectorAll("button, a, input, select")].indexOf(focused) : -1;
  let before = list.firstElementChild;
  for (const item of items) {
    const k = String(key(item));
    const prev = old.get(k);
    const node = render(item, prev || null);
    node.dataset.key = k;
    old.delete(k);
    if (prev && prev !== node) {
      prev.replaceWith(node); // a fresh node takes the old one's place
      if (before === prev) before = node;
    }
    if (node !== before) list.insertBefore(node, before); else before = before.nextElementSibling;
  }
  old.forEach((n) => n.remove());
  if (focused?.isConnected && document.activeElement !== focused) focused.focus({ preventScroll: true });
  else if (focusedRow && !focusedRow.isConnected) {
    const again = list.querySelector(`[data-key="${CSS.escape(focusedRow.dataset.key)}"]`);
    const target = again && focusPath >= 0 ? again.querySelectorAll("button, a, input, select")[focusPath] : null;
    (target || again)?.focus();
  }
}

// Header ---------------------------------------------------------------

function setUpHeader() {
  // Phone menu: a drawer from the left (the shared slide-out layer: focus moves in, Tab stays inside,
  // Escape or a press outside closes it and focus returns to the menu button).
  const drawer = $("#phone-menu");
  const opener = $("[data-phone-menu-open]");
  if (drawer && opener) {
    opener.addEventListener("click", () => SharedComponents.openLayer(drawer, opener));
    $$(".phone-menu__section > button", drawer).forEach((button) => button.addEventListener("click", () => {
      const open = button.getAttribute("aria-expanded") !== "true";
      button.setAttribute("aria-expanded", String(open));
      $(`#${button.getAttribute("aria-controls")}`).hidden = !open;
    }));
    matchMedia("(min-width: 721px)").addEventListener("change", (e) => { if (e.matches) drawer.closeLayer?.(false); });
  }
  // Tabs that do not fit show icons only, as in Storyarr.
  const fit = () => $$(".site-header .menu-tabs").forEach((nav) => {
    nav.classList.remove("is-compact");
    if (nav.scrollWidth > nav.clientWidth + 1) nav.classList.add("is-compact");
  });
  fit();
  window.addEventListener("resize", fit);
  document.fonts?.ready.then(fit);
  $$("[data-sign-out]").forEach((b) => b.addEventListener("click", async () => {
    await api("/api/logout", { method: "POST" }).catch(() => {});
    location.href = "/login.html";
  }));
}

// True when version a is newer than b ("v0.5.1" > "0.5.0"); an older or equal release is never an upgrade.
function isNewer(a, b) {
  const parts = (v) => String(v || "").replace(/^v/, "").split(/[.-]/).slice(0, 3).map((n) => parseInt(n, 10) || 0);
  const [x, y] = [parts(a), parts(b)];
  for (let i = 0; i < 3; i++) if (x[i] !== y[i]) return x[i] > y[i];
  return false;
}

function showVersion(version, repo, latest) {
  if (!version) return;
  const label = `Starboard: v${version}`;
  $$("[data-version]").forEach((n) => { n.textContent = label; });
  if ($(".site-header") && !$(".site-footer")) {
    // The version opens the release notes; a newer release on GitHub shows "Upgrade available" beside it.
    const newer = isNewer(latest, version);
    const button = el("button", { type: "button", class: "btn btn--quiet version-label", onclick: (e) => openReleaseNotes(e.currentTarget) },
      label, el("span", { class: "visually-hidden", text: ", release notes" }));
    document.body.append(el("footer", { class: "site-footer" }, button,
      newer ? el("a", { class: "upgrade-available", href: "/settings-updates.html" }, el("span", { class: "update-dot", "aria-hidden": "true" }), `Upgrade available: ${latest}`) : null,
      // The help centre is plain pages in the repository (docs/help), so it opens on GitHub.
      el("a", { href: `https://github.com/${repo || "TheMightyTRex/starboard"}/blob/main/docs/help/README.md`, target: "_blank", rel: "noopener noreferrer" },
        "Help", el("span", { class: "visually-hidden", text: " centre (opens in a new tab)" })),
      repo ? el("a", { href: `https://github.com/${repo}`, target: "_blank", rel: "noopener noreferrer" }, "GitHub repository", el("span", { class: "visually-hidden", text: " (opens in a new tab)" })) : null,
      el("a", { href: "/settings-updates.html", text: "About and updates" })));
  }
}

// Release notes: one look for every release (Added, Changed, Fixed, Your settings and the way back), in the
// slide-out from the footer and on the upgrade guide's first step.
function releaseNotes(rel, level = 3) {
  const group = (title, items) => items.length ? [el(`h${level + 1}`, { text: title }),
    el("ul", {}, items.map(([t, sentence]) => el("li", {}, el("strong", { text: `${t}. ` }), sentence)))] : [];
  return el("section", { class: "release-notes", "aria-label": `Version ${rel.version}` },
    el(`h${level}`, { text: `Version ${rel.version}` }), el("p", { class: "small muted", text: `Released ${rel.date}` }),
    ...group("Added", rel.added), ...group("Changed", rel.changed), ...group("Fixed", rel.fixed),
    el(`h${level + 1}`, { text: "Your settings and the way back" }), el("p", { text: rel.settings }));
}

async function openReleaseNotes(opener) {
  const panel = sidePanel({ title: "Release notes", opener, wide: true, body: [el("p", { class: "muted", text: "Loading…" })] });
  try {
    const r = await api("/api/releases");
    const newer = isNewer(r.latest, r.current);
    panel.body.replaceChildren(...[
      newer ? el("div", { class: "notice", role: "status" }, icon("circle-arrow-up"), el("div", { class: "notice__body" },
        el("span", { class: "notice__title", text: `Version ${r.latest} is out` }),
        el("p", {}, `You have ${r.current}. `, el("a", { href: "/settings-updates.html", text: "How to update" }), "."))) : null,
      ...r.all.map((rel) => releaseNotes(rel, 3)),
    ].filter(Boolean));
  } catch (e) { panel.body.replaceChildren(el("p", { text: e.message })); }
}

// After an upgrade: with something to choose, a notice opens the upgrade guide (or waits, with Remind me later);
// with nothing to choose, the upgrade is marked as seen and the notes stay under the version.
function upgradeNotice(upgrade) {
  if (!upgrade || upgrade.from === upgrade.to || /\/(upgrade|setup-guide)\.html$/.test(location.pathname)) return;
  if (!upgrade.wizard) { api("/api/releases/seen", { method: "POST" }).catch(() => {}); return; }
  try { if (sessionStorage.getItem(`upgrade-later-${upgrade.to}`)) return; } catch { /* show it */ }
  const main = $("#main .page");
  if (!main || $("#upgrade-notice")) return;
  main.prepend(el("div", { class: "notice", id: "upgrade-notice", role: "status" }, icon("circle-arrow-up"),
    el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: `Starboard ${upgrade.to} is installed` }),
      el("p", { text: `${upgrade.count} ${upgrade.count === 1 ? "thing" : "things"} to choose. The rest carries on as before.` })),
    el("a", { class: "btn btn--primary", href: "/upgrade.html" }, "Open the upgrade guide")));
}

// Display and accessibility panel --------------------------------------

// A slide-out, like every other panel that opens over a page (DESIGN-SYSTEM.md, Consistency rules). Choices apply
// at once and are kept in this browser; Done closes it, Reset goes back to the defaults.
function setUpDisplayPanel() {
  const template = $("#display-panel");
  const opener = $("[data-display-toggle]");
  if (!template || !opener) return;
  opener.addEventListener("click", () => openDisplayPanel(template, opener));
}

function openDisplayPanel(template, opener) {
  const form = template.content.querySelector("[data-display-form]").cloneNode(true);
  const designList = $("[data-design-options]", form);
  const choices = [["", "Use the dashboard's default"], ...Object.entries(DESIGNS).map(([k, v]) => [k, v[0], v[1]])];
  for (const [value, label, help] of choices) {
    designList.append(el("label", { class: "option-card" },
      el("input", { type: "radio", name: "design", value }),
      el("strong", { text: label }),
      help ? el("small", { text: help }) : null));
  }
  const fill = () => {
    const p = readPrefs();
    form.theme.value = p.theme; form.text.value = p.text; form.motion.value = p.motion;
    $$("input[name=design]", form).forEach((r) => { r.checked = r.value === p.design; }); // "" is the dashboard's default
    form.contrast.checked = p.contrast; form.underline.checked = p.underline; form.spacing.checked = p.spacing;
  };
  const save = () => {
    const prefs = {
      theme: form.theme.value, text: form.text.value, motion: form.motion.value, design: form.design.value,
      contrast: form.contrast.checked, underline: form.underline.checked, spacing: form.spacing.checked,
    };
    writePrefs(prefs);
    applyPrefs(prefs);
  };
  form.addEventListener("change", save);
  const done = el("button", { type: "button", class: "btn btn--primary", text: "Done" });
  const reset = el("button", { type: "button", class: "btn", text: "Reset" });
  fill();
  opener.setAttribute("aria-expanded", "true");
  const panel = sidePanel({ title: "Display and accessibility", opener, body: [form], foot: [done, reset],
    onClose: () => opener.setAttribute("aria-expanded", "false") });
  form.addEventListener("submit", (e) => { e.preventDefault(); panel.close(); });
  done.addEventListener("click", () => panel.close());
  reset.addEventListener("click", () => { writePrefs(DEFAULT_PREFS); applyPrefs(DEFAULT_PREFS); fill(); announce("Display settings reset"); });
}

// Every dialog closes with its X button and returns focus (the browser handles Escape and focus trapping).
function wireDialog(dialog) {
  $$("[data-dialog-close]", dialog).forEach((b) => b.addEventListener("click", () => dialog.close()));
}

// Testing (Settings, General): the shared library's Note an issue button, with the notes kept on the server in
// data/ux-notes.json. The script loads only while it is on.
async function startUxNotes(version) {
  if (!version) version = (await api("/api/session").catch(() => ({}))).version;
  const store = {
    list: async () => (await api("/api/ux-notes")).notes,
    add: (note) => api("/api/ux-notes", { method: "POST", body: note }),
    update: (id, changes) => api("/api/ux-notes/update", { method: "POST", body: { id, ...changes } }),
    remove: (id) => api("/api/ux-notes/remove", { method: "POST", body: { id } }),
  };
  const start = () => window.UxNotes?.start({ app: "Starboard", version, store });
  if (window.UxNotes) return start();
  document.head.append(el("script", { src: "/js/ux-notes.js", onload: start }));
}

async function startPage() {
  setUpHeader();
  setUpDisplayPanel();
  try {
    const session = await api("/api/session");
    serverDesign = session.design || "health";
    applyPrefs();
    $$("[data-site-name]").forEach((n) => { n.textContent = session.site_name; });
    document.title = document.title.replace(/ · [^·]*$/, ` · ${session.site_name}`);
    showVersion(session.version, session.repo, session.latest);
    upgradeNotice(session.upgrade);
    if (session.ux_notes) startUxNotes(session.version);
    return session;
  } catch { return null; }
}
