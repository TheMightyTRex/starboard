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
  // Search icon (owner, 12 November 2026: "add the search icon to all searches, make it the default"): every
  // input type="search" gets a Search button with the icon, at the right inside the box. In a form it submits the
  // form; a box that filters as you type gets a button that searches now (Enter's "search" event) and keeps focus.
  // Boxes added later (slide-outs, dialogs) get theirs too. A box can opt out with data-no-search-icon.
  const SEARCH_ICON = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" ' +
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>';
  function addSearchIcon(input) {
    if (input.dataset.searchIcon || input.hasAttribute("data-no-search-icon")) return;
    input.dataset.searchIcon = "1";
    const parent = input.parentElement;
    if (!parent || parent.querySelector(":scope > .search-field__btn")) return;  // it has one already (the header's)
    let box = parent;
    if (!parent.classList.contains("search-box") && !(parent.classList.contains("search-field") && parent.children.length <= 2)) {
      box = document.createElement("span");
      box.className = "search-box";
      parent.insertBefore(box, input);
      box.append(input);
    } else {
      box.classList.add("search-box");
    }
    const form = input.form;
    const words = input.getAttribute("aria-label") || (input.labels && input.labels[0] && input.labels[0].textContent.trim()) || "";
    const button = document.createElement("button");
    button.type = form ? "submit" : "button";
    button.className = "search-field__btn";
    button.innerHTML = SEARCH_ICON;
    const label = document.createElement("span");
    label.className = "visually-hidden";
    label.textContent = words && /^search/i.test(words) ? words : "Search";
    button.append(label);
    if (!form) {
      button.addEventListener("click", () => {
        input.focus();
        input.dispatchEvent(new Event("search", { bubbles: true }));
        input.dispatchEvent(new Event("input", { bubbles: true }));
      });
    }
    box.append(button);
  }
  let searchWatch = null;
  function setupSearchIcons(root = document) {
    root.querySelectorAll('input[type="search"]').forEach(addSearchIcon);
    if (searchWatch || !document.body) return;
    searchWatch = new MutationObserver((changes) => {
      for (const c of changes) {
        for (const n of c.addedNodes) {
          if (n.nodeType !== 1) continue;
          if (n.matches('input[type="search"]')) addSearchIcon(n);
          else if (n.querySelector) n.querySelectorAll('input[type="search"]').forEach(addSearchIcon);
        }
      }
    });
    searchWatch.observe(document.body, { childList: true, subtree: true });
  }

  function setupSearch(root = document) {
    setupSearchIcons(root);
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
        if (await copyText(text)) toast(button.dataset.copied || "Copied to the clipboard", { detail: button.dataset.copied ? text : undefined });
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
  // Words from an app or the page, made safe to put inside HTML.
  const escapeHtml = (text) =>
    String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
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
     data-display="theme|text|motion|contrast|underline|spacing". Light is the default (owner, 18 November 2026);
     theme "system" (Match device) sets data-theme to the device's choice and follows it when it changes.
     Reduce motion is a switch, or radios valued "device" (follows the device), "on" (always still) and
     "off" (full movement, even when the device asks for less). A form with data-display-save="<key>" keeps the choices in
     this browser and restores them; a [data-display-reset] button inside it, or one anywhere with
     data-display-reset="<key>", goes back to the defaults written in the markup. An app that saves to the person's account leaves data-display-save off. */
  /* Whether to keep still: Reduce motion On (pref-motion) always; Off (pref-motion-off) never, even when the device
     asks for less movement; Match device (neither class) follows the device (DASH-437). Every movement in the
     library asks this, never the media query alone. */
  const motionStill = () => {
    const html = document.documentElement;
    if (html.classList.contains("pref-motion")) return true;
    if (html.classList.contains("pref-motion-off")) return false;
    return Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)").matches);
  };
  /* The theme on <html>: light, dark, or the device's choice for "system". Exported as SharedComponents.applyTheme. */
  const darkQuery = window.matchMedia?.("(prefers-color-scheme: dark)");
  let followDevice = false;
  function applyTheme(value) {
    const html = document.documentElement;
    followDevice = value === "system";
    html.dataset.theme = followDevice ? (darkQuery?.matches ? "dark" : "light") : value === "dark" ? "dark" : "light";
  }
  darkQuery?.addEventListener?.("change", () => followDevice && applyTheme("system"));
  function applyDisplay(input) {
    const html = document.documentElement;
    const kind = input.dataset.display;
    if (input.type === "radio" && !input.checked) return;
    if (kind === "theme") applyTheme(input.value);
    if (kind === "text")
      ["125", "150", "175"].forEach((size) =>
        html.classList.toggle(`pref-text-${size}`, input.value === size),
      );
    if (kind === "motion" && input.type === "radio") {
      html.classList.toggle("pref-motion", input.value === "on");
      html.classList.toggle("pref-motion-off", input.value === "off");
    }
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
        const still = motionStill();
        track.scrollBy({ left: (arrow.closest(".shelf-edge--start") ? -1 : 1) * step, behavior: still ? "instant" : "smooth" });
      });
      track.addEventListener("focusin", (event) => event.target.closest(".shelf-track > *")?.scrollIntoView({ block: "nearest", inline: "nearest" }));
      track.addEventListener("scroll", update, { passive: true });
      new ResizeObserver(update).observe(track);
      update();
    });
  }

  /* A to Z jump list (.az-jump). Letters come from the sort title ("The Expanse" under E, "Émile" under E,
     "24" under #): azLetter(title). azJump(nav, letters, noun) draws # and A to Z into the nav, with the letters
     not in the Set shown but not choosable, named "M, no books" from the noun (or the nav's data-noun), or
     "M, none" without one. The row is one Tab stop: Arrow keys, Home and End move between
     the letters that have titles, Enter jumps. A jump scrolls to the heading (#letter-a) and moves focus to it.
     When the heading is not on the page yet (a wall that shows 40 at a time), the nav fires a cancelable
     "az-jump" event with detail.letter: the app shows more, then calls azGo(nav, letter). The letter in
     view gets aria-current="location". */
  const AZ = ["#", ..."ABCDEFGHIJKLMNOPQRSTUVWXYZ"];
  const ARTICLES = /^(the|a|an)\s+/i;
  function azLetter(title) {
    const first = String(title || "").trim().replace(ARTICLES, "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/^[^\p{L}\p{N}]+/u, "").charAt(0).toUpperCase();
    return first >= "A" && first <= "Z" ? first : "#";
  }
  const azId = (letter) => (letter === "#" ? "letter-num" : `letter-${letter.toLowerCase()}`);
  function azJump(nav, letters, noun = nav.dataset.noun) {
    const list = nav.querySelector("ol") || nav.appendChild(document.createElement("ol"));
    list.replaceChildren(...AZ.map((letter) => {
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.className = "az-jump__letter";
      a.textContent = letter;
      a.dataset.letter = letter;
      if (letters.has(letter)) a.href = `#${azId(letter)}`;
      else {
        a.setAttribute("aria-disabled", "true");
        a.setAttribute("role", "link");
        a.setAttribute("aria-label", `${letter === "#" ? "Numbers" : letter}, ${noun ? `no ${noun}` : "none"}`);
      }
      li.append(a);
      return li;
    }));
    setupAzJump(nav.parentNode || document);
  }
  function azGo(nav, letter) {
    const heading = document.getElementById(azId(letter));
    if (!heading) return false;
    const still = motionStill();
    if (!heading.hasAttribute("tabindex")) heading.setAttribute("tabindex", "-1");
    heading.scrollIntoView({ block: "start", behavior: still ? "instant" : "smooth" });
    heading.focus({ preventScroll: true });
    azCurrent(nav, letter);
    return true;
  }
  function azCurrent(nav, letter) {
    nav.querySelectorAll(".az-jump__letter").forEach((a) => {
      if ((a.dataset.letter || a.textContent.trim()) === letter) a.setAttribute("aria-current", "location");
      else a.removeAttribute("aria-current");
    });
  }
  function setupAzJump(root = document) {
    const navs = root.matches?.(".az-jump") ? [root] : root.querySelectorAll(".az-jump");
    navs.forEach((nav) => {
      const live = () => [...nav.querySelectorAll(".az-jump__letter[href]")];
      const rove = (target) => live().forEach((a) => a.setAttribute("tabindex", a === target ? "0" : "-1"));
      rove(nav.querySelector('.az-jump__letter[aria-current="location"][href]') || live()[0]);
      if (nav.dataset.ready) return;
      nav.dataset.ready = "1";
      nav.addEventListener("keydown", (event) => {
        const list = live();
        const at = list.indexOf(document.activeElement);
        if (at < 0) return;
        const go = { ArrowRight: at + 1, ArrowDown: at + 1, ArrowLeft: at - 1, ArrowUp: at - 1, Home: 0, End: list.length - 1 }[event.key];
        if (go === undefined) return;
        event.preventDefault();
        const next = list[Math.max(0, Math.min(list.length - 1, go))];
        rove(next);
        next.focus();
        next.scrollIntoView({ block: "nearest", inline: "nearest" });
      });
      nav.addEventListener("click", (event) => {
        const a = event.target.closest(".az-jump__letter");
        if (!a) return;
        event.preventDefault();
        if (!a.hasAttribute("href")) return;
        rove(a);
        const letter = a.dataset.letter || a.textContent.trim();
        if (azGo(nav, letter)) return;
        nav.dispatchEvent(new CustomEvent("az-jump", { bubbles: true, cancelable: true, detail: { letter } }));
      });
      // The letter in view: the last heading above the middle of the screen.
      let raf = 0;
      const track = () => {
        raf = 0;
        const line = nav.getBoundingClientRect().bottom + 8;
        const headings = [...document.querySelectorAll(".wall-letter[id^='letter-']")];
        let current = headings[0] || null; // at the top of a wall, its first letter
        headings.forEach((h) => {
          if (h.getBoundingClientRect().top <= line + 40) current = h;
        });
        const letter = current ? (current.id === "letter-num" ? "#" : current.id.slice(7).toUpperCase()) : null;
        if (letter && nav.querySelector('[aria-current="location"]')?.textContent.trim() !== letter) azCurrent(nav, letter);
      };
      addEventListener("scroll", () => { raf ||= requestAnimationFrame(track); }, { passive: true });
      raf = requestAnimationFrame(track);
    });
  }


  /* Sortable list (UX-51): rows put in order, such as qualities best first. Each row has Move up and Move down
     buttons (the keyboard and screen reader way, and the way on a phone), and a handle to drag with a mouse or a
     finger. A row can be a marker, such as "Stop upgrading here", moved the same way. Each move says where the row is
     now, keeps the keyboard on the button pressed, and sends a "sortable-change" event with the new order (each
     row's data-value) for the app to save. Buttons are never disabled: at an end they say so instead. */
  function sortableLabel(row) {
    return (row.querySelector(".sortable__label")?.textContent || row.textContent).trim();
  }
  function sortableMoved(list, row, said) {
    const rows = [...list.querySelectorAll(":scope > .sortable__row")];
    const where = rows.indexOf(row) + 1;
    announcer("sortable-status", "status").textContent = said || `${sortableLabel(row)}: ${where} of ${rows.length}`;
    list.dispatchEvent(new CustomEvent("sortable-change", { bubbles: true, detail: { order: rows.map((r) => r.dataset.value), moved: row.dataset.value } }));
  }
  function sortableMove(list, row, by) {
    const sibling = by < 0 ? row.previousElementSibling : row.nextElementSibling;
    if (!sibling || !sibling.classList.contains("sortable__row")) {
      announcer("sortable-status", "status").textContent = `${sortableLabel(row)} is already ${by < 0 ? "first" : "last"}`;
      return;
    }
    if (by < 0) sibling.before(row);
    else sibling.after(row);
    sortableMoved(list, row);
  }
  function setupSortables(root = document) {
    root.querySelectorAll(".sortable").forEach((list) => {
      if (list.dataset.ready) return;
      list.dataset.ready = "1";
      list.addEventListener("click", (event) => {
        const button = event.target.closest("[data-move]");
        if (!button || !list.contains(button)) return;
        sortableMove(list, button.closest(".sortable__row"), button.dataset.move === "up" ? -1 : 1);
        button.focus();
      });
      // Dragging by the handle: the row follows the pointer and settles between the rows either side.
      let dragging = null;
      list.addEventListener("pointerdown", (event) => {
        const handle = event.target.closest(".sortable__handle");
        if (!handle || !list.contains(handle) || event.button > 0) return;
        dragging = handle.closest(".sortable__row");
        dragging.classList.add("is-dragging");
        handle.setPointerCapture(event.pointerId);
        event.preventDefault();
      });
      list.addEventListener("pointermove", (event) => {
        if (!dragging) return;
        const rows = [...list.querySelectorAll(":scope > .sortable__row:not(.is-dragging)")];
        const after = rows.find((r) => { const box = r.getBoundingClientRect(); return event.clientY < box.top + box.height / 2; });
        if (after) { if (dragging.nextElementSibling !== after) after.before(dragging); }
        else if (list.lastElementChild !== dragging) list.append(dragging);
      });
      const drop = () => {
        if (!dragging) return;
        dragging.classList.remove("is-dragging");
        sortableMoved(list, dragging);
        dragging = null;
      };
      list.addEventListener("pointerup", drop);
      list.addEventListener("pointercancel", drop);
    });
  }

  /* Load more as the end comes into view (UX-52): infinite scroll that keeps a real Show more button.
     SharedComponents.loadMore(box, { load, items, noun, pageSize, auto, maxAuto, said }) wires one .load-more:
     - The button is always there and always works: keyboard and screen reader users, a setting that asks for the
       button, Reduce motion, a browser without IntersectionObserver, and a page whose script failed all use it.
       Pressing it moves focus to the first new item, so reading carries on there.
     - Otherwise one IntersectionObserver per list watches the box (no scroll handlers) and loads the next page as
       the box comes within 600px of the screen. Focus stays where it was.
     - After maxAuto pages in a row (3) it stops and waits for the button, so the footer stays in reach; the button
       starts a new run. reset() starts again (a new search, a filter or an A to Z jump).
     - While loading, a visible line says "Loading the next 40"; then a polite status says "40 more shown".
     load() fetches and adds the next page and returns how many it added (0 or nothing: nothing more, or busy).
     items: a selector or a function giving the list's items, to find the first new one after Show more.
     auto: true, false or a function read each time (such as the person's setting). Returns { more, reset, destroy }. */
  function loadMoreFocus(item) {
    if (!item) return;
    const to = item.matches("a[href], button") ? item : item.querySelector("a[href]") || item.querySelector("button") || item; // the title link first
    if (!to.matches("a[href], button, input, select, textarea, [tabindex]")) to.setAttribute("tabindex", "-1");
    to.focus();
  }
  function loadMore(box, options = {}) {
    if (!box) return null;
    box._loadMore?.destroy();
    const button = box.matches("button") ? box : box.querySelector("button");
    const holder = box.matches("button") ? box.parentNode : box;
    const size = options.pageSize || 40;
    const maxAuto = options.maxAuto ?? 3;
    const noun = options.noun ? ` ${options.noun}` : "";
    const said = options.said || ((n) => `${n.toLocaleString("en-GB")} more${noun} shown`);
    const items = () => [...(typeof options.items === "function" ? options.items() : options.items ? document.querySelectorAll(options.items) : [])];
    let line = holder?.querySelector(":scope > .load-more__status");
    if (!line && holder) {
      line = document.createElement("p");
      line.className = "load-more__status";
      line.hidden = true;
      if (button) button.before(line);
      else holder.append(line);
    }
    const show = (text) => {
      if (!line) return;
      line.textContent = text || "";
      line.hidden = !text;
    };
    const tell = (words) => {
      const region = announcer("load-more-status", "status");
      region.textContent = "";
      setTimeout(() => (region.textContent = words), 50);
    };
    let busy = false;
    let run = 0;
    let paused = false;
    let watch = null;
    const shown = () => box.isConnected && !box.hidden && !box.closest("[hidden]");
    const autoOn = () => (typeof options.auto === "function" ? options.auto() : options.auto !== false) && !motionStill();
    const look = () => {
      if (!watch) return;
      watch.unobserve(box);
      watch.observe(box);
    };

    async function more(byButton) {
      if (busy || !shown()) return 0;
      busy = true;
      const before = items().length;
      button?.setAttribute("aria-disabled", "true"); // not disabled, so focus stays on it
      show(`Loading the next ${size.toLocaleString("en-GB")}${noun}`);
      let n = 0;
      try {
        n = Number(await options.load?.()) || 0;
      } catch {
        busy = false;
        paused = true;
        button?.removeAttribute("aria-disabled");
        show(`The next ${size.toLocaleString("en-GB")}${noun} could not be loaded. Select Show more to try again.`);
        tell(`The next ${size.toLocaleString("en-GB")}${noun} could not be loaded`);
        return 0;
      }
      busy = false;
      button?.removeAttribute("aria-disabled");
      show("");
      if (!n) return 0;
      let words = said(n);
      if (byButton) {
        run = 0;
        paused = false;
        loadMoreFocus(items()[before]);
      } else {
        run += 1;
        if (run >= maxAuto && shown()) {
          paused = true;
          show("Paused here so you can reach the end of the page");
          words += ". Paused here so you can reach the end of the page";
        }
      }
      tell(words);
      if (!paused) look(); // still near the end (a short page, a tall screen): look again, with no scroll handler
      return n;
    }
    const onClick = (event) => {
      event.preventDefault();
      if (button.getAttribute("aria-disabled") !== "true") more(true);
    };
    button?.addEventListener("click", onClick);
    if ("IntersectionObserver" in window) {
      watch = new IntersectionObserver((seen) => {
        if (!paused && !busy && seen.some((s) => s.isIntersecting) && autoOn()) more(false);
      }, { rootMargin: options.rootMargin || "0px 0px 600px 0px" });
      watch.observe(box);
    }
    const handle = {
      more: () => more(true),
      reset() {
        run = 0;
        paused = false;
        show("");
        look();
      },
      destroy() {
        watch?.disconnect();
        button?.removeEventListener("click", onClick);
        delete box._loadMore;
      },
      get paused() {
        return paused;
      },
    };
    box._loadMore = handle;
    return handle;
  }

  /* Side tree (.side-tree): the folding side menu is details and summary, so it needs no script. This only makes
     sure the page you are on is shown: its area and group open, and the link in view inside a menu that scrolls
     (only the menu scrolls, never the page). */
  function setupSideTrees(root = document) {
    root.querySelectorAll(".side-tree").forEach((tree) => {
      if (tree.dataset.ready) return;
      tree.dataset.ready = "1";
      const here = tree.querySelector('a[aria-current="page"]');
      if (!here) return;
      for (let d = here.closest("details"); d; d = d.parentElement.closest("details")) d.open = true;
      const box = tree.closest("[data-side-scroll]") || tree;
      if (box.scrollHeight > box.clientHeight) box.scrollTop = here.offsetTop - box.offsetTop - box.clientHeight / 3;
    });
  }

  /* Problem solver (.solver[data-solver]): with no script, the whole tree of questions is a nested list of links.
     With it, one question at a time: each answer that leads to another question is a button, each that leads to an
     article is a link. The new question's heading takes the focus and a polite message says which question it is;
     Back returns to the last question with the focus on the answer chosen; Start again goes back to the first. */
  function setupSolvers(root = document) {
    root.querySelectorAll(".solver[data-solver]").forEach((solver) => {
      if (solver.dataset.ready) return;
      solver.dataset.ready = "1";
      const tree = solver.querySelector(".solver__node");
      if (!tree) return;
      const live = announcer("solver-announcer", "status");
      const step = document.createElement("div");
      step.className = "solver__step";
      const path = [];
      const show = (node, focusChoice) => {
        step.replaceChildren();
        const depth = path.length + 1;
        const progress = document.createElement("p");
        progress.className = "solver__progress";
        progress.textContent = `Question ${depth}`;
        const h = document.createElement("h2");
        h.tabIndex = -1;
        h.textContent = node.querySelector(":scope > .solver__question").textContent;
        const list = document.createElement("ul");
        list.className = "solver__options";
        let again = null;
        node.querySelectorAll(":scope > .solver__answers > li").forEach((li, i) => {
          const item = document.createElement("li");
          const link = li.querySelector(":scope > a");
          const next = li.querySelector(":scope > .solver__node");
          if (next) {
            const b = document.createElement("button");
            b.type = "button";
            b.className = "btn";
            b.textContent = li.querySelector(":scope > .solver__choice").textContent;
            b.addEventListener("click", () => { path.push([node, i]); show(next); });
            item.append(b);
            if (focusChoice === i) again = b;
          } else if (link) {
            const a = link.cloneNode(true);
            a.className = "btn";
            item.append(a);
            if (focusChoice === i) again = a;
          }
          list.append(item);
        });
        const nav = document.createElement("div");
        nav.className = "solver__nav";
        if (path.length) {
          const back = document.createElement("button");
          back.type = "button";
          back.className = "btn btn--quiet";
          back.textContent = "Back";
          back.addEventListener("click", () => { const [prev, i] = path.pop(); show(prev, i); });
          const restart = document.createElement("button");
          restart.type = "button";
          restart.className = "btn btn--quiet";
          restart.textContent = "Start again";
          restart.addEventListener("click", () => { path.length = 0; show(tree); });
          nav.append(back, restart);
        }
        step.append(progress, h, list, nav);
        if (focusChoice !== undefined && again) again.focus();
        else if (solver.classList.contains("is-live")) h.focus();
        if (solver.classList.contains("is-live")) {
          live.textContent = "";
          setTimeout(() => { live.textContent = `Question ${depth}: ${h.textContent}`; }, 50);
        }
      };
      tree.hidden = true;
      solver.append(step);
      show(tree);
      solver.classList.add("is-live");
    });
  }

  /* Header fit (DASH-437): the header gives way in steps when its items do not fit, instead of cutting menu items off
     or squeezing the search box to a few letters. Each step is tried only while something still does not fit:
       1. the level 1 menu shows icons only (.menu-tabs.is-compact; the names stay as tooltips and for screen readers);
       2. the search box becomes the Search button (.site-header.is-search-folded), opening it as a row under the header;
       3. Help and Display show their icons only (.is-actions-compact);
       4. the level 1 menu moves into the Menu button's slide-out (.is-crowded), as on phones.
     A level 2 menu (.site-header__tabs) shows icons only when its names do not fit. It measures again whenever
     anything in the header changes size: the window, the text size or spacing chosen in Display, a name arriving
     after the page loads, the font loading. One ResizeObserver, no timers. */
  const HEADER_STEPS = ["is-search-folded", "is-actions-compact", "is-crowded"];
  function fitHeader(header) {
    if (!header || header.classList.contains("is-search-open")) return;
    const bar = header.querySelector(".site-header__bar");
    const main = bar?.querySelector(":scope > .menu-tabs");
    const input = bar?.querySelector(".site-header__search input");
    const shown = (e) => !!e && e.getClientRects().length > 0;
    const overflows = (e) => shown(e) && e.scrollWidth > e.clientWidth + 1;
    const narrow = () => shown(input) && input.clientWidth < Math.max(150, 6 * parseFloat(getComputedStyle(input).fontSize));
    const fits = () => !overflows(main) && !overflows(bar) && !narrow();
    header.classList.remove(...HEADER_STEPS);
    header.querySelectorAll(".menu-tabs").forEach((nav) => nav.classList.remove("is-compact"));
    header.querySelectorAll(".site-header__tabs .menu-tabs").forEach((nav) => nav.classList.toggle("is-compact", overflows(nav)));
    const steps = [() => main?.classList.add("is-compact"), ...HEADER_STEPS.map((step) => () => header.classList.add(step))];
    for (const step of steps) {
      if (fits()) break;
      step();
    }
  }
  function setupHeaderFit(root = document) {
    root.querySelectorAll(".site-header").forEach((header) => {
      if (header.dataset.fitReady) return;
      header.dataset.fitReady = "1";
      let queued = false;
      const fit = () => {
        if (queued) return;
        queued = true;
        requestAnimationFrame(() => { queued = false; fitHeader(header); });
      };
      const watch = new ResizeObserver(fit);
      const bar = header.querySelector(".site-header__bar");
      if (bar) [bar, ...bar.children].forEach((e) => watch.observe(e));
      header.querySelectorAll(".menu-tabs a, .site-header__actions > *").forEach((e) => watch.observe(e));
      document.fonts?.ready.then(fit);
      fitHeader(header);
    });
  }

  /* ---- Added on 20 November 2026: log viewer, tabs, combobox, sparkline and gauge, pagination, error summary,
     secret field, schedule picker, tag input, popover and alerts, page banner, tooltip and command palette. Each
     part waits until it is on the page, and listens only while it is open. LIBRARY.md has the rules. ---- */
  const num = (n) => Number(n).toLocaleString("en-GB");
  const fold = (s) => String(s).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const andList = (list) => (list.length < 2 ? list.join("") : `${list.slice(0, -1).join(", ")} and ${list[list.length - 1]}`);
  /* Say something through the shared polite region (or the alert region when urgent). Never put a secret in it. */
  function say(text, urgent = false) {
    const region = announcer(urgent ? "toast-alert" : "toast-status", urgent ? "alert" : "status");
    region.textContent = "";
    setTimeout(() => (region.textContent = text), 50);
  }
  // A part's own polite region, inside it, so it is still heard inside a modal dialog.
  function ownStatus(box) {
    let region = box.querySelector(":scope > .visually-hidden[role='status']");
    if (!region) {
      region = document.createElement("p");
      region.className = "visually-hidden";
      region.setAttribute("role", "status");
      box.append(region);
    }
    return (text) => {
      region.textContent = "";
      setTimeout(() => (region.textContent = text), 50);
    };
  }

  /* Log viewer: SharedComponents.logView(box, { lines, maxLines, show, fileName }) returns { add(lines), clear() }.
     Lines are strings ("12:01:03 ERROR Disk 3 did not answer") or { time, level, text }; levels are error, warning,
     info and debug. It keeps the newest maxLines (10,000) and draws only the newest `show` (1,000) that match, with
     Show earlier lines for more. New lines are drawn by themselves, never the whole list again. Following keeps the
     newest line in view; scrolling up pauses it. New errors are said politely, and only while following. */
  const LOG_LEVELS = { error: "Error", warning: "Warning", info: "Info", debug: "Debug" };
  const LOG_WORDS = /^(fatal|crit\w*|err\w*)$/i;
  function logLine(line) {
    if (typeof line !== "string") {
      const level = LOG_LEVELS[line.level] ? line.level : "info";
      const text = String(line.text ?? "");
      return { time: String(line.time ?? ""), level, text, low: text.toLowerCase() };
    }
    const m = /^(\S+(?: \d\d:\d\d:\d\d\S*)?)\s+\[?([A-Za-z]+)\]?:?\s+(.*)$/.exec(line);
    let level = "info";
    if (m) {
      const word = m[2];
      if (LOG_WORDS.test(word)) level = "error";
      else if (/^warn/i.test(word)) level = "warning";
      else if (/^(debug|trace)$/i.test(word)) level = "debug";
      else if (!/^(info|notice)$/i.test(word)) return { time: "", level, text: line, low: line.toLowerCase() };
      return { time: m[1], level, text: m[3], low: m[3].toLowerCase() };
    }
    return { time: "", level, text: line, low: line.toLowerCase() };
  }
  function logView(box, options = {}) {
    if (box.logView) return box.logView;
    const max = options.maxLines || Number(box.dataset.maxLines) || 10000;
    const step = options.show || Number(box.dataset.show) || 1000;
    const scroller = box.querySelector(".log-view__scroll");
    const list = box.querySelector(".log-view__lines");
    const search = box.querySelector("[data-log-search]");
    const levels = [...box.querySelectorAll("[data-log-level]")];
    const follow = box.querySelector("[data-log-follow]");
    const wrap = box.querySelector("[data-log-wrap]");
    const download = box.querySelector("[data-log-download]");
    const countLine = box.querySelector("[data-log-count]");
    [...levels, follow, wrap].forEach((b) => b && (b.dataset.ready = "1")); // not the filter chips' own toggling
    const all = [];
    let term = "";
    let limit = step;
    let hits = 0;
    let drawn = 0;
    let paused = false;
    let fresh = [];
    let errTimer = null;
    let earlier = null;
    const pressed = (b) => !b || b.getAttribute("aria-pressed") === "true";
    const following = () => follow && pressed(follow) && !paused;
    let on = new Set(levels.length ? levels.filter(pressed).map((b) => b.dataset.logLevel) : Object.keys(LOG_LEVELS));
    const termOk = (l) => !term || l.low.includes(term);
    const shows = (l) => on.has(l.level) && termOk(l);
    function draw(l) {
      const li = document.createElement("li");
      li.className = "log-view__line";
      li.dataset.level = l.level;
      const time = document.createElement("span");
      time.className = "log-view__time";
      time.textContent = l.time;
      const level = document.createElement("span");
      level.className = "log-view__level";
      level.textContent = LOG_LEVELS[l.level];
      const text = document.createElement("span");
      text.className = "log-view__text";
      if (term) {
        let i = 0;
        for (let at = l.low.indexOf(term); at !== -1; at = l.low.indexOf(term, i)) {
          text.append(l.text.slice(i, at));
          const mark = document.createElement("mark");
          mark.className = "log-view__match";
          mark.textContent = l.text.slice(at, at + term.length);
          text.append(mark);
          i = at + term.length;
        }
        text.append(l.text.slice(i));
      } else text.textContent = l.text;
      li.append(time, level, text);
      l.node = li;
      return li;
    }
    function counts() {
      const n = { error: 0, warning: 0, info: 0, debug: 0 };
      for (const l of all) if (termOk(l)) n[l.level]++;
      for (const b of levels) {
        const c = b.querySelector("[data-count]");
        if (c) c.textContent = num(n[b.dataset.logLevel] || 0);
      }
    }
    function sayCount() {
      if (!countLine) return;
      const filtered = term || on.size < Object.keys(LOG_LEVELS).length;
      let words = filtered ? `${num(hits)} of ${num(all.length)} lines match` : `${num(all.length)} lines`;
      if (drawn < hits) words += `. Showing the newest ${num(drawn)}`;
      if (follow && !following()) words += ". Following is paused";
      countLine.textContent = `${words}.`;
    }
    function earlierRow() {
      if (drawn >= hits) {
        earlier?.remove();
        earlier = null;
        return;
      }
      if (!earlier) {
        earlier = document.createElement("li");
        earlier.className = "log-view__earlier";
        earlier.innerHTML = '<button class="btn" type="button"></button>';
        earlier.firstChild.addEventListener("click", () => {
          const before = scroller.scrollHeight;
          limit += step;
          render();
          scroller.scrollTop += scroller.scrollHeight - before;
          (earlier?.firstChild || scroller).focus();
        });
      }
      earlier.firstChild.textContent = `Show ${num(Math.min(step, hits - drawn))} earlier lines`;
      list.prepend(earlier);
    }
    function toEnd() {
      if (following()) scroller.scrollTop = scroller.scrollHeight;
    }
    function render() {
      on = new Set(levels.length ? levels.filter(pressed).map((b) => b.dataset.logLevel) : Object.keys(LOG_LEVELS));
      const matched = all.filter(shows);
      hits = matched.length;
      const from = Math.max(0, hits - limit);
      drawn = hits - from;
      const frag = document.createDocumentFragment();
      for (let i = from; i < hits; i++) frag.append(draw(matched[i]));
      if (!hits) {
        const empty = document.createElement("li");
        empty.className = "log-view__empty";
        empty.textContent = all.length ? "No lines match. Change the search or the levels." : "No lines yet.";
        frag.append(empty);
      }
      earlier = null;
      list.replaceChildren(frag);
      earlierRow();
      counts();
      sayCount();
      toEnd();
    }
    function add(lines) {
      const frag = document.createDocumentFragment();
      for (const raw of [].concat(lines)) {
        const l = logLine(raw);
        all.push(l);
        if (shows(l)) {
          hits++;
          drawn++;
          frag.append(draw(l));
        }
        if (l.level === "error" && following()) fresh.push(l);
      }
      if (all.length > max) {
        for (const old of all.splice(0, all.length - max)) {
          if (shows(old)) hits--;
          if (old.node?.isConnected) {
            old.node.remove();
            drawn--;
          }
        }
      }
      list.querySelector(".log-view__empty")?.remove();
      list.append(frag);
      while (drawn > limit) {
        const first = earlier ? earlier.nextElementSibling : list.firstElementChild;
        if (!first) break;
        first.remove();
        drawn--;
      }
      earlierRow();
      counts();
      sayCount();
      toEnd();
      if (fresh.length && !errTimer) {
        errTimer = setTimeout(() => {
          const n = fresh.length;
          const newest = fresh[n - 1].text.slice(0, 120);
          say(n === 1 ? `New error: ${newest}` : `${n} new errors. The newest: ${newest}`);
          fresh = [];
          errTimer = null;
        }, 1500);
      }
    }
    function setFollow(value) {
      paused = !value;
      follow?.setAttribute("aria-pressed", String(value));
      sayCount();
      toEnd();
    }
    let typing = null;
    search?.addEventListener("input", () => {
      clearTimeout(typing);
      typing = setTimeout(() => {
        term = search.value.trim().toLowerCase();
        limit = step;
        render();
        say(term ? `${num(hits)} ${hits === 1 ? "line matches" : "lines match"}` : `${num(hits)} lines`);
      }, 200);
    });
    for (const b of levels)
      b.addEventListener("click", () => {
        b.setAttribute("aria-pressed", String(!pressed(b)));
        limit = step;
        render();
      });
    follow?.addEventListener("click", () => setFollow(!following()));
    wrap?.addEventListener("click", () => {
      const now = !pressed(wrap);
      wrap.setAttribute("aria-pressed", String(now));
      box.toggleAttribute("data-wrap", now);
      toEnd();
    });
    // Only a move up by the person pauses following; text growing as fonts load or the box narrows does not.
    let lastTop = 0;
    scroller.addEventListener("scroll", () => {
      const atEnd = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight < 24;
      if (following() && !atEnd && scroller.scrollTop < lastTop - 4) setFollow(false);
      lastTop = scroller.scrollTop;
    }, { passive: true });
    if (window.ResizeObserver) new ResizeObserver(toEnd).observe(list);
    download?.addEventListener("click", () => {
      const text = all.map((l) => [l.time, LOG_LEVELS[l.level].toUpperCase(), l.text].filter(Boolean).join(" ")).join("\n");
      const url = URL.createObjectURL(new Blob([text + "\n"], { type: "text/plain" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = options.fileName || box.dataset.file || "log.txt";
      document.body.append(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
    if (follow) paused = !pressed(follow);
    box.toggleAttribute("data-wrap", pressed(wrap) && Boolean(wrap));
    render();
    if (options.lines) add(options.lines);
    box.logView = {
      add,
      clear() {
        all.length = 0;
        limit = step;
        render();
      },
      get size() {
        return all.length;
      },
    };
    return box.logView;
  }
  function setupLogViews(root = document) {
    root.querySelectorAll(".log-view[data-log-view]").forEach((box) => logView(box));
  }

  /* Tabs (ARIA tabs pattern): .tabs > [role=tablist] > [role=tab][aria-controls], and [role=tabpanel]s. One Tab stop
     for the list; Left and Right move round, Home and End go to the ends. Moving chooses the tab (automatic), or
     with data-activation="manual" Enter or Space chooses it, for panels that take a moment to fill. A link to a
     panel's id opens its tab. Fires tabs-change with { tab, panel }. */
  function setupTabs(root = document) {
    root.querySelectorAll(".tabs").forEach((box) => {
      if (box.dataset.ready) return;
      const list = box.querySelector('[role="tablist"]');
      const tabs = list ? [...list.querySelectorAll('[role="tab"]')] : [];
      if (!tabs.length) return;
      box.dataset.ready = "1";
      const manual = box.dataset.activation === "manual";
      const panelOf = (tab) => document.getElementById(tab.getAttribute("aria-controls"));
      const choose = (tab, focus = true) => {
        for (const t of tabs) {
          const chosen = t === tab;
          t.setAttribute("aria-selected", String(chosen));
          t.tabIndex = chosen ? 0 : -1;
          const panel = panelOf(t);
          if (panel) panel.hidden = !chosen;
        }
        if (focus) tab.focus();
        box.dispatchEvent(new CustomEvent("tabs-change", { detail: { tab, panel: panelOf(tab) } }));
      };
      const linked = location.hash && tabs.find((t) => `#${t.getAttribute("aria-controls")}` === location.hash);
      choose(linked || tabs.find((t) => t.getAttribute("aria-selected") === "true") || tabs[0], false);
      list.addEventListener("click", (event) => {
        const tab = event.target.closest('[role="tab"]');
        if (tab) choose(tab);
      });
      list.addEventListener("keydown", (event) => {
        const at = tabs.indexOf(document.activeElement);
        if (at < 0) return;
        const keys = { ArrowRight: at + 1, ArrowLeft: at - 1, Home: 0, End: tabs.length - 1 };
        if (manual && (event.key === "Enter" || event.key === " ")) {
          event.preventDefault();
          choose(tabs[at]);
          return;
        }
        if (!(event.key in keys)) return;
        event.preventDefault();
        const tab = tabs[(keys[event.key] + tabs.length) % tabs.length];
        if (manual) tab.focus();
        else choose(tab);
      });
    });
  }

  /* Combobox (ARIA 1.2, a list that filters as you enter text, without choosing by itself): SharedComponents.combobox
     (box, { options, onChoose, always }) or .combobox[data-combobox] with role="option" items in the markup. Focus
     stays in the box: Down and Up move through the list (Down opens it, Alt and Down only opens it), Enter chooses,
     Escape closes the list and then clears the box, Tab leaves. The number found is said politely, and "No <noun>
     match" shows when nothing does. On leaving, an exact name is chosen; anything else goes back to the choice.
     Fires combobox-change with { value, label }. Returns { setOptions, open, close, input }. */
  function combobox(box, options = {}) {
    if (box.combobox) return box.combobox;
    const input = box.querySelector('[role="combobox"]');
    const popup = box.querySelector(".combobox__popup");
    const list = box.querySelector('[role="listbox"]');
    const none = box.querySelector(".combobox__none");
    const toggle = box.querySelector(".combobox__toggle");
    const hidden = box.querySelector('input[type="hidden"]');
    const noun = box.dataset.noun || "options";
    const one = box.dataset.nounOne || "option";
    const always = options.always || box.hasAttribute("data-always-open");
    const tell = ownStatus(box);
    let items = options.options || [...list.querySelectorAll('[role="option"]')].map((o) => ({
      value: o.dataset.value ?? o.textContent.trim(),
      label: o.textContent.trim(),
      hint: o.dataset.hint || "",
      keywords: o.dataset.keywords || o.dataset.hint || "", // a name in its own language matches too
    }));
    let chosen = items.find((i) => hidden && i.value === hidden.value) || items.find((i) => i.label === input.value) || null;
    let shown = [];
    let active = -1;
    let timer = null;
    const isOpen = () => !popup.hidden;
    function draw() {
      const q = fold(input.value.trim());
      const words = (i) => fold(`${i.label} ${i.keywords || ""}`);
      shown = q && !(chosen && input.value === chosen.label) ? items.filter((i) => words(i).includes(q)) : items.slice();
      const frag = document.createDocumentFragment();
      shown.slice(0, options.max || 200).forEach((item, n) => {
        const li = document.createElement("li");
        li.id = `${list.id}-${n}`;
        li.className = "combobox__option";
        li.setAttribute("role", "option");
        li.setAttribute("aria-selected", String(item === chosen));
        const at = q ? fold(item.label).indexOf(q) : -1;
        const label = document.createElement("span");
        if (at >= 0 && !(chosen && input.value === chosen.label)) {
          const mark = document.createElement("mark");
          mark.textContent = item.label.slice(at, at + q.length);
          label.append(item.label.slice(0, at), mark, item.label.slice(at + q.length));
        } else label.textContent = item.label;
        li.append(label);
        if (item.hint) {
          const hint = document.createElement("span");
          hint.className = "combobox__hint";
          hint.textContent = item.hint;
          li.append(hint);
        }
        frag.append(li);
      });
      shown = shown.slice(0, options.max || 200);
      list.replaceChildren(frag);
      list.hidden = !shown.length;
      if (none) {
        none.hidden = shown.length > 0;
        none.textContent = `No ${noun} match "${input.value.trim()}"`;
      }
      active = -1;
      input.removeAttribute("aria-activedescendant");
    }
    function open() {
      if (isOpen()) return;
      popup.hidden = false;
      input.setAttribute("aria-expanded", "true");
    }
    function close() {
      if (always) return;
      popup.hidden = true;
      input.setAttribute("aria-expanded", "false");
      active = -1;
      input.removeAttribute("aria-activedescendant");
    }
    function move(to) {
      if (!shown.length) return;
      active = (to + shown.length) % shown.length;
      [...list.children].forEach((o, n) => o.classList.toggle("is-active", n === active));
      const option = list.children[active];
      input.setAttribute("aria-activedescendant", option.id);
      option.scrollIntoView({ block: "nearest" });
    }
    function choose(n) {
      const item = shown[n];
      if (!item) return;
      chosen = item;
      if (options.onChoose) options.onChoose(item);
      else {
        input.value = item.label;
        if (hidden) hidden.value = item.value;
      }
      close();
      box.dispatchEvent(new CustomEvent("combobox-change", { bubbles: true, detail: item }));
    }
    input.addEventListener("input", () => {
      draw();
      open();
      clearTimeout(timer);
      timer = setTimeout(() => tell(shown.length ? `${num(shown.length)} ${shown.length === 1 ? one : noun} found` : none?.textContent || `No ${noun} match`), 500);
    });
    input.addEventListener("keydown", (event) => {
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        if (!isOpen()) {
          draw();
          open();
          if (event.altKey) return;
        }
        move(event.key === "ArrowDown" ? active + 1 : active < 0 ? shown.length - 1 : active - 1);
      } else if (event.key === "Enter") {
        if (isOpen() && active >= 0) {
          event.preventDefault();
          choose(active);
        } else if (always && shown.length) {
          event.preventDefault();
          choose(0);
        }
      } else if (event.key === "Escape") {
        if (always) return; // the dialog it sits in closes
        event.preventDefault();
        event.stopPropagation();
        if (isOpen()) close();
        else {
          input.value = "";
          chosen = null;
          if (hidden) hidden.value = "";
        }
      } else if (event.key === "Tab") close();
    });
    list.addEventListener("mousedown", (event) => event.preventDefault()); // keep the focus in the box
    list.addEventListener("click", (event) => {
      const option = event.target.closest('[role="option"]');
      if (option) choose([...list.children].indexOf(option));
    });
    toggle?.addEventListener("click", () => {
      if (isOpen()) close();
      else {
        draw();
        open();
      }
      input.focus();
    });
    box.addEventListener("focusout", (event) => {
      if (always || box.contains(event.relatedTarget)) return;
      close();
      const exact = items.find((i) => fold(i.label) === fold(input.value.trim()));
      if (exact && exact !== chosen) {
        shown = [exact];
        choose(0);
      } else if (!input.value.trim()) {
        chosen = null;
        if (hidden) hidden.value = "";
      } else if (!exact) input.value = chosen ? chosen.label : "";
    });
    draw();
    if (always) open();
    else close();
    box.combobox = {
      input,
      open,
      close,
      setOptions(next) {
        items = next;
        draw();
      },
    };
    return box.combobox;
  }
  function setupComboboxes(root = document) {
    root.querySelectorAll(".combobox[data-combobox]").forEach((box) => combobox(box));
  }

  /* Sparkline: sparkline(svg, values, { period, unit, min, max }) draws a small line in a stat tile and writes the
     numbers in words into the tile's .stat__trend ("Last hour: 18% to 42%, lowest 12%, highest 61%"), which is what
     screen readers read; the drawing is hidden from them. Markup alone works too: data-values="18,22,…" on the svg.
     Gauge: gauge(el, value) sets a .gauge's arc and its words; data-max, data-unit, and data-warn and data-danger
     (the levels where its tone changes) on the element. */
  function sparkline(svg, values, options = {}) {
    const v = values.map(Number).filter(Number.isFinite);
    if (v.length < 2) return "";
    const unit = options.unit ?? svg.dataset.unit ?? "";
    const lo = Math.min(...v);
    const hi = Math.max(...v);
    const min = options.min ?? (svg.dataset.min !== undefined ? Number(svg.dataset.min) : lo);
    const max = options.max ?? (svg.dataset.max !== undefined ? Number(svg.dataset.max) : hi);
    const span = max - min || 1;
    const w = 100;
    const h = 32;
    const pts = v.map((x, i) => `${((i / (v.length - 1)) * w).toFixed(2)} ${(h - 2 - ((x - min) / span) * (h - 4)).toFixed(2)}`);
    svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
    svg.setAttribute("preserveAspectRatio", "none");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    svg.innerHTML = `<path class="sparkline__area" d="M0 ${h} L${pts.join(" L")} L${w} ${h}Z"/><polyline class="sparkline__line" points="${pts.join(" ")}"/>`;
    const say1 = (x) => `${num(Number(x.toFixed(1)))}${unit}`;
    const words = `${options.period || svg.dataset.period || "Recently"}: ${say1(v[0])} to ${say1(v[v.length - 1])}, lowest ${say1(lo)}, highest ${say1(hi)}`;
    const out = options.words || svg.closest(".stat, .chart, figure")?.querySelector(".stat__trend");
    if (out) out.textContent = words;
    return words;
  }
  function gauge(el, value, options = {}) {
    const max = options.max ?? Number(el.dataset.max || 100);
    const unit = options.unit ?? el.dataset.unit ?? "%";
    const pct = Math.max(0, Math.min(100, (Number(value) / max) * 100));
    el.querySelector(".gauge__fill")?.setAttribute("stroke-dasharray", `${pct.toFixed(1)} 100`);
    const words = el.querySelector(".gauge__value");
    if (words) words.textContent = options.text ?? `${num(Math.round(Number(value)))}${unit}`;
    const warn = el.dataset.warn !== undefined ? Number(el.dataset.warn) : Infinity;
    const danger = el.dataset.danger !== undefined ? Number(el.dataset.danger) : Infinity;
    if (warn !== Infinity || danger !== Infinity) {
      if (value >= danger) el.dataset.tone = "danger";
      else if (value >= warn) el.dataset.tone = "warning";
      else delete el.dataset.tone;
    }
  }
  function setupCharts(root = document) {
    root.querySelectorAll("svg.sparkline[data-values]").forEach((svg) => {
      if (svg.dataset.ready) return;
      svg.dataset.ready = "1";
      sparkline(svg, svg.dataset.values.split(","));
    });
    root.querySelectorAll(".gauge[data-value]").forEach((el) => {
      if (el.dataset.ready) return;
      el.dataset.ready = "1";
      gauge(el, Number(el.dataset.value));
    });
  }

  /* Pagination: pagination(nav, { page, pageSize, total, noun, sizes, href, onPage, onSize, focus }) draws the
     links and "Showing 21 to 40 of 312". With href(page) each is a real link; with onPage(page) the page changes in
     place, says the new place politely and moves focus to `focus` (the table or its heading) or the current page. */
  function pagination(nav, o) {
    const sizes = o.sizes || [20, 50, 100];
    const last = Math.max(1, Math.ceil(o.total / o.pageSize));
    const page = Math.min(Math.max(1, o.page), last);
    const from = o.total ? (page - 1) * o.pageSize + 1 : 0;
    const to = Math.min(o.total, page * o.pageSize);
    const summary = `Showing ${num(from)} to ${num(to)} of ${num(o.total)}${o.noun ? ` ${escapeHtml(o.noun)}` : ""}`;
    const want = [...new Set([1, page - 1, page, page + 1, last])].filter((p) => p >= 1 && p <= last).sort((a, b) => a - b);
    const pages = [];
    want.forEach((p, i) => {
      if (i && p - want[i - 1] === 2) pages.push(p - 1);
      else if (i && p - want[i - 1] > 2) pages.push(0);
      pages.push(p);
    });
    const link = (p, inner, extra = "") =>
      `<a class="pagination__link" href="${escapeHtml(o.href ? o.href(p) : `#page-${p}`)}" data-page="${p}"${extra}>${inner}</a>`;
    const id = nav.id || (nav.id = `pages-${Math.random().toString(36).slice(2, 8)}`);
    let html = `<p class="pagination__summary">${summary}</p><ul class="pagination__pages">`;
    if (page > 1) html += `<li>${link(page - 1, `${sprite("chevron-left")}Previous<span class="visually-hidden"> page</span>`, ' rel="prev"')}</li>`;
    for (const p of pages)
      html += p
        ? `<li${p !== page && p !== 1 && p !== last ? ' class="pagination__near"' : ""}>${link(p, num(p), p === page ? ` aria-current="page" aria-label="Page ${p}, current page"` : ` aria-label="Page ${p}"`)}</li>`
        : '<li class="pagination__gap" aria-hidden="true">…</li>';
    if (page < last) html += `<li>${link(page + 1, `Next<span class="visually-hidden"> page</span>${sprite("chevron-right")}`, ' rel="next"')}</li>`;
    html += "</ul>";
    if (o.onSize)
      html += `<div class="pagination__size"><label for="${id}-size">Rows per page</label><select class="select" id="${id}-size">${sizes
        .map((s) => `<option${s === o.pageSize ? " selected" : ""}>${s}</option>`)
        .join("")}</select></div>`;
    nav.innerHTML = html;
    if (o.onPage)
      nav.querySelectorAll("[data-page]").forEach((a) =>
        a.addEventListener("click", (event) => {
          event.preventDefault();
          const next = Number(a.dataset.page);
          o.onPage(next);
          pagination(nav, { ...o, page: next });
          (o.focus || nav.querySelector('[aria-current="page"]'))?.focus();
          say(nav.querySelector(".pagination__summary").textContent);
        }),
      );
    nav.querySelector("select")?.addEventListener("change", (event) => {
      const size = Number(event.target.value);
      const first = Math.floor((from - 1) / size) + 1;
      o.onSize(size, first);
      pagination(nav, { ...o, pageSize: size, page: first });
      nav.querySelector("select").focus();
      say(nav.querySelector(".pagination__summary").textContent);
    });
    return { page, last, from, to, summary };
  }

  /* Error summary (after GOV.UK) and field errors. showErrors(form, [{ field: "id", message }]) writes each field's
     .field-error ("Error: " for screen readers), ties it with aria-describedby, sets aria-invalid, fills the form's
     .error-summary with a link to each field, shows it, moves focus to it and puts "Error: " in the page title.
     clearErrors(form) undoes it. A link in the summary moves focus to its field with the label in view. */
  function setFieldError(control, message) {
    const id = `${control.id}-error`;
    let error = document.getElementById(id);
    if (!message) {
      error?.remove();
      control.removeAttribute("aria-invalid");
      const left = (control.getAttribute("aria-describedby") || "").split(" ").filter((x) => x && x !== id);
      if (left.length) control.setAttribute("aria-describedby", left.join(" "));
      else control.removeAttribute("aria-describedby");
      return;
    }
    if (!error) {
      error = document.createElement("p");
      error.className = "field-error";
      error.id = id;
      const field = control.closest(".field, fieldset") || control.parentElement;
      let before = control;
      while (before.parentElement && before.parentElement !== field) before = before.parentElement;
      field.insertBefore(error, before);
    }
    error.innerHTML = `${sprite("circle-alert")}<span><span class="visually-hidden">Error: </span><span></span></span>`;
    error.querySelector("span > span:last-child").textContent = message;
    control.setAttribute("aria-invalid", "true");
    const ids = (control.getAttribute("aria-describedby") || "").split(" ").filter(Boolean);
    if (!ids.includes(id)) control.setAttribute("aria-describedby", [...ids, id].join(" "));
  }
  function clearErrors(form) {
    form.querySelectorAll('[aria-invalid="true"]').forEach((c) => c.id && setFieldError(c, ""));
    const summary = form.querySelector(".error-summary");
    if (summary) summary.hidden = true;
    document.title = document.title.replace(/^Error: /, "");
  }
  function showErrors(form, errors, options = {}) {
    clearErrors(form);
    if (!errors.length) return;
    let summary = form.querySelector(".error-summary");
    if (!summary) {
      summary = document.createElement("div");
      summary.className = "error-summary";
      summary.id = `${form.id || "form"}-errors`;
      form.prepend(summary);
    }
    summary.setAttribute("role", "alert");
    summary.tabIndex = -1;
    summary.setAttribute("aria-labelledby", `${summary.id}-h`);
    summary.innerHTML = `<h2 class="error-summary__title" id="${summary.id}-h">${sprite("circle-alert")}<span></span></h2><ul class="error-summary__list"></ul>`;
    summary.querySelector("h2 span").textContent = options.title || "There is a problem";
    const list = summary.querySelector("ul");
    for (const { field, message } of errors) {
      const control = document.getElementById(field);
      if (control) setFieldError(control, message);
      const li = document.createElement("li");
      li.append(Object.assign(document.createElement("a"), { href: `#${field}` }));
      li.firstChild.textContent = message;
      list.append(li);
    }
    summary.hidden = false;
    if (!document.title.startsWith("Error: ")) document.title = `Error: ${document.title}`;
    summary.focus();
    setupErrorSummaries(summary.parentElement);
  }
  function setupErrorSummaries(root = document) {
    if (document.documentElement.dataset.errorLinks) return;
    document.documentElement.dataset.errorLinks = "1";
    document.addEventListener("click", (event) => {
      const a = event.target.closest('.error-summary a[href^="#"]');
      if (!a) return;
      const control = document.getElementById(a.getAttribute("href").slice(1));
      if (!control) return;
      event.preventDefault();
      const legend = control.closest("fieldset")?.querySelector("legend");
      const label = (control.id && document.querySelector(`label[for="${control.id}"]`)) || legend || control;
      label.scrollIntoView({ block: "start" });
      control.focus({ preventScroll: true });
    });
  }

  /* Secret field: .secret-field[data-secret] with the input (type="password", readonly), and buttons with
     data-secret-show, data-secret-copy and data-secret-replace. data-name names it ("API key"). Show and Hide say the
     new state politely; Copy confirms in a toast without the value; Replace empties the box to enter a new one, with
     Save and Cancel (Enter and Escape), and fires secret-change with { value } for the app to save. The value is
     never written to an attribute, a message, the page title or the console. Set it with input.value, not in the
     markup, so it is not in the page's source. */
  function setupSecrets(root = document) {
    root.querySelectorAll(".secret-field[data-secret]").forEach((box) => {
      if (box.dataset.ready) return;
      box.dataset.ready = "1";
      const input = box.querySelector("input");
      const name = box.dataset.name || "secret";
      const show = box.querySelector("[data-secret-show]");
      const copy = box.querySelector("[data-secret-copy]");
      const replace = box.querySelector("[data-secret-replace]");
      let kept = "";
      let cancel = null;
      const label = (button, words, icon) => {
        // Built from nodes: the name comes from data-name, so it never goes into HTML (CodeQL, 20 November 2026).
        const hidden = Object.assign(document.createElement("span"), { className: "visually-hidden", textContent: ` ${name}` });
        button.innerHTML = sprite(icon);
        button.append(words, hidden);
      };
      const setShown = (shown, tell = true) => {
        input.type = shown ? "text" : "password";
        show?.setAttribute("aria-pressed", String(shown));
        if (show) label(show, shown ? "Hide" : "Show", shown ? "eye-off" : "eye");
        if (tell) say(`${name} ${shown ? "shown" : "hidden"}`);
      };
      const editing = (on) => {
        input.readOnly = !on;
        if (copy) copy.hidden = on;
        if (on) {
          label(replace, "Save", "check");
          replace.classList.add("btn--primary");
          cancel = document.createElement("button");
          cancel.type = "button";
          cancel.className = "btn btn--quiet";
          cancel.textContent = "Cancel";
          cancel.addEventListener("click", () => stop(false));
          replace.after(cancel);
        } else {
          label(replace, "Replace", "pencil");
          replace.classList.remove("btn--primary");
          cancel?.remove();
          cancel = null;
        }
      };
      const stop = (save) => {
        if (save && !input.value.trim()) {
          setFieldError(input, `Enter the new ${name}`);
          input.focus();
          return;
        }
        setFieldError(input, "");
        if (save) {
          const ok = box.dispatchEvent(new CustomEvent("secret-change", { cancelable: true, detail: { value: input.value } }));
          if (ok) say(`${name} replaced`);
        } else {
          input.value = kept;
          say(`${name} not changed`);
        }
        kept = "";
        editing(false);
        setShown(false, false);
        replace.focus();
      };
      if (show) setShown(false, false);
      show?.addEventListener("click", () => setShown(input.type === "password"));
      copy?.addEventListener("click", async () => {
        if (await copyText(input.value)) toast(`${name} copied`);
        else toast(`Your browser did not allow copying`, { tone: "warning", detail: `Select Show, then select the ${name} and copy it.` });
      });
      replace?.addEventListener("click", () => {
        if (!input.readOnly) return stop(true);
        kept = input.value;
        input.value = "";
        editing(true);
        input.focus();
        say(`Enter the new ${name}, then select Save`);
      });
      input.addEventListener("keydown", (event) => {
        if (input.readOnly) return;
        if (event.key === "Enter") {
          event.preventDefault();
          stop(true);
        } else if (event.key === "Escape") {
          event.preventDefault();
          stop(false);
        }
      });
    });
  }

  /* Schedule picker: .schedule[data-schedule] with [data-schedule-repeat] (day, week or hour), [data-schedule-time],
     [data-schedule-minute], day checkboxes valued 0 (Sunday) to 6 in [data-schedule-days], and [data-schedule-words]
     and [data-schedule-next] in a polite status. It reads the choice back in words ("Every weekday at 07:00", "Next:
     tomorrow at 07:00") and fires schedule-change with { repeat, days, time, minute, words }. scheduleWords(value) and
     nextRun(value) are exported for an app's own lists. */
  const DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  function scheduleWords({ repeat, days = [], time = "", minute = 0 }) {
    if (repeat === "hour") return Number(minute) ? `Every hour at ${Number(minute)} minute${Number(minute) === 1 ? "" : "s"} past` : "Every hour, on the hour";
    if (!time) return "Choose a time";
    if (repeat === "day" || days.length === 7) return `Every day at ${time}`;
    if (!days.length) return "No days chosen. Choose at least one day";
    const order = [...days].map(Number).sort((a, b) => ((a + 6) % 7) - ((b + 6) % 7));
    if (order.join() === "1,2,3,4,5") return `Every weekday at ${time}`;
    return `Every ${andList(order.map((d) => DAY_NAMES[d]))} at ${time}`;
  }
  function nextRun({ repeat, days = [], time = "", minute = 0 }, now = new Date()) {
    if (repeat === "hour") {
      const t = new Date(now);
      t.setSeconds(0, 0);
      t.setMinutes(Number(minute) || 0);
      if (t <= now) t.setHours(t.getHours() + 1);
      return t;
    }
    if (!time) return null;
    const [h, m] = time.split(":").map(Number);
    const allowed = repeat === "day" ? [0, 1, 2, 3, 4, 5, 6] : days.map(Number);
    for (let add = 0; add < 8; add++) {
      const t = new Date(now.getFullYear(), now.getMonth(), now.getDate() + add, h, m);
      if (t > now && allowed.includes(t.getDay())) return t;
    }
    return null;
  }
  function whenWords(t, now = new Date()) {
    const pad = (n) => String(n).padStart(2, "0");
    const at = `${pad(t.getHours())}:${pad(t.getMinutes())}`;
    const days = Math.round((new Date(t.getFullYear(), t.getMonth(), t.getDate()) - new Date(now.getFullYear(), now.getMonth(), now.getDate())) / 864e5);
    if (days === 0) return `today at ${at}`;
    if (days === 1) return `tomorrow at ${at}`;
    return `${DAY_NAMES[t.getDay()]} ${t.getDate()} ${MONTH_NAMES[t.getMonth()]} at ${at}`;
  }
  function setupSchedules(root = document) {
    root.querySelectorAll(".schedule[data-schedule]").forEach((box) => {
      if (box.dataset.ready) return;
      box.dataset.ready = "1";
      const repeat = box.querySelector("[data-schedule-repeat]");
      const time = box.querySelector("[data-schedule-time]");
      const minute = box.querySelector("[data-schedule-minute]");
      const days = box.querySelector("[data-schedule-days]");
      const words = box.querySelector("[data-schedule-words]");
      const next = box.querySelector("[data-schedule-next]");
      const update = (tell) => {
        const value = {
          repeat: repeat.value,
          days: [...days.querySelectorAll("input:checked")].map((d) => Number(d.value)),
          time: time?.value || "",
          minute: Number(minute?.value || 0),
        };
        days.closest("fieldset, .field").hidden = value.repeat !== "week";
        if (time) time.closest(".field").hidden = value.repeat === "hour";
        if (minute) minute.closest(".field").hidden = value.repeat !== "hour";
        value.words = scheduleWords(value);
        const t = nextRun(value);
        if (words) words.textContent = value.words;
        if (next) next.textContent = t ? `Next: ${whenWords(t)}` : "";
        if (tell) box.dispatchEvent(new CustomEvent("schedule-change", { detail: value }));
      };
      box.addEventListener("change", () => update(true));
      update(false);
    });
  }

  /* Tag input: .tag-input[data-tag-input] > ul.tag-input__list + input.tag-input__field, and a hidden input that
     holds the words joined with commas. Enter or a comma adds what is in the box (several at once when pasted with
     commas); leaving the box adds it too. Each tag has its own Remove button named with the word. Backspace in an
     empty box moves focus to the last Remove button. Adding and removing are said politely; after a removal, focus
     goes to the next Remove button, or back to the box. Fires tags-change with { values }. */
  function setupTagInputs(root = document) {
    root.querySelectorAll(".tag-input[data-tag-input]").forEach((box) => {
      if (box.dataset.ready) return;
      box.dataset.ready = "1";
      const field = box.querySelector(".tag-input__field");
      const list = box.querySelector(".tag-input__list");
      const hidden = box.querySelector('input[type="hidden"]');
      const values = () => [...list.children].map((li) => li.dataset.value);
      const changed = () => {
        if (hidden) hidden.value = values().join(",");
        box.dispatchEvent(new CustomEvent("tags-change", { detail: { values: values() } }));
      };
      const make = (value) => {
        const li = document.createElement("li");
        li.className = "tag-input__tag";
        li.dataset.value = value;
        li.innerHTML = `<span></span><button type="button">${sprite("x")}</button>`;
        li.firstChild.textContent = value;
        li.lastChild.setAttribute("aria-label", `Remove ${value}`);
        return li;
      };
      [...list.children].forEach((li) => {
        if (!li.querySelector("button")) li.replaceWith(make(li.dataset.value || li.textContent.trim()));
      });
      const add = (text) => {
        const added = [];
        const already = [];
        for (const part of text.split(",").map((p) => p.trim()).filter(Boolean)) {
          if (values().some((v) => v.toLowerCase() === part.toLowerCase())) already.push(part);
          else {
            list.append(make(part));
            added.push(part);
          }
        }
        if (added.length) changed();
        const words = [added.length && `${andList(added)} added`, already.length && `${andList(already)} ${already.length === 1 ? "is" : "are"} already in the list`];
        if (added.length || already.length) say(words.filter(Boolean).join(". "));
      };
      field.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === ",") {
          event.preventDefault();
          add(field.value);
          field.value = "";
        } else if (event.key === "Backspace" && !field.value && list.lastElementChild) {
          event.preventDefault();
          list.lastElementChild.querySelector("button").focus();
        }
      });
      field.addEventListener("input", () => {
        if (!field.value.includes(",")) return;
        const parts = field.value.split(",");
        field.value = parts.pop();
        add(parts.join(","));
      });
      field.addEventListener("blur", () => {
        if (!field.value.trim()) return;
        add(field.value);
        field.value = "";
      });
      list.addEventListener("click", (event) => {
        const button = event.target.closest("button");
        if (!button) return;
        const li = button.closest("li");
        const after = li.nextElementSibling || li.previousElementSibling;
        li.remove();
        changed();
        say(`${li.dataset.value} removed`);
        (after?.querySelector("button") || field).focus();
      });
      box.addEventListener("click", (event) => {
        if (event.target === box || event.target === list) field.focus();
      });
    });
  }

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
  /* Alerts centre: a .popover with data-alerts holding ul.alerts > li.alerts__item[data-unread] (each with
     .alerts__unread hidden text, a link in .alerts__title and a .alerts__read button), and a [data-alerts-read-all]
     button. Opening an alert or Mark as read marks it read; the count on the opening button follows. Fires
     alerts-read with { ids } for the app to remember. */
  function setupAlerts(root = document) {
    root.querySelectorAll(".popover[data-alerts]").forEach((pop) => {
      if (pop.dataset.alertsReady) return;
      pop.dataset.alertsReady = "1";
      const opener = document.querySelector(`[aria-controls="${pop.id}"]`);
      const count = opener?.querySelector(".count");
      const all = pop.querySelector("[data-alerts-read-all]");
      const update = () => {
        const n = pop.querySelectorAll(".alerts__item[data-unread]").length;
        if (count) {
          count.hidden = !n;
          count.firstChild.nodeValue = String(n);
        }
        all?.setAttribute("aria-disabled", String(!n));
      };
      const read = (item) => {
        if (!item.hasAttribute("data-unread")) return false;
        item.removeAttribute("data-unread");
        item.querySelector(".alerts__unread")?.remove();
        item.querySelector(".alerts__read")?.remove();
        return true;
      };
      pop.addEventListener("click", (event) => {
        const one = event.target.closest(".alerts__read");
        const link = event.target.closest(".alerts__title a");
        if (one) {
          const item = one.closest(".alerts__item");
          read(item);
          (item.querySelector(".alerts__title a") || item.querySelector(".alerts__title"))?.focus();
          say("Marked as read");
          pop.dispatchEvent(new CustomEvent("alerts-read", { detail: { ids: [item.dataset.id] } }));
        } else if (link) {
          const item = link.closest(".alerts__item");
          if (read(item)) pop.dispatchEvent(new CustomEvent("alerts-read", { detail: { ids: [item.dataset.id] } }));
        } else if (event.target.closest("[data-alerts-read-all]")) {
          if (all.getAttribute("aria-disabled") === "true") return;
          const ids = [...pop.querySelectorAll(".alerts__item[data-unread]")].filter(read).map((i) => i.dataset.id);
          say("All alerts marked as read");
          pop.dispatchEvent(new CustomEvent("alerts-read", { detail: { ids } }));
        } else return;
        update();
      });
      update();
    });
  }

  /* Page banner: pageBanner(title, { text, tone, action: { label, run } }) shows one message for the whole app under
     the header, until it is closed with the function it returns (when the connection is back, or after the
     restart). Tones: info, success, warning and danger; danger is read out at once, the rest politely. */
  const BANNER_ICONS = { info: "info", success: "circle-check", warning: "triangle-alert", danger: "circle-alert" };
  function pageBanner(title, options = {}) {
    let banner = document.getElementById("app-banner");
    if (!banner) {
      banner = document.createElement("div");
      banner.id = "app-banner";
      banner.className = "page-banner";
      const header = document.querySelector(".site-header");
      if (header) header.after(banner);
      else document.body.prepend(banner);
    }
    const tone = BANNER_ICONS[options.tone] ? options.tone : "info";
    banner.dataset.tone = tone;
    banner.innerHTML = `${sprite(BANNER_ICONS[tone])}<p class="page-banner__text"><strong></strong> <span></span></p>`;
    banner.querySelector("strong").textContent = title;
    banner.querySelector("p span").textContent = options.text || "";
    if (options.action) {
      const actions = document.createElement("div");
      actions.className = "page-banner__actions";
      const button = document.createElement("button");
      button.type = "button";
      button.className = "btn";
      button.textContent = options.action.label;
      button.addEventListener("click", () => options.action.run?.());
      actions.append(button);
      banner.append(actions);
    }
    banner.hidden = false;
    say([title, options.text].filter(Boolean).join(" "), tone === "danger");
    return () => {
      banner.hidden = true;
      banner.replaceChildren();
    };
  }

  /* Tooltip: data-tooltip="Connected" on anything that shows only an icon (an icon button, a .status-icon with
     tabindex="0"). It shows on hover after a moment and at once on keyboard focus, stays while the pointer is on it
     or on the tooltip, and Escape closes it (WCAG 1.4.13). The words must already be the thing's name (aria-label or
     hidden text), so the tooltip is hidden from screen readers and never holds anything new. One element for the
     page, made the first time; the page is listened to only while one shows. */
  let tip = null;
  let tipFor = null;
  let tipTimer = null;
  function placeTip() {
    if (!tipFor) return;
    const r = tipFor.getBoundingClientRect();
    const t = tip.getBoundingClientRect();
    let top = r.top - t.height - 6;
    if (top < 4) top = r.bottom + 6;
    const left = Math.max(4, Math.min(r.left + r.width / 2 - t.width / 2, innerWidth - t.width - 4));
    tip.style.top = `${Math.round(top)}px`;
    tip.style.left = `${Math.round(left)}px`;
  }
  function tipKey(event) {
    if (event.key !== "Escape" || !tip || tip.hidden) return;
    event.preventDefault();
    event.stopPropagation();
    hideTip();
  }
  function showTip(el) {
    clearTimeout(tipTimer);
    if (!tip) {
      tip = document.createElement("div");
      tip.className = "tooltip";
      tip.setAttribute("aria-hidden", "true");
      tip.hidden = true;
      document.body.append(tip);
      tip.addEventListener("pointerenter", () => clearTimeout(tipTimer));
      tip.addEventListener("pointerleave", () => (tipTimer = setTimeout(hideTip, 150)));
    }
    const wasHidden = tip.hidden;
    tipFor = el;
    tip.textContent = el.dataset.tooltip;
    tip.hidden = false;
    placeTip();
    if (wasHidden) {
      addEventListener("scroll", placeTip, { passive: true, capture: true });
      document.addEventListener("keydown", tipKey, true);
    }
  }
  function hideTip() {
    clearTimeout(tipTimer);
    if (!tip || tip.hidden) return;
    tip.hidden = true;
    tipFor = null;
    removeEventListener("scroll", placeTip, { capture: true });
    document.removeEventListener("keydown", tipKey, true);
  }
  function setupTooltips() {
    if (document.documentElement.dataset.tooltips) return;
    document.documentElement.dataset.tooltips = "1";
    document.addEventListener("pointerover", (event) => {
      const el = event.target.closest?.("[data-tooltip]");
      if (!el || el === tipFor) return;
      clearTimeout(tipTimer);
      tipTimer = setTimeout(() => showTip(el), tip && !tip.hidden ? 0 : 300);
    });
    document.addEventListener("pointerout", (event) => {
      const el = event.target.closest?.("[data-tooltip]");
      if (!el || el.contains(event.relatedTarget) || (tip && tip.contains(event.relatedTarget))) return;
      clearTimeout(tipTimer);
      if (el === tipFor && el !== document.activeElement) tipTimer = setTimeout(hideTip, 150);
    });
    document.addEventListener("focusin", (event) => {
      const el = event.target.closest?.("[data-tooltip]");
      if (el && el.matches(":focus-visible")) showTip(el);
    });
    document.addEventListener("focusout", (event) => {
      if (event.target.closest?.("[data-tooltip]") === tipFor) hideTip();
    });
  }

  /* Command palette: a button with data-command-palette opens it, and so do Ctrl+K and Command+K unless the page has
     data-no-shortcut on <html> (WCAG 2.1.4). It is a dialog holding the combobox, always open, listing the page's
     menus (.rail, .menu-tabs and .phone-menu links) and every [data-command] button, or commandPalette.items when an
     app sets it to a function that returns [{ label, hint, keywords, href | run }]. Only the label and keywords are searched,
     never the hint ("Page", "Action"). Enter goes or runs; Escape
     closes, and focus returns to what had it. Built the first time it opens. */
  let palette = null;
  function paletteItems() {
    if (typeof commandPalette.items === "function") return commandPalette.items();
    const seen = new Set();
    const items = [];
    document.querySelectorAll(".rail a[href], .menu-tabs a[href], .phone-menu a[href]").forEach((a) => {
      const label = (a.querySelector(".menu-tabs__label, .rail__name")?.textContent || a.textContent).trim();
      if (!label || seen.has(a.href)) return;
      seen.add(a.href);
      items.push({ label, value: a.href, hint: "Page", href: a.href });
    });
    document.querySelectorAll("[data-command]").forEach((el) =>
      items.push({ label: el.dataset.command || el.textContent.trim(), value: el.dataset.command, hint: "Action", run: () => el.click() }),
    );
    return items;
  }
  function commandPalette(opener = document.activeElement) {
    if (!palette) {
      palette = document.createElement("dialog");
      palette.className = "dialog command-palette";
      palette.setAttribute("aria-label", "Find a page or action");
      palette.innerHTML = `<div class="combobox" data-noun="pages and actions" data-noun-one="page or action"><label class="visually-hidden" for="command-palette-input">Find a page or action</label><input class="input combobox__input" id="command-palette-input" type="text" role="combobox" aria-autocomplete="list" aria-expanded="true" aria-controls="command-palette-list" autocomplete="off" spellcheck="false" placeholder="Find a page or action"><div class="combobox__popup"><ul class="combobox__list" id="command-palette-list" role="listbox" aria-label="Pages and actions"></ul><p class="combobox__none" hidden></p></div></div><p class="command-palette__keys">Up and Down move, Enter goes, Escape closes</p>`;
      document.body.append(palette);
      palette.addEventListener("close", () => palette.opener?.isConnected && palette.opener.focus());
      palette.addEventListener("click", (event) => event.target === palette && palette.close());
      palette.combo = combobox(palette.querySelector(".combobox"), {
        always: true,
        options: [],
        onChoose(item) {
          palette.close();
          if (item.run) item.run();
          else if (item.href) location.href = item.href;
        },
      });
    }
    palette.opener = opener;
    palette.combo.input.value = "";
    palette.combo.setOptions(paletteItems());
    palette.showModal();
    palette.combo.input.focus();
  }
  function setupCommandPalette(root = document) {
    const buttons = root.querySelectorAll("[data-command-palette]");
    buttons.forEach((button) => {
      if (button.dataset.ready) return;
      button.dataset.ready = "1";
      button.setAttribute("aria-haspopup", "dialog");
      button.addEventListener("click", () => commandPalette(button));
    });
    if (!buttons.length || document.documentElement.dataset.paletteKeys) return;
    document.documentElement.dataset.paletteKeys = "1";
    document.addEventListener("keydown", (event) => {
      if (document.documentElement.hasAttribute("data-no-shortcut")) return;
      if (!(event.ctrlKey || event.metaKey) || event.altKey || event.shiftKey || event.key.toLowerCase() !== "k") return;
      if (palette?.open) return;
      event.preventDefault();
      commandPalette(document.activeElement);
    });
  }

  function setup(root) {
    setupLogViews(root); // before setupToggles, so its filter chips keep their own state
    setupMenus(root);
    setupShelves(root);
    setupLayers(root);
    setupDialogs(root);
    setupFolds(root);
    setupToggles(root);
    setupCopy(root);
    setupSearch(root);
    setupHeaderFit(root);
    setupDisplay(root);
    setupAzJump(root);
    setupSortables(root);
    setupSideTrees(root);
    setupSolvers(root);
    setupTabs(root);
    setupComboboxes(root);
    setupCharts(root);
    setupErrorSummaries(root);
    setupSecrets(root);
    setupSchedules(root);
    setupTagInputs(root);
    setupPopovers(root);
    setupAlerts(root);
    setupTooltips(root);
    setupCommandPalette(root);
  }
  /* Waiting standard (DASH-493): set a count bar (.progress.progress--running with role="progressbar") to `done` of
     `total`. It eases onto the count, then creeps towards the next one over `eachMs` (the usual time for one item),
     never past 90% of the way, so the bar never sits still while an item works. With less motion asked for it only
     steps. The words beside the bar still carry the count; this changes the bar and its aria-valuenow only. */
  function creepProgress(bar, done, total, eachMs = 0) {
    const fill = bar && bar.firstElementChild;
    if (!fill || !total) return;
    const start = 4;
    const pct = (i) => Math.min(100, start + ((100 - start) * i) / total);
    const still = motionStill();
    bar.setAttribute("aria-valuenow", String(done));
    clearTimeout(bar._creep);
    fill.style.transition = still ? "none" : "width 300ms ease-out";
    fill.style.width = `${pct(done)}%`;
    if (still || !eachMs || done >= total) return;
    bar._creep = setTimeout(() => {
      fill.style.transition = `width ${eachMs}ms linear`;
      fill.style.width = `${pct(done) + (pct(done + 1) - pct(done)) * 0.9}%`;
    }, 320);
  }
  window.SharedComponents = { setup, applyTheme, creepProgress, setupHeaderFit, fitHeader, motionStill, setupSideTrees, setupSolvers, setupSearch, setupSearchIcons, setupSortables, openLayer, toast, savedNote, copyText, azLetter, azJump, azGo, loadMore,
    logView, setupTabs, combobox, sparkline, gauge, pagination, showErrors, clearErrors, setFieldError, setupSecrets,
    scheduleWords, nextRun, setupSchedules, setupTagInputs, setupPopovers, setupAlerts, pageBanner, setupTooltips, commandPalette, say };
  // An app that wires its own behaviour (Starboard's page scripts) loads this file with data-manual, or
  // sets window.SharedComponentsManual = true first, and calls setup() or openLayer() itself.
  const manual = window.SharedComponentsManual || document.currentScript?.hasAttribute("data-manual");
  if (!manual) document.addEventListener("DOMContentLoaded", () => setup());
})();
