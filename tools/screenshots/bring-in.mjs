// Pictures of Bring in media (DASH-455) from the example-data server, for the design review and the help: each part
// of the step, the folder picker on its places screen and in a folder, Check names in its three lists, the copy's
// progress and the report, in light, dark, on a phone and with 175% text. tools/screenshots/bring-in.sh runs it in the
// Playwright image. The progress and the report are drawn from made-up states written into the example data folder.
import { chromium } from "playwright";
import fs from "fs";

const base = process.env.BASE || "http://127.0.0.1:18792";
const out = process.env.OUT || "/out";
const data = process.env.DATA || "/work/data";
const password = fs.readFileSync(process.env.PASSWORD_FILE, "utf8").trim();
const desk = { width: 1280, height: 900 };
const phone = { width: 390, height: 844 };
const until = (sel, ms = 15000) => `(async () => { for (let i = 0; i < ${ms / 250} && !document.querySelector(${JSON.stringify(sel)}); i++) await new Promise((r) => setTimeout(r, 250)); await new Promise((r) => setTimeout(r, 700)); })()`;
const GB = 1e9;
// In the picker: Drive 2, then its first folder, then wait for the sizes to be counted.
const intoFolder = `(async () => { const w = async (f) => { for (let i = 0; i < 60 && !f(); i++) await new Promise((r) => setTimeout(r, 250)); };
  await w(() => document.querySelector("[data-place^='disk:']")); document.querySelector("[data-place^='disk:']").click();
  await w(() => document.querySelector(".folder-list [role=option]")); document.querySelector(".folder-list [role=option]").click();
  await new Promise((r) => setTimeout(r, 600));
  await w(() => document.querySelector(".folder-row__meta") && ![...document.querySelectorAll(".folder-row__meta")].some((m) => m.textContent === "Counting…"));
  await new Promise((r) => setTimeout(r, 500)); })()`;
const running = { state: "running", phase: "copying", started: Date.now() / 1000 - 1500, files_total: 31, files_done: 12, bytes_total: 98.4 * GB, bytes_done: 41.7 * GB, current: "The Long Field", paused: false };
const stopped = { ...running, state: "stopped", error: "The media disk is nearly full, so the copy stopped. Free some space, then Carry on" };
const report = {
  at: Date.now() / 1000, holding: "", added: { films: 6, series: 3 },
  counts: { copied: 9, look: 1, left: 5 },
  copied: [["Harbour Lights (2019)", "films", "media/movies/Harbour Lights (2019)", "Drive 2: Old media"], ["The Long Field (2021)", "films", "media/movies/The Long Field (2021)", "Drive 2: Old media"],
    ["Paper Planets (2017)", "films", "media/movies/Paper Planets (2017)", "Drive 2: Old media"], ["Glass Orchard (2015)", "films", "media/movies/Glass Orchard (2015)", "/home/sam"],
    ["Northern Line (2023)", "films", "media/movies/Northern Line (2023)", "/home/sam"], ["Copper Valley (2018)", "series", "media/tv/Copper Valley (2018)", "Drive 2: Old media"],
    ["Saltmarsh (2016)", "series", "media/tv/Saltmarsh (2016)", "Drive 2: Old media"], ["First Light", "music", "media/music/Midnight Garden/First Light", "Drive 2: Old media"],
    ["Little Lanterns (2022)", "series", "media/tv/Little Lanterns (2022)", "//192.0.2.20/media"]].map(([title, kind, to, from]) => ({ title, kind, to, from, linked: false, note: "" })),
  look: [{ title: "Tidewater", kind: "films", to: "media/movies/Tidewater", from: "Drive 2: Old media", why: "More than one match: choose the right one" }],
  left: [["sample.mkv", "A sample, not the whole film or episode"], ["RARBG.txt", "Not media"], ["Thumbs.db", "Not media"],
    ["Paper Planets (2017).mkv", "The same title is in Drive 2: Old media, which comes first in your list"], ["The Quiet Coast.epub", "You chose to leave this folder where it is"]]
    .map(([title, why]) => ({ title, kind: null, from: "", why })),
};
const write = (name, value) => fs.writeFileSync(`${data}/bring-in/${name}`, JSON.stringify(value));
const clear = () => { for (const n of ["job.json", "report.json"]) try { fs.unlinkSync(`${data}/bring-in/${n}`); } catch { /* not there */ } };
// Into the set-up guide's step: Continue until the step's own question shows (the steps before keep their defaults).
const intoGuide = `(async () => { for (let i = 0; i < 12; i++) { const h = document.querySelector("#wiz-h"); if (h && /media you already have/.test(h.textContent)) break;
  const b = [...document.querySelectorAll(".wizard__foot .btn")].find((x) => /Continue|Begin/.test(x.textContent)); if (!b) break; b.click(); await new Promise((r) => setTimeout(r, 1500)); }
  await new Promise((r) => setTimeout(r, 800)); })()`;

