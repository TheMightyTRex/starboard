/* alerts: a part of the shared components. Load it after components.js and parts/popover.js, on the pages that use it.
 * Made by tools/parts.py from components.js in github.com/TheMightyTRex/design-system: change it there, not here. */
(() => {
  const S = window.SharedComponents;
  const { focusable, announcer, toast, copyText, sprite, escapeHtml, num, fold, andList, say, ownStatus } = S.kit;
  const { setupPopovers } = S;

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

  Object.assign(S, { setupAlerts });
  S.addSetup(setupAlerts);
})();
