// Disk health: summary tiles, one compact row per disk (failing, then to check, then healthy), each opening
// a wide SMART report slide-out; temperature and age as meters under the list; then recent events.

let repo = "";
let data = null;

const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
const timeNow = () => new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
const short = (d) => (d.device || "").replace("/dev/", "");
const nameOf = (d) => `${d.model}${short(d) ? ` (${short(d)})` : ""}`;
const keyOf = (d) => d.serial || d.device || d.model;
const years = (hours) => hours / 8766;
const HOT = 45; // hard disks are best kept under this

function isHot(d) {
  if (d.temperature == null) return false;
  return d.temperature_limit ? d.temperature >= d.temperature_limit - 5 : d.temperature >= 55;
}

// [tone, word, rank, reason]
function status(d) {
  if (d.passed === false) return ["danger", "Failing", 0, "Failed its own health check"];
  if (d.problems.length) return ["warning", "Needs attention", 1, d.problems.map((p) => `${p.value.toLocaleString("en-GB")} ${p.name.toLowerCase()}`).join(", ")];
  if (isHot(d)) return ["warning", "Hot", 1, `${d.temperature}°C${d.temperature_limit ? `, limit ${d.temperature_limit}°C` : ""}`];
  if (d.passed == null) return ["muted", "Not reported", 2, "No health verdict in the report"];
  return ["success", "Healthy", 3, ""];
}

function age(hours) {
  const y = Math.floor(hours / 8766), days = Math.floor((hours % 8766) / 24);
  const parts = [];
  if (y) parts.push(plural(y, "year", "years"));
  parts.push(plural(days, "day", "days"));
  return `${parts.join(", ")} (${hours.toLocaleString("en-GB")} hours)`;
}

function eventsFor(d) {
  const marks = [short(d), d.serial].filter(Boolean);
  return marks.length ? data.events.filter((line) => marks.some((m) => line.includes(m))) : [];
}

// SMART report slide-out --------------------------------------------------------------------------

function reportBody(d) {
  const [tone, word, , reason] = status(d);
  const facts = [
    ["Model", d.model],
    ["Serial number", d.serial || "Not reported"],
    ["Device", d.device ? el("code", { text: d.device }) : "Not reported"],
    ["Size", d.capacity ? formatBytes(d.capacity) : "Not reported"],
    ["Health check", d.passed === false ? "Failed" : d.passed ? "Passed" : "Not reported"],
    ["Temperature", d.temperature != null ? `${d.temperature}°C${d.temperature_limit ? ` (limit ${d.temperature_limit}°C)` : ""}` : "Not reported"],
    ["Powered on", d.hours != null ? age(d.hours) : "Not reported"],
    ["Last self-test", d.last_test ? `${d.last_test.type || "Test"}: ${d.last_test.result || "no result"}${d.last_test.hours != null ? `, at ${d.last_test.hours.toLocaleString("en-GB")} hours` : ""}` : "None recorded"],
    ["Report from", formatDate(d.checked * 1000, true)],
  ];
  const advice = tone === "danger" ? "Back up what is on it now and replace it."
    : d.problems.length ? "Back up what is on it and plan to replace it. Check again after the next report to see if the counts are rising."
    : isHot(d) ? "Check the airflow around the disk. Hot disks wear out sooner." : "";
  const events = eventsFor(d);
  return [
    tone === "danger" || tone === "warning"
      ? el("div", { class: "notice", "data-tone": tone, role: "status" }, icon("triangle-alert"),
        el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: `${word}: ${reason}` }), advice ? el("p", { text: advice }) : null))
      : chip(word, tone),
    el("dl", { class: "facts" }, facts.flatMap(([k, v]) => [el("dt", { text: k }), el("dd", { class: "numeric" }, v)])),
    el("section", { class: "sys-block", "aria-labelledby": "smart-counters" },
      el("h3", { id: "smart-counters", text: "Counters that should stay at zero" }),
      d.problems.length
        ? el("div", { class: "stats" }, d.problems.map((p) => el("div", { class: "stat", "data-tone": "warning" },
          el("span", { class: "stat__value", text: p.value.toLocaleString("en-GB") }), el("span", { class: "stat__label", text: p.name }))))
        : el("p", { text: "All at zero: reallocated, pending and unreadable sectors, uncorrectable errors, command timeouts, cable errors and spin-up retries." })),
    el("section", { class: "sys-block", "aria-labelledby": "smart-events" },
      el("h3", { id: "smart-events", text: "Events for this disk" }),
      events.length ? el("ul", { class: "rows" }, events.map((line) => el("li", { class: "row row--no-lead" }, el("p", { text: line }))))
        : el("p", { class: "muted", text: "Nothing recorded for this disk." })),
    el("p", { class: "small muted", text: "Starboard shows the counters that matter and the latest self-test. The full attribute table and the self-test history are in the report file on the server." }),
  ];
}

