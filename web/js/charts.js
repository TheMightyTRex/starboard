// Charts for the System pages: line charts over time and horizontal bar charts. No libraries.
// Rules (from the charts guidance): one axis per chart, 2px lines, a 10% wash under a single series, a legend
// for two series, hairline solid grid, a crosshair and tooltip on hover and with the arrow keys, and a table
// view so no value depends on hovering. Text uses text colours; only marks use the series colours.

const SVG_NS = "http://www.w3.org/2000/svg";

function svgEl(tag, attrs = {}) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  return node;
}

function niceMax(value) {
  if (value <= 0) return 1;
  const power = 10 ** Math.floor(Math.log10(value));
  for (const step of [1, 2, 2.5, 5, 10]) if (step * power >= value) return step * power;
  return 10 * power;
}

const timeLabel = (t) => new Date(t * 1000).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });

/**
 * A line chart over time.
 * opts: { title, summary, points: [{t, ...}], series: [{key, name}], format(v), max (fixed top, optional) }
 */
function lineChart(opts) {
  const { title, points, series, format } = opts;
  const card = el("section", { class: "panel chart" });
  const head = el("div", { class: "chart__head" }, el("h2", { text: title }), opts.detail ? el("span", { class: "row__meta", text: opts.detail }) : null);
  card.append(head);
  const latest = points[points.length - 1];
  card.append(el("p", { class: "chart__big num", text: latest ? series.map((s) => (series.length > 1 ? `${s.short || s.name} ${format(latest[s.key] ?? 0)}` : format(latest[s.key] ?? 0))).join("   ") : "Collecting…" }));
  if (series.length > 1) {
    card.append(el("p", { class: "chart__legend" }, series.map((s, i) => el("span", {}, el("i", { class: `swatch swatch--line swatch--${i}`, "aria-hidden": "true" }), s.name))));
  }
  if (points.length < 2) {
    card.append(el("p", { class: "hint", text: "Starboard records a reading every minute. The chart fills in as readings arrive." }));
    return card;
  }
  const plot = el("div", { class: "chart__plot" });
  card.append(plot);
  const tooltip = el("div", { class: "chart__tooltip", role: "status", hidden: true });
  plot.append(tooltip);

  const draw = () => {
    plot.querySelector("svg")?.remove();
    const width = Math.max(240, plot.clientWidth || 320);
    const height = 170;
    const pad = { left: 52, right: 12, top: 10, bottom: 24 };
    const values = points.flatMap((p) => series.map((s) => p[s.key] ?? 0));
    const top = opts.max ?? niceMax(Math.max(...values) * 1.1);
    const t0 = points[0].t, t1 = points[points.length - 1].t;
    const x = (t) => pad.left + ((t - t0) / Math.max(1, t1 - t0)) * (width - pad.left - pad.right);
    const y = (v) => pad.top + (1 - Math.min(1, (v ?? 0) / top)) * (height - pad.top - pad.bottom);
    const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, width, height, class: "chart__svg", tabindex: "0",
      role: "img", "aria-label": `${title}. Use the left and right arrow keys to read values.` });
    // Grid and y-axis labels: 0, half, top.
    for (const v of [0, top / 2, top]) {
      svg.append(svgEl("line", { x1: pad.left, x2: width - pad.right, y1: y(v), y2: y(v), class: "chart__grid" }));
      const label = svgEl("text", { x: pad.left - 6, y: y(v) + 4, class: "chart__axis", "text-anchor": "end" });
      label.textContent = format(v);
      svg.append(label);
    }
    // X-axis labels: start, middle, end.
    [[t0, "start"], [(t0 + t1) / 2, "middle"], [t1, "end"]].forEach(([t, anchor]) => {
      const label = svgEl("text", { x: x(t), y: height - 6, class: "chart__axis", "text-anchor": anchor });
      label.textContent = timeLabel(t);
      svg.append(label);
    });
    series.forEach((s, i) => {
      const coords = points.map((p) => `${x(p.t).toFixed(1)},${y(p[s.key]).toFixed(1)}`);
      if (series.length === 1) {
        svg.append(svgEl("polygon", { points: `${x(t0)},${y(0)} ${coords.join(" ")} ${x(t1)},${y(0)}`, class: `chart__area chart__area--${i}` }));
      }
      svg.append(svgEl("polyline", { points: coords.join(" "), class: `chart__line chart__line--${i}` }));
      svg.append(svgEl("circle", { cx: x(t1), cy: y(latest[s.key]), r: 4, class: `chart__dot chart__dot--${i}` }));
    });
    const cross = svgEl("line", { y1: pad.top, y2: height - pad.bottom, class: "chart__cross", visibility: "hidden" });
    svg.append(cross);
    plot.prepend(svg);

    let index = -1;
    const show = (i) => {
      index = Math.max(0, Math.min(points.length - 1, i));
      const p = points[index];
      cross.setAttribute("x1", x(p.t)); cross.setAttribute("x2", x(p.t)); cross.setAttribute("visibility", "visible");
      tooltip.replaceChildren(el("span", { class: "chart__tooltip-time", text: timeLabel(p.t) }),
        ...series.map((s, k) => el("span", { class: "chart__tooltip-row" },
          el("i", { class: `swatch swatch--line swatch--${k}`, "aria-hidden": "true" }), el("strong", { text: format(p[s.key] ?? 0) }), ` ${s.name}`)));
      tooltip.hidden = false;
      const left = Math.min(width - 150, Math.max(0, x(p.t) + 10));
      tooltip.style.left = `${left}px`;
    };
    const hide = () => { cross.setAttribute("visibility", "hidden"); tooltip.hidden = true; };
    svg.addEventListener("pointermove", (e) => {
      const box = svg.getBoundingClientRect();
      const t = t0 + ((e.clientX - box.left - pad.left) / (width - pad.left - pad.right)) * (t1 - t0);
      let best = 0;
      points.forEach((p, k) => { if (Math.abs(p.t - t) < Math.abs(points[best].t - t)) best = k; });
      show(best);
    });
    svg.addEventListener("pointerleave", hide);
    svg.addEventListener("blur", hide);
    svg.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft" || e.key === "ArrowRight") { e.preventDefault(); show(index < 0 ? points.length - 1 : index + (e.key === "ArrowRight" ? 1 : -1)); }
      if (e.key === "Home") { e.preventDefault(); show(0); }
      if (e.key === "End") { e.preventDefault(); show(points.length - 1); }
      if (e.key === "Escape") hide();
    });
  };
  requestAnimationFrame(draw);
  new ResizeObserver(() => draw()).observe(plot);

  // The table view: every value without hovering (about 12 rows across the range).
  const step = Math.max(1, Math.floor(points.length / 12));
  const rows = points.filter((_, i) => i % step === 0 || i === points.length - 1);
  card.append(el("details", { class: "chart__table" }, el("summary", { text: "Show as a table" }),
    el("div", { class: "table-scroll" }, el("table", {},
      el("thead", {}, el("tr", {}, el("th", { scope: "col", text: "Time" }), series.map((s) => el("th", { scope: "col", text: s.name })))),
      el("tbody", {}, rows.map((p) => el("tr", {}, el("th", { scope: "row", text: timeLabel(p.t) }), series.map((s) => el("td", { class: "num", text: format(p[s.key] ?? 0) })))))))));
  return card;
}

