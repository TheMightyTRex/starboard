// Monitor: live charts while the page is open. The server sends raw counters; rates are worked out here.

const POINTS = 90;
const history = { cpu: [], mem: [], rx: [], tx: [], read: [], write: [], temp: [] };
let previous = null;
let timer = null;
const SVG = "http://www.w3.org/2000/svg";

function push(list, value) { list.push(value); if (list.length > POINTS) list.shift(); }

function sparkline(series, max, label) {
  const w = 300, h = 80;
  const top = max || Math.max(1, ...series.flat());
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
  svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("class", "spark");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", label);
  for (const y of [h - 2, h / 2]) {
    const line = document.createElementNS(SVG, "line");
    Object.entries({ x1: 0, x2: w, y1: y, y2: y, class: y === h / 2 ? "spark__grid spark__grid--mid" : "spark__grid" }).forEach(([k, v]) => line.setAttribute(k, v));
    svg.append(line);
  }
  series.forEach((values, i) => {
    const line = document.createElementNS(SVG, "polyline");
    line.setAttribute("points", values.map((v, k) => `${((w * (k + POINTS - values.length)) / (POINTS - 1)).toFixed(1)},${(h - 2 - (h - 6) * Math.min(1, v / top)).toFixed(1)}`).join(" "));
    line.setAttribute("class", `spark__line spark__line--${i}`);
    svg.append(line);
  });
  return svg;
}

function chart(title, detail, big, svg, legend = []) {
  return el("section", { class: "panel chart" },
    el("div", { class: "chart__head" }, el("h2", { text: title }), el("span", { class: "row__meta", text: detail })),
    el("p", { class: "chart__big num", text: big }),
    svg,
    legend.length ? el("p", { class: "chart__legend" }, legend.map(([text, i]) => el("span", {}, i !== undefined ? el("i", { class: `swatch swatch--${i}`, "aria-hidden": "true" }) : null, text))) : null);
}

const rate = (n) => `${formatBytes(n)}/s`;
const sum = (o, i) => Object.values(o).reduce((t, v) => t + v[i], 0);

function render(m, rates) {
  const memUsed = m.memory.total - m.memory.available;
  const memPct = (memUsed / m.memory.total) * 100;
  const pkg = (m.temps.find((t) => /package|tctl|tdie/i.test(t.label)) || m.temps[0] || {}).c;
  const up = m.uptime_seconds || 0;
  $("#monitor-summary").textContent = `${m.cpu.model} · ${m.cpu.threads} threads · up ${Math.floor(up / 86400)} days ${Math.floor((up % 86400) / 3600)} hours · load ${m.cpu.load.join(" / ")}`;
  const coreBars = el("div", { class: "cores", "aria-label": "Each bar is one processor thread" },
    rates.cores.map((c, i) => { const b = el("span", { title: `Thread ${i + 1}: ${c.toFixed(0)}%` }); b.style.height = `${Math.max(2, c)}%`; return b; }));
  const cpu = chart("Processor", `${m.cpu.threads} threads`, `${rates.cpu.toFixed(0)}%`, sparkline([history.cpu], 100, "Processor use over the last 3 minutes"));
  cpu.append(coreBars);
  $("#charts").replaceChildren(
    cpu,
    chart("Memory", formatBytes(m.memory.total), `${memPct.toFixed(0)}%`, sparkline([history.mem], 100, "Memory use over the last 3 minutes"),
      [[`${formatBytes(memUsed)} used`], [`${formatBytes(m.memory.cached)} cache`], [`${formatBytes(m.memory.available)} free`],
        ...(m.memory.swap_total ? [[`Swap ${formatBytes(m.memory.swap_total - m.memory.swap_free)} of ${formatBytes(m.memory.swap_total)}`]] : [])]),
    chart("Network", Object.keys(m.net).join(", "), `↓ ${rate(rates.rx)}  ↑ ${rate(rates.tx)}`, sparkline([history.rx, history.tx], 0, "Network traffic over the last 3 minutes"),
      [["Download", 0], ["Upload", 1]]),
    chart("Disk activity", `${Object.keys(m.disks).length} disks`, `Read ${rate(rates.read)}  Write ${rate(rates.write)}`, sparkline([history.read, history.write], 0, "Disk activity over the last 3 minutes"),
      [["Read", 0], ["Write", 1]]),
    chart("Temperature", "Processor", pkg != null ? `${pkg.toFixed(0)} °C` : "Not reported", sparkline([history.temp], 100, "Processor temperature over the last 3 minutes"),
      m.temps.filter((t) => !/^Core /.test(t.label)).slice(0, 8).map((t) => [`${t.chip === t.label ? t.chip : `${t.chip} ${t.label}`}: ${t.c} °C`])));
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
      const pkg = (m.temps.find((t) => /package|tctl|tdie/i.test(t.label)) || m.temps[0] || {}).c;
      push(history.cpu, rates.cpu); push(history.mem, ((m.memory.total - m.memory.available) / m.memory.total) * 100);
      push(history.rx, rates.rx); push(history.tx, rates.tx); push(history.read, rates.read); push(history.write, rates.write);
      if (pkg != null) push(history.temp, pkg);
      render(m, rates);
    }
    previous = m;
  } catch (e) {
    $("#monitor-summary").textContent = e.message;
  }
}

function setRunning(on) {
  clearInterval(timer);
  timer = on ? setInterval(tick, 2000) : null;
  const button = $("#pause");
  button.textContent = on ? "Pause" : "Resume";
  button.setAttribute("aria-pressed", String(!on));
  if (on) tick();
}

startPage().then(() => {
  $("#pause").addEventListener("click", () => setRunning(!timer));
  document.addEventListener("visibilitychange", () => { if (!document.hidden && timer) tick(); });
  setRunning(true);
});
