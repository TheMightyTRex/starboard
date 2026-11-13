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

// A small picture of each dashboard design (DASH-315): drawn here as fixed SVG, so it costs no image download and
// follows the theme and high contrast through the .dp-* classes in app.css. The words beside it say what the
// design is, so the picture is hidden from screen readers.
const DESIGN_PICTURES = {
  health: '<rect class="dp-card dp-bad" x="6" y="12" width="108" height="14"/><rect class="dp-edge-bad" x="6" y="12" width="3" height="14"/>'
    + '<rect class="dp-line" x="13" y="17" width="30" height="4"/>'
    + [6, 43, 80].map((x) => [32, 51].map((y) => `<rect class="dp-card" x="${x}" y="${y}" width="34" height="15"/><rect class="dp-edge-ok" x="${x}" y="${y}" width="3" height="15"/><rect class="dp-line" x="${x + 6}" y="${y + 5}" width="18" height="3"/>`).join("")).join(""),
  tiles: [6, 43, 80].map((x) => [12, 40].map((y) => `<rect class="dp-card" x="${x}" y="${y}" width="34" height="24"/><rect class="dp-icon" x="${x + 4}" y="${y + 4}" width="6" height="6"/><rect class="dp-line" x="${x + 13}" y="${y + 5}" width="16" height="3"/><rect class="dp-line dp-soft" x="${x + 4}" y="${y + 14}" width="26" height="2"/><rect class="dp-line dp-soft" x="${x + 4}" y="${y + 18}" width="20" height="2"/>`).join("")).join(""),
  shelf: [10, 25, 40, 55].map((y) => `<rect class="dp-card" x="6" y="${y}" width="108" height="12"/><rect class="dp-icon" x="9" y="${y + 3}" width="6" height="6"/><rect class="dp-line" x="19" y="${y + 3}" width="26" height="3"/><rect class="dp-line dp-soft" x="19" y="${y + 7.5}" width="44" height="2"/><rect class="dp-button" x="96" y="${y + 3}" width="14" height="6"/>`).join(""),
  command: '<rect class="dp-card dp-search" x="18" y="10" width="84" height="12"/><rect class="dp-line dp-soft" x="22" y="15" width="30" height="2"/>'
    + [0, 1, 2, 3, 4, 5].map((n) => [30, 49].map((y) => `<rect class="dp-icon" x="${15 + n * 16}" y="${y}" width="10" height="10"/><rect class="dp-line dp-soft" x="${14 + n * 16}" y="${y + 13}" width="12" height="2"/>`).join("")).join(""),
  board: '<rect class="dp-head" x="6" y="8" width="108" height="8"/>'
    + [18, 26, 34, 42, 50, 58].map((y, n) => `<rect class="dp-row" x="6" y="${y}" width="108" height="7"/><circle class="${n === 2 ? "dp-dot-bad" : "dp-dot-ok"}" cx="11" cy="${y + 3.5}" r="2"/><rect class="dp-line" x="16" y="${y + 2.5}" width="24" height="2"/><rect class="dp-line dp-soft" x="52" y="${y + 2.5}" width="18" height="2"/><rect class="dp-line dp-soft" x="84" y="${y + 2.5}" width="22" height="2"/>`).join(""),
};

function designPicture(key) {
  const box = el("span", { class: "design-picture", "aria-hidden": "true" });
  // A fixed string built in this file from numbers only, never from data.
  box.innerHTML = `<svg viewBox="0 0 120 72" focusable="false"><rect class="dp-frame" x="0.5" y="0.5" width="119" height="71"/>${DESIGN_PICTURES[key] || ""}</svg>`;
  box.dataset.design = key;
  return box;
}

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

