// Drives the browser set-up on a test machine as a person would, from the address the Run first script opened, and
// records every step: a picture, the heading, and what would look wrong (sideways scrolling, an error notice, a script
// error, a button that does nothing). It fills the passwords, ticks every app when ALL_APPS=1, gives made-up VPN
// details, and presses the main button of each step. Run by tools/vm/browser.sh. 6 November 2026.
import fs from "fs";
import { chromium } from "playwright";

const base = process.env.BASE;                        // http://127.0.0.1:18095
const start = process.env.START || "/";               // the path and #code the stand-in browser was given
const out = process.env.OUT || "/out";
const pw = process.env.SB_PASSWORD || "correct horse battery staple";
const allApps = process.env.ALL_APPS === "1";
const install = { basics: "Basics", full: "Full install", all: "Everything", choose: "Choose myself" }[process.env.INSTALL || ""] || "";
const usenet = { nzbget: "NZBGet", sabnzbd: "SABnzbd" }[process.env.USENET || ""] || "";
const width = Number(process.env.WIDTH || 1280);
fs.mkdirSync(out, { recursive: true });

const faults = [];
const steps = [];
const fault = (kind, detail) => { if (!faults.some((f) => f.kind === kind && f.detail === detail)) faults.push({ kind, detail, step: steps.length }); };

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width, height: 900 } });
page.on("pageerror", (e) => fault("script error", e.message));
page.on("console", (m) => { if (m.type() === "error") fault("console error", m.text().slice(0, 200)); });
page.setDefaultTimeout(15000);

await page.goto(base + start, { waitUntil: "networkidle" }).catch((e) => fault("could not open", e.message));
let same = 0, lastKey = "";
for (let n = 0; n < 250; n++) {
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(800);
  const state = await page.evaluate(() => {
    const vis = (e) => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
    const head = [...document.querySelectorAll("main h1, main h2, .wizard h2, .wizard h3")].filter(vis).map((h) => h.textContent.trim()).slice(0, 3).join(" | ");
    const current = document.querySelector('[aria-current="step"]')?.textContent.trim() || "";
    const danger = [...document.querySelectorAll('.notice[data-tone="danger"], [role="alert"]')].filter(vis).map((e) => e.textContent.trim()).filter(Boolean);
    return { url: location.pathname, head, current, danger, sideways: document.documentElement.scrollWidth > innerWidth + 1,
             busy: !!document.querySelector('[aria-busy="true"]:not([hidden])'),
             working: [...document.querySelectorAll(".progress--busy")].some(vis) };
  });
  const key = state.url + state.head + state.current;
  steps.push({ n, ...state });
  await page.screenshot({ path: `${out}/${String(n).padStart(3, "0")}.png`, fullPage: true }).catch(() => {});
  if (state.sideways) fault("page scrolls sideways", `${state.url} ${state.head}`);
  for (const d of state.danger) fault("error shown", `${state.url} ${state.head}: ${d.slice(0, 300)}`);
  if (state.working) { steps.at(-1).note = "waiting for the progress bar"; await page.waitForTimeout(10000); continue; }
  if (key === lastKey) { same++; } else { same = 0; lastKey = key; }
  if (same >= 4) { fault("stuck", `${state.url} ${state.head} ${state.current}`); break; }
  if (state.busy && same < 3) { await page.waitForTimeout(5000); continue; }

  if (state.url === "/index.html" && steps.some((s) => s.pressed === "Go to Apps")) { steps.at(-1).note = "reached the dashboard"; break; }
  // Fill what a person would fill.
  for (const input of await page.locator('main input[type="password"]:visible').all()) {
    if (!(await input.inputValue())) await input.fill(pw);
  }
  const vpn = page.locator('main input[list="vpn-providers"]:visible');
  if (await vpn.count() && !(await vpn.inputValue())) {
    await vpn.fill("protonvpn");
    const fields = page.locator("main .form-stack input.input:visible");
    for (const f of await fields.all()) {
      const ph = (await f.getAttribute("placeholder")) || "";
      if (!(await f.inputValue()) && ph.includes("/32")) await f.fill("192.0.2.2/32");
    }
    const key = page.locator('main input[type="password"]:visible').first();
    if (await key.count()) await key.fill("c3RhcmJvYXJkLXRlc3Qta2V5LW5vdC1yZWFsLTAwMDA=");
  }
  for (const label of [install, usenet].filter(Boolean)) {
    const radio = page.getByRole("radio", { name: new RegExp("^" + label) }).and(page.locator(":visible"));
    if (await radio.count() && !(await radio.first().isChecked())) {
      await radio.first().check().catch((e) => fault("could not choose", `${label}: ${e.message.split("\n")[0]}`));
      await page.waitForTimeout(500);  // choosing an install can add the Usenet choice below it
    }
  }
  if (allApps) {
    for (const box of await page.locator('main input[type="checkbox"]:visible').all()) {
      if (!(await box.isChecked()) && (await box.isEnabled())) await box.check().catch(() => {});
    }
  }
  // The main button of the step.
  const primary = page.locator("main .btn--primary:visible:not([disabled])").filter({ hasNotText: /^(Stop|Remove|Delete|Sign out)/ });
  const named = page.getByRole("button", { name: /^(Continue|Next|Begin|Finish|Write the files|Start the apps|Add the ticked apps|Save|Create|Sign in|Set up|Go to Apps|Keep the defaults)/ });
  const start = page.getByRole("button", { name: /^(Start the apps|Add the ticked apps to Starboard)/ }).and(page.locator(":visible:not([disabled])"));
  const target = (await start.count()) ? start.first() : (await primary.count()) ? primary.last() : (await named.count()) ? named.last() : null;
  if (!target) {
    if (state.url.endsWith("/index.html") || state.url === "/") { steps.at(-1).note = "reached the dashboard"; break; }
    fault("no button to carry on", `${state.url} ${state.head}`);
    break;
  }
  steps.at(-1).pressed = (await target.textContent()).trim();
  await target.click().catch((e) => fault("button failed", `${steps.at(-1).pressed}: ${e.message.split("\n")[0]}`));
}
await browser.close();
fs.writeFileSync(`${out}/result.json`, JSON.stringify({ faults, steps }, null, 2));
console.log(`${steps.length} steps, ${faults.length} faults; last: ${steps.at(-1)?.url} ${steps.at(-1)?.head}`);
for (const f of faults) console.log(" -", f.kind, ":", f.detail);
