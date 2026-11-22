/* combobox: a part of the shared components. Load it after components.js, on the pages that use it.
 * Made by tools/parts.py from components.js in github.com/TheMightyTRex/design-system: change it there, not here. */
(() => {
  const S = window.SharedComponents;
  const { focusable, announcer, toast, copyText, sprite, escapeHtml, num, fold, andList, say, ownStatus } = S.kit;

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

  Object.assign(S, { combobox });
  S.addSetup(setupComboboxes);
})();