// The loading line under the menu (owner, 12 November 2026): the shared .loading-bar on the header's lower edge.
// It shows once any request has taken longer than WAIT_MS, so quick answers never flicker it, and while the next
// page loads after a link is followed. Decorative: what is loading is said by the page itself.
const loading = (() => {
  const WAIT_MS = 300;
  let bar = null, busy = 0, timer = 0;
  const node = () => {
    if (bar?.isConnected) return bar;
    bar = el("div", { class: "loading-bar", "aria-hidden": "true" });
    const header = document.querySelector(".site-header");
    if (header) header.append(bar); else { bar.classList.add("loading-bar--top"); document.body?.prepend(bar); }
    return bar;
  };
  const show = (on) => { const b = document.body ? node() : null; if (b) b.toggleAttribute("data-active", on); };
  const start = () => {
    busy += 1;
    if (busy === 1) timer = setTimeout(() => show(true), WAIT_MS);
  };
  const stop = () => {
    busy = Math.max(0, busy - 1);
    if (!busy) { clearTimeout(timer); show(false); }
  };
  // A new page: from the moment a link takes you to another page here until this one is replaced. Links the page
  // handles itself, downloads, new tabs and links within the page are left alone; ten seconds is the limit.
  window.addEventListener("click", (e) => {
    const a = e.target.closest?.("a[href]");
    if (!a || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    if (a.target && a.target !== "_self" || a.hasAttribute("download") || a.origin !== location.origin) return;
    if (a.pathname === location.pathname && a.search === location.search) return;  // a part of this page
    show(true);
    setTimeout(() => { if (!busy) show(false); }, 10000);
  });
  window.addEventListener("pageshow", () => { if (!busy) show(false); });  // back to a page kept in memory
  return { start, stop };
})();

async function api(path, opts = {}) {
  loading.start();
  try { return await apiCall(path, opts); }
  finally { loading.stop(); }
}

async function apiCall(path, { method = "GET", body } = {}) {
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
    error.data = data;  // which field the problem is about, when the server says (DASH-251)
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
  if (savedBeside(title, options)) return null;
  return window.SharedComponents.toast(title, { ...options, detail });
}
// Settings pattern 2 and 5 (DASH-308): on a Settings page a success says itself beside the control that was just
// used (or, when the section was drawn again, at the foot of that section), never in a toast. Warnings, errors and
// news from elsewhere (no control used in the last 15 seconds) stay toasts.
function savedBeside(text, options) {
  if (options.tone && options.tone !== "success") return false;
  if (!document.querySelector(".page--settings") || !lastUsed || Date.now() - lastUsed.at > 15000) return false;
  let { control, sectionHead } = lastUsed;
  // The part was drawn again after the save (DASH-309): FocusKeeper has put focus on the same control drawn again,
  // so the note goes beside that one.
  if (!control.isConnected) {
    const now = document.activeElement;
    if (now?.matches?.(CONTROLS) && now.closest(".settings-section")?.getAttribute("aria-labelledby") === sectionHead) control = now;
  }
  let spot = null;
  if (control.isConnected && control.getClientRects().length && !control.closest(".side-panel, dialog")) {
    // A choice card or a tick in a group says it under the group, not inside the card.
    const holder = control.closest(".setting__control, .actions, .inline-save, .switch, .field, fieldset, .option-cards") || control;
    spot = holder.classList.contains("switch") && holder.closest(".setting__control") ? holder.closest(".setting__control") : holder;
  } else if (sectionHead) {
    const sec = document.getElementById(sectionHead)?.closest(".settings-section");
    if (!sec) return false;
    spot = [...sec.querySelectorAll(".actions")].pop() || sec.querySelector(".settings-section__head");
  }
  if (!spot) return false;
  const inside = spot.matches(".setting__control, .actions, .settings-section__head");
  let note = inside ? spot.querySelector(":scope > .saved-note") : spot.nextElementSibling?.matches(".saved-note") ? spot.nextElementSibling : null;
  if (!note) {
    note = el("span", { class: "saved-note", hidden: true });
    if (inside) spot.append(note); else spot.after(note);
  }
  window.SharedComponents.savedNote(note, text === "Saved" ? "" : text);
  return true;
}
// Settings pattern 2 (DASH-309): a saved setting says so beside the control that was used ("Saved at 16:31"),
// never in a toast. When there is no such control in view, it is said to screen readers only.
function settingSaved(text) {
  if (!savedBeside(text || "Saved", {})) announce(text || "Saved");
}
// Focus is never lost to the top of the page (screen reader check, 12 November 2026; WCAG 2.4.3 Focus order).
// Many parts are drawn again after a save, a delete or a refresh. When the control that had focus is taken away
// that way, focus moves to the same control drawn again (same id; or the same row and place; or the same name in
// the same section), else to that section's heading, else to the page's h1, so a screen reader carries on from
// where the person was. Slide-outs and dialogs give focus back themselves, so their own closing is left alone.
const FocusKeeper = (() => {
  let last = null;
  const nameOf = (e) => (e.getAttribute("aria-label") || e.textContent || e.value || "").trim().replace(/\s+/g, " ").slice(0, 80);
  const controls = (n) => [...n.querySelectorAll("button, a[href], input, select, textarea, [tabindex]")];
  const describe = (t) => {
    const row = t.closest("[data-key]");
    const section = t.closest("section[aria-labelledby], .settings-section, section");
    return { el: t, id: t.id, name: nameOf(t), tag: t.tagName, key: row?.dataset.key || null, at: row ? controls(row).indexOf(t) : -1,
      head: section?.getAttribute("aria-labelledby") || null, layer: !!t.closest("#side-panel, dialog, .side-panel-layer") };
  };
  document.addEventListener("focusin", (e) => {
    const t = e.target;
    if (!(t instanceof Element) || t === document.body || t.closest(".toasts")) return;
    last = describe(t);
  }, true);
  const shown = (e) => e && e.isConnected && e.getClientRects().length && !e.closest("[hidden], [inert]");
  const land = (e) => {
    if (!e.matches("button, a[href], input, select, textarea, [tabindex]")) e.setAttribute("tabindex", "-1");
    e.focus();
  };
  const find = (l) => {
    const byId = l.id && document.getElementById(l.id);
    if (shown(byId)) return byId;
    if (l.key) {
      const row = [...document.querySelectorAll("[data-key]")].find((n) => n.dataset.key === l.key && shown(n));
      if (row) return (l.at >= 0 && controls(row)[l.at]) || controls(row)[0] || row;
    }
    const heading = l.head && document.getElementById(l.head);
    const scope = heading?.closest("section") || document.querySelector("main");
    const same = scope && controls(scope).find((n) => n.tagName === l.tag && nameOf(n) === l.name && shown(n));
    if (same) return same;
    if (shown(heading)) return heading;
    return document.querySelector("main h1");
  };
  new MutationObserver(() => {
    if (!last || last.el.isConnected) return;
    const l = last;
    last = null;
    if (l.layer || (document.activeElement && document.activeElement !== document.body)) return;
    const to = find(l);
    if (shown(to)) land(to);
  }).observe(document.documentElement, { childList: true, subtree: true });
  // A slide-out or dialog closing gives focus back to what opened it; when that was drawn again meanwhile (a
  // row after Revoke), its stand-in gets focus instead.
  return {
    describe,
    recover(d) {
      if (!d || (document.activeElement && document.activeElement !== document.body)) return;
      const to = d.el?.isConnected && shown(d.el) ? d.el : find({ ...d, el: null });
      if (shown(to)) land(to);
    },
  };
})();

// An error shows beside what it belongs to (content rule): the control named, or the one just used. With
// neither (an error while a page loads), it is an error toast, which stays until it is closed.
const CONTROLS = "button, input, select, textarea";
let lastUsed = null;
for (const type of ["click", "change"]) {
  document.addEventListener(type, (e) => {
    const control = e.target.closest?.(CONTROLS);
    // A confirm dialog closes before its answer comes, so the button that opened it stays the one in use.
    if (control && !control.closest(".toasts, dialog.dialog")) lastUsed = { control, at: Date.now(), sectionHead: control.closest(".settings-section")?.getAttribute("aria-labelledby") || null };
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

// After Show more: focus the first new row's link (or its title), so reading carries on from the new rows.
function focusFirstNew(row) {
  if (!row) return;
  const to = row.querySelector(".row__title a, a[href], button") || row.querySelector(".row__title") || row;
  if (!to.matches("a[href], button, input, select, textarea, [tabindex]")) to.setAttribute("tabindex", "-1");
  to.focus();
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
  // A state chip made with headChip() goes on the title's line, never alone at the top of the body (DASH-309, R3).
  const parts = [body].flat();
  const chipNode = parts.find((n) => n?.dataset?.headChip);
  const bodyNode = el("div", { class: "side-panel__body" }, parts.filter((n) => n !== chipNode));
  const footNode = el("div", { class: "side-panel__foot" }, foot);
  footNode.hidden = !foot.length;
  const layer = el("div", { class: "side-panel-layer", id: "side-panel" },
    el("div", { class: "side-panel-backdrop" }),
    el("aside", { class: wide ? "side-panel side-panel--wide" : "side-panel", role: "dialog", "aria-modal": "true", "aria-labelledby": "side-panel-title" },
      el("div", { class: "panel-header" }, chipNode ? titleChip(heading, chipNode) : heading, close), bodyNode, footNode));
  document.body.append(layer);
  const openedBy = opener instanceof HTMLElement ? FocusKeeper.describe(opener) : null;
  const shut = SharedComponents.openLayer(layer, opener instanceof HTMLElement ? opener : null, () => {
    layer.remove();
    onClose?.();
    setTimeout(() => FocusKeeper.recover(openedBy), 0);
  });
  return {
    layer, body: bodyNode, foot: footNode, close: shut,
    setTitle(text) { heading.textContent = text; close.setAttribute("aria-label", `Close ${text}`); },
    setFoot(nodes) { footNode.replaceChildren(...nodes); footNode.hidden = !nodes.length; },
    // Draws the body again (Check again); a headChip goes on the title's line, as when it opened.
    setBody(nodes) {
      const next = [nodes].flat().filter(Boolean);
      const c = next.find((n) => n?.dataset?.headChip);
      if (c) onTitle(heading, c); else heading.parentElement.querySelector(":scope.title-chip > .chip")?.remove();
      bodyNode.replaceChildren(...next.filter((n) => n !== c));
    },
  };
}

// A slide-out that asks (DASH-309, R6): as confirmDialog, for a list to check or more than two fields, with the
// page still in view. Its one primary button and Cancel are in the foot; resolves true for the primary button and
// false when Cancel, Escape or the close button shut it. Focus goes back to what opened it.
function slideOutConfirm({ title, body, confirm = "Continue", wide = true, opener = document.activeElement }) {
  return new Promise((resolve) => {
    let answered = false;
    const yes = el("button", { type: "button", class: "btn btn--primary" }, confirm);
    const no = el("button", { type: "button", class: "btn" }, "Cancel");
    const panel = sidePanel({ title, wide, opener, body: [body].flat(), foot: [yes, no], onClose: () => { if (!answered) resolve(false); } });
    yes.addEventListener("click", () => { answered = true; resolve(true); panel.close(); });
    no.addEventListener("click", () => panel.close());
  });
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
    const openedBy = opener instanceof HTMLElement ? FocusKeeper.describe(opener) : null;
    dialog.addEventListener("close", () => {
      dialog.remove();
      if (opener?.isConnected) opener.focus();
      resolve(result);
      setTimeout(() => FocusKeeper.recover(openedBy), 0);
    });
    document.body.append(dialog);
    dialog.showModal();
    // Focus starts on the first field it asks for; otherwise on Cancel for a danger choice, so Enter never does
    // the harm by mistake; otherwise on the main button (screen reader check, 12 November 2026).
    const start = $("input, select, textarea", form) || (danger ? $('.dialog__foot button[value="cancel"]', form) : $('.dialog__foot button[value="ok"]', form));
    start?.focus();
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
  // Sign out is in the side menu on every page (issue #9, 12 November 2026) and in the phone menu.
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
  // Every page but Sign in and Set up has the footer (the design system's footer rule).
  const setUp = document.body.classList.contains("first-setup") || /\/(login|setup)\.html$/.test(location.pathname);
  if ($(".site-header") && !$(".site-footer") && !setUp) {
    const brand = $(".site-header__brand svg")?.cloneNode(true);
    const link = (href, text, outside) => el("li", {}, outside
      ? el("a", { href, target: "_blank", rel: "noopener noreferrer" }, text, el("span", { class: "visually-hidden", text: " (opens in a new tab)" }))
      : el("a", { href, text }));
    // Release notes opens the release notes slide-out (UX-50): focus goes into it, and back here when it closes.
    const notes = el("li", {}, el("a", { href: "#release-notes", "aria-haspopup": "dialog", "aria-expanded": "false",
      onclick: (e) => { e.preventDefault(); openReleaseNotes(e.currentTarget); } }, "Release notes"));
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
          // A newer release adds "Upgrade available" to About and updates, in words and with the update dot.
          el("li", {}, el("a", { href: "/settings-updates.html", "data-footer-updates": true }, "About and updates",
            newer ? el("span", { class: "site-footer__upgrade" }, el("span", { class: "update-dot", "aria-hidden": "true" }),
              el("span", { class: "visually-hidden", text: ", " }), "Upgrade available") : null))))),
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
        const h1 = $("#main h1");
        box.remove();
        if (h1) { h1.setAttribute("tabindex", "-1"); h1.focus(); }
      } }, icon("x", 20))));
    // After the page's heading, so a screen reader meets the page's name first (reading order check).
    const head = $(":scope > .page-head", main);
    if (head) head.after(box); else main.prepend(box);
  }
}

