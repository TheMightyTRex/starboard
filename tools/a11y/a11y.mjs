// Accessibility check of every page (owner, 12 November 2026: "a full accessibility check. Keyboard and screen readers
// and other assistive tools"), against the example-data server; tools/a11y.sh runs it in the Playwright image.
// The design system's ACCESSIBILITY.md is the checklist: WCAG 2.2 AA by axe-core in Light, Dark and High contrast;
// one h1, headings in order, landmarks, the skip link first, the tab title; keyboard order with visible focus and no
// trap; the Display slide-out and a dialog keep focus inside, close with Escape and give focus back; reflow at 320 px
// and at 175% text; forced colours (Windows High Contrast) keep focus visible; reduced motion stops movement; live
// regions; labels and errors tied to their fields. Prints one line per finding and a summary; writes a11y.json.
import { chromium } from "playwright";
import fs from "fs";

const base = process.env.BASE || "http://127.0.0.1:18796";
const password = fs.readFileSync(process.env.PASSWORD_FILE, "utf8").trim();
const AXE = fs.readFileSync(process.env.AXE || "/tmp/a/node_modules/axe-core/axe.min.js", "utf8");
const pages = (process.env.PAGES || "").split(",").filter(Boolean);
const findings = [];
const add = (page, area, rule, detail, count = 1) => findings.push({ page, area, rule, detail: String(detail).slice(0, 300), count });

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1280, height: 860 }, bypassCSP: true });  // only so axe can be injected
const page = await ctx.newPage();
await page.goto(`${base}/login.html`);
await page.locator("#password").fill(password);
await page.locator("#password").press("Enter");
await page.waitForURL((u) => !u.pathname.endsWith("login.html"), { timeout: 15000 }).catch(() => {});

async function settle() {
  await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
  // Content drawn after the first answer: wait until nothing says it is busy, then a moment more.
  await page.waitForFunction(() => !document.querySelector("[aria-busy=true]"), null, { timeout: 8000 }).catch(() => {});
  await page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(900);
}

async function axe(name, mode) {
  await page.addScriptTag({ content: AXE });
  const r = await page.evaluate(async () => {
    const res = await window.axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"] },
      resultTypes: ["violations"] });
    return res.violations.map((v) => ({ id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length,
      where: v.nodes.slice(0, 3).map((n) => n.target.join(" ")).join(" | ") }));
  });
  for (const v of r) add(name, `axe ${mode}`, v.id, `${v.impact}: ${v.help} (${v.where})`, v.nodes);
}

async function structure(name) {
  const s = await page.evaluate(() => {
    const vis = (e) => !!(e.offsetParent || e.getClientRects().length);
    const hs = [...document.querySelectorAll("h1,h2,h3,h4,h5,h6")].filter(vis).map((h) => Number(h.tagName[1]));
    let skipped = null;
    for (let i = 1; i < hs.length; i++) if (hs[i] > hs[i - 1] + 1) { skipped = `h${hs[i - 1]} then h${hs[i]}`; break; }
    const focusable = [...document.querySelectorAll("a[href],button,input,select,textarea,[tabindex]")].filter((e) => e.tabIndex >= 0 && !e.disabled && vis(e));
    const unlabelled = [...document.querySelectorAll("input,select,textarea")].filter((e) => vis(e) && e.type !== "hidden" && e.type !== "file"
      && !(e.labels && e.labels.length) && !e.getAttribute("aria-label") && !e.getAttribute("aria-labelledby")).map((e) => e.id || e.name || e.outerHTML.slice(0, 60));
    const iconOnly = [...document.querySelectorAll("button,a[href]")].filter((b) => vis(b) && !b.textContent.trim() && !b.getAttribute("aria-label")
      && !b.getAttribute("aria-labelledby") && !b.getAttribute("title")).map((b) => b.outerHTML.slice(0, 80));
    const small = [...document.querySelectorAll("button,a.btn,input[type=checkbox],input[type=radio],select")].filter(vis).filter((b) => {
      const r = b.getBoundingClientRect(); return r.width > 0 && (r.width < 24 || r.height < 24);
    }).map((b) => (b.getAttribute("aria-label") || b.textContent.trim() || b.id || b.tagName).slice(0, 40));
    return { h1: hs.filter((h) => h === 1).length, skipped, header: !!document.querySelector("header, [role=banner]"),
      nav: !!document.querySelector("nav, [role=navigation]"), main: !!document.querySelector("main, [role=main]"),
      firstSkip: focusable[0]?.classList.contains("skip-link") || /skip to main/i.test(focusable[0]?.textContent || ""),
      title: document.title, live: !!document.querySelector("[aria-live], [role=status], [role=alert]"), unlabelled, iconOnly, small,
      lang: document.documentElement.lang };
  });
  if (s.h1 !== 1) add(name, "structure", "one-h1", `${s.h1} visible h1`);
  if (s.skipped) add(name, "structure", "heading-order", s.skipped);
  for (const k of ["header", "nav", "main"]) if (!s[k]) add(name, "structure", `landmark-${k}`, `no ${k}`);
  if (!s.firstSkip) add(name, "keyboard", "skip-link-first", "the first Tab stop is not Skip to main content");
  if (!/ · /.test(s.title)) add(name, "structure", "tab-title", `"${s.title}"`);
  if (!s.live) add(name, "screen reader", "live-region", "no polite live region");
  if (!/^en/.test(s.lang)) add(name, "screen reader", "lang", `lang="${s.lang}"`);
  if (s.unlabelled.length) add(name, "screen reader", "field-label", s.unlabelled.join(", "), s.unlabelled.length);
  if (s.iconOnly.length) add(name, "screen reader", "icon-button-name", s.iconOnly.join(" | "), s.iconOnly.length);
  if (s.small.length) add(name, "size", "target-24px", s.small.slice(0, 6).join(", "), s.small.length);
}

