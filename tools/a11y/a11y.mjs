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
  !["login.html", "setup.html", "offline.html", "wanted-moved.html", "discover-trending.html", "wanted.html", "wanted-quality.html"].includes(f));
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
