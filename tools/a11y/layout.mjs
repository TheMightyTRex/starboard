// Layout at large text, wide spacing and short windows (DASH-437, 15 November 2026). axe and the reflow check miss a
// menu that cuts off its own items, because the page itself does not scroll sideways. This walks the side menu and
// the header on a few pages at every text size (100, 125, 150 and 175%), with and without wider spacing, in Light,
// Dark and High contrast, at 1280 and 1366 pixels wide and at phone width, and in short windows (600 and 700 pixels
// tall), and fails when:
//   L1 a word in the side menu breaks in the middle ("Starbo ard");
//   L2 a side menu name runs past the side menu's edge;
//   L3 side menu items overlap, or an item is cut off with no way to scroll to it;
//   H1 header items overlap, or run past the header's edge;
//   H2 a header menu item is cut off (only part of it, or none of it, shows);
//   H3 the header search field is too narrow to read what is typed;
//   H4 the page scrolls sideways;
//   H5 header menu items are hidden with no Menu button to reach them.
// The settings are changed the way Display changes them (applyPrefs), so the header refits as it does for a person.
// tools/a11y.sh runs it with LAYOUT=1. SHOTS=1 instead saves the screenshots for the help and the report.
import { chromium } from "playwright";
import fs from "fs";

const base = process.env.BASE;
const password = fs.readFileSync(process.env.PASSWORD_FILE, "utf8").trim();
const PAGES = (process.env.PAGES || "index.html,system.html,settings-general-appearance.html,settings-reelix.html,discover-films.html,library-films.html,dashboard.html,downloads.html").split(",").filter(Boolean);
const VIEWPORTS = [[1280, 860], [1280, 700], [1280, 600], [1366, 768], [1366, 700], [1366, 600], [390, 844], [390, 600]];
const TEXT = ["100", "125", "150", "175"];
const THEMES = [["light", false], ["dark", false], ["light", true]];

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1280, height: 860 } });
const page = await ctx.newPage();
await page.goto(`${base}/login.html`);
await page.locator("#password").fill(password);
await page.locator("#password").press("Enter");
await page.waitForURL((u) => !u.pathname.endsWith("login.html"), { timeout: 15000 }).catch(() => {});

