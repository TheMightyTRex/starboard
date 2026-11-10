// Shared by every page: display settings, the header, the API helper and small DOM helpers.
// The help centre: one page for each article in docs/help, with search (the design system's help centre builder (tools/help_centre), .github/workflows/help.yml).
const HELP_CENTRE = "https://themightytrex.github.io/starboard/help/";
/** docs/help path ("topics/x.md#part") -> its help centre page. */
function helpPage(path) {
  const [file, anchor] = path.split("#");
  const page = file.endsWith("README.md") ? file.replace(/README\.md$/, "index.html") : file.replace(/\.md$/, ".html");
  return HELP_CENTRE + page + (anchor ? `#${anchor}` : "");
}
// Data from the server is always written with textContent, never as HTML.

// A link that opens a new tab: its words, then the new-tab icon, and "(opens in a new tab)" for screen readers
// (LIBRARY.md, Links). `about` adds words for screen readers only, such as whose site it is.
function newTabLink(href, text, { about = "", className = "" } = {}) {
  return el("a", { href, target: "_blank", rel: "noopener noreferrer", class: className || null }, text,
    el("span", { class: "visually-hidden", text: ` (${about ? `${about}, ` : ""}opens in a new tab)` }), icon("external-link", 16));
}

// Required fields (LIBRARY.md, Fields): a * after the label. The key, "* = Required", is in the help slide-out, not
// in the form: most people know the star, and the help is where it is explained.
function requiredMark() {
  return el("span", { class: "field__required", "aria-hidden": "true", text: "*" });
}
// The key for the stars, at the bottom of a help slide-out opened from a form or step that has a required field.
function requiredKey() {
  return el("p", { class: "required-key" }, el("span", { class: "field__required", text: "*" }), "= Required");
}

// In-page help (LIBRARY.md, Help links): a link-styled button with the square help icon that opens a slide-out
// titled with its question. `body` is help written in the page; `page` is a help centre article
// ("topics/x.md#part"), fetched by Starboard (/api/help) and drawn here from data. With an article, the foot has
// "Read it in the help centre", with the new-tab help icon. `back` names a button that closes it ("Back to set-up").
function helpButton(question, { body = null, page = "", title = "", back = "" } = {}) {
  const button = el("button", { type: "button", class: "help-link", "aria-haspopup": "dialog" }, icon("help"), el("span", { text: question }));
  button.addEventListener("click", () => openHelp(title || question, { body, page, back, opener: button }));
  return button;
}

function helpCentreLink(page, text = "Read it in the help centre") {
  return el("a", { class: "help-link", href: helpPage(page), target: "_blank", rel: "noopener noreferrer" },
    icon("help-new-tab"), el("span", { text }), el("span", { class: "visually-hidden", text: " (opens in a new tab)" }));
}

async function openHelp(title, { body = null, page = "", back = "", opener } = {}) {
  const close = back ? el("button", { type: "button", class: "btn", text: back }) : null;
  const panel = sidePanel({ title, opener, wide: true, body: body ? [].concat(body) : [el("p", { class: "muted", text: "Loading…" })],
    foot: [close, page ? helpCentreLink(page) : null].filter(Boolean) });
  close?.addEventListener("click", () => panel.close());
  // The star's key when the form or step this help belongs to has a required field.
  const keyed = !!opener?.closest?.("form, .panel, .side-panel__body, main")?.querySelector(".field__required");
  if (keyed) panel.body.append(requiredKey());
  if (body || !page) return panel;
  const [file, anchor] = page.split("#");
  try {
    const found = await api(`/api/help?page=${encodeURIComponent(file)}`);
    panel.body.replaceChildren(el("div", { class: "prose" }, helpNodes(found.body, panel)), keyed ? requiredKey() : "");
    if (anchor) panel.body.querySelector(`[id="help-${CSS.escape(anchor)}"]`)?.scrollIntoView({ block: "start" });
  } catch (e) {
    panel.body.replaceChildren(el("p", { text: e.message }), keyed ? requiredKey() : "");
  }
  return panel;
}

