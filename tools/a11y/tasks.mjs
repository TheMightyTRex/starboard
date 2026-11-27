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
  return { lost: false, tag: e.tagName, id: e.id, name: e.name || "", role: e.getAttribute("role") || "", text: (e.getAttribute("aria-label") || e.textContent || e.value || "").trim().replace(/\s+/g, " ").slice(0, 60),
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
const film = await tabTo((f) => f.tag === "A" && f.inMain && /\w/.test(f.text) && !/^[A-Z#]$/.test(f.text) && !/My library|Collections|Bring in media/.test(f.text));
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

// T5b Appearance (DASH-389): Tab reaches Underline links among the accessibility options; Space applies it at once,
// focus stays on the switch, and the saved note says so.
await page.goto(`${base}/settings-general-appearance.html`);
await settle();
const under = await tabTo((f) => f.id === "ap-pref-underline", 80);
check("T5b", "Underline links on Appearance can be reached with Tab", !!under);
if (under) {
  await page.keyboard.press("Space");
  await page.waitForTimeout(800);
  const f5b = await focus(), s5b = await said();
  check("T5b", "focus stays on the switch after it applies", f5b.id === "ap-pref-underline", f5b.text);
  check("T5b", "the change is said", /saved/i.test(s5b), s5b);
  check("T5b", "links are underlined at once", await page.evaluate(() => document.documentElement.classList.contains("pref-underline")));
  await page.keyboard.press("Space");
  await page.waitForTimeout(500);
}

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
await page.goto(`${base}/settings-security-keys.html`);
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
  check("T7", "the new key's Copy has focus, ready to copy", f7.tag === "BUTTON" && /^Copy/.test(f7.text), f7.text || f7.id);
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

// T15 Read-only plug-in tables (DASH-402, plug-in API 1.11): Tab reaches a section's line in Watch statistics; Enter
// opens it with focus kept on the line, which says it is expanded; the table has no tick boxes or buttons to Tab past.
await page.goto(`${base}/settings-plugin.html?id=watch-stats`);
await settle();
const wsTab = page.getByRole("tab", { name: "Recent plays" });
if (await wsTab.count()) {
  await wsTab.focus();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(400);
  const line = await tabTo((f) => /^Today/.test(f.text) && f.tag === "BUTTON", 30);
  check("T15", "Tab reaches a section's line", !!line, line ? line.text : "not reached");
  await page.keyboard.press("Enter");
  await page.waitForTimeout(300);
  const f15 = await focus();
  check("T15", "Enter opens it with focus kept on the line", /^Today/.test(f15.text) && f15.tag === "BUTTON", f15.text);
  check("T15", "the line says it is expanded", (await page.locator(".fold__toggle").first().getAttribute("aria-expanded")) === "true");
  check("T15", "the table has nothing to tick or press but its column sort buttons", !(await page.locator(".fold__panel input, .fold__panel tbody button").count()));
} else check("T15", "the example Watch statistics plug-in has its tables", false, "no Recent plays tab");
// T16 Where backups go (DASH-380, several places 26 November 2026): from the section's heading, Tab reaches the first
// place's switch, then its Test, Change and Remove, then the next place; Enter on Test keeps focus on it and the result
// is shown beside the place and said in the polite announcer.
await page.goto(`${base}/settings-general-backup.html`);
await settle();
await page.evaluate(() => { const h = document.querySelector("#bk-copies-h"); h.tabIndex = -1; h.focus(); });
const sw16 = await tabTo((f) => f.tag === "INPUT" && f.id === "place-on-main", 8);
check("T16", "Tab reaches the first place's switch", !!sw16, sw16 ? sw16.text : "not reached");
const test16 = await tabTo((f) => /^Test/.test(f.text) && f.tag === "BUTTON", 4);
check("T16", "Tab reaches Test, named for its place", !!test16 && /USB disk/.test(test16.text), test16 ? test16.text : "not reached");
if (test16) {
  await page.keyboard.press("Enter");
  await settle();
  const f16 = await focus();
  check("T16", "after Test, focus stays on it", f16.id === "place-test-main", `${f16.tag} ${f16.id}`);
  await page.waitForFunction(() => /^Connected: /.test(document.querySelector("#announcer")?.textContent || ""), null, { timeout: 3000 }).catch(() => {});
  check("T16", "the result is beside the place and said politely", /Connected/.test(await page.locator("#place-tested-main").innerText())
    && /^Connected: /.test(await page.locator("#announcer").innerText()), await page.locator("#announcer").innerText());
}
// T17 Recommended Jellyfin plug-ins (DASH-404): arrows choose Trakt's Install and activate without doing anything,
// Tab to Apply this choice and Enter installs it; focus stays in Trakt's choice and the result is said.
await page.goto(`${base}/settings-jellyfin.html#jf-plugins`);  // its topic tab
await settle();
const trakt = page.locator("#jf-plugins-list form[data-key=trakt]");
await trakt.waitFor({ state: "attached", timeout: 10000 }).catch(() => {});
const plugTab = page.getByRole("tab", { name: "Recommended plug-ins" });
if (await plugTab.count()) {  // a person opens its topic tab with the keyboard
  await plugTab.focus();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(300);
}
if (await trakt.count()) {
  await trakt.locator("input[value=none]").focus();
  const f15a = await focus();
  await page.keyboard.press("ArrowUp");
  check("T15", "an arrow moves to Install and activate without installing", (await trakt.locator("input[value=on]").isChecked())
    && !/Installed Trakt/.test(await page.locator("#jf-plugins-list").textContent()), `${f15a.tag} ${f15a.text}`);
  const apply = await tabTo((f) => f.tag === "BUTTON" && /^Apply this choice/.test(f.text), 5);
  check("T15", "Tab reaches Apply this choice", !!apply, apply ? apply.text : "not reached");
  await page.keyboard.press("Enter");
  await settle();
  const f15 = await focus(), s15 = await said();
  check("T15", "after Apply, focus stays in Trakt's choice", !f15.lost && await page.evaluate(() => !!document.activeElement.closest("form[data-key=trakt]")), `${f15.tag} ${f15.text}`);
  check("T15", "the install is said", /Installed Trakt/.test(s15), s15);
} else check("T15", "the example Jellyfin shows its recommended plug-ins", false, "not shown");
// T18 Audio description tracks (DASH-410, plug-in API 1.12): from the page's heading, Tab reaches the Plays in step
// choice for a file; an arrow chooses, focus stays on that choice and what happened is said; Tab goes on to the row's
// link, which says it opens in a new tab, and to the file picker for an upload.
await page.goto(`${base}/settings-plugin.html?id=audio-description-tracks`);
await settle();
const tracksTab = page.getByRole("tab", { name: "Tracks" });
if (await tracksTab.count()) {
  await tracksTab.focus();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(300);
}
const step = await tabTo((f) => f.tag === "SELECT" && /^Plays in step\?: Dune/.test(f.text), 80);
check("T18", "Tab reaches the Plays in step choice for a file", !!step, step ? step.text : "not reached");
if (step) {
  await page.keyboard.press("ArrowDown");
  await settle();
  const f18 = await focus(), s18 = await said();
  check("T18", "after choosing, focus stays on that choice", f18.tag === "SELECT" && /^Plays in step\?: Dune/.test(f18.text), `${f18.tag} ${f18.text}`);
  check("T18", "what happened is said", /example data/.test(s18), s18);
}
const link18 = await tabTo((f) => f.tag === "A" && /^Search AudioVault for Brazil/.test(f.text), 20);
check("T18", "Tab reaches the row's link, which says it opens in a new tab", !!link18 && /opens in a new tab/.test(link18.text), link18 ? link18.text : "not reached");
const file18 = await tabTo((f) => f.tag === "INPUT" && f.inMain && f.id === "add-audio-description-tracks-inbox-file", 20);
check("T18", "Tab reaches the file picker for an upload", !!file18, file18 ? file18.id : "not reached");

// T19 Recommended plug-ins (DASH-425): from the Catalogue's heading, Tab reaches Install for a recommended plug-in,
// whose name is said; Enter opens What it may do with focus in it; Escape closes it and focus goes back to Install.
await page.goto(`${base}/settings-plugins-catalogue.html`);
await settle();
await page.locator("h1").first().focus().catch(() => {});
const rec = await tabTo((f) => f.tag === "BUTTON" && /^Install… Disk forecast$/.test(f.text), 80);
check("T19", "Tab reaches Install for a recommended plug-in, named for a screen reader", !!rec, rec ? rec.text : "not reached");
if (rec) {
  await page.keyboard.press("Enter");
  await settle();
  const in19 = await focus();
  if (in19.inPanel) {  // the warning opened: focus is in it, and Escape gives it back to Install
    check("T19", "Install opens the warning with focus in it", !in19.lost, `${in19.tag} ${in19.text}`);
    await page.keyboard.press("Escape");
    await settle();
    const back19 = await focus();
    check("T19", "Escape closes it and focus goes back to Install", /^Install… Disk forecast$/.test(back19.text), back19.text);
  } else {  // the example server has no copy of its manifest: the problem is said and focus is not lost
    check("T19", "when the warning cannot open, focus is not lost and the problem is said", !in19.lost && !!(await said()), `${in19.text} / ${await said()}`);
  }
}

// T20 A schedule setting (plug-in API 1.14, DASH-432): Tab reaches How often; the arrow keys choose Every week, which
// saves at once with the saved note said, focus stays on the list, and Day comes next in the Tab order.
await page.goto(`${base}/settings-plugin.html?id=picture-shrinker`);
await settle();
const tab20 = page.getByRole("tab", { name: "Settings", exact: true });
if (await tab20.count()) { await tab20.focus(); await page.keyboard.press("Enter"); await page.waitForTimeout(300); }
const often20 = await tabTo((f) => f.id === "pl-picture-shrinker-when-every", 160);
check("T20", "Tab reaches How often in the schedule setting", !!often20, "not reached");
if (often20) {
  await page.keyboard.press("ArrowUp");  // Every month to Every week
  await page.waitForTimeout(900);
  const f20 = await focus();
  check("T20", "choosing Every week keeps focus on How often", f20.id === "pl-picture-shrinker-when-every", f20.id);
  check("T20", "the saved note is said beside it", /Saved/.test(await said()), await said());
  await page.keyboard.press("Tab");
  const day20 = await focus();
  check("T20", "Day is next in the Tab order once it shows", day20.id === "pl-picture-shrinker-when-day", day20.id);
  await page.evaluate(async () => { await api("/api/plugins/picture-shrinker/settings", { method: "PUT", body: { settings: { when: { every: "month", date: 31, time: "03:30" } } } }); });
}
// T32 Check for updates and What is new by keyboard (DASH-462): Tab reaches Check for updates; Enter keeps focus on it
// and the result is said in Ready to update's polite live region; Tab reaches What is new; Enter opens the slide-out
// with focus inside it; Tab reaches the first jump link and Enter takes focus to that item's heading; Escape closes
// it and focus returns to What is new.
await page.goto(`${base}/settings-updates.html`);
await settle();
const go32 = await tabTo((f) => f.tag === "BUTTON" && f.id === "check-updates-now", 80);
check("T32", "Tab reaches Check for updates", !!go32, "not reached");
if (go32) {
  await page.keyboard.press("Enter");
  await page.locator("#up-list-summary", { hasText: "Last checked at" }).waitFor({ timeout: 30000 }).catch(() => {});
  const f32 = await focus();
  check("T32", "focus stays on Check for updates", f32.id === "check-updates-now", `${f32.id} ${f32.text}`);
  check("T32", "what it found is said in a polite live region", /Last checked at \d\d:\d\d/.test(await page.locator("#up-list-summary[role=status][aria-live=polite]").textContent()));
  await page.keyboard.down("Shift"); await page.keyboard.press("Tab"); await page.keyboard.up("Shift");
  const wn32 = await focus();
  check("T32", "What is new is just before it in the Tab order", wn32.id === "whats-new", `${wn32.id} ${wn32.text}`);
  await page.keyboard.press("Enter");
  await page.locator("#side-panel section.release-notes").first().waitFor({ timeout: 15000 }).catch(() => {});
  const in32 = await focus();
  check("T32", "Enter opens What is new with focus inside it", in32.inPanel, in32.text);
  const link32 = await tabTo((f) => f.tag === "A" && f.inPanel, 10);
  check("T32", "Tab reaches the first jump link", !!link32, "not reached");
  if (link32) {
    await page.keyboard.press("Enter");
    const h32 = await focus();
    check("T32", "Enter takes focus to that item's heading", h32.tag === "H3" && h32.inPanel && h32.text === link32.text, `${h32.tag} ${h32.text}`);
  }
  await page.keyboard.press("Escape");
  await page.waitForTimeout(500);
  const back32 = await focus();
  check("T32", "Escape closes it and focus returns to What is new", back32.id === "whats-new", `${back32.id} ${back32.text}`);
}

// T29 Install all updates by keyboard (DASH-454): Tab reaches Install all updates, which says how many; Enter asks for
// the password with focus in the field; Enter then lists what installs with focus on the main button; Enter starts it,
// and focus goes to the batch's panel heading; each change is said in its polite live region; at the end the result
// takes focus. The example server only acts each update's steps (Starboard's writes update.sh's lines).
await page.goto(`${base}/settings-updates.html`);
await settle();
const go29 = await tabTo((f) => f.tag === "BUTTON" && /^Install all \d+ updates$/.test(f.text), 80);
check("T29", "Tab reaches Install all updates, which says how many", !!go29, "not reached");
if (go29) {
  await page.keyboard.press("Enter");
  await page.waitForTimeout(600);
  const pw29 = await focus();
  check("T29", "Enter asks for the password, with focus in the field", pw29.inPanel && pw29.tag === "INPUT", `${pw29.tag} ${pw29.text}`);
  await page.keyboard.type(password);
  await page.keyboard.press("Enter");
  await page.getByRole("dialog", { name: /^Install \d+ updates?$/ }).waitFor({ timeout: 10000 }).catch(() => {});
  await page.waitForTimeout(500);
  const ok29 = await focus();
  check("T29", "the list of what installs opens with focus on its main button", ok29.inPanel && /^Install \d+ updates?$/.test(ok29.text), ok29.text);
  const listed = await page.evaluate(() => [...(document.querySelector("dialog[open] ol")?.children || [])].map((li) => li.textContent));
  check("T29", "it lists the updates in order, Starboard last", listed.length >= 2 && /^Starboard /.test(listed[listed.length - 1]), listed.join(" / "));
  const title29 = await page.evaluate(() => document.querySelector("dialog[open] h2")?.textContent || "");
  check("T29", "the dialog's title and button count what it lists", title29 === `Install ${listed.length} updates` && ok29.text === title29, `${title29} / ${ok29.text} / ${listed.length}`);
  await page.keyboard.press("Enter");
  await page.waitForTimeout(800);
  const head29 = await focus();
  check("T29", "focus goes to the batch's panel heading", head29.id === "update-all-h", `${head29.id} ${head29.text}`);
  const count29 = (await page.locator("#update-all-count .numeric").textContent()).trim();
  check("T29", "the panel counts the same updates", new RegExp(`^\\d+ of ${listed.length} done$`).test(count29), `${count29} / ${listed.length}`);
  const heard29 = [];
  for (let i = 0; i < 240 && !(await page.locator(".update-all .notice").count()); i++) {
    const t = await page.locator(".update-all [aria-live=polite]").textContent().catch(() => "");
    if (t && !heard29.includes(t)) heard29.push(t);
    await page.waitForTimeout(250);
  }
  await page.waitForTimeout(800);
  check("T29", "each change is said in the panel's polite live region", heard29.some((t) => /: (Done|Updating)/.test(t)), heard29.join(" | "));
  const end29 = await focus();
  check("T29", "the result takes focus at the end", /updates finished|did not install|stopped/i.test(end29.text) && !end29.inPanel, end29.text);
  // DASH-473: Close is the next stop after the result; Enter takes the panel away and focus to Ready to update.
  await page.keyboard.press("Tab");
  const close29 = await focus();
  check("T29", "Tab from the result reaches Close", close29.id === "update-all-close", `${close29.id} ${close29.text}`);
  await page.keyboard.press("Enter");
  await page.waitForTimeout(500);
  const after29 = await focus();
  check("T29", "Close takes the panel away and focus goes to Ready to update", after29.id === "up-list-h"
    && !(await page.locator(".update-all").count()), `${after29.id} ${after29.text}`);
}

// T22 A plug-in update by keyboard (plug-in API 1.14, DASH-424): Tab reaches Update, Enter opens the warning with
// focus inside it and What is new readable before the password; Enter in the password starts the update, whose steps
// dialog takes focus at its heading, says each step in its live region, focuses the result, and Escape gives focus to
// the plug-in's State heading.
await page.goto(`${base}/settings-plugin.html?id=picture-shrinker`);
await settle();
const tab22 = page.getByRole("tab", { name: "Versions", exact: true });
if (await tab22.count()) { await tab22.focus(); await page.keyboard.press("Enter"); await page.waitForTimeout(300); }
const go22 = await tabTo((f) => /^Update to 1\.1\.0/.test(f.text), 200);
check("T22", "Tab reaches Update to 1.1.0", !!go22, "not reached");
if (go22) {
  await page.keyboard.press("Enter");
  await page.getByRole("dialog", { name: "Update Picture shrinker to 1.1.0?" }).waitFor({ timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(500);
  const in22 = await focus();
  check("T22", "the warning opens with focus inside it", in22.inPanel, in22.text);
  const order22 = await page.evaluate(() => {
    const panel = document.activeElement?.closest("#side-panel, dialog, [role=dialog]");
    const texts = [...(panel?.querySelectorAll("h2, h3, input") || [])].map((n) => n.tagName === "INPUT" ? `input#${n.id}` : n.textContent.trim());
    return texts;
  });
  const newAt = order22.findIndex((t) => /What is new since 1\.0\.0/.test(t)), pwAt = order22.indexOf("input#pl-install-password");
  check("T22", "What is new and how it is kept safe come before the password", newAt >= 0 && pwAt > newAt
    && order22.some((t) => /kept safe/.test(t)), order22.join(" / "));
  const pw22 = await tabTo((f) => f.id === "pl-install-password", 60);
  check("T22", "Tab reaches the password in the warning", !!pw22, "not reached");
  await page.keyboard.type(password);
  await page.keyboard.press("Enter");
  const run22 = page.getByRole("dialog", { name: "Updating Picture shrinker to 1.1.0" });
  await run22.waitFor({ timeout: 8000 }).catch(() => {});
  const head22 = await focus();
  check("T22", "the steps dialog opens with focus on its heading", head22.text === "Updating Picture shrinker to 1.1.0", head22.text);
  const heard = [];
  for (let i = 0; i < 40 && !(await run22.locator(".notice__title").count()); i++) {
    const t = await run22.locator("[aria-live=polite]").textContent().catch(() => "");
    if (t && !heard.includes(t)) heard.push(t);
    await page.waitForTimeout(250);
  }
  await page.waitForTimeout(300);
  const end22 = await focus();
  check("T22", "each finished step is said in the dialog's live region", heard.some((t) => /: Done$/.test(t)), heard.join(" | "));
  check("T22", "the result takes focus when it finishes", /Picture shrinker is updated/.test(end22.text), end22.text);
  await page.keyboard.press("Escape");
  // The page is drawn again with the new version as the dialog closes: focus settles on State once it is drawn.
  let back22 = await focus();
  for (let i = 0; i < 12 && back22.id !== "pl-picture-shrinker-state-h"; i++) { await page.waitForTimeout(250); back22 = await focus(); }
  const why22 = await page.evaluate(() => {
    const h = document.getElementById("pl-picture-shrinker-state-h");
    return JSON.stringify({ h: !!h, off: h?.closest(".topic-off")?.id || "", hidden: h ? !h.getClientRects().length : null,
      dialogs: document.querySelectorAll("dialog").length, open: document.querySelectorAll("dialog[open]").length,
      panel: !!document.querySelector("#side-panel"), tabs: [...document.querySelectorAll("[role=tab][aria-selected=true]")].map((t) => t.textContent) });
  });
  check("T22", "Escape gives focus to the plug-in's State", back22.id === "pl-picture-shrinker-state-h", `${back22.id || back22.text} ${why22}`);
  check("T22", "State says what is new, in a status region", /What is new in 1\.1\.0/.test(await said()), await said());
}
// T21 The card band (plug-in API 1.14, DASH-428): the dashboard's plug-in cards are reached by heading, and each
// band's chip and time read on their own.
await page.goto(`${base}/dashboard.html`);
await settle();
await page.locator('[data-card="plugin:direct-play:now"] .card-band .chip').waitFor({ timeout: 8000 }).catch(() => {});
const band21 = await page.evaluate(() => {
  const card = document.querySelector('[data-card="plugin:direct-play:now"]');
  const h = card?.querySelector(".card-band h2");
  return { labelled: card?.getAttribute("aria-labelledby") === h?.id, chip: card?.querySelector(".card-band .chip")?.textContent,
    time: card?.querySelector(":scope > .card-foot time")?.textContent  /* 0.19.1: the time is in the card's footer */, focusable: card?.querySelectorAll(".card-band a, .card-band button, .card-band [tabindex]").length };
});
check("T21", "the card is named by its band's heading", band21.labelled, JSON.stringify(band21));
check("T21", "the chip and the time read on their own", band21.chip === "Status: Converting" && /^Updated /.test(band21.time || ""), JSON.stringify(band21));
check("T21", "the band adds no Tab stops", band21.focusable === 0, JSON.stringify(band21));

// T24 Copy issues for an AI helper (DASH-434): from the Downloads heading, Tab reaches the button by its name; Enter
// copies, the live region says "Copied N issues", and focus stays on the button.
await page.context().grantPermissions(["clipboard-read", "clipboard-write"], { origin: base });
await page.goto(`${base}/downloads.html`);
await settle();
await page.locator("h1").first().focus().catch(() => {});
const copy24 = await tabTo((f) => f.tag === "BUTTON" && f.text === "Copy issues for an AI helper", 150);
check("T24", "Tab reaches Copy issues for an AI helper, named for a screen reader", !!copy24, copy24 ? copy24.text : "not reached");
if (copy24) {
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => /^Copied \d+ issues?$/.test(document.querySelector("#announcer")?.textContent || ""), null, { timeout: 15000 }).catch(() => {});
  const after24 = await focus();
  check("T24", "Enter copies and the live region says how many", /Copied \d+ issues?/.test(await said()), await said());
  check("T24", "focus stays on the button", after24.text === "Copy issues for an AI helper", after24.text);
  const next24 = await tabTo((f) => f.tag === "BUTTON", 3);
  check("T24", "Tab goes on to Download as Markdown", next24?.text === "Download as Markdown", next24?.text);
}

// T25 Upload a zip file by keyboard (DASH-414): Tab reaches the zip field, then Check the zip; Enter with no file says
// what to do, in a live place, and focus goes back to the field.
await page.goto(`${base}/settings-plugins-catalogue.html#pl-zip-h`);  // its topic tab
await settle();
await page.locator('#pl-zip-h').scrollIntoViewIfNeeded().catch(() => {});
await page.locator('#pl-zip').focus().catch(() => {});
const zf = await focus();
check("T25", "the zip field takes focus and is named", zf.id === "pl-zip" && !zf.lost, JSON.stringify(zf));
const zb = await tabTo((f) => f.tag === "BUTTON" && f.text === "Check the zip", 4);
check("T25", "Tab goes from the zip field to Check the zip", !!zb, zb ? zb.text : "not reached");
if (zb) {
  await page.keyboard.press("Enter");
  await page.waitForTimeout(500);
  const back = await focus();
  const err = await page.evaluate(() => { const i = document.getElementById("pl-zip"); const id = (i.getAttribute("aria-describedby") || "").split(" ").find((x) => x.endsWith("-error"));
    return { invalid: i.getAttribute("aria-invalid"), text: id ? document.getElementById(id)?.textContent : "" }; });
  check("T25", "with no file, the field says what to do and keeps focus", back.id === "pl-zip" && /Choose the plug-in's zip file/.test(err.text || "") , JSON.stringify({ back, err }));
}

// T26 Pictures and details by keyboard (DASH-431): on Settings, Jellyfin, Tab reaches Move them out of the settings
// folder; Enter opens the confirmation with focus in it, and Escape gives focus back to the button.
await page.goto(`${base}/settings-jellyfin.html#jf-metadata-h`);  // its topic tab
await settle();
await page.locator('#jf-metadata-h').scrollIntoViewIfNeeded().catch(() => {});
await page.locator('#jf-metadata-h').evaluate((h) => { h.tabIndex = -1; h.focus(); }).catch(() => {});
const mv = await tabTo((f) => f.tag === "BUTTON" && /^Move them out of the settings folder/.test(f.text), 10);
check("T26", "Tab reaches Move them out of the settings folder, named for a screen reader", !!mv, mv ? mv.text : "not reached");
if (mv) {
  await page.keyboard.press("Enter");
  await settle();
  const in25 = await focus();
  check("T26", "Enter opens the confirmation with focus in it", in25.inPanel && !in25.lost, JSON.stringify(in25));
  await page.keyboard.press("Escape");
  await settle();
  const back25 = await focus();
  check("T26", "Escape closes it and focus goes back to the button", /^Move them out of the settings folder/.test(back25.text), back25.text);
}

// T37 Choose the media server by keyboard (DASH-565): Settings, Apps, Media server. Check it now keeps focus and says what
// it found; choosing None asks first (focus in the box), and after it focus is on what was said; Go back to Jellyfin
// does the same and leaves Jellyfin in use.
await page.goto(`${base}/settings-jellyfin.html`);
await settle();
const ck = await tabTo((f) => f.tag === "BUTTON" && /^Check it now/.test(f.text), 80);
check("T37", "Tab reaches Check it now, named for a screen reader", !!ck, ck ? ck.text : "not reached");
if (ck) {
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => /answered|did not answer/.test(document.getElementById("ms-said")?.textContent || ""), null, { timeout: 8000 }).catch(() => {});
  const afterCheck = await focus();
  check("T37", "after the check focus stays on the button, and the answer is in the status", /^Check it now/.test(afterCheck.text) && /answered|did not answer/.test(await said()), JSON.stringify(afterCheck) + " " + await said());
}
// A group of radio buttons is one Tab stop, on the one chosen; the arrow keys move to the next, as a screen reader says.
const chosen = await tabTo((f) => f.tag === "INPUT" && f.id === "ms-choice-jellyfin", 40);
check("T37", "Tab reaches the chosen media server in the group, named", !!chosen, chosen ? chosen.text : "not reached");
const none = chosen ? (await page.keyboard.press("ArrowDown"), await focus()) : null;
check("T37", "the Down arrow moves to None", !!none && none.id === "ms-choice-none", none ? none.id : "not reached");
if (none) {
  const go = await tabTo((f) => f.tag === "BUTTON" && /^Use this media server/.test(f.text), 8);
  check("T37", "Tab reaches Use this media server", !!go, go ? go.text : "not reached");
  if (go) {
    await page.keyboard.press("Enter");
    await settle();
    const box = await focus();
    check("T37", "the question opens with focus in it", box.inPanel && !box.lost, JSON.stringify(box));
    await page.keyboard.press("Enter");  // focus starts on the main button, Use none
    await settle();
    const changed = await page.evaluate(() => /No media server is in use now/.test(document.getElementById("ms-said")?.textContent || ""));
    if (changed) {
      const after = await focus();
      check("T37", "after the change focus is on what was said", after.id === "ms-said" && !after.lost, JSON.stringify(after));
      const back = await tabTo((f) => f.tag === "BUTTON" && /^Go back to Jellyfin/.test(f.text), 80);
      check("T37", "Tab reaches Go back to Jellyfin", !!back, back ? back.text : "not reached");
      if (back) {
        await page.keyboard.press("Enter");
        await settle();
        const again = await focus();
        check("T37", "after going back focus is on what was said, and Jellyfin is in use", again.id === "ms-said" && /Jellyfin is your media server again/.test(await said()), JSON.stringify(again) + " " + await said());
      }
    } else {
      // The box's default was Cancel: nothing changed, so focus is back on the button that asked.
      const after = await focus();
      check("T37", "Cancel gives focus back to the choices", !after.lost, JSON.stringify(after));
    }
  }
}

// T-PLEX (DASH-566) Add a Plex app by keyboard alone: Add an app opens the panel with focus in it, the Kind of app list is reached
// with Tab and Plex is chosen by typing its name, the token field is named for a screen reader as a Plex token and its hint says
// where to find it, and Escape closes the panel with focus back on Add an app.
await page.goto(`${base}/settings.html`);
await settle();
const addApp = await tabTo((f) => f.tag === "BUTTON" && /^Add an app/.test(f.text), 60);
check("T-PLEX", "Tab reaches Add an app", !!addApp, addApp ? addApp.text : "not reached");
if (addApp) {
  await page.keyboard.press("Enter");
  await settle();
  const inPanel = await focus();
  check("T-PLEX", "the panel opens with focus inside it", inPanel.inPanel && !inPanel.lost, JSON.stringify(inPanel));
  const kind = await tabTo((f) => f.tag === "SELECT" && f.name === "type", 12);
  check("T-PLEX", "Tab reaches Kind of app", !!kind, kind ? kind.name : "not reached");
  if (kind) {
    await page.keyboard.type("Plex");
    const got = await page.evaluate(() => ({ kind: document.querySelector("#service-form [name=type]").value, name: document.querySelector("#service-form [name=name]").value,
      label: document.querySelector("label[for=" + document.querySelector("#service-form [name=api_key]").id + "]").textContent.trim(),
      hint: document.getElementById(document.querySelector("#service-form [name=api_key]").id + "-hint")?.textContent || "" }));
    check("T-PLEX", "typing Plex chooses it, names the app and calls the key a Plex token", got.kind === "plex" && got.name === "Plex" && /^Plex token/.test(got.label), JSON.stringify(got));
    check("T-PLEX", "the token's hint says where to find it, and is tied to the field", /X-Plex-Token/.test(got.hint), got.hint);
  }
  await page.keyboard.press("Escape");
  await settle();
  const closed = await focus();
  check("T-PLEX", "Escape closes the panel and focus goes back to Add an app", /^Add an app/.test(closed.text), JSON.stringify(closed));
}

// T-WIZARD (DASH-565) The switch wizard by keyboard alone: Switch with help is reached with Tab and opens the slide-out with focus on the
// step's heading, a group of radio buttons is one Tab stop moved with the arrow keys, Next goes to step 2 and focus goes to its
// heading, Back returns, the step is said as text ("Step 1 of 3"), and Escape closes it with focus back on Switch with help.
await page.goto(`${base}/settings-jellyfin.html`);
await settle();
const sw1 = await tabTo((f) => f.tag === "BUTTON" && /^Switch with help/.test(f.text), 80);
check("T-WIZARD", "Tab reaches Switch with help", !!sw1, sw1 ? sw1.text : "not reached");
if (sw1) {
  await page.keyboard.press("Enter");
  await settle();
  const first = await focus();
  check("T-WIZARD", "the wizard opens with focus on the step's heading", first.id === "wizard-step-h" && first.inPanel, JSON.stringify(first));
  check("T-WIZARD", "the step is said in words", /Step 1 of 3/.test(await page.evaluate(() => document.getElementById("side-panel")?.innerText || "")));
  const radio = await tabTo((f) => f.tag === "INPUT" && f.name === "wizard-way", 6);
  check("T-WIZARD", "Tab reaches the way to switch, one stop for the group", !!radio, radio ? radio.id : "not reached");
  if (radio) {
    await page.keyboard.press("ArrowDown");
    const moved = await focus();
    check("T-WIZARD", "the Down arrow moves to the next way", moved.id === "wizard-way-migrate", JSON.stringify(moved));
    const nextBtn = await tabTo((f) => f.tag === "BUTTON" && f.text === "Next", 4);
    check("T-WIZARD", "Tab reaches Next", !!nextBtn);
    if (nextBtn) {
      await page.keyboard.press("Enter");
      await settle();
      const second = await focus();
      check("T-WIZARD", "Next moves focus to the new step's heading", second.id === "wizard-step-h" && /Step 2 of 3/.test(await page.evaluate(() => document.getElementById("side-panel").innerText)), JSON.stringify(second));
      const backBtn = await tabTo((f) => f.tag === "BUTTON" && f.text === "Back", 6);
      if (backBtn) {
        await page.keyboard.press("Enter");
        await settle();
        const again = await focus();
        check("T-WIZARD", "Back returns to step 1 with focus on its heading", again.id === "wizard-step-h" && /Step 1 of 3/.test(await page.evaluate(() => document.getElementById("side-panel").innerText)), JSON.stringify(again));
      } else check("T-WIZARD", "Tab reaches Back", false, "not reached");
    }
  }
  await page.keyboard.press("Escape");
  await settle();
  const out = await focus();
  check("T-WIZARD", "Escape closes the wizard and focus goes back to Switch with help", /^Switch with help/.test(out.text), JSON.stringify(out));
}

// T-WIZARD3 (DASH-587) Carrying a media server move across by keyboard alone, with made-up answers for the servers: step 3 names
// each part with a tick box that has its words, Tab reaches the ticks and the last button, Enter starts it, the progress is said
// in a polite live region, focus lands on Close when it ends, and Escape returns focus to Switch with help.
await page.goto(`${base}/settings-jellyfin.html`);
await settle();
await page.evaluate(async () => {
  const real = window.api;
  const mig = { problem: "", inside: "/data/media", libraries: [{ name: "Films", type: "movies", folders: ["/data/media/movies"], action: "add", why: "" }],
    users: [{ name: "Sam", action: "add", why: "" }], history: { can: true, says: "Read from Jellyfin and marked in Emby for each person with the same name." } };
  const done = { state: "done", said: "Done. The old media server stays added, and you can go back to it for 24 hours.", steps: [
    { part: "libraries", title: "Libraries", state: "done", said: "Added 1 library to Emby", items: [] }, { part: "switch", title: "The switch", state: "done", said: "Emby is now your media server", items: [] }] };
  window.api = async (p, o) => {
    if (p === "/api/media-server" && !o) return { ...(await real(p, o)), available: [{ id: "jellyfin", name: "Jellyfin", page: "/settings-jellyfin.html", set_up: true, has_app: true }, { id: "emby", name: "Emby", page: "/settings-jellyfin.html", set_up: true, has_app: true }], added: ["jellyfin", "emby"] };
    if (p === "/api/media-server/plan") return { ...(await real(p, o)), migration: mig, check: { ok: true, name: "Emby", said: "It answered.", libraries: ["Films"] } };
    if (p === "/api/media-server/migrate") return done;
    return real(p, o);
  };
  await startMediaServer();
});
await settle();
const sw3 = await tabTo((f) => f.tag === "BUTTON" && /^Switch with help/.test(f.text), 80);
if (sw3) {
  await page.keyboard.press("Enter");
  await settle();
  const r3 = await tabTo((f) => f.tag === "INPUT" && f.name === "wizard-way", 6);
  if (r3) await page.keyboard.press("ArrowDown");
  for (let i = 0; i < 2; i++) {
    const n = await tabTo((f) => f.tag === "BUTTON" && f.text === "Next", 6);
    if (n) { await page.keyboard.press("Enter"); await settle(); }
  }
  await page.waitForFunction(() => /^Carry across/.test([...document.querySelectorAll("#side-panel button")].map((b) => b.textContent).find((t) => /^Carry across/.test(t)) || ""), null, { timeout: 8000 }).catch(() => {});
  const labelled = await page.evaluate(() => [...document.querySelectorAll("#side-panel input[type=checkbox]")].map((i) => !!(i.labels && i.labels[0] && i.labels[0].textContent.trim())));
  check("T-WIZARD3", "every tick on step 3 has its words", labelled.length >= 2 && labelled.every(Boolean), JSON.stringify(labelled));
  const tick = await tabTo((f) => f.tag === "INPUT" && /^wizard-part-/.test(f.id), 10);
  check("T-WIZARD3", "Tab reaches a tick", !!tick, tick ? tick.id : "not reached");
  const go3 = await tabTo((f) => f.tag === "BUTTON" && /^Carry across/.test(f.text), 30);
  check("T-WIZARD3", "Tab reaches Carry across and switch", !!go3, go3 ? go3.text : "not reached");
  if (go3) {
    await page.keyboard.press("Enter");
    await page.waitForSelector("#wizard-progress .notice", { timeout: 8000 }).catch(() => {});
    await settle();
    const live3 = await page.evaluate(() => { const l = document.getElementById("wizard-progress"); return { role: l?.getAttribute("role"), live: l?.getAttribute("aria-live"), text: l?.innerText || "" }; });
    check("T-WIZARD3", "progress is said in a polite status region, in words", live3.role === "status" && live3.live === "polite" && /Finished/.test(live3.text) && /Libraries/.test(live3.text), JSON.stringify(live3));
    const end3 = await focus();
    check("T-WIZARD3", "when it ends focus is on Close", /^Close/.test(end3.text) && end3.inPanel, JSON.stringify(end3));
    await page.keyboard.press("Escape");
    await settle();
  }
} else check("T-WIZARD3", "Tab reaches Switch with help", false, "not reached");

// T23 Reduce motion (DASH-437): Off means full movement even when the device asks for less; Match device follows the
// device; On stills movement on a device that does not ask. Checked in the styles and scripts a slide-out, a message
// and the loading line use, as Display leaves them after a reload.
for (const [device, choice, still] of [["reduce", "off", false], ["reduce", "device", true], ["no-preference", "on", true], ["no-preference", "device", false]]) {
  const mctx = await browser.newContext({ viewport: { width: 1280, height: 860 }, reducedMotion: device });
  await mctx.addCookies(await page.context().cookies());
  const mp = await mctx.newPage();
  await mp.addInitScript((choice) => localStorage.setItem("starboard.display", JSON.stringify({ motion: choice })), choice);
  await mp.goto(`${base}/index.html`);
  await mp.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
  const m = await mp.evaluate(() => {
    const add = (html) => { const d = document.createElement("div"); d.innerHTML = html; document.body.append(d); return d.firstElementChild; };
    const toast = add('<div class="toast">x</div>'), bar = add('<div class="loading-bar" data-active></div>');
    return { panel: getComputedStyle(document.documentElement).getPropertyValue("--motion-panel").trim(),
      toast: getComputedStyle(toast).animationName, line: getComputedStyle(bar, "::after").display,
      script: SharedComponents.motionStill() };
  });
  const isStill = m.panel === "0ms" && m.toast === "none" && m.line === "none" && m.script === true;
  const moves = m.panel !== "0ms" && m.toast !== "none" && m.line !== "none" && m.script === false;
  check("T23", `Reduce motion ${choice} on a device set to ${device}: ${still ? "still" : "full movement"}`, still ? isStill : moves, JSON.stringify(m));
  await mctx.close();
}

// T27 Put back (plug-in API 1.15, DASH-406): in Library clean-up's Holding folder, Tab reaches Put back for a film,
// named with its title; Enter puts it back, what happened is said, and focus goes to the next row's Put back.
await page.goto(`${base}/settings-plugin.html?id=library-cleanup`);
await settle();
const heldTab = page.getByRole("tab", { name: "Holding folder" });
if (await heldTab.count()) {
  await heldTab.focus();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(300);
}
const back24 = await tabTo((f) => f.tag === "BUTTON" && /^Put back A made-up film \(2001\)$/.test(f.text), 120);
check("T27", "Tab reaches Put back for a film, named with its title", !!back24, back24 ? back24.text : "not reached");
if (back24) {
  await page.keyboard.press("Enter");
  await settle();
  const f24 = await focus(), s24 = await said();
  check("T27", "what happened is said", /Put back A made-up film/.test(s24), s24);
  check("T27", "focus goes to the next row's Put back, not the top of the page", /^Put back Harbour lights/.test(f24.text), `${f24.tag} ${f24.text}`);
}

// T28 Remove the VPN by keyboard (DASH-440): the warning is an alert dialog with focus on Cancel; Escape cancels and
// gives focus back to Remove the VPN; Hide for 90 days on Downloads is reached by Tab.
await page.goto(`${base}/settings-downloads.html`);
await settle();
const rmPw = await tabTo((f) => f.id === "dl-vpn-remove-pw", 80);
check("T28", "Tab reaches the password for Remove the VPN", !!rmPw);
await page.keyboard.type(password);
const rmBtn = await tabTo((f) => f.tag === "BUTTON" && f.text === "Remove the VPN", 5);
check("T28", "and then Remove the VPN", !!rmBtn);
await page.keyboard.press("Enter");
await page.waitForTimeout(800);
const inWarn = await focus();
const role = await page.evaluate(() => document.activeElement?.closest("dialog")?.getAttribute("role"));
check("T28", "the warning opens as an alert dialog with focus on Cancel", inWarn.inPanel && inWarn.text === "Cancel" && role === "alertdialog", `${role} ${inWarn.text}`);
await page.keyboard.press("Escape");
await page.waitForTimeout(500);
const afterWarn = await focus();
check("T28", "Escape cancels and gives focus back to Remove the VPN", afterWarn.text === "Remove the VPN" && !(await page.locator("dialog[open]").count()), afterWarn.text);

// T30 Connect a cloud service (DASH-452) by keyboard alone: a service in Add a place opens the slide-out at the sign-in
// with focus on its heading; the way to sign in by arrows; focus stays in the slide-out; Escape closes
// it part way, says nothing was saved and gives focus back to the button.
await page.goto(`${base}/settings-general-backup.html`);
await settle();
await page.evaluate(() => { const h = document.querySelector("#places-add"); h.focus(); });
const connect30 = await tabTo((f) => f.id === "place-add-drive", 10);
check("T30", "Tab reaches Google Drive in Add a place", !!connect30);
await page.keyboard.press("Enter");
await page.locator("#cloud-step-heading").waitFor({ timeout: 8000 }).catch(() => {});
const f30 = await focus();
check("T30", "the slide-out opens at the sign-in with focus on its heading", f30.id === "cloud-step-heading" && f30.inPanel, `${f30.tag} ${f30.id}`);
const go30 = true;
const way30 = await tabTo((f) => f.tag === "INPUT" && f.inPanel && f.name === "cloud-way", 6);
check("T30", "Tab reaches the two ways to sign in", !!go30 && !!way30);
await page.keyboard.press("ArrowLeft");
await page.locator(".qr-card").waitFor({ timeout: 8000 }).catch(() => {});
const f30b = await focus();
check("T30", "choosing Complete on the phone keeps focus on the choice", f30b.inPanel && f30b.name === "cloud-way", `${f30b.tag} ${f30b.name}`);
const copy30 = await tabTo((f) => /^Copy the code|^Copy/.test(f.text) && f.tag === "BUTTON", 12);
check("T30", "Tab reaches Copy for the code, inside the slide-out", !!copy30 && copy30.inPanel, copy30 ? copy30.text : "not reached");
let out30 = false;
for (let i = 0; i < 25; i++) { await page.keyboard.press("Tab"); if (!(await focus()).inPanel) { out30 = true; break; } }
check("T30", "Tab stays inside the slide-out", !out30);
await page.keyboard.press("Escape");
await page.waitForTimeout(600);
const f30c = await focus();
check("T30", "Escape closes it part way and gives focus back to the button", f30c.id === "place-add-drive" && !(await page.locator("#side-panel").count()), `${f30c.tag} ${f30c.id}`);
check("T30", "and says nothing was saved", /nothing was saved/.test(await page.locator("#announcer").innerText()));

// T31 Bring in media by keyboard alone (DASH-455): the whole step, part by part. After each Continue, focus is on the
// part's heading; the picker opens on its places with focus on the first place, opens a disk and a folder with Enter,
// and Escape gives focus back to Add a source; Check names says its counts in a status; Move up says where the row is.
await page.goto(`${base}/bring-in.html?part=bring-sources`);
await settle();
let h29 = await focus();
check("T31", "the first part opens with focus on its heading", h29.tag === "H2" && /media you already have/.test(h29.text), `${h29.tag} ${h29.text}`);
const up29 = await tabTo((f) => f.tag === "BUTTON" && /^Move .* up$/.test(f.text), 60) && await tabTo((f) => f.tag === "BUTTON" && /^Move .* up$/.test(f.text), 20);
if (up29) {
  await page.keyboard.press("Enter");
  await page.waitForTimeout(600);
  const s29 = await page.evaluate(() => document.querySelector("#sortable-status")?.textContent || "");
  check("T31", "Move up says where the source is now, and keeps focus on the button", /1 of \d/.test(s29) && /^Move .* up$/.test((await focus()).text), s29);
  await page.keyboard.press("Enter");  // and back: the order is as it was
  await page.waitForTimeout(400);
}
const add29 = await tabTo((f) => f.text === "Add a source", 60);
check("T31", "Tab reaches Add a source", !!add29);
await page.keyboard.press("Enter");
// The places are read from the server (the disks) before the first gets focus: wait for that, not a fixed time.
await page.waitForFunction(() => document.activeElement?.classList?.contains("folder-place"), null, { timeout: 8000 }).catch(() => {});
const place29 = await focus();
check("T31", "the picker opens on its places, with focus on the first one", place29.inPanel && /This computer/.test(place29.text), place29.text);
const disk29 = await tabTo((f) => /Disk 2/.test(f.text), 6);
check("T31", "Tab reaches a disk", !!disk29);
await page.keyboard.press("Enter");
await page.waitForFunction(() => document.activeElement?.getAttribute?.("role") === "listbox", null, { timeout: 8000 }).catch(() => {});
const list29 = await focus();
check("T31", "opening a disk puts focus on its list of folders", list29.role === "listbox", `${list29.tag} ${list29.role}`);
await page.keyboard.press("Enter");
await page.waitForFunction(() => /^In /.test(document.querySelector("#side-panel [aria-live]")?.textContent || ""), null, { timeout: 8000 }).catch(() => {});
const said29 = await page.evaluate(() => document.querySelector("#side-panel [aria-live]")?.textContent || "");
check("T31", "Enter opens the folder and says where you are", /^In /.test(said29), said29);
await page.keyboard.press("Backspace");
await page.waitForTimeout(1200);
await page.keyboard.press("Backspace");
await page.waitForTimeout(1200);
const back29 = await focus();
check("T31", "Backspace goes up, and from the top of the disk back to the places", back29.inPanel && /This computer/.test(back29.text), back29.text);
await page.keyboard.press("Escape");
await page.waitForTimeout(600);
check("T31", "Escape closes the picker and gives focus back to Add a source", (await focus()).text === "Add a source");
for (const [part, words] of [["bring-what", /What is in each place/], ["bring-names", /Check the new names/], ["bring-copy", /Copy your media in/]]) {
  const cont = await tabTo((f) => f.tag === "BUTTON" && f.text === "Continue", 200);
  check("T31", `Tab reaches Continue before ${part}`, !!cont);
  await page.keyboard.press("Enter");
  await settle();
  await page.waitForTimeout(1500);
  const h = await focus();
  check("T31", `${part}: focus moves to the part's heading`, h.tag === "H2" && words.test(h.text), `${h.tag} ${h.text}`);
  if (part === "bring-names") {
    const statusText = () => [...document.querySelectorAll("main [role=status]")].map((n) => n.textContent).join(" | ");
    await page.waitForFunction((f) => /\d+ matched/.test(eval(f)()), statusText.toString(), { timeout: 20000 }).catch(() => {});
    const s = await page.evaluate((f) => eval(f)(), statusText.toString());
    check("T31", "Check names says its counts in a status", /\d+ matched, \d+ need attention, \d+ left where they are/.test(s), s);
  }
}
const start29 = await page.evaluate(() => [...document.querySelectorAll(".wizard__foot .btn")].map((b) => b.textContent));
check("T31", "the last part's button says what it does", start29.includes("Start copying"), start29.join(", "));

// T33 Restart Jellyfin where it is needed (DASH-470), by keyboard alone: on System, Overview, Tab from the Jellyfin
// heading reaches Restart Jellyfin; Enter asks first with focus on Cancel; Shift+Tab and Enter restart; focus stays on
// the button while it works, progress is said in the status, and once Jellyfin answers the result has focus and says
// so. Restart needed is a page route; the restart reaches only the example server's stand-in Jellyfin.
{
  let pending = true;
  const overview = async (route) => {
    const b = await (await route.fetch()).json().catch(() => ({}));
    await route.fulfill({ contentType: "application/json", body: JSON.stringify({ ...b, configured: true, name: "Jellyfin", version: b.version || "10.11.2",
      restart: pending, can_restart: true, playing: b.playing || [], added: b.added || [] }) });
  };
  const asked = [];
  const restart = (route) => { asked.push(route.request().method()); if (route.request().method() === "POST") pending = false; return route.continue(); };
  await page.route(/\/api\/jellyfin(\?fresh=1)?$/, overview);
  await page.route(/\/api\/jellyfin\/restart$/, restart);
  await page.goto(`${base}/system.html`);
  await settle();
  await page.locator("#jellyfin-title").evaluate((h) => { h.tabIndex = -1; h.focus(); });
  const b32 = await tabTo((f) => f.tag === "BUTTON" && f.text === "Restart Jellyfin", 6);
  check("T33", "Tab from the Jellyfin heading reaches Restart Jellyfin", !!b32, b32 ? b32.text : "not reached");
  await page.keyboard.press("Enter");
  await page.waitForTimeout(300);
  const c32 = await focus();
  check("T33", "Enter asks first, with focus on Cancel", c32.inPanel && c32.text === "Cancel", `${c32.tag} ${c32.text}`);
  await page.keyboard.press("Shift+Tab");
  await page.keyboard.press("Enter");
  await page.waitForTimeout(300);
  const w32 = await focus(), sw32 = await said();
  check("T33", "while it works, focus stays on Restart Jellyfin and the progress is said", w32.text === "Restart Jellyfin" && /Jellyfin is restarting|Asking Jellyfin/.test(sw32), `${w32.text} / ${sw32}`);
  // "restarted and answers again": the words while it works also end in "answers again".
  await page.locator("#jellyfin-panel [data-restart] [role=status]", { hasText: "restarted and answers again" }).waitFor({ timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(300);
  const d32 = await focus(), sd32 = await said();
  check("T33", "when Jellyfin answers, focus is on the result and it is said", !d32.lost && /restarted and answers again/.test(d32.text) && /restarted and answers again/.test(sd32), `${d32.tag} ${d32.text} (asked: ${asked.join(" ")})`);
  await page.unroute(/\/api\/jellyfin(\?fresh=1)?$/, overview);
  await page.unroute(/\/api\/jellyfin\/restart$/, restart);
}

// T36 Bulk actions on Wanted (DASH-524): Space ticks a row, Shift and Space takes a run, the bar names the count,
// Stop following asks first, then focus goes to Select all and the result is said.
await page.goto(`${base}/wanted-films.html`);
await settle();
const picks34 = page.locator("#wanted-list .dl-pick__box");
if (await picks34.count() >= 3) {
  await page.locator("#wanted-all").focus();
  const a34 = await tabTo((f) => f.id === "select-all", 12);
  check("T36", "Tab from Find all wanted reaches Select all before the list", !!a34, a34 ? a34.text : "not reached");
  const r34 = await tabTo((f) => /^Select /.test(f.text) && f.tag === "INPUT" && f.id !== "select-all", 6);
  check("T36", "then each row's box, named for its row", !!r34, r34 ? r34.text : "not reached");
  await page.keyboard.press("Space");
  await page.waitForTimeout(200);
  check("T36", "Space ticks it and the bar says 1 film selected", /^1 film selected$/.test(await page.locator("#selection-text").textContent()));
  await picks34.nth(2).focus();
  await page.keyboard.down("Shift"); await page.keyboard.press("Space"); await page.keyboard.up("Shift");
  await page.waitForTimeout(200);
  check("T36", "Shift and Space takes the run of rows", /^3 films selected$/.test(await page.locator("#selection-text").textContent()), await page.locator("#selection-text").textContent());
  check("T36", "Select all is part ticked", await page.locator("#select-all").evaluate((b) => b.indeterminate));
  const gone34 = await picks34.evaluateAll((boxes) => boxes.slice(0, 3).map((b) => b.getAttribute("aria-label")));
  const b34 = await tabTo((f) => f.tag === "BUTTON" && f.text === "Stop following", 80);
  check("T36", "Tab reaches the bar's Stop following after the list", !!b34, b34 ? b34.text : "not reached");
  await page.keyboard.press("Enter");
  await page.waitForTimeout(300);
  const d34 = await focus();
  check("T36", "Stop following asks first, in a dialog", d34.inPanel, `${d34.tag} ${d34.text}`);
  check("T36", "the question names the count", /Stop following 3 films\?/.test(await page.locator("dialog[open] h2").textContent()));
  await page.locator("dialog[open] button[value=ok]").focus();
  await page.keyboard.press("Enter");
  await settle();
  const f34 = await focus(), s34 = await said();
  check("T36", "after it, focus is on Select all", f34.id === "select-all", `${f34.tag} ${f34.text}`);
  check("T36", "the result is said", /no longer follows 3 films/.test(s34), s34);
  const left34 = await picks34.evaluateAll((boxes) => boxes.map((b) => b.getAttribute("aria-label")));
  check("T36", "the rows have left the list and the bar has closed", !gone34.some((n) => left34.includes(n)) && await page.locator("#selection-bar").isHidden(), left34.join(", "));
  await page.locator("#select-all").focus();
  await page.keyboard.press("Space");
  await page.waitForTimeout(300);
  check("T36", "Select all ticks every row and says how many", new RegExp(`${left34.length} films selected`).test(await said()), await said());
  await page.locator("#selection-actions button", { hasText: "Clear selection" }).focus();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(300);
  const c34 = await focus();
  check("T36", "Clear selection closes the bar, says so, and gives focus to Select all", c34.id === "select-all" && /Selection cleared/.test(await said()) && await page.locator("#selection-bar").isHidden(), c34.text);
} else check("T36", "Wanted has rows with a box each", false);

// T34 Restore a full backup on this server (DASH-387) by keyboard alone: Tab from the list's heading reaches Restore
// beside the newest backup; Enter opens a danger dialog with focus on the backup's password; Tab reaches the
// Starboard password, Restore this backup, then Cancel; Escape closes it with focus back on Restore and nothing
// started. With both passwords, Enter starts it: focus is back on Restore and each step is said politely. The example
// server restores nothing (its made-up backup password is "made-up backup").
await page.goto(`${base}/settings-general-backup.html`);
await settle();
await page.locator("#full-list li[data-key]").first().waitFor({ timeout: 10000 }).catch(() => {});
await page.evaluate(() => { const h = [...document.querySelectorAll("#full-body h3")].find((x) => x.textContent === "Full backups in the folder"); h.tabIndex = -1; h.focus(); });
const r34 = await tabTo((f) => /^Restore the full backup from /.test(f.text) && f.tag === "BUTTON", 3);
check("T34", "Tab from the list's heading reaches Restore, named with the backup's date", !!r34, r34 ? r34.text : "not reached");
if (r34) {
  await page.keyboard.press("Enter");
  await page.waitForTimeout(400);
  const d34 = await focus();
  check("T34", "Enter opens the dialog with focus on the backup's password", d34.inPanel && d34.id === "restore-full-pw", `${d34.tag} ${d34.id}`);
  const order34 = [];
  for (let i = 0; i < 3; i++) { await page.keyboard.press("Tab"); const f = await focus(); order34.push(f.id || f.text); }
  check("T34", "Tab goes to the Starboard password, Restore this backup, then Cancel", order34.join(" > ") === "restore-full-mine > Restore this backup > Cancel", order34.join(" > "));
  await page.keyboard.press("Escape");
  await page.waitForTimeout(400);
  const e34 = await focus();
  check("T34", "Escape closes it with focus back on Restore, and nothing started", /^Restore the full backup from /.test(e34.text) && !e34.inPanel
    && await page.evaluate(() => api("/api/backup/full/restore-here").then((r) => r.status.state === "none")), e34.text);
  await page.keyboard.press("Enter");
  await page.waitForTimeout(400);
  await page.keyboard.type("made-up backup");
  await page.keyboard.press("Tab");
  await page.keyboard.type(password);
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => /^Restoring the full backup/.test(document.querySelector("#announcer")?.textContent || ""), null, { timeout: 5000 }).catch(() => {});
  const g34 = await focus();
  check("T34", "Enter in the last field starts it: focus is back on Restore and it is said", /^Restore the full backup from /.test(g34.text) && !g34.lost
    && /^Restoring the full backup/.test(await page.locator("#announcer").innerText()), `${g34.text} | ${await page.locator("#announcer").innerText()}`);
  await page.waitForFunction(() => /Restored the full backup/.test(document.querySelector("#full-restore-state")?.textContent || ""), null, { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(600);
  const h34 = await focus();
  check("T34", "when it ends the result is in the polite region and focus is still on the same Restore", /Restored the full backup/.test(await page.locator("#full-restore-state[aria-live=polite]").innerText())
    && /^Restore the full backup from /.test(h34.text) && !h34.lost, h34.text);
}
// T-REELIXSITES (DASH-559) The Reelix card's line about failing sites by keyboard alone: the link is in the Tab order inside
// the card, has a name that says what it does, and Enter goes to Sites to search.
await page.goto(`${base}/index.html`);
await settle();
await page.waitForFunction(() => document.querySelector(".card__activity a[href*=rx-indexers]"), null, { timeout: 10000 }).catch(() => {});
const sitesLink = await tabTo((f) => f.tag === "A" && /sites? failing/.test(f.text), 160);
check("T-REELIXSITES", "the line about failing sites can be reached with Tab", !!sitesLink, "");
if (sitesLink) {
  check("T-REELIXSITES", "it says how many and what it is about", /^\d+ (of \d+ )?sites? failing$|^All /.test(sitesLink.text), sitesLink.text);
  await page.keyboard.press("Enter");
  await page.waitForURL(/settings-reelix\.html/, { timeout: 8000 }).catch(() => {});
  check("T-REELIXSITES", "Enter opens Settings, Reelix", /settings-reelix\.html#rx-indexers/.test(page.url()), page.url());
}

// T35 Reelix's backup settings (DASH-385, DASH-386) by keyboard alone: the selects change with the arrow keys and
// save at once, focus stays on the select and the saved note says so; choosing the media folder says Reelix must
// restart, with focus still on the select.
await page.goto(`${base}/settings-general-backup.html`);
await settle();
const show35 = page.getByRole("button", { name: "Show Reelix's backups" });
if (await show35.count()) {
  await show35.focus();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(500);
  if (await page.locator("#rs-password").count()) { await page.keyboard.type("made-up"); await page.keyboard.press("Enter"); }
  await page.locator("#rs-every").waitFor({ timeout: 10000 }).catch(() => {});
  await page.waitForTimeout(300);
  const a35 = await focus();
  check("T35", "after the password, focus is not lost", !a35.lost, a35.text);
  await page.locator("#rs-backup-now").focus();
  const s35 = await tabTo((f) => f.id === "rs-every", 3);
  check("T35", "Tab from Make a backup now reaches the first select", !!s35);
  await page.keyboard.press("ArrowDown");
  await page.waitForFunction(() => { const n = document.querySelector("#rs-every")?.parentElement.querySelector(".saved-note"); return n && !n.hidden; }, null, { timeout: 5000 }).catch(() => {});
  const b35 = await focus();
  check("T35", "an arrow key changes it, it saves at once, focus stays and Saved is said", b35.id === "rs-every"
    && /^Saved at \d\d:\d\d$/.test(await page.locator("#rs-every + .saved-note[role=status]").innerText().catch(() => "")), `${b35.id} | ${await page.locator("#rs-every + .saved-note").innerText().catch(() => "no note")}`);
  await page.keyboard.press("ArrowUp");
  await page.waitForTimeout(600);
  const p35 = await tabTo((f) => f.id === "rs-place", 3);
  check("T35", "Tab reaches Where Reelix keeps them", !!p35);
  await page.keyboard.press("ArrowDown");
  await page.locator("[data-restart-notice]").waitFor({ timeout: 10000 }).catch(() => {});
  await page.waitForTimeout(300);
  const c35 = await focus();
  check("T35", "choosing the media folder keeps focus on the select, and what happens next is said", c35.id === "rs-place"
    && /media folder from its next start/.test(await page.locator("#announcer").innerText()) && await page.locator("[data-restart-notice]").count() === 1, `${c35.id} | ${await page.locator("#announcer").innerText()}`);
  await page.keyboard.press("ArrowUp");
  await page.waitForTimeout(800);
  check("T35", "choosing next to its settings again takes the restart notice away", await page.locator("[data-restart-notice]").count() === 0 && (await focus()).id === "rs-place");
} else check("T35", "the example server has Reelix's backups", false);

// T36 History, Across apps (DASH-68): the filter by arrow keys says the new count; Delete history asks first with focus
// on Cancel, and afterwards focus is back on Delete history with the result said. Last, as it empties the list.
{
  await page.goto(`${base}/history-apps.html`);
  await settle();
  await page.locator("#across-list .chip").first().waitFor({ timeout: 10000 }).catch(() => {});
  await page.locator("main h1").evaluate((h) => { h.tabIndex = -1; h.focus(); });
  const f34 = await tabTo((f) => f.name === "across-show", 4);
  check("T36", "Tab from the heading reaches the Show filter, on Everything", !!f34 && f34.id === "across-show-all", f34 ? f34.id : "not reached");
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await page.waitForTimeout(1200);
  const g34 = await focus(), s34 = await said();
  const kinds = await page.locator("#across-list .chip").allTextContents();
  check("T36", "the arrow keys choose Failed, focus stays on it, the list holds only Failed and the count is said",
    g34.id === "across-show-failed" && kinds.length > 0 && kinds.every((k) => k.trim() === "Failed") && /entr(y|ies), newest first/.test(s34), `${g34.id} / ${kinds.length} / ${s34}`);
  const d34 = await tabTo((f) => f.tag === "BUTTON" && f.text === "Delete history" && f.inMain, 60);
  check("T36", "Tab reaches Delete history at the end of the page", !!d34, d34 ? d34.text : "not reached");
  await page.keyboard.press("Enter");
  await page.waitForTimeout(400);
  const c34 = await focus();
  check("T36", "Enter asks first, with focus on Cancel", c34.inPanel && c34.text === "Cancel", `${c34.tag} ${c34.text}`);
  await page.keyboard.press("Shift+Tab");
  await page.keyboard.press("Enter");
  await page.waitForTimeout(1500);
  const e34 = await focus(), t34 = await said();
  check("T36", "after deleting, focus is back on Delete history and the result is said", e34.text === "Delete history" && e34.inMain && /History across apps deleted/.test(t34), `${e34.text} / ${t34}`);
}

// T-WHY (DASH-557) Why is this here? by keyboard alone: the button is reached with Tab, Enter opens the panel with focus on
// its Close button, the panel names what the last search found and did not find, and Escape gives focus back to the button.
await page.goto(`${base}/apps-services.html`);
await settle();
const whyBtn = await tabTo((f) => f.id === "why-here", 60);
check("T-WHY", "Why is this here? can be reached with Tab", !!whyBtn);
if (whyBtn) {
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => document.querySelector("#side-panel .rows"), null, { timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(500);
  const inside = await focus();
  check("T-WHY", "the panel opens with focus inside it", inside.inPanel, inside.text);
  check("T-WHY", "it lists what was found and what was not, with a heading for each", await page.evaluate(() => {
    const h = [...document.querySelectorAll("#side-panel h3")].map((x) => x.textContent);
    return h.some((x) => x.startsWith("Found")) && h.some((x) => x.startsWith("Not found")) && document.querySelector("#side-panel h2")?.textContent === "Why is this here?";
  }));
  check("T-WHY", "each app says what found it and what it matched on", await page.evaluate(() => /Found by: .+/.test(document.querySelector("#side-panel").textContent) && /Matched on: .+/.test(document.querySelector("#side-panel").textContent)));
  await page.keyboard.press("Escape");
  await page.waitForTimeout(500);
  const out = await focus();
  check("T-WHY", "Escape gives focus back to Why is this here?", out.id === "why-here", out.id || out.text);
}

// T-JSON (DASH-555) A custom card by keyboard alone: its row is reached with Tab, Enter opens the panel with focus inside it,
// Ask the address lists the fields (said in a polite status), Space ticks a field and focus stays on it while the "On the card"
// count changes, Remove on a chosen field says so and keeps focus in the panel, and Escape gives focus back to the card's row.
await page.goto(`${base}/apps-services.html`);
await settle();
const jsonRow = await tabTo((f) => f.text === "Download client" && f.tag === "BUTTON", 80);
check("T-JSON", "a custom card's name can be reached with Tab", !!jsonRow);
if (jsonRow) {
  await page.keyboard.press("Enter");
  await page.waitForSelector("#side-panel #jc-ask", { timeout: 8000 }).catch(() => {});
  const inside = await focus();
  check("T-JSON", "the panel opens with focus inside it", inside.inPanel, inside.text);
  await page.focus("#jc-ask");
  await page.keyboard.press("Enter");
  await page.waitForSelector("#jc-filter", { timeout: 8000 }).catch(() => {});
  check("T-JSON", "the fields it answers with are said in a polite status", /Choose the fields to show/.test(await page.locator("#jc-status").textContent()) && (await page.locator("#jc-status").getAttribute("role")) === "status");
  check("T-JSON", "the count of fields is in a status region", /\d+ of \d+ fields/.test(await page.locator("#jc-count[role=status]").textContent()));
  const before = await page.locator("#jc-chosen-h").textContent();
  const box = page.locator("#jc-pick-5");
  await box.focus();
  await page.keyboard.press("Space");
  await page.waitForTimeout(300);
  const after = await page.locator("#jc-chosen-h").textContent();
  check("T-JSON", "Space ticks a field and the On the card count changes", before !== after, `${before} -> ${after}`);
  const kept = await focus();
  check("T-JSON", "focus stays on the ticked field", kept.id === "jc-pick-5", kept.id || kept.text);
  await page.focus("#jc-f0-remove");
  await page.keyboard.press("Enter");
  await page.waitForTimeout(300);
  const afterRemove = await focus();
  check("T-JSON", "removing a chosen field keeps focus inside the panel", afterRemove.inPanel, afterRemove.id || afterRemove.text);
  await page.keyboard.press("Escape");
  await page.waitForTimeout(500);
  const out = await focus();
  check("T-JSON", "Escape gives focus back to the card's name", out.tag === "BUTTON" && out.text === "Download client", out.id || out.text);
}

// T-SIGNIN (DASH-512) Set up a two-step code by keyboard alone: the dialog asks for the password first, the slide-out
// starts in the code field, the recovery codes end on I have saved them, and focus is never lost to the top.
await page.goto(`${base}/settings-security-signin.html`);
await settle();
const setUp = await tabTo((f) => f.tag === "BUTTON" && /Set up a two-step code/.test(f.text), 80);
check("T-SIGNIN", "Set up a two-step code can be reached with Tab", !!setUp);
if (setUp) {
  await page.keyboard.press("Enter");
  await page.waitForTimeout(500);
  const d1 = await focus();
  check("T-SIGNIN", "the password dialog starts in the password field", d1.id === "signin-password", d1.id || d1.text);
  await page.keyboard.type(password);
  await page.keyboard.press("Enter");
  await page.locator("#totp-form").waitFor({ timeout: 8000 });
  await page.waitForTimeout(400);
  const d2 = await focus();
  check("T-SIGNIN", "the QR code slide-out starts in the code field", d2.id === "totp-code" && d2.inPanel, d2.id || d2.text);
  await page.keyboard.type("123456");
  await page.keyboard.press("Enter");
  await page.locator(".recovery-codes").waitFor({ timeout: 8000 });
  await page.waitForTimeout(400);
  const d3 = await focus();
  check("T-SIGNIN", "the recovery codes end on I have saved them", /I have saved them/.test(d3.text) && d3.inPanel, d3.text);
  await page.keyboard.press("Enter");
  await page.waitForTimeout(700);
  const d4 = await focus(), s4 = await said();
  check("T-SIGNIN", "after it closes focus is not lost to the top of the page", !d4.lost, d4.text);
  check("T-SIGNIN", "the result is said", /Two-step code activated|recovery codes left/i.test(s4), s4);
  // Put back: the dialog, then the password, by keyboard.
  const off = await tabTo((f) => f.tag === "BUTTON" && /Deactivate the two-step code/.test(f.text), 80);
  check("T-SIGNIN", "Deactivate the two-step code can be reached with Tab", !!off);
  if (off) {
    await page.keyboard.press("Enter");
    await page.waitForTimeout(500);
    const d5 = await focus();
    check("T-SIGNIN", "its dialog starts in the password field", d5.id === "signin-password", d5.id || d5.text);
    await page.keyboard.type(password);
    await page.keyboard.press("Enter");
    await page.waitForTimeout(1000);
    const d6 = await focus();
    check("T-SIGNIN", "after deactivating, focus is not lost to the top of the page", !d6.lost, d6.text);
  }
}

// T-BUSY (DASH-558) Busy now by keyboard alone: the page reads once when it opens and says so, Check now is reached with
// Tab and pressed with Enter, focus comes back to it, the result is said in a live region, and each table has a caption
// and row headings.
await page.goto(`${base}/system-busy.html`);
await settle();
await page.waitForFunction(() => /Read at/.test(document.querySelector("#busy-summary")?.textContent || ""), null, { timeout: 10000 }).catch(() => {});
check("T-BUSY", "the page reads once when it opens and says when", /Read at \d\d:\d\d:\d\d/.test(await page.locator("#busy-summary").innerText()));
check("T-BUSY", "each table has a caption and row headings", await page.evaluate(() => [...document.querySelectorAll("#busy-containers table, #busy-processes table")].every((t) => t.querySelector("caption")?.textContent.trim() && t.querySelector("tbody th[scope=row]"))));
const again = await tabTo((f) => f.id === "busy-again", 60);
check("T-BUSY", "Check now can be reached with Tab", !!again);
if (again) {
  await page.keyboard.press("Enter");
  await page.waitForTimeout(300);
  check("T-BUSY", "while it reads, the button says it is busy", await page.evaluate(() => document.getElementById("busy-again").hasAttribute("aria-busy") || document.getElementById("busy-summary").hasAttribute("aria-busy")));
  await page.waitForFunction(() => !document.getElementById("busy-again").disabled, null, { timeout: 10000 }).catch(() => {});
  await page.waitForTimeout(500);
  const f = await focus(), s = await said();
  check("T-BUSY", "focus comes back to Check now", f.id === "busy-again", f.id || f.text);
  check("T-BUSY", "the result is said in a live region", /Read at \d\d:\d\d:\d\d/.test(s), s);
}

// T-PEOPLE (DASH-589) People by keyboard alone: Manage opens a slide-out that takes focus and gives it back on Escape, Add a person
// starts in the Name field, a missing name is said and the field keeps focus, and after adding, focus is on the new person's Manage
// button, not the top of the page. Each table has a caption and row headings.
await page.goto(`${base}/settings-people.html`);
await settle();
check("T-PEOPLE", "the table has a caption and row headings", await page.evaluate(() => [...document.querySelectorAll("#people-sections table")].every((t) => t.querySelector("caption")?.textContent.trim() && t.querySelector("tbody th[scope=row]"))));
const manage = await tabTo((f) => f.tag === "BUTTON" && /^Manage /.test(f.text), 80);
check("T-PEOPLE", "Manage can be reached with Tab", !!manage);
if (manage) {
  await page.keyboard.press("Enter");
  await page.waitForTimeout(600);
  const m1 = await focus();
  check("T-PEOPLE", "the slide-out takes focus", m1.inPanel, m1.text);
  await page.keyboard.press("Escape");
  await page.waitForTimeout(600);
  const m2 = await focus();
  check("T-PEOPLE", "Escape gives focus back to the Manage button that opened it", m2.text === manage.text, m2.text);
}
await page.goto(`${base}/settings-people.html`);
await settle();
const addPerson = await tabTo((f) => f.tag === "BUTTON" && /Add a person/.test(f.text), 60);
check("T-PEOPLE", "Add a person can be reached with Tab", !!addPerson);
if (addPerson) {
  await page.keyboard.press("Enter");
  await page.waitForTimeout(600);
  const a1 = await focus();
  check("T-PEOPLE", "the form starts in the Name field", a1.id === "person-name", a1.id || a1.text);
  await page.keyboard.press("Enter");
  await page.waitForTimeout(500);
  const a2 = await focus(), s2 = await said();
  check("T-PEOPLE", "a missing name is said, and focus stays in the form", a2.inPanel && /Enter a name/.test(await page.locator("#side-panel").innerText()), `${a2.text} ${s2}`);
  await page.keyboard.type("Keyboard Kim");
  await page.keyboard.press("Enter");
  await page.waitForTimeout(900);
  const a3 = await focus(), s3 = await said();
  check("T-PEOPLE", "after adding, focus is not lost to the top of the page", !a3.lost && /Manage Keyboard Kim/.test(a3.text), a3.text);
  check("T-PEOPLE", "the result is said", /Added Keyboard Kim/.test(s3), s3);
}

// T-PEOPLE-PW (DASH-589) Make a password by keyboard alone: the dialog starts in the account name, Generate one is the choice
// and the own-password box is hidden, an arrow key chooses Use my own and shows the box while focus stays on the choice, and
// Escape gives focus back to the button that opened the dialog.
await page.goto(`${base}/settings-people.html`);
await settle();
await page.locator('[data-person]', { hasText: "Alex" }).first().focus();
await page.keyboard.press("Enter");
await page.waitForTimeout(700);
const mk = await tabTo((f) => f.tag === "BUTTON" && /^Make a password for Alex in Audiobookshelf/.test(f.text), 40);
check("T-PEOPLE-PW", "Make a password can be reached with Tab", !!mk, mk?.text);
if (mk) {
  await page.keyboard.press("Enter");
  await page.waitForTimeout(600);
  const d1 = await focus();
  check("T-PEOPLE-PW", "the dialog starts in the account name", d1.inPanel && /-user$/.test(d1.id), d1.id || d1.text);
  check("T-PEOPLE-PW", "Generate one is chosen and the own password box is hidden", await page.evaluate(() => document.querySelector("#acct-audiobookshelf-mode-generate")?.checked && document.querySelector("#acct-audiobookshelf-own")?.closest(".field").hidden));
  await page.keyboard.press("Tab");
  await page.keyboard.press("ArrowDown");
  await page.waitForTimeout(300);
  const d2 = await focus();
  check("T-PEOPLE-PW", "an arrow key chooses Use my own, shows its box, and focus stays on the choice", d2.id === "acct-audiobookshelf-mode-own" && await page.evaluate(() => !document.querySelector("#acct-audiobookshelf-own").closest(".field").hidden), d2.id || d2.text);
  await page.keyboard.press("Escape");
  await page.waitForTimeout(500);
  const d3 = await focus();
  check("T-PEOPLE-PW", "Escape gives focus back to Make a password", /^Make a password for Alex/.test(d3.text), d3.text);
}

// T-TRANSCODE (DASH-515) Test hardware video conversion by keyboard alone: Test now is reached with Tab, nothing runs
// until it is pressed, the wait is said, and focus ends on the result's summary, which is read out.
await page.goto(`${base}/system.html`);
await settle();
const before = await page.evaluate(async () => (await api("/api/system/transcode-check")).result);
check("T-TRANSCODE", "nothing has run before Test now is pressed", before === null);
const testNow = await tabTo((f) => f.tag === "BUTTON" && /Test now/.test(f.text), 120);
check("T-TRANSCODE", "Test now can be reached with Tab", !!testNow);
if (testNow) {
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => /Hardware conversion works|Only software|No encoder worked/.test(document.getElementById("transcode-status")?.textContent || ""), null, { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(500);
  const f = await focus(), s = await said();
  check("T-TRANSCODE", "focus moves to the result's summary, not lost to the top", f.id === "transcode-status", f.id || f.text);
  check("T-TRANSCODE", "the result is said in a live region", /Hardware conversion works|Only software|No encoder worked/.test(s), s);
  check("T-TRANSCODE", "the button now says Test again, and each way of converting has a row", (await page.locator("#transcode-go").innerText()).includes("Test again") && (await page.locator("#transcode li").count()) === 4);
}

// T-STALLBOARD (DASH-563) Add the Stallboard catalogue by keyboard alone: the Catalogue sources tab opens with Enter, the
// tick is reached with Tab and pressed with Space, its note is its description, "Stallboard catalogue added" is said, a Stallboard
// tab appears, the page stays on Catalogue sources, focus stays on the tick, and Space again turns it off.
await page.goto(`${base}/settings-plugins-catalogue.html`);
await page.evaluate(() => api("/api/plugins/catalogues", { method: "POST", body: { action: "builtin", id: "stallboard", on: false } }));
await page.goto(`${base}/settings-plugins-catalogue.html`);
await settle();
const srcTab = page.getByRole("tab", { name: "Catalogue sources" });
await srcTab.focus();
await page.keyboard.press("Enter");
await page.waitForTimeout(500);
const tick = await tabTo((f) => f.id === "pl-builtin-stallboard", 30);
check("T-STALLBOARD", "the Stallboard tick can be reached with Tab", !!tick);
if (tick) {
  check("T-STALLBOARD", "the tick has its note as its description", await page.evaluate(() => { const i = document.getElementById("pl-builtin-stallboard"); return /Reviewed mark/.test(document.getElementById(i.getAttribute("aria-describedby")).textContent) && !i.checked; }));
  await page.keyboard.press("Space");
  await page.waitForTimeout(2000);
  const f = await focus(), s = await said();
  check("T-STALLBOARD", "focus stays on the tick after the page is drawn again", f.id === "pl-builtin-stallboard", f.id || f.text);
  check("T-STALLBOARD", "Stallboard catalogue added is said in a live region", /Stallboard catalogue added/.test(s), s);
  check("T-STALLBOARD", "the page stays on Catalogue sources and a Stallboard tab has appeared", await page.evaluate(() => document.querySelector("#topic-tabs [aria-selected=true]")?.textContent.trim() === "Catalogue sources"
    && [...document.querySelectorAll("#topic-tabs [role=tab]")].some((t) => t.textContent.trim() === "Stallboard")));
  await page.keyboard.press("Space");
  await page.waitForTimeout(2000);
  const f2 = await focus(), s2 = await said();
  check("T-STALLBOARD", "Space again clears it, with focus on the tick", f2.id === "pl-builtin-stallboard" && /Stallboard catalogue removed/.test(s2), `${f2.id} ${s2}`);
}

// T-SHADOWS (DASH-536) Remove drop shadows by keyboard alone: Display opens with Enter, the switch is reached with Tab and
// pressed with Space, the note is its description, the saved note is said, focus stays on the switch, and Escape returns
// focus to Display.
await page.goto(`${base}/index.html`);
await page.evaluate(() => api("/api/config/general", { method: "PUT", body: { shadows_off: false } }));  // the made-up install is Lite, which starts with them removed
await page.goto(`${base}/index.html`);
await settle();
const dispBtn = await tabTo((f) => /Display/.test(f.text) && f.tag === "BUTTON", 160);
check("T-SHADOWS", "Display can be reached with Tab", !!dispBtn);
if (dispBtn) {
  await page.keyboard.press("Enter");
  await page.waitForTimeout(700);
  const sw = await tabTo((f) => f.name === "shadows", 30);
  check("T-SHADOWS", "Remove drop shadows can be reached with Tab inside the panel", !!sw && sw.inPanel);
  check("T-SHADOWS", "it is a switch with the note as its description", await page.evaluate(() => { const i = document.querySelector("#side-panel input[name=shadows]"); return i.getAttribute("role") === "switch" && /turning them off helps small and older computers/.test(document.getElementById(i.getAttribute("aria-describedby")).textContent); }));
  await page.keyboard.press("Space");
  await page.waitForTimeout(900);
  const f2 = await focus(), s2 = await page.locator("#dp-shadows-saved").innerText().catch(() => "");
  check("T-SHADOWS", "pressing Space applies it at once", await page.evaluate(() => document.documentElement.dataset.shadows) === "off");
  check("T-SHADOWS", "focus stays on the switch", f2.name === "shadows", f2.text);
  check("T-SHADOWS", "the saved note is said beside it", /Saved/.test(s2), s2);
  await page.keyboard.press("Space");
  await page.waitForTimeout(700);
  check("T-SHADOWS", "Space again puts the shadows back", !(await page.evaluate(() => document.documentElement.dataset.shadows)));
  await page.keyboard.press("Escape");
  await page.waitForTimeout(500);
  const f3 = await focus();
  check("T-SHADOWS", "Escape returns focus to Display", /Display/.test(f3.text), f3.text);
}

// T-PLEX Sign in with Plex (DASH-595): reachable by Tab beside the token field; Enter shows the code in a polite live region
// and puts focus on Cancel; Cancel puts focus back on the button and says so; the approval is said and focus goes to Save.
await page.goto(`${base}/settings.html`);
await settle();
await page.click("#add-service");
await page.locator("#service-form select[name=type]").selectOption("plex");
await page.waitForTimeout(300);
const signIn = page.getByRole("button", { name: "Sign in with Plex" });
await signIn.focus();
await page.keyboard.press("Enter");
await page.locator(".plex-code").waitFor({ timeout: 5000 });
const f2a = await focus();
check("T-PLEX", "Enter shows the code and focus is on Cancel", f2a.tag === "BUTTON" && /^Cancel/.test(f2a.text), `${f2a.tag} ${f2a.text}`);
check("T-PLEX", "the code is in a polite live region with a link to plex.tv/link", await page.locator(".plex-link [aria-live=polite] .plex-code").count() === 1
  && await page.locator(".plex-link [aria-live=polite] a[href='https://plex.tv/link']").count() === 1);
await page.keyboard.press("Enter");
await page.waitForTimeout(300);
const f2b = await focus();
check("T-PLEX", "Cancel puts focus back on Sign in with Plex and says so", /Sign in with Plex/.test(f2b.text) && /Sign-in cancelled/.test(await page.locator(".plex-link [aria-live=polite]").innerText()), f2b.text);
await page.keyboard.press("Enter");
await page.locator(".plex-link", { hasText: "Signed in with Plex" }).waitFor({ timeout: 15000 }).catch(() => {});
const f2c = await focus();
check("T-PLEX", "when it is approved, it is said and focus goes to the save button", /Signed in with Plex/.test(await page.locator(".plex-link [aria-live=polite]").innerText()) && /Add app|Save app|Save and continue/.test(f2c.text), f2c.text);
await page.keyboard.press("Escape");

// T-GEN1 Settings, General, Backup/Logs (DASH-595): one page of sections with a row of in-page links. Tab walks the links in
// reading order, Enter on one moves to its section with focus on the section's heading, and every link has a section.
await page.goto(`${base}/settings-general-backup.html`);
await settle();
const linkNames = await page.locator(".page-links a").allTextContents();
check("T-GEN1", "the in-page links are a list under a named navigation", await page.locator("nav.page-links[aria-label='On this page'] ul li a").count() === linkNames.length && linkNames.length >= 8);
await page.evaluate(() => { document.querySelector("main h1").tabIndex = -1; document.querySelector("main h1").focus(); });
const firstLink = await tabTo((f) => f.tag === "A" && /^When backups are made/.test(f.text), 4);
check("T-GEN1", "Tab from the heading reaches the first link, then the rest in order", !!firstLink);
const seen = [];
for (let i = 1; i < linkNames.length; i++) { await page.keyboard.press("Tab"); seen.push((await focus()).text); }
check("T-GEN1", "the links come in the order the sections do", JSON.stringify(seen) === JSON.stringify(linkNames.slice(1)), seen.join("|"));
await page.locator(".page-links a", { hasText: "Where backups go" }).focus();
await page.keyboard.press("Enter");
await page.waitForTimeout(300);
check("T-GEN1", "Enter moves to the section", (await page.evaluate(() => location.hash)) === "#bk-copies-h" && await page.locator("#bk-copies-h").isVisible());
check("T-GEN1", "the page has one h1 and every section a heading", await page.locator("main h1").count() === 1 && await page.locator("main h2").count() >= 8);
await page.goto(`${base}/system-backup.html`);
await settle();
check("T-GEN1", "the old address opens it", new URL(page.url()).pathname === "/settings-general-backup.html");

// T-ROW1 A row of tabs under the header at phone width (owner, 26 November 2026), by keyboard alone: Tab reaches a tab, the arrow keys, Home and
// End move along the row, the tab with focus shows its name, focus is never lost and stays in view, Enter opens the page, and a
// change of text size keeps focus on the same link.
await page.setViewportSize({ width: 375, height: 812 });
await page.goto(`${base}/settings-general-hours.html`);
await settle();
const rowNav = page.locator('.site-header__tabs nav[aria-label="General"]');
const rowFocus = () => page.evaluate(() => { const a = document.activeElement, n = a.closest("nav"); const r = a.getBoundingClientRect(), b = n ? n.getBoundingClientRect() : r;
  return { text: a.textContent.trim(), inNav: !!n, named: !!a.querySelector(".menu-tabs__label") && a.querySelector(".menu-tabs__label").getBoundingClientRect().width > 2, inView: r.left >= b.left - 1 && r.right <= b.right + 1 }; });
const rowReached = await tabTo((f) => f.tag === "A" && /^General$/.test(f.text), 40);
check("T-ROW1", "Tab reaches the first tab of the row", !!rowReached);
let f = await rowFocus();
check("T-ROW1", "the tab with focus shows its name", f.named && f.inNav, JSON.stringify(f));
await page.keyboard.press("ArrowRight");
f = await rowFocus();
check("T-ROW1", "the right arrow moves to the next tab, in view, with its name", f.text === "Appearance" && f.named && f.inView, JSON.stringify(f));
await page.keyboard.press("End");
await page.waitForTimeout(300);
f = await rowFocus();
check("T-ROW1", "End goes to the last tab, in view", f.text === "Backup/Logs" && f.inView, JSON.stringify(f));
await page.keyboard.press("Home");
check("T-ROW1", "Home goes to the first tab", (await rowFocus()).text === "General");
await page.evaluate(() => document.documentElement.classList.add("pref-text-175"));
await page.waitForTimeout(500);
f = await rowFocus();
check("T-ROW1", "a larger text size keeps focus on the same link, in view", f.text === "General" && f.inView, JSON.stringify(f));
await page.evaluate(() => document.documentElement.classList.remove("pref-text-175"));
await page.keyboard.press("ArrowRight");
await page.keyboard.press("Enter");
await page.waitForLoadState("domcontentloaded");
await settle();
check("T-ROW1", "Enter opens the page, and its row shows that tab as current", new URL(page.url()).pathname === "/settings-general-appearance.html" && await rowNav.locator("a[aria-current=page]").textContent() === "Appearance");
await page.setViewportSize({ width: 1280, height: 860 });

// T-PLU Plug-in updates by keyboard (owner, 26 November 2026): Tab reaches Check now; Enter reads the
// catalogues, says what it found in a polite live region and focus stays on the button; Tab then reaches a tick, Space
// ticks it and the count is said; Update all asks for the password with focus in the field, and Escape gives focus back.
await page.goto(`${base}/settings-updates-plugins.html`);
await settle();
const chk = await tabTo((f) => f.id === "plu-check", 80);
check("T-PLU", "Tab reaches Check now", !!chk, "not reached");
if (chk) {
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => /Read \d+ catalogue|Try again in/.test(document.getElementById("plu-check-result")?.textContent || ""), null, { timeout: 15000 }).catch(() => {});
  const after = await focus();
  check("T-PLU", "after the check, focus is still on the button", after.id === "plu-check", `${after.id} ${after.text}`);
  await page.waitForFunction(() => /Read \d+ catalogue|Try again in/.test([...document.querySelectorAll("[role=status], [aria-live=polite]")].map((n) => n.textContent).join(" | ")), null, { timeout: 4000 }).catch(() => {});
  const said = await page.evaluate(() => [...document.querySelectorAll("[role=status], [aria-live=polite]")].map((n) => n.textContent).join(" | "));
  check("T-PLU", "what it found is said in a polite live region", /Read \d+ catalogue|Try again in/.test(said), said);
  const tick = await tabTo((f) => /^choose-plugin:/.test(f.id), 30);
  check("T-PLU", "Tab reaches a plug-in's tick", !!tick, "not reached");
  if (tick) {
    await page.keyboard.press("Space");
    await page.waitForTimeout(300);
    check("T-PLU", "Space ticks it and the count is said", /1 chosen/.test(await page.locator("#plu-chosen-text").textContent()) && (await page.locator("#plu-chosen-text").getAttribute("aria-live")) === "polite");
  }
  await page.locator("#plu-update-all").focus();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(600);
  const pwP = await focus();
  check("T-PLU", "Update all asks for the password with focus in the field", pwP.inPanel && pwP.tag === "INPUT", `${pwP.tag} ${pwP.text}`);
  await page.keyboard.press("Escape");
  await page.waitForTimeout(400);
  const backP = await focus();
  check("T-PLU", "Escape closes it and focus returns to Update all", backP.id === "plu-update-all", `${backP.id} ${backP.text}`);
}

// T-SYSBACKUP System, Backups (DASH-588): the panel is reached in the Tab order and its one link, named for what it does,
// opens the backup page at Full without media with Enter.
await page.goto(`${base}/system.html`);
await settle();
await page.locator("#backups-panel:not([hidden])").waitFor({ timeout: 10000 }).catch(() => {});
if (await page.locator("#backups-panel:not([hidden])").count()) {
  check("T-SYSBACKUP", "the panel has a heading and says whether the newest full backup was read back", /Backups/.test(await page.locator("#backups-title").innerText()) && /full backup|Full backups/i.test(await page.locator("#backups-sum").innerText()));
  const lk = await tabTo((f) => f.tag === "A" && /Check and restore backups/.test(f.text), 120);
  check("T-SYSBACKUP", "Tab reaches Check and restore backups", !!lk, lk ? lk.text : "not reached");
  if (lk) {
    await page.keyboard.press("Enter");
    await page.waitForURL(/settings-general-backup\.html/, { timeout: 8000 }).catch(() => {});
    check("T-SYSBACKUP", "Enter opens Backup/Logs at Full without media", /settings-general-backup\.html#bk-full-h/.test(page.url()), page.url());
  }
} else check("T-SYSBACKUP", "the example server shows the Backups panel", false, "hidden");
// T-PLACERULE How often a place gets a copy (DASH-588) by keyboard alone: Tab from a place's switch reaches its Copy select,
// named for the place; the arrow key changes it, which applies at once and is said politely; the choice survives a reload.
await page.goto(`${base}/settings-general-backup.html`);
await settle();
await page.locator("#place-on-main").waitFor({ timeout: 10000 }).catch(() => {});
await page.locator("#place-on-main").focus();
const sel16 = await tabTo((f) => f.tag === "SELECT" && f.id === "place-every-main", 4);
check("T-PLACERULE", "Tab reaches the Copy select, named for its place", !!sel16 && /How often .* gets a copy/.test(sel16.text), sel16 ? sel16.text : "not reached");
if (sel16) {
  await page.keyboard.press("ArrowDown");
  await page.waitForTimeout(600);
  check("T-PLACERULE", "the arrow key changes it and the change is said", (await page.locator("#place-every-main").inputValue()) === "weekly" && /Saved: .* at most once a week/.test(await page.locator("#announcer").innerText()), await page.locator("#announcer").innerText());
  await page.reload(); await settle();
  await page.locator("#place-every-main").waitFor({ timeout: 10000 }).catch(() => {});
  check("T-PLACERULE", "the choice is still there after a reload", (await page.locator("#place-every-main").inputValue()) === "weekly");
}
// T-KEYSETUP First-run set-up of full backups (DASH-588) by keyboard alone: Set up full backups (or Keep the backup password)
// is reached with Tab and opens the dialog; Suggest a password by Enter fills both fields and is said politely; Keep it
// stays waiting until the box that says it was stored is ticked; Escape closes with focus back on the opener.
await page.goto(`${base}/settings-general-backup.html`);
await settle();
await page.locator("#schedule-body").waitFor({ timeout: 10000 }).catch(() => {});
if (await page.locator("#keep-key").count()) {
  await page.locator("#keep-key").focus();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(500);
  const k1 = await focus();
  check("T-KEYSETUP", "Enter opens the dialog and focus moves into it", k1.inPanel, `${k1.tag} ${k1.id}`);
  await page.locator("#key-suggest").focus();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(300);
  check("T-KEYSETUP", "Suggest a password fills both fields, shows it once and says so", (await page.locator("#key-pw-1").inputValue()) === (await page.locator("#key-pw-2").inputValue())
    && (await page.locator("#key-pw-1").inputValue()).length === 27 && /suggested/.test(await page.locator("#announcer").innerText()));
  await page.locator("#key-mine").fill("made-up password");
  await page.locator("#key-form button[type=submit], button[form=key-form]").first().focus();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(300);
  check("T-KEYSETUP", "Keep it waits until the stored box is ticked, with the reason beside the field", /Store the suggested password/.test(await page.locator("#key-pw-1-error").innerText()));
  await page.keyboard.press("Escape");
  await page.waitForTimeout(400);
  const k2 = await focus();
  check("T-KEYSETUP", "Escape closes it with focus back on the button that opened it", k2.id === "keep-key", `${k2.id} ${k2.text}`);
} else check("T-KEYSETUP", "the example server shows the set-up button", false, "no #keep-key");

await browser.close();
console.log(`\n== ${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
