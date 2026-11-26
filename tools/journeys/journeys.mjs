// Browser journeys against the example-data server (tools/journeys.sh runs this in the Playwright image).
// TEST-PLAN USE-02, SEC-05, SEC-07, SEC-12 and SEC-13, plus no sideways scrolling at phone width on every page.
// Prints PASS or FAIL for each check and exits 1 if any failed. Everything it adds, it removes again.
import { chromium } from "playwright";
import fs from "fs";

const base = process.env.BASE || "http://127.0.0.1:18792";
const password = fs.readFileSync(process.env.PASSWORD_FILE, "utf8").trim();
const PAGES = ["index.html", "apps-services.html", "apps-updates.html", "search.html", "downloads.html", "downloads-requests.html",
  "upcoming.html", "system.html", "system-storage.html", "system-disks.html", "system-monitor.html", "system-busy.html", "system-network.html",
  "system-logs.html", "system-backup.html", "settings.html", "settings-general.html", "settings-security.html",
  "settings-general-alerts.html", "settings-updates.html", "settings-releases.html", "settings-restore.html", "settings-general-performance.html", "settings-jellyfin.html",
  "settings-audiobookshelf.html", "copy-settings.html", "install-apps.html", "setup-guide.html", "bring-in.html", "upgrade.html", "settings-install.html",
  // The Library, from the made-up Reelix (DASH-163)
  "library-tv.html", "library-tv-networks.html", "library-films.html", "library-films-collections.html", "library-music.html",
  "library-radio.html", "library-radio-stations.html", "library-books.html", "library-books-series.html",
  "library-books-authors.html", "library-audiobooks.html", "library-audiobooks-series.html", "library-audiobooks-authors.html",
  "library-audiobooks-narrators.html",
  "library-film.html?id=3", "library-tv-show.html?id=8", "library-artist.html?id=1", "library-radio-show.html?id=1",
  "library-book.html?id=4", "library-audiobook.html?id=6",
  "discover-films.html", "discover-radio.html", "downloads-finished.html", "wanted-films.html", "wanted-music.html", "wanted-audiobooks.html", "history.html", "history-apps.html", "settings-reelix.html",
  "search-sites.html", "settings-radio.html",  // Search the sites (DASH-213), Settings, Radio (DASH-212)
  "settings-dispatcharr.html",  // Settings, Apps, Dispatcharr (DASH-228)
  // General's level 2 pages (DASH-389)
  "settings-general-appearance.html", "settings-general-lists.html", "settings-general-hours.html", "settings-general-logs.html",
  "settings-general-discover.html", "discover-tv.html", "discover-books.html",  // Discover rows, a section per area (DASH-396)
  // Downloads' level 2 pages (DASH-390)
  "settings-downloads.html", "settings-downloads-usenet.html", "settings-downloads-hours.html",
  // Radio's, Performance's and Security's level 2 pages (DASH-391)
  "settings-radio-link.html", "settings-radio-library.html", "settings-radio-logos.html", "settings-general-pictures.html",
  "settings-security-password.html", "settings-security-signin.html", "settings-security-keys.html", "settings-security-sessions.html",
  "settings-plugins.html", "settings-plugins-catalogue.html", "settings-plugin.html?id=direct-play", "settings-plugin.html?id=jellyfin"];  // with the set-up's Audio description offer (DASH-399)
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
// LIB-04: Play in Jellyfin (DASH-480): a real link styled as a 44px button on the Films wall, a film's page and each
// episode row, to Jellyfin's address for browsers (never the address Starboard uses), opening a new tab, with the item
// in its name; nothing where Jellyfin does not have it, and words saying why; with no address, where to add it.
console.log("\n== LIB-04 Play in Jellyfin");
await open("library-films.html");
await page.locator("#lib-wall .play-link").first().waitFor({ timeout: 10000 }).catch(() => {});
const plays = page.locator("#lib-wall .play-link");
check("LIB-04", "films Jellyfin has show Play on the wall", await plays.count() > 5);
const first = await plays.first().evaluate((a) => ({ tag: a.tagName, href: a.getAttribute("href"), target: a.target, rel: a.rel,
  name: a.textContent.replace(/\s+/g, " ").trim(), h: a.offsetHeight, w: a.offsetWidth,
  title: a.closest(".media-card").querySelector(".media-card__title").textContent.trim() }));