// An article from /api/help as nodes: only these tags, text always as text, headings one level down (the
// slide-out's title is the h2), ids kept apart from the page's with "help-", links to the help centre in a new tab.
const HELP_TAGS = new Set(["h2", "h3", "h4", "p", "ul", "ol", "li", "strong", "em", "code", "pre", "kbd", "br", "blockquote",
  "a", "img", "figure", "figcaption", "table", "thead", "tbody", "tr", "th", "td"]);
const HELP_LEVEL = { h2: "h3", h3: "h4", h4: "h5" };
function helpNodes(list, panel) {
  return (list || []).map((n) => {
    if (typeof n === "string") return document.createTextNode(n);
    const [tag, attrs = {}, kids = []] = n;
    if (!HELP_TAGS.has(tag)) return el("span", {}, helpNodes(kids, panel));
    const node = document.createElement(HELP_LEVEL[tag] || tag);
    if (attrs.id) node.id = `help-${attrs.id}`;
    if (tag === "a") {
      const href = attrs.href || "";
      if (href.startsWith("#")) {
        node.href = href;
        node.addEventListener("click", (e) => {
          e.preventDefault();
          panel.body.querySelector(`[id="help-${CSS.escape(href.slice(1))}"]`)?.scrollIntoView({ block: "start" });
        });
      } else if (href.startsWith("https://")) {
        node.href = href; node.target = "_blank"; node.rel = "noopener noreferrer";
      }
    }
    if (tag === "img") {
      if (!(attrs.src || "").startsWith("https://")) return document.createTextNode("");
      node.src = attrs.src; node.alt = attrs.alt || ""; node.loading = "lazy";
    }
    node.append(...helpNodes(kids, panel));
    if (tag === "a" && node.target) node.append(el("span", { class: "visually-hidden", text: " (opens in a new tab)" }));
    return node;
  });
}

