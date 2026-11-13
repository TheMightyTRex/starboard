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
  "settings-alerts.html", "settings-updates.html", "settings-releases.html", "settings-restore.html", "settings-performance.html", "settings-jellyfin.html",
  "settings-audiobookshelf.html", "copy-settings.html", "install-apps.html", "setup-guide.html", "upgrade.html", "settings-install.html",
  // The Library, from the made-up Reelix (DASH-163)
  "library-tv.html", "library-tv-networks.html", "library-films.html", "library-films-collections.html", "library-music.html",
  "library-radio.html", "library-radio-stations.html", "library-books.html", "library-books-series.html",
  "library-books-authors.html", "library-audiobooks.html", "library-audiobooks-series.html", "library-audiobooks-authors.html",
  "library-audiobooks-narrators.html",
  "library-film.html?id=3", "library-tv-show.html?id=8", "library-artist.html?id=1", "library-radio-show.html?id=1",
  "library-book.html?id=4", "library-audiobook.html?id=6",
  "discover-films.html", "discover-radio.html", "downloads-finished.html", "wanted-films.html", "wanted-music.html", "wanted-audiobooks.html", "history.html", "settings-reelix.html",
  "search-sites.html", "settings-radio.html",  // Search the sites (DASH-213), Settings, Radio (DASH-212)
  "settings-dispatcharr.html",  // Settings, Apps, Dispatcharr (DASH-228)
  // General's level 2 pages (DASH-389)
  "settings-general-appearance.html", "settings-general-lists.html", "settings-general-hours.html", "settings-general-logs.html",
  "settings-general-discover.html", "discover-tv.html", "discover-books.html",  // Discover rows, a section per area (DASH-396)
  // Downloads' level 2 pages (DASH-390)
  "settings-downloads.html", "settings-downloads-usenet.html", "settings-downloads-hours.html",
  // Radio's, Performance's and Security's level 2 pages (DASH-391)
  "settings-radio-link.html", "settings-radio-library.html", "settings-radio-logos.html", "settings-performance-pictures.html",
  "settings-security-password.html", "settings-security-keys.html", "settings-security-sessions.html"];
const SECRET = "made-up-journey-key-7f3a9c1e5b";
const XSS = `<img src=x onerror="window.__xss='name'">`;

let passed = 0, failed = 0;
function check(id, what, ok, detail = "") {
  if (ok) passed++; else failed++;
  console.log(`${ok ? "PASS" : "FAIL"} ${id} ${what}${!ok && detail ? `: ${detail}` : ""}`);
}

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1280, height: 860 } });
await context.addInitScript(() => { try { sessionStorage.setItem("starboard.setup-wizard", JSON.stringify({ opened: true })); } catch { /* fine */ } });  // the set-up wizard counts as seen (DASH-289)
const page = await context.newPage();
const problems = [];
page.on("pageerror", (e) => problems.push(`${page.url()}: ${e.message}`));
page.on("console", (m) => { if (m.type() === "error" && !/40[04]/.test(m.text())) problems.push(`${page.url()}: ${m.text()}`); });
await page.goto(`${base}/login.html`);
await page.fill("input[type=password]", password);
await page.keyboard.press("Enter");
await page.waitForURL(/dashboard|index/);
const api = (path, opts) => page.evaluate(([p, o]) => api(p, o), [path, opts]);
const open = async (p) => { await page.goto(`${base}/${p}`, { waitUntil: "networkidle" }); await page.waitForTimeout(400); };
// The journeys use every setting, so Advanced settings is on for them (DASH-225: each page opens on its basics).
await page.goto(`${base}/settings-general.html`, { waitUntil: "networkidle" });
await api("/api/config/general", { method: "PUT", body: { settings_advanced: true } });
// They also open every section, so the topic tabs are off for them; TAB-01 below checks the tabs themselves.
await page.evaluate(() => localStorage.setItem("starboard.topic-tabs", "off"));

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

// APP-01: What is new in Reelix, from its changelog (the example server's made-up Reelix: seen at 0.7.0, now 0.7.1,
// with 0.7.2 waiting)
console.log("\n== APP-01 What is new in Reelix");
await open("apps-updates.html");
const rxNotice = page.locator(".app-change", { hasText: "Reelix is updated to 0.7.1" });
check("APP-01", "Apps, Updates shows Reelix's notice after its version went up", await rxNotice.count() === 1);
await open("index.html");
check("APP-01", "and so does the Apps page", await page.locator(".app-change", { hasText: "Reelix is updated to 0.7.1" }).count() === 1);
await page.locator(".app-change").getByRole("button", { name: "What is new in Reelix" }).click();
const rxPanel = page.locator("#side-panel");
await rxPanel.locator("h3").first().waitFor({ timeout: 5000 }).catch(() => {});
const afterHeads = await rxPanel.locator("h3").allTextContents();
check("APP-01", "the notice opens the changes from 0.7.0 to 0.7.1 only", afterHeads.join() === "Version 0.7.1", afterHeads.join());
check("APP-01", "entries are text, with bold and code kept", await rxPanel.locator("li strong", { hasText: "Large libraries:" }).count() === 1);
await page.keyboard.press("Escape");
await open("apps-updates.html");
await page.click("#check-updates");
await page.locator("#updates").getByRole("button", { name: "What is new in Reelix" }).waitFor({ timeout: 5000 }).catch(() => {});
await page.locator("#updates").getByRole("button", { name: "What is new in Reelix" }).click();
await rxPanel.locator("h3").first().waitFor({ timeout: 5000 }).catch(() => {});
const beforeHeads = await rxPanel.locator("h3").allTextContents();
const types = await rxPanel.locator("h4").allTextContents();
check("APP-01", "before updating, What is new lists the waiting 0.7.2", beforeHeads.join() === "Version 0.7.2", beforeHeads.join());
check("APP-01", "under the change types, in order", types.join() === "Added,Fixed", types.join());
await page.keyboard.press("Escape");
await page.locator(".app-change").getByRole("button", { name: "Close the notice about Reelix" }).click();
await open("apps-updates.html");
check("APP-01", "a closed notice stays closed", await page.locator(".app-change").count() === 0);

// FB-01: Snaglist's Send feedback, saved in Starboard
console.log("\n== FB-01 Send feedback (Snaglist)");
const fbBefore = (await api("/api/config")).ux_notes;
await api("/api/config/general", { method: "PUT", body: { ux_notes: true } });
await open("index.html");
// Pages with the side menu open it from Feedback in the menu (DASH-292); Snaglist's own corner button is not shown.
const inMenu = page.locator(".rail__feedback");
await inMenu.waitFor({ state: "visible", timeout: 5000 }).catch(() => {});
check("FB-01", "Feedback is in the side menu", await inMenu.isVisible());
check("FB-01", "no corner button over the page", await page.locator("snag-list button", { hasText: "Send feedback" }).count() === 0);
await inMenu.click().catch(() => {});
const go = page.locator("snag-list button", { hasText: /^Continue$/ });
await go.waitFor({ timeout: 5000 }).catch(() => {});
check("FB-01", "Feedback opens Snaglist", await go.count() === 1);
check("FB-01", "its styles are let in by the content policy", await go.evaluate((b) => !["rgba(0, 0, 0, 0)", "rgb(239, 239, 239)", "rgb(240, 240, 240)"].includes(getComputedStyle(b).backgroundColor)).catch(() => false));
await page.keyboard.press("Escape");
await page.evaluate(() => Snaglist.report(document.querySelector("main"), "other"));
await page.locator("snag-list textarea").first().fill("A made-up journey report");
await page.locator("snag-list button", { hasText: /^Review what is sent$/ }).click();
await page.locator("snag-list button", { hasText: /^Save in Starboard$/ }).click();
await page.locator("snag-list", { hasText: "Saved in Starboard" }).first().waitFor({ timeout: 5000 }).catch(() => {});
const saved = ((await api("/api/ux-notes")).notes || []).filter((n) => n.source === "snaglist" && n.markdown.includes("A made-up journey report"));
check("FB-01", "the report is saved in Starboard", saved.length === 1);
await open("settings-general-logs.html");
check("FB-01", "Settings, General, Logs and feedback lists it", await page.locator("#feedback-list .row").count() >= 1);
for (const n of saved) await api("/api/ux-notes/remove", { method: "POST", body: { id: n.id } });
await api("/api/config/general", { method: "PUT", body: { ux_notes: false } });
await open("index.html");
check("FB-01", "deactivated, it is gone", await page.locator("snag-list").count() === 0 && !(await page.locator(".rail__feedback").isVisible()));
await api("/api/config/general", { method: "PUT", body: { ux_notes: fbBefore } });  // on by default since 0.15.2

