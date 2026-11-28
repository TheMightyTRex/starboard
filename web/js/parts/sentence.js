/* sentence: a part of the shared components. Load it after components.js, on the pages that use it.
 * Made by tools/parts.py from components.js in github.com/TheMightyTRex/design-system: change it there, not here. */
(() => {
  const S = window.SharedComponents;
  const { focusable, announcer, toast, copyText, sprite, escapeHtml, num, fold, andList, say, ownStatus, notice } = S.kit;

  /* Sentence (28 November 2026): `.sentence` holds `.sentence__text` with words and `select.sentence__select` (each named by
     aria-label, such as "Short title clips") and `.sentence__readback` (a polite status) with a `[data-readback]` span.
     After a change the readback says the whole sentence in plain words. It is never said when the page opens. */
  function setupSentences(root = document) {
    root.querySelectorAll(".sentence:not([data-ready])").forEach((box) => {
      box.dataset.ready = "";
      const text = box.querySelector(".sentence__text");
      const out = box.querySelector("[data-readback]");
      if (!text || !out) return;
      const say = () => {
        const parts = [...text.childNodes].map((n) => (n.nodeType === 3 ? n.textContent : n.matches?.("select") ? n.selectedOptions[0]?.textContent.trim() : n.querySelector?.("select")?.selectedOptions[0]?.textContent.trim() || "")).join("");
        return parts.replace(/\s+/g, " ").replace(/\s([,.])/g, "$1").trim();
      };
      out.textContent = say();
      text.addEventListener("change", () => { out.textContent = ""; setTimeout(() => (out.textContent = say()), 50); });
    });
  }

  Object.assign(S, { setupSentences });
  S.addSetup(setupSentences);
})();