const PREF_KEY = "starboard.display";
const DEFAULT_PREFS = { theme: "system", text: "100", contrast: false, motion: "device", underline: false, spacing: false, design: "", style: "" };
const DESIGNS = {
  health: ["Health first", "Apps that are not responding at the top, with a coloured edge for status."],
  tiles: ["Tiles", "A grid of cards with a description, like a launcher."],
  shelf: ["Shelf", "One app per row, with room for its details."],
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
  // A style from a plug-in (DASH-284): colours and shape Starboard checked and wrote itself. High contrast wins.
  if (prefs.style && /^[a-z0-9-]+\.[a-z0-9-]+$/.test(prefs.style)) {
    root.dataset.style = prefs.style;
    if (!document.getElementById("plugin-styles")) {
      document.head.append(Object.assign(document.createElement("link"), { id: "plugin-styles", rel: "stylesheet", href: "/api/styles.css" }));
    }
  } else {
    delete root.dataset.style;
  }
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
// An error shows beside what it belongs to (content rule): the control named, or the one just used. With
// neither (an error while a page loads), it is an error toast, which stays until it is closed.
const CONTROLS = "button, input, select, textarea";
let lastUsed = null;
for (const type of ["click", "change"]) {
  document.addEventListener(type, (e) => {
    const control = e.target.closest?.(CONTROLS);
    // A confirm dialog closes before its answer comes, so the button that opened it stays the one in use.
    if (control && !control.closest(".toasts, dialog.dialog")) lastUsed = { control, at: Date.now() };
  }, true);
}
function problem(message, near) {
  let control = near instanceof Element ? near
    : lastUsed?.control.isConnected && Date.now() - lastUsed.at < 30000 ? lastUsed.control : null;
  if (control?.closest(".menu")) control = $(":scope > button", control.closest(".menu-wrap")); // a menu closes: its button stays
  if (!control || !control.getClientRects().length) return window.SharedComponents.toast.error(String(message).replace(/\.$/, ""));
  return inlineError(control, message);
}
function inlineError(control, message) {
  const row = control.closest(".row");
  const box = (row && $(".row__text", row)) || control.closest(".field, td, li");
  const after = box ? null : control.closest(".actions, label") || control;
  const holder = box || after.parentElement;
  $(":scope > .field-error[data-problem]", holder)?.remove();
  const text = String(message).replace(/\.?$/, ".");
  const error = el("p", { class: "field-error", role: "alert", "data-problem": "", id: `problem-${Date.now()}` }, icon("circle-alert"), el("span", { text }));
  if (box) box.append(error); else after.after(error);
  control.setAttribute("aria-describedby", [control.getAttribute("aria-describedby"), error.id].filter(Boolean).join(" "));
  // The next go clears it: a new answer replaces it, a success leaves nothing to explain.
  const clear = () => {
    error.remove();
    const ids = (control.getAttribute("aria-describedby") || "").split(" ").filter((id) => id && id !== error.id);
    if (ids.length) control.setAttribute("aria-describedby", ids.join(" ")); else control.removeAttribute("aria-describedby");
  };
  for (const type of ["click", "input", "change"]) control.addEventListener(type, clear, { once: true });
  return clear;
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
  SharedComponents.setupSearch();
  document.fonts?.ready.then(fit);
  // Sign out beside the title on every Settings page (design system, Sign out); the phone menu has it too. Not on the
  // set-up and upgrade guides, which are wizards.
  const head = $("#main-nav")?.getAttribute("aria-label") === "Settings" && !$("#guide, #upgrade") ? $(".page-head") : null;
  if (head && !head.querySelector("[data-sign-out]")) {
    let actions = head.querySelector(".actions");
    if (!actions) { actions = el("div", { class: "actions" }); head.append(actions); }
    actions.append(el("button", { type: "button", class: "btn", "data-sign-out": "" }, icon("log-out"), "Sign out"));
  }
  $$("[data-sign-out]").forEach((b) => b.addEventListener("click", async () => {
    await api("/api/logout", { method: "POST" }).catch(() => {});
    location.href = "/login.html";
  }));
}

// True when version a is newer than b ("v0.5.1" > "0.5.0"); an older or equal release is never an upgrade.
// Usenet providers for SABnzbd, with affiliate links: the same list and words as USENET in
// starboard/terminal_setup.py. The affiliate note comes before the links, and what Usenet may be used for after
// them; Usenet is never shown as a way to get copyrighted films, series, music or books.
const USENET = [
  ["Newshosting", "https://www.newshosting.com/?a_aid=6aec3d712dec1"],
  ["Easynews", "https://easynews.com/?a_aid=6aec3d712dec1"],
  ["UsenetServer", "https://www.usenetserver.com/?a_aid=6aec3d712dec1&a_bid=ef245116"],
  ["Pure Usenet", "https://www.pureusenet.nl/?a_aid=6aec3d712dec1&a_bid=9fa99e6a"],
  ["XLned", "https://www.xlned.com/?a_aid=6aec3d712dec1&a_bid=dbc287fb"],
];
const USENET_ABOUT = "SABnzbd needs an account with a Usenet provider. Usenet is a worldwide network of discussion groups, running since 1980, that also carries files. Any provider works with SABnzbd.";
const USENET_AD = "these are affiliate links. If you sign up through one, the provider pays a small commission towards Starboard's development. You pay the same price.";
const USENET_RIGHTS_TITLE = "Download only what you have the right to";
const USENET_RIGHTS = "Use Usenet only for files you have the right to download, such as open-source software, works in the public domain and your own backups. Downloading films, series, music or books without the copyright holder's permission is against the law in the UK and most other countries. Starboard does not host or provide any files, and you are responsible for what you download.";

// What Usenet may be used for, as a notice: in the wizard, on Manage apps and on About.
function usenetRights() {
  return el("div", { class: "notice" }, icon("info"), el("div", { class: "notice__body" },
    el("span", { class: "notice__title", text: USENET_RIGHTS_TITLE }), el("p", { text: USENET_RIGHTS })));
}

// The providers: each name is the affiliate link, opening in a new tab, after the Ad note.
function usenetProviders() {
  return el("div", { class: "stack-2" },
    el("p", { text: USENET_ABOUT }),
    el("p", { class: "small" }, el("strong", { text: "Ad: " }), USENET_AD),
    el("ul", { "aria-label": "Usenet providers (affiliate links)" }, USENET.map(([name, url]) => el("li", {},
      el("a", { href: url, target: "_blank", rel: "noopener noreferrer sponsored" }, name,
        el("span", { class: "visually-hidden", text: " (affiliate link, opens in a new tab)" }))))),
    usenetRights());
}

function isNewer(a, b) {
  const parts = (v) => String(v || "").replace(/^v/, "").split(/[.-]/).slice(0, 3).map((n) => parseInt(n, 10) || 0);
  const [x, y] = [parts(a), parts(b)];
  for (let i = 0; i < 3; i++) if (x[i] !== y[i]) return x[i] > y[i];
  return false;
}

// The design system's maker mark: the T-rex, linked to TheMightyTRexUK's GitHub profile (the same in every app).
const MAKER_MARK = '<svg class="maker-mark" viewBox="0 0 32 32" aria-hidden="true" focusable="false"><rect x="1" y="1" width="30" height="30" fill="var(--color-logo-tile)"/><path fill="var(--color-bg)" d="M17 6.5h7.5q2.5 0 2.5 2.2V11h-4v.8h2.6v1.6H21v2.2l2.6 1.5-.6 1-2-1.1V20q0 2.2-2.4 2.9l.9 3.8h1.6V28h-4.3l-.9-4.4h-1.6l-.8 3.1h1.4V28h-4.1l1-4.9q-3.6-1-8.7.3 3.4-3.6 8.2-5.2 3.3-1.3 3.9-4.6V8.4q0-1.9 1.4-1.9Z"/><circle cx="20" cy="8.6" r="1" fill="var(--color-logo-star)"/></svg>';

// The version sits at the bottom of the side menu and in the phone menu; a newer release shows "Update" above it
// (DASH-104, DASH-105). The footer is the design system's: Starboard's links on the left, the maker on the right.
function showVersion(version, repo, latest) {
  if (!version) return;
  const newer = isNewer(latest, version);
  $$("[data-version]").forEach((n) => { n.textContent = `Starboard: v${version}`; });
  $$("[data-version-short]").forEach((n) => {
    n.replaceChildren(el("span", { class: "visually-hidden", text: "Starboard version " }), `v${version}`);
  });
  $$("[data-update-available]").forEach((n) => {
    n.hidden = !newer;
    if (newer) n.setAttribute("aria-label", `Update available: version ${String(latest).replace(/^v/, "")}. About and updates`);
  });
  if ($(".site-header") && !$(".site-footer")) {
    const brand = $(".site-header__brand svg")?.cloneNode(true);
    const link = (href, text, outside) => el("li", {}, outside
      ? el("a", { href, target: "_blank", rel: "noopener noreferrer" }, text, el("span", { class: "visually-hidden", text: " (opens in a new tab)" }))
      : el("a", { href, text }));
    const notes = el("li", {}, el("a", { href: "#release-notes", onclick: (e) => { e.preventDefault(); openReleaseNotes(e.currentTarget); } }, "Release notes"));
    const maker = el("a", { class: "site-footer__maker", href: "https://github.com/TheMightyTRex", rel: "me noopener noreferrer", target: "_blank" });
    maker.innerHTML = MAKER_MARK;  // a fixed string from this file, never from data
    maker.append("TheMightyTRexUK", el("span", { class: "visually-hidden", text: ", on GitHub (opens in a new tab)" }), icon("external-link"));
    document.body.append(el("footer", { class: "site-footer" },
      el("div", { class: "site-footer__app" },
        el("span", { class: "site-footer__brand" }, brand || "", "Starboard"),
        el("nav", { "aria-label": "Starboard" }, el("ul", { class: "site-footer__links" },
          // The help centre's pages, built from docs/help and published on GitHub Pages.
          link(`${HELP_CENTRE}index.html`, "Help", true), notes,
          repo ? link(`https://github.com/${repo}`, "GitHub repository", true) : null,
          link("/settings-updates.html", newer ? "About and updates (1)" : "About and updates")))),
      maker));
  }
}

// Release notes: one look for every release (Added, Changed, Deprecated, Removed, Fixed, Security, Your settings and the
// way back), in the slide-out from the footer and on the upgrade guide's first step.
function releaseNotes(rel, level = 3) {
  const group = (title, items = []) => items.length ? [el(`h${level + 1}`, { text: title }),
    el("ul", {}, items.map(([t, sentence]) => el("li", {}, el("strong", { text: `${t}. ` }), sentence)))] : [];
  return el("section", { class: "release-notes", "aria-label": `Version ${rel.version}` },
    el(`h${level}`, { text: `Version ${rel.version}` }), el("p", { class: "small muted", text: `Released ${rel.date}` }),
    ...group("Added", rel.added), ...group("Changed", rel.changed), ...group("Deprecated", rel.deprecated),
    ...group("Removed", rel.removed), ...group("Fixed", rel.fixed), ...group("Security", rel.security),
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
      // The newest 3, newest first; the rest are on Settings, Updates, Releases (DASH-110).
      ...r.all.slice(0, 3).map((rel) => releaseNotes(rel, 3)),
      r.all.length > 3 ? el("p", {}, el("a", { href: "/settings-releases.html", text: "Read previous releases" }),
        el("span", { class: "muted", text: ` (${r.all.length - 3} more)` })) : null,
    ].filter(Boolean));
  } catch (e) { panel.body.replaceChildren(el("p", { text: e.message })); }
}

