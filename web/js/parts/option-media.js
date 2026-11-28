/* option-media: a part of the shared components. Load it after components.js, on the pages that use it.
 * Made by tools/parts.py from components.js in github.com/TheMightyTRex/design-system: change it there, not here. */
(() => {
  const S = window.SharedComponents;
  const { focusable, announcer, toast, copyText, sprite, escapeHtml, num, fold, andList, say, ownStatus, notice } = S.kit;

  /* A media card inside an option card (28 November 2026): `.option-card--media[data-kind="video"|"audio"]` is a div with
     `.option-card__media` (a small picture, made once and kept), an input and its label, and a button
     `[data-preview-src="address"][data-title]` that reads "Play preview" plus the title in words hidden from the eye.
     Pressing it puts a player in the picture's place; pressing it again, or the end, puts the picture back. Nothing plays
     until it is pressed, one plays at a time, and a file that will not play says so in words. */
  function stopMedia(card) {
    const media = card.querySelector(".option-card__media");
    const player = media.querySelector("video, audio");
    if (player) { player.pause(); player.removeAttribute("src"); player.load(); player.remove(); }
    media.querySelectorAll("img").forEach((x) => { x.hidden = false; });
    card.removeAttribute("data-playing");
    const b = card.querySelector("[data-preview-src]");
    if (b) b.firstChild.textContent = "Play preview";
  }
  function setupOptionMedia(root = document) {
    root.querySelectorAll(".option-card--media:not([data-ready])").forEach((card) => {
      card.dataset.ready = "";
      const b = card.querySelector("[data-preview-src]");
      if (!b) return;
      const media = card.querySelector(".option-card__media");
      b.addEventListener("click", () => {
        if (card.hasAttribute("data-playing")) { stopMedia(card); return; }
        document.querySelectorAll(".option-card--media[data-playing]").forEach(stopMedia);
        card.querySelector(".option-card__error")?.remove();
        const audio = card.dataset.kind === "audio";
        const player = document.createElement(audio ? "audio" : "video");
        player.controls = true;
        player.preload = "none";
        player.setAttribute("aria-label", `Preview of ${b.dataset.title || "this file"}`);
        if (!audio) player.playsInline = true;
        player.addEventListener("ended", () => stopMedia(card));
        player.addEventListener("error", () => {
          stopMedia(card);
          const p = document.createElement("p");
          p.className = "option-card__error";
          p.setAttribute("role", "status");
          p.textContent = "The preview did not play. The file may be missing or in a form this browser cannot play.";
          card.append(p);
        });
        media.querySelectorAll("img").forEach((x) => { x.hidden = !audio; });
        media.append(player);
        player.src = b.dataset.previewSrc;
        card.dataset.playing = "";
        b.firstChild.textContent = "Stop preview";
        player.play().catch(() => { /* the player's own controls stay for the person to press */ });
      });
    });
  }

  Object.assign(S, { setupOptionMedia });
  S.addSetup(setupOptionMedia);
})();
