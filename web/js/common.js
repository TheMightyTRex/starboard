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

function chip(text, tone) { return el("span", { class: "chip", "data-tone": tone, text }); }

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
  if (res.status === 401 && !location.pathname.startsWith("/login")) {
    location.href = "/login.html?next=" + encodeURIComponent(location.pathname + location.search);
    throw new Error("Sign in first");
  }
  if (!res.ok) throw new Error(data.error || `Something went wrong (error ${res.status})`);
  return data;
}

let toastTimer;
function toast(message) {
  let node = $("#toast");
  if (!node) { node = el("div", { id: "toast", class: "toast", role: "status" }); document.body.append(node); }
  node.textContent = message;
  node.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { node.hidden = true; }, 6000);
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
    toast(ok ? `Copied ${label}` : `Could not copy. The address is ${text}`);
  });
  return button;
}

// The app's own icon, fetched and kept by the server; its initials when there is none.
function appIcon(s, className = "app__icon") {
  const box = el("span", { class: `${className} has-image`, "aria-hidden": "true" });
  const img = el("img", { src: `/api/icons/${encodeURIComponent(s.id)}?v=${encodeURIComponent(s.icon || "")}`, alt: "", loading: "lazy", decoding: "async" });
  img.addEventListener("error", () => { img.remove(); box.classList.remove("has-image"); box.textContent = monogram(s.name); });
  box.append(img);
  return box;
}

// Header ---------------------------------------------------------------

function setUpHeader() {
  // Phone menu: a drawer from the left. <dialog> traps focus and closes with Escape.
  const drawer = $("#phone-menu");
  const opener = $("[data-phone-menu-open]");
  if (drawer && opener) {
    opener.addEventListener("click", () => { drawer.showModal(); opener.setAttribute("aria-expanded", "true"); });
    drawer.addEventListener("close", () => { opener.setAttribute("aria-expanded", "false"); opener.focus(); });
    $("[data-phone-menu-close]", drawer).addEventListener("click", () => drawer.close());
    drawer.addEventListener("click", (e) => { if (e.target === drawer) drawer.close(); });  // the backdrop
    $$(".phone-menu-section > button", drawer).forEach((button) => button.addEventListener("click", () => {
      const open = button.getAttribute("aria-expanded") !== "true";
      button.setAttribute("aria-expanded", String(open));
      $(`#${button.getAttribute("aria-controls")}`).hidden = !open;
    }));
    matchMedia("(min-width: 900px)").addEventListener("change", (e) => { if (e.matches && drawer.open) drawer.close(); });
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

function showVersion(version, repo) {
  if (!version) return;
  const label = `Starboard: v${version}`;
  $$("[data-version]").forEach((n) => { n.textContent = label; });
  if ($(".site-header") && !$(".site-footer")) {
    document.body.append(el("footer", { class: "site-footer" },
      el("span", { class: "version-label", text: label }),
      repo ? el("a", { href: `https://github.com/${repo}`, target: "_blank", rel: "noopener noreferrer" }, "GitHub repository", el("span", { class: "visually-hidden", text: " (opens in a new tab)" })) : null,
      el("a", { href: "/settings-updates.html", text: "Updates" })));
  }
}

// Display and accessibility panel --------------------------------------

function setUpDisplayPanel() {
  const dialog = $("#display-panel");
  const opener = $("[data-display-toggle]");
  if (!dialog || !opener) return;
  const form = $("form", dialog);
  const designList = $("[data-design-options]", dialog);
  const choices = [["", "Use the dashboard's default"], ...Object.entries(DESIGNS).map(([k, v]) => [k, v[0], v[1]])];
  for (const [value, label, help] of choices) {
    designList.append(el("label", { class: "design-option" },
      el("input", { type: "radio", name: "design", value }),
      el("span", { text: label }),
      help ? el("small", { text: help }) : null));
  }
  const fill = () => {
    const p = readPrefs();
    form.theme.value = p.theme; form.text.value = p.text; form.motion.value = p.motion; form.design.value = p.design;
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
  form.addEventListener("submit", (e) => { e.preventDefault(); dialog.close(); });
  $("[data-display-reset]", dialog).addEventListener("click", () => { writePrefs(DEFAULT_PREFS); applyPrefs(DEFAULT_PREFS); fill(); announce("Display settings reset"); });
  $("[data-dialog-close]", dialog).addEventListener("click", () => dialog.close());
  opener.addEventListener("click", () => { fill(); dialog.showModal(); opener.setAttribute("aria-expanded", "true"); });
  dialog.addEventListener("close", () => { opener.setAttribute("aria-expanded", "false"); opener.focus(); });
}

// Every dialog closes with its X button and returns focus (the browser handles Escape and focus trapping).
function wireDialog(dialog) {
  $$("[data-dialog-close]", dialog).forEach((b) => b.addEventListener("click", () => dialog.close()));
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
    showVersion(session.version, session.repo);
    return session;
  } catch { return null; }
}
