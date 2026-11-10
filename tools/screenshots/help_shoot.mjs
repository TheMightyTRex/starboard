// Takes the help centre's screenshots (docs/help/images) from the example-data server, marked up to the design
// system's screenshot rules with annotate.js: a red outline round each control, a curved arrow, and a badge with
// the step's number in the article. tools/help-screenshots.sh runs this in the Playwright image.
//
// Each shot in help_shots.json: { topic, file, page, width?, height?, scheme?, run?, marks: [{ t, step?, side? }],
// steps: [...], alt }. A mark's t is the visible text of a control, "$css selector", or "field:name" (the form
// field with that name, with its label and hint). A shot whose mark-up check fails is not taken: it is listed
// at the end, and the run fails. 7 November 2026.
import { chromium } from "playwright";
import fs from "fs";

const base = process.env.BASE || "http://127.0.0.1:18792";
const out = process.env.OUT || "/out";
const only = process.env.ONLY || "";
const password = fs.readFileSync(process.env.PASSWORD_FILE, "utf8").trim();
const annotate = fs.readFileSync(new URL("./annotate.js", import.meta.url), "utf8");
const shots = JSON.parse(fs.readFileSync(new URL("./help_shots.json", import.meta.url), "utf8")).shots
  .filter((s) => !only || only.split(",").includes(s.topic));

fs.mkdirSync(out, { recursive: true });
const browser = await chromium.launch();
const problems = [];
const contexts = {};
async function pageFor(shot) {
  const w = shot.width || 1280, h = shot.height || 800, scheme = shot.scheme || "light";
  const key = `${w}x${h}-${scheme}`;
  if (!contexts[key]) {
    const context = await browser.newContext({ viewport: { width: w, height: h }, colorScheme: scheme });
    await context.addInitScript(() => { try { sessionStorage.setItem("starboard.setup-wizard", JSON.stringify({ opened: true })); } catch { /* fine */ } });  // the set-up wizard counts as seen (DASH-289)
    const page = await context.newPage();
    page.on("pageerror", (e) => problems.push(`${page.url()}: ${e.message}`));
    await page.goto(`${base}/login.html`);
    await page.fill("input[type=password]", password);
    await page.keyboard.press("Enter");
    await page.waitForURL(/dashboard|index/);
    contexts[key] = page;
  }
  return contexts[key];
}

for (const shot of shots) {
  const page = await pageFor(shot);
  // A terminal screen (tools/screenshots/terminal_page.py) is a file next to this script; anything else is a page
  // of the example server.
  const url = shot.page.startsWith("terminal/") ? new URL(`./${shot.page}`, import.meta.url).href : `${base}/${shot.page}`;
  await page.goto(url, { waitUntil: "networkidle" });
  await page.waitForTimeout(1500); // settle (SCREENSHOTS.md section 3)
  if (shot.run) { await page.evaluate(`(async () => { ${shot.run} })()`); await page.waitForTimeout(1500); }
  await page.evaluate(annotate);
  const result = await page.evaluate(({ marks, steps }) => {
    const target = (t) => {
      if (t.startsWith("field:")) {
        const input = document.querySelector(`[name="${t.slice(6)}"]`);
        return input ? (input.closest(".field") || input) : null;
      }
      return t.startsWith("$") ? document.querySelector(t.slice(1)) : window.Annotate.byText(t);
    };
    window.Annotate.clear();
    const missing = [];
    for (const m of marks) {
      const el = target(m.t);
      if (!el) { missing.push(m.t); continue; }
      el.scrollIntoView({ block: "nearest" });
    }
    for (const m of marks) {
      const el = target(m.t);
      if (el) window.Annotate.mark(el, { step: m.step ?? null, side: m.side || "right", tail: m.tail || 110 });
    }
    const v = window.Annotate.verify({ steps });
    if (missing.length) v.problems.unshift(`not on the page: ${missing.join(", ")}`), v.pass = false;
    return v;
  }, { marks: shot.marks, steps: shot.steps });
  await page.waitForTimeout(400);
  if (!result.pass) { problems.push(`${shot.file}: ${result.problems.join("; ")}`); console.log(shot.file, "NOT TAKEN"); continue; }
  await page.screenshot({ path: `${out}/${shot.file}` });
  console.log(shot.file, "ok");
}
console.log(problems.length ? `Problems:\n${problems.join("\n")}` : "No problems");
await browser.close();
process.exit(problems.length ? 1 : 0);
