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
     browser keeps focus inside; Escape closes; focus returns to the button that opened it, even when
     several buttons open the same dialog. With data-close-outside (help, never a dialog with fields),
     a press on the dimmed page outside it closes it too. */
  function setupDialogs(root = document) {
    root.querySelectorAll("[data-dialog]").forEach((opener) => {
      if (opener.dataset.ready) return;
      opener.dataset.ready = "1";
      const dialog = document.getElementById(opener.dataset.dialog);
      if (!dialog) return;
      opener.addEventListener("click", () => {
        dialog.opener = opener;
        dialog.showModal();
      });
      if (dialog.dataset.ready) return;
      dialog.dataset.ready = "1";
      dialog.addEventListener("close", () => dialog.opener?.focus());
      dialog.querySelectorAll("[data-closes]").forEach((el) =>
        el.addEventListener("click", () => dialog.close()),
      );
      if (dialog.hasAttribute("data-close-outside")) {
        dialog.addEventListener("click", (event) => {
          if (event.target !== dialog) return;
          const box = dialog.getBoundingClientRect();
          const inside = event.clientX >= box.left && event.clientX <= box.right &&
            event.clientY >= box.top && event.clientY <= box.bottom;
          if (!inside) dialog.close();
        });
      }
    });
  }

  /* Search buttons: data-search-open on a button names the header search form (aria-controls). Where the
     box is visible (computers), the button moves focus into it. Where it is hidden (phones), the button
     opens it as a row under the header; Escape, or a press outside, closes it and returns focus. */
  function setupSearch(root = document) {
    root.querySelectorAll("[data-search-open]").forEach((button) => {
      if (button.dataset.ready) return;
      button.dataset.ready = "1";
      const form = document.getElementById(button.getAttribute("aria-controls"));
      const header = form?.closest(".site-header");
      const input = form?.querySelector("input");
      if (!form || !header || !input) return;
      const close = (refocus) => {
        if (!header.classList.contains("is-search-open")) return;
        header.classList.remove("is-search-open");
        document.querySelectorAll(`[data-search-open][aria-controls="${form.id}"]`).forEach((b) =>
          b.setAttribute("aria-expanded", "false"),
        );
        if (refocus) (form.searchOpener || button).focus();
      };
      button.addEventListener("click", () => {
        form.searchOpener = button;
        if (form.offsetParent === null) {
          header.classList.add("is-search-open");
          button.setAttribute("aria-expanded", "true");
        }
        input.focus();
      });
      if (!form.dataset.searchReady) {
        form.dataset.searchReady = "1";
        form.addEventListener("keydown", (event) => {
          if (event.key === "Escape") close(true);
        });
        document.addEventListener("pointerdown", (event) => {
          if (!form.contains(event.target) && !event.target.closest("[data-search-open]")) close(false);
        });
      }
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

  /* Copy: copies data-copy and says so in a toast (data-copied names it, such as "Address copied").
     Browsers only open the clipboard to https and localhost, and home servers are often plain http,
     so when it is refused, copy from a hidden text box instead. */
  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      const box = document.createElement("textarea");
      box.value = text;
      box.setAttribute("readonly", "");
      box.className = "visually-hidden";
      const back = document.activeElement;
      document.body.append(box);
      box.select();
      let done = false;
      try {
        done = document.execCommand("copy");
      } catch {
        done = false;
      }
      box.remove();
      back?.focus();
      return done;
    }
  }
  function setupCopy(root = document) {
    root.querySelectorAll("[data-copy]").forEach((button) => {
      if (button.dataset.ready) return;
      button.dataset.ready = "1";
      button.addEventListener("click", async () => {
        const text = button.dataset.copy;
        if (await copyText(text)) toast(button.dataset.copied || "Copied", { detail: button.dataset.copied ? text : undefined });
        else toast("Your browser did not allow copying", { tone: "warning", detail: `Select the text and copy it instead: ${text}` });
      });
    });
  }
  /* Toast (option C): toast("Follow saved", { detail, tone, action: { label, run } }).
     Tones: "success" (the default), "info", "warning" and "danger" (an error). Up to three stack in the
     corner, newest at the bottom; a new one pushes out the oldest that is not an error. Success and
     information stay 5 seconds (10 with an action), a warning 10, and an error until it is closed. Each
     waits while the pointer or keyboard focus is on it. Errors are read out at once (role="alert"), the
     rest politely (role="status"). Shortcuts: toast.error(message, options), toast.warning(...).
     Returns a function that closes it. Settings pages use savedNote() for success instead. */
  // Icons come from the page's own sprite (<use href="#i-name">) unless the app names a sprite file:
  // data-sprite="/icons/sprite.svg" on this script tag, or window.SharedComponentsSprite (Starboard sets it).
  const scriptSprite = document.currentScript?.dataset.sprite || "";
  const sprite = (name) =>
    `<svg class="i" aria-hidden="true" focusable="false"><use href="${window.SharedComponentsSprite || scriptSprite}#i-${name}"/></svg>`;
  const TONES = {
    success: { icon: "circle-check", time: 5000 },
    info: { icon: "info", time: 5000 },
    warning: { icon: "triangle-alert", time: 10000 },
    danger: { icon: "circle-alert", time: 0 },
  };
  function announcer(id, role) {
    let region = document.getElementById(id);
    if (!region) {
      region = document.createElement("div");
      region.id = id;
      region.className = "visually-hidden";
      region.setAttribute("role", role);
      document.body.append(region);
    }
    return region;
  }
  function toast(message, options = {}) {
    let stack = document.getElementById("toast-stack");
    if (!stack) {
      stack = document.createElement("div");
      stack.id = "toast-stack";
      stack.className = "toasts";
      document.body.append(stack);
    }
    const tone = TONES[options.tone] ? options.tone : "success";
    const item = document.createElement("div");
    item.className = "toast";
    item.dataset.tone = tone;
    item.innerHTML = `${sprite(TONES[tone].icon)}<span class="toast__text"><span class="toast__title"></span></span>`;
    item.querySelector(".toast__title").textContent = message;
    if (options.detail) {
      const detail = document.createElement("span");
      detail.className = "toast__detail";
      detail.textContent = options.detail;
      item.querySelector(".toast__text").append(detail);
    }
    if (options.action) {
      const action = document.createElement("button");
      action.type = "button";
      action.className = "btn btn--quiet btn--compact toast__action";
      action.textContent = options.action.label;
      action.addEventListener("click", () => {
        options.action.run?.();
        close();
      });
      item.append(action);
    }
    const shut = document.createElement("button");
    shut.type = "button";
    shut.className = "icon-btn icon-btn--bare toast__close";
    shut.setAttribute("aria-label", `Close message: ${message}`);
    shut.innerHTML = sprite("x");
    shut.addEventListener("click", () => close());
    item.append(shut);
    stack.append(item);
    while (stack.children.length > 3)
      (stack.querySelector('.toast:not([data-tone="danger"])') || stack.firstElementChild).remove();

    // Read out through a separate region, so the toast's own buttons stay out of the announcement.
    const region = announcer(tone === "danger" ? "toast-alert" : "toast-status", tone === "danger" ? "alert" : "status");
    region.textContent = "";
    setTimeout(() => (region.textContent = [message, options.detail].filter(Boolean).join(". ")), 50);

    let left = tone === "danger" ? 0 : Math.max(TONES[tone].time, options.action ? 10000 : 0);
    let started = Date.now();
    let timer = left ? setTimeout(close, left) : null;
    const pause = () => {
      if (!timer) return;
      clearTimeout(timer);
      timer = null;
      left -= Date.now() - started;
    };
    const resume = () => {
      if (!left || timer || item.matches(":hover, :focus-within")) return;
      started = Date.now();
      timer = setTimeout(close, Math.max(left, 2000));
    };
    item.addEventListener("pointerenter", pause);
    item.addEventListener("focusin", pause);
    item.addEventListener("pointerleave", resume);
    item.addEventListener("focusout", () => setTimeout(resume));
    function close() {
      clearTimeout(timer);
      const hadFocus = item.contains(document.activeElement);
      item.remove();
      if (hadFocus) document.querySelector("main")?.focus();
    }
    return close;
  }
  toast.error = (message, options = {}) => toast(message, { ...options, tone: "danger" });
  toast.warning = (message, options = {}) => toast(message, { ...options, tone: "warning" });

  /* Saved note (option D): savedNote(note) shows "Saved at 16:31" in a .saved-note beside the button that
     saved, and hides it at the next change in the same form or settings section. */
  function savedNote(note, text) {
    const now = new Date();
    const time = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
    note.setAttribute("role", "status");
    note.innerHTML = `${sprite("circle-check")}<span></span>`;
    note.querySelector("span").textContent = text || `Saved at ${time}`;
    note.hidden = false;
    const scope = note.closest("form, .settings-section") || document;
    const hide = () => {
      note.hidden = true;
      scope.removeEventListener("input", hide);
      scope.removeEventListener("change", hide);
    };
    scope.addEventListener("input", hide);
    scope.addEventListener("change", hide);
  }

  /* Display and accessibility: theme, text size and reading aids are classes on <html>. Inputs carry
     data-display="theme|text|motion|contrast|underline|spacing". Theme "system" follows the device.
     Reduce motion is a switch, or radios valued "device", "on" and "off" (the device setting still
     applies unless the choice is "on"). A form with data-display-save="<key>" keeps the choices in
     this browser and restores them; a [data-display-reset] button inside it, or one anywhere with
     data-display-reset="<key>", goes back to the defaults written in the markup. An app that saves to the person's account leaves data-display-save off. */
  function applyDisplay(input) {
    const html = document.documentElement;
    const kind = input.dataset.display;
    if (input.type === "radio" && !input.checked) return;
    if (kind === "theme") {
      if (input.value === "system") html.removeAttribute("data-theme");
      else html.dataset.theme = input.value;
    }
    if (kind === "text")
      ["125", "150", "175"].forEach((size) =>
        html.classList.toggle(`pref-text-${size}`, input.value === size),
      );
    if (kind === "motion" && input.type === "radio")
      html.classList.toggle("pref-motion", input.value === "on");
    else if (["contrast", "spacing", "motion", "underline"].includes(kind))
      html.classList.toggle(`pref-${kind}`, input.checked);
  }
  function setupDisplay(root = document) {
    root.querySelectorAll("[data-display]").forEach((input) => {
      if (input.dataset.ready) return;
      input.dataset.ready = "1";
      input.addEventListener("change", () => applyDisplay(input));
    });
    root.querySelectorAll("[data-display-save]").forEach((form) => {
      if (form.dataset.displayReady) return;
      form.dataset.displayReady = "1";
      const key = form.dataset.displaySave;
      const inputs = [...form.querySelectorAll("[data-display]")];
      const save = () => {
        const prefs = {};
        for (const el of inputs) {
          if (el.type === "radio" && el.checked) prefs[el.dataset.display] = el.value;
          if (el.type === "checkbox") prefs[el.dataset.display] = el.checked;
        }
        try {
          localStorage.setItem(key, JSON.stringify(prefs));
        } catch {}
      };
      let prefs = {};
      try {
        prefs = JSON.parse(localStorage.getItem(key) || "{}");
      } catch {}
      for (const el of inputs) {
        const value = prefs[el.dataset.display];
        if (value === undefined) continue;
        if (el.type === "radio") el.checked = el.value === value;
        if (el.type === "checkbox") el.checked = value;
      }
      inputs.forEach(applyDisplay);
      form.addEventListener("change", save);
      const reset =
        form.querySelector("[data-display-reset]") ||
        document.querySelector(`[data-display-reset="${key}"]`);
      reset?.addEventListener("click", () => {
        for (const el of inputs) el.checked = el.defaultChecked;
        try {
          localStorage.removeItem(key);
        } catch {}
        inputs.forEach(applyDisplay);
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
    setupSearch(root);
    setupDisplay(root);
  }
  window.SharedComponents = { setup, setupSearch, openLayer, toast, savedNote, copyText };
  // An app that wires its own behaviour (Starboard's page scripts) loads this file with data-manual, or
  // sets window.SharedComponentsManual = true first, and calls setup() or openLayer() itself.
  const manual = window.SharedComponentsManual || document.currentScript?.hasAttribute("data-manual");
  if (!manual) document.addEventListener("DOMContentLoaded", () => setup());
})();
