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

// T-AITOOL Connect an AI tool (DASH-655): the shared wizard drawn from markup (part wizard-steps). By keyboard alone: choose the
// tool and where it runs with the arrow keys, leave each step with Continue, land on the next question's heading, go back
// with the browser's Back, change an answer from Check your answers and come back to it, enter the password, make the key,
// and land on the result's heading with the key hidden and Copy ready. axe scans each step.
await open("settings-security-ai.html");
await page.waitForSelector(".wizard[data-wizard=connect-ai-tool] .wizard__q");
const qHeading = () => focusOn((e) => e?.classList?.contains("wizard__q") || e?.id === "ai-done-h");
const radio = async (name, value) => { await page.locator(`input[name=${name}][value=${value}]`).focus(); await page.keyboard.press("Space"); };
const goOn = async () => { const b = await tabTo((f) => f.tag === "BUTTON" && /^(Continue|Check your answers)$/.test(f.text), 60); if (b) await page.keyboard.press("Enter"); return b; };
await scan("T-AITOOL", "Connect an AI tool, step 1");
check("T-AITOOL", "nothing has focus on the wizard when the page opens", await page.evaluate(() => !document.querySelector(".wizard")?.contains(document.activeElement)), "");
await radio("tool", "claude-code");
check("T-AITOOL", "Continue is reached by Tab", !!(await goOn()), "");
const h2 = await qHeading();
check("T-AITOOL", "focus lands on the next question's heading", /Where does the AI tool run/.test(h2.text), JSON.stringify(h2));
await page.keyboard.press("Alt+ArrowLeft");
const h1 = await qHeading();
check("T-AITOOL", "the browser's Back button goes to the step before", /Which AI tool/.test(h1.text) && (await page.locator("input[name=tool][value=claude-code]").isChecked()), JSON.stringify(h1));
await goOn(); await qHeading();
await scan("T-AITOOL", "Connect an AI tool, step 2");
await radio("where", "here");
await goOn(); await qHeading();
await scan("T-AITOOL", "Connect an AI tool, step 3");
await goOn(); await qHeading();           // what it may read: the defaults are ticked
await scan("T-AITOOL", "Connect an AI tool, step 4");
const skip = await tabTo((f) => f.tag === "BUTTON" && /^Skip this step/.test(f.text), 60);
check("T-AITOOL", "an optional step has Skip this step", !!skip, "");
if (skip) await page.keyboard.press("Enter");
const h5 = await qHeading();
check("T-AITOOL", "Skip moves on to the name", /What should the key be called/.test(h5.text), JSON.stringify(h5));
await goOn();
const hc = await qHeading();
check("T-AITOOL", "Check your answers has focus on its heading", /Check your answers/.test(hc.text), JSON.stringify(hc));
await scan("T-AITOOL", "Connect an AI tool, Check your answers");
const change = await tabTo((f) => f.tag === "A" && /^Change Where does|^Change /.test(f.text) && /Where/.test(f.text), 60);
check("T-AITOOL", "Tab reaches a Change link named for its question", !!change, change ? change.text : "");
if (change) {
  await page.keyboard.press("Enter");
  const back = await qHeading();
  check("T-AITOOL", "Change goes to that question", /Where does the AI tool run/.test(back.text), JSON.stringify(back));
  await goOn();
  const again = await qHeading();
  check("T-AITOOL", "and then straight back to Check your answers", /Check your answers/.test(again.text), JSON.stringify(again));
}
await page.locator("#ai-password").fill(password);
const make = await tabTo((f) => f.tag === "BUTTON" && /^Turn on AI tools and make the key|^Make the key/.test(f.text), 60);
check("T-AITOOL", "Tab reaches the button that makes the key", !!make, make ? make.text : "");
if (make) {
  await page.keyboard.press("Enter");
  const done = await qHeading();
  check("T-AITOOL", "focus lands on the result's heading", done.id === "ai-done-h", JSON.stringify(done));
  check("T-AITOOL", "the key is hidden until Show", await page.evaluate(() => document.getElementById("ai-key-made")?.type === "password"), "");
  await scan("T-AITOOL", "Connect an AI tool, the result");
  const copyKey = await tabTo((f) => f.tag === "BUTTON" && /^Copy the key/.test(f.text), 30);
  check("T-AITOOL", "Tab reaches Copy for the key", !!copyKey, copyKey ? copyKey.text : "");
}

await finish();
