/* wizard-steps: a part of the shared components. Load it after components.js and parts/error-summary.js, on the pages that use it.
 * Made by tools/parts.py from components.js in github.com/TheMightyTRex/design-system: change it there, not here. */
(() => {
  const S = window.SharedComponents;
  const { focusable, announcer, toast, copyText, sprite, escapeHtml, num, fold, andList, say, ownStatus, notice } = S.kit;
  const { showErrors, clearErrors, setFieldError } = S;

  /* The shared wizard in script (28 November 2026, docs/WIZARD.md, Variants). Markup: `.wizard[data-wizard="id"]`, with
     `data-mode="new"|"again"`, `data-finish="Words that name the action"`, holding
     an optional `ol.steps` (one li for each step), `p.wizard__count`, one `section.wizard__step[data-step][data-title]` for
     each question (`data-optional` when it may be skipped (it then says (optional) and has Skip this step); `data-required` to ask for an answer with an error summary;
     `data-error` is the words of that error), a last `section.wizard__step.wizard__check` and `.wizard__foot` with buttons
     `data-wizard-act="next|back|skip|recommended|finish"`. A choice is an input with `data-label`, and perhaps
     `data-current` (how it is now) and `data-recommended`. The browser's Back button goes step to step (history states);
     Change on Check your answers returns to that step and then to the answers. Fires `wizard-step` and `wizard-finish`
     (`detail: { answers, skipped, changed }`). */
  function wizardValue(step) {
    const out = [];
    step.querySelectorAll("input, select, textarea").forEach((c) => {
      if ((c.type === "radio" || c.type === "checkbox") && !c.checked) return;
      if (c.type === "checkbox" || c.type === "radio" || c.tagName === "SELECT" || c.value !== "") {
        out.push({ value: c.value, label: c.dataset.label || (c.tagName === "SELECT" ? c.selectedOptions[0]?.textContent.trim() : c.value) });
      }
    });
    return out;
  }
  function setupWizards(root = document) {
    root.querySelectorAll(".wizard[data-wizard]:not([data-ready])").forEach((box) => {
      box.dataset.ready = "";
      const id = box.dataset.wizard;
      const steps = [...box.querySelectorAll(".wizard__step")];
      const check = box.querySelector(".wizard__check");
      const questions = steps.filter((s) => s !== check);
      const list = box.querySelector(":scope > .steps");
      const count = box.querySelector(".wizard__count");
      const say = window.SharedComponents.kit.ownStatus(box);
      const again = box.dataset.mode === "again";
      const skipped = new Set();
      const last = steps.length - 1;
      let at = 0;
      let reached = 0;
      let back = false; // Change was pressed: after this step, go to Check your answers
      const act = (n) => box.querySelector(`[data-wizard-act="${n}"]`);
      const title = (s) => s.dataset.title || s.querySelector(".wizard__q")?.textContent.replace(/\(optional\)/, "").trim() || s.dataset.step;
      const skippable = (s) => s.hasAttribute("data-optional") && !s.hasAttribute("data-required");
      const before = (s) => [...s.querySelectorAll("[data-current]")].map((c) => ({ value: c.value, label: c.dataset.label || c.value }));
      const same = (a, b) => a.length === b.length && a.every((x) => b.some((y) => y.value === x.value));
      const words = (v) => (v.length ? v.map((x) => x.label).join(", ") : "Nothing");
      // (optional) on every question that can be skipped, never an asterisk
      questions.forEach((s) => {
        const q = s.querySelector(".wizard__q");
        if (q && skippable(s) && !q.querySelector(".wizard__optional")) {
          const o = document.createElement("span");
          o.className = "wizard__optional";
          o.textContent = " (optional)";
          q.append(o);
        }
      });
            const draw = () => {
        const rows = questions.map((s) => {
          const now = wizardValue(s);
          const was = before(s);
          const changed = again && was.length > 0 && !same(now, was);
          const row = document.createElement("li");
          if (changed) row.dataset.changed = "";
          const text = document.createElement("div");
          const b = document.createElement("b");
          b.textContent = title(s);
          const a = document.createElement("span");
          a.textContent = changed ? `Now: ${words(now)}` : skipped.has(s.dataset.step) ? `${words(now)} (skipped)` : words(now);
          text.append(b, a);
          if (changed) { const w = document.createElement("span"); w.className = "wizard__was"; w.textContent = `Was: ${words(was)}`; text.append(w); }
          const link = document.createElement("a");
          link.href = `#${s.id || `${id}-${s.dataset.step}`}`;
          link.append("Change");
          const hid = document.createElement("span");
          hid.className = "visually-hidden";
          hid.textContent = ` ${title(s)}`;
          link.append(hid);
          link.addEventListener("click", (e) => { e.preventDefault(); back = true; show(questions.indexOf(s), true); });
          row.append(text, link);
          return { row, changed };
        });
        const n = rows.filter((r) => r.changed).length;
        check.querySelectorAll(".wizard-summary, .wizard__change, .wizard__same").forEach((x) => x.remove());
        const ul = document.createElement("ul");
        ul.className = "wizard-summary wizard-summary--check";
        const parts = [ul];
        if (again) {
          const p = document.createElement("p");
          p.className = "wizard__change";
          p.textContent = n ? `${n} of ${rows.length} choices change. The rest stay as they are now.` : "Nothing changes. Every choice stays as it is now.";
          parts.unshift(p);
          ul.append(...rows.filter((r) => r.changed).map((r) => r.row));
          if (n < rows.length) {
            const d = document.createElement("details");
            d.className = "wizard__same";
            const sm = document.createElement("summary");
            sm.textContent = `Choices that stay the same (${rows.length - n})`;
            const u2 = document.createElement("ul");
            u2.className = "wizard-summary wizard-summary--check";
            u2.append(...rows.filter((r) => !r.changed).map((r) => r.row));
            d.append(sm, u2);
            parts.push(d);
          }
        } else ul.append(...rows.map((r) => r.row));
        check.querySelector(".wizard__q").after(...parts);
      };
      const show = (i, focus, fromHistory) => {
        at = Math.max(0, Math.min(last, i));
        reached = Math.max(reached, at);
        steps.forEach((s, k) => { s.hidden = k !== at; });
        box.querySelectorAll(".error-summary").forEach((x) => { x.hidden = true; });
        if (check && at === last) draw();
        [...(list?.children || [])].forEach((item, k) => {
          const done = k < at;
          item.toggleAttribute("data-done", done);
          if (k === at) item.setAttribute("aria-current", "step"); else item.removeAttribute("aria-current");
          const mark = item.querySelector(".visually-hidden");
          if (mark) mark.textContent = k === at ? ", current step" : done ? ", done" : "";
        });
        const word = `Step ${at + 1} of ${steps.length}: ${at === last && check ? "Check your answers" : title(steps[at])}`;
        if (count) count.textContent = word;
        // The progress bar of docs/WIZARD.md section 5: words first, then the bar (role="progressbar"), always shown
        const bar = box.querySelector("[role='progressbar']");
        if (bar) {
          bar.setAttribute("aria-valuemin", "1");
          bar.setAttribute("aria-valuemax", String(steps.length));
          bar.setAttribute("aria-valuenow", String(at + 1));
          bar.setAttribute("aria-valuetext", word);
          if (bar.firstElementChild) bar.firstElementChild.style.width = `${Math.round(((at + 1) / steps.length) * 100)}%`;
          const left = box.querySelector(".meter .numeric");
          if (left) left.textContent = at === last ? "Last step" : `${steps.length - at - 1} to go`;
        }
        const on = at === last && check;
        const next = act("next");
        if (next) { next.hidden = on; next.textContent = back ? "Check your answers" : at === last - 1 && check ? (box.dataset.review || "Check your answers") : "Continue"; }
        const bk = act("back");
        if (bk) bk.hidden = at === 0;
        const sk = act("skip");
        if (sk) sk.hidden = on || back || !skippable(steps[at]);
        const rec = act("recommended");
        if (rec) rec.hidden = on || !box.querySelector("[data-recommended]");
        const fin = act("finish");
        if (fin) { fin.hidden = !on; fin.textContent = box.dataset.finish || "Finish"; }
        if (!fromHistory) {
          try { history.pushState({ wizard: id, step: at }, ""); } catch { /* no history here */ }
        }
        box.dispatchEvent(new CustomEvent("wizard-step", { bubbles: true, detail: { step: steps[at].dataset.step, index: at } }));
        // The wizard speaks only after a step changes, never when it opens
        if (focus || fromHistory) say(word);
        if (focus || fromHistory) { const q = steps[at].querySelector(".wizard__q"); if (q) { q.setAttribute("tabindex", "-1"); q.focus({ preventScroll: false }); } }
      };
      const problems = (s) => {
        if (!s.hasAttribute("data-required")) return [];
        const inputs = [...s.querySelectorAll("input, select, textarea")];
        const ok = inputs.some((c) => ((c.type === "radio" || c.type === "checkbox") ? c.checked : c.value !== ""));
        if (ok) return [];
        if (!inputs[0].id) inputs[0].id = `${id}-${s.dataset.step}-first`;
        return [{ field: inputs[0].id, message: s.dataset.error || `Choose an answer to ${title(s).toLowerCase()}` }];
      };
      act("next")?.addEventListener("click", () => {
        const found = problems(steps[at]);
        if (found.length) { window.SharedComponents.showErrors(steps[at], found); return; }
        skipped.delete(steps[at].dataset.step);
        if (back) { back = false; show(last, true); } else show(at + 1, true);
      });
      act("back")?.addEventListener("click", () => { back = false; if (history.state?.wizard === id && history.state.step === at && at > 0 && reached >= at) history.back(); else show(at - 1, true); });
      act("skip")?.addEventListener("click", () => { skipped.add(steps[at].dataset.step); show(at + 1, true); });
      act("recommended")?.addEventListener("click", () => {
        box.querySelectorAll("[data-recommended]").forEach((c) => {
          if (c.tagName === "SELECT") c.value = c.dataset.recommended || c.value;
          else if (c.type === "radio" || c.type === "checkbox") c.checked = true;
          else if (c.dataset.recommended) c.value = c.dataset.recommended;
          c.dispatchEvent(new Event("change", { bubbles: true }));
        });
        back = false;
        show(last, true);
        say("The recommended choices are selected. Check your answers, then finish.");
      });
      act("finish")?.addEventListener("click", () => {
        const answers = Object.fromEntries(questions.map((s) => [s.dataset.step, wizardValue(s)]));
        const changed = again ? questions.filter((s) => { const w = before(s); return w.length && !same(wizardValue(s), w); }).map((s) => s.dataset.step) : [];
        box.dispatchEvent(new CustomEvent("wizard-finish", { bubbles: true, detail: { answers, skipped: [...skipped], changed } }));
      });
      // The browser's Back button goes step to step, to the step as it was left
      window.addEventListener("popstate", (e) => {
        if (e.state?.wizard === id && box.isConnected) show(e.state.step, false, true);
        else if (!e.state && at !== 0 && box.isConnected) show(0, false, true);
      });
      try { history.replaceState({ wizard: id, step: 0 }, ""); } catch { /* no history here */ }
      show(0, false, true);
    });
  }

  Object.assign(S, { setupWizards });
  S.addSetup(setupWizards);
})();