// WZ-01: Still to set up, one step at a time, each Starboard step set up inside the slide-out (DASH-289)
console.log("\n== WZ-01 Still to set up in the slide-out");
await open("index.html");
const goThrough = page.getByRole("button", { name: "Go through them" });
await goThrough.waitFor({ timeout: 5000 }).catch(() => {});
await goThrough.click().catch(() => {});
const stepFrame = page.locator("#side-panel .wizard-frame");
await stepFrame.waitFor({ timeout: 5000 }).catch(() => {});
check("WZ-01", "the step's own page is in the slide-out", await stepFrame.count() === 1);
const inside = page.frameLocator("#side-panel .wizard-frame");
await inside.locator("#main").waitFor({ timeout: 8000 }).catch(() => {});
check("WZ-01", "it shows without the menus", await inside.locator("html.in-panel").count() === 1 && !(await inside.locator(".rail").isVisible().catch(() => true)));
check("WZ-01", "no second wizard or Send feedback inside", await inside.locator("#side-panel, snag-list").count() === 0);
const firstStep = await page.locator("#side-panel h3").textContent();
await page.locator("#side-panel .side-panel__foot button", { hasText: /^Skip$/ }).click().catch(() => {});
await page.waitForFunction((t) => document.querySelector("#side-panel h3")?.textContent !== t, firstStep, { timeout: 5000 }).catch(() => {});
check("WZ-01", "Skip goes to the next step", (await page.locator("#side-panel h3").textContent().catch(() => firstStep)) !== firstStep);
await page.keyboard.press("Escape");

// SEC-07: names, categories, descriptions and UX notes that look like code are shown as text
console.log("\n== SEC-07 Text that looks like code");
const before = await api("/api/config");
await api("/api/config/general", { method: "PUT", body: { groups: [...before.groups, `"><svg onload="window.__xss='group'">`], ux_notes: true } });
const added = await api("/api/services", { method: "POST", body: { type: "link", name: XSS, url: "http://journey-xss:8080",
  description: `<script>window.__xss='description'</script>`, group: `"><svg onload="window.__xss='group'">` } });