check("LIB-04", "Play is a link to Jellyfin's item page at its address for browsers",
  first.tag === "A" && /^http:\/\/192\.168\.1\.20:8096\/web\/#\/details\?id=[0-9a-f]{32}$/.test(first.href), first.href);
check("LIB-04", "it opens a new tab, safely", first.target === "_blank" && /noopener/.test(first.rel) && /noreferrer/.test(first.rel));
check("LIB-04", "its name says what, where and the new tab", first.name === `Play ${first.title} in Jellyfin (opens in a new tab)`, first.name);
check("LIB-04", "it is a 44px target", first.h >= 44 && first.w >= 44, `${first.w}x${first.h}`);
check("LIB-04", "a film Jellyfin does not have has no Play",
  await page.locator("#lib-wall .media-card").filter({ hasText: "31 Planets" }).locator(".play-link").count() === 0);
// Reading order: the title link, then its Play link.
await page.locator("#lib-wall .media-card__title a").first().focus();
await page.keyboard.press("Tab");
check("LIB-04", "Play follows the title in the Tab order",
  await page.evaluate(() => document.activeElement.classList.contains("play-link")));
check("LIB-04", "with a visible focus outline", await page.evaluate(() => getComputedStyle(document.activeElement).outlineStyle !== "none"));
// The made-up Jellyfin address answers with a stand-in page, so the new tab keeps its address.
await page.context().route("http://192.168.1.20:8096/**", (r) => r.fulfill({ status: 200, contentType: "text/html", body: "<title>Jellyfin</title>" }));
const [popup] = await Promise.all([page.context().waitForEvent("page", { timeout: 5000 }).catch(() => null),
  page.keyboard.press("Enter")]);
check("LIB-04", "Enter opens it in a new tab", Boolean(popup) && /192\.168\.1\.20:8096\/web\/#\/details\?id=/.test(popup?.url() || ""), popup?.url());
await popup?.close();
await page.context().unroute("http://192.168.1.20:8096/**");
await open("library-film.html?id=1");
const head = page.locator(".series-head .play-link");
check("LIB-04", "a film's page has Play as its main action", await head.count() === 1 && /btn--primary/.test(await head.getAttribute("class")));
await open("library-film.html?id=7");
check("LIB-04", "a film Jellyfin has not added says so, with no Play",
  await page.locator(".series-head .play-link").count() === 0 && /Not in Jellyfin yet/.test(await page.locator(".series-head").textContent()));
await open("library-tv-show.html?id=4");
await page.locator("#panel-episodes .play-link").first().waitFor({ timeout: 8000 }).catch(() => {});
const epName = await page.locator("#panel-episodes .play-link").first().evaluate((a) => a.textContent.replace(/\s+/g, " ").trim());
check("LIB-04", "each episode Jellyfin has shows Play, named with its season and number",
  await page.locator("#panel-episodes .play-link").count() === 4 && /^Play .+ \(Season 1, episode 1\) in Jellyfin \(opens in a new tab\)$/.test(epName), epName);
check("LIB-04", "an episode with its file that Jellyfin has not added says so in words",
  /Not in Jellyfin yet/.test(await page.locator("#panel-episodes").textContent()));
// With only the local address Starboard uses (as Install apps saves Jellyfin): Play is made from the host this page
// was opened with and Jellyfin's port, as Starboard's other Open buttons do.
const jfApp = (await api("/api/config")).services.find((x) => x.type === "jellyfin");
const { has_api_key: _k, ...jfSaved } = jfApp;
await api("/api/services", { method: "POST", body: { ...jfSaved, link: "" } });
await open("library-film.html?id=1");
const localHref = await page.locator(".series-head .play-link").getAttribute("href").catch(() => "");
check("LIB-04", "with only a local address, Play uses this page's host and Jellyfin's port",
  localHref === `http://${new URL(base).hostname}:${new URL(jfApp.url).port}${new URL(jfApp.url).pathname.replace(/\/$/, "")}/web/#/details?id=${"0".repeat(28)}1b59`, localHref);
// With no address that can be made (a container's name only): no Play links, and where to add one.
await api("/api/services", { method: "POST", body: { ...jfSaved, link: "http://host.docker.internal:8096" } });
await open("library-film.html?id=1");
check("LIB-04", "with no address a browser can open there is no Play",
  await page.locator(".play-link").count() === 0);
const addLink = page.locator(".series-head .notice a", { hasText: "Add Jellyfin's address" });
check("LIB-04", "and the page says where to add it", await addLink.count() === 1 && (await addLink.getAttribute("href")) === `/settings.html?edit=${encodeURIComponent(jfApp.id)}`);
await api("/api/services", { method: "POST", body: jfSaved });
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
check("RAD-12", "Find it shows the show behind the link", await page.locator("#radio-link-title").textContent().catch(() => "") === "The Lighthouse Keepers");
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

// DL-03: Copy issues for an AI helper (DASH-434): by keyboard, said in the live region, nothing secret, a Markdown file,
// and an empty state when nothing needs attention
console.log("\n== DL-03 copy issues for an AI helper");
await context.grantPermissions(["clipboard-read", "clipboard-write"], { origin: base });
await open("downloads.html");
const copyIssues = page.getByRole("button", { name: "Copy issues for an AI helper" });
check("DL-03", "Queue has a Copy issues for an AI helper button and a Download as Markdown button",
  await copyIssues.count() === 1 && await page.getByRole("button", { name: "Download as Markdown" }).count() === 1);
await copyIssues.focus();
await page.keyboard.press("Enter");
await page.waitForFunction(() => /^Copied \d+ issues?$/.test(document.querySelector("#announcer")?.textContent || ""), null, { timeout: 15000 }).catch(() => {});
const said = await page.locator("#announcer").textContent();
check("DL-03", "the live region says Copied and the number of issues", /^Copied \d+ issues?$/.test(said), said);
check("DL-03", "focus stays on the button", await copyIssues.evaluate((b) => b === document.activeElement));
const copied = await page.evaluate(() => navigator.clipboard.readText()).catch(() => "");
check("DL-03", "the copy starts with the prompt and has each issue with its details", copied.startsWith("# Download issues from Starboard")
  && /Diagnose the issue/.test(copied) && /Sample\.Science\.Weekly/.test(copied) && /Reelix ids:\*\* queue 33, radio episode 203/.test(copied)
  && /Harbour Usenet/.test(copied), copied.slice(0, 200));  // the default install's example: Reelix's radio episode (Sonarr's Old.Show is in EXAMPLE_SETUP=existing)
check("DL-03", "no key, passkey, private address or home folder in the copy",
  copied.length > 0 && !/made-up-indexer-key|made-up-passkey|192\.168\.1\.20|\/home\/someone/.test(copied));
check("DL-03", "the page says what was copied, with a way to read it", /Copied \d+ issues? for an AI helper/.test(await page.locator("#issues-export").textContent())
  && await page.locator("#issues-export summary", { hasText: "Show what was copied" }).count() === 1);
const [mdFile] = await Promise.all([page.waitForEvent("download", { timeout: 15000 }).catch(() => null),
  page.getByRole("button", { name: "Download as Markdown" }).click()]);
check("DL-03", "Download as Markdown saves a .md file", /^starboard-download-issues-\d{8}-\d{4}\.md$/.test(mdFile?.suggestedFilename() || ""), mdFile?.suggestedFilename());
await page.route("**/api/queue/issues*", (route) => route.fulfill({ contentType: "application/json",
  body: JSON.stringify({ generated_at: "2026-11-15T12:00:00Z", count: 0, apps_asked: 2, items: [], errors: [], markdown: "# Download issues from Starboard\n" }) }));
await copyIssues.click();
await page.locator("#issues-export .empty").waitFor({ timeout: 5000 }).catch(() => {});
check("DL-03", "with nothing to copy, an empty state says so", /No issues to copy/.test(await page.locator("#issues-export").textContent()));
await page.waitForFunction(() => /No issues to copy/.test(document.querySelector("#announcer")?.textContent || ""), null, { timeout: 3000 }).catch(() => {});
check("DL-03", "and so does the live region", /No issues to copy/.test(await page.locator("#announcer").textContent()));
await page.unroute("**/api/queue/issues*");

// DL-04: a download that needs attention (DASH-496): its name opens a slide-out with what is wrong in plain words,
// the download folder, and every action that fits, each with one line on what it does; focus goes in and back to the
// name; the delete asks first and names what it deletes; the result is said in the live region and gets focus.
// The default install's example is Reelix's radio episode whose folder holds only a .par2 file.
console.log("\n== DL-04 a download that needs attention");
await open("downloads.html");
const radioName = page.locator("#queue button", { hasText: "Sample Science Weekly · Ask a scientist 3" });
await radioName.focus();
await page.keyboard.press("Enter");
await page.locator("#side-panel").waitFor({ timeout: 5000 }).catch(() => {});
check("DL-04", "selecting the name opens the slide-out with focus on Close",
  await page.evaluate(() => document.activeElement?.getAttribute("aria-label") === "Close Sample Science Weekly · Ask a scientist 3"));
await page.waitForFunction(() => document.querySelector("#attention") && !document.querySelector("#attention").hasAttribute("aria-busy"), null, { timeout: 10000 }).catch(() => {});
const naFirst = await page.locator("#attention .notice__title").first().textContent().catch(() => "");
check("DL-04", "it says what is wrong in plain words first", naFirst === "No media was downloaded", naFirst);
await page.waitForFunction(() => /No media was downloaded\. \d+ actions to choose from/.test(document.querySelector("#announcer")?.textContent || ""), null, { timeout: 3000 }).catch(() => {});
check("DL-04", "the live region says it, with the number of actions", /No media was downloaded\. \d+ actions/.test(await page.locator("#announcer").textContent()));
const naActions = await page.locator("#attention .action-list button").evaluateAll((bs) => bs.map((b) => b.dataset.action));
check("DL-04", "every action that fits is listed, with Remove and delete the files and the blocklist",
  ["block-search", "import", "ignore", "remove-keep", "delete", "delete-block"].every((a) => naActions.includes(a)), naActions.join());
check("DL-04", "each action has its one line, tied to the button", await page.locator("#attention .action-list button").evaluateAll((bs) =>
  bs.every((b) => (document.getElementById(b.getAttribute("aria-describedby"))?.textContent || "").length > 20)));
check("DL-04", "one primary button, the suggested one (Find another)", await page.locator("#attention .btn--primary").count() === 1
  && /Find another/.test(await page.locator("#attention .btn--primary").textContent()));
check("DL-04", "the folder's files are listed with what each one is", /Sample\.Science\.Weekly\.3\.par2/.test(await page.locator("#attention").textContent())
  && await page.locator("#attention .file-kind", { hasText: "Other" }).count() === 1);
check("DL-04", "what is wrong comes before the actions, and the actions before the files (reading order)", await page.evaluate(() => {
  const at = (q) => [...document.querySelectorAll("#attention *")].indexOf(document.querySelector(q));
  return at(".notice") < at(".action-list") && at(".action-list") < at("#na-files-h");
}));
const naTabs = [];
for (let n = 0; n < 9; n++) { await page.keyboard.press("Tab"); naTabs.push(await page.evaluate(() => !!document.activeElement?.closest("#side-panel"))); }
check("DL-04", "Tab stays inside the slide-out", naTabs.every(Boolean));
await page.keyboard.press("Escape");
await page.waitForTimeout(300);
check("DL-04", "Escape closes it and focus goes back to the name", await radioName.evaluate((b) => b === document.activeElement));
await page.keyboard.press("Enter");
await page.waitForFunction(() => document.querySelector("#attention [data-action=delete]"), null, { timeout: 10000 }).catch(() => {});
const naDelete = page.locator("#attention [data-action=delete]");
await naDelete.focus();
await page.keyboard.press("Enter");
await page.locator("dialog[open]").waitFor({ timeout: 3000 }).catch(() => {});
const naAsk = await page.locator("dialog[open]").textContent().catch(() => "");
check("DL-04", "Remove and delete the files asks first, naming what it deletes and the space it frees",
  /1 file from the download folder and frees 40 KB/.test(naAsk) && /Sample\.Science\.Weekly\.3\.par2/.test(naAsk) && /cannot be undone/.test(naAsk), naAsk.slice(0, 200));
check("DL-04", "the question starts on Cancel", await page.evaluate(() => document.activeElement?.textContent === "Cancel"));
await page.keyboard.press("Escape");
await page.waitForTimeout(300);
check("DL-04", "Cancel deletes nothing and focus goes back to the button", await naDelete.evaluate((b) => b === document.activeElement));
await naDelete.click();
await page.locator("dialog[open]").getByRole("button", { name: "Delete the files", exact: true }).click();
await page.locator("#na-result").waitFor({ timeout: 20000 }).catch(() => {});
await page.waitForFunction(() => /^Removed\. 1 file deleted, 40 KB freed/.test(document.querySelector("#announcer")?.textContent || ""), null, { timeout: 5000 }).catch(() => {});
check("DL-04", "the result is said in the live region", /^Removed\. 1 file deleted, 40 KB freed/.test(await page.locator("#announcer").textContent()),
  await page.locator("#announcer").textContent());
check("DL-04", "and shown in the slide-out, with focus on it", await page.evaluate(() => document.activeElement?.id === "na-result"));
await page.keyboard.press("Escape");
await page.waitForTimeout(500);
check("DL-04", "the download has left the queue", await page.locator("#queue button", { hasText: "Sample Science Weekly · Ask a scientist 3" }).count() === 0);

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

// SETUP-271: Your drives in the browser set-up (DASH-271) hands over to System, Storage, Pool, which then offers the
// way back to the set-up guide; the guide reads the Storage page's words from the file the terminal set-up reads.
console.log("\n== SETUP-271 Your drives and the Storage page");
await open("system-pool.html?from=guide");
const backToGuide = page.getByRole("link", { name: "Back to the set-up guide" });
check("SETUP-271", "System, Storage, Pool opened from the set-up offers the way back", await backToGuide.count() === 1);
check("SETUP-271", "and it leads to the set-up guide", (await backToGuide.getAttribute("href")) === "/setup-guide.html");
await open("system-pool.html");
check("SETUP-271", "opened on its own, it does not", await page.getByRole("link", { name: "Back to the set-up guide" }).count() === 0);
const words = await page.evaluate(async () => (await (await fetch("/setup-answers.json")).json()));
check("SETUP-271", "the shared words have the Storage page and API keys steps", !!(words.storage_page?.usage?.length && words.keys?.places?.sonarr));

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
// 0.19.1 (owner): the version is a link to Settings, Updates, with a gently pulsing dot above it when an update is out.
check("FOOT-01", "the version at the bottom of the side menu links to Settings, Updates",
  /^(Starboard version )?v\d+\.\d+\.\d+(, update available: version \d+\.\d+\.\d+)?$/.test((await page.locator(".rail__end a.rail__version [data-version-short]").textContent()).trim())
  && (await page.locator(".rail__end a.rail__version").getAttribute("href")) === "/settings-updates.html");
const footLinks = await page.locator(".site-footer .site-footer__links a").evaluateAll((as) => as.map((a) => a.childNodes[0].textContent.trim()));
check("FOOT-01", "the footer links are Help, Discord support server, Release notes, GitHub repository, About and updates",
  footLinks.join("|") === "Help|Discord support server|Release notes|GitHub repository|About and updates", footLinks.join(", "));
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
check("FOOT-02", "About and updates says Update available when a newer release is out", /About and updates, ?Update available/.test(await upgradeText("99.0.0")));
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
// Dispatcharr is an add-on, not in the default install the example server shows, so it is added for these checks
// and taken away after (the made-up Dispatcharr answers in the example server whatever the address).
const dispatcharr = await api("/api/services", { method: "POST", body: { type: "link", name: "Dispatcharr", icon: "dispatcharr",
  url: `http://127.0.0.1:${Number(new URL(base).port) + 1}/dispatcharr`, api_key: "example-key" } });
await open("settings-dispatcharr.html");
await page.locator("#dp-source-h").waitFor({ timeout: 10000 });
check("DISP-01", "Settings, Apps, Dispatcharr shows the source, channels and Jellyfin",
  (await page.locator("#dp-source-h, #dp-channels-h, #dp-jellyfin-h").count()) === 3);
check("DISP-01", "a playlist address asks for no user name", await page.locator("#dp-user").isHidden());
await page.check("#dp-kind-xc");
check("DISP-01", "Xtream Codes asks for a user name and password", await page.locator("#dp-user").isVisible() && await page.locator("#dp-pass").isVisible());
await page.click("#dp-save");
// The design system's error summary (20 November 2026): "There is a problem" at the top of the form has focus, with a
// link to each field that is wrong; the field says so too.
check("DISP-02", "saving Xtream Codes without a user name says so at the field and in the error summary, which has focus",
  (await page.locator("#dp-user").getAttribute("aria-invalid")) === "true" && await page.evaluate(() => document.activeElement.classList.contains("error-summary"))
  && /There is a problem/.test(await page.locator(".error-summary").innerText()));
await page.locator(".error-summary a[href='#dp-user']").click();
check("DISP-02", "its link puts focus on the field", await page.evaluate(() => document.activeElement.id) === "dp-user");
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
await api(`/api/services/${dispatcharr.id}`, { method: "DELETE" }).catch(() => {});

// DASH-389: General's sections are pages on the level 2 menu; Style is Appearance, with the accessibility options;
// old addresses go to the part's new page.
console.log("\n== MENU2 General on the level 2 menu");
const level2 = async (p) => { await open(p); return (await page.locator(".site-header__tabs .menu-tabs a").evaluateAll((as) => as.map((a) => a.textContent.trim()))).join("|"); };
const headings = () => page.locator("main .settings-sections h2").evaluateAll((hs) => hs.map((h) => h.textContent.trim()).join("|"));
check("MENU2-01", "General has Names and apps, Appearance, Pages and lists, Discover rows, Download hours, Logs and feedback, Alerts, Performance, Pictures, Backup and restore",
  (await level2("settings-general.html")) === "Names and apps|Appearance|Pages and lists|Discover rows|Download hours|Logs and feedback|Alerts|Performance|Pictures|Backup and restore", await level2("settings-general.html"));
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
check("MENU2-05", "Performance and Pictures are tabs of General", (await level2("settings-general-performance.html")) === "Names and apps|Appearance|Pages and lists|Discover rows|Download hours|Logs and feedback|Alerts|Performance|Pictures|Backup and restore");
check("MENU2-05", "Pictures has the picture cache and its Clear", (await level2("settings-general-pictures.html")) && (await headings()) === "Pictures|Clear", await headings());
check("MENU2-05", "Security has Who can open the dashboard, Password, Sign-in methods, API keys, Sign out everywhere",
  (await level2("settings-security.html")) === "Who can open the dashboard|Password|Sign-in methods|API keys|Sign out everywhere", await level2("settings-security.html"));
for (const [from, to] of [["settings-radio.html#radio-logos-h", "/settings-radio-logos.html"], ["settings-general-performance.html#pf-pictures-h", "/settings-general-pictures.html"],
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
check("OWN-01", "the own style offers Mica's seven accents, Blue first", ownCards.join(",") === "blue,teal,dusk,lime,rose,amber,graphite", ownCards.join(","));
await page.locator("input[name=pl-own-colours][value=lime]").check();
await page.waitForTimeout(500);
check("OWN-01", "choosing Lime saves it for the server and uses its colours here",
  (await api("/api/config")).own_colours === "lime" && await page.evaluate(() => document.documentElement.dataset.palette) === "lime"
  && (await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--color-accent").trim())) === "#3a5700");
check("OWN-01", "the saved note says so beside the choice", /Saved/.test(await page.locator("#pl-own-colours-saved").textContent()));
await page.locator(".style-gallery button", { hasText: "Use this style" }).first().click();
await page.waitForTimeout(300);
check("OWN-02", "a plug-in style in use leaves the own colours out", await page.evaluate(() => !document.documentElement.dataset.palette && !!document.documentElement.dataset.style));
await page.evaluate(() => resetStyle());
await page.waitForTimeout(300);
check("OWN-02", "Reset style goes back to the own style in Lime", await page.evaluate(() => !document.documentElement.dataset.style && document.documentElement.dataset.palette === "lime"));
check("OWN-02", "and the own style's card says Lime", /Lime accent/.test(await page.locator(".style-gallery__item").first().innerText()));
await api("/api/config/general", { method: "PUT", body: { own_colours: "blue" } });
await page.evaluate(() => setOwnColours("blue"));
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
// DASH-402: a plug-in's tables to read only (plug-in API 1.11), on the example Watch statistics plug-in: each table is
// its own tab, a section opens to its table with only the plug-in's columns, and nothing can be ticked or activated.
console.log("\n== WS Read-only plug-in tables");
await open("settings-plugin.html?id=watch-stats");  // topic tabs are off here, so the three tables are on one page
await page.locator(".fold__toggle").first().waitFor({ timeout: 10000 }).catch(() => {});
const wsLine = (await page.locator(".fold__toggle").first().innerText()).replace(/\s+/g, " ");
check("WS-01", "each section's line says how many rows it has, not how many are active", /^Today 2 rows/.test(wsLine) && !/active/.test(wsLine), wsLine);
await page.locator(".fold__toggle").first().click();
await page.waitForTimeout(300);
const wsHeads = await page.locator(".fold__panel").first().locator("table th[scope=col]").allInnerTexts();
check("WS-02", "the open section's table has only the plug-in's columns", wsHeads.join(",") === "Time,Person,Title,Device,Minutes", wsHeads.join(","));
check("WS-03", "nothing can be ticked, activated or deactivated",
  !(await page.locator(".fold__panel input[type=checkbox]").count()) && !(await page.locator(".fold__panel").getByRole("button", { name: /^(Activate|Deactivate)/ }).count()));
check("WS-04", "each row is named by its first cell", (await page.locator(".fold__panel tbody th[scope=row]").count()) === 2);
await page.locator(".fold__toggle", { hasText: "Series" }).click();
await page.waitForTimeout(300);
const wsTop = await page.locator(".fold__toggle", { hasText: "Series" }).locator("xpath=ancestor::section[1]").locator("tbody tr").first().innerText();
check("WS-05", "Top titles shows the most played series first, with plays, people and hours", /^Slow Horses\s+3\s+2\s+2\.5/.test(wsTop), wsTop);
// A search that leaves a section with no rows hides that section. It stopped the page with "q is not defined" (found
// on On demand's Leagues, 19 November 2026), so the list was not drawn again after a change.
const wsBefore = problems.length;
const wsFolds = () => page.locator("#fold-watch-stats-titles-q").locator("xpath=ancestor::*[.//*[contains(concat(' ', normalize-space(@class), ' '), ' fold ')]][1]").locator(".fold__name").allInnerTexts();
const wsAll = (await wsFolds()).sort().join(",");
await page.locator("#fold-watch-stats-titles-q").fill("Slow Horses");
await page.waitForTimeout(400);
const wsFound = (await wsFolds()).join(",");
check("WS-07", "a search hides the section with no match and keeps the one with a match, with no script error",
  problems.length === wsBefore && wsAll === "Films,Series" && wsFound === "Series", `before ${wsAll}, searched ${wsFound} ${problems.slice(wsBefore).join(" | ")}`);
await page.locator("#fold-watch-stats-titles-q").fill("");
await page.waitForTimeout(400);
check("WS-08", "an empty search brings every section back", (await wsFolds()).sort().join(",") === wsAll, (await wsFolds()).join(","));
problems.length = wsBefore;  // said by WS-07; the last check counts the script errors of every other page
await page.setViewportSize({ width: 375, height: 812 });
check("WS-06", "the tables fit at phone width", await page.evaluate(() => document.documentElement.scrollWidth - innerWidth) <= 0);
await page.setViewportSize({ width: 1280, height: 860 });
// DASH-441: a plug-in button with a confirm asks first (focus on Cancel, Escape cancels); a list setting is a box
// with one value a line, saved as a list.
console.log("\n== PLA Plug-in actions and list settings");
await open("settings-plugin.html?id=direct-play");
const plaSaid = page.locator('section[aria-labelledby="pl-direct-play-actions-h"] [role=status]');
await page.getByRole("button", { name: "Pause fixing" }).click();
const plaDialog = page.locator("dialog[open]");
await plaDialog.waitFor({ timeout: 5000 });
check("PLA-01", "a button with a confirm asks first, in words from the plug-in", /Stops converting files/.test(await plaDialog.innerText()));
check("PLA-01", "the box starts on Cancel", await page.evaluate(() => document.activeElement?.textContent?.trim() === "Cancel"));
await page.keyboard.press("Escape");
await page.waitForTimeout(300);
check("PLA-02", "Escape closes it, runs nothing, and focus goes back to the button",
  await plaDialog.count() === 0 && !(await plaSaid.textContent()).trim()
  && await page.evaluate(() => document.activeElement?.textContent?.trim() === "Pause fixing"));
await page.getByRole("button", { name: "Pause fixing" }).click();
await plaDialog.waitFor({ timeout: 5000 });
await plaDialog.getByRole("button", { name: "Pause fixing", exact: true }).click();
await page.waitForTimeout(800);
check("PLA-03", "choosing the action in the box runs it", /Paused/.test(await plaSaid.textContent()));
await open("settings-plugin.html?id=notifications");
const plaList = page.locator("#pl-notifications-telegram_chat");
check("PLA-04", "a list setting is a box with one value a line", (await plaList.evaluate((n) => n.tagName)) === "TEXTAREA"
  && /One chat id a line|One a line/.test(await page.locator(`#${await plaList.getAttribute("aria-describedby")}`).textContent()));
await plaList.fill("12345\n\n  67890  \n");
await plaList.locator("xpath=ancestor::form").getByRole("button", { name: "Save" }).click();
await page.waitForTimeout(800);
check("PLA-05", "saving a list says nothing is wrong", await page.locator('#toast-stack .toast[data-tone="danger"]').count() === 0);
await open("settings-plugin.html?id=notifications");
check("PLA-05", "it is kept as a list: one value a line, blank lines and spaces left out", (await plaList.inputValue()) === "12345\n67890");
// DASH-411: app plug-ins (plug-in API 1.13). Jellystat's page on the home network, the clear choice on removal, and
// Tdarr's offer to copy the Tdarr the main install runs.
console.log("\n== AP App plug-ins");
await open("settings-plugin.html?id=jellystat");
const apLink = page.locator('section[aria-labelledby="pl-jellystat-web-h"] a', { hasText: "Open Jellystat" });
check("AP-01", "an app plug-in's page has its address on the home network, with Open",
  (await apLink.count()) === 1 && (await apLink.getAttribute("href")) === "http://127.0.0.1:3000/"
  && /port 3000/.test(await page.locator('section[aria-labelledby="pl-jellystat-web-h"]').innerText()));
await page.getByRole("button", { name: "Remove Jellystat" }).click();
const apDialog = page.locator("dialog[open]");
await apDialog.waitFor({ timeout: 5000 });
const apRadios = apDialog.locator("input[type=radio]");
check("AP-02", "removing asks where its data goes, kept with Starboard's data by default",
  (await apRadios.count()) === 2 && await apRadios.first().isChecked()
  && /holding folder/.test(await apDialog.innerText()) && /Nothing is deleted/.test(await apDialog.innerText()));
await apDialog.getByRole("button", { name: "Cancel" }).click();
check("AP-03", "Cancel puts focus back on Remove", await page.evaluate(() => /Remove Jellystat/.test(document.activeElement?.textContent || "")));
await open("settings-plugins.html");
check("AP-04", "Your plug-ins has Open for an active app plug-in, named for a screen reader",
  (await page.getByRole("link", { name: /Open Jellystat/ }).count()) === 1);
await open("settings-plugin.html?id=tdarr");
const apAdopt = page.getByRole("button", { name: /Bring in the Tdarr you already have/ });
check("AP-05", "an inactive app plug-in offers to copy the app the main install runs", (await apAdopt.count()) === 1);
await apAdopt.click();
await page.waitForTimeout(500);
const apSaid = await page.locator('section[aria-labelledby="pl-tdarr-adopt-h"] [role=status]').innerText();
check("AP-06", "with no such app, it says so plainly in a live region", /found no Tdarr|Docker/.test(apSaid), apSaid);
await open("settings-plugins-catalogue.html");
const apGroup = page.locator('section[aria-label="Apps you can add"]');
check("AP-08", "the catalogue groups the apps together, each with what it uses at rest",
  (await apGroup.count()) === 1 && /At rest: about \d+ MB of memory/.test(await apGroup.innerText()));
await open("settings-plugin.html?id=tdarr");
check("AP-07", "an app plug-in that is not active says a port is chosen when it is", /chooses a free port/.test(await page.locator('section[aria-labelledby="pl-tdarr-web-h"]').innerText()));
// DASH-410: plug-in API 1.12 on the example Audio description plug-ins: a row's link opens in a new tab and says so,
// the plug-in's own words for each state, and an upload that takes only a file.
console.log("\n== AD Audio description sources");
await open("settings-plugin.html?id=audio-description-sources");
const adTab = page.getByRole("tab", { name: "AudioVault" });
if (await adTab.count()) await adTab.click();
await page.locator("[data-menu=films]").first().waitFor({ timeout: 10000 }).catch(() => {});
await page.locator("[data-menu=films]").first().click();
await page.waitForTimeout(300);
const adLink = page.getByRole("link", { name: /^Search AudioVault for Brazil \(1985\) \(opens in a new tab\)$/ });
check("ADS-01", "a row's link is named by where it goes and says it opens in a new tab", (await adLink.count()) === 1);
check("ADS-02", "it goes to AudioVault's own search in a new tab, with nothing passed back",
  (await adLink.getAttribute("href")) === "https://audiovault.net/movies?search=Brazil" && (await adLink.getAttribute("target")) === "_blank"
  && /noopener/.test(await adLink.getAttribute("rel") || ""));
check("ADS-03", "a link-only row says so in the plug-in's own words, not Works", (await page.getByText("No description here").count()) > 0
  && !(await page.locator(".row__side").getByText(/^Works$/).count()));
await open("settings-plugin.html?id=audio-description-tracks");
const adtTab = page.getByRole("tab", { name: "Tracks" });
if (await adtTab.count()) await adtTab.click();
await page.getByLabel("Choose a description track").waitFor({ timeout: 10000 }).catch(() => {});
check("ADS-04", "the upload takes only a file: a labelled file picker and no address box",
  (await page.getByLabel("Choose a description track").count()) === 1 && !(await page.locator("#add-audio-description-tracks-inbox").count()));
check("ADS-05", "each file shows what happened in plain words", (await page.getByText("Lengths differ", { exact: true }).count()) === 1
  && (await page.getByText("Added", { exact: true }).count()) === 1 && !(await page.getByText("Not answering", { exact: true }).count()));
check("ADS-06", "the plays in step choice is named for its file", (await page.getByLabel("Plays in step?: Dune (2021).mp3").count()) === 1);
await page.setViewportSize({ width: 375, height: 812 });
check("ADS-07", "the list fits at phone width", await page.evaluate(() => document.documentElement.scrollWidth - innerWidth) <= 0);
await page.setViewportSize({ width: 1280, height: 860 });
// DASH-401: the Notifications plug-in's settings, a section for each channel; a saved token never comes back to the page.
console.log("\n== NT Notifications plug-in settings");
await open("settings-plugin.html?id=notifications");
const ntHtml = await page.content();
const ntApi = JSON.stringify(await api("/api/plugins"));
check("NT-01", "a saved bot token is never sent back to the page", !ntHtml.includes("tg-example-token-401") && !ntApi.includes("tg-example-token-401"));
check("NT-02", "each channel has its own section", (await page.getByRole("tab", { name: "Telegram" }).count()) + (await page.getByRole("heading", { name: "Telegram" }).count()) > 0);
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

// DASH-301: filters on Discover's rows (the same filters on every row, with counts, remembered for the account).
await api("/api/library/discover-filters?tab=films", { method: "POST", body: { filters: {} } });
await open("discover-films.html");
await page.locator("#discover-filters #df-where-out").waitFor({ timeout: 10000 });

const allCards = await page.locator("#discover-rows .discover-card").count();
await page.locator("#df-where-out").check({ force: true });
await page.waitForTimeout(400);
const outCards = await page.locator("#discover-rows .discover-card:not([hidden])").count();
check("DSC-01", "Not in your library hides the covers you have, in every row, and the count follows", outCards > 0 && outCards < allCards
  && (await page.locator("#discover-count").textContent()).includes(" of "), `${outCards} of ${allCards}`);
check("DSC-01", "the choice is remembered for the account", (await api("/api/library/discover-filters?tab=films")).filters.where === "out");
await page.locator("#df-decade").selectOption({ index: 1 });
await page.waitForTimeout(400);
const decadeCards = await page.locator("#discover-rows .discover-card:not([hidden])").count();
check("DSC-01", "a decade narrows it further (the filters combine)", decadeCards > 0 && decadeCards < outCards, `${decadeCards} of ${outCards}`);
await open("discover-films.html");
await page.locator("#discover-filters #df-where-out").waitFor({ timeout: 10000 });
check("DSC-01", "a new visit starts with the same filters on", await page.locator("#df-where-out").isChecked() && (await page.locator("#df-decade").inputValue()) !== "");
await page.locator("#df-clear").click();
await page.waitForTimeout(300);
check("DSC-01", "Clear filters shows every cover again and focus goes to All", (await page.locator("#discover-rows .discover-card[hidden]").count()) === 0
  && await page.evaluate(() => document.activeElement.id) === "df-where-all");
await api("/api/library/discover-filters?tab=films", { method: "POST", body: { filters: {} } });

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

console.log("\n== Full without media: which disk (DASH-260)");
await open("system-backup.html");
await page.locator("#full-disk p").first().waitFor({ timeout: 10000 }).catch(() => {});
const fullFolder = await page.locator("#full-folder").inputValue().catch(() => "");
check("BK-01", "the copies go to the media folder's disk, not the system disk", fullFolder === "/srv/media/backups/starboard", fullFolder);
check("BK-01", "the page says which disk the folder is on", /On WDC WD40EFRX \(\/srv\/media\), not the system disk/.test(await page.locator("#full-disk").textContent()));
check("BK-01", "the copies in the folder are listed, newest first", (await page.locator("#full-body ul.rows li").count()) === 2);
// The section may sit behind a topic tab, so the folder is set as the picker would set it.
await page.evaluate(() => { const i = document.querySelector("#full-folder"); i.value = "/home/sam/backups"; i.dispatchEvent(new Event("change")); });
await page.waitForFunction(() => /on the system disk/.test(document.querySelector("#full-disk")?.textContent || ""), null, { timeout: 10000 }).catch(() => {});
check("BK-01", "a folder on the system disk is warned about", /This folder is on the system disk/.test(await page.locator("#full-disk").textContent()));
// API keys that read and manage, with scopes (DASH-274): the form offers both, the key works on /api/v1 with only
// its scopes, and a read key cannot change anything.
await open("settings-security-keys.html");
await page.getByRole("button", { name: "Make a key" }).first().click();
await page.waitForTimeout(400);
const rights = await page.locator("#key-right option").allTextContents();
check("API-01", "Make a key asks what it may do: Read only or Read and manage", rights.join("|") === "Read only|Read and manage", rights.join("|"));
const scopeNames = await page.locator("#key-scopes .check strong").allTextContents();
check("API-01", "and what it may see, one tick for each area", scopeNames.join("|") === "Apps|Downloads|Media|Library|Requests|System|Logs|Updates", scopeNames.join("|"));
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
// DASH-464: AI assistants over MCP, on the same page. Off until activated; the switch says what it shares, keeps focus
// and says the result in a live region; a Read only key then gets the tools, and deactivating stops it at once. The
// assistant's calls go from here, as an assistant's would, not from the page.
console.log("\n== MCP AI assistants");
await open("settings-security-keys.html");
const mcpOn = page.locator("#mcp-on");
await mcpOn.waitFor({ timeout: 10000 });
check("MCP-01", "AI assistants is on the API keys page, inactive at first", !(await mcpOn.isChecked()) && /Inactive/.test(await page.locator("#mcp-result").textContent()));
check("MCP-01", "the switch has its name and says what it shares", (await page.getByRole("switch", { name: "Let AI assistants connect" }).count()) === 1
  && /cannot change anything/.test(await page.locator("#mcp-h").textContent()));
check("MCP-01", "the result is a live region", (await page.locator("#mcp-result").getAttribute("role")) === "status");
const mcpKey = (await api("/api/keys", { method: "POST", body: { name: "Journey assistant", right: "read", scopes: [], expires_days: "90", password } })).key;
const mcpCall = async (msg) => {
  const r = await fetch(`${base}/api/v1/mcp`, { method: "POST", headers: { Authorization: `Bearer ${mcpKey}`, "Content-Type": "application/json" }, body: JSON.stringify(msg) });
  return { status: r.status, body: await r.json().catch(() => null) };
};
const mcpOff = await mcpCall({ jsonrpc: "2.0", id: 1, method: "tools/list" });
check("MCP-02", "while inactive, a key gets 403 mcp_off", mcpOff.status === 403 && mcpOff.body?.code === "mcp_off", JSON.stringify(mcpOff.body).slice(0, 120));
await mcpOn.focus();
await page.keyboard.press("Space");
await page.waitForFunction(() => /Active:/.test(document.querySelector("#mcp-result")?.textContent || ""), null, { timeout: 5000 }).catch(() => {});
check("MCP-03", "Space activates it, focus stays on the switch and the address shows",
  await mcpOn.isChecked() && await page.evaluate(() => document.activeElement?.id === "mcp-on")
  && /\/api\/v1\/mcp$/.test(await page.locator("section[aria-labelledby='sc-mcp-h'] dd code").first().textContent()));
const mcpList = await mcpCall({ jsonrpc: "2.0", id: 2, method: "tools/list" });
check("MCP-04", "then a Read only key gets the read-only tools", mcpList.status === 200 && mcpList.body?.result?.tools?.length === 9
  && mcpList.body.result.tools.every((t) => t.annotations.readOnlyHint), JSON.stringify(mcpList.body).slice(0, 120));
await page.keyboard.press("Space");
await page.waitForFunction(() => /Inactive:/.test(document.querySelector("#mcp-result")?.textContent || ""), null, { timeout: 5000 }).catch(() => {});
check("MCP-05", "deactivating it stops the assistant at once", (await mcpCall({ jsonrpc: "2.0", id: 3, method: "ping" })).status === 403);
for (const k of (await api("/api/keys")).keys.filter((k) => k.name === "Journey assistant")) await api(`/api/keys/${k.id}`, { method: "DELETE" });
// DASH-380, several places (26 November 2026): Where backups go on System, Backup and restore, set by the example server to
// a made-up USB disk, Google Drive and OneDrive, with a stand-in helper. Test answers beside the place and focus stays on
// it; a wrong share is said in an alert that takes focus; a place can be deactivated and the page says if the backup is safe.
console.log("\n== CP Where backups go");
await open("system-backup.html");
const cp = page.locator("#copies-body");
await cp.locator("#places-h").waitFor({ timeout: 10000 }).catch(() => {});
check("CP-01", "the section is there, after Full without media, with its heading",
  await page.evaluate(() => { const h = [...document.querySelectorAll("main h2")].map((x) => x.textContent); return h.indexOf("Where backups go") === h.indexOf("Full without media") + 1; }));
check("CP-01", "three places are listed, each with its name, its logo or icon (decorative) and its last copy in words",
  (await page.locator(".place__title").allTextContents()).join() === "USB disk,Google Drive,OneDrive"
  && await page.locator(".places .place-logo[aria-hidden=true]").count() === 3 && await page.locator(".places .place-state", { hasText: "Copied and read back" }).count() === 3);
check("CP-01", "the page says the newest backup is safe, because each place read it back", /^Safe/.test(await page.locator("#places-safe").innerText()));
check("CP-01", "every kind of place can be added, with the services",
  await page.locator(".place-adds button").count() === 11 && await page.locator("#place-add-onedrive").isVisible());
await page.locator("#place-test-main").click();
await page.waitForFunction(() => !document.querySelector("#place-test-main")?.disabled && /Tested/.test(document.querySelector("#place-tested-main")?.textContent || ""), null, { timeout: 8000 }).catch(() => {});
check("CP-02", "Test says Connected beside the place, with 5 full backups there (DASH-452)",
  /Connected/.test(await page.locator("#place-tested-main").innerText()) && /5 full backups there/.test(await page.locator("#place-tested-main").innerText()), await page.locator("#place-tested-main").innerText());
check("CP-02", "focus stays on Test", await page.evaluate(() => document.activeElement.id) === "place-test-main");
await page.waitForFunction(() => /^Connected: /.test(document.querySelector("#announcer")?.textContent || ""), null, { timeout: 3000 }).catch(() => {});
check("CP-02", "the result is said politely", /^Connected: /.test(await page.locator("#announcer").innerText()));
await page.locator("#place-add-smb").click();
await page.locator("#place-smb").waitFor();
await page.fill("#place-smb", "nas.home/backups");
await page.fill("#place-mine", password);
await page.locator("#place-save").click();
await page.locator("#place-error [role=alert]").waitFor({ timeout: 5000 }).catch(() => {});
check("CP-03", "a share written wrongly is not saved, said in an alert that takes focus",
  /\/\/computer\/share/.test(await page.locator("#place-error").innerText()) && await page.evaluate(() => document.activeElement.id) === "place-error");
check("CP-03", "the password box never shows a kept value", (await page.locator("#place-smb-password").inputValue()) === "");
await page.keyboard.press("Escape");
await page.waitForFunction(() => !document.querySelector(".side-panel"));
await page.locator("#place-on-d1a2b3").focus();
await page.keyboard.press("Space");
await page.waitForFunction(() => /Deactivated/.test(document.querySelector("#place-d1a2b3 .place-state")?.textContent || ""), null, { timeout: 5000 }).catch(() => {});
check("CP-04", "deactivating a place is said in words and a shape, and focus stays on its switch",
  /Deactivated/.test(await page.locator("#place-d1a2b3 .place-state").innerText()) && await page.evaluate(() => document.activeElement.id) === "place-on-d1a2b3");
await page.keyboard.press("Space");
await page.waitForFunction(() => /Copied and read back/.test(document.querySelector("#place-d1a2b3 .place-state")?.textContent || ""), null, { timeout: 5000 }).catch(() => {});
const copiesNow = await api("/api/backup/copies");
check("CP-04", "the page never gets a password or config back", !JSON.stringify(copiesNow).includes("smb_password\":") && !("rclone_config" in copiesNow) && copiesNow.destinations.length === 3);
check("CP-04", "the API says safe only when each place read it back", copiesNow.safe.safe === true && copiesNow.safe.places.length === 3);
await page.locator("#copies-now").click();
await page.waitForFunction(() => /Copied and read back|Copying/.test(document.querySelector("#copies-body")?.textContent || ""), null, { timeout: 8000 }).catch(() => {});
check("CP-05", "Copy the newest full backup now copies to every place that is activated", /Copied and read back|Copying/.test(await page.locator("#copies-body").innerText()));
console.log("\n== Audio description, chosen in the set-up (DASH-399)");
await open("settings-plugins-catalogue.html");
const adOffer = page.locator('[data-offer="audio-description"]');
check("AD-01", "the Catalogue offers Audio description, chosen in the set-up, as a notice people hear",
  (await adOffer.count()) === 1 && /Audio description, chosen in the set-up/.test(await adOffer.textContent())
  && (await adOffer.locator('[role="status"]').count()) === 1);
check("AD-01", "until it is in the collection, it says so and offers no install button",
  /not in the plug-ins collection yet/.test(await adOffer.textContent()) || (await adOffer.getByRole("button", { name: /Install Audio description/ }).count()) === 1);
await open("settings-plugins.html");
check("AD-02", "Your plug-ins links to the Catalogue for it",
  (await page.locator('[data-offer="audio-description"] a[href="/settings-plugins-catalogue.html"]').count()) === 1);
await page.locator('[data-offer="audio-description"]').getByRole("button", { name: /^Not now\s*:\s*Audio description$/ }).click();
await page.waitForTimeout(600);
check("AD-03", "Not now takes the offer away, says so and puts focus on the page's heading",
  (await page.locator('[data-offer="audio-description"]').count()) === 0
  && await page.evaluate(() => document.activeElement?.tagName === "H1")
  && /no longer offered/.test(await page.locator("body").textContent()));
check("AD-03", "and the set-up's wish is forgotten", (await api("/api/plugins")).wanted.length === 0);
await api("/api/config/general", { method: "PUT", body: { extras: { audio_description: true } } });  // as it was
// DASH-404: recommended Jellyfin plug-ins, against the example server's stand-in Jellyfin (no real Jellyfin is changed)
console.log("\n== DASH-404 Recommended Jellyfin plug-ins");
await open("settings-jellyfin.html");
const plug = page.locator("#jf-plugins-list");
await plug.locator("[data-key=skip]").waitFor({ timeout: 10000 });
check("JF-01", "each recommended plug-in has its own choice", (await plug.locator("form[data-key]").count()) === 5);  // with Picture shrinker (DASH-433)
check("JF-01", "what is installed shows with its version", /Installed: Playback Reporting 19\.0\.0\.0/.test(await plug.textContent()));
check("JF-01", "downloaded times name TheIntroDB on Jellyfin 12", /Downloaded times \(recommended\): TheIntroDB/.test(await plug.locator("[data-key=skip]").textContent()));
await plug.locator("[data-key=merge] input[value=on]").check();
await plug.locator("[data-key=merge]").getByRole("button", { name: "Apply this choice" }).click();
await page.locator("#jf-plugins-list", { hasText: "Installed Merge Versions" }).waitFor({ timeout: 10000 });
check("JF-02", "installing says so and asks for a restart", /Jellyfin needs a restart/.test(await plug.textContent()));
check("JF-02", "focus stays in the Merge Versions choice after it is drawn again",
  await page.evaluate(() => !!document.activeElement?.closest("#jf-plugins-list")));
await plug.getByRole("button", { name: "Restart Jellyfin", exact: true }).click();
await page.getByRole("dialog").getByRole("button", { name: "Restart Jellyfin", exact: true }).click();
// Restart where it is needed (DASH-470): the section is drawn again once Jellyfin answers, with the result focused.
await page.locator("#jf-plugins-list", { hasText: "Jellyfin restarted." }).waitFor({ timeout: 30000 }).catch(() => {});
check("JF-03", "once Jellyfin answers, the result is shown and has focus", await page.evaluate(() => /Jellyfin restarted/.test(document.activeElement?.textContent || "")));
const after = await api("/api/jellyfin/plugins");
// The section drawn again after the restart (DASH-470) is what finishes the set-up, so it says so there.
check("JF-03", "after the restart Merge Versions is active and set to quiet hours",
  after.groups.find((g) => g.id === "merge").installed[0]?.status === "Active" && /Set up after the restart/.test(await plug.textContent()), JSON.stringify(after.finished));
const moved = await api("/api/jellyfin/plugins", { method: "POST", body: { group: "playback", choice: "none" } });
check("JF-04", "Do not install deactivates and never uninstalls", moved.done[0] === "Deactivated Playback Reporting (still installed)", moved.done.join("; "));
await api("/api/jellyfin/plugins", { method: "POST", body: { group: "playback", choice: "on" } });

// DASH-425 (owner, 14 November 2026): recommended plug-ins in the catalogue, and Direct play's card on the dashboard
// with its own refresh time (plug-in API 1.14: 10 seconds at the quickest, asked together, nothing while hidden).
console.log("\n== DASH-425 Recommended plug-ins and the Direct play card");
await open("settings-plugins-catalogue.html");
const recGroup = page.locator("[data-recommended]");
check("REC-01", "the collection starts with a Recommended group, with Direct play and Disk forecast",
  (await recGroup.count()) === 1 && /Direct play/.test(await recGroup.innerText()) && /Disk forecast/.test(await recGroup.innerText())
  && await page.evaluate(() => { const g = document.querySelector("[data-recommended]"); return !!g && !g.previousElementSibling?.matches("section[aria-label]"); }));
check("REC-02", "each recommended entry has a Recommended chip, and is listed once",
  (await recGroup.locator(".chip", { hasText: "Recommended" }).count()) === 2
  && (await page.locator(".row__title", { hasText: "Disk forecast" }).count()) === 1);
const recInstall = recGroup.getByRole("button", { name: /Install… Disk forecast/ });
check("REC-03", "a recommended plug-in is not added by itself: it still has Install", (await recInstall.count()) === 1
  && !(await api("/api/plugins")).plugins.some((p) => p.id === "disk-forecast"));
if (await recInstall.count()) {
  // The example server has no copy of Disk forecast's manifest, so its warning may not open here; what matters is
  // that Install takes the same path as any plug-in: a preview first, then the warning with the password.
  const previews = [];
  const onPreview = (r) => { if (r.url().endsWith("/api/plugins/preview") && r.method() === "POST") previews.push(r.postData() || ""); };
  page.on("request", onPreview);
  await recInstall.click();
  const recDialog = page.getByRole("dialog");
  await recDialog.waitFor({ timeout: 5000 }).catch(() => {});
  page.off("request", onPreview);
  check("REC-04", "Install asks for the plug-in's warning first, as for any plug-in", previews.some((b) => /"catalogue_id":\s*"disk-forecast"/.test(b)), previews.join(" | "));
  if (await recDialog.count()) {
    check("REC-04", "the warning asks for the password", (await recDialog.locator("input[type=password]").count()) === 1);
    await page.keyboard.press("Escape");
  }
  await page.waitForTimeout(400);
  check("REC-04", "nothing is added",
    !(await api("/api/plugins")).plugins.some((p) => p.id === "disk-forecast"));
}
const dashBefore = (await api("/api/config")).dashboard;
await api("/api/config/general", { method: "PUT", body: { dashboard: { layout: dashBefore.layout,
  cards: [{ id: "plugin:direct-play:now", size: "half" }, { id: "plugin:direct-play:saved", size: "half" }] } } });
const dpAsked = [];
const onAsk = (r) => { if (r.url().includes("/api/plugins/cards/answers")) dpAsked.push({ at: Date.now(), url: decodeURIComponent(r.url()) }); };
page.on("request", onAsk);
await open("dashboard.html");
const dpCard = page.locator('[data-card="plugin:direct-play:now"]');
await dpCard.getByText(/Converting now: Dune \(2021\)/).waitFor({ timeout: 8000 }).catch(() => {});
const firstText = await dpCard.innerText().catch(() => "");
check("DPC-01", "the card says what is being converted, how far in words, the next files and the totals",
  /Converting now: Dune \(2021\)/.test(firstText) && /\d+% done/.test(firstText) && /Next: Slow Horses, series 1 episode 3/.test(firstText)
  && /1,173 files fixed, 1\.03 TB saved, 40 files still to do/.test(firstText), firstText);
await page.waitForTimeout(23000);
const both = dpAsked.filter((a) => a.url.includes("plugin:direct-play:now") && a.url.includes("plugin:direct-play:saved"));
const gaps = dpAsked.slice(1).map((a, i) => a.at - dpAsked[i].at);
check("DPC-02", "a card at 10 seconds is asked again about every 10 seconds, both due cards in one request",
  both.length >= 2 && gaps.every((g) => g >= 9000), `${dpAsked.length} asks, gaps ${gaps.join(", ")}`);
check("DPC-03", "the card asking for 2 seconds is held to 10", gaps.every((g) => g >= 9000)
  && (await api("/api/plugins/direct-play/cards/saved")).refresh_seconds === 10);
check("DPC-04", "the card's words change as it is asked again, in place", firstText !== await dpCard.innerText());
await page.evaluate(() => { Object.defineProperty(document, "hidden", { value: true, configurable: true }); document.dispatchEvent(new Event("visibilitychange")); });
const hiddenFrom = dpAsked.length;
await page.waitForTimeout(12000);
check("DPC-05", "nothing is asked while the tab is hidden", dpAsked.length === hiddenFrom, `${dpAsked.length - hiddenFrom} asks`);
page.off("request", onAsk);
await api("/api/config/general", { method: "PUT", body: { dashboard: { layout: dashBefore.layout, cards: dashBefore.cards || null } } });
await open("settings-plugin.html?id=direct-play");
check("DPC-06", "Pause and Resume stay on the plug-in's page",
  (await page.getByRole("button", { name: "Pause fixing" }).count()) === 1 && (await page.getByRole("button", { name: "Resume fixing" }).count()) === 1);
const every = page.getByLabel("Card updates every");
check("DPC-07", "Card updates every offers 10 seconds to 5 minutes",
  (await every.count()) === 1 && (await every.locator("option").allInnerTexts()).join("|") === "10 seconds|30 seconds|1 minute|5 minutes");
if (await every.count()) {
  await every.selectOption("30");
  await page.waitForTimeout(800);
  check("DPC-07", "choosing a time saves at once, with a saved note", /Saved/.test(await page.locator("body").innerText()));
  await every.selectOption("10");
  await page.waitForTimeout(500);
}
// Plug-in API 1.14 (DASH-428, DASH-432): logos in Manage, the Catalogue and the plug-in's page; every plug-in card drawn
// with the band (logo, name as the heading, a status chip and when it last updated); a job on a schedule from settings.
console.log("\n== API 1.14 Logos, the card band and job schedules");
await open("settings-plugins.html");
const dpRow = page.locator("section[aria-labelledby=pl-yours-h] li", { hasText: "Direct play" });
check("LOGO-01", "Manage shows Direct play's logo, served by Starboard, beside its name and hidden from screen readers",
  (await dpRow.locator(".app-icon.has-image img[src^='/api/plugins/direct-play/logo']").count()) === 1
  && (await dpRow.locator(".app-icon").getAttribute("aria-hidden")) === "true");
check("LOGO-01", "a plug-in without a logo shows its initials on the tile",
  (await page.locator("section[aria-labelledby=pl-yours-h] li", { hasText: "Watch statistics" }).locator(".app-icon[data-initials]").innerText()) === "WS");
const logoAnswer = await page.evaluate(async () => { const r = await fetch("/api/plugins/direct-play/logo"); return { type: r.headers.get("content-type"), csp: r.headers.get("content-security-policy"), text: await r.text() }; });
check("LOGO-02", "the logo is the cleaned SVG, sent with a policy that runs nothing",
  logoAnswer.type === "image/svg+xml" && /sandbox/.test(logoAnswer.csp) && /default-src 'none'/.test(logoAnswer.csp) && !/script/i.test(logoAnswer.text), JSON.stringify(logoAnswer).slice(0, 200));
check("LOGO-02", "a plug-in without a logo has nothing to serve", (await page.evaluate(async () => (await fetch("/api/plugins/watch-stats/logo")).status)) === 404);
await open("settings-plugins-catalogue.html");
check("LOGO-03", "a catalogue entry shows the logo catalogue.json carries, cleaned, as a data address",
  (await page.locator(".row", { hasText: "Disk forecast" }).first().locator(".app-icon img[src^='data:image/svg+xml;base64,']").count()) === 1);
await open("settings-plugin.html?id=direct-play");
check("LOGO-04", "the plug-in's page shows its logo beside the name, with its text alternative",
  (await page.locator(".plugin-head img").getAttribute("alt")) === "A play symbol on a screen" && (await page.locator(".plugin-head h1").innerText()) === "Direct play");

await open("dashboard.html");
const dpBand = page.locator('[data-card="plugin:direct-play:now"] .card-band');
await dpBand.locator(".chip").waitFor({ timeout: 8000 }).catch(() => {});
check("BAND-01", "Direct play's card has the grey band with its logo and its name as the card's heading",
  (await dpBand.locator(".app-icon img").count()) === 1 && (await dpBand.locator("h2").innerText()) === "Direct play"
  && await dpBand.evaluate((b) => getComputedStyle(b).backgroundColor !== getComputedStyle(b.parentElement).backgroundColor));
// 0.19.1 (owner, design B): the time is in a lighter grey footer at the foot of the card, so the band stays on one line.
const dpFoot = page.locator('[data-card="plugin:direct-play:now"] > .card-foot');
check("BAND-02", "the chip and the time make sense alone to a screen reader",
  (await dpBand.locator(".chip").textContent()) === "Status: Converting" && /^Updated (\d+ seconds|just now)/.test(await dpFoot.locator("time").textContent()),
  `${await dpBand.locator(".chip").textContent()} / ${await dpFoot.locator("time").textContent()}`);
check("BAND-02", "the chip sits at the right of the band", await dpBand.evaluate((b) => {
  const side = b.querySelector(".card-band__side").getBoundingClientRect(), h = b.querySelector("h2").getBoundingClientRect();
  return side.left > h.left && Math.abs(side.top + side.height / 2 - (h.top + h.height / 2)) < 12; }));
const bandHeadings = await page.evaluate(() => [...document.querySelectorAll("main h1, main h2, main h3, main h4")].map((h) => Number(h.tagName[1])));
check("BAND-03", "the page's headings stay in order: the cards' headings are h2 under the page's h1",
  bandHeadings[0] === 1 && bandHeadings.every((n, i) => i === 0 || n <= bandHeadings[i - 1] + 1), bandHeadings.join(","));
const wsBand = page.locator('[data-card="plugin:watch-stats:week"] .card-band');
check("BAND-04", "a plug-in without a logo has its initials, and without a status only the time",
  (await wsBand.locator(".app-icon[data-initials]").innerText()) === "WS" && (await wsBand.locator(".chip").count()) === 0
  && /^Updated 10 minutes ago$/.test(await page.locator('[data-card="plugin:watch-stats:week"] > .card-foot time').textContent()) && /Watched this week/.test(await wsBand.locator("h2").innerText()));
check("BAND-05", "a status with its own words keeps the chip's colour from the status",
  (await page.locator('[data-card="plugin:picture-shrinker:saved"] .card-band .chip').textContent()) === "Status: Waiting for 03:30"
  && (await page.locator('[data-card="plugin:picture-shrinker:saved"] .card-band .chip').getAttribute("data-tone")) === "neutral");
check("BAND-06", "nothing in the band is a live region, so a refresh does not interrupt", (await page.locator(".card-band [aria-live], .card-band [role=status]").count()) === 0);

// DASH-442 (owner, 15 November 2026): every built-in card has the same band as plug-in cards. A card about one app shows
// that app's own logo from the Apps page's icons (Jellyfin's for Now playing); Starboard's own cards and cards that
// combine several apps show a design system icon on the tile. A chip only where the card has something to say.
// The example server is the default install: Jellyfin, Reelix, qBittorrent and NZBGet, and Gluetun.
const exampleApps = (await api("/api/config")).services;
const appId = (test) => exampleApps.find(test)?.id;
await open("dashboard.html");
await page.locator('[data-card="health"] .card-band .chip').waitFor({ timeout: 8000 }).catch(() => {});
const builtIn = await page.evaluate(() => [...document.querySelectorAll(".dash-card:not([data-card^='plugin:'])")].map((c) => {
  const b = c.querySelector(":scope > .card-band"), h = b?.querySelector("h2");
  return { id: c.dataset.card, band: !!b, labelled: !!h && c.getAttribute("aria-labelledby") === h.id, heading: h?.textContent || "",
    logoHidden: b?.querySelector(".app-icon")?.getAttribute("aria-hidden") === "true", img: b?.querySelector(".app-icon img")?.getAttribute("src") || "",
    own: !!b?.querySelector(".app-icon > svg"), app: b?.querySelector(".app-icon")?.dataset.app || "", height: Math.round(b?.getBoundingClientRect().height || 0),
    // On a narrow card the band wraps by design, the chip and time moving under the name (the design system's .card-band).
    wrapped: !!h && b.querySelector(".card-band__side").getBoundingClientRect().top >= h.getBoundingClientRect().bottom - 1 };
}));
// Direct play's band: a plug-in card with one line of title, as every built-in card has (Watch statistics' second line,
// "Watched this week", makes its band taller).
const bandHeight = await page.locator('[data-card="plugin:direct-play:now"] .card-band').evaluate((b) => Math.round(b.getBoundingClientRect().height));
check("BAND-07", "every built-in card has the band, its name as the heading the card is labelled by, and a logo hidden from screen readers",
  builtIn.length >= 8 && builtIn.every((c) => c.band && c.labelled && c.heading && c.logoHidden), JSON.stringify(builtIn.filter((c) => !(c.band && c.labelled && c.logoHidden))));
check("BAND-07", "a built-in card's band is as tall as a plug-in card's band with one line of title", builtIn.filter((c) => !c.wrapped).length >= 6 && builtIn.filter((c) => !c.wrapped).every((c) => Math.abs(c.height - bandHeight) <= 1),
  `${bandHeight}: ${builtIn.map((c) => `${c.id} ${c.height}`).join(", ")}`);
const byId = Object.fromEntries(builtIn.map((c) => [c.id, c]));
check("BAND-08", "Now playing shows Jellyfin's own logo, the same file as the Apps page",
  byId.playing?.app === "jellyfin" && byId.playing?.img === `/api/icons/${appId((s) => s.type === "jellyfin")}?v=jellyfin`, byId.playing?.img);
// The made-up Reelix serves no logo.png, so its tile falls back to its initials, as on the Apps page.
// Earlier journeys may leave a Sonarr or Radarr beside Reelix: then Downloads and Coming up combine apps and show
// Starboard's icon. Either way the logo follows the rule.
const arrKinds = new Set(exampleApps.filter((s) => s.enabled !== false && (s.icon === "reelix" || ["sonarr", "radarr", "lidarr", "readarr"].includes(s.type)))
  .map((s) => (s.icon === "reelix" ? "reelix" : s.type)));
const arrLogo = arrKinds.size === 1 ? [...arrKinds][0] : "starboard";
check("BAND-08", `Downloads and Coming up show ${arrLogo === "reelix" ? "Reelix's logo (Reelix alone)" : "Starboard's icon (several apps)"}; VPN shows Gluetun's`,
  byId.downloads?.app === arrLogo && byId.coming?.app === arrLogo
  && byId.vpn?.app === "gluetun" && byId.vpn?.img === `/api/icons/${appId((s) => s.type === "gluetun")}?v=gluetun`, JSON.stringify(builtIn.map((c) => [c.id, c.app, c.img])));
check("BAND-08", "Starboard's own cards show a design system icon on the tile",
  ["disk", "load", "alerts", "health", "setup"].filter((k) => byId[k]).every((k) => byId[k].own && byId[k].app === "starboard" && !byId[k].img), JSON.stringify(builtIn.map((c) => [c.id, c.own, c.app])));
const healthChip = (await page.locator('[data-card="health"] .card-band .chip').textContent()) || "";
check("BAND-09", "Service health's state is a chip in the band, in words with no number, and the footer says when it was updated",
  /^Status: (Running|Not responding)$/.test(healthChip) && /^Updated /.test(await page.locator('[data-card="health"] > .card-foot time').textContent()), healthChip);
check("BAND-09", "a card with nothing to say has no chip and no time (Recently added, kept by the server for 5 minutes)",
  (await page.locator('[data-card="recent"] .card-band__side > *').count()) === 0
  && (await page.locator('[data-card="recent"] > .card-foot').count()) === 0);
const healthBefore = (await page.evaluate(() => [...document.querySelectorAll(".dash-card")].map((c) => c.dataset.card))).indexOf("health");
await page.getByRole("button", { name: "Edit dashboard" }).click();
await page.locator('[data-card="health"] .dash-card__tools').waitFor({ timeout: 5000 }).catch(() => {});
check("BAND-10", "Edit dashboard keeps each built-in card's band and heading, with the card's tools under the band",
  await page.locator('[data-card="health"]').evaluate((c) => c.querySelector(":scope > .card-band + .dash-card__head .dash-card__tools") !== null
    && c.getAttribute("aria-labelledby") === c.querySelector(".card-band h2")?.id));
await page.getByRole("button", { name: "Move Service health later" }).click();
const healthAfter = (await page.evaluate(() => [...document.querySelectorAll(".dash-card")].map((c) => c.dataset.card))).indexOf("health");
check("BAND-10", "Move later moves a banded card and keeps focus in it",
  healthAfter === healthBefore + 1 && await page.evaluate(() => !!document.activeElement?.closest("[data-card='health']")), `${healthBefore} to ${healthAfter}`);
await page.getByRole("button", { name: "Cancel" }).click();

// DASH-443 (owner, 15 November 2026): Still to set up's Go through them sits at the right of its band, and focus comes
// back to it when the slide-out closes; a plug-in card shows its own title for its size (plug-in API 1.15), on one
// line, also after its size is changed in Edit dashboard; a small card shows only its chip's icon, the words kept for
// screen readers. Picture shrinker's card in the example server has a title for each size.
console.log("\n== TTL Titles for each card size, and the set-up button in the band");
await open("dashboard.html");
const setupCard = page.locator('[data-card="setup"]');
const walkButton = setupCard.locator(".card-band .card-band__side button");
await walkButton.waitFor({ timeout: 8000 }).catch(() => {});
check("TTL-01", "Go through them is in Still to set up's band, at its right", (await walkButton.innerText().catch(() => "")) === "Go through them"
  && await setupCard.evaluate((c) => { const b = c.querySelector(".card-band").getBoundingClientRect(), x = c.querySelector(".card-band__side button").getBoundingClientRect();
    return x.right > b.right - 40 && x.top >= b.top && x.bottom <= b.bottom; }));
check("TTL-01", "the card's heading comes before the button, and the button before the list", await setupCard.evaluate((c) => {
  const h = c.querySelector("h2"), x = c.querySelector(".card-band__side button"), list = c.querySelector(".dash-card__body ul");
  return !!(h && x && list) && !!(h.compareDocumentPosition(x) & Node.DOCUMENT_POSITION_FOLLOWING) && !!(x.compareDocumentPosition(list) & Node.DOCUMENT_POSITION_FOLLOWING); }));
await walkButton.focus();
await page.keyboard.press("Enter");
await page.locator("#side-panel h3").waitFor({ timeout: 5000 }).catch(() => {});
// On a busy server the slide-out can be drawn a moment before it moves focus to its heading; wait for that, as a
// person would, so Escape reaches the slide-out (release 0.19.1 checks, 16 November 2026).
await page.waitForFunction(() => document.activeElement?.closest?.("#side-panel"), null, { timeout: 5000 }).catch(() => {});
const walkOpened = await page.locator("#side-panel").count() === 1;
await page.keyboard.press("Escape");
await page.waitForFunction(() => document.activeElement?.closest?.('[data-card="setup"] .card-band__side'), null, { timeout: 5000 }).catch(() => {});
check("TTL-02", "closing the slide-out gives focus back to Go through them", walkOpened && await page.evaluate(() =>
  document.activeElement?.textContent?.trim() === "Go through them" && !!document.activeElement.closest('[data-card="setup"] .card-band__side')),
  await page.evaluate(() => document.activeElement?.outerHTML?.slice(0, 120)));
// Escape pressed inside the step's page (the slide-out's frame) closes the slide-out too (16 November 2026).
const walkAgain = page.locator('[data-card="setup"] .card-band__side button', { hasText: "Go through them" });
await walkAgain.focus();
await page.keyboard.press("Enter");
const escFrame = page.frameLocator("#side-panel iframe");
await escFrame.locator("body").waitFor({ timeout: 8000 }).catch(() => {});
// A click on the step's page (its heading, so nothing opens) is the person's own move: focus stays in the page.
const frames = await page.locator("#side-panel iframe").count();
let clickErr = "";
await escFrame.locator("body").click({ position: { x: 24, y: 24 }, timeout: 8000 }).catch((e) => { clickErr = String(e.message || e).split("\n")[0]; });
await page.waitForTimeout(2500);  // past the wizard's own guard against the page taking focus as it loads
const focusInFrame = await page.evaluate(() => document.activeElement?.tagName === "IFRAME");
await page.keyboard.press("Escape");
await page.waitForFunction(() => !document.querySelector("#side-panel"), null, { timeout: 5000 }).catch(() => {});
await page.waitForFunction(() => document.activeElement?.closest?.('[data-card="setup"] .card-band__side'), null, { timeout: 5000 }).catch(() => {});
check("TTL-02", "a click in the step's page keeps focus there, and Escape there closes the slide-out and gives focus back to Go through them",
  focusInFrame && (await page.locator("#side-panel").count()) === 0
  && await page.evaluate(() => document.activeElement?.textContent?.trim() === "Go through them"),
  `frames: ${frames}; click: ${clickErr || "ok"}; in frame: ${focusInFrame}; ${await page.evaluate(() => document.activeElement?.outerHTML?.slice(0, 100))}`);
const psTitles = (await api("/api/plugins/cards")).cards.find((c) => c.id === "plugin:picture-shrinker:saved")?.titles || {};
check("TTL-03", "Picture shrinker's card hands the dashboard a title for each size", ["small", "medium", "half", "wide", "full"].every((k) => psTitles[k]), JSON.stringify(psTitles));
const dashKept = (await api("/api/config")).dashboard;
for (const size of ["small", "medium", "half", "wide", "full"]) {
  await api("/api/config/general", { method: "PUT", body: { dashboard: { layout: dashKept.layout,
    cards: [{ id: "plugin:picture-shrinker:saved", size }, { id: "disk", size: "small" }, { id: "load", size: "small" }] } } });
  await open("dashboard.html");
  const ps = page.locator('[data-card="plugin:picture-shrinker:saved"]');
  await ps.locator(".card-band .chip").waitFor({ timeout: 8000 }).catch(() => {});
  const got = await ps.evaluate((c) => {
    const h = c.querySelector(".card-band h2"), lh = parseFloat(getComputedStyle(h).lineHeight) || 20;
    const words = c.querySelector(".chip__words");
    return { shown: h.firstChild?.textContent.trim(), heard: h.textContent.trim(), lines: Math.round(h.getBoundingClientRect().height / lh),
      labelled: c.getAttribute("aria-labelledby") === h.id, wordsWidth: words ? words.getBoundingClientRect().width : -1,
      chip: c.querySelector(".card-band .chip")?.textContent || "", time: !!c.querySelector(":scope > .card-foot time") };
  });
  check("TTL-04", `a ${size} card shows its ${size} title on one line, its name for screen readers after it`,
    got.shown === psTitles[size] && got.lines === 1 && got.labelled && got.heard.includes("Picture shrinker"), JSON.stringify(got));
  check("TTL-05", `a ${size} card's chip shows ${size === "small" ? "only its icon, its words kept for screen readers" : "its words"}, with the time`,
    got.chip === "Status: Waiting for 03:30" && got.time && (size === "small" ? got.wordsWidth <= 1 : got.wordsWidth > 20), JSON.stringify(got));
}
// Edit dashboard: changing the size draws the card's title for its new size, and focus stays on its size list.
await page.getByRole("button", { name: "Edit dashboard" }).click();
const psSize = page.locator('[data-card="plugin:picture-shrinker:saved"] .dash-card__tools select');
await psSize.waitFor({ timeout: 5000 }).catch(() => {});
await psSize.selectOption("small");
await page.waitForTimeout(300);
check("TTL-06", "in Edit dashboard a new size shows that size's title, and its size list keeps focus",
  (await page.locator('[data-card="plugin:picture-shrinker:saved"] .card-band h2').evaluate((h) => h.firstChild?.textContent)) === psTitles.small
  && await page.evaluate(() => document.activeElement?.tagName === "SELECT" && !!document.activeElement.closest('[data-card="plugin:picture-shrinker:saved"]'))
  && (await page.locator('[data-card="plugin:picture-shrinker:saved"] .dash-card__tools select').getAttribute("aria-label")) === `Size of ${psTitles.small} (Picture shrinker)`);
await page.getByRole("button", { name: "Cancel" }).click();
await api("/api/config/general", { method: "PUT", body: { dashboard: { layout: dashKept.layout, cards: dashKept.cards || null } } });

await open("settings-plugin.html?id=picture-shrinker");
const schedOften = page.getByLabel("How often", { exact: true });
check("SCH-01", "the schedule setting shows how often, the date and the time, from its default",
  (await schedOften.inputValue()) === "month" && (await page.getByLabel("Date", { exact: true }).inputValue()) === "31" && (await page.getByLabel("Time", { exact: true }).inputValue()) === "03:30"
  && !(await page.getByLabel("Day", { exact: true }).isVisible()));
const schedHeights = await page.evaluate(() => [...document.querySelectorAll(".schedule-fields select, .schedule-fields input")].filter((c) => c.offsetParent).map((c) => Math.round(c.getBoundingClientRect().height)));
check("SCH-01", "the side-by-side controls share one height", schedHeights.length === 3 && new Set(schedHeights).size === 1, schedHeights.join(","));
await schedOften.selectOption("week");
await page.waitForTimeout(700);
check("SCH-02", "Every week shows the day, saves at once and says so", await page.getByLabel("Day", { exact: true }).isVisible() && /Saved/.test(await page.locator(".setting--schedule").innerText()));
await page.getByLabel("Day", { exact: true }).selectOption("tuesday");
await page.waitForTimeout(500);
await page.getByLabel("Time", { exact: true }).fill("04:15");
await page.getByLabel("Time", { exact: true }).dispatchEvent("change");
await page.waitForTimeout(700);
const schedSaved = (await api("/api/plugins")).plugins.find((p) => p.id === "picture-shrinker").settings.find((x) => x.key === "when").value;
check("SCH-02", "the schedule is kept as the person set it, with nothing stray", JSON.stringify(schedSaved) === '{"every":"week","time":"04:15","day":"tuesday"}', JSON.stringify(schedSaved));
check("SCH-02", "focus stays on the control just used", await page.evaluate(() => document.activeElement?.id === "pl-picture-shrinker-when-time"));
const schedBad = await page.evaluate(async () => (await fetch("/api/plugins/picture-shrinker/settings", { method: "PUT", headers: { "Content-Type": "application/json", "X-Starboard": "1" },
  body: JSON.stringify({ settings: { when: { every: "week", time: "04:15" } } }) })).json());
check("SCH-03", "Starboard checks a schedule and says what is wrong in plain words", schedBad.error === "When to shrink: needs a day of the week", JSON.stringify(schedBad));
await open("system.html");
const schedJob = page.locator("#jobs li", { hasText: "Picture shrinker: Shrink pictures" });
await schedJob.waitFor({ timeout: 8000 }).catch(() => {});
check("SCH-04", "System, Jobs shows the schedule in words and when it runs next",
  /Every week on Tuesday at 04:15, next Tuesday \d{1,2} \w+ at 04:15/.test(await schedJob.innerText()), await schedJob.innerText().catch(() => ""));
await schedJob.getByRole("button", { name: /Run now/ }).click();
await page.waitForTimeout(2500);
check("SCH-05", "Run now works as for any other job", /Shrank 0 pictures/.test(await page.locator("#jobs li", { hasText: "Picture shrinker" }).innerText()));
await api("/api/plugins/picture-shrinker/settings", { method: "PUT", body: { settings: { when: { every: "month", date: 31, time: "03:30" } } } });

// PUP: a plug-in that updates safely (plug-in API 1.14, DASH-424). Picture shrinker 1.1.0 is in a made-up catalogue,
// with its changes, a settings migration and a before and an after step that answer here; nothing is fetched.
console.log("\n== PUP Plug-in updates and What is new");
await api("/api/plugins/picture-shrinker/settings", { method: "PUT", body: { settings: { poster_height: 1200 } } });
await open("settings-plugin.html?id=picture-shrinker");
const pupGo = page.getByRole("button", { name: "Update to 1.1.0…" }).first();
check("PUP-01", "a newer version in a catalogue offers Update on the plug-in's page", (await pupGo.count()) === 1);
await pupGo.click();
const pupWarn = page.getByRole("dialog", { name: "Update Picture shrinker to 1.1.0?" });
await pupWarn.waitFor({ timeout: 8000 }).catch(() => {});
const pupNew = pupWarn.locator("section[aria-labelledby=pl-update-new-h]");
check("PUP-01", "before updating, What is new since 1.0.0 lists the new version's own changes",
  (await pupNew.getByRole("heading", { name: "What is new since 1.0.0" }).count()) === 1
  && /Photos of people/.test(await pupNew.innerText()) && /Version 1\.1\.0/.test(await pupNew.innerText()), await pupNew.innerText().catch(() => ""));
const pupSafe = await pupWarn.locator("section[aria-labelledby=pl-update-safe-h]").innerText().catch(() => "");
check("PUP-01", "and how it is kept safe: the settings that move, the step before, the health wait and Roll back",
  /poster_height is now max_poster_height/.test(pupSafe) && /finish or pause its work first/.test(pupSafe)
  && /waits up to 30 seconds/.test(pupSafe) && /Version 1\.0\.0 is kept/.test(pupSafe), pupSafe);
await page.locator("#pl-install-password").fill(password);
await pupWarn.getByRole("button", { name: "Update Picture shrinker", exact: true }).click();
const pupRun = page.getByRole("dialog", { name: "Updating Picture shrinker to 1.1.0" });
await pupRun.waitFor({ timeout: 8000 }).catch(() => {});
check("PUP-02", "the update opens its steps with focus on the heading",
  await page.evaluate(() => document.activeElement?.textContent === "Updating Picture shrinker to 1.1.0"));
await pupRun.locator(".notice__title", { hasText: "Picture shrinker is updated" }).waitFor({ timeout: 20000 }).catch(() => {});
const pupSteps = await pupRun.locator(".task-list__item").allInnerTexts();
check("PUP-02", "each step is done: ready, settings, install, health and tidy up",
  (await pupRun.locator(".task-list__item[data-state=done]").count()) === 5 && /Moving its settings/.test(pupSteps.join(" ")), pupSteps.join(" | "));
check("PUP-02", "the result is focused and said in the live region",
  await page.evaluate(() => document.activeElement?.closest(".notice")?.textContent.includes("Picture shrinker is updated"))
  && /Picture shrinker is updated/.test(await pupRun.locator("[role=status][aria-live=polite]").textContent()));
await pupRun.getByRole("button", { name: "Done" }).click();
await page.waitForTimeout(400);
check("PUP-03", "closing it takes focus to the plug-in's State", await page.evaluate(() => document.activeElement?.id === "pl-picture-shrinker-state-h"));
const pupAfter = (await api("/api/plugins")).plugins.find((p) => p.id === "picture-shrinker");
check("PUP-03", "the settings moved to the new key with the value chosen", pupAfter.version === "1.1.0"
  && pupAfter.settings.find((x) => x.key === "max_poster_height")?.value === 1200, JSON.stringify(pupAfter.settings.map((x) => [x.key, x.value])));
const pupWn = page.locator("#pl-picture-shrinker-whats-new");
check("PUP-04", "after the update, State shows What is new in 1.1.0", /What is new in 1\.1\.0/.test(await pupWn.innerText().catch(() => "")));
await page.getByRole("button", { name: "Roll back to 1.0.0" }).first().click();
await page.locator("#pl-rb-picture-shrinker").fill(password);
await page.getByRole("dialog", { name: "Roll back Picture shrinker to 1.0.0?" }).getByRole("button", { name: "Roll back", exact: true }).click();
const pupBack = page.getByRole("dialog", { name: "Rolling Picture shrinker back to 1.0.0" });
await pupBack.locator(".notice__title", { hasText: "Picture shrinker is back on 1.0.0" }).waitFor({ timeout: 20000 }).catch(() => {});
check("PUP-05", "Roll back runs as steps and ends back on 1.0.0", (await pupBack.locator(".notice__title").textContent().catch(() => "")) === "Picture shrinker is back on 1.0.0");
await pupBack.getByRole("button", { name: "Done" }).click();
await page.waitForTimeout(400);
const pupBefore = (await api("/api/plugins")).plugins.find((p) => p.id === "picture-shrinker");
check("PUP-05", "with the settings as they were before the update", pupBefore.version === "1.0.0"
  && pupBefore.settings.find((x) => x.key === "poster_height")?.value === 1200 && !pupBefore.whats_new);
check("PUP-05", "and focus back on State", await page.evaluate(() => document.activeElement?.id === "pl-picture-shrinker-state-h"));
await open("settings-security-keys.html");
await page.getByRole("button", { name: "Make a key" }).first().click();
const pupBox = page.getByRole("checkbox", { name: /^Updates/ });
check("PUP-06", "Make a key offers Updates, only given when ticked", (await pupBox.count()) === 1 && !(await pupBox.isChecked()));
await page.keyboard.press("Escape");

// UPD: Settings, Updates as the one place (DASH-417, DASH-420, DASH-422). The example server has a newer made-up
// release whose update only writes update.sh's lines, a newer Reelix, a newer plug-in, three recent updates and a
// stand-in Jellyfin with a newer Playback Reporting, so nothing is fetched or restarted.
console.log("\n== UPD Settings, Updates");
await open("settings-updates.html");
await page.locator("#updates-list:not([aria-busy])").waitFor({ timeout: 5000 }).catch(() => {});
const ready = await page.locator("#up-list-summary").textContent();
check("UPD-05", "Ready to update says in a live region what is ready", /updates are ready: .*Starboard/.test(ready)
  && (await page.locator("#up-list-summary[role=status]").count()) === 1, ready);
check("UPD-05", "Starboard waits for you; the plug-in updates by itself", (await page.locator('[data-key="starboard"]').textContent()).includes("Waits for you")
  && (await page.locator('[data-key="plugin:picture-shrinker"]').textContent()).includes("Updates by itself"));
const autoSwitches = page.locator("#updates-auto").getByRole("switch");
check("UPD-01", "Update by themselves has a switch for each of the five parts", (await autoSwitches.count()) === 5);
const auto = page.getByRole("switch", { name: "Starboard: update by itself" });
check("UPD-01", "Starboard's is deactivated by default", (await auto.count()) === 1 && !(await auto.isChecked()));
check("UPD-01", "the hours are a choice, the download hours first", (await page.locator("#updates-auto input[type=radio]").count()) === 2
  && await page.locator('#updates-auto input[value="download"]').isChecked());
check("UPD-05", "Recent updates lists what each did, by whom", (await page.locator("#updates-recent li").count()) >= 3
  && (await page.locator("#updates-recent").textContent()).includes("updated by itself"));
// UPD-09 Check for updates (DASH-462): it asks every part now, says what it found in the live region, and focus stays
// on the button. The stand-in Jellyfin has a newer Playback Reporting, which only Jellyfin knows about until asked.
const checkBtn = page.locator("#check-updates-now");
check("UPD-09", "Ready to update has Check for updates", (await checkBtn.count()) === 1 && (await checkBtn.textContent()).trim() === "Check for updates");
check("UPD-09", "nothing asks Jellyfin which plug-ins are new before it is pressed", !(await page.locator("#up-list-summary").textContent()).includes("Playback Reporting"));
await checkBtn.focus();
await page.keyboard.press("Enter");
await page.locator("#up-list-summary", { hasText: "Checked at" }).waitFor({ timeout: 30000 }).catch(() => {});
const checkedSays = await page.locator("#up-list-summary").textContent();
check("UPD-09", "it says in the live region when it checked and what is ready, Jellyfin's plug-ins too", /^Checked at \d\d:\d\d\. \d+ updates are ready: .*Playback Reporting 20\.0\.0\.0 for Jellyfin/.test(checkedSays), checkedSays);
check("UPD-09", "focus stays on Check for updates", await page.evaluate(() => document.activeElement?.id === "check-updates-now"));
check("UPD-09", "Jellyfin's row names the new version", (await page.locator('[data-key="jellyfin-plugins"]').textContent()).includes("New versions: Playback Reporting 20.0.0.0"));
const readyNow = (checkedSays.match(/(\d+) updates are ready/) || [])[1];
check("UPD-09", "Install all updates counts what the check found", (await page.locator("#install-all").textContent()).trim() === `Install all ${readyNow} updates`, readyNow);

// UPD-10 What is new (DASH-462): one slide-out with the notes of every waiting update, by item, under Added, Changed,
// Fixed and Security; an item without notes says so; a jump link takes focus to its item; Escape gives focus back.
await page.locator("#whats-new").click();
const wnPanel = page.getByRole("dialog", { name: /^What is new in \d+ updates$/ });
await wnPanel.locator("h3").first().waitFor({ timeout: 15000 }).catch(() => {});
const wnHeads = await wnPanel.locator("section.release-notes > .release-notes__head > h3").allTextContents();
// DASH-475: each item has its own picture beside its heading, decorative since the name is beside it.
const wnPics = await wnPanel.locator(".release-notes__head > .app-icon").evaluateAll((n) => n.map((x) => [x.getAttribute("aria-hidden"), x.querySelector("img")?.getAttribute("alt") ?? null]));
check("UPD-10", "each plug-in and Starboard has its picture beside its name, hidden from screen readers", wnPics.length >= 2
  && wnPics.every(([hidden, alt]) => hidden === "true" && (alt === null || alt === "")), JSON.stringify(wnPics));
check("UPD-10", "it lists Starboard first, then Reelix and the plug-ins, each from the version you have to the new one",
  /^Starboard \d+\.\d+\.\d+ to \d+\.\d+\.\d+$/.test(wnHeads[0] || "") && /^Reelix 0\.7\.1 to 0\.7\.2$/.test(wnHeads[1] || "")
  && wnHeads.includes("Picture shrinker 1.0.0 to 1.1.0") && wnHeads.includes("Playback Reporting 19.0.0.0 to 20.0.0.0"), wnHeads.join(" / "));
const sbKinds = await wnPanel.locator("section.release-notes").first().locator("h4").allTextContents();
check("UPD-10", "Starboard's notes are under Added, Changed, Fixed and Security", sbKinds.join(",") === "Added,Changed,Fixed,Security", sbKinds.join(","));
const psKinds = await wnPanel.locator("section.release-notes", { hasText: "Picture shrinker 1.0.0" }).locator("h4").allTextContents();
check("UPD-10", "a plug-in's notes come from its new manifest", psKinds.join(",") === "Added,Changed,Fixed" && (await wnPanel.textContent()).includes("Photos of people"), psKinds.join(","));
check("UPD-10", "an item with no notes says so plainly", /Starboard has no notes for [^.]+\. Its maker lists what changed on its release page\.|Starboard has no notes for [^,]+, and does not know where its maker lists them\./.test(await wnPanel.textContent()), (await wnPanel.textContent()).slice(0, 400));
check("UPD-10", "the release page links open in a new tab and say so", (await wnPanel.locator('a[target="_blank"]').count()) >= 2
  && (await wnPanel.locator('a[target="_blank"] .visually-hidden').first().textContent()).includes("opens in a new tab"));
await wnPanel.getByRole("navigation", { name: "Updates in this list" }).getByRole("link", { name: /^Reelix / }).click();
check("UPD-10", "a jump link takes focus to its item's heading", await page.evaluate(() => document.activeElement?.tagName === "H3" && document.activeElement.textContent.startsWith("Reelix")));
await page.keyboard.press("Escape");
await page.waitForTimeout(400);
check("UPD-10", "Escape closes it and focus returns to What is new", (await page.locator("#side-panel").count()) === 0 && await page.evaluate(() => document.activeElement?.id === "whats-new"));

// UPD-11 Install all updates with only one update waiting (DASH-462: it was shown only from two).
await page.route("**/api/updates", async (route) => {
  const r = await route.fetch();
  const body = await r.json();
  let kept = false;
  body.items = body.items.map((t) => { if (t.update_available && !kept) { kept = true; return t; } return { ...t, update_available: false }; });
  body.jellyfin_waiting = [];
  await route.fulfill({ response: r, json: body });
});
await open("settings-updates.html");
await page.locator("#updates-list:not([aria-busy])").waitFor({ timeout: 5000 }).catch(() => {});
check("UPD-11", "one update waiting still offers Install 1 update and What is new", (await page.locator("#install-all").textContent().catch(() => "")).trim() === "Install 1 update"
  && (await page.locator("#whats-new").count()) === 1);
await page.unroute("**/api/updates");
await open("settings-updates.html");
await page.locator("#updates-list:not([aria-busy])").waitFor({ timeout: 5000 }).catch(() => {});

const appsAuto = page.getByRole("switch", { name: "Your other apps: update by itself" });
await appsAuto.check();
await page.waitForTimeout(500);
check("UPD-07", "a part's switch saves at once", (await api("/api/config")).apps_auto_update === true);
await appsAuto.uncheck();
await page.waitForTimeout(500);
const goNow = page.locator('[data-key="starboard"]').getByRole("button", { name: "Update now" });
check("UPD-02", "a newer release offers Update now on Starboard's row", (await goNow.count()) === 1);
await goNow.click();
const ask = page.getByRole("dialog");
check("UPD-02", "Update now asks for the password first, with focus in the field",
  await page.evaluate(() => document.activeElement?.id === "su-password"));
await page.locator("#su-password").fill("not-the-password");
await ask.getByRole("button", { name: "Update now" }).click();
await page.locator("#su-password-error:not([hidden])").waitFor({ timeout: 5000 }).catch(() => {});
check("UPD-02", "a wrong password is said under the field, and nothing starts",
  /not right/.test(await page.locator("#su-password-error").textContent()) && !(await api("/api/self-update")).running);
{ const expected = problems.filter((x) => !(/settings-updates\.html: .*\b401\b/.test(x)));  // the wrong password just tried
  problems.splice(0, problems.length, ...expected); }
await page.locator("#su-password").fill(password);
await page.getByRole("dialog").getByRole("button", { name: "Update now" }).click();
const progress = page.getByRole("dialog", { name: "Updating Starboard" });
await progress.waitFor({ timeout: 5000 });
check("UPD-03", "the progress dialog opens with focus on its heading",
  await page.evaluate(() => document.activeElement?.textContent === "Updating Starboard"));
await progress.locator(".notice__title", { hasText: "Starboard is updated" }).waitFor({ timeout: 20000 }).catch(() => {});
check("UPD-03", "it follows each step and ends with the result, focused",
  (await progress.locator(".task-list__item[data-state=done]").count()) === 6
  && await page.evaluate(() => document.activeElement?.closest(".notice")?.textContent.includes("Starboard is updated")));
await progress.getByRole("button", { name: "Done" }).click();
check("UPD-03", "closing it takes focus to Ready to update, as Update now is gone", await page.evaluate(() => document.activeElement?.id === "up-list-h"));
check("UPD-03", "the page says how it ended", (await page.locator("#self-update-result").textContent()).includes("Starboard is updated"));
const back = await api("/api/self-update");
check("UPD-04", "the record says who started it and how it ended", back.update?.by === "you" && back.update?.outcome === "updated", JSON.stringify(back.update));
// Jellyfin's plug-ins from the same place, with the same password dialog and progress (DASH-422).
const jfGo = page.locator('[data-key="jellyfin-plugins"]').getByRole("button", { name: "Check for updates and install them" });
await jfGo.waitFor({ timeout: 5000 }).catch(() => {});
await jfGo.click();
await page.getByRole("dialog").locator("input[type=password]").fill(password);
await page.getByRole("dialog").getByRole("button", { name: "Update now" }).click();
const jfProgress = page.getByRole("dialog", { name: "Updating Jellyfin's plug-ins" });
await jfProgress.waitFor({ timeout: 5000 }).catch(() => {});
await jfProgress.locator(".notice__title").waitFor({ timeout: 45000 }).catch(() => {});
check("UPD-06", "Jellyfin's plug-ins update with each step and end with what is new, focused",
  (await jfProgress.locator(".notice").textContent()).includes("Playback Reporting 19.0.0.0 to 20.0.0.0")
  && await page.evaluate(() => !!document.activeElement?.closest(".notice")));
await jfProgress.getByRole("button", { name: "Done" }).click();
check("UPD-06", "and it is in Recent updates", (await page.locator("#updates-recent").textContent()).includes("Jellyfin's plug-ins"));

// UPD-08 Install all updates (DASH-454): with more than one update waiting, one button says how many; a wrong
// password is said in the dialog; the list says what installs in order; the panel follows each update to the end,
// with words and icons for each state, and Recent updates records the batch.
const allBtn = page.locator("#install-all");
await allBtn.waitFor({ timeout: 5000 }).catch(() => {});
check("UPD-08", "Install all updates says how many are waiting", /^Install all \d+ updates$/.test((await allBtn.textContent().catch(() => "")).trim()));
await allBtn.click();
await page.getByRole("dialog").locator("input[type=password]").fill("not-the-password");
await page.getByRole("dialog").getByRole("button", { name: "Continue" }).click();
await page.getByRole("dialog").locator(".field-error:not([hidden])").waitFor({ timeout: 5000 }).catch(() => {});
check("UPD-08", "a wrong password is said under the field", /not right/.test(await page.getByRole("dialog").locator(".field-error").textContent().catch(() => "")));
{ const expected = problems.filter((x) => !(/settings-updates\.html: .*\b401\b/.test(x)));
  problems.splice(0, problems.length, ...expected); }
await page.getByRole("dialog").locator("input[type=password]").fill(password);
await page.getByRole("dialog").getByRole("button", { name: "Continue" }).click();
const allAsk = page.getByRole("dialog", { name: /^Install \d+ updates?$/ });
await allAsk.waitFor({ timeout: 10000 }).catch(() => {});
const allOrder = await allAsk.locator("ol li").allTextContents();
const allTitle = (await allAsk.locator("h2").textContent()).trim();
check("UPD-08", "the dialog's title, its button and its list count the same updates", allTitle === `Install ${allOrder.length} updates`
  && (await allAsk.getByRole("button", { name: allTitle, exact: true }).count()) === 1, `${allTitle} / ${allOrder.length}`);
check("UPD-08", "the list puts Starboard last", allOrder.length >= 2 && /^Starboard /.test(allOrder[allOrder.length - 1]), allOrder.join(" / "));
await allAsk.getByRole("button", { name: /^Install \d+ updates?$/ }).click();
await page.locator(".update-all .notice").waitFor({ timeout: 90000 }).catch(() => {});
const batchItems = await page.locator(".update-all .task-list__item").evaluateAll((li) => li.map((n) => [n.dataset.state, n.querySelector(".chip")?.textContent, !!n.querySelector(".chip svg")]));
check("UPD-08", "each update ends with its state in words and an icon", batchItems.length >= 2 && batchItems.every(([st, w, ic]) => st && w && ic), JSON.stringify(batchItems));
check("UPD-08", "the panel counts the same updates as the dialog", new RegExp(`^${allOrder.length} of ${allOrder.length} done$`).test((await page.locator("#update-all-count .numeric").textContent()).trim()));
// #161: at the end the words say how it ended, never "Updates finished" while it works, and the bar stops moving.
const allLabel = (await page.locator("#update-all-count > span").first().textContent()).trim();
check("UPD-08", "the panel says how it ended and its bar stops moving", /^(All updates finished|Some updates did not install|The updates stopped)$/.test(allLabel)
  && !(await page.locator(".update-all .progress").evaluate((n) => n.classList.contains("progress--running"))), allLabel);
// DASH-473: Close takes the finished panel away, focus goes to Ready to update, and it is announced.
await page.locator("#update-all-close").click();
await page.waitForTimeout(300);
check("UPD-08", "Close takes the panel away and focus goes to Ready to update", (await page.locator(".update-all").count()) === 0
  && await page.evaluate(() => document.activeElement?.id === "up-list-h"));
check("UPD-08", "closing it is announced", /Install all updates closed/.test(await page.locator("#announcer").textContent()));
await page.waitForTimeout(1500);
check("UPD-08", "Recent updates records the batch as All updates", (await page.locator("#updates-recent").textContent()).includes("All updates"));
const allRuns = await api("/api/updates");
check("UPD-08", "the batch is in the record, and nothing is left running", allRuns.recent.some((r) => r.kind === "batch" && r.state !== "running") && !allRuns.running, JSON.stringify(allRuns.running));

// Batch 0.19, plug-in API 1.15: a plug-in from a zip file (DASH-414), updated from one, and Jellyfin's metadata moved
// out of its settings folder (DASH-431). The example server never reaches Docker: its build is made up.
console.log("\n== ZIP Plug-ins from a zip file");
function crc32(buf) {
  let c, crc = 0xffffffff;
  for (const b of buf) { c = (crc ^ b) & 0xff; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; crc = (crc >>> 8) ^ c; }
  return (crc ^ 0xffffffff) >>> 0;
}
function storedZip(files) {  // a plain zip with no packing, enough for Starboard's checks
  const parts = [], central = [];
  let offset = 0;
  for (const [name, text] of Object.entries(files)) {
    const n = Buffer.from(name), d = Buffer.from(text), crc = crc32(d);
    const head = Buffer.alloc(30); head.writeUInt32LE(0x04034b50, 0); head.writeUInt16LE(20, 4); head.writeUInt32LE(crc, 14);
    head.writeUInt32LE(d.length, 18); head.writeUInt32LE(d.length, 22); head.writeUInt16LE(n.length, 26);
    const cen = Buffer.alloc(46); cen.writeUInt32LE(0x02014b50, 0); cen.writeUInt16LE(0x031e, 4); cen.writeUInt16LE(20, 6);
    cen.writeUInt32LE(crc, 16); cen.writeUInt32LE(d.length, 20); cen.writeUInt32LE(d.length, 24); cen.writeUInt16LE(n.length, 28);
    cen.writeUInt32LE((0o100644 << 16) >>> 0, 38); cen.writeUInt32LE(offset, 42);
    parts.push(head, n, d); central.push(cen, n); offset += 30 + n.length + d.length;
  }
  const cd = Buffer.concat(central), end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0); end.writeUInt16LE(central.length / 2, 8); end.writeUInt16LE(central.length / 2, 10);
  end.writeUInt32LE(cd.length, 12); end.writeUInt32LE(offset, 16);
  return Buffer.concat([...parts, cd, end]);
}
const zipManifest = (version) => JSON.stringify({ manifest_version: 1, id: "zip-hello", name: "Zip hello", version, author: "TheMightyTRexUK",
  description: "A made-up plug-in from a zip file, built from its own Dockerfile.", licence: "MIT", homepage: "https://example.invalid/zip-hello",
  support_url: "https://example.invalid/zip-hello/issues", starboard_api: ">=1.15 <2.0", permissions: [],
  containers: [{ name: "main", image: `local/zip-hello:${version}`, build: true, port: 8080 }] });
const zipFile = (version, extra = {}) => ({ name: `zip-hello-${version}.zip`, mimeType: "application/zip",
  buffer: storedZip({ "starboard-plugin.json": zipManifest(version), Dockerfile: "FROM python:3.12-alpine\nCOPY app.py /app.py\nUSER 1000:1000\nCMD [\"python3\", \"/app.py\"]\n", "app.py": "print('hello')\n", ...extra }) });
await open("settings-plugins-catalogue.html");
const zipSec = page.locator('section[aria-labelledby="pl-zip-h"]');
check("ZIP-01", "the Catalogue has Upload a zip file, with a labelled file field", (await zipSec.count()) === 1
  && (await zipSec.getByLabel("The plug-in's zip file").count()) === 1);
await zipSec.getByRole("button", { name: "Check the zip" }).click();
check("ZIP-02", "Check the zip with no file says so on the field and keeps focus there",
  /Choose the plug-in's zip file/.test(await zipSec.innerText()) && await page.evaluate(() => document.activeElement?.id === "pl-zip"));
await zipSec.getByLabel("The plug-in's zip file").setInputFiles(zipFile("1.0.0", { "../evil.sh": "x" }));
await zipSec.getByRole("button", { name: "Check the zip" }).click();
await page.waitForTimeout(800);
check("ZIP-03", "a zip with a name outside it is refused before anything is shown", /points outside the zip/.test(await zipSec.innerText()));
await zipSec.getByLabel("The plug-in's zip file").setInputFiles(zipFile("1.0.0"));
await zipSec.getByRole("button", { name: "Check the zip" }).click();
await zipSec.getByRole("heading", { name: "Zip hello 1.0.0" }).waitFor({ timeout: 8000 }).catch(() => {});
const zipSaid = await zipSec.innerText();
check("ZIP-04", "a good zip shows what was checked, the image the build starts from, and focus goes to its name",
  /Checked: 3 files/.test(zipSaid) && /starting from python:3\.12-alpine/.test(zipSaid)
  && await page.evaluate(() => document.activeElement?.textContent === "Zip hello 1.0.0"), zipSaid.slice(0, 300));
await zipSec.getByRole("button", { name: "Install Zip hello…" }).click();
const zipWarn = page.getByRole("dialog", { name: "Install Zip hello?" });
await zipWarn.waitFor({ timeout: 8000 }).catch(() => {});
check("ZIP-05", "the warning says Starboard builds its image from the zip, with its limits",
  /builds its image, local\/zip-hello:1\.0\.0/.test(await zipWarn.innerText()) && /2 GB of memory/.test(await zipWarn.innerText()));
await page.locator("#pl-install-password").fill(password);
await zipWarn.getByRole("button", { name: "Install Zip hello", exact: true }).click();
const zipRun = page.getByRole("dialog", { name: "Installing Zip hello 1.0.0" });
await zipRun.waitFor({ timeout: 8000 }).catch(() => {});
await zipRun.locator(".notice__title", { hasText: "Zip hello installed" }).waitFor({ timeout: 20000 }).catch(() => {});
check("ZIP-06", "the install runs as steps (check, build, install), each done",
  (await zipRun.locator(".task-list__item[data-state=done]").count()) === 3, (await zipRun.locator(".task-list").innerText().catch(() => "")));
await zipRun.getByRole("button", { name: "Done" }).click().catch(() => {});
await page.waitForURL(/settings-plugin\.html\?id=zip-hello/, { timeout: 8000 }).catch(() => {});
await page.waitForTimeout(800);
check("ZIP-07", "then its own page opens, offering Update from a zip file", /id=zip-hello/.test(page.url())
  && (await page.getByRole("heading", { name: "Update from a zip file" }).count()) === 1);
await page.getByLabel("The new version's zip file").setInputFiles(zipFile("1.0.1"));
await page.getByRole("button", { name: "Upload and check" }).click();
const zipUp = page.getByRole("dialog", { name: "Update Zip hello to 1.0.1?" });
await zipUp.waitFor({ timeout: 8000 }).catch(() => {});
check("ZIP-08", "a newer zip opens the update warning", (await zipUp.count()) === 1);
await page.locator("#pl-install-password").fill(password);
await zipUp.getByRole("button", { name: "Update Zip hello", exact: true }).click();
const zipUpRun = page.getByRole("dialog", { name: "Updating Zip hello to 1.0.1" });
await zipUpRun.locator(".notice__title", { hasText: "Zip hello is now 1.0.1" }).waitFor({ timeout: 20000 }).catch(() => {});
const zipUpSteps = await zipUpRun.locator(".task-list").innerText().catch(() => "");
check("ZIP-09", "the update builds first, then runs the usual update steps", /Building its container from the zip/.test(zipUpSteps)
  && (await api("/api/plugins")).plugins.find((p) => p.id === "zip-hello")?.version === "1.0.1", zipUpSteps);
await zipUpRun.getByRole("button", { name: "Done" }).click().catch(() => {});
await api("/api/plugins/zip-hello/remove", { method: "POST", body: { password } });
check("ZIP-10", "the example plug-in is removed again", !(await api("/api/plugins")).plugins.some((p) => p.id === "zip-hello"));
await open("settings-plugin.html?id=on-demand");
check("ZIP-11", "a plug-in added from a zip updates from a zip, not an address",
  (await page.getByRole("heading", { name: "Update from a zip file" }).count()) === 1 && (await page.getByRole("heading", { name: "Update from an address" }).count()) === 0);

console.log("\n== JFM Jellyfin's metadata");
await open("settings-jellyfin.html");
const jfm = page.locator('section[aria-labelledby="jf-metadata-h"]');
await jfm.getByRole("button", { name: /Move them out of the settings folder/ }).waitFor({ timeout: 8000 }).catch(() => {});
check("JFM-01", "Settings, Jellyfin says where its pictures and details are, and offers to move them", /In its settings folder/.test(await jfm.innerText()));
await jfm.getByRole("button", { name: /Move them out of the settings folder/ }).click();
const jfmAsk = page.getByRole("dialog", { name: "Move Jellyfin's pictures and details?" });
await jfmAsk.waitFor({ timeout: 5000 }).catch(() => {});
check("JFM-02", "the move asks for the password and says nothing is deleted", /Nothing is deleted/.test(await jfmAsk.innerText()));
await page.locator("#jf-metadata-pw").fill(password);
await jfmAsk.getByRole("button", { name: "Move them" }).click();
const jfmRun = page.getByRole("dialog", { name: "Moving Jellyfin's pictures and details" });
await jfmRun.locator(".notice__title", { hasText: "Jellyfin's metadata is moved" }).waitFor({ timeout: 20000 }).catch(() => {});
check("JFM-03", "each step is done and the result names the watch count",
  (await jfmRun.locator(".task-list__item[data-state=done]").count()) === 7 && /watches 2,074 folders/.test(await jfmRun.innerText()));
await jfmRun.getByRole("button", { name: "Done" }).click().catch(() => {});
await page.waitForTimeout(600);
check("JFM-04", "the section then says they are outside the settings folder", /Outside its settings folder/.test(await jfm.innerText()));

console.log("\n== Library clean-up: Put back (plug-in API 1.15, DASH-406)");
await open("settings-plugin.html?id=library-cleanup");
const heldTabJ = page.getByRole("tab", { name: "Holding folder" });
if (await heldTabJ.count()) { await heldTabJ.click(); await page.waitForTimeout(400); }
const putBack = page.getByRole("button", { name: "Put back A made-up film (2001)" });
check("HLD-01", "each row in the holding folder has Put back, named with its title", await putBack.count() === 1
  && await page.getByRole("button", { name: /^Put back / }).count() === 3);
await putBack.click();
await page.waitForTimeout(800);
check("HLD-02", "Put back says what it did and the row leaves the list",
  /Put back A made-up film/.test(await page.locator("[role=status]").allInnerTexts().then((t) => t.join(" ")))
  && await page.getByRole("button", { name: /^Put back / }).count() === 2);
check("HLD-02", "focus goes to the next row's Put back", await page.evaluate(() => /^Put back Harbour lights/.test(document.activeElement?.textContent || "")));
const mayText = await page.locator('section[aria-labelledby="pl-library-cleanup-may-h"]').innerText().catch(() => "");
check("HLD-03", "What it may do names the holding folder permission", /holding folder/i.test(mayText), mayText.slice(0, 200));

// VPN-01 to VPN-04 (DASH-440): Continue without a VPN in the browser set-up, with its warning as an alert dialog
// (focus on Cancel, Escape cancels); then Remove the VPN and Add a VPN in Settings, Downloads, VPN, the quiet
// reminder on Downloads (hidden for 90 days) and the dashboard's No VPN card. The VPN is added back at the end.
console.log("\n== VPN-01 Continue without a VPN in the set-up");
await open("install-apps.html?wizard=1");
const wiz = async (name) => { await page.locator(".wizard-frame, main").getByRole("button", { name, exact: true }).last().click(); await page.waitForTimeout(900); };
await wiz("Begin");
await page.getByRole("radio", { name: /Basics/ }).first().waitFor({ timeout: 15000 });
const without = page.getByRole("radio", { name: /Continue without a VPN/ });
for (let i = 0; i < 4 && !(await without.count()); i++) await wiz("Continue");  // What to set up (Basics), then Folders
await without.waitFor({ timeout: 15000 });
check("VPN-01", "the VPN step offers the VPN account first, as the suggested choice",
  await page.getByRole("radio", { name: /Use my VPN account \(recommended\)/ }).isChecked() && !(await without.isChecked()));
await without.check();
check("VPN-01", "choosing it hides the VPN account's fields", await page.getByText("VPN provider", { exact: true }).isHidden());
await wiz("Continue");
const warn = page.locator("dialog[open][role=alertdialog]");
await warn.waitFor({ timeout: 5000 });
check("VPN-01", "a warning opens as an alert dialog with its words", (await warn.textContent()).includes("can see your home internet address")
  && (await warn.getAttribute("aria-describedby")) !== null);
check("VPN-01", "focus starts on Cancel", await page.evaluate(() => document.activeElement?.closest("dialog[open]") && document.activeElement.textContent.trim() === "Cancel"));
await page.keyboard.press("Escape");
await page.waitForTimeout(400);
check("VPN-01", "Escape cancels: still on the VPN step, with focus on the choice", await without.isVisible()
  && await page.evaluate(() => document.activeElement?.type === "radio"));
await wiz("Continue");
await warn.waitFor({ timeout: 5000 });
await warn.getByRole("button", { name: "I understand, continue without a VPN" }).click();
await page.waitForTimeout(1200);
check("VPN-01", "confirming goes on to the next step", await without.count() === 0);
await page.getByRole("button", { name: "Back", exact: true }).first().click();
await page.waitForTimeout(1200);
check("VPN-01", "Back shows the VPN step with the choice kept", await page.getByRole("radio", { name: /Continue without a VPN/ }).isChecked());

console.log("\n== VPN-02 Remove the VPN in Settings");
if (!(await api("/api/downloads/vpn-state")).on) {
  await api("/api/downloads/vpn", { method: "POST", body: { password, vpn: { provider: "mullvad", type: "wireguard", wireguard_private_key: "made-up", wireguard_addresses: "192.168.1.20/32" } } });
}
await open("settings-downloads.html");
const rmPw = page.locator("#dl-vpn-remove-pw");
await rmPw.waitFor({ timeout: 10000 });
await rmPw.fill(password);
await page.getByRole("button", { name: "Remove the VPN" }).click();
await warn.waitFor({ timeout: 5000 });
check("VPN-02", "Remove the VPN shows the same warning, Cancel focused",
  (await warn.textContent()).includes("Remove the VPN?") && await page.evaluate(() => document.activeElement?.textContent.trim() === "Cancel"));
await warn.getByRole("button", { name: "Cancel" }).click();
check("VPN-02", "Cancel removes nothing", (await api("/api/downloads/vpn-state")).on === true);
await page.getByRole("button", { name: "Remove the VPN" }).click();
await warn.getByRole("button", { name: "I understand, remove the VPN" }).click();
await page.getByText("VPN removed").waitFor({ timeout: 10000 });
check("VPN-02", "confirmed, the VPN is removed", (await api("/api/downloads/vpn-state")).on === false);

console.log("\n== VPN-03 The quiet No VPN states");
await open("settings-downloads.html");
check("VPN-03", "Settings, Downloads, VPN says No VPN with Add a VPN, not an error",
  await page.locator("#dl-vpn-h").count() === 1 && await page.getByRole("button", { name: "Add a VPN" }).count() === 1
  && await page.locator(".notice[data-tone=danger]").count() === 0);
await open("downloads.html");
const reminder = page.locator("#vpn-reminder");
await reminder.waitFor({ timeout: 10000 });
check("VPN-03", "Downloads says Downloading without a VPN, with the link to add one",
  (await reminder.textContent()).includes("Downloading without a VPN") && (await reminder.getByRole("link", { name: "Add a VPN" }).getAttribute("href")) === "/settings-downloads.html");
await reminder.getByRole("button", { name: "Hide for 90 days" }).click();
await page.waitForTimeout(800);
check("VPN-03", "Hide for 90 days hides it, with focus on the page heading", await reminder.count() === 0
  && await page.evaluate(() => document.activeElement?.tagName === "H1"));
await open("downloads.html");
check("VPN-03", "and it stays hidden", await page.locator("#vpn-reminder").count() === 0);
// The default install's example has Gluetun on Apps, and the example server cannot start the apps again, so Gluetun
// would stay on Apps until ./install.sh --start-apps runs. The card is shown as it is once that has run: the transfer
// answer with no VPN app (the real one lists none once Gluetun is taken off Apps).
await page.route("**/api/transfer", (route) => route.fulfill({ contentType: "application/json", body: JSON.stringify({ clients: [], vpn: [], errors: [] }) }));
await open("dashboard.html");
await page.waitForTimeout(1500);
const vpnCard = page.locator("section, article, .card").filter({ has: page.getByRole("heading", { name: "VPN", exact: true }) }).last();
check("VPN-03", "the dashboard's VPN card says No VPN, with Add a VPN", (await vpnCard.textContent()).includes("No VPN")
  && await vpnCard.getByRole("link", { name: "Add a VPN" }).count() === 1);
await page.unroute("**/api/transfer");

console.log("\n== VPN-04 Add a VPN later");
await open("settings-downloads.html");
await page.getByRole("button", { name: "Add a VPN" }).click();
check("VPN-04", "Add a VPN opens the form with focus on the provider", await page.evaluate(() => document.activeElement?.id === "dl-vpn-add-provider"));
await page.getByRole("button", { name: "Add the VPN" }).click();
check("VPN-04", "a missing detail is said by its field", (await page.locator(".field-error:not([hidden])").first().textContent()).includes("Choose your VPN provider"));
await page.locator("#dl-vpn-add-provider").selectOption("other");  // a provider that is not listed, typed as Gluetun writes it
await page.locator("#dl-vpn-add-other").fill("mullvad");
await page.locator("#dl-vpn-add-key").fill("made-up");
await page.locator("#dl-vpn-add-address").fill("192.168.1.20/32");
await page.locator("#dl-vpn-add-pw").fill(password);
await page.getByRole("button", { name: "Add the VPN" }).click();
await page.getByText("VPN added").waitFor({ timeout: 10000 });
check("VPN-04", "the VPN is added back, with Gluetun", (await api("/api/downloads/vpn-state")).on === true);

console.log("\n== LOG-01 Log limits and Delete all logs, by keyboard (DASH-451)");
await open("settings-general-logs.html");
await page.locator("#logs-now").filter({ hasText: /^Now: |no logs/ }).waitFor({ timeout: 10000 });
const sizeSelect = page.locator('select[aria-labelledby="lg-size-l"]');
check("LOG-01", "No more than shows 50 MB, the default", (await sizeSelect.inputValue()) === "50");
await sizeSelect.focus();
await page.keyboard.press("ArrowUp");  // 25 MB, chosen by keyboard
await page.waitForTimeout(800);
check("LOG-01", "the new limit is saved", (await api("/api/config")).logs.max_mb === 25
  && await page.locator(".saved-note:not([hidden])").count() > 0);
check("LOG-01", "the apps' own logs say what Docker keeps or that it cannot ask", /Docker/.test(await page.locator("#logs-apps").textContent()));
const delBtn = page.getByRole("button", { name: "Delete all logs" });
await delBtn.focus();
await page.keyboard.press("Enter");
const dialog = page.getByRole("dialog", { name: "Delete all logs?" });
await dialog.waitFor({ timeout: 5000 });
check("LOG-01", "the dialog says how much goes and what stays", /Every log Starboard keeps goes: .+ in \d+ files?/.test(await dialog.textContent())
  && (await dialog.textContent()).includes("Today's file and the API's audit log are emptied, not removed"));
check("LOG-01", "focus starts on the password", await page.evaluate(() => document.activeElement?.type === "password"));
await page.keyboard.press("Escape");
await page.waitForTimeout(300);
check("LOG-01", "Escape cancels, with focus back on Delete all logs", await page.evaluate(() => document.activeElement?.id === "logs-delete"));
await page.keyboard.press("Enter");
await dialog.waitFor({ timeout: 5000 });
await page.keyboard.type(password);
await page.keyboard.press("Tab");
check("LOG-01", "Tab goes from the password to Delete all logs", await page.evaluate(() => document.activeElement?.textContent === "Delete all logs" && !!document.activeElement.closest("dialog")));
await page.keyboard.press("Enter");
await page.locator("#logs-delete-status").filter({ hasText: "All logs deleted" }).waitFor({ timeout: 10000 });
check("LOG-01", "said in the live region, with focus on Delete all logs",
  (await page.locator("#logs-delete-status").getAttribute("role")) === "status" && await page.evaluate(() => document.activeElement?.id === "logs-delete"));
check("LOG-01", "the size is shown as next to nothing", (await page.locator("#logs-delete-size").textContent()).includes("less than 1 KB"));
const logsAfter = (await api("/api/logs")).entries;
check("LOG-01", "the log says who deleted them", logsAfter.length < 5 && logsAfter.some((e) => /^All logs deleted by a signed-in browser \(session [0-9a-f]{8}\)/.test(e.message)));
await api("/api/config/general", { method: "PUT", body: { logs: { max_mb: 50 } } });
// CLD: Connect a cloud service (DASH-452), Test connection and Monthly backups. Stand-ins only (tools/screenshots/
// example_server.py): the phone's sign-in is approved at the stand-in on the example server's port + 2, as a phone would.
console.log("\n== CLD Connect a cloud service, Test connection, Monthly");
const standin = base.replace(/:(\d+)$/, (_, p) => `:${Number(p) + 2}`);
const placesBefore = (await api("/api/backup/copies")).destinations.map((d) => d.id);
const announced = () => page.evaluate(() => document.querySelector("#announcer")?.textContent || "");
const activeId = () => page.evaluate(() => document.activeElement?.id || document.activeElement?.className || "");
await open("system-backup.html");
const addDrive = page.locator("#place-add-drive");
check("CLD-01", "Add a place offers each service with its logo, name and how many are connected, the services in the agreed order",
  (await page.locator(".place-adds button strong").allTextContents()).slice(3).join() === "Google Drive,OneDrive,Dropbox,Backblaze B2,An S3-compatible service,Nextcloud or another WebDAV server,An SFTP server,Your own rclone remote"
  && /1 connected/.test(await addDrive.innerText()));
await addDrive.focus();
await page.keyboard.press("Enter");
await page.locator("#cloud-step-heading").waitFor();
check("CLD-02", "the slide-out opens at the sign-in with focus on its heading, as step 2 of 5", await activeId() === "cloud-step-heading"
  && /step 2 of 5/.test(await page.locator(".wizard-progress").innerText()));
await page.locator("#cloud-way").waitFor();
check("CLD-03", "Google Drive offers both ways to sign in, the same weight", await page.locator("#cloud-way .option-card").count() === 2
  && /Complete on the phone/.test(await page.locator("#cloud-way").innerText()) && /Complete in this browser/.test(await page.locator("#cloud-way").innerText()));
await page.locator("#cloud-open-signin").waitFor();
check("CLD-04", "in this browser: the sign-in link opens in a new tab and says so", (await page.locator("#cloud-open-signin").getAttribute("target")) === "_blank"
  && /opens in a new tab/.test(await page.locator("#cloud-open-signin").innerText()) && /^https:\/\/accounts\.google\.com\//.test(await page.locator("#cloud-open-signin").getAttribute("href")));
await page.locator("input[name=cloud-way][value=browser]").focus();
await page.keyboard.press("ArrowLeft");
await page.locator(".qr-card").waitFor();
const code = (await page.locator(".device-code__value").innerText()).trim();
check("CLD-05", "on the phone: a QR code with its text alternative, the page and the code written out, each with Copy",
  /^QR code for /.test(await page.locator(".qr-card__code svg").getAttribute("aria-label")) && await page.locator(".qr-card .address a").count() === 1
  && await page.locator(".qr-card .address .copy-btn").count() === 1 && /Copy/.test(await page.locator(".device-code .btn").innerText()) && /^\d{4}-\d{4}$/.test(code));
check("CLD-05", "the code is spelt out for screen readers", (await page.locator(".device-code__value").getAttribute("aria-label")).startsWith("Code: "));
check("CLD-05", "focus stays on the choice just made", await page.evaluate(() => document.activeElement?.value === "phone"));
check("CLD-06", "the wait is said in a polite live region, with the time left", (await page.locator("#cloud-wait-words").getAttribute("role")) === "status"
  && /Waiting for you to sign in on your phone/.test(await page.locator("#cloud-wait-words").innerText()) && /minutes? left/.test(await page.locator("#cloud-time-left").innerText()));
await page.request.get(`${standin}/device/approve?user_code=${encodeURIComponent(code)}`);  // as the phone would
await page.locator("[data-step=folder]").waitFor({ timeout: 20000 });
check("CLD-06", "approved on the phone: the wizard moves on by itself and says so", /Approved on your phone/.test(await announced())
  && await activeId() === "cloud-step-heading", await announced());
await page.locator("#cloud-folder-list .check").first().waitFor();
check("CLD-07", "the folder step: a new folder (recommended) and the folders there already", (await page.locator("#cloud-new-folder").inputValue()) === "starboard-backups"
  && await page.locator("#cloud-folder-list input[name=cloud-folder]").count() === 3);
await page.locator(".side-panel__foot .btn--primary").click();
await page.locator("#cloud-test-box .notice").waitFor();
check("CLD-08", "the test: each check done, said in words and in the live region", await page.locator(".test-checks li[data-state=done]").count() === 4
  && /^Connected: Starboard can write to Google Drive, starboard-backups/.test(await page.locator("#cloud-test-status").innerText()) && await activeId() === "cloud-test-go");
await page.keyboard.press("Enter");
await page.locator("#cloud-save").waitFor();
check("CLD-09", "check and save: a table of the answers, each with Change", await page.locator(".side-panel .table tbody tr").count() === 3
  && await page.locator(".side-panel .table tbody button", { hasText: "Change" }).count() === 3);
await page.locator(".side-panel__foot .btn--primary").click();
check("CLD-09", "a missing password is said beside its field", (await page.locator("#cloud-password").getAttribute("aria-invalid")) === "true" && await activeId() === "cloud-password");
await page.locator("#cloud-password").fill(password);
await page.keyboard.press("Enter");
await page.locator(".side-panel").waitFor({ state: "detached" });
await page.waitForTimeout(600);
check("CLD-10", "saved: the slide-out closes and focus is on Add a place", ["places-add", "place-add-drive"].includes(await activeId()), await activeId());
const savedCopies = await api("/api/backup/copies");
const addedPlaces = savedCopies.destinations.filter((d) => !placesBefore.includes(d.id));
check("CLD-10", "the second Google Drive is a new place with its own rclone remote, and the first keeps its own",
  addedPlaces.length === 1 && addedPlaces[0].service === "drive" && addedPlaces[0].remote.startsWith("starboard-drive:")
  && savedCopies.destinations.find((d) => d.id === "d1a2b3").remote.startsWith("starboard-cloud:"), JSON.stringify(addedPlaces.map((d) => d.remote)));
check("CLD-10", "the page is never sent the sign-in", !JSON.stringify(savedCopies).includes("standin-") && !JSON.stringify(savedCopies).includes("token"));
// Test connection: busy while it runs, then the result beside the place, kept for next time.
const newId = addedPlaces[0]?.id;
const testBtn = page.locator(`#place-test-${newId}`);
await testBtn.click();
await page.waitForFunction((i) => !document.querySelector(`#place-test-${i}`)?.disabled, newId);
check("CLD-11", "Test shows Connected with when, and focus stays on the button", /Connected/.test(await page.locator(`#place-tested-${newId}`).innerText())
  && /Tested/.test(await page.locator(`#place-tested-${newId}`).innerText()) && await activeId() === `place-test-${newId}`);
await page.waitForFunction(() => /^Connected: /.test(document.querySelector("#announcer")?.textContent || ""), null, { timeout: 3000 }).catch(() => {});
check("CLD-11", "and says it in the live region", /^Connected: Google Drive/.test(await announced()), await announced());
await open("system-backup.html");
check("CLD-11", "the result is still there when the page is opened again", /Connected/.test(await page.locator(`#place-tested-${newId}`).innerText()));
// Closing part way: Dropbox, the link only, then Escape.
await page.locator("#place-add-dropbox").click();
await page.locator("#cloud-open-signin").waitFor();
check("CLD-12", "Dropbox signs in with the link in this browser only, no QR code", await page.locator("#cloud-way").count() === 0 && await page.locator(".qr-card").count() === 0);
await page.locator("#cloud-answer").fill("http://127.0.0.1:53682/?state=SomeoneElse123&code=abc");
await page.locator("#cloud-answer-go").click();
await page.waitForTimeout(400);
check("CLD-12", "an address from another sign-in is refused beside the field", (await page.locator("#cloud-answer").getAttribute("aria-invalid")) === "true"
  && /different sign-in/.test(await page.locator("#cloud-answer-error").innerText()));
await page.keyboard.press("Escape");
await page.waitForTimeout(500);
check("CLD-12", "closing part way: focus back on the service, nothing saved, the sign-in ended", await activeId() === "place-add-dropbox"
  && /nothing was saved/.test(await announced()) && (await api("/api/backup/cloud/session")).state === "none"
  && (await api("/api/backup/copies")).destinations.length === placesBefore.length + 1);
// Pasting back in this browser, by keyboard: OneDrive, again: it has its own remote, starboard-onedrive-2 or the first free.
await page.locator("#place-add-onedrive").click();
await page.locator("#cloud-way").waitFor();
if (await page.locator("input[name=cloud-way][value=browser]").isChecked() === false) await page.locator("input[name=cloud-way][value=browser]").check();
await page.locator("#cloud-open-signin").waitFor();
const odState = new URL(await page.locator("#cloud-open-signin").getAttribute("href")).searchParams.get("state");
await page.locator("#cloud-answer").fill(`localhost:53682/?code=M.made-up&state=${odState}`);
await page.locator("#cloud-answer").press("Enter");
await page.locator("[data-step=folder]").waitFor({ timeout: 15000 });
check("CLD-13", "the address pasted back (without http://, as a phone shows it) signs in", /Signed in to OneDrive/.test(await announced()), await announced());
await page.keyboard.press("Escape");
await page.waitForTimeout(400);
// Phone width: the QR step does not scroll sideways.
await page.setViewportSize({ width: 375, height: 812 });
await page.locator("#place-add-drive").click();
await page.locator("input[name=cloud-way][value=phone]").check();
await page.locator(".qr-card").waitFor();
const qrWide = await page.evaluate(() => Math.max(document.documentElement.scrollWidth - innerWidth, document.querySelector(".side-panel__body").scrollWidth - document.querySelector(".side-panel__body").clientWidth));
check("CLD-14", "the QR step fits a phone without scrolling sideways", qrWide <= 0, `${qrWide}px`);
await page.keyboard.press("Escape");
await page.setViewportSize({ width: 1280, height: 860 });
// Monthly backups: least to most often, saves at once, keeps 6.
await open("system-backup.html");
const schedValues = await page.locator("input[name=backup-schedule]").evaluateAll((l) => l.map((i) => i.value));
check("MON-01", "When backups are made lists Off, Manual, Monthly, Weekly, Nightly", schedValues.join() === "off,manual,monthly,weekly,nightly", schedValues.join());
const schedWas = (await api("/api/backup/schedule")).mode;
await page.locator("input[name=backup-schedule][value=monthly]").check();
await page.waitForTimeout(700);
const monthly = await api("/api/backup/schedule");
check("MON-01", "Monthly saves at once: the 1st at 03:00, keeping 6, said in its hint", monthly.mode === "monthly" && monthly.keep === 6
  && new Date(monthly.next * 1000).getDate() === 1 && new Date(monthly.next * 1000).getHours() === 3
  && /1st of each month at 03:00\. The newest 6 are kept/.test(await page.locator("label.option-card", { hasText: "Monthly" }).innerText()));
check("MON-01", "focus stays on Monthly and the save is said", await page.evaluate(() => document.activeElement?.value === "monthly") && /Saved: Monthly/.test(await announced()));
await api("/api/config/general", { method: "PUT", body: { backup_schedule: schedWas } });
// Put the example's places back as they were: remove the one the journey added.
for (const d of (await api("/api/backup/copies")).destinations.filter((x) => !placesBefore.includes(x.id))) await api("/api/backup/copies/forget", { method: "POST", body: { password, id: d.id } });

console.log("\n== Bring in media (DASH-455)");
await open("bring-in.html?part=bring-sources");
await page.waitForSelector(".bring-sources li", { timeout: 10000 }).catch(() => {});
const rows455 = await page.locator(".bring-sources .sortable__row").count();
check("BRING-1", "the sources show in order, each said to be read only", rows455 === 3 &&
  (await page.locator(".bring-sources .bring-source__meta").allTextContents()).every((x) => /read only/.test(x)));
const pub455 = await page.evaluate(async () => {
  const now = await (await fetch("/api/bring-in")).json();
  const put = (sources) => fetch("/api/bring-in/sources", { method: "PUT", headers: { "Content-Type": "application/json", "X-Starboard": "1" }, body: JSON.stringify({ sources }) });
  await put(now.sources.map((s) => s.kind === "smb" ? { ...s, password: "made-up-share-secret" } : s));
  const text = await (await fetch("/api/bring-in")).text();
  return { text, set: JSON.parse(text).sources.find((s) => s.kind === "smb")?.password_set };
});
check("BRING-2", "a share's password is kept, and never sent back", pub455.set === true && !pub455.text.includes("made-up-share-secret"));
await open("bring-in.html?part=bring-names");
await page.waitForSelector(".bring-name", { timeout: 15000 }).catch(() => {});
const counts455 = await page.locator("[data-filter=bring-state] label").allTextContents();
check("BRING-3", "Check names has Matched, Needs attention and Left where it is, with counts", counts455.length === 3 && counts455.every((x) => /\d/.test(x)), counts455.join(" | "));
await open("bring-in.html?part=bring-copy");
await page.waitForSelector("main table", { timeout: 10000 }).catch(() => {});
check("BRING-4", "the copy part shows what will happen before anything is copied", /Sources, in order/.test(await page.locator("main table").first().textContent().catch(() => "")));
// RESTART-01 (DASH-470): Restart where it is needed. Jellyfin says Restart needed on System, Overview: Restart Jellyfin
// is beside it, says what it does, asks first, follows Jellyfin until it answers (in words, in a polite status) and
// moves focus to the result; a failure is said beside the button, which works again. The same button is on Settings,
// Updates and Settings, Apps, Jellyfin, and Restart Reelix is beside a Reelix restore that waits. The made-up
// restart needs are page routes; the restart itself reaches only the example server's stand-in Jellyfin.
console.log("\n== RESTART-01 Restart where it is needed");
let jfPending = true;
const jfInfo = async (route) => {
  const b = await (await route.fetch()).json().catch(() => ({}));
  await route.fulfill({ contentType: "application/json", body: JSON.stringify({ ...b, configured: true, name: "Jellyfin", version: b.version || "10.11.2",
    restart: jfPending, can_restart: true, playing: b.playing || [], added: b.added || [] }) });
};
await page.route(/\/api\/jellyfin(\?fresh=1)?$/, jfInfo);
const jfRestartFails = (route) => route.request().method() === "POST"
  ? route.fulfill({ status: 400, contentType: "application/json", body: JSON.stringify({ error: "Jellyfin did not restart: connection refused" }) }) : route.continue();
const jfRestartWorks = (route) => { if (route.request().method() === "POST") jfPending = false; return route.continue(); };
await open("system.html");
const jfPanel = page.locator("#jellyfin-panel");
const restartJf = jfPanel.getByRole("button", { name: "Restart Jellyfin" });
check("RESTART-01", "Overview: Restart Jellyfin shows beside Restart needed", await jfPanel.locator(".chip").filter({ hasText: "Restart needed" }).count() === 1
  && await restartJf.count() === 1);
const what01 = await restartJf.evaluate((b) => document.getElementById(b.getAttribute("aria-describedby").split(" ")[0])?.textContent || "").catch(() => "");
check("RESTART-01", "the button says what it does", /stopped/.test(what01) && /under a minute/.test(what01), what01);
check("RESTART-01", "the button is at least 44 by 44", await restartJf.evaluate((b) => { const r = b.getBoundingClientRect(); return r.width >= 44 && r.height >= 44; }).catch(() => false));
await restartJf.focus();
await page.keyboard.press("Enter");
const dialog01 = page.getByRole("dialog", { name: "Restart Jellyfin?" });
check("RESTART-01", "it asks first, starting on Cancel", await dialog01.count() === 1 && await page.evaluate(() => document.activeElement?.textContent === "Cancel"));
await page.keyboard.press("Escape");
await page.waitForTimeout(200);
check("RESTART-01", "Cancel changes nothing and focus returns to the button", jfPending && await restartJf.evaluate((b) => document.activeElement === b));
// A failure first: said beside the button, and the button can be pressed again.
await page.route(/\/api\/jellyfin\/restart$/, jfRestartFails);
await page.keyboard.press("Enter");
await dialog01.getByRole("button", { name: "Restart Jellyfin", exact: true }).click();
await page.waitForSelector("#jellyfin-panel .field-error[role=alert]", { timeout: 5000 }).catch(() => {});
const fail01 = await jfPanel.locator(".field-error[role=alert]").textContent().catch(() => "");
check("RESTART-01", "a failure is said beside the button", /did not restart/.test(fail01), fail01);
check("RESTART-01", "after a failure the button can be pressed again", await restartJf.getAttribute("aria-disabled") === null && jfPending);
await page.unroute(/\/api\/jellyfin\/restart$/, jfRestartFails);
await page.route(/\/api\/jellyfin\/restart$/, jfRestartWorks);
await restartJf.focus();
await page.keyboard.press("Enter");
await dialog01.getByRole("button", { name: "Restart Jellyfin", exact: true }).click();
const status01 = jfPanel.locator("[data-restart] [role=status]");
await page.locator("#jellyfin-panel [data-restart] [role=status]", { hasText: /\w/ }).waitFor({ timeout: 5000 }).catch(() => {});
const working01 = await status01.textContent();
check("RESTART-01", "while it works, progress is said in words and focus stays on the button",
  /Asking Jellyfin to restart|Jellyfin is restarting/.test(working01) && await restartJf.evaluate((b) => document.activeElement === b && b.getAttribute("aria-disabled") === "true"), working01);
// "restarted and answers again": the words while it works also end in "answers again".
await page.locator("#jellyfin-panel [data-restart] [role=status]", { hasText: "restarted and answers again" }).waitFor({ timeout: 30000 }).catch(() => {});
await page.waitForTimeout(500);
const done01 = await status01.textContent();
check("RESTART-01", "when Jellyfin answers, the status says so and takes focus", /Jellyfin restarted and answers again/.test(done01)
  && await status01.evaluate((s) => document.activeElement === s), `${done01} / ${await api("/api/jellyfin/restart").then(JSON.stringify).catch((e) => e.message)}`);
const state01 = await jfPanel.locator("#jellyfin-state").textContent();
check("RESTART-01", "the button goes and the state updates by itself", await restartJf.count() === 0 && !/Restart needed/.test(state01), state01);
check("RESTART-01", "the notice says Jellyfin restarted, in words and not colour alone", await jfPanel.locator("[data-restart-notice] .notice__title").textContent() === "Jellyfin restarted");
await page.unroute(/\/api\/jellyfin\/restart$/, jfRestartWorks);
await open("system.html");
check("RESTART-01", "with no restart needed, there is no Restart button", await page.locator("#jellyfin-panel").getByRole("button", { name: /^Restart/ }).count() === 0);
await page.unroute(/\/api\/jellyfin(\?fresh=1)?$/, jfInfo);
// Settings, Updates: Jellyfin's plug-ins row.
const jfUpdates = async (route) => {
  const b = await (await route.fetch()).json().catch(() => ({}));
  await route.fulfill({ contentType: "application/json", body: JSON.stringify({ ...b, connected: true, count: b.count || 1, restart: true, can_restart: true }) });
};
await page.route(/\/api\/updates\/jellyfin$/, jfUpdates);
await open("settings-updates.html");
await page.waitForSelector("[data-key=jellyfin-plugins] [data-restart]", { timeout: 10000 }).catch(() => {});
const jfRow = page.locator("[data-key=jellyfin-plugins]");
check("RESTART-01", "Updates: Jellyfin's plug-ins say Restart needed, with Restart Jellyfin", /Restart needed/.test(await jfRow.textContent().catch(() => ""))
  && await jfRow.getByRole("button", { name: "Restart Jellyfin" }).count() === 1);
await page.unroute(/\/api\/updates\/jellyfin$/, jfUpdates);
// Settings, Apps, Jellyfin: Recommended plug-ins, with the stand-in Jellyfin said to wait for a restart.
const jfPlugins = async (route) => {
  if (route.request().method() !== "GET") return route.continue();
  const b = await (await route.fetch()).json().catch(() => ({}));
  await route.fulfill({ contentType: "application/json", body: JSON.stringify({ ...b, restart: true, can_restart: true }) });
};
await page.route(/\/api\/jellyfin\/plugins$/, jfPlugins);
await open("settings-jellyfin.html");
await page.waitForSelector("#jf-plugins-list [data-restart] button", { timeout: 10000 }).catch(() => {});
check("RESTART-01", "Settings, Jellyfin: Restart Jellyfin beside Jellyfin needs a restart", await page.locator("#jf-plugins-list").getByRole("button", { name: "Restart Jellyfin" }).count() === 1);
await page.unroute(/\/api\/jellyfin\/plugins$/, jfPlugins);
// Backup: Restart Reelix beside a restore that waits, restarted and followed through Starboard's own routes.
let rxWaiting = true;
const rxBackups = async (route) => {
  const b = await (await route.fetch()).json().catch(() => ({}));
  await route.fulfill({ contentType: "application/json", body: JSON.stringify({ backups: [], every: 7, keep: 5, ...b, service: b.service || "reelix", restore_waiting: rxWaiting }) });
};
const rxRestart = (route) => { rxWaiting = false; return route.fulfill({ contentType: "application/json", body: JSON.stringify({ said: "Reelix restarted" }) }); };
const rxStatus = (route) => route.fulfill({ contentType: "application/json", body: JSON.stringify({ items: [{ id: "reelix", state: "up" }], recent: [] }) });
await page.route(/\/api\/reelix\/admin\/system\/backups$/, rxBackups);
await page.route(/\/api\/services\/[a-z0-9-]+\/restart$/, rxRestart);
await page.route(/\/api\/status\?id=/, rxStatus);
await open("system-backup.html");
await page.getByRole("button", { name: "Show Reelix's backups" }).click();
await page.waitForTimeout(300);
if (await page.locator("#rs-password").count()) { await page.fill("#rs-password", "made-up"); await page.keyboard.press("Enter"); }
await page.waitForSelector("section[aria-labelledby=rs-backups-h] [data-restart] button", { timeout: 10000 }).catch(() => {});
const restartRx = page.locator("section[aria-labelledby=rs-backups-h]").getByRole("button", { name: "Restart Reelix" });
check("RESTART-01", "Backup: Restart Reelix beside a restore that waits", await restartRx.count() === 1);
if (await restartRx.count()) {
  await restartRx.focus();
  await page.keyboard.press("Enter");
  await page.getByRole("dialog", { name: "Restart Reelix?" }).getByRole("button", { name: "Restart Reelix", exact: true }).click();
  await page.waitForSelector("#rs-restored", { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(300);
  check("RESTART-01", "the backups show no stray word null", !/\bnull\b/.test(await page.locator("section[aria-labelledby=rs-backups-h]").innerText()));
  check("RESTART-01", "after Reelix answers, the backups are drawn again and focus is on the result",
    await page.evaluate(() => document.activeElement?.id === "rs-restored") && await restartRx.count() === 0);
}
await page.unroute(/\/api\/reelix\/admin\/system\/backups$/, rxBackups);
await page.unroute(/\/api\/services\/[a-z0-9-]+\/restart$/, rxRestart);
await page.unroute(/\/api\/status\?id=/, rxStatus);

// Full backups: Checked in the list (DASH-381) and Restore on this server (DASH-387). The example server restores
// nothing: its made-up backup password is "made-up backup", and the steps pass in a few seconds.
console.log("\n== Full backups: Checked, and Restore on this server (DASH-381, DASH-387)");
await open("system-backup.html");
await page.locator("#full-list li[data-key]").first().waitFor({ timeout: 10000 }).catch(() => {});
const fullRows = page.locator("#full-list li[data-key]");
check("BKC-01", "the newest full backup says Checked, the one made before the check does not",
  /Checked/.test(await fullRows.nth(0).innerText()) && !/Checked/.test(await fullRows.nth(1).innerText()), await fullRows.nth(0).innerText());
check("BKC-01", "the page says what Checked means", /Checked means Starboard read the copy back/.test(await page.locator("#full-body").innerText()));
const restoreBtn = fullRows.nth(1).getByRole("button", { name: /^Restore the full backup from / });
check("RST-01", "each full backup has a danger Restore button that names its date", await restoreBtn.count() === 1
  && await restoreBtn.evaluate((b) => b.classList.contains("btn--danger")));
await restoreBtn.focus();
await page.keyboard.press("Enter");
const rstDialog = page.getByRole("dialog", { name: /^Restore the full backup from / });
await rstDialog.waitFor({ timeout: 5000 }).catch(() => {});
const rstText = await rstDialog.innerText().catch(() => "");
check("RST-02", "the dialog says what is replaced, that a full backup is made first and that the apps stop",
  /go back to how they were then/.test(rstText) && /first makes a full backup of how things are now/.test(rstText) && /Your apps stop/.test(rstText) && /media is not touched/.test(rstText), rstText);
check("RST-02", "it is a danger dialog with Cancel, and focus starts on the backup's password",
  await rstDialog.getByRole("button", { name: "Restore this backup" }).evaluate((b) => b.classList.contains("btn--danger"))
  && await rstDialog.getByRole("button", { name: "Cancel" }).count() === 1 && await activeId() === "restore-full-pw", await activeId());
await page.keyboard.press("Escape");
await page.waitForTimeout(300);
check("RST-02", "Escape closes it, changes nothing and focus is back on Restore",
  await rstDialog.count() === 0 && (await api("/api/backup/full/restore-here")).status.state === "none"
  && await page.evaluate(() => document.activeElement?.closest("li")?.dataset.key === document.querySelectorAll("#full-list li[data-key]")[1].dataset.key));
await page.keyboard.press("Enter");
await rstDialog.waitFor({ timeout: 5000 }).catch(() => {});
await page.fill("#restore-full-pw", "not the backup password");
await page.fill("#restore-full-mine", password);
await rstDialog.getByRole("button", { name: "Restore this backup" }).click();
await page.waitForSelector("#restore-full-pw[aria-invalid=true]", { timeout: 5000 }).catch(() => {});
check("RST-03", "a wrong backup password opens the dialog again with the error under that field, focus in it, and nothing started",
  /does not open this backup/.test(await page.locator("#restore-full-pw-error").innerText().catch(() => "")) && await activeId() === "restore-full-pw"
  && (await page.locator("#restore-full-pw").getAttribute("aria-describedby") || "").includes("restore-full-pw-error")
  && (await api("/api/backup/full/restore-here")).status.state === "none");
await page.fill("#restore-full-pw", "made-up backup");
await page.fill("#restore-full-mine", password);
await rstDialog.getByRole("button", { name: "Restore this backup" }).click();
await page.waitForFunction(() => /Restoring the full backup/.test(document.querySelector("#full-restore-state")?.textContent || ""), null, { timeout: 5000 }).catch(() => {});
await page.waitForTimeout(300);
check("RST-04", "both passwords right: the page says it is restoring, in a live region, and says so to screen readers",
  /Restoring the full backup from/.test(await page.locator("#full-restore-state").innerText()) && await page.locator("#full-restore-state").getAttribute("aria-live") === "polite"
  && /^Restoring the full backup from/.test(await announced()), await page.locator("#full-restore-state").innerText());
check("RST-04", "no backup can be made meanwhile, and focus is back on the Restore button",
  await page.getByRole("button", { name: "Make a full backup" }).isDisabled()
  && await page.evaluate(() => document.activeElement?.closest("li")?.dataset.key === document.querySelectorAll("#full-list li[data-key]")[1].dataset.key));
await page.waitForFunction(() => /Restored the full backup/.test(document.querySelector("#full-restore-state")?.textContent || ""), null, { timeout: 20000 }).catch(() => {});
await page.waitForTimeout(500);
const rstDone = await page.locator("#full-restore-state").innerText();
check("RST-05", "when it ends the page says so, with the apps and where the backup of before is",
  /Restored the full backup from/.test(rstDone) && /settings of 7 apps are back/.test(rstDone) && /starboard-full-[0-9-]+\.starboard/.test(rstDone), rstDone);
check("RST-05", "the list is drawn again with focus still on the same row, and a backup can be made again",
  await page.evaluate(() => document.activeElement?.closest("li")?.dataset.key === document.querySelectorAll("#full-list li[data-key]")[1].dataset.key)
  && !(await page.getByRole("button", { name: "Make a full backup" }).isDisabled()));

// Reelix's backup settings (DASH-385) and its backups on another disk (DASH-386).
console.log("\n== Reelix's backups: selects that apply at once, and the folder on another disk (DASH-385, DASH-386)");
let rxMoved = false;
const rxPlace = async (route) => {
  const b = await (await route.fetch()).json().catch(() => ({}));
  if (rxMoved && b.place) b.place = { ...b.place, now: b.place.chosen, restart: false };
  await route.fulfill({ contentType: "application/json", body: JSON.stringify({ ...b, service: b.service || "reelix" }) });
};
await page.route(/\/api\/reelix\/admin\/system\/(backups|backup-place|backup-settings)$/, rxPlace);
await page.route(/\/api\/services\/[a-z0-9-]+\/restart$/, (route) => { rxMoved = true; return route.fulfill({ contentType: "application/json", body: JSON.stringify({ said: "Reelix restarted" }) }); });
await page.route(/\/api\/status\?id=/, rxStatus);
await open("system-backup.html");
await page.getByRole("button", { name: "Show Reelix's backups" }).click();
await page.waitForTimeout(300);
if (await page.locator("#rs-password").count()) { await page.fill("#rs-password", "made-up"); await page.keyboard.press("Enter"); }
await page.waitForSelector("#rs-every", { timeout: 10000 }).catch(() => {});
const rxSection = page.locator("section[aria-labelledby=rs-backups-h]");
check("RXB-01", "how often and how many are selects with a label and a hint, and there is no Save button",
  await page.evaluate(() => ["rs-every", "rs-keep"].every((id) => { const s = document.getElementById(id); return s?.tagName === "SELECT" && document.getElementById(s.getAttribute("aria-labelledby"))?.textContent && document.getElementById(s.getAttribute("aria-describedby"))?.textContent; }))
  && await rxSection.getByRole("button", { name: /Save/ }).count() === 0);
await page.locator("#rs-every").focus();
await page.locator("#rs-every").selectOption("14");
await page.waitForFunction(() => { const n = document.querySelector("#rs-every")?.parentElement.querySelector(".saved-note"); return n && !n.hidden; }, null, { timeout: 5000 }).catch(() => {});
const rxSaved = await api("/api/reelix/admin/system/backups", { method: "POST", body: { password: "made-up" } });
check("RXB-02", "a choice applies at once: Reelix has it, the saved note shows beside the select as a status, and focus stays on it",
  rxSaved.every === 14 && /^Saved at \d\d:\d\d$/.test(await page.locator("#rs-every + .saved-note").innerText().catch(() => ""))
  && await page.locator("#rs-every + .saved-note").getAttribute("role") === "status" && await activeId() === "rs-every", `${rxSaved.every} ${await activeId()}`);
await page.locator("#rs-keep").selectOption("10");
await page.waitForFunction(() => { const n = document.querySelector("#rs-keep")?.parentElement.querySelector(".saved-note"); return n && !n.hidden; }, null, { timeout: 5000 }).catch(() => {});
const rxSaved2 = await api("/api/reelix/admin/system/backups", { method: "POST", body: { password: "made-up" } });
check("RXB-02", "the second select saves with the first one's newest value", rxSaved2.every === 14 && rxSaved2.keep === 10, `${rxSaved2.every} ${rxSaved2.keep}`);
const rxOptions = await page.locator("#rs-place option").allTextContents();
check("RXB-03", "where Reelix keeps them names both places and their disks",
  rxOptions.length === 2 && /Next to its settings, on the system disk/.test(rxOptions[0]) && /In the media folder, on WDC WD40EFRX/.test(rxOptions[1]), rxOptions.join(" | "));
await page.locator("#rs-place").focus();
await page.locator("#rs-place").selectOption("media");
await page.waitForSelector("section[aria-labelledby=rs-backups-h] [data-restart-notice]", { timeout: 10000 }).catch(() => {});
await page.waitForTimeout(300);
check("RXB-03", "choosing the media folder saves at once, keeps focus on the select and says Reelix must restart",
  await activeId() === "rs-place" && await page.locator("#rs-place").inputValue() === "media"
  && /The new backup folder waits for Reelix to restart/.test(await rxSection.innerText()) && /media folder from its next start/.test(await announced()), await announced());
const restartMoved = rxSection.getByRole("button", { name: "Restart Reelix" });
if (await restartMoved.count()) {
  await restartMoved.focus();
  await page.keyboard.press("Enter");
  await page.getByRole("dialog", { name: "Restart Reelix?" }).getByRole("button", { name: "Restart Reelix", exact: true }).click();
  await page.waitForSelector("#rs-restored", { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(300);
}
check("RXB-04", "after the restart the notice goes, the result has focus and no stray word null shows",
  await restartMoved.count() === 0 && await page.evaluate(() => document.activeElement?.id === "rs-restored") && !/\bnull\b/.test(await rxSection.innerText()));
const rxRestoreBtn = rxSection.getByRole("button", { name: /^Restore / }).first();
if (await rxRestoreBtn.count()) {
  await rxRestoreBtn.click();
  const rxDialog = page.getByRole("dialog", { name: "Restore this Reelix backup?" });
  check("RXB-05", "the restore dialog says Reelix must restart before anything changes", /happens when Reelix restarts/.test(await rxDialog.innerText().catch(() => "")));
  await rxDialog.getByRole("button", { name: "Cancel" }).click();
} else check("RXB-05", "the restore dialog says Reelix must restart before anything changes", false, "no Reelix backup in the list");
// Back to how it was.
rxMoved = false;
await api("/api/reelix/admin/system/backup-place", { method: "POST", body: { password: "made-up", place: "settings" } });
await api("/api/reelix/admin/system/backup-settings", { method: "POST", body: { password: "made-up", every: 7, keep: 5 } });
await page.unroute(/\/api\/reelix\/admin\/system\/(backups|backup-place|backup-settings)$/, rxPlace);
await page.unroute(/\/api\/services\/[a-z0-9-]+\/restart$/);
await page.unroute(/\/api\/status\?id=/, rxStatus);

// DASH-512: the two-step code and single sign-on for Starboard's own sign-in. Both are off until set up; set-up asks for
// the password, shows a QR code and the recovery codes once; signing in then asks for the code after the password;
// deactivating puts it back. The example server takes 123456 as the right code (tools/screenshots/example_server.py).
console.log("\n== SIGNIN-01 Two-step code and single sign-on");
const problemsBefore = problems.length;  // the refusals below are answered 401 and 409 on purpose; the browser logs each as an error
await page.setViewportSize({ width: 1280, height: 860 });
await open("settings-security-signin.html");
check("SIGNIN-01", "nothing is on at first: the two-step code says Off, with its set-up button", await page.getByRole("button", { name: "Set up a two-step code" }).count() === 1
  && /Off/.test(await page.locator("#sc-2fa-h").locator("xpath=ancestor::section").innerText()));
const signinState = await api("/api/security/signin");
check("SIGNIN-01", "the settings say so, and never hold a secret", !signinState.totp.enabled && !signinState.oidc.enabled && signinState.password_login && !JSON.stringify(signinState).includes("made-up-client-secret"));
await page.getByRole("button", { name: "Set up a two-step code" }).click();
check("SIGNIN-02", "the set-up asks for the password first, with focus in its field", await page.evaluate(() => document.activeElement?.id === "signin-password"));
await page.fill("#signin-password", "not the password at all");
await page.keyboard.press("Enter");
await page.waitForTimeout(800);
check("SIGNIN-02", "a wrong password is refused and no QR code is shown", await page.locator(".qr-card__code svg").count() === 0);
await page.getByRole("button", { name: "Set up a two-step code" }).click();
await page.fill("#signin-password", password);
await page.keyboard.press("Enter");
await page.locator("#totp-form").waitFor({ timeout: 8000 });
check("SIGNIN-02", "the QR code has a name for screen readers, and the key can be typed instead", await page.locator('.qr-card__code svg[role=img][aria-label]').count() === 1 && /^[A-Z2-7 ]{20,}$/.test(await page.locator("#totp-key").innerText()));
check("SIGNIN-02", "focus is in the code field", await page.evaluate(() => document.activeElement?.id === "totp-code"));
await page.fill("#totp-code", "000000");
await page.keyboard.press("Enter");
await page.waitForTimeout(800);
check("SIGNIN-02", "a wrong code is refused beside the field and nothing is turned on", /not right/.test(await page.locator("#totp-code-error").innerText().catch(() => "")) && !(await api("/api/security/signin")).totp.enabled);
await page.fill("#totp-code", "123456");
await page.keyboard.press("Enter");
await page.locator(".recovery-codes").waitFor({ timeout: 8000 });
const recovery = await page.locator(".recovery-codes code").allTextContents();
check("SIGNIN-02", "8 different recovery codes are shown, once", recovery.length === 8 && new Set(recovery).size === 8 && recovery.every((c) => /^[a-z2-9]{5}-[a-z2-9]{5}$/.test(c)), recovery.join(" "));
check("SIGNIN-02", "focus is on I have saved them", await page.evaluate(() => /I have saved them/.test(document.activeElement?.textContent || "")));
await page.keyboard.press("Enter");
await page.waitForTimeout(600);
check("SIGNIN-02", "it is on, and says how many recovery codes are left", /8 of 8 recovery codes left/.test(await page.locator("#recovery-left").innerText()));
check("SIGNIN-02", "focus is not lost to the top of the page", await page.evaluate(() => document.activeElement && document.activeElement !== document.body));
// Signing in as someone who has not: a second browser, with no session.
const other = await (await browser.newContext({ viewport: { width: 1280, height: 860 } })).newPage();
await other.goto(`${base}/login.html`);
await other.fill("#password", password);
await other.keyboard.press("Enter");
await other.locator("#code").waitFor({ state: "visible", timeout: 8000 });
check("SIGNIN-03", "the code is asked for after the password, and nothing is signed in yet", /login/.test(other.url()) && await other.evaluate(() => document.activeElement?.id === "code"));
check("SIGNIN-03", "the password form is gone and the step says what to enter", await other.locator("#login-form").isHidden() && /authenticator app/.test(await other.locator("label[for=code]").innerText()));
await other.fill("#code", "111111");
await other.keyboard.press("Enter");
await other.waitForTimeout(800);
check("SIGNIN-03", "a wrong code says so under the field, keeps focus there and signs nobody in", /not right/.test(await other.locator("#code-error").innerText()) && await other.evaluate(() => document.activeElement?.id === "code") && /login/.test(other.url()));
await other.fill("#code", recovery[0].toUpperCase());
await other.keyboard.press("Enter");
await other.waitForURL((u) => !u.pathname.endsWith("login.html"), { timeout: 8000 }).catch(() => {});
check("SIGNIN-03", "a recovery code signs in, once", !/login/.test(other.url()) && (await api("/api/security/signin")).totp.recovery_left === 7);
await other.context().close();
await open("settings-security-signin.html");
await page.getByRole("button", { name: "Deactivate the two-step code" }).click();
check("SIGNIN-04", "deactivating asks first, and the safe choice is not the default", await page.getByRole("dialog").count() === 1);
await page.fill("#signin-password", password);
await page.keyboard.press("Enter");
await page.getByRole("button", { name: "Set up a two-step code" }).waitFor({ timeout: 8000 }).catch(() => {});
check("SIGNIN-04", "after it, the two-step code is off again and the password alone signs in", !(await api("/api/security/signin")).totp.enabled && await page.getByRole("button", { name: "Set up a two-step code" }).count() === 1);
// Single sign-on, as far as a made-up provider allows: the form, the secret kept out of the page, the test before it can be used.
await page.getByRole("tab", { name: "Single sign-on" }).click().catch(() => {});
check("SIGNIN-05", "the secret is never in the page, only that it is kept", await page.locator("#sso-secret").getAttribute("placeholder") === "Kept. Leave blank to keep it" && !(await page.content()).includes("made-up-client-secret"));
check("SIGNIN-05", "Allow single sign-on is a switch with a name", await page.getByRole("switch", { name: /Allow single sign-on/ }).count() === 1);
const pwOff = await page.evaluate(async () => { try { await api("/api/security/password-login", { method: "POST", body: { password: "example-password", allowed: false } }); return "allowed"; } catch (e) { return e.message; } });
check("SIGNIN-05", "the password cannot be deactivated until single sign-on is on and has been tested", /Activate single sign-on and test it first/.test(pwOff), pwOff);
const asKey = await page.evaluate(async () => (await fetch("/api/security/signin", { credentials: "omit", headers: { Authorization: "Bearer sb_manage_000000_nope" } })).status);
check("SIGNIN-05", "an API key, or a made-up one, cannot read any of it", asKey === 401, String(asKey));
problems.splice(problemsBefore, problems.length, ...problems.slice(problemsBefore).filter((m) => !/status of (401|409)/.test(m)));

// DASH-515: the hardware video conversion check. Nothing at rest; the test runs only when Test now is pressed, through the
// made-up Jellyfin (the example server answers as a chip where VAAPI works and Quick Sync does not).
console.log("\n== TRANSCODE-01 Hardware video conversion check");
await open("system.html");
check("TRANSCODE-01", "the panel is there and offers Test now", await page.getByRole("button", { name: "Test now" }).count() === 1);
check("TRANSCODE-01", "nothing has been tested before the button is pressed", (await api("/api/system/transcode-check")).result === null);
await page.getByRole("button", { name: "Test now" }).click();
await page.locator("#transcode li").first().waitFor({ timeout: 30000 });
const tcRows = await page.locator("#transcode li").allInnerTexts();
check("TRANSCODE-01", "a row for VAAPI, Intel Quick Sync, NVIDIA NVENC and software", tcRows.length === 4 && /VAAPI/.test(tcRows[0]) && /Quick Sync/.test(tcRows[1]) && /NVENC/.test(tcRows[2]) && /Software/.test(tcRows[3]), tcRows.join(" | ").slice(0, 200));
check("TRANSCODE-01", "VAAPI works and names its device", /Works/.test(tcRows[0]) && /\/dev\/dri\/renderD128/.test(tcRows[0]));
check("TRANSCODE-01", "Quick Sync says why not, with the fix, in words", /Does not work/.test(tcRows[1]) && /How to fix it/.test(tcRows[1]));
check("TRANSCODE-01", "the result is a status the person is moved to", await page.evaluate(() => document.activeElement?.id === "transcode-status") && (await page.locator("#transcode-status").getAttribute("role")) === "status");
check("TRANSCODE-01", "it says nothing was opened or changed", /No media was opened and nothing was changed/.test(await page.locator("#transcode").innerText()));

// DASH-536: Remove drop shadows. Kept for everyone on the server, applied at once and before the page draws, with the
// borders staying; the note says what it costs, in the owner's words.
console.log("\n== SHADOWS-01 Remove drop shadows");
// The made-up install runs Reelix Lite, so an unanswered setting starts with the shadows removed; the person's own answer is used after that.
// The example server answers the setting when it sets the install up (so the pictures keep their shadows), so first clear the answer: null means follow the install again.
await api("/api/config/general", { method: "PUT", body: { shadows_off: null } });
await open("index.html");
check("SHADOWS-01", "an unanswered setting follows the Lite install: removed", (await api("/api/session")).shadows_off === true && (await api("/api/config")).shadows_answered === false);
await api("/api/config/general", { method: "PUT", body: { shadows_off: false } });
await page.evaluate(() => { try { localStorage.removeItem("starboard.display"); } catch { /* fine */ } });  // earlier journeys may have left High contrast on, which has no shadows
await open("library-films.html");
await page.locator("#lib-wall .media-card").first().waitFor({ timeout: 15000 });
const shdShadowof = () => page.evaluate(() => { const c = document.querySelector("#lib-wall .media-card .cover:not(.is-wanted)") || document.querySelector(".card"); const s = getComputedStyle(c); return { shadow: s.boxShadow, border: s.borderTopWidth }; });
const shdBefore = await shdShadowof();
check("SHADOWS-01", "shadows are kept by default here, and the page says so", shdBefore.shadow !== "none" && !(await page.evaluate(() => document.documentElement.dataset.shadows)) && (await api("/api/session")).shadows_off === false, JSON.stringify(shdBefore));
await page.locator("[data-display-toggle]").click();
const shdSw = page.getByRole("switch", { name: "Remove drop shadows" });
await shdSw.waitFor();
check("SHADOWS-01", "the switch has the note as its description", /^Drop shadows cost a little processor on every scroll; turning them off helps small and older computers/.test(await page.evaluate(() => document.getElementById(document.querySelector("#side-panel input[name=shadows]").getAttribute("aria-describedby")).textContent)));
await shdSw.check();
await page.waitForTimeout(600);
const shdAfter = await shdShadowof();
check("SHADOWS-01", "turning it on removes the shadow at once and keeps the border", shdAfter.shadow === "none" && shdAfter.border === shdBefore.border && await page.evaluate(() => document.documentElement.dataset.shadows) === "off", JSON.stringify(shdAfter));
const shdCfg = await api("/api/config");
check("SHADOWS-01", "it is kept on the server and in the browser for the first paint", shdCfg.shadows_off === true && shdCfg.shadows_answered === true && await page.evaluate(() => localStorage.getItem("starboard.shadows")) === "off", JSON.stringify([shdCfg.shadows_off, shdCfg.shadows_answered]));
check("SHADOWS-01", "the saved note says so beside the switch", /Saved/.test(await page.locator("#dp-shadows-saved").textContent()), await page.locator("#dp-shadows-saved").evaluate((n) => n.outerHTML.slice(0, 120)).catch((e) => String(e).slice(0, 80)));
await page.keyboard.press("Escape");
await page.goto(`${base}/library-films.html`, { waitUntil: "commit" });
await page.waitForFunction(() => document.documentElement.dataset.shadows === "off" || document.readyState === "complete", null, { timeout: 5000 });
check("SHADOWS-01", "shdAfter a reload the shadows are still gone, from the very first paint", await page.evaluate(() => document.documentElement.dataset.shadows) === "off");
await open("settings-general-appearance.html");
check("SHADOWS-01", "Settings, General, Appearance has the same switch, on", await page.getByRole("switch", { name: "Remove drop shadows" }).isChecked());
await open("index.html");
check("SHADOWS-01", "the plug-in and help pages are covered by the same attribute (every page loads common.js)", await page.evaluate(() => document.documentElement.dataset.shadows) === "off");
await api("/api/config/general", { method: "PUT", body: { shadows_off: false } });
await open("index.html");
check("SHADOWS-01", "putting the shadows back works for everyone too", (await api("/api/session")).shadows_off === false && !(await page.evaluate(() => document.documentElement.dataset.shadows)));

// LOG-02: System, Logs limits what it shows (DASH-534): Lines shown and Alerts only, kept for the account, applied at once
// with the saved note beside them, by keyboard, with how many are shown said in a live region.
console.log("\n== LOG-02 Logs shown");
await api("/api/config/general", { method: "PUT", body: { logs: { show_lines: 200, alerts_only: false } } });
await open("system-logs.html");
const logSelect = page.getByLabel("Lines shown");
check("LOG-02", "Lines shown offers 50, 100, 200, 500 and 1,000 and starts at 200",
  JSON.stringify(await logSelect.locator("option").allTextContents()) === JSON.stringify(["50 lines", "100 lines", "200 lines", "500 lines", "1,000 lines"]) && await logSelect.inputValue() === "200");
check("LOG-02", "the count is a polite live region and says how many there are", /^Showing (all|the newest) [\d,]+/.test(await page.locator("#entries-count").textContent()) && await page.locator("#entries-count").getAttribute("role") === "status");
await logSelect.focus();
await page.keyboard.press("ArrowUp");  // by keyboard: 100 lines
await page.getByText(/^Saved at \d\d:\d\d$/).waitFor({ timeout: 5000 }).catch(() => {});
const logCfg = await api("/api/config");
check("LOG-02", "choosing 100 lines is saved for the account at once, with the saved note, and keeps focus on the select",
  logCfg.logs.show_lines === 100 && await page.locator("#logs-limit-note").isVisible() && await page.evaluate(() => document.activeElement.id) === "logs-limit", JSON.stringify(logCfg.logs));
await page.reload({ waitUntil: "networkidle" });
check("LOG-02", "it is still 100 after a reload", await page.getByLabel("Lines shown").inputValue() === "100");
const alertsSwitch = page.getByRole("switch", { name: "Alerts only" });
check("LOG-02", "Alerts only is a switch, off to start with", await alertsSwitch.isVisible() && !(await alertsSwitch.isChecked()));
await alertsSwitch.focus();
await page.keyboard.press("Space");
await page.waitForFunction(() => document.querySelector("#logs-alerts-only")?.checked && /Saved at/.test(document.querySelector("#logs-limit-note")?.textContent || ""), null, { timeout: 5000 }).catch(() => {});
const onlyRows = await page.evaluate(() => [...document.querySelectorAll("#entries tbody tr td:nth-child(2)")].map((td) => td.textContent.trim()));
check("LOG-02", "Alerts only shows errors and warnings and nothing else, and is saved", onlyRows.every((l) => /Error|Warning/.test(l)) && (await api("/api/config")).logs.alerts_only === true && await page.evaluate(() => document.activeElement.id) === "logs-alerts-only", JSON.stringify(onlyRows));
const downloaded = await page.evaluate(async () => (await fetch("/api/logs/download")).text());
check("LOG-02", "Download gives the same: a line saying how many, then alerts only", /^# Starboard log: the newest \d+ of [\d,]+ entries, alerts only/.test(downloaded) && !/ INFO /.test(downloaded), downloaded.slice(0, 120));
await api("/api/config/general", { method: "PUT", body: { logs: { show_lines: 200, alerts_only: false } } });

// Settings, Plug-ins: each plug-in's tab has its own icon, and icons only still name the current and focused tab (owner, 26 November 2026).
console.log("\n== PTI Plug-in tab icons");
await page.setViewportSize({ width: 375, height: 812 });
await open("settings-plugin.html?id=notifications");
await page.waitForFunction(() => document.querySelectorAll('nav[aria-label="Plug-ins"] a').length > 4, null, { timeout: 5000 }).catch(() => {});
const ptiTabs = () => page.evaluate(() => [...document.querySelectorAll('nav[aria-label="Plug-ins"] a')].map((a) => {
  const r = a.getBoundingClientRect(), l = a.querySelector(".menu-tabs__label"), s = a.querySelector("svg");
  return { name: a.textContent.trim(), icon: s?.querySelector("use")?.getAttribute("href") || "", hidden: s?.getAttribute("aria-hidden"), w: Math.round(r.width), h: Math.round(r.height),
    shown: l.getBoundingClientRect().width > 8, current: a.getAttribute("aria-current") === "page", title: a.title };
}));
let pti = await ptiTabs();
const ptiPlugs = pti.slice(2);
check("PTI-01", "at 375 wide the tabs show icons only, and each is at least 44 by 44", pti.length > 4 && pti.filter((x) => !x.current).every((x) => !x.shown && x.w >= 44 && x.h >= 44), JSON.stringify(pti.map((x) => [x.name, x.w, x.h])));
const known = ptiPlugs.filter((x) => !/#i-puzzle$/.test(x.icon));
check("PTI-02", "every plug-in tab with an icon of its own has a different one",
  known.length > 8 && new Set(known.map((x) => x.icon)).size === known.length, JSON.stringify(known.map((x) => [x.name, x.icon])));
check("PTI-03", "a plug-in with no icon of its own gets the neutral puzzle piece", ptiPlugs.some((x) => /#i-puzzle$/.test(x.icon)) && ptiPlugs.find((x) => x.name === "Notifications")?.icon.endsWith("#i-bell"));
check("PTI-04", "every icon is hidden from a screen reader, and every tab keeps its name as text and as its tooltip", pti.every((x) => x.hidden === "true" && x.name && x.title === x.name));
check("PTI-05", "the tab you are on shows its name beside the icon, with the bar under it, and is in view",
  pti.filter((x) => x.current).length === 1 && pti.find((x) => x.current).name === "Notifications" && pti.find((x) => x.current).shown
  && await page.evaluate(() => { const a = document.querySelector('nav[aria-label="Plug-ins"] a[aria-current]'), r = a.getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth + 1; }));
const ptiLinks = page.locator('nav[aria-label="Plug-ins"] a');
await ptiLinks.first().focus();
await page.keyboard.press("Tab");
await page.keyboard.press("Tab");
const ptiFocus = await page.evaluate(() => { const a = document.activeElement; return { name: a.textContent.trim(), shown: (a.querySelector(".menu-tabs__label")?.getBoundingClientRect().width || 0) > 8, ring: getComputedStyle(a).outlineStyle !== "none" }; });
check("PTI-06", "Tab moves along the tabs, and the tab with focus shows its name and a focus ring", ptiFocus.shown && ptiFocus.ring && ptiFocus.name.length > 0, JSON.stringify(ptiFocus));
check("PTI-07", "the row scrolls inside itself, not the page", await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
await open("settings-plugins.html");
check("PTI-09", "at 375 wide a notice with buttons keeps its words readable (DASH-602)", await page.evaluate(() => [...document.querySelectorAll(".notice")].every((n) => (n.querySelector(".notice__body")?.getBoundingClientRect().width || 999) > 150)));
await page.setViewportSize({ width: 1280, height: 860 });
await open("settings-plugin.html?id=notifications");
await page.waitForFunction(() => document.querySelectorAll('nav[aria-label="Plug-ins"] a').length > 4, null, { timeout: 5000 }).catch(() => {});
pti = await ptiTabs();
check("PTI-08", "on a computer the same icons show, and the tab name shows for the current tab", pti.length > 4 && pti.slice(2).every((x) => x.icon && x.h >= 44) && pti.find((x) => x.current)?.shown, JSON.stringify(pti.filter((x) => x.current)));

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