// What is new in an app Starboard updates (Reelix), from the app's own changelog: the versions between the one
// installed and the newest, in the same look as Starboard's release notes. Built as text, never as HTML.
function changeParts(parts) {
  return parts.map(([kind, text]) => kind === "strong" ? el("strong", { text }) : kind === "code" ? el("code", { text }) : text);
}

function changeItems(items) {
  return el("ul", {}, items.map((i) => el("li", {}, ...changeParts(i.parts), i.items.length ? changeItems(i.items) : null)));
}

function appChanges(result, level = 3) {
  if (!result.versions.length) return [el("p", { text: `Nothing in ${result.app}'s changelog for these versions.` })];
  return result.versions.map((v) => el("section", { class: "release-notes", "aria-label": `${result.app} ${v.version}` },
    el(`h${level}`, { text: `Version ${v.version}` }),
    el("p", { class: "small muted", text: v.withdrawn ? `Released ${v.date}, then withdrawn` : `Released ${v.date}` }),
    v.summary.length ? el("p", {}, ...changeParts(v.summary)) : null,
    ...v.sections.flatMap((s) => [el(`h${level + 1}`, { text: s.type }), changeItems(s.items)])));
}

async function openAppChanges({ app, name, from = "", to = "", opener }) {
  const title = `What is new in ${name}`;
  const panel = sidePanel({ title, opener, wide: true, body: [el("p", { class: "muted", text: "Loading…" })] });
  try {
    const r = await api(`/api/app-changes?${new URLSearchParams({ app, from, to })}`);
    const span = r.from && r.to ? `From ${r.from} to ${r.to}` : r.to ? `Version ${r.to}` : `Newer than ${r.from}`;
    panel.body.replaceChildren(el("p", { class: "muted" }, `${span}, from ${r.app}'s changelog. `,
      el("a", { href: r.source, target: "_blank", rel: "noopener noreferrer" }, "The whole changelog",
        el("span", { class: "visually-hidden", text: " (opens in a new tab)" })), "."), ...appChanges(r));
  } catch (e) { panel.body.replaceChildren(el("p", { text: e.message })); }
}

