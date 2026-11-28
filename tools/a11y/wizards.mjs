// Every wizard and multi-step flow by keyboard alone (owner, 27 November 2026), one task per path. The registry is
// tools/a11y/wizards.json and tools/check-wizard-coverage.py fails when a flow in it has no task here or in tasks.mjs.
// Each task: reach every control by Tab and Shift+Tab in the visible order with a visible ring and no trap, Enter and
// Space act, focus lands on the new step's heading after each step, Escape closes a slide-out or dialog and returns focus to
// its opener, an error moves focus to the error. After each step: axe and the voice-control name check on that step.
// Waits are for a heading or a focus, never a fixed sleep. tools/a11y.sh runs it with TASKS=1 (after tasks.mjs) or WIZARDS=1.
import { start } from "./kit.mjs";

const { base, page, check, focus, settle, tabTo, signIn, open, focusOn, tabOrder, scan, finish } = await start();
await signIn();

// Walks a wizard drawn by wizardFrame (settings-core.js): the step list, "Step n of m", the heading #wiz-h, the step's own
// controls and Back, Skip this step and Continue. It leaves each step by Skip (or Continue when the step cannot be skipped)
// with the keyboard, and stops at the last step or after `most` steps.
async function walk(id, name, { most = 40, scanEach = true } = {}) {
  const seen = [];
  for (let i = 0; i < most; i++) {
    const h = await page.waitForSelector("#wiz-h", { timeout: 10000 }).catch(() => null);
    if (!h) { check(id, `${name}: a step heading is on screen`, false, `after ${seen.length} steps`); break; }
    const title = (await h.textContent()).trim();
    if (seen.includes(title)) { check(id, `${name}: no step comes round twice`, false, title); break; }
    seen.push(title);
    const label = `${name}, step ${seen.length} (${title.slice(0, 40)})`;
    // The step is ready when Continue can be used (it waits while the step loads); focus is judged then, not before.
    await page.waitForFunction(() => { const c = [...document.querySelectorAll("main .wizard__foot .btn")].find((b) => /^(Continue|Go to Apps|Write the files|Start copying)/.test(b.textContent)); return !c || !c.disabled; }, null, { timeout: 8000 }).catch(() => {});
    await settle();
    const now = await focusOn((e) => !!e && e !== document.body, 3000);
    check(id, `${label}: focus is on the step's heading or its first control`, now.id === "wiz-h" || (now.inMain && !now.lost), JSON.stringify(now));
    await page.evaluate(() => document.getElementById("wiz-h").focus());
    await tabOrder(id, label, "main", { start: "#wiz-h" });
    if (scanEach) await scan(id, label);
    const last = await page.evaluate(() => !![...document.querySelectorAll("main .wizard__foot button")].find((b) => /^(Go to Apps|Finish|Done|Start copying)/.test(b.textContent)));
    // Leave by keyboard: Skip this step if there is one, else Continue.
    const next = await tabTo((f) => f.tag === "BUTTON" && /^(Skip this step|Continue|Go to Apps|Start copying)/.test(f.text), 60);
    if (!next) { check(id, `${name}: Tab reaches the button that leaves step ${seen.length}`, false, title); break; }
    if (last || /^(Go to Apps|Start copying)/.test(next.text)) break;
    await page.keyboard.press("Enter");
    await page.waitForFunction((t) => document.getElementById("wiz-h")?.textContent.trim() !== t, title, { timeout: 8000 }).catch(() => {});
    await settle();
  }
  check(id, `${name}: ${seen.length} steps reached by keyboard`, seen.length >= 2, seen.join(" > "));
  return seen;
}