function openReport(d, opener) {
  const again = el("button", { type: "button", class: "btn" }, icon("refresh-cw"), el("span", { text: "Check again" }));
  const panel = sidePanel({ title: `${nameOf(d)}, SMART report`, opener, wide: true, body: reportBody(d), foot: [again] });
  again.addEventListener("click", async () => {
    await load();
    const now = data?.disks.find((x) => keyOf(x) === keyOf(d));
    if (now) panel.body.replaceChildren(...reportBody(now));
    announce(`Checked ${nameOf(d)} again.`);
  });
}

// Page --------------------------------------------------------------------------------------------

function stat(value, label, tone) {
  return el("div", { class: "stat", "data-tone": tone ? tone[0] : null },
    el("span", { class: "stat__value", text: value }), el("span", { class: "stat__label", text: label }), tone ? chip(tone[1], tone[0]) : null);
}

function diskRow(d) {
  const [tone, word, , reason] = status(d);
  const cell = (label, ...content) => el("td", { "data-label": label }, ...content);
  return el("tr", {},
    cell("Disk", el("strong", { text: d.model }), short(d) ? el("span", { class: "small muted", text: ` ${short(d)}` }) : null),
    cell("Status", chip(word, tone), reason ? el("span", { class: "small", text: reason }) : null),
    cell("Size", d.capacity ? formatBytes(d.capacity) : "Not reported"),
    Object.assign(cell("Temperature", d.temperature != null ? `${d.temperature}°C` : "Not reported"), { className: "numeric" }),
    Object.assign(cell("Powered on", d.hours != null ? `${years(d.hours).toFixed(1)} years` : "Not reported"), { className: "numeric" }),
    cell("Last self-test", d.last_test ? d.last_test.result || d.last_test.type : "None recorded"),
    el("td", {}, el("button", { type: "button", class: "btn", "aria-haspopup": "dialog", onclick: (e) => openReport(d, e.currentTarget) },
      el("span", { text: "SMART report" }), el("span", { class: "visually-hidden", text: ` for ${nameOf(d)}` }))));
}

function meterPanel(id, title, hint, rows) {
  return el("section", { class: "panel", "aria-labelledby": id },
    el("div", { class: "sys-panel-head" }, el("h2", { id, text: title }), el("span", { class: "small muted", text: hint })),
    el("ul", { class: "meter-list" }, rows.map((r) => {
      const fill = el("span");
      fill.style.width = `${Math.min(100, Math.max(1, r.pct))}%`;
      return el("li", { class: "meter" },
        el("div", { class: "meter__label" }, el("span", { text: r.label }), el("span", { class: "numeric", text: r.value })),
        el("div", { class: "progress", "data-tone": r.tone || null, "aria-hidden": "true" }, fill));
    })));
}

function emptyState(title, text) {
  $("#disks").replaceChildren(el("div", { class: "empty" }, icon("heart-pulse", 32), el("h2", { text: title }), el("p", { text }),
    repo ? el("a", { class: "btn", href: `https://github.com/${repo}#disk-health`, target: "_blank", rel: "noopener noreferrer" },
      el("span", { text: "Open the set-up guide" }), el("span", { class: "visually-hidden", text: " (opens in a new tab)" })) : null));
  $("#disk-stats").replaceChildren();
  $("#disk-meters").replaceChildren();
  $("#events-panel").hidden = true;
}