async function keyboard(name) {
  await page.evaluate(() => { document.activeElement?.blur(); window.scrollTo(0, 0); });
  await page.mouse.click(1, 1).catch(() => {});
  const seen = [];
  let stuck = 0, invisible = [], hidden = [], covered = [];
  for (let i = 0; i < 45; i++) {
    await page.keyboard.press("Tab");
    const f = await page.evaluate(() => {
      const e = document.activeElement;
      if (!e || e === document.body) return null;
      const cs = getComputedStyle(e);
      const r = e.getBoundingClientRect();
      // The ring may be on the element, on the card around it, or on its cover (a whole-card link), or an SVG stroke.
      const shows = (n) => { const s = getComputedStyle(n); return (s.outlineStyle !== "none" && parseFloat(s.outlineWidth) >= 2) ||
        (s.boxShadow && s.boxShadow !== "none") || (n instanceof SVGElement && s.stroke !== "none" && parseFloat(s.strokeWidth) >= 2); };
      const card = e.closest(".media-card, .network-card, .collection-card, .card, .row, li");
      const near = [e, e.parentElement, e.parentElement?.parentElement, ...(card ? [card, ...card.querySelectorAll(".cover, img")] : [])].filter(Boolean);
      const ring = near.some(shows);
      const header = document.querySelector(".site-header");
      const hb = header ? header.getBoundingClientRect() : null;
      const sticky = header && getComputedStyle(header).position === "sticky";
      const top = document.elementFromPoint(Math.max(0, Math.min(innerWidth - 1, r.left + r.width / 2)), Math.max(0, Math.min(innerHeight - 1, r.top + Math.min(r.height / 2, 10))));
      const all = [...document.querySelectorAll("*")];
      return { key: (e.id || "") + "|" + e.tagName + "|" + (e.getAttribute("aria-label") || e.textContent || e.name || "").trim().slice(0, 30) + "#" + all.indexOf(e),
        ring, size: r.width * r.height, inside: e.closest("dialog,[role=dialog]") ? 1 : 0,
        covered: !!(sticky && hb && r.top < hb.bottom - 2 && r.bottom > 0 && !header.contains(e) && top && header.contains(top)) };
    });
    if (!f) continue;
    if (seen.length && seen[seen.length - 1] === f.key) { if (++stuck > 2) break; } else stuck = 0;
    seen.push(f.key);
    if (!f.ring) invisible.push(f.key);
    if (f.size === 0) hidden.push(f.key);
    if (f.covered) covered.push(f.key);
  }
  if (stuck > 2) add(name, "keyboard", "trap", `focus stays on ${seen[seen.length - 1]}`);
  if (invisible.length) add(name, "keyboard", "focus-visible", [...new Set(invisible)].slice(0, 5).join(" ; "), new Set(invisible).size);
  if (hidden.length) add(name, "keyboard", "focus-on-hidden", [...new Set(hidden)].slice(0, 5).join(" ; "), new Set(hidden).size);
  if (covered.length) add(name, "keyboard", "focus-not-obscured", [...new Set(covered)].slice(0, 5).join(" ; "), new Set(covered).size);
}

async function reflow(name) {
  await page.setViewportSize({ width: 320, height: 700 });
  await page.waitForTimeout(300);
  const over = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
  if (over > 1) add(name, "reflow", "320px", `${over}px sideways scroll`);
  await page.setViewportSize({ width: 1280, height: 860 });
  await page.evaluate(() => document.documentElement.classList.add("pref-text-175"));
  await page.waitForTimeout(200);
  const over2 = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
  if (over2 > 1) add(name, "reflow", "text-175", `${over2}px sideways scroll at 175% text`);
  await page.evaluate(() => document.documentElement.classList.remove("pref-text-175"));
}

const ALL = pages.length ? pages : fs.readdirSync(process.env.WEB || "/web").filter((f) => f.endsWith(".html") &&
  !["login.html", "setup.html", "offline.html", "wanted-moved.html", "discover-trending.html", "wanted.html", "wanted-quality.html"].includes(f))
  // A plug-in's own page with a plug-in: the example Styles plug-in, just updated, shows What is new (DASH-393).
  .concat(["settings-plugin.html?id=styles", "settings-plugin.html?id=watch-stats", "settings-plugin.html?id=notifications",
    "settings-plugin.html?id=audio-description-sources", "settings-plugin.html?id=audio-description-tracks",
    "settings-plugin.html?id=jellystat", "settings-plugin.html?id=tdarr", "settings-plugin.html?id=direct-play",
    "settings-plugin.html?id=jellyfin", "settings-plugin.html?id=picture-shrinker", "settings-plugin.html?id=on-demand", "settings-plugin.html?id=library-cleanup"]);  // built from a zip, with Jellyfin libraries, and Put back on each row (plug-in API 1.15, DASH-406)  // a PNG logo and a schedule setting (plug-in API 1.14)  // Direct play (DASH-425)  // app plug-ins (DASH-411)  // links on rows and a file-only upload (DASH-410)  // read-only tables (DASH-402), settings in sections with secrets (DASH-401)
for (const name of ALL) {
  try {
    await page.goto(`${base}/${name}`);
    await settle();
    if (new URL(page.url()).pathname !== `/${name.split("?")[0]}`) { add(name, "page", "redirects", page.url()); continue; }
    await axe(name, "light");
    await structure(name);
    await keyboard(name);
    await reflow(name);
    // Each scheme is scanned as the page is first seen, as the light scan is: from the top, nothing focused. The
    // keyboard walk scrolls, and a row left partly under the sticky header measured as a small target (13 November
    // 2026: wanted-films.html, and the index.html target-size flake).
    const fromTop = () => page.evaluate(() => { document.activeElement?.blur(); window.scrollTo(0, 0); });
    await page.evaluate(() => document.documentElement.setAttribute("data-theme", "dark"));
    await fromTop();
    await page.waitForTimeout(150);
    await axe(name, "dark");
    await page.evaluate(() => { document.documentElement.removeAttribute("data-theme"); document.documentElement.classList.add("pref-contrast"); });
    await fromTop();
    await page.waitForTimeout(150);
    await axe(name, "high contrast");
    console.log(`checked ${name}`);
  } catch (e) { add(name, "page", "error", e.message.split("\n")[0]); }
}