// After an app's version goes up (seen on Apps, Updates): a notice with What is new, until it is closed.
async function appChangeNotices() {
  const main = $("#main .page");
  if (!main) return;
  let list = [];
  try { list = (await api("/api/app-changes/notices")).notices; } catch { return; }
  for (const n of list) {
    const id = `app-change-${n.app}`;
    if (document.getElementById(id)) continue;
    const box = el("div", { class: "notice app-change", id, role: "status" }, icon("circle-arrow-up"),
      el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: `${n.name} is updated to ${n.to}` }),
        el("p", { text: `It was ${n.from}. Its changelog says what is new.` })),
      el("div", { class: "app-change__actions" }, el("button", { type: "button", class: "btn", onclick: (e) => openAppChanges({ app: n.app, name: n.name, from: n.from, to: n.to, opener: e.currentTarget }) },
        "What is new", el("span", { class: "visually-hidden", text: ` in ${n.name}` })),
      el("button", { type: "button", class: "icon-btn", "aria-label": `Close the notice about ${n.name}`, onclick: () => {
        api("/api/app-changes/seen", { method: "POST", body: { app: n.app } }).catch(() => {});
        box.remove();
        $("#main h1")?.focus?.();
      } }, icon("x", 20))));
    main.prepend(box);
  }
}

// The upgrade guide inside a slide-out (?panel=1): only its steps, without the menus around them.
if (new URLSearchParams(location.search).get("panel") === "1" && window.parent !== window) document.documentElement.classList.add("in-panel");