// A page inside a slide-out (?panel=1), such as the upgrade guide or a Still to set up step: only its content,
// without the menus around it, and without its own wizard, Send feedback or upgrade notice (the page around it has them).
const IN_PANEL = new URLSearchParams(location.search).get("panel") === "1" && window.parent !== window;
if (IN_PANEL) document.documentElement.classList.add("in-panel");
// A link to a part of a page (#rx-basics-h) whose part is drawn after the page loads: scroll to it once it is there,
// and put the keyboard there too. Stops looking after 8 seconds; a page with no #part does nothing.
if (location.hash.length > 1) {
  const want = decodeURIComponent(location.hash.slice(1));
  const reach = () => {
    const target = document.getElementById(want);
    if (!target) return false;
    target.scrollIntoView({ block: "start" });
    if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
    if (document.activeElement !== target) target.focus({ preventScroll: true });
    return true;
  };
  document.addEventListener("DOMContentLoaded", () => {
    // Parts drawn above it later push it down (VM test): it is kept in view while the page fills in, until the person
    // scrolls or presses a key, and for 8 seconds at most.
    let found = false;
    const stop = () => { watch.disconnect(); ["wheel", "keydown", "touchstart", "pointerdown"].forEach((e) => removeEventListener(e, stop, true)); };
    const watch = new MutationObserver(() => { found = reach() || found; });
    ["wheel", "keydown", "touchstart", "pointerdown"].forEach((e) => addEventListener(e, stop, true));
    found = reach();
    watch.observe(document.body, { childList: true, subtree: true });
    setTimeout(stop, 8000);
  });
}
// Only the part a step needs (owner, 12 November 2026: "just the setting that is needed for each step"): with
// ?only=1 and a #part, the page in the slide-out shows that part's section and nothing else of the page. Pages redraw
// as they load, so it is kept that way while the page is open (one small check per change, nothing on a timer).
if (IN_PANEL && location.hash.length > 1 && new URLSearchParams(location.search).get("only") === "1") {
  const want = decodeURIComponent(location.hash.slice(1));
  const narrow = () => {
    const target = document.getElementById(want);
    const main = document.getElementById("main");
    if (!target || !main || !main.contains(target)) return;
    const keep = target.closest("section") || target;
    document.documentElement.classList.add("panel-only");
    keep.classList.add("panel-keep");  // shown even when it is an advanced section and Advanced settings is off
    for (let node = keep; node && node !== main; node = node.parentElement) {
      for (const sib of node.parentElement.children) {
        if (sib !== node && !sib.matches("script, template, #announcer")) sib.classList.add("panel-off");
      }
      node.classList.remove("panel-off");
    }
  };
  document.addEventListener("DOMContentLoaded", () => {
    narrow();
    new MutationObserver(narrow).observe(document.body, { childList: true, subtree: true });
  });
}
// The address of a Starboard page for a slide-out: ?panel=1 before any #part, such as /settings-reelix.html#rx-indexers-h.
// { only: true } shows just that part (Still to set up).
function panelUrl(href, { only = false } = {}) {
  const url = new URL(href, location.origin);
  url.searchParams.set("panel", "1");
  if (only && url.hash) url.searchParams.set("only", "1");
  return url.pathname + url.search + url.hash;
}

