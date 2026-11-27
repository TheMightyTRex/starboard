// Voice control check for tools/a11y (owner, 27 November 2026), run inside the page with page.evaluate:
//  - labelInName: WCAG 2.5.3 Label in Name. A person using Voice Access, Voice Control or Dragon says the words they see, so the
//    accessible name of every control must contain its visible text (compared without case, spaces or punctuation). Handles
//    icon-only buttons (no visible text, so nothing to match), aria-label that replaces the visible words, aria-labelledby,
//    visually hidden text, and text split across child elements. axe's label-content-name-mismatch is a start; this reads more.
//  Target Size (WCAG 2.5.8, 24 by 24 CSS pixels) is already reported for every button, button-like link, tick and select by
//  structure() in a11y.mjs as target-24px, which is stricter than the standard (it ignores the spacing exception), so it is
//  not repeated here.
// Returns a list of findings: { selector, visible, name }.
export const labelInName = () => {
  const norm = (s) => (s || "").toLowerCase().normalize("NFKD").replace(/[^\p{L}\p{N}]+/gu, "");
  const shown = (e) => {
    if (!e.getClientRects().length) return false;
    const s = getComputedStyle(e);
    return s.visibility !== "hidden" && s.display !== "none" && !e.closest("template, [hidden]");
  };
  const clipped = (e) => {  // visually hidden text: still in the accessible name, not in the visible label
    const s = getComputedStyle(e);
    const b = e.getBoundingClientRect();
    return (s.position === "absolute" && (b.width <= 1 || b.height <= 1)) || s.clip === "rect(0px, 0px, 0px, 0px)" || e.matches(".visually-hidden, .sr-only");
  };
  const text = (node, forName) => {  // visible text (forName false) or the accessible name from content (forName true)
    if (node.nodeType === 3) return node.textContent;
    if (node.nodeType !== 1) return "";
    if (node.matches("script, style, template")) return "";
    if (node.getAttribute("aria-hidden") === "true" && !forName) return "";
    if (node.getAttribute("aria-hidden") === "true") return "";
    const s = getComputedStyle(node);
    if (s.display === "none" || s.visibility === "hidden") return "";
    if (!forName && clipped(node)) return "";
    if (node.tagName === "IMG") return forName ? node.getAttribute("alt") || "" : "";
    if (node.tagName === "SVG" || node instanceof SVGElement) return forName ? node.querySelector("title")?.textContent || "" : "";
    if (node.tagName === "INPUT" || node.tagName === "SELECT" || node.tagName === "TEXTAREA") return "";
    if (forName && node.getAttribute("aria-label")) return node.getAttribute("aria-label");
    return [...node.childNodes].map((c) => text(c, forName)).join(" ");
  };
  const byIds = (ids) => ids.split(/\s+/).map((id) => document.getElementById(id)).filter(Boolean).map((n) => n.getAttribute("aria-label") || n.textContent).join(" ");
  const nameOf = (e) => {
    if (e.getAttribute("aria-labelledby")) return byIds(e.getAttribute("aria-labelledby"));
    if (e.getAttribute("aria-label")) return e.getAttribute("aria-label");
    if (e.labels && e.labels.length) return [...e.labels].map((l) => text(l, true)).join(" ");
    if (e.tagName === "INPUT" && /^(button|submit|reset)$/.test(e.type)) return e.value;
    return text(e, true) || e.getAttribute("title") || "";
  };
  const visibleOf = (e) => {
    if (e.labels && e.labels.length && e.tagName !== "BUTTON") return [...e.labels].map((l) => text(l, false)).join(" ");
    if (e.tagName === "INPUT" && /^(button|submit|reset)$/.test(e.type)) return e.value;
    if (e.tagName === "INPUT" || e.tagName === "SELECT" || e.tagName === "TEXTAREA") return "";
    return text(e, false);
  };
  const selector = (e) => e.tagName.toLowerCase() + (e.id ? `#${e.id}` : "") + (typeof e.className === "string" && e.className ? "." + e.className.trim().split(/\s+/).slice(0, 2).join(".") : "");
  const out = [];
  const controls = document.querySelectorAll("a[href], button, input:not([type=hidden]), select, textarea, summary, [role=button], [role=link], [role=tab], [role=menuitem], [role=checkbox], [role=radio], [role=switch], [role=option], [role=combobox]");
  for (const e of controls) {
    if (!shown(e) || e.disabled) continue;
    const visible = norm(visibleOf(e));
    if (!visible) continue;  // icon only, or a field with no label text: nothing to say aloud (the missing name is its own rule)
    const name = norm(nameOf(e));
    if (!name.includes(visible)) out.push({ selector: selector(e), visible: visibleOf(e).trim().replace(/\s+/g, " ").slice(0, 60), name: nameOf(e).trim().replace(/\s+/g, " ").slice(0, 60) });
  }
  return out;
};