await api("/api/ux-notes", { method: "POST", body: { what: `<img src=x onerror="window.__xss='note'">`, page: "/index.html", part: XSS } });
for (const p of ["index.html", "apps-services.html", "settings.html", "settings-general-logs.html"]) {
  await open(p);
  if (p === "settings-general-logs.html") {
    await page.locator("#feedback-list .row").first().waitFor({ timeout: 5000 }).catch(() => {});
    check("SEC-07", "a saved report is shown as text", await page.locator("#feedback-list").getByText(`<img src=x onerror="window.__xss='note'">`).count() > 0);
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

// LIB-01 and SRCH-01: the Library from the made-up Reelix, the A to Z list, an item page, and Search (DASH-163, DASH-162)
console.log("\n== LIB-01 The Library");
await open("library-films.html");
await page.locator("#lib-wall .media-card").first().waitFor({ timeout: 10000 }).catch(() => {});
check("LIB-01", "the Films wall shows covers", await page.locator("#lib-wall .media-card").count() >= 20);
check("LIB-01", "with a heading for each letter", await page.locator("#lib-wall h2.wall-letter").count() > 2);
const az = page.locator("nav.az-jump");
check("LIB-01", "the A to Z list has # and A to Z", await az.locator(".az-jump__letter").count() === 27);
check("LIB-01", "letters with nothing are shown but not links", await az.locator('.az-jump__letter[aria-disabled="true"]:not([href])').count() > 0);
const sizes = await az.locator(".az-jump__letter").first().evaluate((a) => [a.offsetWidth, a.offsetHeight]);
check("LIB-01", "letters are 44px targets", sizes[0] >= 44 && sizes[1] >= 44, sizes.join("x"));
check("LIB-01", "the row is one Tab stop", await az.locator('.az-jump__letter[tabindex="0"]').count() === 1);
const target = az.locator(".az-jump__letter[href]").nth(5);
const letter = (await target.textContent()).trim();
await target.click();
await page.waitForTimeout(800);
check("LIB-01", `choosing ${letter} moves focus to its heading`, await page.evaluate(() => document.activeElement.className) === "wall-letter"
  && (await page.evaluate(() => document.activeElement.textContent)).startsWith(letter));
await page.locator("#lib-q").fill("harbour");
await page.waitForTimeout(800);
const found = await page.locator("#lib-wall .media-card__title").allTextContents();
check("LIB-01", "searching the wall keeps only matches", found.length > 0 && found.every((x) => /harbour/i.test(x)), found.join(", "));
await page.locator("#lib-q").fill("");
await page.locator("#lib-sort").selectOption("added");
await page.waitForTimeout(600);
check("LIB-01", "a changed view offers Save this view as default", await page.locator("#lib-save").isVisible());
await page.locator("#lib-save").click();
await page.waitForTimeout(500);
check("LIB-01", "the view is saved for the account", (await api("/api/library/views")).views.films?.sort === "added");
await api("/api/library/views", { method: "DELETE" });
await open("library-tv-show.html?id=2");
check("LIB-01", "an item page has its name as the heading", (await page.locator("h1").textContent()).length > 2);
check("LIB-01", "and its episodes with a status", await page.locator("#panel-episodes .chip").count() > 3);
await page.locator('[role="tab"]', { hasText: "About" }).focus();
check("LIB-01", "About is a tab", await page.locator('[role="tab"]', { hasText: "About" }).count() === 1);
await open("library-tv-show.html?id=8");
await page.locator("#panel-episodes details").first().waitFor({ timeout: 8000 }).catch(() => {});
const seasons = await page.locator("#panel-episodes details").evaluateAll((ds) => ds.map((d) => [d.querySelector("summary").textContent, d.open]));
check("LIB-01", "a series of two seasons shows each season, only the newest open",
  seasons.length === 2 && !seasons[0][1] && seasons[1][1] && /Season 2/.test(seasons[1][0]), JSON.stringify(seasons));
await open("library-books-series.html");
await page.locator("#groups .row__title a, #groups .collection-card__link").first().click();
await page.waitForLoadState("networkidle");
check("LIB-01", "a series opens the wall with only its books", /group=/.test(page.url()) && await page.locator("#lib-wall .media-card").count() > 0);
// DASH-261: narrator pages, and Narrated by on an audiobook's summary links to them.
await open("library-audiobooks-narrators.html");
check("LIB-02", "Narrators lists each narrator", await page.locator("#groups .collection-card__link").count() >= 3);
await open("library-audiobook.html?id=18");
const narratorLink = page.locator('.facts a[href*="by=narrators"]').first();
check("LIB-02", "an audiobook's narrator links to their page", await narratorLink.count() === 1);
await narratorLink.click();
await page.waitForLoadState("networkidle");
check("LIB-02", "a narrator's page shows their recordings", /by=narrators/.test(page.url()) && await page.locator("#lib-wall .media-card").count() > 0
  && /read by this narrator/.test(await page.locator(".page-head__summary").textContent()));

// INF-01: load more as you scroll (DASH-277 with the design system's UX-52): the Films wall loads its next 40 as its end
// comes into view, says so politely and leaves focus alone; Show 40 more moves focus; the button alone with the setting
// or Reduce motion; a pause after three lots so the footer stays in reach; the A to Z list still works.
console.log("\n== INF-01 Load more as you scroll");
const generalBefore = await api("/api/config");
await api("/api/config/general", { method: "PUT", body: { infinite_scroll: true } });
await page.route("**/api/library/wall?*", async (route) => { await new Promise((r) => setTimeout(r, 700)); await route.continue(); });
await open("library-films.html");
await page.locator("#lib-wall .media-card").first().waitFor({ timeout: 10000 }).catch(() => {});
const cards = () => page.locator("#lib-wall .media-card").count();
check("INF-01", "the wall starts with 40", await cards() === 40, String(await cards()));
check("INF-01", "Show 40 more is a real button in the box", await page.locator("#lib-more button", { hasText: "Show 40 more" }).count() === 1);
await page.locator("#lib-q").focus();
await page.locator("#lib-more").evaluate((e) => e.scrollIntoView({ block: "end" }));
await page.waitForTimeout(350);
check("INF-01", "while loading, a line says Loading the next 40 films", (await page.locator("#lib-more .load-more__status").textContent()) === "Loading the next 40 films"
  && await page.locator("#lib-more .load-more__status").isVisible());
await page.waitForTimeout(1500);
check("INF-01", "the end coming into view loads the rest by itself", await cards() === 64, String(await cards()));
check("INF-01", "a screen reader hears how many, politely", (await page.locator("#load-more-status").textContent()) === "24 more films shown"
  && (await page.locator("#load-more-status").getAttribute("role")) === "status");
check("INF-01", "focus stays where it was", await page.evaluate(() => document.activeElement.id) === "lib-q");
check("INF-01", "the loading line goes once loaded", await page.locator("#lib-more .load-more__status").isHidden());
check("INF-01", "with nothing more, the box goes", await page.locator("#lib-more").isHidden());

// The A to Z list: a jump moves focus to its heading, and loading nearby never takes it away.
await open("library-films.html");
await page.locator("#lib-wall .media-card").first().waitFor({ timeout: 10000 }).catch(() => {});
const lastLetter = page.locator("nav.az-jump .az-jump__letter[href]").last();
const lastText = (await lastLetter.textContent()).trim();
await lastLetter.click();
await page.waitForTimeout(2500);
check("INF-01", `the A to Z list still jumps to ${lastText}, with focus on its heading`, await page.evaluate(() => document.activeElement.className) === "wall-letter"
  && (await page.evaluate(() => document.activeElement.textContent)).startsWith(lastText));

// The button alone: the setting asks for it.
await api("/api/config/general", { method: "PUT", body: { infinite_scroll: false } });
await open("library-films.html");
await page.locator("#lib-wall .media-card").first().waitFor({ timeout: 10000 }).catch(() => {});
await page.locator("#lib-more").evaluate((e) => e.scrollIntoView({ block: "end" }));
await page.waitForTimeout(1800);
check("INF-01", "with the setting deactivated, nothing loads by itself", await cards() === 40, String(await cards()));
await page.locator("#lib-more button").focus();
await page.keyboard.press("Enter");
await page.waitForTimeout(1800);
check("INF-01", "Show 40 more by keyboard loads the rest", await cards() === 64, String(await cards()));
const firstNew = await page.locator("#lib-wall li").nth(40).locator("a").first().getAttribute("href");
check("INF-01", "and moves focus to the first new title", await page.evaluate(() => document.activeElement.getAttribute("href")) === firstNew, firstNew);
check("INF-01", "and says how many", (await page.locator("#load-more-status").textContent()) === "24 more films shown");

// The button alone: Reduce motion.
await api("/api/config/general", { method: "PUT", body: { infinite_scroll: true } });
await page.emulateMedia({ reducedMotion: "reduce" });
await open("library-films.html");
await page.locator("#lib-wall .media-card").first().waitFor({ timeout: 10000 }).catch(() => {});
await page.locator("#lib-more").evaluate((e) => e.scrollIntoView({ block: "end" }));
await page.waitForTimeout(1800);
check("INF-01", "with Reduce motion, nothing loads by itself", await cards() === 40, String(await cards()));
await page.emulateMedia({ reducedMotion: "no-preference" });
await page.unroute("**/api/library/wall?*");

// The footer stays in reach: a list that always has more pauses after three lots, and the button carries on.
await open("history.html");
const paused = await page.evaluate(async () => {
  const main = document.querySelector("main");
  const list = document.createElement("ul");
  list.className = "rows";
  const box = document.createElement("div");
  box.className = "load-more";
  box.innerHTML = '<span class="load-more__count"></span><button class="btn" type="button">Show 1 more</button>';
  main.append(list, box);
  let n = 0;
  const handle = window.SharedComponents.loadMore(box, { pageSize: 1, items: () => list.children, load: async () => {
    const li = document.createElement("li");
    li.className = "row";
    li.innerHTML = `<a href="#x${n}">Made-up row ${++n}</a>`;
    list.append(li);
    return 1;
  } });
  box.scrollIntoView({ block: "end" });
  await new Promise((r) => setTimeout(r, 1500));
  const out = { rows: list.children.length, paused: handle.paused, line: box.querySelector(".load-more__status").textContent };
  box.querySelector("button").click();
  await new Promise((r) => setTimeout(r, 300));
  out.afterButton = list.children.length;
  out.focus = document.activeElement.textContent;
  handle.destroy();
  list.remove();
  box.remove();
  return out;
});
check("INF-01", "after three lots in a row it pauses, so the footer stays in reach", paused.rows === 3 && paused.paused, JSON.stringify(paused));
check("INF-01", "and says so on screen", paused.line === "Paused here so you can reach the end of the page", paused.line);
check("INF-01", "Show more carries on, with focus on the first new row", paused.afterButton >= 4 && paused.focus === "Made-up row 4", JSON.stringify(paused));
await api("/api/config/general", { method: "PUT", body: { infinite_scroll: generalBefore.infinite_scroll !== false } });

console.log("\n== SRCH-01 Search");
await open("index.html");
// 12 November 2026: Search left the side menu (phones keep it in their menu); the search box has its own button.
check("SRCH-01", "Search is not in the side menu", await page.locator("nav.rail .rail__search").count() === 0);
const searchBtn = page.locator("#header-search .search-field__btn");
const vw = page.viewportSize()?.width || 1280;
if (vw < 1200) await page.locator("[data-search-open]").click();
check("SRCH-01", "the search box has a Search button you can see", await searchBtn.isVisible());
await page.locator("#header-search-input").fill("harbour");
await searchBtn.click();
await page.waitForURL(/search\.html\?q=harbour/, { timeout: 5000 }).catch(() => {});
check("SRCH-01", "the Search button opens the Search page with the words", /search\.html\?q=harbour/.test(page.url()));
await open("search.html");
await page.locator("#lib-start .lib-kinds a").first().waitFor({ timeout: 8000 }).catch(() => {});
check("SRCH-01", "the Search page opens on the Library, with each kind and its count", await page.locator("#lib-start .lib-kinds a").count() === 6);
await page.locator("#q").fill("harbour");
await page.locator("#lib-found .row").first().waitFor({ timeout: 5000 }).catch(() => {});
check("SRCH-01", "typing searches your library first", await page.locator("#lib-found .row").count() > 0);
await page.locator("#lookup button", { hasText: "Add" }).first().waitFor({ timeout: 10000 }).catch(() => {});
check("SRCH-01", "then Not in your library, with Add", await page.locator("#lookup button", { hasText: "Add" }).count() > 0);
check("SRCH-01", "and Follow for radio", await page.locator("#lookup button", { hasText: "Follow" }).count() > 0);
await page.locator("#lookup button", { hasText: "Add" }).first().click();
await page.locator("#side-panel button[type=submit]:not([disabled])").waitFor({ timeout: 5000 }).catch(() => {});
await page.locator("#side-panel button[type=submit]").click();
await page.locator("#lookup .chip", { hasText: "Added" }).waitFor({ timeout: 5000 }).catch(() => {});
check("SRCH-01", "Add sends it to Reelix and says Added", await page.locator("#lookup .chip", { hasText: "Added" }).count() === 1);
await page.setViewportSize({ width: 375, height: 812 });
await open("index.html");
check("SRCH-01", "on a phone, the header search button stays", await page.locator(".site-header__search-btn[data-search-open]").isVisible());
await page.locator("[data-phone-menu-open]").click();
check("SRCH-01", "and the menu keeps its search field", await page.locator("#phone-search-input").isVisible());
await page.keyboard.press("Escape");
await page.setViewportSize({ width: 1280, height: 860 });

// SRCH-02: Search the sites directly (DASH-213)
console.log("\n== SRCH-02 search the sites");
await open("search-sites.html");
await page.locator("#sites-q").fill("blue planet");
await page.keyboard.press("Enter");
await page.locator("#sites-table tbody tr").first().waitFor({ timeout: 10000 }).catch(() => {});
check("SRCH-02", "a search lists each site's releases in a table", await page.locator("#sites-table tbody tr").count() === 5);
check("SRCH-02", "a site that did not answer is named", await page.locator("#sites-answers .notice", { hasText: "Slow Site" }).count() === 1);
await page.locator("#sites-site").selectOption({ label: "Harbour Usenet 2" });
check("SRCH-02", "the Site filter narrows the table and the count", await page.locator("#sites-table tbody tr").count() === 2 && (await page.locator("#sites-count").textContent()) === "2 of 5");
await page.locator("#sites-table button", { hasText: "Get this one" }).first().click();
await page.locator("#sites-table .chip", { hasText: "Sent to" }).waitFor({ timeout: 5000 }).catch(() => {});
check("SRCH-02", "Get this one sends it and says where", await page.locator("#sites-table .chip", { hasText: "Sent to NZBGet" }).count() === 1);
check("SRCH-02", "focus stays on that row", await page.evaluate(() => document.activeElement?.closest("tr")?.querySelector(".chip") !== null));

// RAD-12: Settings, Radio: a show from a link, and files matched by hand (DASH-212)
console.log("\n== RAD-12 radio library review and a show from a link");
await open("settings-radio-library.html");
await page.locator("#radio-library-h").scrollIntoViewIfNeeded();
await page.locator("button", { hasText: "Match by hand" }).first().waitFor({ timeout: 5000 }).catch(() => {});
check("RAD-12", "files that match no episode are listed by podcast", await page.locator("section[aria-labelledby=radio-library-h] .rows .row").count() >= 2);
await page.locator("button", { hasText: "Match by hand" }).first().click();
await page.locator("#side-panel select").first().waitFor({ timeout: 5000 }).catch(() => {});
await page.locator("#side-panel select").first().selectOption({ index: 1 });
await page.locator("#side-panel button", { hasText: "Match" }).first().click();
await page.locator("#side-panel .chip", { hasText: "Matched" }).waitFor({ timeout: 5000 }).catch(() => {});
check("RAD-12", "Match by hand matches a file to the chosen episode", await page.locator("#side-panel .chip", { hasText: "Matched" }).count() === 1);
await page.keyboard.press("Escape");
await open("settings-radio.html#radio-link-h");
await page.locator("#radio-link").fill("https://www.bbc.co.uk/programmes/example");
await page.locator("#radio-link").press("Enter");
await page.locator("button", { hasText: "Follow this show" }).waitFor({ timeout: 5000 }).catch(() => {});
check("RAD-12", "Look it up shows the show behind the link", await page.locator("#radio-link-title").textContent().catch(() => "") === "The Lighthouse Keepers");
await page.locator("button", { hasText: "Follow this show" }).click();
await page.locator("section[aria-labelledby=radio-link-h] .notice", { hasText: "added" }).waitFor({ timeout: 5000 }).catch(() => {});
check("RAD-12", "Follow this show adds it and says so", await page.locator("section[aria-labelledby=radio-link-h] .notice", { hasText: "added" }).count() === 1);

// LIB-02: music already on disk (DASH-282): the note on Library, Music, the slide-out of matches, then bring them in
console.log("\n== LIB-02 bring in music from disk");
await open("library-music.html");
await page.locator("#lib-import .notice").waitFor({ timeout: 5000 }).catch(() => {});
check("LIB-02", "the note counts the artist folders not in the library", /3 folders on disk/.test(await page.locator("#lib-import").textContent().catch(() => "")));
await page.locator("#lib-import button", { hasText: "Bring them in" }).click();
await page.locator("#side-panel .rows .row").first().waitFor({ timeout: 10000 }).catch(() => {});
const musicRows = page.locator("#side-panel .rows .row");
check("LIB-02", "each artist folder is a row with its matches", await musicRows.count() === 3);
const ticks = await musicRows.locator("input[type=checkbox]").evaluateAll((xs) => xs.map((x) => x.checked));
check("LIB-02", "a sure match is ticked; two artists of one name and no match are not", JSON.stringify(ticks) === JSON.stringify([true, false, false]), JSON.stringify(ticks));
await page.locator("#side-panel button", { hasText: "Bring in the ticked ones" }).click();
await page.locator("#lib-import .notice", { hasText: "Brought in" }).waitFor({ timeout: 10000 }).catch(() => {});
check("LIB-02", "it says what was brought in where the note was", /Brought in 1 artist\b/.test(await page.locator("#lib-import").textContent().catch(() => "")));

// LIB-03: a folder with no match comes in with your own details (DASH-322), as the made-up Reelix has RFX-90's route
console.log("\n== LIB-03 bring in a folder with your own details");
await open("library-films.html");
await page.locator("#lib-import button", { hasText: "Bring them in" }).click();
await page.locator("#side-panel .rows .row").first().waitFor({ timeout: 10000 }).catch(() => {});
const homeRow = page.locator("#side-panel .rows .row", { hasText: "home movies" });
await homeRow.locator("select").selectOption("own");
const ownTitle = homeRow.locator("input[id^=own-title]");
check("LIB-03", "Use my own details opens the fields, ticks the folder and moves focus to the title",
  await ownTitle.isVisible() && await homeRow.locator("input[type=checkbox]").isChecked() && await ownTitle.evaluate((x) => x === document.activeElement));
await ownTitle.fill("Our home movies");
await homeRow.locator("input[id^=own-year]").fill("2004");
await page.locator("#side-panel button", { hasText: "Bring in the ticked ones" }).click();
await page.locator("#lib-import .notice", { hasText: "Brought in" }).waitFor({ timeout: 10000 }).catch(() => {});
check("LIB-03", "the folder with its own details is brought in with the matched ones", /Brought in 3 films\b/.test(await page.locator("#lib-import").textContent().catch(() => "")));

// DL-02: held downloads on Activity, Downloads (DASH-210): Get it now and Remove, with focus kept in the list
console.log("\n== DL-02 held downloads");
await open("downloads.html");
await page.locator("#held > li").first().waitFor({ timeout: 10000 }).catch(() => {});
check("DL-02", "each held release is a row with its state, Get it now and Remove", await page.locator("#held > li").count() === 3
  && await page.locator("#held > li").first().locator(".row__side .chip", { hasText: "Held" }).count() === 1);
check("DL-02", "the soonest is first, in words", (await page.locator("#held > li .row__title").first().textContent()) === "Iron Valley (1982)");
await page.locator("#held > li").first().locator("button", { hasText: "Get it now" }).click();
await page.waitForFunction(() => document.querySelectorAll("#held > li").length === 2, null, { timeout: 5000 }).catch(() => {});
check("DL-02", "Get it now sends it and says where", await page.locator("#held > li").count() === 2 && /Sent to qBittorrent/.test(await page.locator("#toast-stack").textContent().catch(() => "")));
check("DL-02", "focus moves to the next row's first button", await page.evaluate(() => document.activeElement?.closest("#held > li") !== null && /Get it now/.test(document.activeElement.textContent)));
await page.locator("#held > li").first().locator("button", { hasText: "Remove" }).click();
await page.locator("dialog[open]").getByRole("button", { name: "Remove", exact: true }).click();
await page.waitForFunction(() => document.querySelectorAll("#held > li").length === 1, null, { timeout: 5000 }).catch(() => {});
check("DL-02", "Remove asks first, then takes it off the list", await page.locator("#held > li").count() === 1);

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

// RX-01: Reelix's settings (DASH-154): the password is asked, used in a request body only, never kept by the page's
// storage or put in an address; a site is added, tested and removed again; the unlocked page fits a phone.
console.log("\n== RX-01 Settings, Reelix");
const RXPASS = "made-up-reelix-password-41c2";
const addresses = [];
page.on("request", (r) => addresses.push(r.url()));
await open("settings-reelix.html");
await page.getByRole("button", { name: "Show sites to search" }).click();
await page.locator("#rx-password").fill(RXPASS);
await page.locator("dialog button[value=ok]").click();
await page.locator("section[aria-labelledby=rx-indexers-h] .rows").waitFor({ timeout: 15000 });
check("RX-01", "the password opens the list of sites", await page.locator("section[aria-labelledby=rx-indexers-h] .rows > .row").count() >= 1);
await page.getByRole("button", { name: "Add a site to search" }).click();
await page.locator(".rx-pick", { hasText: "EZTV" }).first().click();
await page.locator("#side-panel .side-panel__foot").getByRole("button", { name: "Test" }).waitFor({ timeout: 15000 });
await page.locator("#side-panel .side-panel__foot").getByRole("button", { name: "Test" }).click();
await page.locator("#side-panel .notice").waitFor({ timeout: 15000 });
check("RX-01", "a site's test answers in the form", (await page.locator("#side-panel .notice").textContent())?.includes("The test passed"));
await page.locator("#side-panel .side-panel__foot").getByRole("button", { name: "Save" }).click();
await page.waitForTimeout(1500);
const eztv = page.locator("section[aria-labelledby=rx-indexers-h] .rows > .row", { hasText: "EZTV" });
check("RX-01", "the added site is in the list", await eztv.count() === 1);
check("RX-01", "each row has its state and Edit (settings pattern 8)", await eztv.locator(".chip").count() === 1 && await eztv.getByRole("button", { name: /Edit/ }).count() === 1);
await eztv.getByRole("button", { name: /Edit/ }).click();
await page.locator("#side-panel .side-panel__foot").getByRole("button", { name: "Remove" }).click();
await page.locator("dialog button[value=ok]").click();
await page.waitForTimeout(1500);
check("RX-01", "removed again", await eztv.count() === 0);
await page.setViewportSize({ width: 375, height: 812 });
await page.waitForTimeout(300);
check("RX-01", "the unlocked page does not scroll sideways at 375 wide",
  await page.evaluate(() => document.documentElement.scrollWidth - innerWidth) <= 0);
await page.setViewportSize({ width: 1280, height: 860 });
check("RX-01", "the password is never in an address", !addresses.some((a) => a.includes(RXPASS)));
check("RX-01", "the page keeps no copy in browser storage",
  !(await page.evaluate((p) => JSON.stringify({ ...localStorage, ...sessionStorage }).includes(p) || document.cookie.includes(p), RXPASS)));

// MOVE-01: Apps you already run (DASH-249 to 254, DASH-190 to 192), on the example server's made-up server set up by
// hand: Moving over says what moves where; a qBittorrent ban is said under its field and goes when the next try
// starts; the move opens a dialog with a task list and a result, focus goes to the dialog and back; the review lists
// held sites with Activate, a site Reelix cannot search and the waiting titles; the requests choice; the takeover's
// dialog; Keep it; Clear away; Change your install leaves out the apps from the person's own Compose file.
// MOVE-02: Install apps offers the move itself (DASH-127): once the server is set up, it opens on Apps you already run
// while Starboard finds apps Reelix replaces, with the same steps as Settings, Your install.
console.log("\n== MOVE-02 Moving over from Install apps");
await open("install-apps.html");
const ia = page.locator("section[aria-labelledby=in-takeover-h]");
await ia.locator("[aria-labelledby=tk-reelix-h]").waitFor({ timeout: 15000 });
check("MOVE-02", "Install apps offers to move the apps into Reelix", await ia.getByRole("button", { name: "Move them into Reelix" }).count() === 1);
const iaText = await ia.locator("[aria-labelledby=tk-reelix-h]").textContent();
check("MOVE-02", "it lists the apps it found", ["Prowlarr", "Radarr", "Sonarr", "Seerr"].every((x) => iaText.includes(x)));
check("MOVE-02", "it comes before what is installed", await page.evaluate(() => {
  const a = document.querySelector("section[aria-labelledby=in-takeover-h]"), b = document.getElementById("ia-have-h");
  return !!(a && b && (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING));
}));

console.log("\n== MOVE-01 Apps you already run");
await open("settings-install.html#in-takeover-h");
const tk = page.locator("section[aria-labelledby=in-takeover-h]");
await tk.locator("[aria-labelledby=tk-reelix-h]").waitFor({ timeout: 15000 });
const reelixStep = tk.locator("[aria-labelledby=tk-reelix-h]");
check("MOVE-01", "the qBittorrent user name comes from its settings file", (await reelixStep.textContent()).includes("signs in to qBittorrent as harbour"));
check("MOVE-01", "the qBittorrent password says what it is for and that it is optional",
  (await reelixStep.textContent()).includes("qBittorrent's password (optional)") && (await reelixStep.textContent()).includes("What it is for"));
const [mpw, qpw] = [reelixStep.locator("input[type=password]").nth(0), reelixStep.locator("input[type=password]").nth(1)];
// DASH-129: the old apps needed no password (qBittorrent's allow list), so the step says why Reelix needs it.
check("MOVE-01", "it says the old apps needed no qBittorrent password, and why Reelix does",
  /did not need qBittorrent's password[\s\S]*198\.51\.100\.0\/24[\s\S]*Reelix reaches qBittorrent by its name/.test(await reelixStep.textContent()));
check("MOVE-01", "and that a fixed address still becomes its name without one", (await reelixStep.textContent()).includes("such as Gluetun's IP address, still becomes its name"));
// DASH-128: a key Prowlarr hides and Starboard could not read is asked for by name in the preview, then checked.
await mpw.fill(password);
await reelixStep.getByRole("button", { name: "Show what moves" }).click();
const keyField = reelixStep.getByLabel("NZB Harbour: API key");
await keyField.waitFor({ timeout: 10000 });
check("MOVE-01", "the preview names the hidden key still needed and asks for it", (await reelixStep.textContent()).includes("Prowlarr (1 key still needed), 1 key read from its settings"));
check("MOVE-01", "the key field is a password field, never filled in by the browser",
  await keyField.getAttribute("type") === "password" && await keyField.getAttribute("autocomplete") === "off");
await keyField.fill("made-up-site-key");
await reelixStep.getByRole("button", { name: "Show what moves" }).click();
await reelixStep.getByText("Prowlarr, 1 key read from its settings").waitFor({ timeout: 10000 });
check("MOVE-01", "with the key typed, nothing is still needed", (await reelixStep.textContent()).includes("still needed") === false);
check("MOVE-01", "the typed key is never in browser storage",
  !(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }).includes("made-up-site-key"))));
