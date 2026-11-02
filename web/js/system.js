// System overview: summary tiles that say a warning in words, Needs attention (each warning opens a
// slide-out with the full message), then charts over the chosen time range. Charts update in place.

let range = null;
let config = null;
const charts = {};

function checkAgainLabel(button) { button.replaceChildren(icon("refresh-cw"), el("span", { text: "Check again" })); }

function tile(value, label, tone) {
  return el("div", { class: "stat", "data-tone": tone ? tone[0] : null },
    el("span", { class: "stat__value", text: value }), el("span", { class: "stat__label", text: label }), tone ? chip(tone[1], tone[0]) : null);
}

const tempTone = (c) => (c == null ? null : c >= 85 ? ["danger", "Very hot"] : c >= 75 ? ["warning", "Hot"] : null);
const busyTone = (pct, word) => (pct >= 90 ? ["warning", word] : null);
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
const timeNow = () => new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });

function uptime(seconds) {
  if (!seconds) return "Up for an unknown time";
  const d = Math.floor(seconds / 86400), h = Math.floor((seconds % 86400) / 3600);
  return d ? `Up ${plural(d, "day", "days")}` : `Up ${plural(h, "hour", "hours")}`;
}

// Needs attention ---------------------------------------------------------------------------------

const TONE_ORDER = { danger: 0, warning: 1, info: 2 };

function warnings(health, disks) {
  const byId = Object.fromEntries((config?.services || []).map((s) => [s.id, s]));
  const byName = Object.fromEntries((config?.services || []).map((s) => [s.name, s]));
  const items = [];
  for (const e of health.errors || []) {
    const s = byId[e.service];
    const name = s?.name || e.service;
    items.push({ key: `error:${e.service}`, kind: "error", tone: "danger", word: "Not responding", service: s, name,
      title: `${name} is not responding`, meta: `${name} · asked at ${timeNow()}`, message: e.message });
  }
  for (const h of health.items || []) {
    const tone = h.level === "error" ? "danger" : h.level === "warning" ? "warning" : "info";
    items.push({ key: `app:${h.service_name}:${h.message}`, kind: "app", tone, word: tone === "danger" ? "Error" : tone === "warning" ? "Needs attention" : "Note",
      service: byName[h.service_name], name: h.service_name, title: h.message, meta: `${h.service_name} · from its own health check`, message: h.message });
  }
  for (const d of disks?.disks || []) {
    if (d.passed !== false && !d.problems.length) continue;
    const name = `${d.model}${d.device ? ` (${d.device.replace("/dev/", "")})` : ""}`;
    items.push({ key: `disk:${d.serial || d.device || d.model}`, kind: "disk", tone: d.passed === false ? "danger" : "warning",
      word: d.passed === false ? "Failing" : "Needs attention",
      title: d.passed === false ? `${name} failed its health check` : `${name}: ${d.problems.map((p) => `${p.value.toLocaleString("en-GB")} ${p.name.toLowerCase()}`).join(", ")}`,
      meta: `Disk health · report from ${formatDate(d.checked * 1000, true)}` });
  }
  return items.sort((a, b) => TONE_ORDER[a.tone] - TONE_ORDER[b.tone]);
}

function openWarning(item, opener) {
  const s = item.service;
  const facts = item.kind === "error"
    ? [["App", item.name], ["What happened", "Starboard asked for its warnings and had no answer"], ["Asked at", timeNow()]]
    : [["From", `${item.name}'s own health check`], ["Level", item.word], ["Checked at", timeNow()]];
  sidePanel({
    title: item.kind === "error" ? `${item.name} is not responding` : `Warning from ${item.name}`,
    opener,
    body: [
      chip(item.word, item.tone),
      el("p", { class: "sys-message", text: item.message }),
      el("dl", { class: "facts" }, facts.flatMap(([k, v]) => [el("dt", { text: k }), el("dd", { text: v })])),
      item.kind === "error" ? el("p", { class: "small muted", text: "Check that the app is running and that its address in Settings, Manage apps is right." }) : null,
    ],
    foot: [
      s?.link ? el("a", { class: "btn btn--primary", href: reachableUrl(s.link), target: "_blank", rel: "noopener noreferrer" },
        icon("external-link"), el("span", { text: `Open ${item.name}` }), el("span", { class: "visually-hidden", text: " (opens in a new tab)" })) : null,
      el("a", { class: "btn", href: "/index.html", text: "View in Apps" }),
    ].filter(Boolean),
  });
}