// The folder picker (DASH-240, decided 10 November 2026): a field for a folder on this computer with Browse. Typing
// still works; leaving the field checks it and says in plain words what happens (there, made for you, free space,
// a folder Starboard never uses). Browse opens a slide-out of folders, one level at a time, to choose from.
// folderField({ id, label, value, hint }) returns { node, input }; read input.value as usual.
let folderCount = 0;
function folderField({ id, label, value = "", hint = "", input: given = null, required = false }) {
  const input = given || el("input", { class: "input", id, value, spellcheck: "false", autocomplete: "off" });
  id = input.id || id || `folder-${++folderCount}`;
  input.id = id;
  if (required) input.required = true;
  input.setAttribute("aria-describedby", `${hint ? `${id}-hint ` : ""}${id}-check ${id}-error`);
  // The same error spot as Settings' field(), so a page's setError and showProblemNear still work.
  const error = el("span", { class: "field-error", id: `${id}-error`, hidden: true });
  input.fieldError = error;
  const browse = el("button", { type: "button", class: "btn", "aria-haspopup": "dialog" }, icon("folder-open"), "Browse",
    el("span", { class: "visually-hidden", text: ` for ${label.toLowerCase()}` }));
  const said = el("div", { class: "small folder-check", id: `${id}-check`, "aria-live": "polite" });
  let last = "";
  const check = async () => {
    const v = input.value.trim();
    if (!v || v === last) return;
    last = v;
    try {
      const r = await api(`/api/folders/check?path=${encodeURIComponent(v)}`);
      if (r.ok && r.path !== input.value) input.value = r.path;  // tidied: spaces and a trailing slash gone
      last = input.value;
      said.dataset.tone = r.ok ? "" : "danger";
      said.replaceChildren(...r.lines.map((l) => el("p", { text: l })));
    } catch { said.replaceChildren(); }
  };
  input.addEventListener("change", check);
  input.addEventListener("blur", check);
  browse.addEventListener("click", () => folderBrowser(input.value.trim(), browse, (chosen) => { input.value = chosen; input.dispatchEvent(new Event("input", { bubbles: true })); check(); input.focus(); }));
  if (input.value) setTimeout(check, 0);
  const hintNode = hint ? el("span", { class: "hint", id: `${id}-hint`, text: hint }) : null;
  input.fieldHint = hintNode;
  const node = el("div", { class: "field", "data-span": "all" }, el("label", { for: id, text: label }), hintNode,
    el("div", { class: "folder-field" }, input, browse), error, said);
  return { node, input };
}

