// How people use Starboard, by keyboard alone, as a screen reader user would (owner, 12 November 2026). Each task
// is done with keys only; after each step it checks where focus is (never lost to the top of the page) and what
// was said (the polite announcer, saved notes, the page title). tools/a11y.sh runs it with TASKS=1.
import { chromium } from "playwright";
import fs from "fs";

const base = process.env.BASE;
const password = fs.readFileSync(process.env.PASSWORD_FILE, "utf8").trim();
let passed = 0, failed = 0;
const check = (id, what, ok, detail = "") => { ok ? passed++ : failed++; console.log(`${ok ? "PASS" : "FAIL"} ${id} ${what}${!ok && detail ? `: ${detail}` : ""}`); };
const browser = await chromium.launch();
const page = await (await browser.newContext({ viewport: { width: 1280, height: 860 } })).newPage();
const focus = () => page.evaluate(() => {
  const e = document.activeElement;
  if (!e || e === document.body) return { lost: true, text: "the page itself" };
  return { lost: false, tag: e.tagName, id: e.id, role: e.getAttribute("role") || "", text: (e.getAttribute("aria-label") || e.textContent || e.value || "").trim().replace(/\s+/g, " ").slice(0, 60),
    inMain: !!e.closest("main"), inPanel: !!e.closest("#side-panel, dialog") };
});
const said = () => page.evaluate(() => [...document.querySelectorAll("#announcer, [role=status], [role=alert], .saved-note:not([hidden])")]
  .map((n) => n.textContent.trim()).filter(Boolean).join(" | ").slice(0, 200));
