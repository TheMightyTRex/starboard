/* tabs: a part of the shared components. Load it after components.js, on the pages that use it.
 * Made by tools/parts.py from components.js in github.com/TheMightyTRex/design-system: change it there, not here. */
(() => {
  const S = window.SharedComponents;
  const { focusable, announcer, toast, copyText, sprite, escapeHtml, num, fold, andList, say, ownStatus, notice } = S.kit;

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

  Object.assign(S, { setupTabs });
  S.addSetup(setupTabs);
})();
