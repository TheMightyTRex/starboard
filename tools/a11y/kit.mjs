// The shared parts of the keyboard tasks for wizards (tools/a11y/wizards.mjs): signing in, where focus is, waiting for the
// page or a heading (never a fixed sleep: the MENU3-03 flake was a timing race), the Tab order of a step, and an axe scan
// and a voice check of a step. The older tasks in tasks.mjs keep their own copies of the small helpers.
import { chromium } from "playwright";
import fs from "fs";
import { labelInName } from "./voice.mjs";

export async function start() {
  const base = process.env.BASE;
  const password = fs.readFileSync(process.env.PASSWORD_FILE, "utf8").trim();
  const AXE = fs.readFileSync(process.env.AXE || "/tmp/a/node_modules/axe-core/axe.min.js", "utf8");
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 860 }, bypassCSP: true });  // only so axe can be injected
  const page = await ctx.newPage();
  const tally = { passed: 0, failed: 0 };
  page.on("pageerror", (e) => console.log(`PAGEERROR ${e.message.split("\n")[0]}`));
  const check = (id, what, ok, detail = "") => { ok ? tally.passed++ : tally.failed++; console.log(`${ok ? "PASS" : "FAIL"} ${id} ${what}${!ok && detail ? `: ${detail}` : ""}`); };
  const focus = () => page.evaluate(() => {
    const e = document.activeElement;
    if (!e || e === document.body) return { lost: true, text: "the page itself", tag: "BODY", id: "" };
    return { lost: false, tag: e.tagName, id: e.id, name: e.name || "", role: e.getAttribute("role") || "",
      text: (e.getAttribute("aria-label") || e.textContent || e.value || "").trim().replace(/\s+/g, " ").slice(0, 60),
      inMain: !!e.closest("main"), inPanel: !!e.closest("#side-panel, dialog, [role=dialog]") };
  });
  // Waits for the page to be quiet (no request in flight, nothing marked busy). No fixed sleep.
  const settle = async () => {
    await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
    await page.waitForFunction(() => !document.querySelector("[aria-busy=true]"), null, { timeout: 8000 }).catch(() => {});
  };
  const tabTo = async (match, most = 120) => {
    for (let i = 0; i < most; i++) {
      await page.keyboard.press("Tab");
      const f = await focus();
      if (match(f)) return f;
    }
    return null;
  };
  const signIn = async () => {
    await page.goto(`${base}/login.html`);
    await page.locator("#password").fill(password);
    await page.locator("#password").press("Enter");
    await page.waitForURL((u) => !u.pathname.endsWith("login.html"), { timeout: 15000 }).catch(() => {});
  };
  const open = async (path) => { await page.goto(`${base}/${path}`); await settle(); };
  // Waits until focus is on something that matches (a heading after a step, the opener after Escape) and returns it.
  const focusOn = async (match, ms = 6000) => {
    try { await page.waitForFunction((src) => { const f = new Function("e", `return (${src})(e)`); return f(document.activeElement); }, match.toString(), { timeout: ms }); } catch { /* reported by the caller */ }
    return focus();
  };

  // The Tab order inside a scope (CSS selector), starting from its first stop: Tab forward to the end, then Shift+Tab back.
  // Asserts: every stop shows a focus ring, the order never jumps back up the page, forward and back are the same list in
  // reverse, nothing is a trap (a non-modal scope is left at the end; a modal one wraps).
  const tabOrder = async (id, what, scope, { modal = false, start = null, most = 80 } = {}) => {
    await page.evaluate(([sc, st, md]) => {
      const s = st ? document.querySelector(st) : null;
      if (s) { s.focus(); return; }
      document.activeElement?.blur();
      if (!md) return;
      // A modal scope: start on its last Tab stop, so the first Tab wraps to its first. (After blur the browser would carry on from where focus was.)
      const tabbable = [...document.querySelector(sc).querySelectorAll("a[href], button, input, select, textarea, [tabindex]")].filter((e) => e.tabIndex >= 0 && !e.disabled && e.type !== "hidden" && e.getClientRects().length);
      tabbable[tabbable.length - 1]?.focus();
    }, [scope, start, modal]);
    const stop = () => page.evaluate((sc) => {
      const e = document.activeElement;
      if (!e || e === document.body) return null;
      const root = document.querySelector(sc);
      const r = e.getBoundingClientRect();
      const s = getComputedStyle(e);
      const ringOf = (n) => { const c = getComputedStyle(n); return (c.outlineStyle !== "none" && parseFloat(c.outlineWidth) >= 2) || (c.boxShadow && c.boxShadow !== "none"); };
      const card = e.closest(".row, li, label, .card");
      if (!e.__tid) e.__tid = (window.__tids = (window.__tids || 0) + 1);  // one identity per element, so a redrawn control counts as a different stop
      return { inside: !!root?.contains(e), n: e.__tid, x: r.left, y: r.top + scrollY, b: r.bottom + scrollY,
        ring: ringOf(e) || (!!card && ringOf(card)) || e.matches("input[type=radio], input[type=checkbox]") && !!e.closest("label") && ringOf(e.closest("label")),
        hidden: r.width === 0 || r.height === 0 || s.visibility === "hidden",
        label: (e.getAttribute("aria-label") || e.textContent || e.name || e.id || "").trim().replace(/\s+/g, " ").slice(0, 40) };
    }, scope);
    const forward = [];
    let left = false;
    for (let i = 0; i < most; i++) {
      await page.keyboard.press("Tab");
      const f = await stop();
      if (!f) continue;
      if (!f.inside) { left = true; break; }
      if (forward.length && forward[0].n === f.n) break;  // wrapped to the first stop: a modal scope
      forward.push(f);
    }
    const noRing = forward.filter((f) => !f.ring).map((f) => f.label);
    const jumps = forward.filter((f, i) => i && f.b < forward[i - 1].y - 40 && f.x <= forward[i - 1].x + 10).map((f) => f.label);
    const hidden = forward.filter((f) => f.hidden).map((f) => f.label);
    check(id, `${what}: ${forward.length} Tab stops, every one shows focus`, forward.length > 0 && noRing.length === 0 && hidden.length === 0, `no ring: ${noRing.join(", ")}; hidden: ${hidden.join(", ")}`);
    check(id, `${what}: Tab never jumps back up the page`, jumps.length === 0, jumps.join(", "));
    check(id, `${what}: ${modal ? "Tab wraps and stays inside" : "Tab leaves at the end, no trap"}`, modal ? !left && forward.length < most : left || forward.length < most, `${forward.length} stops`);
    // Back with Shift+Tab: the same stops in reverse.
    if (left || modal) await page.keyboard.press("Shift+Tab");  // from the first stop after the scope (or the wrap to the first), back onto the last one
    const back = [];
    const lastN = forward.length ? forward[forward.length - 1].n : -1;
    if (forward.length) {
      const cur = await stop();
      if (cur && cur.n === lastN) back.push(cur);
      for (let i = 0; i < forward.length + 1 && back.length < forward.length; i++) {
        await page.keyboard.press("Shift+Tab");
        const f = await stop();
        if (f && f.inside) back.push(f);
      }
    }
    const same = back.length === forward.length && back.every((f, i) => f.n === forward[forward.length - 1 - i].n);
    check(id, `${what}: Shift+Tab walks the same stops in reverse`, same, `forward ${forward.length}, back ${back.length}`);
    return forward;
  };

  // axe-core WCAG 2.2 AA and the voice-control name check on what is on screen now (a wizard step, a dialog, a slide-out).
  const scan = async (id, what) => {
    await page.addScriptTag({ content: AXE });
    const v = await page.evaluate(async () => {
      // An open slide-out or dialog is scanned on its own: the page behind it belongs to the page's own scan.
      const res = await window.axe.run(document.querySelector("#side-panel, dialog[open]") || document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"] }, resultTypes: ["violations"] });
      return res.violations.map((x) => `${x.id} (${x.nodes.length}): ${x.nodes.slice(0, 2).map((n) => n.target.join(" ")).join(" | ")}`);
    });
    check(id, `${what}: axe finds nothing`, v.length === 0, v.join("; "));
    const names = await page.evaluate(labelInName);
    for (const m of names) console.log(`VOICE ${what} | ${m.selector} | shows "${m.visible}" | named "${m.name}"`);
    check(id, `${what}: every control's name holds its visible words`, names.length === 0, names.slice(0, 4).map((m) => `${m.selector} "${m.visible}" / "${m.name}"`).join("; "));
  };

  const finish = async () => {
    await browser.close();
    console.log(`\n== ${tally.passed} passed, ${tally.failed} failed`);
    process.exit(tally.failed ? 1 : 0);
  };
  return { base, page, check, focus, settle, tabTo, signIn, open, focusOn, tabOrder, scan, finish, tally };
}