// Why is this here? open on Other services (DASH-557), in Light, Dark and High contrast.
if (!pages.length || pages.some((p) => p.includes("apps-services"))) {
  try {
    await page.goto(`${base}/apps-services.html`);
    await settle();
    await page.locator("#why-here").click();
    await page.waitForFunction(() => document.querySelector("#side-panel .rows"), null, { timeout: 8000 }).catch(() => {});
    await page.waitForTimeout(500);
    const name = "apps-services.html, Why is this here?";
    await axe(name, "light");
    await structure(name);
    await page.evaluate(() => document.documentElement.setAttribute("data-theme", "dark"));
    await page.waitForTimeout(150);
    await axe(name, "dark");
    await page.evaluate(() => { document.documentElement.removeAttribute("data-theme"); document.documentElement.classList.add("pref-contrast"); });
    await page.waitForTimeout(150);
    await axe(name, "high contrast");
    await page.evaluate(() => document.documentElement.classList.remove("pref-contrast"));
    console.log("checked Why is this here?");
  } catch (e) { add("apps-services.html, Why is this here?", "page", "error", e.message.split("\n")[0]); }
}

// Catalogue sources with the Stallboard tick on, and the Stallboard tab it adds (DASH-563), in Light, Dark and High contrast.
if (!pages.length || pages.some((p) => p.includes("settings-plugins-catalogue"))) {
  const scan = async (name) => {
    await axe(name, "light");
    await structure(name);
    await page.evaluate(() => document.documentElement.setAttribute("data-theme", "dark"));
    await page.waitForTimeout(150);
    await axe(name, "dark");
    await page.evaluate(() => { document.documentElement.removeAttribute("data-theme"); document.documentElement.classList.add("pref-contrast"); });
    await page.waitForTimeout(150);
    await axe(name, "high contrast");
    await page.evaluate(() => document.documentElement.classList.remove("pref-contrast"));
  };
  try {
    await page.goto(`${base}/settings-plugins-catalogue.html`);
    await settle();
    await page.evaluate(() => api("/api/plugins/catalogues", { method: "POST", body: { action: "builtin", id: "stallboard", on: true } }));
    await page.goto(`${base}/settings-plugins-catalogue.html`);
    await settle();
    await page.getByRole("tab", { name: "Catalogue sources", exact: true }).click();
    await page.waitForTimeout(300);
    await scan("settings-plugins-catalogue.html, Catalogue sources with Stallboard on");
    await page.getByRole("tab", { name: "Stallboard", exact: true }).click();
    await page.waitForTimeout(300);
    await scan("settings-plugins-catalogue.html, the Stallboard tab");
    await page.evaluate(() => api("/api/plugins/catalogues", { method: "POST", body: { action: "builtin", id: "stallboard", on: false } }));
    console.log("checked the Stallboard catalogue");
  } catch (e) { add("settings-plugins-catalogue.html, Stallboard", "page", "error", e.message.split("\n")[0]); }
}

// A custom card (DASH-555): its panel with the chosen fields and the fields to choose from, and the dashboard with the card
// on it, in Light, Dark and High contrast.
if (!pages.length || pages.some((p) => p.includes("apps-services"))) {
  try {
    await page.goto(`${base}/apps-services.html`);
    await settle();
    await page.locator("[data-json-card]").first().click();
    await page.waitForSelector("#jc-ask", { timeout: 8000 });
    await page.locator("#jc-ask").click();
    await page.waitForSelector("#jc-filter", { timeout: 8000 }).catch(() => {});
    await page.waitForTimeout(500);
    await page.evaluate(() => window.scrollTo(0, 0));  // Playwright scrolled the page to reach the row; axe is run from the top as for the other panels
    await page.waitForTimeout(200);
    const name = "apps-services.html, custom card";
    await axe(name, "light");
    await structure(name);
    await page.evaluate(() => document.documentElement.setAttribute("data-theme", "dark"));
    await page.waitForTimeout(150);
    await axe(name, "dark");
    await page.evaluate(() => { document.documentElement.removeAttribute("data-theme"); document.documentElement.classList.add("pref-contrast"); });
    await page.waitForTimeout(150);
    await axe(name, "high contrast");
    await page.evaluate(() => document.documentElement.classList.remove("pref-contrast"));
    console.log("checked the custom card panel");
  } catch (e) { add("apps-services.html, custom card", "page", "error", e.message.split("\n")[0]); }
}
if (!pages.length || pages.some((p) => p.includes("dashboard"))) {
  try {
    await page.goto(`${base}/dashboard.html`);
    await settle();
    await page.evaluate(async () => {
      const cards = (await api("/api/json-cards")).cards;
      const cfg = await api("/api/config/general", { method: "PUT", body: { dashboard: { layout: "glance", cards: [{ id: `json:${cards[0].id}`, size: "half" }, { id: "health", size: "half" }] } } });
      dash = cfg.dashboard; draw();
    });
    await page.waitForSelector('[data-card^="json:"] dl', { timeout: 8000 });
    await page.waitForTimeout(500);
    const name = "dashboard.html, custom card";
    await axe(name, "light");
    await structure(name);
    await page.evaluate(() => document.documentElement.setAttribute("data-theme", "dark"));
    await page.waitForTimeout(150);
    await axe(name, "dark");
    await page.evaluate(() => { document.documentElement.removeAttribute("data-theme"); document.documentElement.classList.add("pref-contrast"); });
    await page.waitForTimeout(150);
    await axe(name, "high contrast");
    await page.evaluate(() => document.documentElement.classList.remove("pref-contrast"));
    await page.evaluate(async () => { await api("/api/config/general", { method: "PUT", body: { dashboard: { layout: "glance", cards: null } } }); });
    console.log("checked the custom card on the dashboard");
  } catch (e) { add("dashboard.html, custom card", "page", "error", e.message.split("\n")[0]); }
}