await mpw.fill(password);
await qpw.fill("banned");
await reelixStep.getByRole("button", { name: "Move them into Reelix" }).click();
await reelixStep.locator(".field-error:not([hidden])").waitFor({ timeout: 10000 });
check("MOVE-01", "a ban after wrong passwords is said under the qBittorrent field, with how to clear it",
  /stopped accepting sign-ins[\s\S]*docker restart qbittorrent/.test(await reelixStep.locator(".field-error:not([hidden])").textContent()));
check("MOVE-01", "focus goes to the qBittorrent field", await qpw.evaluate((n) => n === document.activeElement));
await qpw.fill("right");
await reelixStep.getByRole("button", { name: "Move them into Reelix" }).click();
check("MOVE-01", "the earlier error goes as soon as the next try starts", await reelixStep.locator(".field-error:not([hidden])").count() === 0);
const dlg = page.locator("dialog.task-dialog[open]");
await dlg.waitFor({ timeout: 10000 });
check("MOVE-01", "a dialog opens with a task list", await dlg.locator(".task-list__item").count() >= 4);
check("MOVE-01", "focus is in the dialog", await page.evaluate(() => !!document.activeElement.closest("dialog[open]")));
check("MOVE-01", "it has a working bar and a Close that says the work carries on",
  await dlg.locator("[role=progressbar]").count() === 1 && (await dlg.textContent()).includes("Closing this does not stop it"));
