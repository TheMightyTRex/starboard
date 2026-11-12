// Reading order (owner, 12 November 2026: "make sure screen readers follow best practice on the sequencing and order
// of the app"). A screen reader reads, and Tab moves, in the page's code order; people see the visual order. For
// every page (in each app-card design on Apps), this lists:
//  - order: a thing read later that is shown clearly above, or to the left on the same line, of the one before it
//    in the same column (WCAG 1.3.2 Meaningful sequence, 2.4.3 Focus order);
//  - tab: Tab order that jumps back up the page;
//  - landmarks: the order skip link, header, navigation, main, footer;
//  - head: the page starts with its h1 inside main, before any control of the page's own.
// tools/a11y.sh runs it with ORDER=1.
import { chromium } from "playwright";
import fs from "fs";

const base = process.env.BASE;
const password = fs.readFileSync(process.env.PASSWORD_FILE, "utf8").trim();
const findings = [];
const add = (page, rule, detail) => findings.push({ page, rule, detail: String(detail).slice(0, 300) });
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
  await page.waitForTimeout(900);
}

async function check(name, width) {
  const r = await page.evaluate(() => {
    const out = { order: [], landmarks: [], head: [] };
    const shown = (e) => {
      if (!e.getClientRects().length) return false;
      const s = getComputedStyle(e);
      if (s.visibility === "hidden" || s.display === "none") return false;
      const b = e.getBoundingClientRect();
      if (b.width < 2 || b.height < 2) return false;
      if (e.closest("details:not([open])") && !e.closest("summary")) return false;  // a closed fold-out shows only its summary
      return !e.closest("[hidden], [aria-hidden=true], .visually-hidden, #side-panel, dialog:not([open])");
    };
    const main = document.querySelector("main");
    // Reading items: headings, text blocks, controls and chips, not their children twice.
    const items = [...main.querySelectorAll("h1,h2,h3,h4,p,li > .row__title,button,a[href],input,select,textarea,.chip,dt,dd,label,legend,th,td,figcaption,summary")]
      .filter(shown).filter((e) => !e.parentElement.closest("button,a[href],label,summary,.chip"));
    const label = (e) => `${e.tagName.toLowerCase()} "${(e.getAttribute("aria-label") || e.textContent || e.value || "").trim().replace(/\s+/g, " ").slice(0, 40)}"`;
    for (let i = 1; i < items.length; i++) {
      const a = items[i - 1].getBoundingClientRect(), b = items[i].getBoundingClientRect();
      const sameColumn = Math.min(a.right, b.right) - Math.max(a.left, b.left) > 0;
      const sameLine = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > Math.min(a.height, b.height) * 0.5;
      // A grid of cards reads left to right, then the next row: a jump back to the left on a lower line is normal.
      if (sameColumn && b.bottom < a.top - 8) out.order.push(`${label(items[i])} is read after ${label(items[i - 1])} but shown above it`);
      else if (sameLine && b.right < a.left - 8) out.order.push(`${label(items[i])} is read after ${label(items[i - 1])} but shown to its left`);
    }
    // Landmarks in order.
    const marks = [...document.querySelectorAll("a.skip-link, header, nav, main, footer, [role=banner], [role=navigation], [role=main], [role=contentinfo]")]
      .filter((e) => !e.closest("#side-panel, dialog, template") && (e.matches("a.skip-link") || e.getClientRects().length));
    const kinds = marks.map((e) => e.matches("a.skip-link") ? "skip" : e.matches("header,[role=banner]") && !e.closest("main, article, section") ? "header"
      : e.matches("nav,[role=navigation]") ? (e.closest("main") ? "nav-in-main" : "nav") : e.matches("main,[role=main]") ? "main" : e.matches("footer,[role=contentinfo]") && !e.closest("main") ? "footer" : "");
    const seq = kinds.filter((k) => ["skip", "header", "main", "footer"].includes(k));
    const want = ["skip", "header", "main", "footer"].filter((k) => seq.includes(k));
    if (seq.join() !== [...new Set(seq)].join() || [...new Set(seq)].join() !== want.join()) out.landmarks.push(`landmarks in order ${kinds.filter(Boolean).join(", ")}`);
    if (kinds[0] !== "skip") out.landmarks.push(`the skip link is not first (${kinds[0] || "none"})`);
    // The page's own content starts with its h1.
    const firstReal = [...main.querySelectorAll("h1,h2,h3,button,a[href],input,select,textarea,p")].filter(shown)
      .find((e) => !e.closest(".lib-tabs, .menu-tabs, .page-back, .back-link") && !e.matches(".page-back, .back-link, a[href].back"));
    if (firstReal && firstReal.tagName !== "H1") out.head.push(`main starts with ${label(firstReal)} before the h1`);
    return out;
  });
  for (const o of [...new Set(r.order)].slice(0, 8)) add(`${name}${width ? ` @${width}` : ""}`, "order", o);
  if (r.order.length > 8) add(`${name}${width ? ` @${width}` : ""}`, "order", `and ${r.order.length - 8} more`);
  for (const o of r.landmarks) add(name, "landmarks", o);
  for (const o of r.head) add(name, "head", o);
}

