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
  return marks.length ? data.events.filter((e) => marks.some((m) => e.text.includes(m))) : [];
}

// One event: its time, then the words, with a status icon (the word is in hidden text and the tooltip).
const EVENT_WORDS = { danger: ["Problem", "circle-x"], warning: ["Worth a look", "triangle-alert"], info: ["Information", "info"] };
function eventRow(e) {
  const [word, iconName] = EVENT_WORDS[e.tone] || EVENT_WORDS.info;
  return el("li", { class: "row row--no-lead" },
    el("p", {}, el("span", { class: "status-icon", "data-tone": e.tone === "info" ? null : e.tone, title: word }, icon(iconName), el("span", { class: "visually-hidden", text: `${word}: ` })),
      e.when ? el("span", { class: "small muted numeric", text: `${e.when} ` }) : null, e.text));
}

// SMART report slide-out --------------------------------------------------------------------------

function reportBody(d) {
  const [tone, word, , reason] = status(d);
  const facts = [
    ["Model", d.model],
    ["Serial number", d.serial || "Not reported"],
    ["Device", d.device ? el("code", { text: d.device }) : "Not reported"],
    ["Size", d.capacity ? formatBytes(d.capacity) : "Not reported"],
    ["Speed", d.rpm === 0 ? "Solid state" : d.rpm ? `${d.rpm.toLocaleString("en-GB")} rpm` : "Not reported"],
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
      : headChip(word, tone),
    el("dl", { class: "facts" }, facts.flatMap(([k, v]) => [el("dt", { text: k }), el("dd", { class: "numeric" }, v)])),
    el("section", { class: "sys-block", "aria-labelledby": "smart-counters" },
      el("h3", { id: "smart-counters", text: "Counters that should stay at zero" }),
      d.problems.length
        ? el("div", { class: "stats" }, d.problems.map((p) => el("div", { class: "stat", "data-tone": "warning" },
          el("span", { class: "stat__value", text: p.value.toLocaleString("en-GB") }), el("span", { class: "stat__label", text: p.name }))))
        : el("p", { text: "All at zero: reallocated, pending and unreadable sectors, uncorrectable errors, command timeouts, cable errors and spin-up retries." })),
    ...tempCharts(d),
    el("section", { class: "sys-block", "aria-labelledby": "smart-events" },
      el("h3", { id: "smart-events", text: "Events for this disk" }),
      events.length ? el("ul", { class: "rows" }, events.map(eventRow))
        : el("p", { class: "muted", text: "Nothing recorded for this disk." })),
    (d.tests || []).length > 1 ? el("section", { class: "sys-block", "aria-labelledby": "smart-tests" },
      el("h3", { id: "smart-tests", text: "Self-tests, newest first" }),
      el("div", { class: "table-wrap", "data-stack": true }, el("table", { class: "table" },
        el("caption", { class: "visually-hidden", text: "Self-tests, newest first" }),
        el("thead", {}, el("tr", {}, ["Test", "Result", "At hour"].map((t) => el("th", { scope: "col", text: t })))),
        el("tbody", {}, d.tests.map((t) => el("tr", {}, el("td", { "data-label": "Test", text: t.type || "Test" }), el("td", { "data-label": "Result", text: t.result || "No result" }),
          el("td", { "data-label": "At hour", class: "numeric", text: t.hours != null ? t.hours.toLocaleString("en-GB") : "" }))))))) : null,
    (d.attributes || []).length ? el("details", { class: "disclosure" }, el("summary", { text: `Every attribute (${d.attributes.length})` }),
      el("div", { class: "disclosure__body" }, el("div", { class: "table-wrap", "data-stack": true }, el("table", { class: "table" },
        el("caption", { class: "visually-hidden", text: "Every SMART attribute" }),
        el("thead", {}, el("tr", {}, ["ID", "Attribute", "Value", "Worst", "Threshold", "Raw"].map((t) => el("th", { scope: "col", text: t })))),
        el("tbody", {}, d.attributes.map((a) => el("tr", {},
          el("td", { "data-label": "ID", class: "numeric", text: a.id ?? "" }), el("th", { scope: "row", "data-label": "Attribute", text: a.name }),
          el("td", { "data-label": "Value", class: "numeric", text: a.value ?? "" }), el("td", { "data-label": "Worst", class: "numeric", text: a.worst ?? "" }),
          el("td", { "data-label": "Threshold", class: "numeric", text: a.threshold ?? "" }), el("td", { "data-label": "Raw", class: "numeric", text: a.raw })))))))) : null,
    d.report ? el("a", { class: "btn", href: `/api/disk-health/report?file=${encodeURIComponent(d.report)}`, download: "" }, icon("download"), "Download the full report") : null,
  ].filter(Boolean);
}

