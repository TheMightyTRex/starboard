// Browser journeys against the example-data server (tools/journeys.sh runs this in the Playwright image).
// TEST-PLAN USE-02, SEC-05, SEC-07, SEC-12 and SEC-13, plus no sideways scrolling at phone width on every page.
// Prints PASS or FAIL for each check and exits 1 if any failed. Everything it adds, it removes again.
import { chromium } from "playwright";
import fs from "fs";

const base = process.env.BASE || "http://127.0.0.1:18792";
const password = fs.readFileSync(process.env.PASSWORD_FILE, "utf8").trim();
const PAGES = ["index.html", "apps-services.html", "apps-updates.html", "search.html", "downloads.html", "downloads-requests.html",
  "upcoming.html", "system.html", "system-storage.html", "system-disks.html", "system-monitor.html", "system-network.html",
  "system-logs.html", "system-backup.html", "settings.html", "settings-general.html", "settings-security.html",
  "settings-alerts.html", "settings-updates.html", "settings-performance.html", "settings-jellyfin.html",
  "settings-audiobookshelf.html", "copy-settings.html", "install-apps.html", "setup-guide.html", "upgrade.html"];
const SECRET = "made-up-journey-key-7f3a9c1e5b";
const XSS = `<img src=x onerror="window.__xss='name'">`;

let passed = 0, failed = 0;
function check(id, what, ok, detail = "") {
  if (ok) passed++; else failed++;
  console.log(`${ok ? "PASS" : "FAIL"} ${id} ${what}${!ok && detail ? `: ${detail}` : ""}`);
}

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1280, height: 860 } });
const page = await context.newPage();
const problems = [];
page.on("pageerror", (e) => problems.push(`${page.url()}: ${e.message}`));
page.on("console", (m) => { if (m.type() === "error" && !/40[04]/.test(m.text())) problems.push(`${page.url()}: ${m.text()}`); });
await page.goto(`${base}/login.html`);
await page.fill("input[type=password]", password);
await page.keyboard.press("Enter");
await page.waitForURL(/index/);
const api = (path, opts) => page.evaluate(([p, o]) => api(p, o), [path, opts]);
const open = async (p) => { await page.goto(`${base}/${p}`, { waitUntil: "networkidle" }); await page.waitForTimeout(400); };

// USE-02: add, change, test and remove an app, through the page as a person would
console.log("\n== USE-02 Manage apps");
await open("settings.html");
await page.click("#add-service");
const panel = page.locator("#service-form");
await panel.locator("select[name=type]").selectOption("link");
await panel.locator("input[name=name]").fill("Journey App");
await panel.locator("input[name=url]").fill("http://journey-app:8080");
await page.getByRole("button", { name: "Add app" }).click();
await page.waitForTimeout(800);
check("USE-02", "added: the toast says so", (await page.locator("#toast-stack").textContent())?.includes("Journey App added"));
const row = () => page.locator("#app-sections .row__title button", { hasText: /^Journey/ });
check("USE-02", "added: it is in the list", await row().count() === 1);
await row().click();
await panel.locator("input[name=name]").fill("Journey Renamed");
await page.getByRole("button", { name: "Save app" }).click();
await page.waitForTimeout(800);
check("USE-02", "changed: the new name is in the list", (await row().textContent())?.includes("Journey Renamed"));
await row().click();
await panel.locator("select[name=type]").selectOption("sonarr");
await panel.locator("input[name=url]").fill("http://127.0.0.1:9");
await panel.locator("input[name=api_key]").fill("made-up");
await page.getByRole("button", { name: "Test connection" }).click();
await page.getByText(/Cannot connect|Cannot test yet/).first().waitFor({ timeout: 20000 }).catch(() => {});
check("USE-02", "test: an app that is not there says it cannot connect", await page.getByText(/Cannot connect|Cannot test yet/).count() > 0);
await page.getByRole("button", { name: /^Remove/ }).click();
await page.locator("dialog[open]").getByRole("button", { name: "Remove Journey Renamed", exact: true }).click();
await page.waitForTimeout(800);
check("USE-02", "removed: gone from the list", await row().count() === 0);

// CON-01: an error shows beside what it belongs to; with nothing on the page, as an error toast that stays
console.log("\n== CON-01 Errors beside what they belong to");
await open("settings-general.html");
const cats = (await api("/api/config")).groups;
await page.locator("#category-list .row").first().getByRole("button", { name: /^Rename/ }).click();
await page.locator("dialog[open] input").fill(cats[1]);
await page.locator("dialog[open]").getByRole("button", { name: "Rename category" }).click();
await page.waitForTimeout(300);
const beside = page.locator("#category-list .row").first().locator(".field-error");
check("CON-01", "a rename to a name in use says so in its row", (await beside.textContent().catch(() => ""))?.includes("There is already a category"));
check("CON-01", "and not in a toast", await page.locator("#toast-stack .toast").count() === 0);
await page.locator("#category-list .row").first().getByRole("button", { name: /^Rename/ }).click();
await page.keyboard.press("Escape");
check("CON-01", "the next try clears it", await beside.count() === 0);
await open("index.html");
await page.evaluate(() => problem("A made-up journey error"));
check("CON-01", "with nothing in use, an error toast", await page.locator('#toast-stack .toast[data-tone="danger"]').count() === 1);
await open("apps-updates.html");
const summary = await page.locator("#updates-summary").textContent();
const label = (await page.locator("#check-updates").textContent()).trim();
check("DASH-50", "the Updates button says Check until the first check", /Not checked/.test(summary) ? label === "Check" : /Last checked/.test(summary) ? label === "Check again" : true, `${label} / ${summary}`);