await dlg.getByRole("button", { name: "Close", exact: true }).first().click();
check("MOVE-01", "closed, the page says it is still running", await reelixStep.getByText(/still running/).count() === 1);
await reelixStep.getByRole("button", { name: "Show progress" }).click();
await dlg.locator(".notice").waitFor({ timeout: 30000 });
check("MOVE-01", "the result is in the dialog at the end", (await dlg.locator(".notice").textContent()).includes("Moved into Reelix"));
await dlg.getByRole("button", { name: "Done" }).click();
await tk.locator("[aria-labelledby=tk-review-h]").waitFor({ timeout: 10000 });
const review = tk.locator("[aria-labelledby=tk-review-h]");
check("MOVE-01", "the review lists held sites, each with Activate", await review.getByRole("button", { name: /^Activate (?!all)/ }).count() === 3);
check("MOVE-01", "and a site Reelix cannot search yet", (await review.textContent()).includes("Knaben"));
check("MOVE-01", "and points to the titles waiting for a match", await tk.locator("[aria-labelledby=tk-waiting-h] .row").count() === 3);
await review.locator("input[type=password]").fill(password);
await review.getByRole("button", { name: "Activate all" }).click();
await page.waitForTimeout(1500);
check("MOVE-01", "Activate all leaves no held site", await tk.locator("[aria-labelledby=tk-review-h]").getByRole("button", { name: /^Activate / }).count() === 0);
const rq = tk.locator("[aria-labelledby=tk-requests-h]");
check("MOVE-01", "Seerr beside Reelix: Reelix's own requests is recommended", (await rq.locator(".option-card").first().textContent()).includes("Use Reelix's own requests (recommended)"));
await rq.locator("input[value=seerr]").check();
await page.waitForTimeout(1500);
check("MOVE-01", "Keep Seerr takes Seerr over", (await tk.locator("[aria-labelledby=tk-take-h]").textContent()).includes("Taken overSeerr"));
check("MOVE-01", "with a message for Seerr's users", (await tk.locator("[aria-labelledby=tk-requests-h] .message-to-send").textContent()).includes("keep asking for films and series in Seerr"));
await tk.locator("[aria-labelledby=tk-requests-h] input[value=reelix]").check();
await page.waitForTimeout(1500);
const take = tk.locator("[aria-labelledby=tk-take-h]");
await take.locator("input[type=password]").fill(password);
await take.getByRole("button", { name: "Take over my apps" }).click();
await dlg.waitFor({ timeout: 10000 });
await dlg.locator(".notice").waitFor({ timeout: 30000 });
const takeSteps = await dlg.locator(".task-list").textContent();
check("MOVE-01", "the takeover's dialog lists saving the way back, stopping, copying each app and starting",
  ["Save the way back", "Stop your old apps", "Copy Jellyfin's settings", "Start your apps in Starboard"].every((x) => takeSteps.includes(x)), takeSteps);
await dlg.getByRole("button", { name: "Done" }).click();
await tk.getByRole("button", { name: "Keep it" }).waitFor({ timeout: 15000 });
await tk.locator("input[type=password]").first().fill(password);
await tk.getByRole("button", { name: "Keep it" }).click();
await tk.locator("[aria-labelledby=tk-clear-h]").waitFor({ timeout: 10000 });
check("MOVE-01", "after Keep it, the apps Reelix replaced can be cleared away", await tk.locator("[aria-labelledby=tk-clear-h] input[type=checkbox]").count() >= 3);
await tk.locator("[aria-labelledby=tk-clear-h] input[type=password]").fill(password);
await tk.getByRole("button", { name: "Clear away", exact: true }).click();
await page.locator("dialog[open]").getByRole("button", { name: "Clear away", exact: true }).click();
await dlg.locator(".notice").waitFor({ timeout: 30000 });
check("MOVE-01", "clearing away says what was cleared", (await dlg.locator(".notice").textContent()).includes("Cleared away"));
await dlg.getByRole("button", { name: "Done" }).click();
await page.waitForTimeout(3500);
check("MOVE-01", "and lists the holding folder", (await tk.textContent()).includes("starboard-holding"));
await open("install-apps.html");
check("MOVE-01", "Install apps opens", await page.locator("h1").count() === 1);
await page.locator("#ia-have-h").waitFor({ timeout: 10000 });
check("MOVE-02", "once Starboard runs them, Install apps no longer offers a move", await page.locator("section[aria-labelledby=in-takeover-h]").count() === 0);

// Phone width: no page scrolls sideways
// TAB-01: topic tabs on a long Settings page (12 November 2026): one tab per section, one section shown at a time,
// arrow keys move between tabs, and Sign out is in the side menu (issue #9).
console.log("\n== TAB-01 Topic tabs");
await page.evaluate(() => localStorage.removeItem("starboard.topic-tabs"));
await open("settings-general.html");
const tabs = await page.locator("#topic-tabs [role=tab]").count();
check("TAB-01", "a long Settings page has a tab per topic", tabs >= 4, `${tabs} tabs`);
const shown = () => page.evaluate(() => [...document.querySelectorAll(".settings-sections section.settings-section[role=tabpanel]")].filter((s) => getComputedStyle(s).display !== "none").length);
check("TAB-01", "one topic shows at a time", (await shown()) === 1);
await page.locator("#topic-tabs [role=tab]").nth(1).click();
check("TAB-01", "choosing a tab shows its topic", (await page.locator("#topic-tabs [role=tab]").nth(1).getAttribute("aria-selected")) === "true" && (await shown()) === 1);
await page.keyboard.press("ArrowRight");
check("TAB-01", "the arrow keys move to the next tab", (await page.locator("#topic-tabs [role=tab]").nth(2).getAttribute("aria-selected")) === "true");
check("TAB-01", "Advanced settings is a switch in the heading", (await page.locator(".page-head #advanced-switch").count()) === 1);
check("TAB-01", "Sign out is in the side menu", (await page.locator(".rail [data-sign-out]").count()) === 1);
await page.evaluate(() => localStorage.setItem("starboard.topic-tabs", "off"));