// Still to set up, one at a time (DASH-289, owner, 10 November 2026): a slide-out that walks through each item left,
// with Do it now (the place that does it), Skip (later), Ignore (not asked again; Bring back in the list), Done for
// a guided step, and Next step. It opens by itself once in each browser session while anything is left, and
// remembers where it was when Do it now goes to another page.
const WIZARD_KEY = "starboard.setup-wizard";
function wizardMemory(update) {
  let m = {};
  try { m = JSON.parse(sessionStorage.getItem(WIZARD_KEY) || "{}"); } catch { /* a fresh start */ }
  if (update) { m = { ...m, ...update }; try { sessionStorage.setItem(WIZARD_KEY, JSON.stringify(m)); } catch { /* fine */ } }
  return m;
}
async function setupWizard({ opener = document.activeElement, onChange } = {}) {
  let items;
  try { items = (await api("/api/setup/left")).items.filter((i) => !i.done && !i.ignored); } catch { return; }
  if (!items.length) return;
  const mem = wizardMemory({ opened: true });
  let index = Math.max(0, items.findIndex((i) => i.key === mem.at));
  // Closing it (X or Escape) ends this session's walk-through; Do it now leaves the page, so it carries on there.
  const panel = sidePanel({ title: "Still to set up", opener, wide: false, body: [], onClose: () => { wizardMemory({ at: null }); onChange?.(); } });
  const draw = () => {
    if (index >= items.length) {
      panel.body.replaceChildren(el("div", { class: "stack-4" }, el("h3", { text: "That is all for now" }),
        el("p", { text: "What you skipped stays on the list, so you can come back to it. What you ignored is not asked again." })));
      const close = el("button", { type: "button", class: "btn btn--primary", text: "Close" });
      close.addEventListener("click", () => panel.close());
      panel.setFoot([close]);
      wizardMemory({ at: null });
      close.focus();
      return;
    }
    const item = items[index];
    wizardMemory({ at: item.key });
    const heading = el("h3", { tabindex: "-1", text: item.title });
    const outside = item.href.startsWith("http");
    const doIt = el("a", { class: "btn btn--primary", href: outside ? reachableUrl(item.href) : item.href, ...(outside ? { target: "_blank", rel: "noopener" } : {}) },
      "Do it now", outside ? el("span", { class: "visually-hidden", text: " (opens in a new tab)" }) : null);
    const doneBtn = item.guided ? el("button", { type: "button", class: "btn" }, "Done") : null;
    doneBtn?.addEventListener("click", async () => {
      try { await api("/api/setup/left/done", { method: "POST", body: { key: item.key } }); announce(`${item.title}: done`); items.splice(index, 1); draw(); onChange?.(); }
      catch (e) { problem(e.message, doneBtn); }
    });
    const bar = el("div", { class: "wizard-steps", "aria-hidden": "true" }, items.map((_, i) => el("span", { class: i < index ? "is-past" : i === index ? "is-now" : "" })));
    panel.body.replaceChildren(el("div", { class: "stack-4" },
      el("p", { class: "small muted", text: `Step ${index + 1} of ${items.length}` }), bar, heading,
      el("p", { text: item.why }), el("div", { class: "actions" }, doIt, doneBtn)));
    const skip = el("button", { type: "button", class: "btn", text: "Skip" });
    skip.addEventListener("click", () => { index += 1; draw(); announce("Skipped for now"); });
    const ignore = el("button", { type: "button", class: "btn btn--quiet", text: "Ignore" });
    ignore.addEventListener("click", async () => {
      try { await api("/api/setup/left/ignore", { method: "POST", body: { key: item.key } }); items.splice(index, 1); announce(`${item.title}: not asked again`); draw(); onChange?.(); }
      catch (e) { problem(e.message, ignore); }
    });
    const next = el("button", { type: "button", class: "btn btn--primary", text: index === items.length - 1 ? "Finish" : "Next step" });
    next.addEventListener("click", () => { index += 1; draw(); });
    panel.setFoot([next, skip, ignore]);
    heading.focus();
  };
  draw();
}
// Once in each browser session, on the page with the list, while anything is left.
let wizardStarted = false;
function setupWizardOnce(onChange) {
  if (wizardStarted || $("#side-panel")) return;  // a page that redraws (the dashboard, each minute) asks only once
  wizardStarted = true;
  const mem = wizardMemory();
  if (mem.opened && !mem.at) return;
  setTimeout(() => setupWizard({ onChange }), 600);
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
    el("div", { class: "actions" }, chooseNow(upgrade), el("a", { class: "btn btn--quiet", href: "/upgrade.html" }, "Open as a page"))));
}