// Temperature over 30 days (Starboard keeps one reading an hour) and the drive's own recent log (SCT).
function tempCharts(d) {
  const out = [];
  const rows = (data.history || {})[d.serial || d.device] || [];
  if (rows.length > 1) {
    const chart = lineChart({ level: 3, title: "Temperature, last 30 days", series: [{ key: "temp", name: "Temperature" }], format: (v) => `${Math.round(v)}°C`,
      xFormat: (t) => new Date(t * 1000).toLocaleDateString("en-GB", { day: "numeric", month: "short" }), points: [] });
    chart.update({ points: rows.map(([t, temp]) => ({ t, temp })), span: "the last 30 days", note: "One reading an hour, recorded while Disk health is open or Starboard watches in the background." });
    out.push(chart);
  }
  if (d.sct?.temps?.length > 1) {
    const now = Date.now() / 1000;
    const step = d.sct.minutes * 60;
    const points = d.sct.temps.map((temp, i) => ({ t: now - (d.sct.temps.length - 1 - i) * step, temp }));
    const chart = lineChart({ level: 3, title: "Temperature, the drive's own log", series: [{ key: "temp", name: "Temperature" }], format: (v) => `${Math.round(v)}°C`, points: [] });
    chart.update({ points, span: `the last ${Math.round((points.length * step) / 3600)} hours`, note: `The drive records one reading every ${d.sct.minutes} ${d.sct.minutes === 1 ? "minute" : "minutes"}.` });
    out.push(chart);
  }
  return out;
}

async function readNow() {
  const b = $("#read-now");
  b.disabled = true;
  try {
    await api("/api/disk-health/read", { method: "POST" });
    $("span", b).textContent = "Reading the disks…";
    announce("Asked the server to read the disks. New reports arrive in about a minute.");
    setTimeout(async () => { await load(); }, 60000);
  } catch (e) { problem(`Not asked: ${e.message}`); b.disabled = false; }
}

function openReport(d, opener) {
  const again = el("button", { type: "button", class: "btn" }, icon("refresh-cw"), el("span", { text: "Check again" }));
  const panel = sidePanel({ title: `${nameOf(d)}, SMART report`, opener, body: reportBody(d), foot: [again] });
  again.addEventListener("click", async () => {
    await load();
    const now = data?.disks.find((x) => keyOf(x) === keyOf(d));
    if (now) panel.setBody(reportBody(now));
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
    el("div", { class: "panel__head" }, el("h2", { id, text: title }), el("span", { class: "small muted", text: hint })),
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
    const read = $("#read-now");
    read.hidden = !data.can_read;
    read.disabled = !!data.reading;
    $("span", read).textContent = data.reading ? "Reading the disks…" : "Read disks now";
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
      ? data.events.map(eventRow)
      : [el("li", { class: "row row--no-lead" }, el("p", { class: "muted", text: "Nothing recorded yet." }))]));

    const newest = Math.max(...disks.map((d) => d.checked));
    $("#disks-summary").textContent = `${plural(disks.length, "disk", "disks")} · ${toCheck ? `${toCheck} to check` : "all healthy"} · last SMART report ${formatDate(newest * 1000, true)}`;
  } catch (e) {
    $("#disks-summary").textContent = `Could not load disk health: ${e.message}`;
  }
}

startPage().then((session) => {
  $("#read-now").addEventListener("click", readNow);
  repo = session?.repo || "";
  const refresh = $("#refresh");
  refresh.replaceChildren(icon("refresh-cw"), el("span", { text: "Check again" }));
  refresh.addEventListener("click", async () => { await load(); announce(`Checked again at ${timeNow()}.`); });
  load();
});