// DASH-104: the version at the bottom of the side menu; the footer's links in the design system's order, with
// "Upgrade available" when a newer release is out, and TheMightyTRexUK on the right; no footer on Sign in.
console.log("\n== FOOT Footer and version");
await open("index.html");
check("FOOT-01", "the version is plain text at the bottom of the side menu",
  /^(Starboard version )?v\d+\.\d+\.\d+$/.test((await page.locator(".rail__end .rail__version").textContent()).trim()));
const footLinks = await page.locator(".site-footer .site-footer__links a").evaluateAll((as) => as.map((a) => a.childNodes[0].textContent.trim()));
check("FOOT-01", "the footer links are Help, Release notes, GitHub repository, About and updates",
  footLinks.join("|") === "Help|Release notes|GitHub repository|About and updates", footLinks.join(", "));
const maker = page.locator(".site-footer > a.site-footer__maker");
check("FOOT-01", "TheMightyTRexUK is on the right, one link to the GitHub profile, with the dinosaur mark",
  (await maker.count()) === 1 && (await maker.getAttribute("href")) === "https://github.com/TheMightyTRex"
  && /TheMightyTRexUK/.test(await maker.innerText()) && (await maker.locator("svg.maker-mark").count()) === 1);
const footBox = await page.locator(".site-footer").boundingBox(), mainBox = await page.locator("main").boundingBox();
check("FOOT-01", "the footer is under the page's own part", !!(footBox && mainBox && footBox.y >= mainBox.y + mainBox.height - 1));
const upgradeText = (latest) => page.evaluate((l) => {
  document.querySelector(".site-footer")?.remove();
  showVersion("0.16.5", "TheMightyTRex/starboard", l);
  return document.querySelector("[data-footer-updates]").textContent;
}, latest);
check("FOOT-02", "About and updates says Upgrade available when a newer release is out", /About and updates, ?Upgrade available/.test(await upgradeText("99.0.0")));
check("FOOT-02", "and says nothing more when Starboard is up to date", (await upgradeText("0.16.5")).trim() === "About and updates");
const signedOut = await (await browser.newContext()).newPage();
await signedOut.goto(`${base}/login.html`, { waitUntil: "networkidle" });
await signedOut.waitForTimeout(500);
check("FOOT-03", "Sign in has no footer", (await signedOut.locator(".site-footer").count()) === 0);
await signedOut.context().close();

// DASH-315: a small picture of each design in Settings, General, Default design and in Display's Design list.
console.log("\n== DES Design pictures");
await open("settings-general-appearance.html");
const defaultPics = await page.locator(".option-card:has(input[name=design]) .design-picture").evaluateAll((ps) => ps.map((p) => ({
  key: p.dataset.design, hidden: p.getAttribute("aria-hidden") === "true", drawn: p.querySelectorAll("svg rect, svg circle").length })));
check("DES-01", "Default design has a picture for each of the 5 designs", defaultPics.map((p) => p.key).join(",") === "health,tiles,shelf,command,board", JSON.stringify(defaultPics));
check("DES-01", "each picture is drawn and hidden from screen readers (the words say what it is)", defaultPics.every((p) => p.hidden && p.drawn > 5));
await page.click("[data-display-toggle]");
await page.waitForTimeout(500);
const panelPics = await page.locator("#side-panel .option-card:has(input[name=design]) .design-picture").evaluateAll((ps) => ps.map((p) => p.dataset.design));
const serverDefault = await page.evaluate(() => document.documentElement.dataset.design);
check("DES-02", "Display's Design list has a picture for each choice", panelPics.length === 6, panelPics.join(","));
check("DES-02", "Use the dashboard's default shows the default design's picture", panelPics[0] === serverDefault, `${panelPics[0]} and ${serverDefault}`);
await page.keyboard.press("Escape");

// DASH-228: Dispatcharr set up from Starboard, against the made-up Dispatcharr and Jellyfin of the example server: the
// IPTV source with its own checks, then Jellyfin's tuner and guide, then channels made from the playlist.
console.log("\n== DISP Dispatcharr");
await open("settings-dispatcharr.html");
await page.locator("#dp-source-h").waitFor({ timeout: 10000 });
check("DISP-01", "Settings, Apps, Dispatcharr shows the source, channels and Jellyfin",
  (await page.locator("#dp-source-h, #dp-channels-h, #dp-jellyfin-h").count()) === 3);
check("DISP-01", "a playlist address asks for no user name", await page.locator("#dp-user").isHidden());
await page.check("#dp-kind-xc");
check("DISP-01", "Xtream Codes asks for a user name and password", await page.locator("#dp-user").isVisible() && await page.locator("#dp-pass").isVisible());
await page.click("#dp-save");
check("DISP-02", "saving Xtream Codes without a user name says so at the field, and puts focus there",
  (await page.locator("#dp-user").getAttribute("aria-invalid")) === "true" && await page.evaluate(() => document.activeElement.id) === "dp-user");
await page.check("#dp-kind-m3u");
await page.fill("#dp-guide", "https://iptv.example/xmltv.php");
await page.click("#dp-save");
await page.locator("#dp-jellyfin-h").locator("xpath=ancestor::section").getByText("Jellyfin has Dispatcharr").waitFor({ timeout: 10000 });
check("DISP-03", "saving adds Dispatcharr to Jellyfin as a tuner with its guide", true);
check("DISP-03", "what was done is said beside Save, and focus stays on Save",
  /Jellyfin: added Dispatcharr/.test(await page.locator("#dp-source-h").locator("xpath=ancestor::section").innerText())
  && await page.evaluate(() => document.activeElement.id) === "dp-save");
await page.click("#dp-make");
await page.locator("#dp-make").waitFor({ state: "detached", timeout: 10000 });
const made = await page.locator("#dp-channels-h").locator("xpath=ancestor::section").innerText();
check("DISP-04", "Make channels makes a channel for each stream and says so", /making 48 channels/.test(made) && /Channels in Dispatcharr\s+48/.test(made), made);
check("DISP-04", "focus goes to the Channels heading, not the top of the page", await page.evaluate(() => document.activeElement.id) === "dp-channels-h");

// DASH-389: General's sections are pages on the level 2 menu; Style is Appearance, with the accessibility options;
// old addresses go to the part's new page.
console.log("\n== MENU2 General on the level 2 menu");
const level2 = async (p) => { await open(p); return (await page.locator(".site-header__tabs .menu-tabs a").evaluateAll((as) => as.map((a) => a.textContent.trim()))).join("|"); };
const headings = () => page.locator("main .settings-sections h2").evaluateAll((hs) => hs.map((h) => h.textContent.trim()).join("|"));
check("MENU2-01", "General has Names and apps, Appearance, Pages and lists, Discover rows, Download hours, Logs and feedback",
  (await level2("settings-general.html")) === "Names and apps|Appearance|Pages and lists|Discover rows|Download hours|Logs and feedback", await level2("settings-general.html"));
check("MENU2-01", "each page shows only its own parts", (await headings()) === "Names|Categories|App cards|Set-up guide", await headings());
await open("settings-general-appearance.html");
check("MENU2-02", "Appearance holds style and colours, the default design and accessibility", (await headings()) === "Style and colours|Default design|Accessibility", await headings());
check("MENU2-02", "and Style is called Appearance on the menu", (await page.locator(".site-header__tabs [aria-current=page]").textContent()).trim() === "Appearance");
await page.locator("#ap-pref-underline").check();
await page.waitForTimeout(300);
check("MENU2-02", "an accessibility option applies at once", await page.evaluate(() => document.documentElement.classList.contains("pref-underline")));
await page.click("[data-display-toggle]");
await page.waitForTimeout(400);
check("MENU2-02", "Display shows the same choice", await page.locator("#side-panel #pref-underline").isChecked());
await page.locator("#side-panel #pref-underline").uncheck();
await page.keyboard.press("Escape");
await page.waitForTimeout(300);
check("MENU2-02", "and a change in Display shows on the page", !(await page.locator("#ap-pref-underline").isChecked()));
for (const [from, to] of [["settings-general.html#download-hours", "/settings-general-hours.html#download-hours"],
  ["settings-general.html#gn-style-h", "/settings-general-appearance.html#gn-style-h"], ["settings-general.html#logs", "/settings-general-logs.html#logs"],
  ["settings-general.html?discover=films#discover-rows-s", "/settings-general-discover.html#dr-films"]]) {
  await open("index.html");
  await open(from);
  const at = await page.evaluate(() => location.pathname + location.search + location.hash);
  check("MENU2-03", `the old address ${from} opens its new page`, at === to, at);
}
await open("settings-general-lists.html");
check("MENU2-03", "Pages and lists has Long lists", await page.locator("#gn-scroll-h").count() === 1);

