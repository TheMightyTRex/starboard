/* more-rows: a part of the shared components. Load it after components.js, on the pages that use it.
 * Made by tools/parts.py from components.js in github.com/TheMightyTRex/design-system: change it there, not here. */
(() => {
  const S = window.SharedComponents;
  const { focusable, announcer, toast, copyText, sprite, escapeHtml, num, fold, andList, say, ownStatus, notice } = S.kit;

  /* More rows (28 November 2026): `.more` holds a switch `input[role="switch"][data-more-switch]` and any number
     of elements with `data-more`. They are hidden until the switch is on, the choice is kept for the session
     (`data-key`), and the change is said in words. Without script every row shows. */
  function setupMoreRows(root = document) {
    root.querySelectorAll(".more:not([data-ready])").forEach((box) => {
      box.dataset.ready = "";
      const sw = box.querySelector("[data-more-switch]");
      if (!sw) return;
      const key = box.dataset.key ? `more:${box.dataset.key}` : "";
      try { if (key && sessionStorage.getItem(key) === "on") sw.checked = true; } catch { /* kept only when the browser allows it */ }
      const say = window.SharedComponents.kit.ownStatus(box);
      const apply = (told) => {
        const rows = [...box.querySelectorAll("[data-more]")];
        rows.forEach((r) => { r.hidden = !sw.checked; });
        sw.setAttribute("aria-controls", rows.map((r) => r.id).filter(Boolean).join(" "));
        try { if (key) sessionStorage.setItem(key, sw.checked ? "on" : "off"); } catch { /* nothing to keep it in */ }
        if (told) say(sw.checked ? `More settings shown: ${rows.length}` : "More settings hidden");
      };
      sw.addEventListener("change", () => apply(true));
      apply(false);
    });
  }

  Object.assign(S, { setupMoreRows });
  S.addSetup(setupMoreRows);
})();