const SHOTS = [
  { file: "1-sources.png", page: "bring-in.html?part=bring-sources", ...desk, run: until(".bring-sources li") },
  { file: "1-sources-dark.png", page: "bring-in.html?part=bring-sources", ...desk, scheme: "dark", run: until(".bring-sources li") },
  { file: "1-sources-phone.png", page: "bring-in.html?part=bring-sources", ...phone, full: true, run: until(".bring-sources li") },
  { file: "1-sources-175.png", page: "bring-in.html?part=bring-sources", ...desk, text: "175", full: true, run: until(".bring-sources li") },
  { file: "1-sources-in-the-set-up.png", page: "setup-guide.html", ...desk, full: true, run: intoGuide },
  { file: "picker-1-places.png", page: "bring-in.html?part=bring-sources", ...desk, run: until(".bring-sources li"), click: "#bring-add", after: until(".folder-place") },
  { file: "picker-1-places-phone.png", page: "bring-in.html?part=bring-sources", ...phone, run: until(".bring-sources li"), click: "#bring-add", after: until(".folder-place") },
  { file: "picker-2-folder.png", page: "bring-in.html?part=bring-sources", ...desk, run: until(".bring-sources li"), click: "#bring-add", after: intoFolder },
  { file: "picker-2-folder-dark.png", page: "bring-in.html?part=bring-sources", ...desk, scheme: "dark", run: until(".bring-sources li"), click: "#bring-add", after: intoFolder },
  { file: "picker-2-folder-phone.png", page: "bring-in.html?part=bring-sources", ...phone, run: until(".bring-sources li"), click: "#bring-add", after: intoFolder },
  { file: "picker-2-folder-175.png", page: "bring-in.html?part=bring-sources", ...desk, text: "175", run: until(".bring-sources li"), click: "#bring-add", after: intoFolder },
  { file: "2-what.png", page: "bring-in.html?part=bring-what", width: 1280, height: 1400, run: until(".bring-what table") + ";" + until("[role=status]") },
  { file: "2-what-dark.png", page: "bring-in.html?part=bring-what", width: 1280, height: 1400, scheme: "dark", run: until(".bring-what table") },
  { file: "2-what-phone.png", page: "bring-in.html?part=bring-what", ...phone, full: true, run: until(".bring-what table") },
  { file: "2-what-175.png", page: "bring-in.html?part=bring-what", ...desk, text: "175", full: true, run: until(".bring-what table") },
  { file: "3-names-matched.png", page: "bring-in.html?part=bring-names", width: 1280, height: 1300, run: until(".bring-name") },
  { file: "3-names-look.png", page: "bring-in.html?part=bring-names", width: 1280, height: 1100, run: until(".bring-name"), click: "label[for='bring-state-look']", after: until(".bring-choices") },
  { file: "3-names-left.png", page: "bring-in.html?part=bring-names", width: 1280, height: 1100, run: until(".bring-name"), click: "label[for='bring-state-left']", after: until(".bring-name") },
  { file: "3-names-dark.png", page: "bring-in.html?part=bring-names", width: 1280, height: 1100, scheme: "dark", run: until(".bring-name"), click: "label[for='bring-state-look']", after: until(".bring-choices") },
  { file: "3-names-phone.png", page: "bring-in.html?part=bring-names", ...phone, full: true, run: until(".bring-name") },
  { file: "3-names-175.png", page: "bring-in.html?part=bring-names", ...desk, text: "175", full: true, run: until(".bring-name"), click: "label[for='bring-state-look']", after: until(".bring-choices") },
  { file: "4-copy-check.png", page: "bring-in.html?part=bring-copy", ...desk, run: until(".table") },
  { file: "4-copy-check-phone.png", page: "bring-in.html?part=bring-copy", ...phone, full: true, run: until(".table") },
  { file: "4-copy-progress.png", page: "bring-in.html", ...desk, prepare: () => write("job.json", running), run: until(".wizard-job") },
  { file: "4-copy-progress-dark.png", page: "bring-in.html", ...desk, scheme: "dark", prepare: () => write("job.json", running), run: until(".wizard-job") },
  { file: "4-copy-progress-phone.png", page: "bring-in.html", ...phone, prepare: () => write("job.json", running), run: until(".wizard-job") },
  { file: "4-copy-stopped.png", page: "bring-in.html", ...desk, prepare: () => write("job.json", stopped), run: until(".wizard-job") },
  { file: "4-copy-progress-dashboard.png", page: "dashboard.html", ...desk, prepare: () => write("job.json", running), run: until(".bring-banner") },
  { file: "4-copy-progress-activity.png", page: "downloads.html", ...desk, prepare: () => write("job.json", running), run: until(".bring-banner") },
  { file: "5-report.png", page: "bring-in.html", width: 1280, height: 1600, prepare: () => { write("report.json", report); write("job.json", { ...running, state: "done", phase: "done", files_done: 31, bytes_done: 98.4 * GB, report: report.counts }); }, run: until(".bring-report__part li") },
  { file: "5-report-dark.png", page: "bring-in.html", width: 1280, height: 1600, scheme: "dark", prepare: () => { write("report.json", report); write("job.json", { ...running, state: "done", phase: "done", report: report.counts }); }, run: until(".bring-report__part li") },
  { file: "5-report-phone.png", page: "bring-in.html", ...phone, full: true, prepare: () => { write("report.json", report); write("job.json", { ...running, state: "done", phase: "done", report: report.counts }); }, run: until(".bring-report__part li"), cleanup: clear },
];