// Choose now: the things to choose, in a slide-out over the page you are on (the upgrade guide itself, framed).
function chooseNow(upgrade) {
  const button = el("button", { type: "button", class: "btn btn--primary", "aria-haspopup": "dialog" }, "Choose now");
  button.addEventListener("click", () => {
    const frame = el("iframe", { class: "panel-frame", src: "/upgrade.html?panel=1", title: `Upgrade guide for Starboard ${upgrade.to}` });
    const panel = sidePanel({ title: `Starboard ${upgrade.to}: ${upgrade.count} ${upgrade.count === 1 ? "thing" : "things"} to choose`, opener: button, wide: true, body: [frame] });
    const done = (e) => {
      if (e.origin !== location.origin || !e.data?.starboard) return;
      window.removeEventListener("message", done);
      panel.close();
      if (e.data.starboard === "upgrade-done") { $("#upgrade-notice")?.remove(); toast(`Starboard ${upgrade.to}: your choices are saved`); }
      if (e.data.starboard === "upgrade-later") $("#upgrade-notice")?.remove();
    };
    window.addEventListener("message", done);
  });
  return button;
}

// Display and accessibility panel --------------------------------------

// A slide-out, like every other panel that opens over a page (DESIGN-SYSTEM.md, Consistency rules). Choices apply
// at once and are kept in this browser; Done closes it, Reset goes back to the defaults.
// Set through the style object, which the page's content security policy allows (a style attribute it would not).
function styleSwatch(x) {
  const sw = el("span", { class: "style-swatch", "aria-hidden": "true" });
  sw.style.setProperty("--sw-a", x.light);
  sw.style.setProperty("--sw-b", x.bg_dark);
  return sw;
}

function setUpDisplayPanel() {
  const template = $("#display-panel");
  const opener = $("[data-display-toggle]");
  if (!template || !opener) return;
  opener.addEventListener("click", () => openDisplayPanel(template, opener));
}