/**
 * Horizontal bars, one per row, with the value at the tip and an optional limit mark.
 * opts: { title, detail, rows: [{label, value, limit, tone, note}], max, format(v) }
 */
function barChart(opts) {
  const { title, rows, format } = opts;
  const top = opts.max ?? niceMax(Math.max(...rows.map((r) => Math.max(r.value, r.limit || 0)), 1));
  const card = el("section", { class: "panel chart" },
    el("div", { class: "chart__head" }, el("h2", { text: title }), opts.detail ? el("span", { class: "row__meta", text: opts.detail }) : null));
  const list = el("ul", { class: "bars" });
  for (const r of rows) {
    const bar = el("span", { class: "bar__fill", "data-tone": r.tone || "" });
    bar.style.width = `${Math.max(0.5, (r.value / top) * 100)}%`;
    const track = el("span", { class: "bar__track" }, bar);
    if (r.limit) {
      const limit = el("span", { class: "bar__limit", title: `Limit ${format(r.limit)}` });
      limit.style.left = `${(r.limit / top) * 100}%`;
      track.append(limit);
    }
    const item = el("li", { class: "bar", tabindex: "0", title: `${r.label}: ${format(r.value)}${r.limit ? ` (limit ${format(r.limit)})` : ""}${r.note ? `. ${r.note}` : ""}` },
      el("span", { class: "bar__label", text: r.label }), track, el("span", { class: "bar__value num", text: format(r.value) }));
    list.append(item);
  }
  card.append(list);
  if (rows.some((r) => r.limit)) card.append(el("p", { class: "chart__legend" }, el("span", {}, el("i", { class: "swatch swatch--limit", "aria-hidden": "true" }), "Limit")));
  card.append(el("details", { class: "chart__table" }, el("summary", { text: "Show as a table" }),
    el("div", { class: "table-scroll" }, el("table", {},
      el("thead", {}, el("tr", {}, el("th", { scope: "col", text: "Item" }), el("th", { scope: "col", text: "Value" }), rows.some((r) => r.limit) ? el("th", { scope: "col", text: "Limit" }) : null)),
      el("tbody", {}, rows.map((r) => el("tr", {}, el("th", { scope: "row", text: r.label }), el("td", { class: "num", text: format(r.value) }), rows.some((x) => x.limit) ? el("td", { class: "num", text: r.limit ? format(r.limit) : "" }) : null)))))));
  return card;
}

/** A small trend line for a stat tile (no axes; the tile's words carry the value). */
function trendLine(values, max) {
  const w = 120, h = 32;
  const top = max ?? Math.max(1, ...values);
  const svg = svgEl("svg", { viewBox: `0 0 ${w} ${h}`, class: "trend", "aria-hidden": "true", preserveAspectRatio: "none" });
  if (values.length > 1) {
    svg.append(svgEl("polyline", { class: "chart__line chart__line--0",
      points: values.map((v, i) => `${((i / (values.length - 1)) * w).toFixed(1)},${(h - 2 - (h - 4) * Math.min(1, (v ?? 0) / top)).toFixed(1)}`).join(" ") }));
  }
  return svg;
}

const RANGE_KEY = "starboard.range";
function rangePicker(onChange) {
  let hours = "1";
  try { hours = localStorage.getItem(RANGE_KEY) || "1"; } catch { /* private window */ }
  const box = el("div", { class: "segmented", role: "radiogroup", "aria-label": "Time range" });
  for (const [value, label] of [["1", "Last hour"], ["6", "Last 6 hours"], ["24", "Last 24 hours"]]) {
    const input = el("input", { type: "radio", name: "range", value, checked: value === hours });
    input.addEventListener("change", () => { try { localStorage.setItem(RANGE_KEY, value); } catch { /* ignore */ } onChange(value); });
    box.append(el("label", {}, input, el("span", { text: label })));
  }
  return { element: box, get value() { return box.querySelector("input:checked").value; } };
}

const percent = (v) => `${Math.round(v)}%`;
const perSecond = (v) => `${formatBytes(v)}/s`;
const degrees = (v) => `${Math.round(v)} °C`;
