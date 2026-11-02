// Monitor: live charts while the page is open, using the same line chart as Overview. The server sends raw
// counters; rates are worked out here. Charts and thread meters update in place, so focus stays where it is.

let every = 2; // seconds between readings; Settings, Performance
let POINTS = 90; // 3 minutes of readings
const points = [];
let previous = null;
let timer = null;
let charts = null;
const threadRows = [];

const rate = (n) => `${formatBytes(n)}/s`;
const sum = (o, i) => Object.values(o).reduce((t, v) => t + v[i], 0);
const tempTone = (c) => (c == null ? null : c >= 85 ? ["danger", "Very hot"] : c >= 75 ? ["warning", "Hot"] : null);
const packageTemp = (m) => (m.temps.find((t) => /package|tctl|tdie/i.test(t.label)) || m.temps[0] || {}).c;
const SPAN = "the last 3 minutes";

// Axis and table labels count back from now: "3 min ago", "40 s ago", "now".
function ago(t, last) {
  const s = Math.round(last - t);
  if (s < 1) return "now";
  if (s < 60) return `${s} s ago`;
  return `${Number((s / 60).toFixed(1))} min ago`;
}

function makeCharts() {
  const base = { points: [], span: SPAN, xFormat: ago, waiting: "Reading the server. The chart starts in a few seconds." };
  charts = {
    cpu: lineChart({ ...base, title: "Processor", series: [{ key: "cpu", name: "Processor" }], format: percent, max: 100 }),
    mem: lineChart({ ...base, title: "Memory", series: [{ key: "mem", name: "Memory" }], format: percent, max: 100 }),
    temp: lineChart({ ...base, title: "Processor temperature", series: [{ key: "temp", name: "Temperature" }], format: degrees, max: 100 }),
    net: lineChart({ ...base, title: "Network", series: [{ key: "rx", name: "Download" }, { key: "tx", name: "Upload" }], format: perSecond }),
    disk: lineChart({ ...base, title: "Disk activity", series: [{ key: "read", name: "Read" }, { key: "write", name: "Write" }], format: perSecond }),
  };
  $("#charts").replaceChildren(...Object.values(charts));
}

function renderThreads(cores) {
  const list = $("#threads");
  cores.forEach((c, i) => {
    let r = threadRows[i];
    if (!r) {
      const value = el("span", { class: "numeric" });
      const fill = el("span");
      const bar = el("div", { class: "progress", "aria-hidden": "true" }, fill);
      const node = el("li", { class: "meter" }, el("div", { class: "meter__label" }, el("span", { text: `Thread ${i + 1}` }), value), bar);
      r = threadRows[i] = { node, value, fill, bar };
      list.append(node);
    }
    const busy = c >= 90;
    r.value.textContent = `${Math.round(c)}%${busy ? ", busy" : ""}`;
    r.fill.style.width = `${Math.max(1, Math.min(100, c))}%`;
    if (busy) r.bar.dataset.tone = "warning"; else delete r.bar.dataset.tone;
  });
}

function render(m, rates) {
  const memUsed = m.memory.total - m.memory.available;
  const pkg = packageTemp(m);
  const up = m.uptime_seconds || 0;
  $("#monitor-machine").textContent = [m.cpu.model, `up ${Math.floor(up / 86400)} days ${Math.floor((up % 86400) / 3600)} hours`,
    m.cpu.load.length ? `load ${m.cpu.load.map((l) => l.toFixed(2)).join(", ")} (1, 5 and 15 minutes)` : null].filter(Boolean).join(" · ");
  $("#threads-detail").textContent = `${m.cpu.threads} threads, now`;
  charts.cpu.update({ points, tone: rates.cpu >= 90 ? ["warning", "Busy"] : null });
  charts.mem.update({ points, note: [`${formatBytes(memUsed)} used of ${formatBytes(m.memory.total)}`, `${formatBytes(m.memory.cached)} cache`, `${formatBytes(m.memory.available)} free`,
    m.memory.swap_total ? `swap ${formatBytes(m.memory.swap_total - m.memory.swap_free)} of ${formatBytes(m.memory.swap_total)}` : null].filter(Boolean).join(" · ") });
  const tempPoints = points.filter((p) => p.temp != null);
  charts.temp.hidden = !tempPoints.length;
  if (tempPoints.length) {
    charts.temp.update({ points: tempPoints, tone: tempTone(pkg),
      note: m.temps.filter((t) => !/^Core /.test(t.label)).slice(0, 6).map((t) => `${t.chip === t.label ? t.chip : `${t.chip} ${t.label}`} ${Math.round(t.c)}°C`).join(" · ") });
  }
  charts.net.update({ points, detail: Object.keys(m.net).join(", ") || null });
  charts.disk.update({ points, detail: Object.keys(m.disks).length ? plural(Object.keys(m.disks).length) : null });
  renderThreads(rates.cores);
}

