// Charts for the System pages: line charts over time and horizontal bar charts. No libraries.
// Rules (from the charts guidance and the shared library's line chart): one axis per chart, 2px lines, a 10%
// wash under a single series, a legend for two series with the second dashed (so it is not colour alone),
// hairline grid, a crosshair and tooltip on hover and with the arrow keys, a sentence that describes the
// chart, and a table view so no value depends on hovering. Text uses text colours; only marks use the series
// colours. A chart can be updated in place (card.update), so a focused chart or an open table keeps focus.

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

// The same for bytes, so axis labels land on round numbers of KB, MB or GB.
function niceBytes(value) {
  if (value <= 0) return 1024;
  const unit = 1024 ** Math.floor(Math.log(value) / Math.log(1024));
  return niceMax(value / unit) * unit;
}

const timeLabel = (t) => new Date(t * 1000).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });

let chartCount = 0;

/**
 * A line chart over time, in a panel.
 * opts: { title, detail, points: [{t, ...}], series: [{key, name}], format(v), max (fixed top, optional),
 *         level (heading level, 2 by default), now (words beside the title; worked out when left out),
 *         tone: [tone, word] (a status chip beside the value, for example ["warning", "Hot"]),
 *         span (the period in the description, for example "the last 6 hours"),
 *         xFormat(t, lastT) (axis and table labels; clock time by default), note (a line under the chart),
 *         waiting (words shown until there are two readings) }
 * Returns the panel; panel.update(changedOpts) redraws it in place.
 */