function warningRow(item) {
  const lead = item.service ? appIcon(item.service, "app-icon") : el("span", { class: "sys-lead", "aria-hidden": "true" }, icon(item.kind === "disk" ? "hard-drive" : "circle-alert"));
  const titleControl = item.kind === "disk"
    ? el("a", { href: "/system-disks.html", text: item.title })
    : el("button", { type: "button", "aria-haspopup": "dialog", text: item.title, onclick: (e) => openWarning(item, e.currentTarget) });
  return el("li", { class: "row row--opens sys-row--lead" }, lead,
    el("div", {}, el("p", { class: "row__title clamp-2" }, titleControl), el("p", { class: "row__meta", text: item.meta })),
    el("div", { class: "row__side" }, chip(item.word, item.tone)));
}

function renderWarnings(items) {
  const box = $("#health");
  const panel = $("#health-panel");
  panel.removeAttribute("aria-busy");
  const worst = items.some((i) => i.tone === "danger") ? "danger" : items.some((i) => i.tone === "warning") ? "warning" : null;
  if (worst) panel.dataset.tone = worst; else delete panel.dataset.tone;
  if (!items.length) {
    box.replaceChildren(el("div", { class: "empty" }, icon("circle-check", 32),
      el("h3", { text: "Nothing needs attention" }), el("p", { text: "Your apps and disks report no problems." })));
    return;
  }
  let list = $("ul.rows", box);
  if (!list) { list = el("ul", { class: "rows" }); box.replaceChildren(list); }
  renderKeyed(list, items, (i) => i.key, (item) => warningRow(item));
}

// Charts ------------------------------------------------------------------------------------------

function makeCharts() {
  const base = { level: 3, points: [] };
  charts.cpu = lineChart({ ...base, title: "Processor", series: [{ key: "cpu", name: "Processor" }], format: percent, max: 100 });
  charts.mem = lineChart({ ...base, title: "Memory", series: [{ key: "mem", name: "Memory" }], format: percent, max: 100 });
  charts.temp = lineChart({ ...base, title: "Processor temperature", series: [{ key: "temp", name: "Temperature" }], format: degrees, max: 100 });
  charts.net = lineChart({ ...base, title: "Network", series: [{ key: "rx", name: "Download" }, { key: "tx", name: "Upload" }], format: perSecond });
  $("#charts").replaceChildren(charts.cpu, charts.mem, charts.temp, charts.net);
}

async function load() {
  try {
    const [sys, hist, health, disks] = await Promise.all([
      api("/api/system"), api(`/api/history?hours=${range.value}`), api("/api/health"),
      api("/api/disk-health").catch(() => null)]);
    const points = hist.points || [];
    const last = points[points.length - 1] || {};
    const memUsed = sys.memory.total - sys.memory.available;
    const memPct = sys.memory.total ? (memUsed / sys.memory.total) * 100 : 0;
    const temp = last.temp;
    const load1 = sys.load.length ? sys.load[0] : null;
    $("#stats").replaceChildren(
      tile(points.length ? percent(last.cpu) : "Not recorded yet", "Processor", points.length ? busyTone(last.cpu, "Busy") : null),
      tile(formatBytes(memUsed), `Memory used of ${formatBytes(sys.memory.total)} (${percent(memPct)})`, busyTone(memPct, "Nearly full")),
      tile(temp != null ? degrees(temp) : "Not reported", "Processor temperature", tempTone(temp)),
      tile(load1 != null ? load1.toFixed(1) : "Not reported", `Load, ${plural(sys.cpus, "thread", "threads")}`, load1 > sys.cpus ? ["warning", "Busy"] : null));

    const items = warnings(health, disks);
    renderWarnings(items);

    const span = RANGE_WORDS[hist.hours] || "the last hour";
    $("#range-title").textContent = span.replace(/^the l/, "L");
    const latest = points[points.length - 1];
    charts.cpu.update({ points, span, tone: latest ? busyTone(latest.cpu, "Busy") : null });
    charts.mem.update({ points, span, tone: latest ? busyTone(latest.mem, "Nearly full") : null });
    const tempPoints = points.filter((p) => p.temp != null);
    charts.temp.hidden = !tempPoints.length;
    if (tempPoints.length) charts.temp.update({ points: tempPoints, span, tone: tempTone(temp) });
    charts.net.update({ points, span });

    const count = items.filter((i) => i.tone !== "info").length;
    $("#system-summary").textContent = `${uptime(sys.uptime_seconds)} · ${count ? plural(count, "warning", "warnings") : "no warnings"} · updated at ${timeNow()}`;
  } catch (e) {
    $("#system-summary").textContent = `Could not load the system details: ${e.message}`;
  }
}

startPage().then(async () => {
  checkAgainLabel($("#refresh"));
  range = rangePicker(() => load(), { live: true });
  $("#range-row").append(range.element);
  makeCharts();
  config = await api("/api/config").catch(() => null);
  $("#refresh").addEventListener("click", async () => { await load(); announce("Checked again."); });
  load();
});
