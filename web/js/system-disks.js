// Disk health: each disk's SMART report, and recent events.

async function load() {
  try {
    const data = await api("/api/disk-health");
    const grid = $("#disks");
    grid.replaceChildren();
    if (!data.configured) {
      grid.append(el("p", { class: "empty", text: "Not set up yet. See Disk health in the README: a job on the server saves each disk's SMART report, and STARBOARD_SMART_DIR tells Starboard where." }));
      $("#disks-summary").textContent = "Not set up.";
      $("#events").replaceChildren();
      return;
    }
    let attention = 0;
    for (const d of data.disks) {
      const failing = d.passed === false;
      const hot = d.temperature && d.temperature_limit && d.temperature >= d.temperature_limit - 5;
      const tone = failing ? "danger" : d.problems.length || hot ? "warning" : "success";
      if (tone !== "success") attention += 1;
      const facts = [
        ["Health check", d.passed === false ? "Failed" : d.passed ? "Passed" : "Not reported"],
        ["Temperature", d.temperature != null ? `${d.temperature} °C${d.temperature_limit ? ` (limit ${d.temperature_limit} °C)` : ""}` : "Not reported"],
        ["Size", d.capacity ? formatBytes(d.capacity) : "Not reported"],
        ["Powered on", d.hours != null ? `${d.hours.toLocaleString("en-GB")} hours (${(d.hours / 8766).toFixed(1)} years)` : "Not reported"],
        ["Last self-test", d.last_test ? `${d.last_test.type}: ${d.last_test.result}` : "None recorded"],
      ];
      grid.append(el("section", { class: "panel disk", "data-tone": tone, "aria-label": d.model },
        el("div", { class: "disk__head" },
          el("div", {}, el("h2", { class: "disk__title", text: d.model }), el("p", { class: "row__meta", text: [d.device, d.serial].filter(Boolean).join(" · ") })),
          chip(failing ? "Failing" : tone === "warning" ? "Check" : "Healthy", tone)),
        el("dl", { class: "facts" }, facts.flatMap(([k, v]) => [el("dt", { text: k }), el("dd", { class: "num", text: v })])),
        d.problems.length ? el("ul", { class: "disk__problems" }, d.problems.map((p) => el("li", { text: `${p.name}: ${p.value.toLocaleString("en-GB")}` }))) : null,
        el("p", { class: "hint", text: `Report from ${formatDate(d.checked * 1000, true)}` })));
    }
    const name = (d) => `${d.model}${d.device ? ` (${d.device.replace("/dev/", "")})` : ""}`;
    const withTemp = data.disks.filter((d) => d.temperature != null);
    const withHours = data.disks.filter((d) => d.hours != null);
    $("#disk-charts").replaceChildren(
      ...(withTemp.length ? [barChart({ title: "Temperature", detail: "Against each disk's own limit", format: degrees,
        rows: withTemp.map((d) => ({ label: name(d), value: d.temperature, limit: d.temperature_limit,
          tone: d.temperature_limit && d.temperature >= d.temperature_limit - 5 ? "warning" : "" })) })] : []),
      ...(withHours.length ? [barChart({ title: "Age", detail: "Years powered on, oldest first", format: (v) => `${v.toFixed(1)} years`,
        rows: withHours.map((d) => ({ label: name(d), value: d.hours / 8766 })).sort((a, b) => b.value - a.value) })] : []));
    $("#disks-summary").textContent = `${data.disks.length} disks · ${attention ? `${attention} to check` : "all healthy"}`;
    $("#events").replaceChildren(...(data.events.length ? data.events : ["Nothing recorded yet."]).map((line) => el("li", { class: "row" }, el("p", { class: "row__meta", text: line }))));
  } catch (e) {
    $("#disks-summary").textContent = e.message;
  }
}

startPage().then(() => { $("#refresh").addEventListener("click", load); load(); });
