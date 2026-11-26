// System, Overview, Busy now (DASH-558): the heaviest containers and processes by processor and memory. One read when the
// page opens and one each time Check now is pressed; nothing runs between. The server reads twice, a second apart.


const pct = (n) => `${n < 0.1 ? "under 0.1" : n < 10 ? n.toFixed(1) : Math.round(n)}%`;

function table(caption, columns, rows) {
  return el("div", { class: "table-wrap", "data-stack": true }, el("table", { class: "table" },
    el("caption", { class: "visually-hidden", text: caption }),
    el("thead", {}, el("tr", {}, columns.map(([text, numeric], i) => el("th", { scope: "col", class: numeric ? "numeric" : null, text })))),
    el("tbody", {}, rows)));
}

function draw(r) {
  const at = new Date(r.at * 1000).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  $("#busy-notes").replaceChildren(...(r.notes || []).map((n) => notice("info", n)));
  const cs = r.containers || [];
  $("#busy-containers").hidden = !cs.length;
  $("#busy-containers-detail").textContent = `The ${cs.length} busiest of ${r.containers_total}, now`;
  $("#busy-containers-list").replaceChildren(table("Containers, busiest first, with their processor and memory and what Starboard thinks each is",
    [["Container"], ["Processor", true], ["Memory", true], ["What Starboard thinks it is"]],
    cs.map((c) => el("tr", {},
      el("th", { scope: "row", "data-label": "Container", text: c.name }),
      el("td", { class: "numeric", "data-label": "Processor", text: pct(c.cpu) }),
      el("td", { class: "numeric", "data-label": "Memory", text: formatBytes(c.memory) }),
      el("td", { "data-label": "What Starboard thinks it is", text: c.note || "Nothing to say" })))));
  const ps = r.processes || [];
  $("#busy-processes").hidden = !ps.length;
  $("#busy-processes-detail").textContent = `The ${ps.length} busiest of ${r.processes_total}, now`;
  $("#busy-processes-list").replaceChildren(ps.length ? table("Processes, busiest first, with their processor and memory, the container they run in and what Starboard thinks each is",
    [["Process"], ["Processor", true], ["Memory", true], ["Container"], ["What Starboard thinks it is"]],
    ps.map((p) => el("tr", {},
      el("th", { scope: "row", "data-label": "Process", text: p.name }),
      el("td", { class: "numeric", "data-label": "Processor", text: pct(p.cpu) }),
      el("td", { class: "numeric", "data-label": "Memory", text: formatBytes(p.memory) }),
      el("td", { "data-label": "Container", text: p.container || "None" }),
      el("td", { "data-label": "What Starboard thinks it is", text: p.note || "Nothing to say" })))) : "");
  const top = cs[0] && (!ps[0] || cs[0].cpu >= ps[0].cpu) ? `${cs[0].name} ${pct(cs[0].cpu)}` : ps[0] ? `${ps[0].name} ${pct(ps[0].cpu)}` : "";
  const summary = `Read at ${at}${top ? ` · busiest: ${top} of the whole processor` : ""} · took ${r.seconds} seconds`;
  $("#busy-summary").textContent = summary;
  return summary;
}

async function read(announceIt) {
  const again = $("#busy-again");
  again.disabled = true;
  again.setAttribute("aria-busy", "true");
  $("#busy-summary").setAttribute("aria-busy", "true");
  if (announceIt) $("#busy-summary").textContent = "Reading what is using the processor…";
  try {
    const summary = draw(await api("/api/busy"));
    if (announceIt) announce(summary);
  } catch (e) {
    $("#busy-summary").textContent = `Could not read what is busy: ${e.message}`;
    if (announceIt) announce("Could not read what is busy");
  } finally {
    again.disabled = false;
    again.removeAttribute("aria-busy");
    $("#busy-summary").removeAttribute("aria-busy");
    if (announceIt) again.focus();  // a disabled button drops focus: it comes back here, beside the result
  }
}

startPage().then(() => {
  $("#busy-again").addEventListener("click", () => read(true));
  read(false);
});