// The media server plug-in (DASH-565): Jellyfin's own plug-in page, with its Media server card and the state chip with its
// shape, and the catalogue's Media servers tab, in Light, Dark and High contrast.
if (!pages.length || pages.some((p) => p.includes("settings-plugin"))) {
  const scan = async (name) => {
    await axe(name, "light");
    await structure(name);
    await page.evaluate(() => document.documentElement.setAttribute("data-theme", "dark"));
    await page.waitForTimeout(150);
    await axe(name, "dark");
    await page.evaluate(() => { document.documentElement.removeAttribute("data-theme"); document.documentElement.classList.add("pref-contrast"); });
    await page.waitForTimeout(150);
    await axe(name, "high contrast");
    await page.evaluate(() => document.documentElement.classList.remove("pref-contrast"));
  };
  try {
    await page.goto(`${base}/settings-plugin.html?id=jellyfin`);
    await settle();
    await scan("settings-plugin.html, Jellyfin as the media server");
    await page.goto(`${base}/settings-plugins-catalogue.html`);
    await settle();
    await page.getByRole("tab", { name: "Media servers", exact: true }).click();
    await page.waitForTimeout(300);
    await scan("settings-plugins-catalogue.html, the Media servers tab");
    console.log("checked the media server plug-in");
  } catch (e) { add("settings-plugin.html, Jellyfin as the media server", "page", "error", e.message.split("\n")[0]); }
}

// Alerts, The server itself (DASH-556): the host alerts' switches, limits and times, with More settings on, in Light, Dark and High contrast.
if (!pages.length || pages.includes("settings-general-alerts.html")) {
  const name = "settings-general-alerts.html, The server itself";
  try {
    await page.goto(`${base}/settings-general-alerts.html`);
    await settle();
    await page.evaluate(() => api("/api/config/general", { method: "PUT", body: { settings_advanced: true } }));
    await page.goto(`${base}/settings-general-alerts.html`);
    await settle();
    await page.getByRole("tab", { name: "The server itself", exact: true }).click();
    await page.waitForTimeout(300);
    await axe(name, "light");
    await structure(name);
    await keyboard(name);
    await page.evaluate(() => document.documentElement.setAttribute("data-theme", "dark"));
    await page.waitForTimeout(150);
    await axe(name, "dark");
    await page.evaluate(() => { document.documentElement.removeAttribute("data-theme"); document.documentElement.classList.add("pref-contrast"); });
    await page.waitForTimeout(150);
    await axe(name, "high contrast");
    await page.evaluate(() => document.documentElement.classList.remove("pref-contrast"));
    await page.evaluate(() => api("/api/config/general", { method: "PUT", body: { settings_advanced: false } }));
    console.log("checked the host alerts");
  } catch (e) { add(name, "page", "error", e.message.split("\n")[0]); }
}

// Search with its results and More filters open (DASH-301): the filters only show once something is searched for.
if (!pages.length || pages.includes("search.html")) {
  const name = "search.html?q=harbour, More filters";
  try {
    await page.goto(`${base}/search.html?q=harbour`);
    await settle();
    await page.waitForSelector("#sf-more", { timeout: 10000 });
    if ((await page.getAttribute("#sf-more", "aria-expanded")) !== "true") await page.click("#sf-more");
    await page.waitForTimeout(1500);  // Reelix's lookups arrive
    await axe(name, "light");
    await keyboard(name);
    await reflow(name);
    await page.evaluate(() => { document.activeElement?.blur(); window.scrollTo(0, 0); document.documentElement.setAttribute("data-theme", "dark"); });
    await page.waitForTimeout(150);
    await axe(name, "dark");
    await page.evaluate(() => { document.documentElement.removeAttribute("data-theme"); document.documentElement.classList.add("pref-contrast"); });
    await page.waitForTimeout(150);
    await axe(name, "high contrast");
    await page.evaluate(() => document.documentElement.classList.remove("pref-contrast"));
    console.log(`checked ${name}`);
  } catch (e) { add(name, "page", "error", e.message.split("\n")[0]); }
}

// A plug-in update (plug-in API 1.14, DASH-424): the warning with What is new and how it is kept safe, then the
// update's steps dialog with its result, each in Light, Dark and High contrast, with its structure.
if (!pages.length || pages.some((p) => p.includes("picture-shrinker"))) {
  const scan = async (name) => {
    await axe(name, "light");
    await structure(name);
    await page.evaluate(() => document.documentElement.setAttribute("data-theme", "dark"));
    await page.waitForTimeout(150);
    await axe(name, "dark");
    await page.evaluate(() => { document.documentElement.removeAttribute("data-theme"); document.documentElement.classList.add("pref-contrast"); });
    await page.waitForTimeout(150);
    await axe(name, "high contrast");
    await page.evaluate(() => document.documentElement.classList.remove("pref-contrast"));
  };
  try {
    await page.goto(`${base}/settings-plugin.html?id=picture-shrinker`);
    await settle();
    const versions = page.getByRole("tab", { name: "Versions", exact: true });  // the topic tabs show one part at a time
    if (await versions.count()) { await versions.click(); await page.waitForTimeout(300); }
    await page.getByRole("button", { name: "Update to 1.1.0…" }).first().click();
    const warn = page.getByRole("dialog", { name: "Update Picture shrinker to 1.1.0?" });
    await warn.waitFor({ timeout: 8000 });
    await page.waitForTimeout(400);
    await scan("settings-plugin.html?id=picture-shrinker, Update warning");
    await page.locator("#pl-install-password").fill(password);
    await warn.getByRole("button", { name: "Update Picture shrinker", exact: true }).click();
    const run = page.getByRole("dialog", { name: "Updating Picture shrinker to 1.1.0" });
    await run.locator(".notice__title").waitFor({ timeout: 20000 });
    await scan("settings-plugin.html?id=picture-shrinker, Update steps");
    await run.getByRole("button", { name: "Done" }).click();
    await settle();
    await scan("settings-plugin.html?id=picture-shrinker, What is new after the update");
    console.log("checked the plug-in update");
  } catch (e) { add("settings-plugin.html?id=picture-shrinker, Update", "page", "error", e.message.split("\n")[0]); }
}

