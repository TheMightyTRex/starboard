/* Copied from the design system (tools/annotate.js); change it there and copy it again.
 * Screenshot mark-up for help, to docs/SCREENSHOTS.md: a red outline 5px outside the control, a curved arrow
 * with a filled head touching it, and a badge with the article's step number. Paste into the browser console
 * (or inject it with a test tool), mark, verify, then take the screenshot. Nothing is sent anywhere.
 *
 *   Annotate.mark("Add an app", { step: 2, side: "right" })     // exact visible text, tightest element
 *   Annotate.mark("$#save", { step: 3 })                         // a CSS selector, after the $
 *   Annotate.mark([el1, el2], { step: 4, side: "bottom" })       // one outline round several elements
 *   Annotate.mark(Annotate.choice("Keep the old one"), { step: 5 }) // a radio or tick box with its words
 *   Annotate.verify({ steps: [2, 3, 4, 5] })  // { pass, problems }: never capture when pass is false
 *   Annotate.clear()
 */
(() => {
  const RED = "#C71F1F", GAP = 5, STROKE = 3, BADGE = 13, MAX = 3;
  const NS = "http://www.w3.org/2000/svg";
  const marks = [];
  let layer = null;

  function svg(tag, attrs) {
    const n = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    return n;
  }

  function ensureLayer() {
    if (layer && document.body.contains(layer)) return layer;
    layer = svg("svg", { id: "__annotate_layer", width: innerWidth, height: innerHeight, "aria-hidden": "true" });
    Object.assign(layer.style, { position: "fixed", inset: "0", pointerEvents: "none", zIndex: "2147483647", overflow: "visible" });
    document.body.append(layer);
    return layer;
  }

  /** The element whose own visible text is exactly `text`, the tightest one. */
  function byText(text) {
    const want = text.trim();
    let best = null;
    for (const el of document.querySelectorAll("body *")) {
      if (el.closest("#__annotate_layer")) continue;
      const r = el.getBoundingClientRect();
      if (!r.width || !r.height) continue;
      if ((el.innerText || "").trim() === want && (!best || best.contains(el))) best = el;
    }
    return best;
  }

  /** A radio button or tick box with its label and the description under it, as one target. */
  function choice(text) {
    const label = typeof text === "string" ? byText(text) : text;
    if (!label) return null;
    for (let p = label; p && p !== document.body; p = p.parentElement) {
      if (p.querySelector('input[type="radio"], input[type="checkbox"]')) return p;
    }
    return label;
  }

  function resolve(target) {
    if (Array.isArray(target)) return target.flatMap(resolve);
    if (target instanceof Element) return [target];
    if (typeof target === "string") {
      const el = target.startsWith("$") ? document.querySelector(target.slice(1)) : byText(target);
      return el ? [el] : [];
    }
    return [];
  }

  function union(els) {
    const rs = els.map((e) => e.getBoundingClientRect());
    const x1 = Math.min(...rs.map((r) => r.left)), y1 = Math.min(...rs.map((r) => r.top));
    const x2 = Math.max(...rs.map((r) => r.right)), y2 = Math.max(...rs.map((r) => r.bottom));
    return { x: x1, y: y1, w: x2 - x1, h: y2 - y1 };
  }

  function draw(m) {
    const r = union(m.els);
    const box = { x: r.x - GAP, y: r.y - GAP, w: r.w + GAP * 2, h: r.h + GAP * 2 };
    m.box = box;
    const g = svg("g", {});
    g.append(svg("rect", { x: box.x, y: box.y, width: box.w, height: box.h, rx: 4, fill: "none", stroke: RED, "stroke-width": STROKE }));
    // The arrow: from `tail` pixels away on the chosen side, a curve that ends on the outline.
    const t = m.tail;
    const mid = { x: box.x + box.w / 2, y: box.y + box.h / 2 };
    const end = { right: { x: box.x + box.w, y: mid.y }, left: { x: box.x, y: mid.y },
                  top: { x: mid.x, y: box.y }, bottom: { x: mid.x, y: box.y + box.h } }[m.side];
    const dir = { right: [1, 0], left: [-1, 0], top: [0, -1], bottom: [0, 1] }[m.side];
    const start = { x: end.x + dir[0] * t, y: end.y + dir[1] * t + (dir[0] ? -t * 0.45 : 0) + 0 };
    if (!dir[0]) start.x = end.x + t * 0.45;
    const ctrl = { x: end.x + dir[0] * t * 0.15 + (dir[0] ? 0 : t * 0.5), y: end.y + dir[1] * t * 0.15 + (dir[0] ? -t * 0.5 : 0) };
    // Stop the line short of the head, so the filled head (not the line) touches the outline.
    const head = 14;
    const tx = end.x - ctrl.x, ty = end.y - ctrl.y, len = Math.hypot(tx, ty) || 1;
    const ux = tx / len, uy = ty / len;
    const base = { x: end.x - ux * head, y: end.y - uy * head };
    g.append(svg("path", { d: `M${start.x},${start.y} Q${ctrl.x},${ctrl.y} ${base.x},${base.y}`, fill: "none", stroke: RED, "stroke-width": STROKE, "stroke-linecap": "round" }));
    const px = -uy, py = ux;
    g.append(svg("polygon", { points: `${end.x},${end.y} ${base.x + px * 8},${base.y + py * 8} ${base.x - px * 8},${base.y - py * 8}`, fill: RED }));
    m.arrow = { start, end };
    // The step badge: top-left, else top-right, else the bottom corners, whichever stays on screen.
    if (m.step != null) {
      const spots = [[box.x, box.y], [box.x + box.w, box.y], [box.x, box.y + box.h], [box.x + box.w, box.y + box.h]];
      const [bx, by] = spots.find(([x, y]) => x - BADGE >= 0 && y - BADGE >= 0 && x + BADGE <= innerWidth && y + BADGE <= innerHeight) || spots[0];
      g.append(svg("circle", { cx: bx, cy: by, r: BADGE, fill: RED, stroke: "#fff", "stroke-width": 2 }));
      const label = svg("text", { x: bx, y: by + 5, "text-anchor": "middle", fill: "#fff", "font-size": 14, "font-weight": 700, "font-family": "system-ui, sans-serif" });
      label.textContent = String(m.step);
      g.append(label);
      m.badge = { x: bx, y: by };
    }
    m.node = g;
    ensureLayer().append(g);
  }

  function mark(target, { step = null, side = "right", tail = 130 } = {}) {
    const els = resolve(target);
    if (!els.length) throw new Error(`Annotate: nothing on the page matches ${JSON.stringify(String(target))}`);
    const m = { target, els, step, side, tail };
    draw(m);
    marks.push(m);
    return m;
  }

  function verify({ steps } = {}) {
    const problems = [];
    if (!Array.isArray(steps)) problems.push("Say which article steps this picture shows: verify({ steps: [...] }), [] for none");
    if (marks.length > MAX) problems.push(`${marks.length} outlines: at most ${MAX} in one picture`);
    for (const m of marks) {
      const name = typeof m.target === "string" ? m.target : m.els[0].tagName.toLowerCase();
      if (!m.els.every((e) => document.contains(e))) { problems.push(`${name}: the control has left the page`); continue; }
      const r = union(m.els);
      const b = m.box;
      if (Math.abs(r.x - GAP - b.x) > 2 || Math.abs(r.y - GAP - b.y) > 2 || Math.abs(r.w + GAP * 2 - b.w) > 2 || Math.abs(r.h + GAP * 2 - b.h) > 2) {
        problems.push(`${name}: the page moved, so the outline no longer wraps the control. Clear and mark again`);
      }
      for (const [x, y] of [[b.x, b.y], [b.x + b.w, b.y + b.h], [m.arrow.start.x, m.arrow.start.y]]) {
        if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) { problems.push(`${name}: part of the outline or arrow is off the screen`); break; }
      }
      const cx = r.x + r.w / 2, cy = r.y + r.h / 2;
      const top = document.elementFromPoint(cx, cy);
      if (top && !m.els.some((e) => e === top || e.contains(top) || top.contains(e))) problems.push(`${name}: something covers the control`);
      if (Array.isArray(steps) && steps.length && m.step == null) problems.push(`${name}: the outline has no step number`);
    }
    if (Array.isArray(steps)) {
      const badges = marks.map((m) => m.step).filter((s) => s != null).sort((a, b) => a - b);
      const want = [...steps].sort((a, b) => a - b);
      if (JSON.stringify(badges) !== JSON.stringify(want)) problems.push(`The badges read ${badges.join(", ") || "none"}; the steps shown are ${want.join(", ") || "none"}`);
    }
    return { pass: problems.length === 0, problems };
  }

  function clear() {
    marks.splice(0).forEach((m) => m.node && m.node.remove());
    if (layer) { layer.remove(); layer = null; }
  }

  window.Annotate = { mark, verify, clear, byText, choice, marks };
})();