// Settings pattern 4, a location (DASH-310, approved 12 November 2026): the folder in words with its free space, the
// path small under it, Browse that opens where the folder is, Set automatically (the right folder for this setting)
// and the typed path under Advanced. app is whose view of the folders the path is in: "reelix" (inside /data) or
// "host" (this computer). setting picks what Set automatically gives. onChange(path) runs after Browse, Set
// automatically or typing; without it, read input.value when saving.
// locationPicker({ id, label, value, app, setting, hint, onChange }) returns { node, input, refresh }.
let locationCount = 0;
function locationPicker({ id, label, value = "", app = "host", setting = "", hint = "", onChange = null, input: given = null }) {
  const input = given || el("input", { class: "input", value, spellcheck: "false", autocomplete: "off" });
  id = input.id || id || `location-${++locationCount}`;
  input.id = id;
  const error = el("span", { class: "field-error", id: `${id}-error`, hidden: true });
  input.fieldError = error;
  input.setAttribute("aria-describedby", `${id}-words ${id}-error`);
  const words = el("span", { class: "location__words", id: `${id}-words`, "aria-live": "polite" });
  const path = el("span", { class: "location__path" });
  const browse = el("button", { type: "button", class: "btn", "aria-haspopup": "dialog" }, icon("folder-open"), "Browse",
    el("span", { class: "visually-hidden", text: ` for ${label.toLowerCase()}` }));
  const auto = el("button", { type: "button", class: "btn btn--quiet", hidden: true }, "Set automatically",
    el("span", { class: "visually-hidden", text: ` for ${label.toLowerCase()}` }));
  const type = el("details", { class: "location__type" }, el("summary", {}, "Type a path (Advanced)"),
    el("label", { for: id, class: "visually-hidden", text: label }), input, error);
  let last = null, seen = null;
  const show = (r) => {
    seen = r;
    path.textContent = r.path || "";
    path.hidden = !r.path;
    const free = r.free != null ? `${formatBytes(r.free)} free` : "";
    words.dataset.tone = r.ok ? "" : "danger";
    words.textContent = [r.ok ? r.words : "", free, ...r.lines].filter(Boolean).join(" · ");
    browse.disabled = !r.can_browse;
    auto.hidden = !r.suggest || r.suggest === r.path;
  };
  const refresh = async () => {
    const v = input.value.trim();
    if (v === last) return seen;
    last = v;
    try { show(await api(`/api/locations?app=${encodeURIComponent(app)}&for=${encodeURIComponent(setting)}&path=${encodeURIComponent(v)}`)); }
    catch (e) { words.dataset.tone = "danger"; words.textContent = e.message; }
    return seen;
  };
  const set = async (v) => {
    input.value = v;
    error.hidden = true;
    input.removeAttribute("aria-invalid");
    input.dispatchEvent(new Event("input", { bubbles: true }));
    await refresh();
    if (onChange && seen?.ok !== false) onChange(v);
  };
  input.addEventListener("change", () => set(input.value.trim()));
  auto.addEventListener("click", () => { if (seen?.suggest) set(seen.suggest); });
  browse.addEventListener("click", async () => {
    const r = seen || await refresh();
    folderBrowser(r?.start || r?.host || "", browse, async (host) => {
      try {
        const out = await api(`/api/locations/chosen?app=${encodeURIComponent(app)}&host=${encodeURIComponent(host)}`);
        await set(out.path);
      } catch (e) { words.dataset.tone = "danger"; words.textContent = e.message; }
      browse.focus();
    });
  });
  const node = el("div", { class: "location", "data-span": "all" },
    el("div", { class: "location__now" }, el("span", { class: "location__label", text: label }),
      hint ? el("span", { class: "small muted", text: hint }) : null, words, path),
    el("div", { class: "location__actions" }, browse, auto), type);
  // A problem shown by setError opens the typed path, so the message is next to it.
  input.addEventListener("invalid", () => { type.open = true; });
  new MutationObserver(() => { if (!error.hidden) type.open = true; }).observe(error, { attributes: true, attributeFilter: ["hidden"] });
  setTimeout(refresh, 0);
  return { node, input, refresh };
}

// Settings pattern 2: a number with its unit beside it (20 | MB/s), the unit part of the control.
function unitInput(input, unit) {
  input.classList.add("input");
  if (!input.getAttribute("inputmode")) input.setAttribute("inputmode", "numeric");
  return el("span", { class: "input-unit" }, input, el("span", { class: "input-unit__unit", "aria-hidden": "true", text: unit }));
}

// Settings pattern 7: what is missing and the one thing to do.
function emptyState(title, text, action = null) {
  return el("div", { class: "empty" }, el("p", {}, el("strong", { text: title })), text ? el("p", { text }) : null, action);
}