// Check for updates and What is new (DASH-462): Ready to update after a check, and the What is new slide-out with
// every waiting update's notes, in Light, Dark and High contrast, with its structure.
if (!pages.length || pages.some((p) => p.includes("settings-updates"))) {
  const scan = async (name) => {
    await axe(name, "light");
    await structure(name);
    await page.evaluate(() => document.documentElement.setAttribute("data-theme", "dark"));
    await page.waitForTimeout(150);
    await axe(name, "dark");
    await page.evaluate(() => { document.documentElement.removeAttribute("data-theme"); document.documentElement.classList.add("pref-contrast"); });
    await page.waitForTimeout(150);
    await axe(name, "high contrast");
    await page.evaluate(() => document.documentElement.classList.remove("pref-contrast"));
  };
  try {
    await page.goto(`${base}/settings-updates.html`);
    await settle();
    await page.locator("#check-updates-now").click();
    await page.locator("#up-list-summary", { hasText: "Checked at" }).waitFor({ timeout: 30000 });
    await scan("settings-updates.html, after Check for updates");
    await page.locator("#whats-new").click();
    await page.locator("#side-panel section.release-notes").first().waitFor({ timeout: 15000 });
    await page.waitForTimeout(300);
    await scan("settings-updates.html, What is new");
    await page.keyboard.press("Escape");
    // About (DASH-408): the accessibility and lean sections, in a tab that is hidden until it is chosen.
    await page.goto(`${base}/settings-updates.html`);
    await settle();
    await page.locator('[role="tab"]', { hasText: "About" }).click();
    await page.waitForTimeout(300);
    await scan("settings-updates.html, About");
    console.log("checked Check for updates, What is new and About");
  } catch (e) { add("settings-updates.html, What is new", "page", "error", e.message.split("\n")[0]); }
}

// A download that needs attention (DASH-496): its slide-out with what is wrong, the actions and the folder, and the
// question before deleting, in Light, Dark and High contrast, with its structure. Nothing is deleted.
if (!pages.length || pages.some((p) => p.startsWith("downloads.html"))) {
  const scan = async (name) => {
    await axe(name, "light");
    await structure(name);
    await page.evaluate(() => document.documentElement.setAttribute("data-theme", "dark"));
    await page.waitForTimeout(150);
    await axe(name, "dark");
    await page.evaluate(() => { document.documentElement.removeAttribute("data-theme"); document.documentElement.classList.add("pref-contrast"); });
    await page.waitForTimeout(150);
    await axe(name, "high contrast");
    await page.evaluate(() => document.documentElement.classList.remove("pref-contrast"));
  };
  try {
    await page.goto(`${base}/downloads.html`);
    await settle();
    await page.locator("#queue button", { hasText: "Sample Science Weekly" }).click();
    await page.locator("#attention .action-list").first().waitFor({ timeout: 15000 });
    await page.waitForTimeout(300);
    await scan("downloads.html, a download that needs attention");
    await page.locator("#attention [data-action=delete]").click();
    await page.locator("dialog[open]").waitFor({ timeout: 5000 });
    await page.waitForTimeout(300);
    await scan("downloads.html, before deleting a download's files");
    await page.keyboard.press("Escape");
    await page.keyboard.press("Escape");
    console.log("checked a download that needs attention");
  } catch (e) { add("downloads.html, a download that needs attention", "page", "error", e.message.split("\n")[0]); }
}

// Restart where it is needed (DASH-470): Restart Jellyfin on System, Overview, Settings, Updates and Settings, Apps,
// Jellyfin, while Jellyfin says Restart needed (made up with page routes), and while it works, in Light, Dark and
// High contrast, with its structure. Nothing is restarted: the restart itself is a made-up answer that never ends.
// Plug-in updates (owner, 26 November 2026): the list, after Check for updates now, and What is new.
if (!pages.length || pages.some((p) => p.includes("settings-updates-plugins") || p.includes("settings-plugins"))) {
  const scanP = async (name) => {
    await axe(name, "light");
    await structure(name);
    await page.evaluate(() => document.documentElement.setAttribute("data-theme", "dark"));
    await page.waitForTimeout(150);
    await axe(name, "dark");
    await page.evaluate(() => { document.documentElement.removeAttribute("data-theme"); document.documentElement.classList.add("pref-contrast"); });
    await page.waitForTimeout(150);
    await axe(name, "high contrast");
    await page.evaluate(() => document.documentElement.classList.remove("pref-contrast"));
  };
  try {
    for (const name of ["settings-updates-plugins.html", "settings-plugins.html"]) {
      await page.goto(`${base}/${name}`);
      await settle();
      await page.locator("#plu-check").click();
      await page.locator("#plu-result", { hasText: /Read \d+ catalogue|Try again in/ }).waitFor({ timeout: 30000 });
      await scanP(`${name}, after Check for updates now`);
    }
    await page.locator("#plugin-updates button", { hasText: "What is new" }).first().click();
    await page.locator("#side-panel").waitFor({ timeout: 15000 });
    await page.waitForTimeout(800);
    await scanP("settings-plugins.html, What is new in a plug-in");
    await page.keyboard.press("Escape");
    console.log("checked the plug-in update list");
  } catch (e) { add("settings-updates-plugins.html", "page", "error", e.message.split("\n")[0]); }
}