// A dialog or slide-out opened by Enter on its opener: focus goes in, the Tab order is walked and axe scans it, and Escape
// closes it and gives focus back to the opener (matched by its words).
async function panelTask(id, name, { page: url, opener, opened = null, scope = "#side-panel, dialog[open]", back = null }) {
  await open(url);
  const b = page.getByRole("button", { name: opener }).first();
  if (!(await b.count())) { check(id, `${name}: the opener is on the page`, false, String(opener)); return; }
  const text = (await b.textContent()).trim().replace(/\s+/g, " ");
  await b.focus();
  await page.keyboard.press("Enter");
  const inside = await focusOn((e) => !!e && !!e.closest("#side-panel, dialog[open]"));
  check(id, `${name}: Enter opens it and focus goes inside`, inside.inPanel, JSON.stringify(inside));
  if (opened) check(id, `${name}: it opens at the right place`, opened.test(await page.evaluate(() => document.querySelector("#side-panel, dialog[open]")?.innerText || "")), "");
  await page.evaluate((sc) => { document.querySelector(sc).setAttribute("data-wizard-scope", ""); }, scope);
  await tabOrder(id, name, "[data-wizard-scope]", { modal: true, start: null });
  await scan(id, name);
  await page.keyboard.press("Escape");
  const out = await focusOn((e) => !!e && !e.closest("#side-panel, dialog[open]"));
  const want = back || new RegExp("^" + text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  check(id, `${name}: Escape closes it and focus goes back to the opener`, want.test(out.text) && !out.inPanel, JSON.stringify(out));
}

// T-SETUP The set-up guide: every step in order by keyboard.
await open("setup-guide.html");
await walk("T-SETUP", "Set-up guide");

// T-BRING Bring in media: the four parts, each by Continue.
await open("bring-in.html?part=bring-sources");
await walk("T-BRING", "Bring in media", { most: 6 });

// T-UPGRADE The upgrade guide after an update that brings choices (the made-up answer says there is one).
await page.route("**/api/releases", async (route) => {
  const r = await route.fetch(); const j = await r.json();
  await route.fulfill({ response: r, json: { ...j, pending: { from: "0.39.0", to: "9.9.9", review: ["storage", "keys", "hours", "alerts", "preset"],
    releases: [{ version: "9.9.9", date: "27 November 2026", added: [["A new thing", "It does a thing."]], settings: "Nothing in your settings changes." }] } } });
});
await open("upgrade.html");
await walk("T-UPGRADE", "Upgrade guide", { most: 8 });
await page.unroute("**/api/releases");

// T-FIRSTPW The first password with the set-up code: errors move focus to the field they are about, one at a time.
await page.route("**/api/session*", async (route) => {
  const r = await route.fetch(); const j = await r.json();
  await route.fulfill({ response: r, json: { ...j, needs_setup: true, signed_in: false, site_name: j.site_name || "Starboard" } });
});
await open("setup.html");
await page.waitForSelector("#login-form [name=token]", { timeout: 8000 }).catch(() => {});
// The page wires the form when the session answer arrives and then fills the dashboard name: wait for that, not a time.
await page.waitForFunction(() => !!document.querySelector("#login-form [name=site_name]")?.value, null, { timeout: 8000 }).catch(() => {});
await scan("T-FIRSTPW", "Create your password");
await tabOrder("T-FIRSTPW", "Create your password", "main", { start: "#login-form [name=token]" });
await page.locator("#login-form [name=token]").focus();
await page.keyboard.press("Enter");
await page.waitForSelector("#token-error:not([hidden])", { timeout: 5000 }).catch(() => {});
const e1 = await focusOn((e) => e?.name === "token");
check("T-FIRSTPW", "Enter with no set-up code puts focus on that field, with its error beside it", e1.name === "token" && await page.evaluate(() => document.querySelector("#login-form [name=token]").getAttribute("aria-invalid") === "true"), JSON.stringify(e1));
await page.locator("#login-form [name=token]").fill("ABCD-1234");
await page.locator("#login-form [name=password]").fill("short");
await page.locator("#login-form [name=password]").press("Enter");
const e2 = await focusOn((e) => e?.name === "password");
check("T-FIRSTPW", "a short password puts focus on the password field", e2.name === "password", JSON.stringify(e2));
await page.unroute("**/api/session*");

// T-RESTORE A saved copy: the slide-out, then Restore this copy asks for the password in a dialog; Escape steps back out.
await panelTask("T-RESTORE", "Saved copy slide-out", { page: "settings-restore.html", opener: /^Open the copy from/ });
await open("settings-restore.html");
const copy = page.getByRole("button", { name: /^Open the copy from/ }).first();
await copy.focus(); await page.keyboard.press("Enter");
await focusOn((e) => !!e?.closest("#side-panel"));
const rest = await tabTo((f) => f.tag === "BUTTON" && /^Restore this copy/.test(f.text), 8);
check("T-RESTORE", "Tab reaches Restore this copy", !!rest, rest ? rest.text : "not reached");
if (rest) {
  await page.keyboard.press("Enter");
  const dlg = await focusOn((e) => !!e?.closest("dialog[open]"));
  check("T-RESTORE", "Restore this copy opens a dialog with focus inside it", dlg.inPanel, JSON.stringify(dlg));
  await scan("T-RESTORE", "Restore this copy, the confirm dialog");
  await page.keyboard.press("Escape");
  const again = await focusOn((e) => !!e && !e.closest("dialog[open]"));
  check("T-RESTORE", "Escape closes the dialog and focus returns to Restore this copy", /^Restore this copy/.test(again.text), JSON.stringify(again));
}

// T-POOL Add a disk and Balance the files: each opens at its step heading, scans clean, and Cancel gives focus back.
for (const [opener, heading] of [[/^Add a disk/, /Choose a disk/], [/^Balance the files/, /How to balance/]]) {
  await open("system-pool.html");
  const o = page.getByRole("button", { name: opener }).first();
  const label = (await o.textContent()).trim();
  await o.focus(); await page.keyboard.press("Enter");
  const h = await focusOn((e) => e?.tagName === "H2" && heading.test(e.textContent));
  check("T-POOL", `${label}: focus lands on the step's heading`, heading.test(h.text) && h.tag === "H2", JSON.stringify(h));
  await scan("T-POOL", `${label}, first step`);
  const cancel = await tabTo((f) => f.tag === "BUTTON" && f.text === "Cancel", 40);
  check("T-POOL", `${label}: Tab reaches Cancel`, !!cancel);
  if (cancel) {
    await page.keyboard.press("Enter");
    // The job takes over the page, so Cancel puts focus on the page's heading (it is made focusable for that), not on a button that is drawn again.
    const back = await focusOn((e) => e?.id === "pool-title");
    check("T-POOL", `${label}: Cancel puts focus on the page heading, Pool`, back.id === "pool-title" && back.text === "Pool", JSON.stringify(back));
  }
}

// T-ADD Library: Add from a search result opens the Add slide-out; Escape returns focus to that result's Add button.
await panelTask("T-ADD", "Add slide-out", { page: "search.html?q=harbour", opener: /^Add Harbour Rising/ });

// T-FINDALL Library: Find all wanted counts first and asks in a dialog.
await panelTask("T-FINDALL", "Find all wanted dialog", { page: "library-films.html", opener: /^Find all wanted/ });

// T-INSTALL Install apps (apps already installed): taking over with no password puts focus on the password field.
await open("install-apps.html");
await scan("T-INSTALL", "Install apps");
await tabOrder("T-INSTALL", "Install apps", "main", { start: "#main" });
const take = page.getByRole("button", { name: /^Take over my apps/ }).first();
await take.focus(); await page.keyboard.press("Enter");
const pw = await focusOn((e) => e?.tagName === "INPUT" && e.type === "password");
check("T-INSTALL", "Take over my apps with no password puts focus on the password field", pw.tag === "INPUT" && await page.evaluate(() => document.activeElement.getAttribute("aria-invalid") === "true" || !!document.activeElement.closest(".field")?.querySelector("[role=alert], .field__error:not([hidden])")), JSON.stringify(pw));

// T-WSTEPS The wizard steps that tasks.mjs already walks by key, scanned by axe and the voice-control check at each step.
await open("settings-jellyfin.html");
const sw = page.getByRole("button", { name: /^Switch with help/ }).first();
await sw.focus(); await page.keyboard.press("Enter");
await focusOn((e) => e?.id === "wizard-step-h");
for (let step = 1; step <= 2; step++) {
  await scan("T-WSTEPS", `Switch media server, step ${step}`);
  await tabOrder("T-WSTEPS", `Switch media server, step ${step}`, "#side-panel", { modal: true, start: "#wizard-step-h" });
  const next = await tabTo((f) => f.tag === "BUTTON" && f.text === "Next", 20);
  if (!next) break;
  await page.keyboard.press("Enter");
  await page.waitForFunction((n) => new RegExp(`Step ${n} of 3`).test(document.getElementById("side-panel")?.innerText || ""), step + 1, { timeout: 8000 }).catch(() => {});
}
await page.keyboard.press("Escape");
await open("settings-general-backup.html");
await page.evaluate(() => document.querySelector("#places-add").focus());
const drive = await tabTo((f) => f.id === "place-add-drive", 10);
if (drive) {
  await page.keyboard.press("Enter");
  await focusOn((e) => e?.id === "cloud-step-heading");
  await scan("T-WSTEPS", "Connect a cloud service, sign-in step");
  await tabOrder("T-WSTEPS", "Connect a cloud service, sign-in step", "#side-panel", { modal: true, start: "#cloud-step-heading" });
  await page.keyboard.press("Escape");
}

// T-CHOOSE Choose a download (a film Starboard has not found yet): the wide slide-out of what Reelix found, best first.
await open("library-films.html");
const missing = await page.evaluate(() => { const a = [...document.querySelectorAll("a[href*='library-film.html']")]; return a.map((x) => x.getAttribute("href")); });
let chosen = null;
for (const href of missing.slice(0, 12)) {
  await page.goto(`${base}/${href.replace(/^\//, "")}`); await settle();
  if (await page.getByRole("button", { name: /^Choose a download/ }).count()) { chosen = href; break; }
}
if (chosen) await panelTask("T-CHOOSE", "Choose a download slide-out", { page: chosen.replace(/^\//, ""), opener: /^Choose a download/ });
else check("T-CHOOSE", "a film with Choose a download is in the example library", false, `${missing.length} films tried`);

// T-LOGIN2 Sign in with a two-step code (the made-up answer says a code is needed): the code field takes focus, the change is said.
await page.context().clearCookies();
await page.goto(`${base}/login.html`);
await page.route("**/api/login", (route) => route.fulfill({ json: { needs_code: true, challenge: "made-up" } }));
await page.waitForSelector("#login-form #password", { timeout: 8000 });
await page.waitForFunction(() => document.activeElement?.id === "password", null, { timeout: 5000 }).catch(() => {});
await page.locator("#login-form #password").fill("a made-up password");
await page.keyboard.press("Enter");
const code = await focusOn((e) => e?.id === "code");
check("T-LOGIN2", "after the password, focus goes to the two-step code field", code.id === "code", JSON.stringify(code));
await page.waitForFunction(() => /two-step code/i.test(document.getElementById("announcer")?.textContent || ""), null, { timeout: 3000 }).catch(() => {});
check("T-LOGIN2", "and it is said in the announcer", /two-step code/i.test(await page.locator("#announcer").innerText()), "");
await scan("T-LOGIN2", "Sign in, two-step code");
await page.keyboard.press("Enter");
const err = await focusOn((e) => e?.id === "code");
check("T-LOGIN2", "Enter with no code keeps focus on the code field", err.id === "code", JSON.stringify(err));

// T-PAGEWIZ A plug-in's page made of the shared wizard (plug-in API 1.26, the example plug-in Page parts example): Continue, the
// preview beside the step, Play preview (only when pressed), Skip, Check your answers, Change that comes back to the answers, the
// browser's Back button, and the confirm button that names its action. All by keyboard.
await open("settings-plugin.html?id=page-parts");
await page.getByRole("tab", { name: /Set up the breaks/ }).focus();
await page.keyboard.press("Enter");
await page.waitForSelector(".wizard[data-wizard] .wizard__q", { timeout: 10000 }).catch(() => {});
const wiz = ".wizard[data-wizard]";
await page.evaluate((w) => document.querySelector(`${w} .wizard__step:not([hidden]) .wizard__q`)?.focus(), wiz);
await tabOrder("T-PAGEWIZ", "Page parts wizard, first step", "[data-preview-scope]", { start: `${wiz} .wizard__step:not([hidden]) .wizard__q` });
await scan("T-PAGEWIZ", "Page parts wizard, first step");
const goOn = async (n = 1) => { for (let i = 0; i < n; i++) { await tabTo((f) => f.tag === "BUTTON" && /^(Continue|Check your answers)$/.test(f.text), 60); await page.keyboard.press("Enter"); await settle(); } };
await goOn(2);
check("T-PAGEWIZ", "Continue moves focus to the next question", (await focusOn((e) => !!e?.classList.contains("wizard__q"))).lost === false, "");
check("T-PAGEWIZ", "nothing plays before Play preview is pressed", (await page.locator(`${wiz} audio, ${wiz} video`).count()) === 0, "");
await page.evaluate((w) => document.querySelector(`${w} [data-preview-src]`)?.focus(), wiz);
await page.keyboard.press("Space");
await page.waitForSelector(`${wiz} audio`, { timeout: 4000 }).catch(() => {});
check("T-PAGEWIZ", "Space on Play preview puts a player in the card", (await page.locator(`${wiz} audio`).count()) === 1, "");
check("T-PAGEWIZ", "Play preview is named with the file", /Stop preview of Station title/.test(await page.locator(`${wiz} [data-preview-src]`).first().textContent()), "");
await scan("T-PAGEWIZ", "Page parts wizard, clips");
await tabTo((f) => f.tag === "BUTTON" && /^Skip this step$/.test(f.text), 60);
await page.keyboard.press("Enter"); await settle();
await goOn(1);
check("T-PAGEWIZ", "Check your answers is reached", await page.locator(`${wiz} .wizard__check`).isVisible(), "");
await scan("T-PAGEWIZ", "Page parts wizard, Check your answers");
await tabTo((f) => f.tag === "A" && /^Change Style/.test(f.text), 60);
await page.keyboard.press("Enter"); await settle();
check("T-PAGEWIZ", "Change returns to that step", (await page.locator(`${wiz} .wizard__step:not([hidden])`).getAttribute("data-step")) === "style", "");
await goOn(1);
check("T-PAGEWIZ", "and then to Check your answers", await page.locator(`${wiz} .wizard__check`).isVisible(), "");
await page.goBack(); await settle();
check("T-PAGEWIZ", "the browser's Back button goes to the step before", !(await page.locator(`${wiz} .wizard__check`).isVisible()), "");

// T-PAGESENT A sentence with selects: a change by keyboard is saved at once, said in plain words, and focus stays on the select.
await open("settings-plugin.html?id=page-parts");
await page.getByRole("tab", { name: /In a sentence/ }).focus();
await page.keyboard.press("Enter");
await page.waitForSelector(".sentence select", { timeout: 10000 }).catch(() => {});
await scan("T-PAGESENT", "Page parts sentence");
await page.locator(".sentence select[aria-label=Clips]").focus();
await page.keyboard.press("ArrowDown");
await page.waitForFunction(() => /clips/.test(document.querySelector("[data-readback]")?.textContent || ""), null, { timeout: 4000 }).catch(() => {});
check("T-PAGESENT", "the sentence is read back in plain words", /clips/.test(await page.locator("[data-readback]").innerText()), "");
check("T-PAGESENT", "focus stays on the select that changed", (await focus()).text === "Clips", "");

// T-PAGEMORE Show more settings: the switch shows and hides the rows by keyboard, focus stays on it.
await open("settings-plugin.html?id=page-parts");
await page.getByRole("tab", { name: /Clips and music/ }).focus();
await page.keyboard.press("Enter");
await page.waitForSelector("[data-more-switch]", { timeout: 10000 }).catch(() => {});
await scan("T-PAGEMORE", "Page parts, clips and music");
await page.locator("[data-more-switch]").focus();
check("T-PAGEMORE", "the extra rows are hidden at first", (await page.locator("[data-more]:visible").count()) === 0, "");
await page.keyboard.press("Space");
check("T-PAGEMORE", "Space on Show more settings shows them", (await page.locator("[data-more]:visible").count()) > 0, "");
check("T-PAGEMORE", "focus stays on the switch", (await focus()).role === "switch", "");

await finish();