// SEC-07: names, categories, descriptions and UX notes that look like code are shown as text
console.log("\n== SEC-07 Text that looks like code");
const before = await api("/api/config");
await api("/api/config/general", { method: "PUT", body: { groups: [...before.groups, `"><svg onload="window.__xss='group'">`], ux_notes: true } });
const added = await api("/api/services", { method: "POST", body: { type: "link", name: XSS, url: "http://journey-xss:8080",
  description: `<script>window.__xss='description'</script>`, group: `"><svg onload="window.__xss='group'">` } });
await api("/api/ux-notes", { method: "POST", body: { what: `<img src=x onerror="window.__xss='note'">`, page: "/index.html", part: XSS } });
for (const p of ["index.html", "apps-services.html", "settings.html", "settings-general.html"]) {
  await open(p);
  if (p === "index.html") {
    await page.locator(".ux-dock button").last().click();
    await page.waitForTimeout(500);
    check("SEC-07", "a UX note is shown as text", await page.locator("dialog[open]").getByText(`<img src=x onerror="window.__xss='note'">`).count() > 0);
  }
  const ran = await page.evaluate(() => window.__xss);
  check("SEC-07", `${p}: nothing ran`, !ran, `window.__xss = ${ran}`);
}
await open("index.html");
check("SEC-07", "the name is shown as text", await page.getByText(XSS, { exact: true }).count() > 0);
const notes = await api("/api/ux-notes");
for (const n of notes.notes || []) await api("/api/ux-notes/remove", { method: "POST", body: { id: n.id } });
await api(`/api/services/${added.id}`, { method: "DELETE" });
await api("/api/config/general", { method: "PUT", body: { groups: before.groups, ux_notes: before.ux_notes } });

// SEC-12 and SEC-13: every page has the content policy and runs no blocked script; a saved key never comes back
console.log("\n== SEC-12 and SEC-13 every page");
const keyed = await api("/api/services", { method: "POST", body: { type: "sonarr", name: "Journey Keyed", url: "http://journey-keyed:8989", api_key: SECRET } });
const leaks = [];
page.on("response", async (r) => {
  try { if ((await r.text()).includes(SECRET)) leaks.push(r.url()); } catch { /* bodies of redirects and images */ }
});
const blocked = [];
page.on("console", (m) => { if (/Content Security Policy|Refused to (execute|load|apply)/i.test(m.text())) blocked.push(`${page.url()}: ${m.text()}`); });
const noPolicy = [];
for (const p of PAGES) {
  const r = await page.goto(`${base}/${p}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(300);
  if (!/script-src 'self'/.test(r.headers()["content-security-policy"] || "") && !/default-src 'self'/.test(r.headers()["content-security-policy"] || "")) noPolicy.push(p);
}
for (const p of ["/api/config", "/api/logs", "/api/logs/report", "/api/session", "/api/services/status"]) {
  await page.goto(`${base}${p}`).catch(() => {});
}
check("SEC-12", `content policy on all ${PAGES.length} pages`, noPolicy.length === 0, noPolicy.join(", "));
check("SEC-12", "no script or style blocked", blocked.length === 0, blocked.slice(0, 5).join(" | "));
check("SEC-13", "the saved key is in no page or answer", leaks.length === 0, leaks.join(", "));
await api(`/api/services/${keyed.id}`, { method: "DELETE" }).catch(() => {});

// SEC-05: after signing in, the next address can only be a page on this dashboard
console.log("\n== SEC-05 Sign-in goes only to this dashboard");
for (const trick of ["//evil.example/", "/%09/evil.example", "https://evil.example/"]) {
  const fresh = await browser.newContext();
  const p = await fresh.newPage();
  await p.goto(`${base}/login.html?next=${encodeURIComponent(trick)}`);
  await p.fill("input[type=password]", password);
  await p.keyboard.press("Enter");
  await p.waitForLoadState("networkidle").catch(() => {});
  await p.waitForTimeout(800);
  check("SEC-05", `next=${trick} stays on the dashboard`, new URL(p.url()).origin === new URL(base).origin, p.url());
  await fresh.close();
}

// Phone width: no page scrolls sideways
console.log("\n== Phone width");
await page.setViewportSize({ width: 375, height: 812 });
const wide = [];
for (const p of PAGES) {
  await open(p);
  const over = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
  if (over > 0) wide.push(`${p} by ${over}px`);
}
check("USE-01", "no page scrolls sideways at 375 wide", wide.length === 0, wide.join(", "));
check("ALL", "no script errors on any page", problems.length === 0, problems.slice(0, 5).join(" | "));

console.log(`\n== ${passed} passed, ${failed} failed`);
await browser.close();
process.exit(failed ? 1 : 0);