const plural = (n) => `${n} ${n === 1 ? "disk" : "disks"}`;

// Each app's share of the whole processor since the last reading, and its memory. Needs per-app use (installer).
function renderApps(m, prev, dt) {
  $("#apps-panel").hidden = !m.apps;
  if (!m.apps || !prev?.apps) return;
  const before = new Map(prev.apps.map((a) => [a.name, a.cpu_usec]));
  const rows = m.apps.map((a) => ({ ...a, cpu: before.has(a.name) ? Math.max(0, (a.cpu_usec - before.get(a.name)) / (dt * 1e6 * m.cpu.threads)) * 100 : 0 }))
    .sort((a, b) => b.cpu - a.cpu || b.memory - a.memory).slice(0, 12);
  $("#apps-detail").textContent = `The ${rows.length} busiest of ${m.apps.length}, now`;
  const tbody = $("#apps-use tbody") || (() => {
    const body = el("tbody");
    $("#apps-use").replaceChildren(el("div", { class: "table-wrap", "data-stack": true }, el("table", { class: "table" },
      el("caption", { class: "visually-hidden", text: "Processor and memory for each app, busiest first" }),
      el("thead", {}, el("tr", {}, el("th", { scope: "col", text: "App" }), el("th", { scope: "col", class: "numeric", text: "Processor" }), el("th", { scope: "col", class: "numeric", text: "Memory" }))),
      body)));
    return body;
  })();
  tbody.replaceChildren(...rows.map((a) => el("tr", {},
    el("th", { scope: "row", "data-label": "App", text: a.name }),
    el("td", { "data-label": "Processor", class: "numeric", text: `${a.cpu < 0.1 ? "under 0.1" : a.cpu.toFixed(1)}%` }),
    el("td", { "data-label": "Memory", class: "numeric", text: formatBytes(a.memory) }))));
}

async function tick() {
  if (document.hidden) return;
  try {
    const m = await api("/api/monitor");
    if (previous) {
      const dt = Math.max(0.5, m.time - previous.time);
      const busy = (a, b) => (b && a ? Math.max(0, 100 * (1 - (a[1] - b[1]) / Math.max(1, a[0] - b[0]))) : 0);
      const rates = {
        cpu: busy(m.cpu.total, previous.cpu.total),
        cores: m.cpu.cores.map((c, i) => busy(c, previous.cpu.cores[i])),
        rx: Math.max(0, (sum(m.net, 0) - sum(previous.net, 0)) / dt), tx: Math.max(0, (sum(m.net, 1) - sum(previous.net, 1)) / dt),
        read: Math.max(0, (sum(m.disks, 0) - sum(previous.disks, 0)) / dt), write: Math.max(0, (sum(m.disks, 1) - sum(previous.disks, 1)) / dt),
      };
      const pkg = packageTemp(m);
      points.push({ t: m.time, cpu: rates.cpu, mem: ((m.memory.total - m.memory.available) / m.memory.total) * 100,
        rx: rates.rx, tx: rates.tx, read: rates.read, write: rates.write, temp: pkg ?? null });
      if (points.length > POINTS) points.shift();
      render(m, rates);
      renderApps(m, previous, dt);
    }
    previous = m;
  } catch (e) {
    $("#monitor-summary").textContent = `Could not read the server: ${e.message}`;
  }
}

// Pause keeps one label; aria-pressed says whether it is on.
function setRunning(on) {
  clearInterval(timer);
  timer = on ? setInterval(tick, every * 1000) : null;
  $("#pause").setAttribute("aria-pressed", String(!on));
  $("#monitor-summary").textContent = on
    ? `Live while this page is open · every ${every} seconds · last 3 minutes`
    : "Paused · press Pause again to carry on";
  if (on) tick();
}

startPage().then(async () => {
  const cfg = await api("/api/config").catch(() => null);
  every = cfg?.performance?.monitor_refresh || 2;
  POINTS = Math.round(180 / every);
  const pause = $("#pause");
  pause.replaceChildren(icon("pause"), el("span", { text: "Pause" }));
  pause.addEventListener("click", () => { setRunning(!timer); announce(timer ? "Monitor carrying on." : "Monitor paused."); });
  makeCharts();
  document.addEventListener("visibilitychange", () => { if (!document.hidden && timer) tick(); });
  setRunning(true);
});