async function load() {
  try {
    data = await api("/api/disk-health");
    if (!data.configured) {
      emptyState("Disk health is not set up", "A job on the server saves each disk's SMART report, and STARBOARD_SMART_DIR tells Starboard where to find them.");
      $("#disks-summary").textContent = "Not set up";
      return;
    }
    if (!data.disks.length) {
      emptyState("No SMART reports yet", "The folder in STARBOARD_SMART_DIR has no reports in it yet. They appear after the job on the server next runs.");
      $("#disks-summary").textContent = "No reports yet";
      return;
    }
    const disks = [...data.disks].sort((a, b) => status(a)[2] - status(b)[2] || (b.temperature ?? 0) - (a.temperature ?? 0));
    const failing = disks.filter((d) => status(d)[0] === "danger").length;
    const toCheck = disks.filter((d) => ["danger", "warning"].includes(status(d)[0])).length;
    const withTemp = disks.filter((d) => d.temperature != null).sort((a, b) => b.temperature - a.temperature);
    const withHours = disks.filter((d) => d.hours != null).sort((a, b) => b.hours - a.hours);
    $("#disk-stats").replaceChildren(
      stat(String(disks.length), disks.length === 1 ? "Disk" : "Disks"),
      stat(String(toCheck), "To check", failing ? ["danger", "Failing"] : toCheck ? ["warning", "Needs attention"] : null),
      stat(withTemp.length ? `${withTemp[0].temperature}°C` : "Not reported", withTemp.length ? `Hottest, ${nameOf(withTemp[0])}` : "Hottest", isHot(withTemp[0] || {}) ? ["warning", "Hot"] : null),
      stat(withHours.length ? `${years(withHours[0].hours).toFixed(1)} years` : "Not reported", withHours.length ? `Oldest, ${nameOf(withHours[0])}` : "Oldest",
        withHours.length && years(withHours[0].hours) >= 5 ? ["warning", "Plan to replace"] : null));

    let tbody = $("#disks tbody");
    if (!tbody) {
      tbody = el("tbody");
      $("#disks").replaceChildren(el("div", { class: "table-wrap sys-disks", "data-stack": true },
        el("table", { class: "table" }, el("caption", { class: "visually-hidden", text: "Disks, most urgent first" }),
          el("thead", {}, el("tr", {}, ["Disk", "Status", "Size", "Temperature", "Powered on", "Last self-test"].map((h) =>
            el("th", { scope: "col", class: ["Temperature", "Powered on"].includes(h) ? "numeric" : null, text: h })),
          el("th", { scope: "col" }, el("span", { class: "visually-hidden", text: "Details" })))), tbody)));
    }
    renderKeyed(tbody, disks, keyOf, (d) => diskRow(d));

    $("#disk-meters").replaceChildren(
      ...(withTemp.length ? [meterPanel("temp-title", "Temperature", `Under ${HOT}°C is fine`, withTemp.map((d) => {
        const warm = d.temperature >= HOT || isHot(d);
        return { label: nameOf(d), value: `${d.temperature}°C${warm ? ", hot" : ""}`, pct: (d.temperature / 60) * 100, tone: warm ? "warning" : null };
      }))] : []),
      ...(withHours.length ? [meterPanel("age-title", "Powered on", "Plan to replace after about 5 years", withHours.map((d) => {
        const y = years(d.hours);
        return { label: nameOf(d), value: `${y.toFixed(1)} years${y >= 5 ? ", plan to replace" : ""}`, pct: (y / 6) * 100, tone: y >= 5 ? "warning" : null };
      }))] : []));

    $("#events-panel").hidden = false;
    $("#events").replaceChildren(...(data.events.length
      ? data.events.map((line) => el("li", { class: "row row--no-lead" }, el("p", { text: line })))
      : [el("li", { class: "row row--no-lead" }, el("p", { class: "muted", text: "Nothing recorded yet." }))]));

    const newest = Math.max(...disks.map((d) => d.checked));
    $("#disks-summary").textContent = `${plural(disks.length, "disk", "disks")} · ${toCheck ? `${toCheck} to check` : "all healthy"} · last SMART report ${formatDate(newest * 1000, true)}`;
  } catch (e) {
    $("#disks-summary").textContent = `Could not load disk health: ${e.message}`;
  }
}

startPage().then((session) => {
  repo = session?.repo || "";
  const refresh = $("#refresh");
  refresh.replaceChildren(icon("refresh-cw"), el("span", { text: "Check again" }));
  refresh.addEventListener("click", async () => { await load(); announce(`Checked again at ${timeNow()}.`); });
  load();
});
