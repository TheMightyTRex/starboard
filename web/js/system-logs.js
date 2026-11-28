// System, Logs: what Starboard did and every problem it met, newest first. Report a problem gathers the details
// an issue needs (personal details removed) and links to GitHub. Download and Delete all logs sit in the page head.

const LEVEL_WORDS = { error: ["Error", "danger"], warning: ["Warning", "warning"], info: ["Info", "neutral", "info"], detail: ["Detail", "muted"] };
const DETAIL_WORDS = { off: "Off", day: "For 24 hours", on: "Until I turn it off" };
const SHOW_LINES = [50, 100, 200, 500, 1000];  // DASH-534: the most lines shown, the same in Copy and Download
let level = "all";
let query = "";
let entries = [];
let state = null;

const when = (t) => new Date(t * 1000).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", second: "2-digit" });

async function load() {
  const r = await api(`/api/logs?level=${level}&q=${encodeURIComponent(query)}`);
  state = r;
  entries = r.entries;
  render();
  renderHead();
  renderReport();
  renderLimits();
}

// The most lines shown and Alerts only (DASH-534), kept for the account with the other log settings, applied at once
// with the saved note beside the control. They are drawn once, so each keeps focus while the list is drawn again.
const number = (n) => Number(n).toLocaleString("en-GB");
async function saveShown(change, control) {
  try { await api("/api/config/general", { method: "PUT", body: { logs: change } }); }
  catch (e) { problem(e.message, control); await load(); return; }
  await load();
  const note = $("#logs-limit-note");
  note.replaceChildren();
  window.SharedComponents.savedNote(note);
}

function renderLimits() {
  if ($("#logs-limit")) {
    $("#logs-limit").value = String(state.limit);
    $("#logs-alerts-only").checked = !!state.alerts_only;
    return;
  }
  const select = el("select", { class: "select", id: "logs-limit" },
    SHOW_LINES.map((n) => el("option", { value: String(n), text: `${number(n)} lines`, selected: n === state.limit })));
  select.addEventListener("change", () => saveShown({ show_lines: Number(select.value) }, select));
  const only = el("input", { type: "checkbox", role: "switch", id: "logs-alerts-only", "aria-describedby": "logs-alerts-hint", checked: !!state.alerts_only });
  only.addEventListener("change", () => saveShown({ alerts_only: only.checked }, only));
  $("#logs-shown").replaceChildren(
    el("div", { class: "toolbar__row" },
      el("label", { class: "switch", for: "logs-limit" }, el("span", { class: "nowrap", text: "Lines shown" }), select),
      el("label", { class: "switch", for: "logs-alerts-only" }, el("span", { class: "nowrap", text: "Alerts only" }), only),
      el("span", { class: "saved-note", id: "logs-limit-note", hidden: true })),
    el("p", { class: "small muted", id: "logs-alerts-hint", text: "Alerts only shows errors and warnings and leaves out information and detail." }));
}

// "Showing the newest 200 of 3,412 entries": what is shown, out of what the log holds. With a search, a level or Alerts
// only, it counts the entries that match, out of all the log holds.
function showingText() {
  const n = entries.length;
  if (!n) return state.filtered ? `No entries match, out of ${number(state.total)} in the log` : "";
  const word = (k) => (k === 1 ? "entry" : "entries");
  const total = number(state.total);
  if (!state.filtered) return state.all_found ? `Showing all ${number(n)} ${word(n)}` : `Showing the newest ${number(n)} of ${total} entries`;
  return state.all_found ? `Showing all ${number(n)} matching ${word(n)}, of ${total} in the log`
    : `Showing the newest ${number(n)} matching entries, of ${total} in the log`;
}

function renderHead() {
  const s = state.summary;
  const keep = state.settings.keep_days;
  const most = state.settings.max_mb ?? 50;
  $("#logs-summary").replaceChildren(
    s.files ? `${s.days} ${s.days === 1 ? "day" : "days"} of logs (${logBytes(s.bytes)}) · kept for ${keep} days, no more than ${most} MB · `
      : `No logs yet · kept for ${keep} days, no more than ${most} MB · `,
    el("a", { href: "/settings-general-backup.html#logs", text: "Change in Settings, General, Backup/Logs" }));
  const del = el("button", { type: "button", class: "btn btn--danger", id: "logs-delete-all", disabled: !s.files }, icon("trash-2"), "Delete all logs");
  del.addEventListener("click", async () => {
    let r;
    try { r = await deleteAllLogs(s); } catch (e) { problem(e.message, del); return; }
    if (!r) return;
    // Said, as the page shows it (R5): the summary is drawn again, and focus goes back to the button.
    await load();
    $("#logs-delete-all")?.focus();
    announce(deletedLogsText(r));
  });
  $("#logs-actions").replaceChildren(
    el("a", { class: "btn", href: "/api/logs/download", download: "" }, icon("download"), "Download"), del);
  $("#logs-notice").replaceChildren(...(state.detailed
    ? [notice("info", "Detailed logging is active", state.settings.detail === "day"
      ? `Until ${new Date(state.settings.detail_until * 1000).toLocaleString("en-GB", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}. It records every page request and every call to your apps, to help find a problem.`
      : "Until you turn it off. It records every page request and every call to your apps, to help find a problem.")]
    : []));
}