if (!pages.length || pages.some((p) => /^system\.html|settings-updates|settings-jellyfin/.test(p))) {
  const scan = async (name) => {
    await axe(name, "light");
    await structure(name);
    await page.evaluate(() => document.documentElement.setAttribute("data-theme", "dark"));
    await page.waitForTimeout(150);
    await axe(name, "dark");
    await page.evaluate(() => { document.documentElement.removeAttribute("data-theme"); document.documentElement.classList.add("pref-contrast"); });
    await page.waitForTimeout(150);
    await axe(name, "high contrast");
    await page.evaluate(() => document.documentElement.classList.remove("pref-contrast"));
  };
  const needed = (extra) => async (route) => {
    if (route.request().method() !== "GET") return route.continue();
    const b = await (await route.fetch()).json().catch(() => ({}));
    await route.fulfill({ contentType: "application/json", body: JSON.stringify({ ...b, ...extra(b), restart: true, can_restart: true }) });
  };
  const overview = needed((b) => ({ configured: true, name: "Jellyfin", version: b.version || "10.11.2", playing: b.playing || [], added: b.added || [] }));
  const updates = needed((b) => ({ connected: true, count: b.count || 1 }));
  const plugins = needed(() => ({}));
  const away = (route) => route.request().method() === "POST" ? route.fulfill({ contentType: "application/json", body: "{}" })
    : route.fulfill({ contentType: "application/json", body: JSON.stringify({ answering: false, restart: null }) });
  try {
    await page.route(/\/api\/jellyfin(\?fresh=1)?$/, overview);
    await page.route(/\/api\/updates\/jellyfin$/, updates);
    await page.route(/\/api\/jellyfin\/plugins$/, plugins);
    await page.route(/\/api\/jellyfin\/restart$/, away);
    await page.goto(`${base}/system.html`);
    await settle();
    await scan("system.html, Restart Jellyfin");
    await page.locator("#jellyfin-panel [data-restart] button").click();
    await page.getByRole("dialog").getByRole("button", { name: "Restart Jellyfin", exact: true }).click();
    await page.waitForTimeout(500);
    await scan("system.html, Restart Jellyfin while it works");
    await page.goto(`${base}/settings-updates.html`);
    await settle();
    await page.locator("[data-key=jellyfin-plugins] [data-restart]").waitFor({ timeout: 10000 });
    await scan("settings-updates.html, Restart Jellyfin");
    await page.goto(`${base}/settings-jellyfin.html`);
    await settle();
    await scan("settings-jellyfin.html, Restart Jellyfin");
    console.log("checked Restart where it is needed");
  } catch (e) { add("Restart where it is needed", "page", "error", e.message.split("\n")[0]); }
  await page.unroute(/\/api\/jellyfin(\?fresh=1)?$/, overview);
  await page.unroute(/\/api\/updates\/jellyfin$/, updates);
  await page.unroute(/\/api\/jellyfin\/plugins$/, plugins);
  await page.unroute(/\/api\/jellyfin\/restart$/, away);
}

// Downloading without a VPN (DASH-440): the set-up's VPN step with Continue without a VPN chosen, and its warning,
// an alert dialog, in Light, Dark and High contrast; then Settings, Downloads, VPN with Remove the VPN's warning.
if (!pages.length || pages.some((p) => p.includes("install-apps") || p.includes("settings-downloads"))) {
  const themes = async (name) => {
    await axe(name, "light");
    await structure(name);
    await page.evaluate(() => document.documentElement.setAttribute("data-theme", "dark"));
    await page.waitForTimeout(150);
    await axe(name, "dark");
    await page.evaluate(() => { document.documentElement.removeAttribute("data-theme"); document.documentElement.classList.add("pref-contrast"); });
    await page.waitForTimeout(150);
    await axe(name, "high contrast");
    await page.evaluate(() => document.documentElement.classList.remove("pref-contrast"));
  };
  try {
    await page.goto(`${base}/install-apps.html?wizard=1`);
    await settle();
    const go = async (name) => { await page.getByRole("button", { name, exact: true }).last().click(); await page.waitForTimeout(900); };
    await go("Begin");
    const without = page.getByRole("radio", { name: /Continue without a VPN/ });
    for (let i = 0; i < 4 && !(await without.count()); i++) await go("Continue");
    await without.check();
    await themes("install-apps.html, VPN step without a VPN");
    await go("Continue");
    await page.locator("dialog[open][role=alertdialog]").waitFor({ timeout: 5000 });
    await page.waitForTimeout(300);
    await themes("install-apps.html, Continue without a VPN warning");
    await page.keyboard.press("Escape");
    await page.goto(`${base}/settings-downloads.html`);
    await settle();
    await page.locator("#dl-vpn-remove-pw").fill(password);
    await page.getByRole("button", { name: "Remove the VPN" }).click();
    await page.locator("dialog[open][role=alertdialog]").waitFor({ timeout: 5000 });
    await page.waitForTimeout(300);
    await themes("settings-downloads.html, Remove the VPN warning");
    await page.keyboard.press("Escape");
    console.log("checked the no-VPN warning");
  } catch (e) { add("install-apps.html / settings-downloads.html, no-VPN warning", "page", "error", e.message.split("\n")[0]); }
}

