/* charts: a part of the shared components. Load it after components.js, on the pages that use it.
 * Made by tools/parts.py from components.js in github.com/TheMightyTRex/design-system: change it there, not here. */
(() => {
  const S = window.SharedComponents;
  const { focusable, announcer, toast, copyText, sprite, escapeHtml, num, fold, andList, say, ownStatus } = S.kit;

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

  Object.assign(S, { sparkline, gauge });
  S.addSetup(setupCharts);
})();