const settle = async () => {
  await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
  await page.waitForFunction(() => !document.querySelector("[aria-busy=true]"), null, { timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(700);
};
const tabTo = async (match, most = 120) => {
  for (let i = 0; i < most; i++) {
    await page.keyboard.press("Tab");
    const f = await focus();
    if (match(f)) return f;
  }
  return null;
};

// T1 Sign in with the keyboard: the password field has focus first, Enter signs in.
await page.goto(`${base}/login.html`);
await page.keyboard.type(password);
await page.keyboard.press("Enter");
await page.waitForURL((u) => !u.pathname.endsWith("login.html"), { timeout: 15000 }).catch(() => {});
check("T1", "the password field has focus when Sign in opens, and Enter signs in", !page.url().endsWith("login.html"));
await settle();

// T2 Nothing opens by itself (owner, 12 November 2026: Still to set up only from Go through them).
await page.waitForTimeout(1500);
const opened = await focus();
check("T2", "no slide-out opens by itself after signing in", !opened.inPanel && !(await page.locator("#side-panel").count()), opened.text);
// Go through them opens it with focus in it; Escape gives focus back to Go through them.
const walk = page.getByRole("button", { name: /Go through them/ }).first();
if (await walk.count()) {
  await walk.focus();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(1200);
  const inside = await focus();
  check("T2", "Go through them opens Still to set up with focus on the step", inside.inPanel && !/^IFRAME$/.test(inside.tag), inside.tag + " " + inside.text);
  await page.keyboard.press("Escape");
  await page.waitForTimeout(500);
  const back = await focus();
  // The card is drawn again as it closes: focus goes to Go through them, or to that card's own heading.
  check("T2", "Escape gives focus back to Go through them, or its card", /Go through them|Still to set up/.test(back.text) && back.inMain, back.text);
}
// Skip to main content: the first Tab stop on a fresh page, and it moves focus into the page's own part.
await page.goto(`${base}/settings-general.html`);
await settle();
await page.keyboard.press("Tab");
const skip = await focus();
check("T2", "the first Tab stop is Skip to main content", /skip to main/i.test(skip.text), skip.text);
await page.keyboard.press("Enter");
await page.keyboard.press("Tab");
const afterSkip = await focus();
check("T2", "after Skip, the next Tab is inside the page's own part", afterSkip.inMain, afterSkip.text);

// T3 Search: from the header, type and press Enter; the result count is said; focus is not lost.
await page.goto(`${base}/index.html`);
await settle();
await page.locator("#header-search-input").focus();
await page.keyboard.type("harbour");
await page.keyboard.press("Enter");
await page.waitForURL(/search\.html/, { timeout: 10000 }).catch(() => {});
await settle();
const s3 = await said(), f3 = await focus();
check("T3", "search says how much it found", /result|found|in your library|no /i.test(s3), s3);
// A new page starts at its top (the browser's own place), and its tab title says which page it is.
check("T3", "the results page's tab title names it", /^Search/.test(await page.title()), await page.title());
check("T3", "focus after searching is at the page's start or in it", f3.lost || f3.inMain, f3.text);

// T4 Library: Tab to a film and open it with Enter; the film page's h1 is its title and the tab title names it.
await page.goto(`${base}/library-films.html`);
await settle();
const film = await tabTo((f) => f.tag === "A" && f.inMain && /\w/.test(f.text) && !/^[A-Z#]$/.test(f.text) && !/My library|Collections/.test(f.text));
check("T4", "a film can be reached with Tab", !!film, film?.text);
await page.keyboard.press("Enter");
await page.waitForURL(/library-film\.html/, { timeout: 10000 }).catch(() => {});
await settle();
const h1 = await page.evaluate(() => document.querySelector("main h1")?.textContent.trim());
const title = await page.title();
check("T4", "the film page's h1 is its title, and the tab title starts with it", !!h1 && title.startsWith(h1), `${h1} / ${title}`);

// T5 A setting: Tab to a switch, Space changes it; focus stays on it and the saved note says so.
await page.goto(`${base}/settings-general.html#topic-2`);
await settle();
await page.evaluate(() => document.querySelector(".page-head input[role=switch]")?.click());
await page.waitForTimeout(400);
await page.evaluate(() => [...document.querySelectorAll("#topic-tabs [role=tab]")].find((t) => /App cards/.test(t.textContent))?.click());
await page.waitForTimeout(300);
await page.locator('[aria-labelledby="card-home-l"]').focus().catch(() => {});
const sw = await focus();
if (sw && sw.role === "switch") {
  await page.keyboard.press("Space");
  await page.waitForTimeout(1500);
  const f5 = await focus(), s5 = await said();
  check("T5", "focus stays on the switch after it saves", !f5.lost && f5.tag === "INPUT", f5.text);
  check("T5", "the change is said (saved note)", /saved|activated|deactivated|on|off/i.test(s5), s5);
  await page.keyboard.press("Space");
  await page.waitForTimeout(1200);
} else check("T5", "a switch can be reached with Tab", false);

// T6 Edit an app in a slide-out: Enter opens it, focus goes in, Escape closes and focus comes back to Edit.
await page.goto(`${base}/settings.html`);
await settle();
const edit = await tabTo((f) => f.tag === "BUTTON" && /^Edit/.test(f.text) && f.inMain, 80);
check("T6", "Edit on an app can be reached with Tab", !!edit, edit?.text);
if (edit) {
  await page.keyboard.press("Enter");
  await page.waitForTimeout(600);
  const f6 = await focus();
  check("T6", "focus moves into the slide-out", f6.inPanel, f6.text);
  await page.keyboard.press("Escape");
  await page.waitForTimeout(500);
  const g6 = await focus();
  check("T6", "Escape closes it and focus returns to Edit", /^Edit/.test(g6.text), g6.text);
}

// T7 Make a key and revoke it: after Revoke, the row is gone and focus is not lost to the top.
await page.goto(`${base}/settings-security.html`);
await settle();
await page.evaluate(() => [...document.querySelectorAll("#topic-tabs [role=tab]")].find((t) => /API keys/.test(t.textContent))?.click());
await page.waitForTimeout(300);
const make = await tabTo((f) => f.tag === "BUTTON" && /Make a key/.test(f.text), 80);
check("T7", "Make a key can be reached with Tab", !!make);
if (make) {
  await page.keyboard.press("Enter");
  await page.waitForTimeout(500);
  const f7a = await focus();
  check("T7", "Make a key starts in its first field", f7a.id === "key-name", f7a.id || f7a.text);
  await page.keyboard.type("Journey key");
  await page.locator("#key-password").fill(password);
  await page.locator("#key-password").press("Enter");
  await page.waitForTimeout(1500);
  const f7 = await focus();
  check("T7", "the new key has focus, ready to copy", f7.id === "key-made", f7.text || f7.id);
  await page.keyboard.press("Escape");
  await page.waitForTimeout(500);
  const edit7 = page.locator("#security-sections .row", { hasText: "Journey key" }).getByRole("button", { name: /Edit/ });
  await edit7.focus();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(500);
  await page.locator("#side-panel").getByRole("button", { name: /Revoke/ }).focus();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(400);
  const first = await focus();
  check("T7", "the confirm box opens with focus on Cancel, the safe choice", /Cancel/.test(first.text), first.text);
  await page.locator("dialog button[value=ok]").focus();
  await page.keyboard.press("Enter");  // the dialog's Revoke
  await page.waitForTimeout(1500);
  const g7 = await focus(), s7 = await said();
  check("T7", "after Revoke, focus is not lost to the top of the page", !g7.lost && !g7.inPanel, g7.text);
  check("T7", "the revoke is said", /revoked/i.test(s7), s7);
}

// T8 Show more on Wanted: focus moves to the first new row and the count is said.
await page.goto(`${base}/wanted-films.html`);
await settle();
const s8a = await said();
check("T8", "the list's count is said when it loads", /\d/.test(s8a), s8a);
const more = page.locator("#wanted-more button, #wanted-more");
if (await more.first().isVisible().catch(() => false)) {
  await more.first().focus();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(1500);
  const f8 = await focus();
  check("T8", "after Show more, focus is on the first new row", !f8.lost && f8.inMain && !/more/i.test(f8.text), f8.text);
} else console.log("note T8 the example has no second page of Wanted");

// T9 A film's Files and history (DASH-209): arrow to the tab, Delete this file by keyboard; after it, focus is on the
// Files heading and the deletion is said.
await page.goto(`${base}/library-film.html?id=1`);
await settle();
const extrasTab = page.locator("#tab-extras");
if (await extrasTab.count()) {
  await page.locator("[role=tab][aria-selected=true]").focus();
  await page.keyboard.press("End");
  await settle();
  check("T9", "End moves to the Files and history tab and opens it", await page.locator("#panel-extras").isVisible());
  const del = page.locator("#panel-extras .lib-files button").first();
  if (await del.count()) {
    await del.focus();
    await page.keyboard.press("Enter");
    await page.waitForTimeout(400);
    const inDialog = await focus();
    check("T9", "Delete this file opens a dialog with focus in it", inDialog.inPanel, inDialog.text);
    await page.keyboard.press("Shift+Tab");
    await page.keyboard.press("Enter");
    await settle();
    const f9 = await focus(), s9 = await said();
    check("T9", "after Delete this file, focus is on the Files heading", f9.id === "extras-files-heading", f9.text);
    check("T9", "the deletion is said", /deleted/i.test(s9), s9);
  } else console.log("note T9 the example film has no file");
} else check("T9", "the film page has a Files and history tab", false);

// T10 Select several (DASH-206): Space ticks, the count is said, an action returns focus to Select several.
await page.goto(`${base}/library-films.html`);
await settle();
const selectBtn = page.locator("#lib-select");
if (await selectBtn.count()) {
  await selectBtn.focus();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(300);
  const t10 = await focus();
  check("T10", "Select several moves focus to the first tick", /^Tick /.test(t10.text), t10.text);
  await page.keyboard.press("Space");
  await page.waitForTimeout(300);
  const count = await page.locator("#lib-bulk-count").textContent();
  check("T10", "the ticked count updates in a polite live region", /1 ticked/.test(count), count);
  await page.locator("#lib-bulk button", { hasText: "Stop following" }).focus();
  await page.keyboard.press("Enter");
  await settle();
  const f10 = await focus();
  check("T10", "after the action, focus is back on Select several", f10.id === "lib-select", f10.text);
} else check("T10", "the Films wall has Select several", false);

// T11 Keep for a podcast (DASH-319): the choice opens in a dialog, arrows move without saving, Save gives focus back.
await page.goto(`${base}/library-radio-show.html?id=13`);
await settle();
const keepBtn = page.locator("#radio-keep");
if (await keepBtn.count()) {
  await keepBtn.focus();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(400);
  const k1 = await focus();
  check("T11", "Keep opens with focus on the chosen option", k1.inPanel && k1.tag === "INPUT", k1.text);
  await page.keyboard.press("ArrowDown");
  check("T11", "moving through the options saves nothing", (await page.locator("dialog[open]").count()) === 1);
  await page.keyboard.press("Tab");
  await page.keyboard.press("Enter");
  await settle();
  const k2 = await focus(), s11 = await said();
  check("T11", "after Save, focus is back on Keep", k2.id === "radio-keep", k2.text);
  check("T11", "the change is said", /keeps/i.test(s11), s11);
} else console.log("note T11 the example has no podcast with Keep");

// T12 Live TV's channels in sub menus (DASH-361): Enter on a list's row opens it with focus on its heading; Space on
// a channel's switch keeps focus on it and says what it did; the back link returns focus to the row that opened it.
await page.goto(`${base}/settings-plugin.html?id=livetv`);
await settle();
const chTab = page.getByRole("tab", { name: "Channels" });
if (await chTab.count() && await page.locator('[data-menu="in:samsung"]').count()) {
  await chTab.focus();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(300);
  const row = await tabTo((f) => f.text === "Samsung TV Plus" && f.tag === "BUTTON", 60);
  check("T12", "Tab reaches a list's row in Channels", !!row, row ? row.text : "not reached");
  await page.keyboard.press("Enter");
  await page.waitForTimeout(300);
  const h = await focus();
  check("T12", "Enter opens the list with focus on its heading", h.tag === "H3" && h.text === "Samsung TV Plus", `${h.tag} ${h.text}`);
  const sub = await tabTo((f) => f.text === "US" && f.tag === "BUTTON", 40);
  await page.keyboard.press("Enter");
  await page.waitForTimeout(300);
  const sec = await tabTo((f) => f.text === "News" && f.tag === "BUTTON", 40);
  await page.keyboard.press("Enter");
  await page.waitForTimeout(300);
  const toggle = await tabTo((f) => /^(Activate|Deactivate) /.test(f.text) && f.tag === "BUTTON", 40);
  check("T12", "a region and a section open by keyboard, down to the channels", !!(sub && sec && toggle), toggle ? toggle.text : "not reached");
  if (toggle) {
    await page.keyboard.press("Space");
    await settle();
    const t2 = await focus(), s12 = await said();
    check("T12", "after Activate or Deactivate, focus is on the channel's button again", /^(Activate|Deactivate) /.test(t2.text) && t2.inMain, t2.text);
    check("T12", "what it did is said", /activated|deactivated/i.test(s12), s12);
  }
  await page.locator(".back-link--button").first().focus();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(300);
  const b12 = await focus();
  check("T12", "the back link returns focus to the row that opened it", b12.text === "News" && b12.tag === "BUTTON", `${b12.tag} ${b12.text}`);
} else console.log("note T12 the example has no Live TV channels");

// T13 Release notes (UX-50): Tab reaches Release notes in the footer; Enter opens the slide-out with focus in it,
// the newest 3 releases and Read previous releases; Escape closes it and gives focus back to Release notes.
await page.goto(`${base}/settings-general.html`);
await settle();
await page.locator(".site-footer__brand").scrollIntoViewIfNeeded();
await page.locator(".site-footer__links a").first().focus();
const notesLink = await tabTo((f) => f.text === "Release notes" && f.tag === "A", 5);
check("T13", "Tab reaches Release notes in the footer", !!notesLink, notesLink ? notesLink.text : "not reached");
check("T13", "Release notes says it opens a slide-out", (await page.locator(".site-footer a", { hasText: "Release notes" }).getAttribute("aria-haspopup")) === "dialog");
await page.keyboard.press("Enter");
await page.waitForFunction(() => document.querySelectorAll("#side-panel .release-notes").length > 0, null, { timeout: 8000 }).catch(() => {});
const r1 = await focus();
check("T13", "Enter opens the release notes with focus in the slide-out", r1.inPanel, r1.text);
const shownReleases = await page.locator("#side-panel .release-notes").count();
check("T13", "the slide-out shows the newest 3 releases", shownReleases === 3, `${shownReleases} shown`);
const prev = page.locator("#side-panel a", { hasText: "Read previous releases" });
check("T13", "then Read previous releases, to Settings, Updates, Releases", (await prev.count()) === 1 && (await prev.getAttribute("href")) === "/settings-releases.html");
const reached = await tabTo((f) => f.text === "Read previous releases", 10);
check("T13", "Tab reaches Read previous releases inside the slide-out", !!reached && reached.inPanel, reached ? reached.text : "not reached");
await page.keyboard.press("Escape");
await page.waitForTimeout(400);
const r2 = await focus();
check("T13", "Escape closes it and gives focus back to Release notes", r2.text === "Release notes" && !r2.inPanel && !(await page.locator("#side-panel").count()), r2.text);

// T14 What is new on a plug-in's State (DASH-393): Tab reaches Got it inside the notice, which is a polite status;
// Enter hides it and puts focus on the State heading, and it is not shown again.
await page.goto(`${base}/settings-plugin.html?id=styles`);
await settle();
const wn14 = page.locator("#pl-styles-whats-new");
if (await wn14.count()) {
  check("T14", "What is new is a polite status", (await wn14.getAttribute("role")) === "status");
  await page.evaluate(() => { const h = document.querySelector("#pl-styles-state-h"); h.tabIndex = -1; h.focus(); });
  const got = await tabTo((f) => /^Got it/.test(f.text) && f.tag === "BUTTON", 30);
  check("T14", "Tab reaches Got it in What is new", !!got, got ? got.text : "not reached");
  await page.keyboard.press("Enter");
  await settle();
  const g2 = await focus();
  check("T14", "after Got it, focus is on the State heading", g2.id === "pl-styles-state-h" && g2.inMain, `${g2.tag} ${g2.id} ${g2.text}`);
  check("T14", "What is new is gone", !(await page.locator("#pl-styles-whats-new").count()));
} else check("T14", "the example Styles plug-in shows What is new", false, "not shown");

await browser.close();
console.log(`\n== ${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