// Connect a cloud service (DASH-452): each step of the wizard, both ways to sign in, and Test connection's result,
// in Light, Dark and High contrast, with their structure. Stand-ins only; the phone is approved at the example
// server's stand-in on its port + 2.
if (!pages.length || pages.some((p) => p.includes("system-backup"))) {
  const themes = async (name) => {
    await axe(name, "light");
    await structure(name);
    await page.evaluate(() => document.documentElement.setAttribute("data-theme", "dark"));
    await page.waitForTimeout(150);
    await axe(name, "dark");
    await page.evaluate(() => { document.documentElement.removeAttribute("data-theme"); document.documentElement.classList.add("pref-contrast"); });
    await page.waitForTimeout(150);
    await axe(name, "high contrast");
    await page.evaluate(() => document.documentElement.classList.remove("pref-contrast"));
  };
  const foot = () => page.locator(".side-panel__foot .btn--primary").first().click();
  try {
    // Where backups go (several places, 26 November 2026): the list, a form in a slide-out, the wizard opened from a
    // service in Add a place, each step, and Test beside a place.
    await page.goto(`${base}/system-backup.html`);
    await settle();
    await page.locator("#place-on-main").waitFor();
    await themes("system-backup.html, Where backups go");
    await page.evaluate(() => { window.scrollTo(0, 0); document.querySelector("#place-add-smb").click(); });
    await page.locator("#place-smb").waitFor();
    await themes("Where backups go, add a network share");
    await page.keyboard.press("Escape");
    await page.waitForFunction(() => !document.querySelector(".side-panel"));
    await page.evaluate(() => { window.scrollTo(0, 0); document.querySelector("#place-add-drive").click(); });
    await page.locator("#cloud-way").waitFor();
    await page.locator("input[name=cloud-way][value=browser]").check();
    await page.locator("#cloud-open-signin").waitFor();
    await themes("Connect a cloud service, Google Drive, Complete in this browser");
    await page.locator("input[name=cloud-way][value=phone]").check();
    await page.locator(".qr-card").waitFor();
    await themes("Connect a cloud service, Google Drive, Complete on the phone");
    const code = (await page.locator(".device-code__value").innerText()).trim();
    await page.request.get(base.replace(/:(\d+)$/, (_, p) => `:${Number(p) + 2}`) + `/device/approve?user_code=${encodeURIComponent(code)}`);
    await page.locator("#cloud-folder-list .check").first().waitFor({ timeout: 20000 });
    await themes("Connect a cloud service, choose the folder");
    await foot();
    await page.locator("#cloud-test-box .notice").waitFor();
    await themes("Connect a cloud service, test");
    await foot();
    await page.locator("#cloud-save").waitFor();
    await themes("Connect a cloud service, check and save");
    await page.locator("#cloud-password").fill(password);
    await foot();
    await page.locator(".side-panel").waitFor({ state: "detached" });
    await page.locator("[id^=place-test-]").last().click();
    await page.waitForFunction(() => ![...document.querySelectorAll("[id^=place-test-]")].some((b) => b.disabled));
    await themes("system-backup.html, Test connection result");
    // Opened without scrolling the page, so nothing on the page behind sits half under the sticky header.
    await page.evaluate(() => { window.scrollTo(0, 0); document.querySelector("#place-add-webdav").click(); });
    await page.locator("#cloud-details").waitFor();
    await themes("Connect a cloud service, Nextcloud details");
    await page.keyboard.press("Escape");
    console.log("checked Where backups go and Connect a cloud service");
  } catch (e) { add("system-backup.html, Where backups go", "page", "error", e.message.split("\n")[0]); }
  // Full backups with Checked and Restore, the restore dialog (also with an error under a field), the restore while
  // it runs and when it ends (DASH-381, DASH-387); Reelix's backup settings and the folder choice (DASH-385, DASH-386).
  // The example server restores and moves nothing.
  try {
    await page.goto(`${base}/system-backup.html`);
    await settle();
    await page.locator("#full-list li[data-key]").first().waitFor();
    await page.locator("#full-list").scrollIntoViewIfNeeded();
    await themes("system-backup.html, full backups with Checked and Restore");
    await page.locator("#full-list li[data-key] button").nth(1).click();
    await page.locator("#restore-full-pw").waitFor();
    await themes("Restore a full backup, the dialog");
    await page.locator("#restore-full-pw").fill("not the backup password");
    await page.locator("#restore-full-mine").fill(password);
    await page.locator("dialog .dialog__foot .btn--danger").click();
    await page.locator("#restore-full-pw[aria-invalid=true]").waitFor();
    await themes("Restore a full backup, a wrong backup password");
    await page.locator("#restore-full-pw").fill("made-up backup");
    await page.locator("#restore-full-mine").fill(password);
    await page.locator("dialog .dialog__foot .btn--danger").click();
    await page.locator("#full-restore-state .notice").waitFor();
    await axe("Restore a full backup, restoring", "light");
    await page.locator("#full-restore-state .notice[data-tone=success]").waitFor({ timeout: 20000 });
    await themes("Restore a full backup, restored");
    await page.getByRole("button", { name: "Show Reelix's backups" }).click();
    await page.locator("#rs-password").fill("made-up");
    await page.keyboard.press("Enter");
    await page.locator("#rs-place").waitFor();
    await page.locator("#rs-every").selectOption("14");
    await page.locator("#rs-every + .saved-note:not([hidden])").waitFor();
    await themes("Reelix's backups, the settings with a saved note");
    await page.locator("#rs-place").selectOption("media");
    await page.locator("[data-restart-notice]").waitFor();
    await themes("Reelix's backups, the new folder waits for a restart");
    await page.locator("section[aria-labelledby=rs-backups-h] li.row button").first().click();
    await page.getByRole("dialog", { name: "Restore this Reelix backup?" }).waitFor();
    await themes("Reelix's backups, the restore dialog");
    await page.keyboard.press("Escape");
    await page.evaluate(async () => {
      await api("/api/reelix/admin/system/backup-place", { method: "POST", body: { password: "made-up", place: "settings" } });
      await api("/api/reelix/admin/system/backup-settings", { method: "POST", body: { password: "made-up", every: 7, keep: 5 } });
    });
    console.log("checked full backups and Reelix's backups");
  } catch (e) { add("system-backup.html, full backups and Reelix's backups", "page", "error", e.message.split("\n")[0]); }
}