async function folderBrowser(start, opener, onChoose) {
  const list = el("ul", { class: "folder-list", role: "listbox", "aria-label": "Folders", tabindex: "0" });
  const crumbs = el("nav", { class: "folder-crumbs", "aria-label": "Where you are" });
  const info = el("p", { class: "small muted", "aria-live": "polite" });
  const choose = el("button", { type: "button", class: "btn btn--primary", text: "Choose this folder" });
  const cancel = el("button", { type: "button", class: "btn", text: "Cancel" });
  const panel = sidePanel({ title: "Choose a folder", opener, body: [crumbs, info, list], foot: [choose, cancel] });
  cancel.addEventListener("click", () => panel.close());
  let here = "", active = 0, typed = "", typedAt = 0;
  const pick = (i) => {
    const items = [...list.children];
    if (!items.length) return;
    active = Math.max(0, Math.min(i, items.length - 1));
    items.forEach((n, k) => n.setAttribute("aria-selected", String(k === active)));
    list.setAttribute("aria-activedescendant", items[active].id);
    items[active].scrollIntoView({ block: "nearest" });
  };
  const open = async (path) => {
    let r;
    try { r = await api(`/api/folders?path=${encodeURIComponent(path || "")}`); }
    catch (e) { if (path) { info.textContent = `${e.message}. Showing the places to start from.`; return open(""); } info.textContent = e.message; return; }
    here = r.path;
    choose.disabled = !here;
    crumbs.replaceChildren(el("button", { type: "button", class: "btn btn--quiet btn--compact", text: "All places", onclick: () => open("") }),
      ...r.crumbs.map((c, k) => [el("span", { "aria-hidden": "true", text: "/" }),
        el("button", { type: "button", class: "btn btn--quiet btn--compact", text: c.name, "aria-current": k === r.crumbs.length - 1 ? "location" : null, onclick: () => open(c.path) })]).flat());
    info.textContent = r.why || [here ? `In ${r.crumbs.map((c) => c.name).join("/").replace(/^\/\//, "/")}` : "Choose where to start", r.free != null ? `${formatBytes(r.free)} free on its disk` : "",
      r.folders.length ? `${r.folders.length} ${r.folders.length === 1 ? "folder" : "folders"}` : "No folders inside"].filter(Boolean).join(" · ");
    list.replaceChildren(...r.folders.map((f, k) => el("li", { role: "option", id: `folder-opt-${k}`, "aria-selected": "false", "data-path": f.path,
      onclick: () => open(f.path) }, icon("folder"), el("span", { text: f.name }))));
    active = 0;
    if (r.folders.length) pick(0);
    list.focus();
  };
  // Up and Down move, Enter or Right opens, Left or Backspace goes up, letters jump to a folder.
  list.addEventListener("keydown", (e) => {
    const items = [...list.children];
    if (e.key === "ArrowDown") { e.preventDefault(); pick(active + 1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); pick(active - 1); }
    else if ((e.key === "Enter" || e.key === "ArrowRight") && items[active]) { e.preventDefault(); open(items[active].dataset.path); }
    else if ((e.key === "ArrowLeft" || e.key === "Backspace") && here) { e.preventDefault(); open(here.split("/").slice(0, -1).join("/") || ""); }
    else if (e.key.length === 1 && /\S/.test(e.key)) {
      typed = Date.now() - typedAt < 700 ? typed + e.key.toLowerCase() : e.key.toLowerCase();
      typedAt = Date.now();
      const k = items.findIndex((n) => n.textContent.toLowerCase().startsWith(typed));
      if (k >= 0) pick(k);
    }
  });
  choose.addEventListener("click", () => { if (here) { panel.close(); onChoose(here); } });
  open(start);
}

// Still to set up, one at a time (DASH-289, owner, 10 November 2026): a slide-out that walks through each item left,
// with Skip (later), Ignore (not asked again; Bring back in the list), Done for a guided step, and Next step.
// Starboard's own steps show their page inside the slide-out, so the set-up is done there (owner, 10 November
// 2026); another app's step (Tdarr, Wizarr...) opens that app in a new tab, as apps do not let Starboard frame them. It opens only from Go through them,
// and remembers where it was when Open as a page goes to another page.
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
  const mem = wizardMemory({ opened: true, started: true });
  let index = Math.max(0, items.findIndex((i) => i.key === mem.at));
  // Closing it (X or Escape) ends this session's walk-through; Do it now leaves the page, so it carries on there.
  const panel = sidePanel({ title: "Still to set up", opener, wide: true, body: [], onClose: () => { wizardMemory({ at: null, started: false }); onChange?.(); } });
  // After a step's page saves, Next step asks again, so a finished step says so and leaves the list.
  const recheck = async (item) => {
    try {
      const now = (await api("/api/setup/left")).items.find((i) => i.key === item.key);
      if (now && now.done) { announce(`${item.title}: done`); onChange?.(); return true; }
    } catch { /* carry on */ }
    return false;
  };
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
    const doIt = outside ? el("a", { class: "btn btn--primary", href: reachableUrl(item.href), target: "_blank", rel: "noopener" },
      "Open the app", el("span", { class: "visually-hidden", text: " (opens in a new tab)" }))
      : el("a", { class: "btn btn--quiet", href: item.href }, "Open as a page");
    const frame = outside ? null : el("iframe", { class: "panel-frame wizard-frame", src: panelUrl(item.href, { only: true }), title: `${item.title}: set it up here` });
    // The step's page may put focus on its first field as it loads; the step's heading keeps it, so the step is
    // read first and Tab then goes into the page.
    if (frame) {
      let acted = false;
      const mark = () => { acted = true; };
      panel.layer.addEventListener("keydown", mark, { once: true });
      panel.layer.addEventListener("pointerdown", mark, { once: true });
      const keep = () => { if (!acted && document.activeElement === frame && frame.isConnected) heading.focus(); };
      window.addEventListener("blur", () => setTimeout(keep, 0));
      frame.addEventListener("load", () => { keep(); setTimeout(keep, 800); setTimeout(keep, 2000); });
    }
    const doneBtn = item.guided ? el("button", { type: "button", class: "btn" }, "Done") : null;
    doneBtn?.addEventListener("click", async () => {
      try { await api("/api/setup/left/done", { method: "POST", body: { key: item.key } }); announce(`${item.title}: done`); items.splice(index, 1); draw(); onChange?.(); }
      catch (e) { problem(e.message, doneBtn); }
    });
    const bar = el("div", { class: "wizard-steps", "aria-hidden": "true" }, items.map((_, i) => el("span", { class: i < index ? "is-past" : i === index ? "is-now" : "" })));
    panel.body.replaceChildren(el("div", { class: frame ? "wizard-step wizard-step--framed" : "wizard-step" },
      el("div", { class: "stack-4 wizard-step__head" },
        el("p", { class: "small muted", text: `Step ${index + 1} of ${items.length}` }), bar, heading,
        el("p", { text: item.why }), el("div", { class: "actions" }, doIt, doneBtn)),
      frame));
    const skip = el("button", { type: "button", class: "btn", text: "Skip" });
    skip.addEventListener("click", () => { index += 1; draw(); announce("Skipped for now"); });
    const ignore = el("button", { type: "button", class: "btn btn--quiet", text: "Ignore" });
    ignore.addEventListener("click", async () => {
      try { await api("/api/setup/left/ignore", { method: "POST", body: { key: item.key } }); items.splice(index, 1); announce(`${item.title}: not asked again`); draw(); onChange?.(); }
      catch (e) { problem(e.message, ignore); }
    });
    const next = el("button", { type: "button", class: "btn btn--primary", text: index === items.length - 1 ? "Finish" : "Next step" });
    next.addEventListener("click", async () => {
      next.disabled = true;
      if (!item.guided && await recheck(item)) { items.splice(index, 1); draw(); return; }
      index += 1; draw();
    });
    panel.setFoot([next, skip, ignore]);
    heading.focus();
  };
  draw();
}
// Still to set up opens only when the person selects Go through them (owner, 12 November 2026: "it should only open
// when you select Go through them"; it used to open by itself once a session). A walk-through the person started and
// left with Open as a page carries on where it was on the next page with the list.
let wizardStarted = false;
function setupWizardOnce(onChange) {
  if (wizardStarted || IN_PANEL || $("#side-panel")) return;
  wizardStarted = true;
  const mem = wizardMemory();
  if (!mem.at || !mem.started) return;
  const h1 = $("main h1");
  if (h1) h1.setAttribute("tabindex", "-1");
  setTimeout(() => setupWizard({ onChange, opener: h1 || undefined }), 300);
}