function lineChart(opts) {
  const id = `chart-${++chartCount}`;
  let o = { ...opts };
  const level = Math.min(6, Math.max(2, o.level || 2));
  const card = el("section", { class: "panel chart", "aria-labelledby": `${id}-h` });
  const nowText = el("span", { class: "numeric" });
  const toneSlot = el("span");
  const head = el("div", { class: "chart__head" },
    el(`h${level}`, { id: `${id}-h`, text: o.title }),
    el("span", { class: "chart__value" }, nowText, " ", toneSlot));
  const detail = el("p", { class: "row__meta" });
  const desc = el("p", { class: "visually-hidden", id: `${id}-d` });
  const legend = el("p", { class: "chart__legend" });
  const waiting = el("p", { class: "hint", text: "Starboard records a reading every minute. The chart fills in as readings arrive." });
  const plot = el("div", { class: "chart__plot" });
  const tooltip = el("div", { class: "chart__tooltip", role: "status", hidden: true });
  const svg = svgEl("svg", { class: "chart__svg", tabindex: "0", role: "img", "aria-labelledby": `${id}-h ${id}-d` });
  plot.append(svg, tooltip);
  const note = el("p", { class: "row__meta" });
  const caption = el("caption", { class: "visually-hidden" });
  const headRow = el("tr");
  const tbody = el("tbody");
  const table = el("details", { class: "disclosure" }, el("summary", { text: "Show as a table" }),
    el("div", { class: "disclosure__body" }, el("div", { class: "table-wrap" }, el("table", { class: "table" }, caption, el("thead", {}, headRow), tbody))));
  card.append(head, detail, desc, legend, waiting, plot, note, table);

  const xLabel = (t) => (o.xFormat ? o.xFormat(t, o.points[o.points.length - 1]?.t ?? t) : timeLabel(t));
  const value = (p, s) => p[s.key] ?? 0;
  let index = -1;
  let geometry = null;

  const describe = () => {
    const { points, series, format } = o;
    if (!points.length) return "No readings yet.";
    const span = o.span || (o.detail ? o.detail.toLowerCase() : "this period");
    const parts = series.map((s) => {
      const values = points.map((p) => value(p, s));
      const low = Math.min(...values), high = Math.max(...values), last = values[values.length - 1];
      return `${series.length > 1 ? `${s.name} ` : ""}between ${format(low)} and ${format(high)}, now ${format(last)}`;
    });
    return `Over ${span}: ${parts.join("; ")}.${o.tone ? ` ${o.tone[1]}.` : ""} Use the left and right arrow keys to read each value.`;
  };

  const draw = () => {
    const { points, series, format } = o;
    svg.replaceChildren();
    geometry = null;
    if (points.length < 2) return;
    const width = Math.max(240, plot.clientWidth || 320);
    const height = 180;
    const pad = { left: 60, right: 14, top: 10, bottom: 26 };
    const values = points.flatMap((p) => series.map((s) => value(p, s)));
    const top = o.max ?? (o.format === perSecond ? niceBytes : niceMax)(Math.max(...values) * 1.1);
    const t0 = points[0].t, t1 = points[points.length - 1].t;
    const x = (t) => pad.left + ((t - t0) / Math.max(1, t1 - t0)) * (width - pad.left - pad.right);
    const y = (v) => pad.top + (1 - Math.min(1, (v ?? 0) / top)) * (height - pad.top - pad.bottom);
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.setAttribute("width", width);
    svg.setAttribute("height", height);
    for (let k = 0; k <= 4; k += 1) {
      const v = (top * k) / 4;
      svg.append(svgEl("line", { x1: pad.left, x2: width - pad.right, y1: y(v), y2: y(v), class: "chart__grid" }));
      const label = svgEl("text", { x: pad.left - 6, y: y(v) + 4, class: "chart__axis", "text-anchor": "end" });
      label.textContent = format(v);
      svg.append(label);
    }
    const ticks = width < 420 ? 3 : 5;
    for (let k = 0; k < ticks; k += 1) {
      const t = t0 + ((t1 - t0) * k) / (ticks - 1);
      const label = svgEl("text", { x: x(t), y: height - 6, class: "chart__axis", "text-anchor": k === 0 ? "start" : k === ticks - 1 ? "end" : "middle" });
      label.textContent = xLabel(t);
      svg.append(label);
    }
    series.forEach((s, i) => {
      const coords = points.map((p) => `${x(p.t).toFixed(1)},${y(value(p, s)).toFixed(1)}`);
      if (series.length === 1) {
        svg.append(svgEl("polygon", { points: `${x(t0)},${y(0)} ${coords.join(" ")} ${x(t1)},${y(0)}`, class: `chart__area chart__area--${i}` }));
      }
      const line = svgEl("polyline", { points: coords.join(" "), class: `chart__line chart__line--${i}` });
      if (i === 1) line.setAttribute("stroke-dasharray", "6 4"); // the second series is dashed, so it is not colour alone
      svg.append(line);
      svg.append(svgEl("circle", { cx: x(t1), cy: y(value(points[points.length - 1], s)), r: 4, class: `chart__dot chart__dot--${i}` }));
    });
    const cross = svgEl("line", { y1: pad.top, y2: height - pad.bottom, class: "chart__cross", visibility: "hidden" });
    svg.append(cross);
    geometry = { width, pad, t0, t1, x, cross };
    if (index >= 0) show(Math.min(index, points.length - 1));
  };

  function show(i) {
    if (!geometry) return;
    const { points, series, format } = o;
    index = Math.max(0, Math.min(points.length - 1, i));
    const p = points[index];
    const { x, cross, width } = geometry;
    cross.setAttribute("x1", x(p.t)); cross.setAttribute("x2", x(p.t)); cross.setAttribute("visibility", "visible");
    tooltip.replaceChildren(el("span", { class: "chart__tooltip-time", text: xLabel(p.t) }),
      ...series.map((s, k) => el("span", { class: "chart__tooltip-row" },
        el("i", { class: k ? "chart__swatch chart__swatch--2" : "chart__swatch", "aria-hidden": "true" }), el("strong", { text: format(value(p, s)) }), ` ${s.name}`)));
    tooltip.hidden = false;
    tooltip.style.left = `${Math.min(width - 150, Math.max(0, x(p.t) + 10))}px`;
  }
  const hide = () => { geometry?.cross.setAttribute("visibility", "hidden"); tooltip.hidden = true; index = -1; };
  svg.addEventListener("pointermove", (e) => {
    if (!geometry) return;
    const { points } = o;
    const { pad, width, t0, t1 } = geometry;
    const box = svg.getBoundingClientRect();
    const t = t0 + ((e.clientX - box.left - pad.left) / (width - pad.left - pad.right)) * (t1 - t0);
    let best = 0;
    points.forEach((p, k) => { if (Math.abs(p.t - t) < Math.abs(points[best].t - t)) best = k; });
    show(best);
  });
  svg.addEventListener("pointerleave", hide);
  svg.addEventListener("blur", hide);
  svg.addEventListener("keydown", (e) => {
    const last = o.points.length - 1;
    if (e.key === "ArrowLeft" || e.key === "ArrowRight") { e.preventDefault(); show(index < 0 ? last : index + (e.key === "ArrowRight" ? 1 : -1)); }
    if (e.key === "Home") { e.preventDefault(); show(0); }
    if (e.key === "End") { e.preventDefault(); show(last); }
    if (e.key === "Escape") hide();
  });

  const render = () => {
    const { points, series, format } = o;
    const latest = points[points.length - 1];
    nowText.textContent = o.now ?? (latest
      ? (series.length > 1 ? series.map((s) => `${s.name} ${format(value(latest, s))}`).join(" · ") : `${format(value(latest, series[0]))} now`)
      : "Collecting");
    toneSlot.replaceChildren(...(o.tone ? [chip(o.tone[1], o.tone[0])] : []));
    detail.textContent = o.detail || "";
    detail.hidden = !o.detail;
    desc.textContent = describe();
    legend.replaceChildren(...(series.length > 1 ? series.map((s, i) => el("span", {},
      el("i", { class: i ? "chart__swatch chart__swatch--2" : "chart__swatch", "aria-hidden": "true" }), s.name)) : []));
    legend.hidden = series.length < 2;
    note.textContent = o.note || "";
    note.hidden = !o.note;
    const enough = points.length >= 2;
    waiting.textContent = o.waiting || "Starboard records a reading every minute. The chart fills in as readings arrive.";
    waiting.hidden = enough;
    plot.hidden = !enough;
    table.hidden = !enough;
    caption.textContent = o.title;
    headRow.replaceChildren(el("th", { scope: "col", text: "Time" }), ...series.map((s) => el("th", { scope: "col", class: "numeric", text: s.name })));
    // About 12 rows across the range, always with the latest.
    const step = Math.max(1, Math.floor(points.length / 12));
    const rows = points.filter((_, i) => i % step === 0 || i === points.length - 1);
    tbody.replaceChildren(...rows.map((p) => el("tr", {}, el("th", { scope: "row", text: xLabel(p.t) }),
      ...series.map((s) => el("td", { class: "numeric", text: format(value(p, s)) })))));
    if (plot.isConnected) draw();
  };

  card.update = (changes = {}) => { o = { ...o, ...changes }; render(); };
  render();
  requestAnimationFrame(draw);
  let lastWidth = 0;
  new ResizeObserver(() => { if (plot.clientWidth !== lastWidth) { lastWidth = plot.clientWidth; draw(); } }).observe(plot);
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

/**
 * The time range: a labelled segmented control (Last hour, 6 hours, 24 hours), remembered in this browser.
 * rangePicker(onChange, { live }) returns { element, value }; onChange(value) runs when it changes.
 * live: true adds a "Live" link to Monitor. The layout is set here so it needs no page style sheet.
 */
const RANGE_KEY = "starboard.range";
function rangePicker(onChange, { live = false } = {}) {
  let hours = "1";
  try { hours = localStorage.getItem(RANGE_KEY) || "1"; } catch { /* private window */ }
  if (!["1", "6", "24"].includes(hours)) hours = "1";
  const box = el("div", { class: "segmented" });
  for (const [value, label] of [["1", "Last hour"], ["6", "6 hours"], ["24", "24 hours"]]) {
    const input = el("input", { type: "radio", name: "range", value, checked: value === hours });
    input.addEventListener("change", () => { try { localStorage.setItem(RANGE_KEY, value); } catch { /* ignore */ } onChange(value); });
    box.append(el("label", {}, input, el("span", { text: label })));
  }
  const element = el("fieldset", { class: "range-picker" },
    el("legend", { class: "visually-hidden", text: "Time range" }),
    el("span", { class: "small muted", "aria-hidden": "true", text: "Time range" }), box,
    live ? el("a", { class: "btn btn--quiet", href: "/system-monitor.html" }, icon("chart-line"), el("span", { text: "Live" })) : null);
  Object.assign(element.style, { display: "flex", flexWrap: "wrap", alignItems: "center", gap: "var(--space-3)", margin: "0", padding: "0", border: "0", minWidth: "0" });
  return { element, get value() { return box.querySelector("input:checked").value; } };
}

const RANGE_WORDS = { 1: "the last hour", 6: "the last 6 hours", 24: "the last 24 hours" };
const percent = (v) => `${Math.round(v)}%`;
const perSecond = (v) => `${formatBytes(v)}/s`;
const degrees = (v) => `${Math.round(v)}°C`;
