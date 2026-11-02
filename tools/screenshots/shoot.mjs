// Takes every README screenshot from the example-data server (tools/screenshots.sh runs this in the
// Playwright image). Each shot: file, page, size, theme, and optionally a script to run first and a thing to
// click. Console errors are listed at the end; the run fails if a page scrolls sideways.
import { chromium } from "playwright";
import fs from "fs";

const base = process.env.BASE || "http://127.0.0.1:18792";
const out = process.env.OUT || "/out";
const password = fs.readFileSync(process.env.PASSWORD_FILE, "utf8").trim();
const top = (selector) => `window.scrollTo(0, document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect().top + scrollY - 130)`;
const jellyfin = `document.querySelector("#jellyfin-panel").hidden = false;
  renderJellyfin({ configured: true, name: "Jellyfin", version: "10.11.2", restart: false, update: true, channels: 42,
    guide: { state: "Idle", finished: new Date(Date.now() - 3600e3).toISOString(), result: "Completed" },
    playing: [{ title: "The Long Field", series: "", user: "Sam", device: "Living room TV", progress: 42, paused: false, transcoding: false }],
    added: [{ title: "Harbour Street", series: "", type: "Movie", when: new Date(Date.now() - 7200e3).toISOString() }] });
  ${top("#jellyfin-panel")}`;

const desk = { width: 1280, height: 860 };
const phone = { width: 390, height: 844 };
// The upgrade shots come last: they set the example server back to 0.4.0, which adds the upgrade notice.
const SHOTS = [
  { file: "apps.png", page: "index.html", ...desk },
  { file: "storage.png", page: "system-storage.html", ...desk },
  { file: "storage-dark.png", page: "system-storage.html", ...desk, scheme: "dark" },
  { file: "storage-drives.png", page: "system-storage.html", ...desk, run: top("#drives-panel") },
  { file: "storage-history.png", page: "system-storage.html", width: 1280, height: 760, run: top("#growth-panel") },
  { file: "jellyfin.png", page: "system.html", width: 1280, height: 560, run: jellyfin },
  { file: "install-apps.png", page: "install-apps.html", ...desk },
  { file: "setup-guide.png", page: "setup-guide.html", ...desk },
  { file: "performance.png", page: "settings-performance.html", ...desk },
  { file: "search-new-apps.png", page: "settings.html", ...desk, click: "#find-apps" },
  { file: "release-notes.png", page: "index.html", ...desk, click: ".site-footer .version-label" },
  { file: "logs.png", page: "system-logs.html", ...desk, before: 'api("/api/config/general", { method: "PUT", body: { logs: { detail: "day" } } })' },
  { file: "logs-entries.png", page: "system-logs.html", ...desk, run: top("#entries-h") },
  { file: "display.png", page: "index.html", ...desk, click: "[data-display-toggle]" },
  { file: "copy-settings.png", page: "copy-settings.html", width: 1280, height: 1000, click: "#copy-sections button[type=submit]", after: top("#copy-sections h3") },
  { file: "audiobookshelf.png", page: "settings-audiobookshelf.html", ...desk, run: top("#listening-sections .table-wrap") },
  { file: "logs-settings.png", page: "settings-general.html", width: 1280, height: 700, run: top("#gn-logs-h") },
  { file: "apps-phone.png", page: "index.html", ...phone },
  { file: "storage-phone.png", page: "system-storage.html", ...phone },
  { file: "upgrade-notice.png", page: "index.html", ...desk, before: 'api("/api/config/general", { method: "PUT", body: { last_version: "0.4.0" } })' },
  { file: "upgrade-guide.png", page: "upgrade.html", ...desk },
];

fs.mkdirSync(out, { recursive: true });
const browser = await chromium.launch();
const errors = [];
let failed = false;
const contexts = {};
async function pageFor(shot) {
  const key = `${shot.width}x${shot.height}-${shot.scheme || "light"}`;
  if (!contexts[key]) {
    const context = await browser.newContext({ viewport: { width: shot.width, height: shot.height }, colorScheme: shot.scheme || "light" });
    const page = await context.newPage();
    page.on("pageerror", (e) => errors.push(`${page.url()}: ${e.message}`));
    page.on("console", (m) => { if (m.type() === "error" && !/40[04]/.test(m.text())) errors.push(`${page.url()}: ${m.text()}`); });
    await page.goto(`${base}/login.html`);
    await page.fill("input[type=password]", password);
    await page.keyboard.press("Enter");
    await page.waitForURL(/index/);
    contexts[key] = page;
  }
  return contexts[key];
}
for (const shot of SHOTS) {
  const page = await pageFor(shot);
  if (shot.before) {
    await page.goto(`${base}/index.html`, { waitUntil: "networkidle" });
    await page.evaluate(shot.before);
  }
  await page.goto(`${base}/${shot.page}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(600);
  if (shot.run) { await page.evaluate(shot.run); await page.waitForTimeout(300); }
  if (shot.click) { await page.locator(shot.click).first().click(); await page.waitForTimeout(600); }
  if (shot.after) { await page.evaluate(shot.after); await page.waitForTimeout(300); }
  await page.screenshot({ path: `${out}/${shot.file}` });
  const wide = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
  if (wide > 0) failed = true;
  console.log(shot.file, wide > 0 ? `SCROLLS SIDEWAYS by ${wide}px` : "ok");
}
console.log(errors.length ? `Console errors:\n${errors.join("\n")}` : "No console errors");
await browser.close();
process.exit(failed || errors.length ? 1 : 0);