// After an upgrade: with something to choose, a notice opens the upgrade guide (or waits, with Remind me later);
// with nothing to choose, the upgrade is marked as seen and the notes stay under the version.
function upgradeNotice(upgrade) {
  if (!upgrade || IN_PANEL || upgrade.from === upgrade.to || /\/(upgrade|setup-guide)\.html$/.test(location.pathname)) return;
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

// Reset style (owner, 10 November 2026): back to Starboard's standard colours in this browser, leaving every other
// Display choice as it is. In the Display panel and in Settings, General.
function resetStyle() {
  const prefs = { ...readPrefs(), style: "" };
  writePrefs(prefs);
  applyPrefs(prefs);
  announce("Style reset to Starboard's standard colours");
  document.dispatchEvent(new CustomEvent("stylechange"));
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
  const styleReset = el("button", { type: "button", class: "btn btn--quiet btn--compact" }, icon("rotate-ccw"), "Reset style");
  const styleSet = el("fieldset", { hidden: true }, el("legend", { text: "Style" }),
    el("p", { class: "hint", text: "Colours and shape from your plug-ins, checked for accessibility. High contrast always wins. This browser only." }), styleList,
    el("div", { class: "actions" }, styleReset));
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
    // Each design's small picture (DASH-315); the dashboard's default shows the design that is the default.
    designList.append(el("label", { class: "option-card" },
      el("input", { type: "radio", name: "design", value }),
      el("strong", { text: label }),
      help ? el("small", { text: help }) : el("small", { text: `The default is ${DESIGNS[serverDesign]?.[0] || "Health first"}.` }),
      designPicture(value || serverDesign)));
  }
  const fill = () => {
    const p = readPrefs();
    $$("input[name=style]", form).forEach((r) => { r.checked = r.value === (p.style || ""); }); // Reset un-ticks a style too
    styleReset.disabled = !p.style;
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
  form.addEventListener("change", (e) => {
    save();
    styleReset.disabled = !readPrefs().style;
    if (e.target.name === "style") document.dispatchEvent(new CustomEvent("stylechange"));  // Settings, General shows it
  });
  styleReset.addEventListener("click", () => { resetStyle(); fill(); });
  const done = el("button", { type: "button", class: "btn btn--primary", text: "Done" });
  const reset = el("button", { type: "button", class: "btn", text: "Reset" });
  fill();
  opener.setAttribute("aria-expanded", "true");
  const panel = sidePanel({ title: "Display and accessibility", opener, body: [form], foot: [done, reset],
    onClose: () => opener.setAttribute("aria-expanded", "false") });
  form.addEventListener("submit", (e) => { e.preventDefault(); panel.close(); });
  done.addEventListener("click", () => panel.close());
  reset.addEventListener("click", () => { writePrefs(DEFAULT_PREFS); applyPrefs(DEFAULT_PREFS); fill(); announce("Display settings reset"); document.dispatchEvent(new CustomEvent("stylechange")); });
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
  if (IN_PANEL) return;  // the page around the slide-out has it
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

// Settings, Plug-ins (DASH-318): the level 2 menu is Manage, Catalogue, then one tab for each plug-in added.
function pluginTabs(list) {
  const nav = $('.site-header__tabs nav[aria-label="Plug-ins"]');
  if (!nav || !list.length) return;
  const here = location.pathname.endsWith("/settings-plugin.html") ? new URLSearchParams(location.search).get("id") : null;
  if (here) $$("a[aria-current]", nav).forEach((a) => a.removeAttribute("aria-current"));
  const tpl = $("a", nav);
  for (const p of list) {
    const a = tpl.cloneNode(true);
    a.href = `/settings-plugin.html?id=${encodeURIComponent(p.id)}`;
    a.removeAttribute("aria-current");
    if (p.id === here) a.setAttribute("aria-current", "page");
    a.querySelector("svg")?.replaceWith(icon("puzzle"));
    a.querySelector(".menu-tabs__label").textContent = p.name;
    nav.append(a);
  }
}

// Logos legible in light and dark (owner, 12 November 2026): a network's logo is measured once, in the first browser
// that shows it (mostly light, mostly dark, or on its own solid background), and the answer is kept on the server, so
// no logo is measured again. CSS keeps each logo's own colours and uses the tone only to choose the tile behind it
// (13 November 2026): a dark tile for a white logo, a light tile for a dark one.
function logoTone(img, name, tone, kind = "network") {
  if (tone) { img.dataset.tone = tone; return img; }
  img.addEventListener("load", () => {
    try {
      const c = document.createElement("canvas");
      c.width = c.height = 48;
      const x = c.getContext("2d", { willReadFrequently: true });
      x.drawImage(img, 0, 0, 48, 48);
      const px = x.getImageData(0, 0, 48, 48).data;
      let seen = 0, solid = 0, light = 0, pale = 0, vivid = 0;
      for (let i = 0; i < px.length; i += 4) {
        const a = px[i + 3] / 255;
        if (a < 0.12) continue;
        seen += 1;
        if (a > 0.9) solid += 1;
        const lum = (0.2126 * px[i] + 0.7152 * px[i + 1] + 0.0722 * px[i + 2]) / 255;
        light += a * lum;
        if (lum > 0.6) pale += 1;
        if (Math.max(px[i], px[i + 1], px[i + 2]) - Math.min(px[i], px[i + 1], px[i + 2]) > 80) vivid += 1;
      }
      if (!seen) return;
      // A picture that fills its whole square with paint has its own background; otherwise light or dark ink.
      // Light and dark ink together (a dark disc with light letters) also keeps its own look, or its letters would go.
      // Light and dark ink together on a painted shape goes on a black tile (issues #12 and #13): mostly pale paint
      // with dark letters (Cinemax) has its shades reversed, so the letters are white; coloured paint with white
      // letters (Sky Max) keeps its colours, so the white letters stay white.
      // A strongly coloured logo with some white in it counts too: Sky Max is only 15% white (issue #13).
      const mixed = (pale / seen > 0.15 && pale / seen < 0.85) || (vivid / seen > 0.5 && pale / seen > 0.05 && pale / seen < 0.5);
      const t = seen / (48 * 48) > 0.92 && solid / seen > 0.9 ? "solid"
        : mixed ? (pale / seen >= 0.5 ? "invert" : "boxed") : light / seen > 0.6 ? "light" : "dark";
      img.dataset.tone = t;
      api("/api/library/network-logo/tone", { method: "POST", body: { name, tone: t, kind } }).catch(() => { /* measured again next time */ });
    } catch { /* a picture the browser will not let us read: it keeps the standard look */ }
  }, { once: true });
  return img;
}

// One of several (DASH-309, R4: DESIGN-SYSTEM.md section 10): a segmented control of radios, All first, each
// choice with its count ("Films 12"). Radios give the arrow keys; the ids stay the same when it is drawn again, so
// focus comes back to the chosen one. options: [[value, words, count]], count may be left out.
function segmentedFilter({ name, label, options, value, onChange }) {
  const box = el("fieldset", { class: "segmented", "data-filter": name }, el("legend", { class: "visually-hidden", text: label }));
  for (const [v, words, count] of options) {
    const id = `${name}-${String(v || "all").replace(/[^\w-]+/g, "-").toLowerCase()}`;
    const input = el("input", { type: "radio", name, id, value: String(v ?? ""), checked: String(v ?? "") === String(value ?? "") });
    input.addEventListener("change", () => { if (input.checked) onChange(v); });
    box.append(el("label", { for: id }, input, el("span", { text: count == null ? words : `${words} ${Number(count).toLocaleString("en-GB")}` })));
  }
  return box;
}

// A state chip on its title's line (owner, 12 November 2026, a rule: DESIGN-SYSTEM.md, Chips): the title on the left,
// the chip at the right, centred on the line. headChip() marks a chip for a section's or a card's heading; onTitle()
// puts one beside any title now (a heading drawn earlier, such as a section's h2).
function headChip(...args) {
  const c = chip(...args);
  c.dataset.headChip = "1";
  return c;
}
function titleChip(title, chipNode) {
  return el("div", { class: "title-chip" }, title, chipNode);
}
function onTitle(title, chipNode) {
  if (!title) return;
  const row = title.parentElement?.classList.contains("title-chip") ? title.parentElement : null;
  if (row) { row.querySelector(":scope > .chip")?.remove(); row.append(chipNode); return; }
  const wrap = el("div", { class: "title-chip" });
  title.replaceWith(wrap);
  wrap.append(title, chipNode);
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
    // Menu items that belong to a plug-in show only once it is added (owner, 12 November 2026).
    const added = new Set((session.plugins || []).map((p) => p.id));
    $$("[data-plugin]").forEach((n) => { n.hidden = !added.has(n.dataset.plugin); });
    pluginTabs(session.plugins || []);
    showVersion(session.version, session.repo, session.latest);
    upgradeNotice(session.upgrade);
    if (session.ux_notes) startFeedback(session).catch(() => { /* the page works without it */ });
    return session;
  } catch { return null; }
}

// A row of cards that goes past the screen's edge (issue #17): the design system's shelf (UX-30), with no scroll bar,
// the edges fading into the page where there is more, and an arrow over each fade. Wraps `list` (a ul) and returns
// the wrapper to put in its place; the shelf sets itself up once it is on the page. The arrows are for the mouse and
// touch: Tab goes through the cards themselves and the row follows the focus, so the arrows are left out of the Tab
// order (they sit halfway up the row, so Tab would jump back up to them); they keep their names for screen readers
// and voice control.
function shelfScroller(list, name) {
  list.classList.add("shelf-track");
  const box = el("div", { class: "shelf-scroller" },
    list,
    el("div", { class: "shelf-edge shelf-edge--start", hidden: true },
      el("button", { type: "button", class: "shelf-arrow", tabindex: "-1", "aria-label": `Earlier in ${name}` }, icon("chevron-left"))),
    el("div", { class: "shelf-edge shelf-edge--end", hidden: true },
      el("button", { type: "button", class: "shelf-arrow", tabindex: "-1", "aria-label": `More in ${name}` }, icon("chevron-right"))));
  const outer = el("div", { class: "shelf-holder" }, box);  // setup() looks inside what it is given
  requestAnimationFrame(() => window.SharedComponents?.setup(outer));
  return outer;
}
