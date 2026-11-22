/* command-palette: a part of the shared components. Load it after components.js and parts/combobox.js, on the pages that use it.
 * Made by tools/parts.py from components.js in github.com/TheMightyTRex/design-system: change it there, not here. */
(() => {
  const S = window.SharedComponents;
  const { focusable, announcer, toast, copyText, sprite, escapeHtml, num, fold, andList, say, ownStatus } = S.kit;
  const { combobox } = S;

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

  Object.assign(S, { commandPalette });
  S.addSetup(setupCommandPalette);
})();
