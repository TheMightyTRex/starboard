/* wizard-preview: a part of the shared components. Load it after components.js, on the pages that use it.
 * Made by tools/parts.py from components.js in github.com/TheMightyTRex/design-system: change it there, not here. */
(() => {
  const S = window.SharedComponents;
  const { focusable, announcer, toast, copyText, sprite, escapeHtml, num, fold, andList, say, ownStatus, notice } = S.kit;

  /* Preview pane (28 November 2026): `.wizard-preview` holds `.wizard-preview__frame`, `.wizard-preview__strip`, `.wizard-preview__caption`
     (a polite status) and `.wizard-preview__total`. setPreview(pane, { image: { src, alt }, lines: [text], corner, strip:
     [{ label, seconds, kind }], caption, total }) draws it from a picture or from text and styles, never a video. An input
     with `data-preview` (the same object as JSON) inside the same `[data-preview-scope]` as the pane fills it when it is
     changed, and the checked choice fills it when a wizard shows a step. The caption is said only after a change. */
  function setPreview(pane, d, said = true) {
    const frame = pane.querySelector(".wizard-preview__frame");
    const strip = pane.querySelector(".wizard-preview__strip");
    const cap = pane.querySelector(".wizard-preview__caption");
    const total = pane.querySelector(".wizard-preview__total");
    if (frame) {
      frame.replaceChildren();
      const img = d.image && /^(data:image\/(png|jpeg|webp);base64,|\/|https:\/\/)/.test(d.image.src || "") ? d.image : null;
      if (img) {
        const i = document.createElement("img");
        i.src = img.src;
        i.alt = img.alt || "";
        frame.append(i);
      }
      (d.lines || []).slice(0, 3).forEach((t) => { const s = document.createElement("span"); s.className = "wizard-preview__line"; s.textContent = t; frame.append(s); });
      if (d.corner) { const c = document.createElement("span"); c.className = "wizard-preview__corner"; c.textContent = d.corner; frame.append(c); }
    }
    if (strip) {
      strip.replaceChildren();
      strip.hidden = !(d.strip || []).length;
      (d.strip || []).slice(0, 12).forEach((p) => {
        const li = document.createElement("li");
        li.dataset.kind = p.kind || "";
        li.style.flexGrow = String(Math.max(1, Math.min(60, Number(p.seconds) || 1)));
        li.textContent = p.label;
        strip.append(li);
      });
    }
    if (total) total.textContent = d.total || "";
    if (cap) {
      cap.textContent = "";
      if (said) setTimeout(() => (cap.textContent = d.caption || ""), 50); else cap.textContent = d.caption || "";
    }
  }
  function setupPreviewPanes(root = document) {
    root.querySelectorAll(".wizard-preview:not([data-ready])").forEach((pane) => {
      pane.dataset.ready = "";
      const scope = pane.closest("[data-preview-scope]") || pane.parentElement;
      const use = (input, said) => {
        try { setPreview(pane, JSON.parse(input.dataset.preview), said); } catch { /* a choice with no preview leaves the last one */ }
      };
      scope.addEventListener("change", (e) => { if (e.target.dataset?.preview) use(e.target, true); });
      scope.addEventListener("wizard-step", () => {
        const here = scope.querySelector(".wizard__step:not([hidden])");
        const pick = here && [...here.querySelectorAll("[data-preview]")].find((c) => c.checked || c.tagName === "SELECT");
        if (pick) use(pick, false);
      });
      const first = scope.querySelector("[data-preview]:checked");
      if (first) use(first, false);
    });
  }

  Object.assign(S, { setPreview, setupPreviewPanes });
  S.addSetup(setupPreviewPanes);
})();
