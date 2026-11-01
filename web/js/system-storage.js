// Storage: free space in each folder Starboard has been given (STARBOARD_DISKS).

function meter(pct, label) {
  const bar = el("div", { class: "progress", role: "progressbar", "aria-valuenow": String(pct), "aria-valuemin": "0", "aria-valuemax": "100", "aria-label": label }, el("span"));
  bar.firstChild.style.width = `${pct}%`;
  if (pct >= 90) bar.dataset.tone = "danger"; else if (pct >= 80) bar.dataset.tone = "warning";
  return bar;
}

async function load() {
  try {
    const sys = await api("/api/system");
    const list = $("#storage");
    list.replaceChildren();
    const found = sys.disks.filter((d) => !d.missing);
    if (!sys.disks.length) list.append(el("li", { class: "empty", text: "No folders set yet. List them in STARBOARD_DISKS (see the README)." }));
    let total = 0, free = 0;
    for (const d of sys.disks) {
      if (d.missing) { list.append(el("li", { class: "row" }, el("p", { class: "row__title", text: d.label }), el("div", { class: "row__side" }, chip("Folder not found", "warning")))); continue; }
      total += d.total; free += d.free;
      const pct = Math.round((d.used / d.total) * 100);
      list.append(el("li", { class: "row" },
        el("div", {}, el("p", { class: "row__title", text: d.label }), el("p", { class: "row__meta num", text: `${formatBytes(d.used)} used · ${formatBytes(d.free)} free of ${formatBytes(d.total)}` })),
        el("div", { class: "row__side" }, d.filesystem ? el("span", { class: "tag", title: "Filesystem", text: d.filesystem }) : null, el("span", { class: "num", text: `${pct}%` }), pct >= 90 ? chip("Nearly full", "danger") : pct >= 80 ? chip("Filling up", "warning") : chip("Space free", "success")),
        meter(pct, `${d.label}, ${pct}% used`)));
    }
    const stats = $("#storage-stats");
    stats.replaceChildren();
    if (found.length) {
      const stat = (v, l) => el("div", { class: "stat" }, el("span", { class: "stat__value", text: v }), el("span", { class: "stat__label", text: l }));
      stats.append(stat(formatBytes(free), "Free"), stat(formatBytes(total), "In total"), stat(`${Math.round(((total - free) / total) * 100)}%`, "Used"));
    }
    const rows = found.map((d) => {
      const pct = (d.used / d.total) * 100;
      return { label: d.label, value: pct, tone: pct >= 90 ? "danger" : pct >= 80 ? "warning" : "", note: `${formatBytes(d.free)} free of ${formatBytes(d.total)}` };
    }).sort((a, b) => b.value - a.value);
    $("#storage-charts").replaceChildren(...(rows.length ? [
      barChart({ title: "How full each folder is", detail: "Fullest first", rows, max: 100, format: percent }),
      barChart({ title: "Free space", detail: "Most free first", rows: found.map((d) => ({ label: d.label, value: d.free })).sort((a, b) => b.value - a.value), format: formatBytes }),
    ] : []));
    $("#storage-summary").textContent = `${found.length} ${found.length === 1 ? "folder" : "folders"}`;
  } catch (e) {
    $("#storage-summary").textContent = e.message;
  }
}

startPage().then(() => { $("#refresh").addEventListener("click", load); load(); });