// DASH-512: the sign-in page in each state it can be in: the two-step code after the password, a single sign-on button
// beside the password, and single sign-on alone. Set up through the settings API (the example server takes 123456 as
// the right code), looked at as someone who has not signed in, then put back.
try {
  await page.goto(`${base}/settings-security-signin.html`);
  await settle();
  const call = (path, body) => page.evaluate(([p, b]) => api(p, { method: "POST", body: b }), [path, body]);
  await call("/api/security/totp/start", { password });
  await call("/api/security/totp/confirm", { code: "123456" });
  const anon = await (await browser.newContext({ viewport: { width: 1280, height: 860 }, bypassCSP: true })).newPage();
  const axeOn = async (name, mode) => {
    await anon.addScriptTag({ content: AXE });
    const r = await anon.evaluate(async () => (await window.axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"] }, resultTypes: ["violations"] }))
      .violations.map((v) => ({ id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length, where: v.nodes.slice(0, 3).map((n) => n.target.join(" ")).join(" | ") })));
    for (const v of r) add(name, `axe ${mode}`, v.id, `${v.impact}: ${v.help} (${v.where})`, v.nodes);
  };
  for (const scheme of ["light", "dark"]) {
    await anon.emulateMedia({ colorScheme: scheme });
    await anon.goto(`${base}/login.html`);
    await anon.locator("#password").fill(password);
    await anon.locator("#password").press("Enter");
    await anon.locator("#code").waitFor({ state: "visible", timeout: 8000 });
    await anon.waitForTimeout(400);
    if (!(await anon.evaluate(() => document.activeElement?.id === "code"))) add("login.html, the two-step code", "keyboard", "focus-moves", "focus did not move to the code field");
    if (!(await anon.evaluate(() => /Password accepted/.test(document.getElementById("announcer")?.textContent || "")))) add("login.html, the two-step code", "screen reader", "live-region", "the step is not announced");
    await axeOn("login.html, the two-step code", scheme);
    await anon.locator("#code").fill("000000");
    await anon.locator("#code").press("Enter");
    await anon.waitForTimeout(700);
    if (!(await anon.evaluate(() => { const e = document.getElementById("code"); return e?.getAttribute("aria-invalid") === "true" && /code-error/.test(e.getAttribute("aria-describedby") || "") && document.activeElement === e; })))
      add("login.html, the two-step code", "screen reader", "error-tied-to-field", "a wrong code is not tied to its field with focus on it");
    await axeOn("login.html, the two-step code, with an error", scheme);
  }
  await call("/api/security/totp/off", { password });
  await call("/api/security/oidc/enable", { password, enabled: true });
  for (const [label, off] of [["a single sign-on button", false], ["single sign-on alone", true]]) {
    if (off) await call("/api/security/password-login", { password, allowed: false });
    await anon.emulateMedia({ colorScheme: "light" });
    await anon.goto(`${base}/login.html`);
    await anon.waitForTimeout(900);
    if (!(await anon.getByRole("link", { name: /Sign in with Authentik/ }).count())) add(`login.html, ${label}`, "page", "sso-button", "no sign-in button for the provider");
    if (off && (await anon.locator("#login-form").isVisible())) add(`login.html, ${label}`, "page", "password-form", "the password form is shown while the password is deactivated");
    await axeOn(`login.html, ${label}`, "light");
    await anon.emulateMedia({ colorScheme: "dark" });
    await anon.reload();
    await anon.waitForTimeout(700);
    await axeOn(`login.html, ${label}`, "dark");
  }
  await call("/api/security/oidc/enable", { password, enabled: false });  // also allows the password again
  await anon.context().close();
  console.log("checked the sign-in page's states");
} catch (e) { add("login.html, its states", "page", "error", e.message.split("\n")[0]); }

// Slide-out and dialog behaviour (once; every page uses the same code): Display, then a confirm dialog.
await page.goto(`${base}/settings-general.html`);
await settle();
const display = page.getByRole("button", { name: /Display/ }).first();
await display.focus();
await page.keyboard.press("Enter");
await page.waitForTimeout(400);
const inPanel = async () => page.evaluate(() => !!document.activeElement?.closest("#side-panel, .side-panel, [role=dialog]"));
if (!(await inPanel())) add("Display slide-out", "keyboard", "focus-moves-in", "focus did not move into the slide-out");
let left = false;
for (let i = 0; i < 30; i++) { await page.keyboard.press("Tab"); if (!(await inPanel())) { left = true; break; } }
if (left) add("Display slide-out", "keyboard", "focus-trapped", "Tab left the open slide-out");
await page.keyboard.press("Escape");
await page.waitForTimeout(400);
const back = await page.evaluate(() => /Display/.test(document.activeElement?.textContent || ""));
if (!back) add("Display slide-out", "keyboard", "focus-returns", "focus did not return to Display after Escape");

// Forced colours (Windows High Contrast): focus rings must survive.
await page.emulateMedia({ forcedColors: "active" });
await page.goto(`${base}/settings-general.html`);
await settle();
let noRing = 0;
for (let i = 0; i < 15; i++) {
  await page.keyboard.press("Tab");
  const ok = await page.evaluate(() => { const cs = getComputedStyle(document.activeElement); return cs.outlineStyle !== "none" && parseFloat(cs.outlineWidth) > 0; });
  if (!ok) noRing++;
}
if (noRing) add("settings-general.html", "forced colours", "focus-visible", `${noRing} of 15 Tab stops have no outline in forced colours`);
await page.emulateMedia({ forcedColors: "none" });

// Reduced motion: transitions and animations become instant.
await page.emulateMedia({ reducedMotion: "reduce" });
await page.goto(`${base}/index.html`);
await settle();
const moving = await page.evaluate(() => [...document.querySelectorAll("*")].filter((e) => {
  const cs = getComputedStyle(e);
  const t = Math.max(...cs.transitionDuration.split(",").map(parseFloat)) * 1000;
  const a = cs.animationName !== "none" ? Math.max(...cs.animationDuration.split(",").map(parseFloat)) * 1000 : 0;
  return t > 50 || a > 50;
}).slice(0, 5).map((e) => e.className || e.tagName));
if (moving.length) add("index.html", "motion", "reduced-motion", moving.join(", "), moving.length);

await browser.close();
fs.writeFileSync(process.env.OUT || "/work/a11y.json", JSON.stringify(findings, null, 1));
const by = {};
for (const f of findings) { const k = `${f.area} · ${f.rule}`; by[k] = by[k] || { pages: new Set(), n: 0 }; by[k].pages.add(f.page); by[k].n += f.count; }
console.log(`\n== ${findings.length} findings on ${ALL.length} pages`);
for (const [k, v] of Object.entries(by).sort((a, b) => b[1].pages.size - a[1].pages.size)) console.log(`${String(v.pages.size).padStart(3)} pages  ${k}  (${v.n})`);
