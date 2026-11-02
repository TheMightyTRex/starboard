/*
 * Shared component behaviour (version 1, 2 November 2026). Plain JavaScript, no libraries.
 * Starboard can use it as it is; Storyarr has the same behaviour in its React components. Each part
 * below says what the behaviour must be, so both apps keep to it.
 */
(() => {
  const focusable =
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

  /* Menu: a button with aria-haspopup="menu" and aria-controls. Opens with focus on the first item;
     Arrow keys, Home and End move; Escape closes and returns focus to the button; a press outside
     closes it; choosing an item closes it. */
  function setupMenus(root = document) {
    root.querySelectorAll('[aria-haspopup="menu"][aria-controls]').forEach((button) => {
      if (button.dataset.ready) return;
      button.dataset.ready = "1";
      const menu = document.getElementById(button.getAttribute("aria-controls"));
      const items = () => [...menu.querySelectorAll('[role^="menuitem"]:not([disabled])')];
      const close = (refocus = true) => {
        menu.hidden = true;
        button.setAttribute("aria-expanded", "false");
        if (refocus) button.focus();
      };
      const open = () => {
        menu.hidden = false;
        // A menu inside a shelf that scrolls sideways is fixed over the page, under its button.
        if (menu.hasAttribute("data-fixed")) {
          const r = button.getBoundingClientRect();
          menu.style.top = `${r.bottom + 4}px`;
          menu.style.left = `${Math.max(8, Math.min(r.right - menu.offsetWidth, innerWidth - menu.offsetWidth - 8))}px`;
        }
        button.setAttribute("aria-expanded", "true");
        items()[0]?.focus();
      };
      menu.hidden = true;
      button.setAttribute("aria-expanded", "false");
      button.addEventListener("click", () => (menu.hidden ? open() : close()));
      button.addEventListener("keydown", (event) => {
        if (event.key === "ArrowDown" && menu.hidden) {
          event.preventDefault();
          open();
        }
      });
      menu.addEventListener("keydown", (event) => {
        const list = items();
        const at = list.indexOf(document.activeElement);
        const go = (index) => list[(index + list.length) % list.length]?.focus();
        if (event.key === "Escape") close();
        else if (event.key === "ArrowDown") go(at + 1);
        else if (event.key === "ArrowUp") go(at - 1);
        else if (event.key === "Home") go(0);
        else if (event.key === "End") go(list.length - 1);
        else if (event.key === "Tab") close(false);
        else return;
        event.preventDefault();
      });
      menu.addEventListener("click", (event) => {
        const item = event.target.closest('[role^="menuitem"]');
        if (!item) return;
        if (item.getAttribute("role") === "menuitemradio") {
          menu
            .querySelectorAll('[role="menuitemradio"]')
            .forEach((radio) => radio.setAttribute("aria-checked", String(radio === item)));
        }
        close();
      });
      document.addEventListener("pointerdown", (event) => {
        if (!menu.hidden && !menu.contains(event.target) && !button.contains(event.target))
          close(false);
      });
    });
  }

  /* Slide-out and phone menu: a layer opened by a button with data-opens="<id>". Focus moves to the
     close button; Tab stays inside; Escape, the close button and a press on the backdrop close it,
     and focus goes back to the button that opened it. The page behind cannot scroll. */
  function setupLayers(root = document) {
    root.querySelectorAll("[data-opens]").forEach((opener) => {
      if (opener.dataset.ready) return;
      opener.dataset.ready = "1";
      opener.addEventListener("click", () => openLayer(opener.dataset.opens, opener));
    });
  }
  function openLayer(id, opener, onClose) {
    const layer = typeof id === "string" ? document.getElementById(id) : id;
    if (!layer) return () => {};
    layer.closeLayer?.(false); // already open: start again
    layer.hidden = false;
    opener?.setAttribute("aria-expanded", "true");
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const panel = layer.querySelector("[role=dialog], nav, aside") || layer;
    (panel.querySelector("[data-closes]") || panel.querySelector(focusable))?.focus();
    const onKey = (event) => {
      if (event.key === "Escape") return close();
      if (event.key !== "Tab") return;
      const list = [...panel.querySelectorAll(focusable)].filter((el) => el.offsetParent);
      const first = list[0];
      const last = list[list.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    const onClick = (event) => {
      if (event.target.closest("[data-closes]") || event.target.classList.contains("side-panel-backdrop")) close();
    };
    function close(refocus = true) {
      layer.hidden = true;
      layer.closeLayer = null;
      document.body.style.overflow = overflow;
      opener?.setAttribute("aria-expanded", "false");
      layer.removeEventListener("keydown", onKey);
      layer.removeEventListener("click", onClick);
      if (refocus && opener?.isConnected) opener.focus();
      onClose?.();
    }
    layer.addEventListener("keydown", onKey);
    layer.addEventListener("click", onClick);
    layer.closeLayer = close;
    return close;
  }

  /* Dialog: a native <dialog> opened with showModal() by a button with data-dialog="<id>". The
     browser keeps focus inside; Escape closes; focus returns to the opener. */
  function setupDialogs(root = document) {
    root.querySelectorAll("[data-dialog]").forEach((opener) => {
      if (opener.dataset.ready) return;
      opener.dataset.ready = "1";
      const dialog = document.getElementById(opener.dataset.dialog);
      opener.addEventListener("click", () => dialog.showModal());
      dialog.addEventListener("close", () => opener.focus());
      dialog.querySelectorAll("[data-closes]").forEach((el) =>
        el.addEventListener("click", () => dialog.close()),
      );
    });
  }

  /* Phone menu sections fold open; the section you are in starts open. */
  function setupFolds(root = document) {
    root.querySelectorAll(".phone-menu__section > button[aria-controls]").forEach((button) => {
      if (button.dataset.ready) return;
      button.dataset.ready = "1";
      button.addEventListener("click", () => {
        const list = document.getElementById(button.getAttribute("aria-controls"));
        const open = button.getAttribute("aria-expanded") !== "true";
        button.setAttribute("aria-expanded", String(open));
        list.hidden = !open;
      });
    });
  }

  /* Filter chips toggle aria-pressed. Help buttons show and hide their text. */
  function setupToggles(root = document) {
    root.querySelectorAll(".filter-chip").forEach((chip) => {
      if (chip.dataset.ready) return;
      chip.dataset.ready = "1";
      chip.addEventListener("click", () =>
        chip.setAttribute("aria-pressed", String(chip.getAttribute("aria-pressed") !== "true")),
      );
    });
    root.querySelectorAll(".help > button[aria-controls]").forEach((button) => {
      if (button.dataset.ready) return;
      button.dataset.ready = "1";
      const text = document.getElementById(button.getAttribute("aria-controls"));
      text.hidden = true;
      button.addEventListener("click", () => {
        text.hidden = !text.hidden;
        button.setAttribute("aria-expanded", String(!text.hidden));
      });
      button.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
          text.hidden = true;
          button.setAttribute("aria-expanded", "false");
        }
      });
    });
  }

  /* Copy: copies data-copy and says so in the page's status region (role="status"). */
  function setupCopy(root = document) {
    root.querySelectorAll("[data-copy]").forEach((button) => {
      if (button.dataset.ready) return;
      button.dataset.ready = "1";
      button.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(button.dataset.copy);
          toast("Copied.");
        } catch {
          toast("Your browser did not allow copying. Select the text and copy it instead.");
        }
      });
    });
  }
  function toast(message) {
    let region = document.getElementById("toast");
    if (!region) {
      region = document.createElement("div");
      region.id = "toast";
      region.className = "toast";
      region.setAttribute("role", "status");
      document.body.append(region);
    }
    region.hidden = false;
    region.textContent = message;
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => (region.hidden = true), 4000);
  }

  /* Display settings: theme, text size and reading aids are classes on <html>. */
  function setupDisplay(root = document) {
    root.querySelectorAll("[data-display]").forEach((input) => {
      if (input.dataset.ready) return;
      input.dataset.ready = "1";
      input.addEventListener("change", () => {
        const html = document.documentElement;
        const kind = input.dataset.display;
        if (kind === "theme") html.dataset.theme = input.value;
        if (kind === "text")
          ["125", "150", "175"].forEach((size) =>
            html.classList.toggle(`pref-text-${size}`, input.value === size),
          );
        if (["contrast", "spacing", "motion", "underline"].includes(kind))
          html.classList.toggle(`pref-${kind}`, input.checked);
      });
    });
  }

  /* Shelf (UX-30): a .shelf-scroller with a .shelf-track and two .shelf-edge arrows. An edge shows
     only when there are more books that way; each arrow press moves one screen less one cover (a jump
     with reduced motion); tabbing to a book scrolls it fully into view. */
  function setupShelves(root = document) {
    root.querySelectorAll(".shelf-scroller").forEach((box) => {
      if (box.dataset.ready) return;
      box.dataset.ready = "1";
      const track = box.querySelector(".shelf-track");
      const start = box.querySelector(".shelf-edge--start");
      const end = box.querySelector(".shelf-edge--end");
      const update = () => {
        start.hidden = track.scrollLeft <= 2;
        end.hidden = track.scrollLeft + track.clientWidth >= track.scrollWidth - 2;
      };
      box.addEventListener("click", (event) => {
        const arrow = event.target.closest(".shelf-arrow");
        if (!arrow) return;
        const first = track.firstElementChild;
        const gap = parseFloat(getComputedStyle(track).columnGap) || 0;
        const step = Math.max(track.clientWidth - (first ? first.getBoundingClientRect().width + gap : 0), 100);
        const still = matchMedia("(prefers-reduced-motion: reduce)").matches || document.documentElement.classList.contains("pref-motion");
        track.scrollBy({ left: (arrow.closest(".shelf-edge--start") ? -1 : 1) * step, behavior: still ? "instant" : "smooth" });
      });
      track.addEventListener("focusin", (event) => event.target.closest(".shelf-track > *")?.scrollIntoView({ block: "nearest", inline: "nearest" }));
      track.addEventListener("scroll", update, { passive: true });
      new ResizeObserver(update).observe(track);
      update();
    });
  }

  function setup(root) {
    setupMenus(root);
    setupShelves(root);
    setupLayers(root);
    setupDialogs(root);
    setupFolds(root);
    setupToggles(root);
    setupCopy(root);
    setupDisplay(root);
  }
  window.SharedComponents = { setup, openLayer, toast };
  // An app that wires its own behaviour (Starboard's page scripts) loads this file with data-manual, or
  // sets window.SharedComponentsManual = true first, and calls setup() or openLayer() itself.
  const manual = window.SharedComponentsManual || document.currentScript?.hasAttribute("data-manual");
  if (!manual) document.addEventListener("DOMContentLoaded", () => setup());
})();