// DASH-390: Downloads has VPN, Usenet and Download hours on the level 2 menu; Download hours is the same field as
// General's, so a change in one shows in the other.
console.log("\n== MENU2 Downloads on the level 2 menu");
check("MENU2-04", "Downloads has VPN, Usenet and Download hours", (await level2("settings-downloads.html")) === "VPN|Usenet|Download hours");
check("MENU2-04", "VPN shows only the VPN", (await headings()) === "VPN", await headings());
await open("settings-downloads-hours.html");
const hoursWas = await page.locator("[aria-labelledby=dh-on-l]").isChecked();
await page.locator("[aria-labelledby=dh-on-l]").click();
await page.waitForTimeout(500);
check("MENU2-04", "Download hours on Downloads is the switch itself and saves", (await api("/api/config")).download_hours.enabled === !hoursWas);
await open("settings-general-hours.html");
check("MENU2-04", "and General, Download hours shows the same", (await page.locator("[aria-labelledby=dh-on-l]").isChecked()) === !hoursWas);
await api("/api/config/general", { method: "PUT", body: { download_hours: { enabled: hoursWas } } });
await open("index.html");
await open("settings-downloads.html#dl-hours-h");
check("MENU2-04", "the old address of Download hours on Downloads opens its page", await page.evaluate(() => location.pathname) === "/settings-downloads-hours.html");

// DASH-391: Radio, Performance and Security have their parts as pages on the level 2 menu; old anchors go there;
// a page made only of parts under Advanced settings shows them anyway.
console.log("\n== MENU2 Radio, Performance and Security on the level 2 menu");
check("MENU2-05", "Radio has Sources, Add a show from a link, Your podcast library, Station logos",
  (await level2("settings-radio.html")) === "Sources|Add a show from a link|Your podcast library|Station logos", await level2("settings-radio.html"));
check("MENU2-05", "Sources shows only the sources", (await headings()) === "Sources", await headings());
check("MENU2-05", "Performance has Preset and Pictures", (await level2("settings-performance.html")) === "Preset|Pictures");
check("MENU2-05", "Pictures has the picture cache and its Clear", (await level2("settings-performance-pictures.html")) && (await headings()) === "Pictures|Clear", await headings());
check("MENU2-05", "Security has Who can open the dashboard, Password, API keys, Sign out everywhere",
  (await level2("settings-security.html")) === "Who can open the dashboard|Password|API keys|Sign out everywhere", await level2("settings-security.html"));
for (const [from, to] of [["settings-radio.html#radio-logos-h", "/settings-radio-logos.html"], ["settings-performance.html#pf-pictures-h", "/settings-performance-pictures.html"],
  ["settings-security.html#sc-keys-h", "/settings-security-keys.html"], ["settings-security.html#sc-pw-h", "/settings-security-password.html"]]) {
  await open("index.html");
  await open(from);
  check("MENU2-06", `the old address ${from} opens its new page`, await page.evaluate(() => location.pathname) === to);
}
await api("/api/config/general", { method: "PUT", body: { settings_advanced: false } });
await open("settings-security-sessions.html");
check("MENU2-06", "Sign out everywhere shows its parts with Advanced settings inactive",
  await page.locator("#sc-ses-h").isVisible() && await page.locator("#sc-danger-h").isVisible());
await api("/api/config/general", { method: "PUT", body: { settings_advanced: true } });

