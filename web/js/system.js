// System: load, memory, uptime, storage and the warnings apps report.

function stat(value, label) {
  return el("div", { class: "stat" }, el("span", { class: "stat__value", text: value }), el("span", { class: "stat__label", text: label }));
}

function uptime(seconds) {
  if (!seconds) return "Unknown";
  const d = Math.floor(seconds / 86400), h = Math.floor((seconds % 86400) / 3600);
  return d ? `${d} days ${h} hours` : `${h} hours`;
}

async function load() {
  try {
    const [sys, health] = await Promise.all([api("/api/system"), api("/api/health")]);
    const memUsed = sys.memory.total - sys.memory.available;
    $("#stats").replaceChildren(
      stat(sys.load.length ? sys.load[0].toFixed(2) : "–", `Load (1 minute) on ${sys.cpus} threads`),
      stat(`${Math.round((memUsed / sys.memory.total) * 100) || 0}%`, `Memory used of ${formatBytes(sys.memory.total)}`),
      stat(uptime(sys.uptime_seconds), "Since the last restart"));
    const disks = $("#disks");
    disks.replaceChildren();
    if (!sys.disks.length) disks.append(el("p", { class: "hint", text: "No folders set. See the README to show free space." }));
    for (const d of sys.disks) {
      if (d.missing) { disks.append(el("p", { class: "notice", "data-tone": "warning", text: `${d.label}: folder not found` })); continue; }
      const pct = Math.round((d.used / d.total) * 100);
      const bar = el("div", { class: "progress", role: "progressbar", "aria-valuenow": String(pct), "aria-valuemin": "0", "aria-valuemax": "100", "aria-label": `${d.label}, ${pct}% used` }, el("span"));
      bar.firstChild.style.width = `${pct}%`;
      disks.append(el("div", { class: "meter-row" },
        el("div", { class: "meter-row__label" }, el("strong", { text: d.label }), el("span", { class: "num", text: `${formatBytes(d.free)} free of ${formatBytes(d.total)}` })), bar));
    }
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
    $("#system-summary").textContent = `${health.items.length} warnings · updated ${new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}`;
  } catch (e) {
    $("#system-summary").textContent = e.message;
  }
}

startPage().then(() => { $("#refresh").addEventListener("click", load); load(); });