function openDisplayPanel(template, opener) {
  const form = template.content.querySelector("[data-display-form]").cloneNode(true);
  const designList = $("[data-design-options]", form);
  // Styles from plug-ins that are turned on (DASH-284), shown above Design; none, and the list stays hidden.
  const styleList = el("div", { class: "option-cards" });
  const styleSet = el("fieldset", { hidden: true }, el("legend", { text: "Style" }),
    el("p", { class: "hint", text: "Colours and shape from your plug-ins, checked for accessibility. High contrast always wins. This browser only." }), styleList);
  designList.closest("fieldset").before(styleSet);
  api("/api/styles").then((r) => {
    if (!r.styles.length) return;
    for (const [value, label, help, swatch] of [["", "Starboard", "The standard colours.", null], ...r.styles.map((x) => [x.value, x.name, `${x.description} From ${x.plugin}.`, x])]) {
      styleList.append(el("label", { class: "option-card" },
        el("input", { type: "radio", name: "style", value, checked: value === readPrefs().style }),
        el("strong", {}, swatch ? styleSwatch(swatch) : null, label),
        el("small", { text: help })));
    }
    styleSet.hidden = false;
  }).catch(() => { /* signed out, or no plug-ins: no list */ });
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
      style: form.querySelector("input[name=style]:checked")?.value || "",
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

// Testing (Settings, General): Snaglist's Send feedback button (web/js/snaglist.js, from
// github.com/TheMightyTRex/snaglist; copy a new version in, never edit it here). Each report goes as a GitHub
// issue on Starboard's repository, or is saved in Starboard (data/ux-notes.json, listed in Settings, General).
// It sends without cookies, so a key given while signed in stands in. The script loads only while it is on.
async function startFeedback(session) {
  if (!session?.version) session = await api("/api/session").catch(() => ({}));
  const { key } = await api("/api/feedback/key");
  const inMenu = $$("[data-feedback-open]");
  const start = () => { window.Snaglist?.start({
    app: "Starboard", version: session.version || "", language: "en-GB", userToggle: false,
    // Pages with the side menu open it from Feedback in the menu. Pages without one, such as the set-up, keep the
    // button bottom left: side panels open on the right, with their Save and Remove buttons at the bottom.
    launcher: inMenu.length ? false : "bottom-left",
    theme: document.documentElement.dataset.theme || "auto", // the theme chosen in Display, or the device's
    types: ["bug", "ux", "visual", "accessibility", "performance", "content", "feature", "idea", "other", "check"],
    send: {
      github: session.repo ? { repo: session.repo } : null,
      endpoint: { url: "/api/feedback", headers: { "X-Starboard": "1", "X-Starboard-Feedback": key } },
      copy: true, download: true,
    },
    text: {
      sendEndpoint: "Save in Starboard",
      endpointNote: "Save in Starboard keeps the report on this server, listed in Settings, General, Send feedback.",
      sent: "Saved in Starboard. It is listed in Settings, General, Send feedback.",
    },
  });
    inMenu.forEach((b) => {
      b.hidden = false;
      if (b.dataset.feedbackReady) return;
      b.dataset.feedbackReady = "1";
      b.addEventListener("click", () => {
        b.closest(".side-panel-layer")?.querySelector("[data-closes]")?.click(); // the phone menu closes first
        window.Snaglist?.open();
      });
    });
  };
  document.documentElement.classList.add("has-feedback");  // the side menu keeps room for the button under it
  if (window.Snaglist) return start();
  document.head.append(el("script", { src: "/js/snaglist.js", onload: start }));
}
function stopFeedback() {
  window.Snaglist?.destroy();
  $$("[data-feedback-open]").forEach((b) => { b.hidden = true; });
}

// The server's name at the start of the level 1 menu; nothing shows when it is empty.
function showServerName(name) {
  $$("[data-server-name]").forEach((n) => {
    n.replaceChildren(el("span", { class: "visually-hidden", text: "Server: " }), name || "");
    n.hidden = !name;
  });
}

// Infinite scroll (DASH-277): a Show more button loads the next lot by itself as it nears the screen. The button
// stays, so keyboard and screen reader users can still use it; focus never moves on its own, and a screen reader
// hears how many were added. Off when the setting asks for the button, or when Reduce motion is on.
let listLoading = "auto";
function autoLoadMore(button, load, noun = "more") {
  if (!button || !("IntersectionObserver" in window)) return;
  const root = document.documentElement;  // Display, Reduce motion: On, Off, or the device's own setting
  const reduced = root.classList.contains("pref-motion") || (!root.classList.contains("pref-motion-off") && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches);
  if (listLoading !== "auto" || reduced) return;
  let busy = false;
  new IntersectionObserver(async (seen) => {
    if (!seen.some((x) => x.isIntersecting) || busy || button.hidden || button.closest("[hidden]") || button.disabled) return;
    busy = true;
    try { const n = await load(); if (n) announce(`${n} ${noun} loaded`); } finally { busy = false; }
  }, { rootMargin: "600px 0px" }).observe(button);
}

async function startPage() {
  setUpHeader();
  setUpDisplayPanel();
  try {
    const session = await api("/api/session");
    serverDesign = session.design || "health";
    applyPrefs();
    $$("[data-site-name]").forEach((n) => { n.textContent = session.site_name; });
    showServerName(session.server_name);
    listLoading = session.infinite_scroll === false ? "button" : "auto";
    document.title = document.title.replace(/ · [^·]*$/, ` · ${session.site_name}`);
    // DASH-238: until the first set-up has finished, only the set-up wizard: no menus, and other pages lead to it.
    if (session.first_setup) {
      document.body.classList.add("first-setup");
      const allowed = ["/setup-guide.html", "/install-apps.html", "/login.html", "/setup.html"];
      if (!allowed.some((p) => location.pathname.endsWith(p))) { location.replace("/setup-guide.html"); return null; }
    }
    showVersion(session.version, session.repo, session.latest);
    upgradeNotice(session.upgrade);
    if (session.ux_notes) startFeedback(session).catch(() => { /* the page works without it */ });
    return session;
  } catch { return null; }
}