async function settle() {
  await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
  await page.waitForFunction(() => !document.querySelector("[aria-busy=true]"), null, { timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(500);
}
// Change the Display settings as the Display slide-out does, then let the header refit.
async function prefs(text, spacing, theme, contrast) {
  await page.evaluate(([text, spacing, theme, contrast]) => {
    // Send feedback is on in the example data on some pages only: show it everywhere, as its longest case.
    document.querySelectorAll(".rail__feedback").forEach((b) => { b.hidden = false; });
    applyPrefs({ ...readPrefs(), text, spacing, theme, contrast });
  }, [text, spacing, theme, contrast]);
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(120);
}

// Everything is measured in the page: one call per state.
const measure = () => page.evaluate(() => {
  const out = [];
  const shown = (e) => e && getComputedStyle(e).display !== "none" && getComputedStyle(e).visibility !== "hidden" && e.getClientRects().length > 0;
  const name = (e) => (e.getAttribute("aria-label") || e.textContent || "").trim().replace(/\s+/g, " ").slice(0, 30);
  const textNodes = (e) => { const w = document.createTreeWalker(e, NodeFilter.SHOW_TEXT); const n = []; while (w.nextNode()) n.push(w.currentNode); return n; };
  // Side menu.
  const rail = document.querySelector(".rail");
  if (shown(rail)) {
    const box = rail.getBoundingClientRect();
    const items = [...rail.querySelectorAll(":scope > *:not(.rail__end), .rail__end > *")].filter(shown);
    for (const item of items) {
      for (const node of textNodes(item).filter((n) => n.textContent.trim() && !n.parentElement.closest(".visually-hidden"))) {
        for (const m of node.textContent.matchAll(/\S+/g)) {
          const r = document.createRange();
          r.setStart(node, m.index); r.setEnd(node, m.index + m[0].length);
          const rects = [...r.getClientRects()].filter((x) => x.width > 0.5);
          const lines = new Set(rects.map((x) => Math.round(x.top)));
          if (lines.size > 1) out.push(["L1", `"${m[0]}" breaks over ${lines.size} lines`]);
          for (const x of rects) {
            if (x.left < box.left - 0.5 || x.right > box.right - 0.5) { out.push(["L2", `"${m[0]}" runs past the side menu's edge by ${Math.round(Math.max(box.left - x.left, x.right - box.right + 1))}px`]); break; }
          }
        }
      }
    }
    for (let i = 1; i < items.length; i++) {
      const a = items[i - 1].getBoundingClientRect(), b = items[i].getBoundingClientRect();
      if (a.bottom > b.top + 1) out.push(["L3", `${name(items[i - 1])} and ${name(items[i])} overlap by ${Math.round(a.bottom - b.top)}px`]);
    }
    const scrolls = /auto|scroll/.test(getComputedStyle(rail).overflowY);
    for (const item of items) {
      const r = item.getBoundingClientRect();
      if (r.bottom > box.bottom + 1 && !scrolls) out.push(["L3", `${name(item)} is cut off at the foot of the side menu`]);
      // An item squeezed smaller than what it holds: its icon or name spills over the next one.
      if (item.scrollHeight > item.clientHeight + 1 && getComputedStyle(item).overflow === "visible") out.push(["L3", `${name(item)} is squeezed to ${Math.round(r.height)}px, smaller than its icon and name`]);
    }
  }
  // Header.
  const bar = document.querySelector(".site-header__bar");
  if (shown(bar)) {
    const box = bar.getBoundingClientRect();
    const kids = [...bar.children].filter(shown).filter((k) => k.getBoundingClientRect().width > 1).sort((a, b) => a.getBoundingClientRect().left - b.getBoundingClientRect().left);
    for (let i = 0; i < kids.length; i++) {
      const r = kids[i].getBoundingClientRect();
      if (r.right > box.right + 1 || r.left < box.left - 1) out.push(["H1", `${kids[i].className.split(" ")[0]} runs past the header's edge`]);
      if (i && kids[i - 1].getBoundingClientRect().right > r.left + 1) out.push(["H1", `${kids[i - 1].className.split(" ")[0]} and ${kids[i].className.split(" ")[0]} overlap`]);
    }
    let hidden = false;
    for (const nav of document.querySelectorAll(".site-header .menu-tabs")) {
      if (!shown(nav)) { hidden = true; continue; }
      const n = nav.getBoundingClientRect();
      // A 2nd level row that scrolls sideways (26 November 2026) may have tabs past its edge, with a fade; what must hold is that
      // each tab is 44px wide and the current tab is fully in view.
      const scrolls = !!nav.closest(".site-header__tabs") && nav.scrollWidth > nav.clientWidth + 1;
      for (const a of nav.querySelectorAll("a")) {
        const r = a.getBoundingClientRect();
        if (r.width < 1) continue;
        if (scrolls) {
          if (r.width < 43.9) out.push(["H2", `${nav.getAttribute("aria-label")} menu: ${name(a)} is under 44px wide (${Math.round(r.width)}px)`]);
          if (a.getAttribute("aria-current") === "page" && (r.left < n.left - 1 || r.right > n.right + 1)) out.push(["H2", `${nav.getAttribute("aria-label")} menu: the current tab ${name(a)} is not in view`]);
          continue;
        }
        if (r.left < n.left - 1 || r.right > n.right + 1) out.push(["H2", `${nav.getAttribute("aria-label")} menu: ${name(a)} is cut off (${Math.round(Math.max(0, Math.min(r.right, n.right) - Math.max(r.left, n.left)))} of ${Math.round(r.width)}px show)`]);
      }
    }
    const input = document.querySelector("#header-search-input");
    if (shown(input) && input.closest(".site-header__search") && shown(input.closest(".site-header__search"))) {
      const size = parseFloat(getComputedStyle(input).fontSize);
      const w = input.clientWidth;
      if (w < Math.max(150, 6 * size)) out.push(["H3", `the search field is ${w}px wide (at least ${Math.round(Math.max(150, 6 * size))}px needed at this text size)`]);
    }
    if (hidden && !shown(document.querySelector("[data-phone-menu-open]"))) out.push(["H5", "header menu items are hidden and there is no Menu button"]);
  }
  if (document.scrollingElement.scrollWidth > innerWidth + 1) out.push(["H4", `the page scrolls sideways by ${document.scrollingElement.scrollWidth - innerWidth}px`]);
  return out;
});

if (process.env.SHOTS) {
  // The before and after pictures for DASH-437: the side menu and header at large text, and a short window.
  const dir = process.env.SHOTS_DIR || "/work/shots", tag = process.env.SHOTS_TAG || "shot";
  fs.mkdirSync(dir, { recursive: true });
  const shots = [
    ["1-side-menu-150", "index.html", [1280, 860], "150", false, { x: 0, y: 0, width: 420, height: 860 }],
    ["1-side-menu-175", "index.html", [1280, 860], "175", false, { x: 0, y: 0, width: 420, height: 860 }],
    ["1-side-menu-175-spacing", "index.html", [1280, 860], "175", true, { x: 0, y: 0, width: 420, height: 860 }],
    ["2-header-system-175", "system.html", [1280, 860], "175", false, { x: 0, y: 0, width: 1280, height: 260 }],
    ["2-header-system-175-spacing", "system.html", [1280, 860], "175", true, { x: 0, y: 0, width: 1280, height: 260 }],
    ["2-header-settings-175", "settings-general-appearance.html", [1366, 768], "175", false, { x: 0, y: 0, width: 1366, height: 260 }],
    ["3-short-window-600", "index.html", [1280, 600], "100", false, null],
    ["3-short-window-600-150", "index.html", [1280, 600], "150", false, null],
  ];
  for (const [file, path, [w, h], text, spacing, clip] of shots) {
    await page.setViewportSize({ width: w, height: h });
    await page.goto(`${base}/${path}`);
    await settle();
    await prefs(text, spacing, "light", false);
    await page.screenshot({ path: `${dir}/${tag}-${file}.png`, ...(clip ? { clip } : {}) });
    const found = await measure();
    console.log(`${tag}-${file}: ${found.length ? found.map((f) => f.join(" ")).join("; ") : "no layout findings"}`);
  }
  await browser.close();
  process.exit(0);
}

let checked = 0;
const failures = new Map();
for (const path of PAGES) {
  await page.setViewportSize({ width: 1280, height: 860 });
  await page.goto(`${base}/${path}`);
  await settle();
  for (const [w, h] of VIEWPORTS) {
    await page.setViewportSize({ width: w, height: h });
    for (const text of TEXT) for (const spacing of [false, true]) for (const [theme, contrast] of THEMES) {
      await prefs(text, spacing, theme, contrast);
      checked++;
      for (const [rule, what] of await measure()) {
        const key = `${rule} ${path}: ${what}`;
        const where = `${w}x${h} ${text}%${spacing ? " spacing" : ""} ${contrast ? "high contrast" : theme}`;
        if (!failures.has(key)) failures.set(key, []);
        failures.get(key).push(where);
      }
    }
  }
  // Leave the next page as it would start.
  await prefs("100", false, "system", false);
}
for (const [key, where] of failures) console.log(`FAIL ${key} (${where.length}: ${where.slice(0, 3).join(", ")}${where.length > 3 ? ", ..." : ""})`);
console.log(`Layout: ${checked} states on ${PAGES.length} pages, ${failures.size} findings, ${[...failures.values()].reduce((n, w) => n + w.length, 0)} failing states`);
fs.writeFileSync("/work/layout.json", JSON.stringify([...failures].map(([k, w]) => ({ finding: k, states: w })), null, 1));
await browser.close();
process.exit(failures.size ? 1 : 0);