fs.mkdirSync(out, { recursive: true });
const only = process.env.ONLY ? new RegExp(process.env.ONLY) : null;
const browser = await chromium.launch();
const errors = [];
let failed = false;
const contexts = {};
async function pageFor(shot) {
  const key = `${shot.width}x${shot.height}-${shot.scheme || "light"}-${shot.text || "100"}`;
  if (!contexts[key]) {
    const context = await browser.newContext({ viewport: { width: shot.width, height: shot.height }, colorScheme: shot.scheme || "light" });
    const text = shot.text || "100";
    await context.addInitScript((t) => {
      try {
        sessionStorage.setItem("starboard.setup-wizard", JSON.stringify({ opened: true }));
        localStorage.setItem("starboard.display", JSON.stringify({ text: t }));
        if (!sessionStorage.getItem("starboard-guide")) sessionStorage.setItem("starboard-guide", JSON.stringify({ start: "new" }));  // the set-up's new install
      } catch { /* fine */ }
    }, text);
    const page = await context.newPage();
    page.on("pageerror", (e) => errors.push(`${page.url()}: ${e.message}`));
    page.on("console", (m) => { if (m.type() === "error" && !/40[04]/.test(m.text())) errors.push(`${page.url()}: ${m.text()}`); });
    await page.goto(`${base}/login.html`);
    await page.fill("input[type=password]", password);
    await page.keyboard.press("Enter");
    await page.waitForURL(/dashboard|index/);
    contexts[key] = page;
  }
  return contexts[key];
}
for (const shot of SHOTS) {
  if (only && !only.test(shot.file)) continue;
  clear();
  if (shot.prepare) shot.prepare();
  const page = await pageFor(shot);
  await page.goto(`${base}/${shot.page}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(600);
  try {
    if (shot.run) { await page.evaluate(shot.run); await page.waitForTimeout(300); }
    if (shot.click) { await page.locator(shot.click).first().click(); await page.waitForTimeout(600); }
    if (shot.after) { await page.evaluate(shot.after); await page.waitForTimeout(300); }
  } catch (e) { errors.push(`${shot.file}: ${e.message}`); }
  await page.screenshot({ path: `${out}/${shot.file}`, fullPage: !!shot.full });
  const wide = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
  if (wide > 0) failed = true;
  console.log(shot.file, wide > 0 ? `SCROLLS SIDEWAYS by ${wide}px` : "ok");
  if (shot.cleanup) shot.cleanup();
}
clear();
// The terminal set-up's screens (bring-in-terminal.py wrote them as pages).
if (fs.existsSync("/work/term") && (!only || only.test("terminal"))) {
  const tp = await (await browser.newContext({ viewport: { width: 900, height: 860 } })).newPage();
  for (const f of fs.readdirSync("/work/term").filter((x) => x.endsWith(".html")).sort()) {
    await tp.goto(`file:///work/term/${f}`);
    await tp.locator(".term").screenshot({ path: `${out}/${f.replace(".html", ".png")}` });
    console.log(f.replace(".html", ".png"), "ok");
  }
}
console.log(errors.length ? `Console errors:\n${errors.join("\n")}` : "No console errors");
await browser.close();
process.exit(failed || errors.length ? 1 : 0);