// A saved setting says so beside its control (DASH-309, R5): the select is drawn again, keeps focus, and has the note.
async function setDetail(mode) {
  try { await api("/api/config/general", { method: "PUT", body: { logs: { detail: mode } } }); }
  catch (e) { problem(e.message, $("#detail-choice")); return; }
  await load();
  const select = $("#detail-choice");
  if (!select) return;
  select.focus();
  const note = el("span", { class: "saved-note", hidden: true });
  select.after(note);
  window.SharedComponents.savedNote(note, mode === "off" ? "Off" : mode === "day" ? "Turned on for 24 hours" : "On");
}

function renderReport() {
  const box = $("#report");
  // The same choice as Settings, General, so it reads the same in both places.
  const detailSelect = el("select", { class: "select", id: "detail-choice" },
    Object.entries(DETAIL_WORDS).map(([v, t]) => el("option", { value: v, text: t, selected: v === state.settings.detail })));
  detailSelect.addEventListener("change", () => setDetail(detailSelect.value));
  const copy = el("button", { type: "button", class: "btn" }, icon("copy"), "Copy the details");
  copy.addEventListener("click", async () => {
    try {
      const text = await (await fetch("/api/logs/report", { credentials: "same-origin" })).text();
      if (!await copyText(text)) throw new Error("not copied");
      // Beside the button, not a toast (R5).
      const note = copy.parentElement.querySelector(".saved-note") || el("span", { class: "saved-note", hidden: true });
      copy.parentElement.append(note);
      window.SharedComponents.savedNote(note, "Copied. Paste it into the issue.");
    } catch { problem("Could not copy. Use Download instead"); }
  });
  const preview = el("pre", { class: "code-block", text: "Loading…" });
  const details = el("details", {}, el("summary", { text: "Show what will be copied" }), preview);
  details.addEventListener("toggle", async () => {
    if (details.open) preview.textContent = await (await fetch("/api/logs/report", { credentials: "same-origin" })).text();
  });
  const issue = state.repo
    ? el("a", { class: "btn btn--primary", href: `https://github.com/${state.repo}/issues/new?template=bug_report.md`, target: "_blank", rel: "noopener noreferrer" },
      icon("external-link"), "Open a new issue on GitHub", el("span", { class: "visually-hidden", text: " (opens in a new tab)" }))
    : el("p", { class: "small muted", text: "Set STARBOARD_REPO on the server to link straight to the issue page." });
  box.replaceChildren(
    el("ol", { class: "steps-list" },
      el("li", {}, el("strong", { text: state.detailed ? "Detailed logging is active. " : "Turn on detailed logging. " }),
        "It records every page request and every call to your apps.",
        el("div", { class: "field field--short" }, el("label", { for: "detail-choice", text: "Detailed logging" }), detailSelect)),
      el("li", {}, el("strong", { text: "Do the thing that went wrong again. " })),
      el("li", {}, el("strong", { text: "Copy the details and open an issue. " }), "Paste them in, and say what you expected to happen. ",
        el("div", { class: "actions" }, copy, issue))),
    el("p", { class: "small muted", text: "Starboard removes personal details before it writes anything to its log. These are passwords, API keys and tokens, IP addresses, host and computer names, email addresses, the user name in folder paths and the dashboard's name. Read the text before you post it all the same." }),
    details);
}

function render() {
  const list = $("#entries");
  list.removeAttribute("aria-busy");
  const said = showingText();
  if ($("#entries-count").textContent !== said) $("#entries-count").textContent = said;  // a live region: only a real change is said
  if (!entries.length) {
    list.replaceChildren(el("p", { class: "muted", text: query || level !== "all" || state.alerts_only ? "Nothing matches." : "Nothing logged yet." }));
    return;
  }
  const rows = entries.map((e) => {
    const [word, tone, iconName] = LEVEL_WORDS[e.level] || LEVEL_WORDS.info;
    const message = e.trace || e.log
      ? el("details", {}, el("summary", { text: e.message }), el("pre", { class: "code-block", text: e.trace || e.log }))
      : e.message;
    return el("tr", {},
      el("td", { "data-label": "Time", class: "nowrap tabular", text: when(e.t) }),
      el("td", { "data-label": "Level" }, chip(word, tone, iconName)),
      el("td", { "data-label": "Area", text: e.area }),
      el("td", { "data-label": "What happened" }, message));
  });
  list.replaceChildren(el("div", { class: "table-wrap", "data-stack": true }, el("table", { class: "table" },
    el("caption", { class: "visually-hidden", text: "Log, newest first" }),
    el("thead", {}, el("tr", {}, ["Time", "Level", "Area", "What happened"].map((h) => el("th", { scope: "col", text: h })))),
    el("tbody", {}, rows))));
}

function toolbar() {
  // One of three at a time, so a segmented control (filter chips are for toggles that can be on together).
  const chips = el("fieldset", { class: "segmented" }, el("legend", { class: "visually-hidden", text: "Show" }),
    [["all", "Everything"], ["problems", "Problems"], ["detail", "Detailed"]].map(([value, label]) => {
      const input = el("input", { type: "radio", name: "log-level", value, checked: value === level });
      input.addEventListener("change", () => { level = value; load(); });
      return el("label", {}, input, el("span", { text: label }));
    }));
  const search = el("input", { class: "input", type: "search", placeholder: "Search the log", "aria-label": "Search the log" });
  let timer = null;
  search.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => { query = search.value; load(); }, 300); });
  $("#logs-toolbar").replaceChildren(el("div", { class: "toolbar__row" }, el("div", { class: "toolbar__search" }, search), chips));
}

startPage().then(() => {
  toolbar();
  load().catch((e) => { $("#entries").replaceChildren(el("p", { text: e.message })); });
});
