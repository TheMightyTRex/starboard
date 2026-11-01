// System overview: summary tiles with a trend line, charts over the chosen time range, and app warnings.

let range = null;

function tile(label, value, values, max, tone) {
  return el("div", { class: "stat", "data-tone": tone || "" },
    el("span", { class: "stat__label", text: label }),
    el("div", { class: "stat__trend" }, el("span", { class: "stat__value", text: value }), trendLine(values, max)));
}

function uptime(seconds) {
  if (!seconds) return "Unknown";
  const d = Math.floor(seconds / 86400), h = Math.floor((seconds % 86400) / 3600);
  return d ? `${d} days ${h} hours` : `${h} hours`;
}

async function load() {
  try {
    const [sys, hist, health] = await Promise.all([api("/api/system"), api(`/api/history?hours=${range.value}`), api("/api/health")]);
    const points = hist.points;
    const last = points[points.length - 1] || {};
    const memUsed = sys.memory.total - sys.memory.available;
    const memPct = (memUsed / sys.memory.total) * 100;
    const col = (key) => points.map((p) => p[key]);
    const temp = last.temp;
    $("#stats").replaceChildren(
      tile("Processor", points.length ? percent(last.cpu) : "–", col("cpu"), 100, last.cpu >= 90 ? "warning" : ""),
      tile("Memory", percent(memPct), col("mem"), 100, memPct >= 90 ? "warning" : ""),
      tile(`Load on ${sys.cpus} threads`, sys.load.length ? sys.load[0].toFixed(2) : "–", col("load"), Math.max(sys.cpus, ...col("load")), sys.load[0] > sys.cpus ? "warning" : ""),
      tile("Processor temperature", temp != null ? degrees(temp) : "Not reported", col("temp"), 100, temp >= 85 ? "danger" : ""));
    const detail = { 1: "Last hour", 6: "Last 6 hours", 24: "Last 24 hours" }[hist.hours];
    $("#charts").replaceChildren(
      lineChart({ title: "Processor use", detail, points, series: [{ key: "cpu", name: "Processor" }], format: percent, max: 100 }),
      lineChart({ title: "Memory use", detail, points, series: [{ key: "mem", name: "Memory" }], format: percent, max: 100 }),
      lineChart({ title: "Network", detail, points, series: [{ key: "rx", name: "Download", short: "↓" }, { key: "tx", name: "Upload", short: "↑" }], format: perSecond }),
      lineChart({ title: "Disk activity", detail, points, series: [{ key: "read", name: "Read", short: "Read" }, { key: "write", name: "Write", short: "Write" }], format: perSecond }),
      lineChart({ title: "Processor temperature", detail, points, series: [{ key: "temp", name: "Temperature" }], format: degrees }));
    const list = $("#health");
    list.replaceChildren();
    for (const e of health.errors) list.append(el("li", { class: "row" }, el("p", { text: e.message }), el("div", { class: "row__side" }, chip("Not responding", "danger"))));
    for (const h of health.items) {
      const tone = h.level === "error" ? "danger" : h.level === "warning" ? "warning" : "info";
      list.append(el("li", { class: "row" },
        el("div", {}, el("p", { class: "row__title", text: h.service_name }), el("p", { class: "row__meta", text: h.message })),
        el("div", { class: "row__side" }, chip(tone === "info" ? "Note" : "Needs attention", tone))));
    }
    if (!list.children.length) list.append(el("li", { class: "empty", text: "Nothing needs attention." }));
    $("#system-summary").textContent = `Up ${uptime(sys.uptime_seconds)} · ${health.items.length} warnings · updated ${new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}`;
  } catch (e) {
    $("#system-summary").textContent = e.message;
  }
}

startPage().then(() => {
  range = rangePicker(load);
  $("#range-row").append(range.element);
  $("#refresh").addEventListener("click", load);
  load();
});
