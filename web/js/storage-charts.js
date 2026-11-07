// Charts for System, Storage: the pool as one bar (how full) and a ring (what fills it), each drive in the pool,
// space used over time with a forecast, and the biggest series and films. Drawn by the browser from answers the
// server already has, so they cost the server nothing. Rules as in charts.js: colours follow the media type in a
// fixed order (checked for colour blindness in light and dark), free space is grey with a hatch, every chart has
// a legend or labels, a description and a table, and every part can be reached with Tab for its value.

const MEDIA = [
  { key: "tv", name: "TV" }, { key: "movies", name: "Films" }, { key: "audiobooks", name: "Audiobooks and radio" },
  { key: "music", name: "Music" }, { key: "books", name: "Books and comics" },
  { key: "downloads", name: "Downloads waiting" }, { key: "other", name: "Everything else" },
];
const FREE = { key: "free", name: "Free space" };
const SVGNS = "http://www.w3.org/2000/svg";
let storageChartCount = 0;

function sv(tag, attrs = {}, ...kids) {
  const n = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v !== null && v !== undefined) n.setAttribute(k, v);
  kids.forEach((k) => k && n.append(k));
  return n;
}
const mediaFill = (key) => key === "free" ? `url(#${hatchId})` : `var(--media-${key})`;
const share = (b, of) => { const p = of ? (b / of) * 100 : 0; return p === 0 ? "0%" : p < 0.1 ? "under 0.1%" : p < 1 ? `${p.toFixed(1)}%` : `${Math.round(p)}%`; };
let hatchId = "media-hatch";

