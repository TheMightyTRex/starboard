/* popover: a part of the shared components. Load it after components.js, on the pages that use it.
 * Made by tools/parts.py from components.js in github.com/TheMightyTRex/design-system: change it there, not here. */
(() => {
  const S = window.SharedComponents;
  const { focusable, announcer, toast, copyText, sprite, escapeHtml, num, fold, andList, say, ownStatus } = S.kit;

  /* Popover: a button with data-popover and aria-controls opens a .popover (role="dialog", not modal, named by its
     heading). Focus moves to its heading, or to [data-autofocus]; Escape, a press outside, or Tab out of it closes
     it, and Escape returns focus to the button. It listens to the page only while it is open. Fires popover-open
     and popover-close on the popover. */
  function setupPopovers(root = document) {
    root.querySelectorAll("[data-popover][aria-controls]").forEach((button) => {
      if (button.dataset.ready) return;
      const pop = document.getElementById(button.getAttribute("aria-controls"));
      if (!pop) return;
      button.dataset.ready = "1";
      const outside = (event) => {
        if (!pop.contains(event.target) && !button.contains(event.target)) close(false);
      };
      function close(refocus = true) {
        if (pop.hidden) return;
        pop.hidden = true;
        button.setAttribute("aria-expanded", "false");
        document.removeEventListener("pointerdown", outside);
        if (refocus) button.focus();
        pop.dispatchEvent(new Event("popover-close"));
      }
      function open() {
        pop.hidden = false;
        button.setAttribute("aria-expanded", "true");
        // Keep it in the window: start at the button's left edge when it would run off the left, and the other way.
        pop.classList.remove("is-flipped-start", "is-flipped-end");
        const box = pop.getBoundingClientRect();
        if (getComputedStyle(pop).position !== "fixed") {
          if (box.left < 8) pop.classList.add("is-flipped-start");
          else if (box.right > innerWidth - 8) pop.classList.add("is-flipped-end");
        }
        document.addEventListener("pointerdown", outside);
        const head = pop.querySelector(".popover__head :is(h2, h3)");
        if (head && !head.hasAttribute("tabindex")) head.tabIndex = -1;
        (pop.querySelector("[data-autofocus]") || head || pop.querySelector(focusable))?.focus();
        pop.dispatchEvent(new Event("popover-open"));
      }
      pop.hidden = true;
      button.setAttribute("aria-expanded", "false");
      button.addEventListener("click", () => (pop.hidden ? open() : close()));
      pop.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        event.stopPropagation();
        close();
      });
      pop.addEventListener("focusout", (event) => {
        if (event.relatedTarget && !pop.contains(event.relatedTarget) && event.relatedTarget !== button) close(false);
      });
      pop.closePopover = close;
    });
  }

  Object.assign(S, { setupPopovers });
  S.addSetup(setupPopovers);
})();
