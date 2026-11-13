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

  /* A to Z jump list (.az-jump). Letters come from the sort title ("The Expanse" under E, "Émile" under E,
     "24" under #): azLetter(title). azJump(nav, letters) draws # and A to Z into the nav, with the letters
     not in the Set shown but not choosable. The row is one Tab stop: Arrow keys, Home and End move between
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
  function azJump(nav, letters) {
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
        a.setAttribute("aria-label", `${letter === "#" ? "Numbers" : letter}, no titles`);
      }
      li.append(a);
      return li;
    }));
    setupAzJump(nav.parentNode || document);
  }
  function azGo(nav, letter) {
    const heading = document.getElementById(azId(letter));
    if (!heading) return false;
    const still = matchMedia("(prefers-reduced-motion: reduce)").matches || document.documentElement.classList.contains("pref-motion");
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
      announcer("sortable-status", "status").textContent = `${sortableLabel(row)} is already ${by < 0 ? "at the top" : "at the bottom"}`;
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
  const motionStill = () => {
    const html = document.documentElement;
    if (html.classList.contains("pref-motion")) return true;
    if (html.classList.contains("pref-motion-off")) return false;
    return Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)").matches);
  };
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
        show("More could not be loaded. Show more tries again.");
        tell("More could not be loaded");
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
    setupAzJump(root);
    setupSortables(root);
  }
  window.SharedComponents = { setup, setupSearch, setupSearchIcons, setupSortables, openLayer, toast, savedNote, copyText, azLetter, azJump, azGo, loadMore };
  // An app that wires its own behaviour (Starboard's page scripts) loads this file with data-manual, or
  // sets window.SharedComponentsManual = true first, and calls setup() or openLayer() itself.
  const manual = window.SharedComponentsManual || document.currentScript?.hasAttribute("data-manual");
  if (!manual) document.addEventListener("DOMContentLoaded", () => setup());
})();