function hatchDefs() {
  return sv("defs", {}, sv("pattern", { id: hatchId, width: 6, height: 6, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" },
    sv("rect", { width: 6, height: 6, fill: "var(--media-free)" }), sv("line", { x1: 0, y1: 0, x2: 0, y2: 6, stroke: "var(--media-free-line)", "stroke-width": 2 })));
}

// A tooltip that follows the pointer, and the same words for keyboard and screen readers.
function markValue(node, text) {
  node.setAttribute("tabindex", "0");
  node.setAttribute("role", "img");
  node.setAttribute("aria-label", text);
  node.append(sv("title", {}, text));
}

// Types under 1% of the whole are drawn as one mark (the legend still lists each one).
function groupSmall(parts, of) {
  const big = parts.filter((p) => p.bytes / of >= 0.01);
  const small = parts.filter((p) => p.bytes > 0 && p.bytes / of < 0.01);
  if (small.length < 2) return parts.filter((p) => p.bytes > 0);
  return [...big, { key: "other", name: "Smaller types", bytes: small.reduce((n, p) => n + p.bytes, 0), parts: small }];
}

function mediaLegend(parts, of, { free } = {}) {
  const rows = [...parts.filter((p) => p.bytes > 0), ...(free ? [free] : [])];
  return el("ul", { class: "media-legend" }, rows.map((p) => {
    const sw = el("span", { class: `media-legend__swatch media-legend__swatch--${p.key}`, "aria-hidden": "true" });
    return el("li", {}, sw, el("span", { text: p.name }),
      el("span", { class: "numeric", text: formatBytes(p.bytes) }), el("span", { class: "numeric muted", text: share(p.bytes, of) }));
  }));
}

function mediaTable(caption, parts, of) {
  return el("details", { class: "chart__table" }, el("summary", { text: "Show as a table" }),
    el("div", { class: "table-scroll" }, el("table", {}, el("caption", { class: "visually-hidden", text: caption }),
      el("thead", {}, el("tr", {}, ["Type", "Size", "Share"].map((h) => el("th", { scope: "col", text: h })))),
      el("tbody", {}, parts.map((p) => el("tr", {}, el("th", { scope: "row", text: p.name }),
        el("td", { class: "num", text: formatBytes(p.bytes) }), el("td", { class: "num", text: share(p.bytes, of) })))))));
}

// One bar for the whole pool: each type, then free space. The marks stretch to the width; the labels are HTML
// under the marks wide enough to hold them, so text never stretches and follows Text size.
function poolBar(parts, total) {
  const W = 1000, H = 40;
  const svg = sv("svg", { class: "media-bar", viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "none", role: "group", "aria-label": "The pool by type, then free space" }, hatchDefs());
  const labels = el("div", { class: "media-bar__labels", "aria-hidden": "true" });
  let x = 0;
  for (const p of parts) {
    const w = (p.bytes / total) * W;
    if (w <= 0) continue;
    const rect = sv("rect", { class: "media-mark", x: x.toFixed(1), y: 0, width: Math.max(w - 2, 1.5).toFixed(1), height: H, fill: mediaFill(p.key) });
    markValue(rect, `${p.name}: ${formatBytes(p.bytes)}, ${share(p.bytes, total)}${p.parts ? ` (${p.parts.map((q) => q.name).join(", ")})` : ""}`);
    svg.append(rect);
    if (w > 130) {
      const label = el("span", { class: "media-bar__label", text: `${p.name} ${formatBytes(p.bytes)}` });
      label.style.left = `${(x / W) * 100}%`;
      label.style.maxWidth = `${(w / W) * 100}%`;
      labels.append(label);
    }
    x += w;
  }
  return el("div", { class: "media-bar-wrap" }, svg, labels);
}

// A ring of what fills the pool (no free space, so the types compare with each other); the total in the middle.
function mediaRing(parts, total, middle) {
  const size = 220, R = size / 2 - 2, r = R * 0.62, c = size / 2;
  const svg = sv("svg", { class: "media-ring", viewBox: `0 0 ${size} ${size}`, role: "group", "aria-label": "Share of each type" });
  const at = (a, rad) => `${(c + rad * Math.cos(a)).toFixed(2)} ${(c + rad * Math.sin(a)).toFixed(2)}`;
  let a = -Math.PI / 2;
  const drawn = parts.filter((p) => p.bytes > 0);
  for (const p of drawn) {
    const da = (p.bytes / total) * Math.PI * 2;
    if (drawn.length === 1) {
      svg.append(sv("circle", { cx: c, cy: c, r: (R + r) / 2, fill: "none", stroke: mediaFill(p.key), "stroke-width": R - r }));
      break;
    }
    const b = a + da, large = da > Math.PI ? 1 : 0;
    const path = sv("path", { class: "media-mark", fill: mediaFill(p.key),
      d: `M ${at(a, R)} A ${R} ${R} 0 ${large} 1 ${at(b, R)} L ${at(b, r)} A ${r} ${r} 0 ${large} 0 ${at(a, r)} Z` });
    markValue(path, `${p.name}: ${formatBytes(p.bytes)}, ${share(p.bytes, total)}`);
    svg.append(path);
    a = b;
  }
  svg.append(sv("text", { class: "media-ring__value", x: c, y: c + 2, "text-anchor": "middle" }, middle[0]),
    sv("text", { class: "media-ring__label", x: c, y: c + 24, "text-anchor": "middle" }, middle[1]));
  return svg;
}

/**
 * The pool card: how full (bar), and what fills it (ring), when the space has been sorted by type.
 * disk: {label, total, used, free}; types: {tv: bytes, ...} or null; when: words; action: a node (the button).
 */
function poolCard(disk, types, when, action) {
  const id = `pool-${++storageChartCount}`;
  const parts = types ? MEDIA.map((m) => ({ ...m, bytes: types[m.key] || 0 })) : [];
  const counted = parts.reduce((n, p) => n + p.bytes, 0);
  if (types && disk.used > counted) {
    // What the folder reading cannot see (file system overhead, hidden files) joins Everything else.
    parts.find((p) => p.key === "other").bytes += disk.used - counted;
  }
  const free = { ...FREE, bytes: disk.free };
  const pct = Math.round((disk.used / disk.total) * 100);
  const barParts = types ? [...groupSmall(parts, disk.total), free] : [{ key: "used", name: "Used", bytes: disk.used }, free];
  const sentence = types
    ? `${disk.label}: ${formatBytes(disk.total)}, ${pct}% full. ${parts.filter((p) => p.bytes / disk.used >= 0.05).map((p) => `${p.name} ${formatBytes(p.bytes)}`).join(", ")}; ${formatBytes(disk.free)} free.`
    : `${disk.label}: ${formatBytes(disk.used)} of ${formatBytes(disk.total)} used, ${formatBytes(disk.free)} free.`;
  return el("section", { class: "panel chart media-pool", "aria-labelledby": `${id}-h` },
    el("div", { class: "chart__head" }, el("h2", { id: `${id}-h`, text: disk.label }),
      el("span", { class: "chart__value numeric", text: `${pct}% full · ${formatBytes(disk.free)} free of ${formatBytes(disk.total)}` })),
    el("p", { class: "visually-hidden", text: sentence }),
    poolBar(barParts, disk.total),
    types ? el("div", { class: "media-pool__split" },
      mediaRing(groupSmall(parts, disk.used), disk.used, [formatBytes(disk.used), "of media and files"]),
      mediaLegend(parts, disk.used)) : el("p", { class: "muted", text: "Sort the space by type (TV, films, books and so on) with Sort by type." }),
    el("div", { class: "media-pool__foot" }, el("span", { class: "small muted", text: when }), action),
    types ? mediaTable(`${disk.label} by type`, [...parts.filter((p) => p.bytes > 0), free], disk.total) : null);
}

/** Each drive in the pool, bar length by size, fullest first. onOpen(label, opener) opens its details. */
function drivesChart(drives, onOpen) {
  const biggest = Math.max(...drives.map((d) => d.total));
  const sorted = [...drives].sort((a, b) => b.used / b.total - a.used / a.total);
  const list = el("ul", { class: "drive-bars" }, sorted.map((d) => {
    const pct = Math.round((d.used / d.total) * 100);
    const tone = pct >= 98 ? "danger" : pct >= 90 ? "warning" : null;
    const track = el("span", { class: "drive-bars__track" });
    track.style.width = `${Math.max(8, (d.total / biggest) * 100)}%`;
    const fill = el("span", { class: "drive-bars__fill", "data-tone": tone });
    fill.style.width = `${pct}%`;
    track.append(fill);
    return el("li", {},
      el("button", { type: "button", class: "drive-bars__name", "aria-haspopup": "dialog", onclick: (e) => onOpen(d.label, e.currentTarget) }, d.label),
      el("span", { class: "drive-bars__bar", role: "img", "aria-label": `${pct}% used` }, track),
      el("span", { class: "numeric small", text: `${pct}% · ${formatBytes(d.free)} free of ${formatBytes(d.total)}` }),
      tone ? chip(tone === "danger" ? "Full" : "Nearly full", tone) : null);
  }));
  return [list, el("details", { class: "chart__table" }, el("summary", { text: "Show as a table" }),
    el("div", { class: "table-scroll" }, el("table", {}, el("caption", { class: "visually-hidden", text: "Drives in the pool" }),
      el("thead", {}, el("tr", {}, ["Drive", "Size", "Used", "Free"].map((h) => el("th", { scope: "col", text: h })))),
      el("tbody", {}, sorted.map((d) => el("tr", {}, el("th", { scope: "row", text: d.label }), el("td", { class: "num", text: formatBytes(d.total) }),
        el("td", { class: "num", text: `${formatBytes(d.used)} (${Math.round((d.used / d.total) * 100)}%)` }), el("td", { class: "num", text: formatBytes(d.free) })))))))];
}

// Least squares over the readings: bytes a day. Needs a week, so one busy day does not decide it.
function growthRate(points) {
  if (points.length < 7) return null;
  const n = points.length, mx = points.reduce((s, p) => s + p.day, 0) / n, my = points.reduce((s, p) => s + p.used, 0) / n;
  const num = points.reduce((s, p) => s + (p.day - mx) * (p.used - my), 0), den = points.reduce((s, p) => s + (p.day - mx) ** 2, 0);
  return den ? num / den : null;
}

/**
 * Space used each day for one folder, with a dashed forecast to full when it is growing.
 * readings: [{date: "YYYY-MM-DD", used, total}] oldest first.
 */
function growthChart(label, readings, width = 640) {
  const pts = readings.slice(-90).map((r) => ({ ...r, day: Date.parse(`${r.date}T12:00:00`) / 86400000 }));
  const last = pts[pts.length - 1];
  const rate = growthRate(pts);
  const daysLeft = rate && rate > 0 ? (last.total - last.used) / rate : null;
  const fullOn = daysLeft ? new Date((last.day + daysLeft) * 86400000) : null;
  const sentence = pts.length < 7
    ? `Starboard has ${pts.length} ${pts.length === 1 ? "day" : "days"} of readings. The forecast appears after a week.`
    : !rate || rate <= 0 ? `${label} has not grown over the last ${pts.length} days.`
      : `${label} grows by about ${formatBytes(rate * 30)} a month. At this rate it is full in about ${daysLeft > 730 ? `${Math.round(daysLeft / 365)} years` : daysLeft > 60 ? `${Math.round(daysLeft / 30)} months` : `${Math.round(daysLeft)} days`} (${fullOn.toLocaleDateString("en-GB", { month: "long", year: "numeric" })}).`;
  const W = Math.max(320, Math.round(width)), H = 220, pad = { l: 64, r: 12, t: 18, b: 24 }; // drawn at the real width
  const ahead = daysLeft ? Math.min(daysLeft, Math.max(30, pts.length)) : 0;
  const d0 = pts[0].day, d1 = last.day + ahead;
  const low = Math.min(...pts.map((p) => p.used)) * 0.98, high = last.total;
  const x = (d) => pad.l + ((d - d0) / Math.max(1, d1 - d0)) * (W - pad.l - pad.r);
  const y = (v) => pad.t + (1 - (v - low) / Math.max(1, high - low)) * (H - pad.t - pad.b);
  const svg = sv("svg", { class: "growth", viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": sentence });
  for (let i = 0; i <= 3; i++) {
    const v = low + ((high - low) * i) / 3;
    svg.append(sv("line", { class: "chart__grid", x1: pad.l, x2: W - pad.r, y1: y(v), y2: y(v) }),
      sv("text", { class: "chart__axis", x: pad.l - 6, y: y(v) + 4, "text-anchor": "end" }, formatBytes(v)));
  }
  svg.append(sv("line", { class: "growth__limit", x1: pad.l, x2: W - pad.r, y1: y(high), y2: y(high) }),
    sv("text", { class: "chart__axis", x: W - pad.r, y: y(high) - 5, "text-anchor": "end" }, "Size of the pool"));
  if (pts.length > 1) svg.append(sv("path", { class: "growth__line", d: pts.map((p, i) => `${i ? "L" : "M"}${x(p.day).toFixed(1)},${y(p.used).toFixed(1)}`).join(" ") }));
  else svg.append(sv("circle", { class: "growth__dot", cx: x(last.day), cy: y(last.used), r: 4 }));
  if (ahead) svg.append(sv("path", { class: "growth__forecast", d: `M${x(last.day)},${y(last.used)} L${x(d1)},${y(last.used + rate * ahead)}` }));
  const legend = el("p", { class: "chart__legend" }, el("span", {}, el("i", { class: "chart__swatch", "aria-hidden": "true" }), "Used"),
    ahead ? el("span", {}, el("i", { class: "chart__swatch chart__swatch--2", "aria-hidden": "true" }), "Forecast") : null);
  const table = el("details", { class: "chart__table" }, el("summary", { text: "Show as a table" }),
    el("div", { class: "table-scroll" }, el("table", {}, el("thead", {}, el("tr", {}, ["Day", "Used", "Free"].map((h) => el("th", { scope: "col", text: h })))),
      el("tbody", {}, pts.slice().reverse().slice(0, 60).map((p) => el("tr", {}, el("th", { scope: "row", text: p.date }),
        el("td", { class: "num", text: formatBytes(p.used) }), el("td", { class: "num", text: formatBytes(p.total - p.used) })))))));
  return [el("p", { class: "growth__sentence", text: sentence }), svg, legend, table];
}

/** The biggest folders in the library, coloured by type. */
function biggestChart(items) {
  const top = Math.max(...items.map((i) => i.bytes), 1);
  const name = (k) => (MEDIA.find((m) => m.key === k) || {}).name || "";
  const list = el("ul", { class: "biggest" }, items.map((i) => {
    const fill = el("span", { class: `biggest__fill media-fill--${i.type}` });
    fill.style.width = `${Math.max(1, (i.bytes / top) * 100)}%`;
    return el("li", { tabindex: "0", title: `${i.name} (${name(i.type)}): ${formatBytes(i.bytes)}` },
      el("span", { class: "biggest__name" }, el("span", { text: i.name }), el("span", { class: "small muted", text: ` ${name(i.type)}` })),
      el("span", { class: "biggest__track" }, fill), el("span", { class: "numeric small", text: formatBytes(i.bytes) }));
  }));
  const types = [...new Set(items.map((i) => i.type))];
  return [list, el("ul", { class: "media-legend media-legend--inline" }, types.map((t) => el("li", {},
    el("span", { class: `media-legend__swatch media-legend__swatch--${t}`, "aria-hidden": "true" }), el("span", { text: name(t) }))))];
}