// DASH-388: the own style's colours, from the design system's palettes, on the Styles plug-in's page; a plug-in style
// in use, then Reset style, comes back to the own style in those colours.
console.log("\n== OWN Own style colours");
await open("settings-plugin.html?id=styles");
const ownCards = await page.locator("input[name=pl-own-colours]").evaluateAll((rs) => rs.map((r) => r.value));
check("OWN-01", "the own style offers Teal and the design system's five palettes", ownCards.join(",") === "teal,indigo,forest,plum,ember,graphite", ownCards.join(","));
await page.locator("input[name=pl-own-colours][value=forest]").check();
await page.waitForTimeout(500);
check("OWN-01", "choosing Forest saves it for the server and uses its colours here",
  (await api("/api/config")).own_colours === "forest" && await page.evaluate(() => document.documentElement.dataset.palette) === "forest"
  && (await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--color-accent").trim())) === "#2f6b3a");
check("OWN-01", "the saved note says so beside the choice", /Saved/.test(await page.locator("#pl-own-colours-saved").textContent()));
await page.locator(".style-gallery button", { hasText: "Use this style" }).first().click();
await page.waitForTimeout(300);
check("OWN-02", "a plug-in style in use leaves the own colours out", await page.evaluate(() => !document.documentElement.dataset.palette && !!document.documentElement.dataset.style));
await page.evaluate(() => resetStyle());
await page.waitForTimeout(300);
check("OWN-02", "Reset style goes back to the own style in Forest", await page.evaluate(() => !document.documentElement.dataset.style && document.documentElement.dataset.palette === "forest"));
check("OWN-02", "and the own style's card says Forest", /Forest colours/.test(await page.locator(".style-gallery__item").first().innerText()));
await api("/api/config/general", { method: "PUT", body: { own_colours: "teal" } });
await page.evaluate(() => setOwnColours("teal"));
// What is new on a plug-in's State (DASH-393): the example Styles plug-in was just updated from 1.0.0 to 1.1.0.
console.log("\n== WN What is new in a plug-in");
await open("settings-plugin.html?id=styles");
const wn = page.locator("#pl-styles-whats-new");
await wn.waitFor({ timeout: 10000 }).catch(() => {});
const wnText = (await wn.count()) ? await wn.innerText() : "";
check("WN-01", "an updated plug-in's State shows What is new in its version, and what it was before",
  /What is new in 1\.1\.0/.test(wnText) && /Updated from 1\.0\.0/.test(wnText), wnText.slice(0, 120));
check("WN-01", "it is inside the State section, after the version line",
  await page.evaluate(() => !!document.querySelector("#pl-styles-whats-new")?.closest("section")?.querySelector("#pl-styles-state-h")));
check("WN-01", "it is said politely", (await wn.getAttribute("role")) === "status");
check("WN-02", "each type of change shows its first line, with how many more",
  /Added: Three new styles: Sunset/.test(wnText) && /\(and 1 more\)/.test(wnText) && /Changed: /.test(wnText) && /Fixed: /.test(wnText), wnText);
check("WN-02", "the older version's changes are left out", !/The first ten styles/.test(wnText));
await wn.getByText(/^All 5 changes$/).click();
check("WN-03", "All changes opens the rest", await wn.getByText("A style chosen on a phone is kept after Starboard restarts.").isVisible());
await page.setViewportSize({ width: 375, height: 812 });
await open("settings-plugin.html?id=styles");
check("WN-04", "What is new fits at phone width", await page.evaluate(() => document.documentElement.scrollWidth - innerWidth) <= 0
  && await page.locator("#pl-styles-whats-new").isVisible());
await page.setViewportSize({ width: 1280, height: 860 });
await open("settings-plugin.html?id=styles");
await page.locator("#pl-styles-whats-new").getByRole("button", { name: /^Got it/ }).click();
await page.locator("#pl-styles-whats-new").waitFor({ state: "detached", timeout: 5000 }).catch(() => {});
await page.waitForTimeout(200);
check("WN-05", "Got it hides it and puts focus on the State heading",
  !(await page.locator("#pl-styles-whats-new").count()) && await page.evaluate(() => document.activeElement.id) === "pl-styles-state-h");
await open("settings-plugin.html?id=styles");
check("WN-05", "Got it is kept on the server: it is not shown again", !(await page.locator("#pl-styles-whats-new").count()));
// DASH-395: a row for each genre in Settings' Discover rows, unticked until ticked, then on the Discover page as a
// row (fetched when shown) and no longer as a chip. DASH-396: each area is its own section on Discover rows.
console.log("\n== GEN Genre rows");
await api("/api/library/discover-layout?tab=films", { method: "DELETE" });
await open("settings-general-discover.html#dr-films");
await page.locator("#dr-films-list").waitFor({ timeout: 10000 });
const genreTicks = await page.locator("#dr-films-list li").evaluateAll((ls) => ls.map((l) => ({
  id: l.dataset.value, on: l.querySelector("input").checked, words: l.querySelector("label").textContent })));
check("GEN-01", "Films lists the genres after the standard rows, unticked", genreTicks.length > 15
  && genreTicks.slice(0, 5).every((r) => r.on && !r.id.startsWith("genre/")) && genreTicks.slice(5).every((r) => !r.on && r.id.startsWith("genre/")),
  JSON.stringify(genreTicks.slice(0, 7)));
check("GEN-01", "in sentence case, and said to be a genre", genreTicks.some((r) => r.words === "Science fiction (genre)"), genreTicks.map((r) => r.words).join(", "));
await page.check("#dr-films-row-genre-movie-35");
await page.waitForTimeout(600);
await page.check("#dr-films-row-genre-movie-878");
await page.waitForTimeout(600);
check("GEN-02", "ticking a genre saves it and says Saved, with focus left on the tick",
  /Saved/.test(await page.locator("#dr-films-saved").textContent()) && await page.evaluate(() => document.activeElement.id) === "dr-films-row-genre-movie-878");
await open("discover-films.html");
await page.locator(".discover-row h2", { hasText: /^Comedy$/ }).waitFor({ timeout: 10000 });
const heads = await page.locator("#discover-rows > .discover-row h2").allTextContents();
check("GEN-03", "Discover, Films shows the two ticked genres as rows, after the standard rows", heads.slice(-2).join(",") === "Comedy,Science fiction", heads.join(", "));
check("GEN-03", "and they are no longer chips", (await page.locator(".discover-genres .filter-chip", { hasText: /^(Comedy|Science fiction)$/ }).count()) === 0
  && (await page.locator(".discover-genres .filter-chip", { hasText: /^Western$/ }).count()) === 1);
await page.locator(".discover-row", { hasText: "Science fiction" }).scrollIntoViewIfNeeded();
await page.locator(".discover-row", { hasText: "Science fiction" }).locator(".discover-card").first().waitFor({ timeout: 10000 });
check("GEN-03", "a genre row loads its covers when it comes into view", (await page.locator(".discover-row", { hasText: "Science fiction" }).locator(".discover-card").count()) > 0);
check("GEN-04", "the TV list has its own genres, all unticked",
  (await api("/api/library/discover-layout?tab=tv")).rows.filter((r) => r.genre).every((r) => !r.shown));
await api("/api/library/discover-layout?tab=films", { method: "DELETE" });

// DASH-396 (owner, 13 November 2026: "Do you have the same options for TV, books, audio books and Radio - might need a
// separate section for each in the settings"): Discover rows has a section per area; with topic tabs, only the area
// shown asks Reelix; each Discover page opens its own section; Radio offers its shared genres as rows.
console.log("\n== DR Discover rows by area");
await open("settings-general-discover.html");
check("DR-01", "Discover rows has a section for each area, in the Discover menu's order",
  (await headings()) === "Films|TV|Music|Radio|Books|Audiobooks", await headings());
await page.evaluate(() => localStorage.removeItem("starboard.topic-tabs"));
const asked = [];
const askedFor = (r) => { const m = r.url().match(/discover-layout\?tab=(\w+)/); if (m) asked.push(m[1]); };
page.on("request", askedFor);
await open("discover-tv.html");
await page.click("text=Change these rows");
await page.locator("#dr-tv-list").waitFor({ timeout: 10000 });
await page.waitForTimeout(500);
check("DR-02", "Discover, TV's Change these rows opens TV's section, with its tab chosen",
  await page.evaluate(() => location.pathname + location.hash) === "/settings-general-discover.html#dr-tv"
  && (await page.locator("#topic-tabs [aria-selected=true]").textContent()) === "TV" && await page.locator("#dr-films").isHidden(),
  await page.evaluate(() => location.pathname + location.hash));
check("DR-02", "and only TV's rows were asked for", asked.join(",") === "tv", asked.join(","));
await page.click("#topic-tabs [role=tab] >> text=Radio");
await page.locator("#dr-radio-list").waitFor({ timeout: 10000 });
check("DR-02", "choosing the Radio tab asks for Radio's rows then", asked.join(",") === "tv,radio", asked.join(","));
page.off("request", askedFor);
await page.evaluate(() => localStorage.setItem("starboard.topic-tabs", "off"));
for (const [from, to] of [["settings-general-lists.html?discover=radio#discover-rows-s", "/settings-general-discover.html#dr-radio"],
  ["settings-general-lists.html#discover-rows-s", "/settings-general-discover.html"], ["settings-general-discover.html?discover=books", "/settings-general-discover.html#dr-books"]]) {
  await open("index.html");
  await open(from);
  const at = await page.evaluate(() => location.pathname + location.search + location.hash);
  check("DR-03", `the old address ${from} opens its area`, at === to, at);
}
await api("/api/library/discover-layout?tab=radio", { method: "DELETE" });
await open("settings-general-discover.html#dr-radio");
await page.locator("#dr-radio-list").scrollIntoViewIfNeeded();
await page.locator("#dr-radio-list").waitFor({ timeout: 10000 });
const radioTicks = await page.locator("#dr-radio-list li").evaluateAll((ls) => ls.map((l) => ({ id: l.dataset.value, on: l.querySelector("input").checked })));
check("DR-04", "Radio lists its shared genres after its rows, unticked", radioTicks.length > 4
  && radioTicks.filter((r) => r.id.startsWith("all-genre-")).every((r) => !r.on) && radioTicks.filter((r) => !r.id.startsWith("all-genre-")).every((r) => r.on),
  JSON.stringify(radioTicks));
await page.check("#dr-radio-row-all-genre-comedy");
await page.waitForTimeout(600);
check("DR-04", "ticking Comedy saves it", /Saved/.test(await page.locator("#dr-radio-saved").textContent()));
await open("discover-radio.html");
const radioHeads = await page.locator("#discover-rows > .discover-row h2").allTextContents();
check("DR-05", "Discover, Radio shows Comedy as a row, and not as a chip", radioHeads.includes("Comedy")
  && (await page.locator(".discover-genres .filter-chip", { hasText: /^Comedy$/ }).count()) === 0
  && (await page.locator(".discover-genres .filter-chip", { hasText: /^Drama$/ }).count()) === 1, radioHeads.join(", "));
await page.locator(".discover-row", { hasText: "Comedy" }).scrollIntoViewIfNeeded();
await page.locator(".discover-row", { hasText: "Comedy" }).locator(".discover-card").first().waitFor({ timeout: 10000 });
check("DR-05", "the Comedy row loads its shows when it comes into view", (await page.locator(".discover-row", { hasText: "Comedy" }).locator(".discover-card").count()) > 0);
await open("settings-general-discover.html#dr-radio");
await page.locator("#dr-radio-reset").scrollIntoViewIfNeeded();
await page.click("#dr-radio-reset");
await page.waitForTimeout(600);
check("DR-05", "Put back the standard rows unticks Comedy again and says so",
  /Standard rows put back/.test(await page.locator("#dr-radio-saved").textContent()) && !(await page.locator("#dr-radio-row-all-genre-comedy").isChecked()));
const books = await api("/api/library/discover-layout?tab=books");
check("DR-06", "Books has Trending and Reelix's nine subjects, all standard rows that show",
  books.rows.length === 10 && books.rows.every((r) => r.shown && !r.genre), books.rows.map((r) => r.id).join(","));
check("DR-06", "Music has no genre rows (Reelix has no music genres)", (await api("/api/library/discover-layout?tab=music")).rows.every((r) => !r.genre));

// API keys that read and manage, with scopes (DASH-274): the form offers both, the key works on /api/v1 with only
// its scopes, and a read key cannot change anything.
await open("settings-security-keys.html");
await page.getByRole("button", { name: "Make a key" }).first().click();
await page.waitForTimeout(400);
const rights = await page.locator("#key-right option").allTextContents();
check("API-01", "Make a key asks what it may do: Read only or Read and manage", rights.join("|") === "Read only|Read and manage", rights.join("|"));
const scopeNames = await page.locator("#key-scopes .check strong").allTextContents();
check("API-01", "and what it may see, one tick for each area", scopeNames.join("|") === "Apps|Downloads|Media|Library|Requests|System", scopeNames.join("|"));
await page.fill("#key-name", "Journey manager");
await page.selectOption("#key-right", "manage");
await page.check("#key-scope-downloads");
await page.fill("#key-password", password);
await page.locator("#key-password").press("Enter");
await page.locator("#key-made").waitFor({ timeout: 5000 });
const keyMade = await page.locator("#key-made").inputValue();
check("API-02", "the key says it may manage", /^sb_manage_[0-9a-f]{6}_/.test(keyMade), keyMade.slice(0, 18));
const keyCall = (path, method = "GET", body) => page.evaluate(async ([p, m, k, b]) => {
  const r = await fetch(p, { method: m, headers: { Authorization: `Bearer ${k}`, "Content-Type": "application/json" }, body: b ? JSON.stringify(b) : undefined });
  return { status: r.status, body: await r.json().catch(() => null) };
}, [path, method, keyMade, body]);
const keyMe = await keyCall("/api/v1/me");
check("API-02", "/api/v1/me shows its right and scope", keyMe.body?.right === "manage" && keyMe.body?.scopes.join() === "downloads", JSON.stringify(keyMe.body));
check("API-02", "it reads download hours", (await keyCall("/api/v1/download-hours")).status === 200);
check("API-02", "it cannot read outside its scope", (await keyCall("/api/v1/apps")).status === 404);
const acted = await keyCall("/api/v1/download-hours", "POST", { action: "follow" });
check("API-02", "it can follow the download hours again", [200, 400].includes(acted.status), JSON.stringify(acted.body).slice(0, 120));
await page.keyboard.press("Escape");
await page.waitForTimeout(400);
check("API-03", "the list says the key reads and manages", /read and manage/.test(await page.locator("#security-sections .row", { hasText: "Journey manager" }).textContent()));
const listed = await api("/api/keys");
for (const k of listed.keys.filter((k) => k.name === "Journey manager")) await api(`/api/keys/${k.id}`, { method: "DELETE" });

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