async function tabOrder(name) {
  await page.evaluate(() => { document.activeElement?.blur(); window.scrollTo(0, 0); });
  let lastY = -1, lastX = -1, jumps = [], been = false;
  for (let i = 0; i < 80; i++) {
    await page.keyboard.press("Tab");
    const f = await page.evaluate(() => {
      const e = document.activeElement;
      if (!e || e === document.body) return null;
      if (!e.closest("main")) return { out: true };
      const r = e.getBoundingClientRect();
      return { y: r.top + scrollY, x: r.left, b: r.bottom + scrollY, t: (e.getAttribute("aria-label") || e.textContent || e.name || e.id || "").trim().replace(/\s+/g, " ").slice(0, 40) };
    });
    if (!f) continue;
    if (f.out) { if (been) break; continue; }  // past the end of the page's own part: done, no wrapping round
    been = true;
    // Up and not to the right: a grid of cards goes left to right, then down, which is fine.
    if (lastY >= 0 && f.b < lastY - 40 && f.x <= lastX + 10) jumps.push(`Tab goes back up to "${f.t}"`);
    lastY = f.y; lastX = f.x;
  }
  for (const j of [...new Set(jumps)].slice(0, 4)) add(name, "tab", j);
}

const ALL = (process.env.PAGES || "").split(",").filter(Boolean).length ? process.env.PAGES.split(",") : fs.readdirSync(process.env.WEB || "/web").filter((f) => f.endsWith(".html") &&
  !["login.html", "setup.html", "offline.html", "wanted-moved.html", "discover-trending.html", "wanted.html", "wanted-quality.html"].includes(f));
const ITEMS = { "library-film.html": "?id=3", "library-tv-show.html": "?id=8", "library-artist.html": "?id=1", "library-radio-show.html": "?id=1",
  "library-book.html": "?id=4", "library-audiobook.html": "?id=6" };
for (const name of ALL) {
  try {
    await page.goto(`${base}/${name}${ITEMS[name] || ""}`);
    await settle();
    await check(name);
    await tabOrder(name);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(300);
    await check(name, 390);
    await page.setViewportSize({ width: 1280, height: 860 });
    console.log(`checked ${name}`);
  } catch (e) { add(name, "error", e.message.split("\n")[0]); }
}
// Apps in each card design (Display, Design): the parts of a card are placed in rows by design.
for (const design of ["health", "tiles", "board", "shelf"]) {
  await page.goto(`${base}/index.html`);
  await settle();
  await page.evaluate((d) => document.documentElement.setAttribute("data-design", d), design);
  await page.waitForTimeout(300);
  await check(`index.html design ${design}`);
}
await browser.close();
fs.writeFileSync(process.env.OUT || "/work/order.json", JSON.stringify(findings, null, 1));
const by = {};
for (const f of findings) { by[f.rule] = by[f.rule] || new Set(); by[f.rule].add(f.page.split(" ")[0]); }
console.log(`\n== ${findings.length} findings`);
for (const [k, v] of Object.entries(by)) console.log(`${k}: ${v.size} pages`);
