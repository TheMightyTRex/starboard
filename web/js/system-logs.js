// System, Logs: what Starboard did and every problem it met, newest first. Report a problem gathers the details
// an issue needs (personal details removed) and links to GitHub. Download and Delete logs sit in the page head.

const LEVEL_WORDS = { error: ["Error", "danger"], warning: ["Warning", "warning"], info: ["Info", "neutral", "info"], detail: ["Detail", "muted"] };
const DETAIL_WORDS = { off: "Off", day: "For 24 hours", on: "Until I deactivate it" };
let level = "all";
let query = "";
let entries = [];
let state = null;

const when = (t) => new Date(t * 1000).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", second: "2-digit" });

async function load(more = false) {
  const before = more && entries.length ? entries[entries.length - 1].t : "";
  const r = await api(`/api/logs?level=${level}&q=${encodeURIComponent(query)}${before ? `&before=${before}` : ""}`);
  state = r;
  entries = more ? entries.concat(r.entries) : r.entries;
  render(r.entries.length === 300);
  renderHead();
  renderReport();
}

function renderHead() {
  const s = state.summary;
  const keep = state.settings.keep_days;
  $("#logs-summary").replaceChildren(
    s.days ? `${s.days} ${s.days === 1 ? "day" : "days"} of logs (${formatBytes(s.bytes)}) · kept for ${keep} days · ` : `No logs yet · kept for ${keep} days · `,
    el("a", { href: "/settings-general-logs.html#logs", text: "Change in Settings, General, Logs and feedback" }));
  const del = el("button", { type: "button", class: "btn btn--danger", disabled: !s.days }, icon("trash-2"), "Delete logs");
  del.addEventListener("click", async () => {
    const ok = await confirmDialog({ title: "Delete all logs?", danger: true, confirm: "Delete logs",
      message: "Starboard removes every day of its log now. This cannot be undone. New entries start again straight away." });
    if (!ok) return;
    const r = await api("/api/logs/clear", { method: "POST" });
    // Said, as the page shows it (R5): the summary says No logs yet, and focus goes to the list's heading.
    await load();
    announce(`Deleted ${r.removed} ${r.removed === 1 ? "day" : "days"} of logs`);
  });
  $("#logs-actions").replaceChildren(
    el("a", { class: "btn", href: "/api/logs/download", download: "" }, icon("download"), "Download"), del);
  $("#logs-notice").replaceChildren(...(state.detailed
    ? [notice("info", "Detailed logging is active", state.settings.detail === "day"
      ? `Until ${new Date(state.settings.detail_until * 1000).toLocaleString("en-GB", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}. It records every page request and every call to your apps, to help find a problem.`
      : "Until you deactivate it. It records every page request and every call to your apps, to help find a problem.")]
    : []));
}

function notice(tone, title, text) {
  return el("div", { class: "notice", "data-tone": tone, role: "status" }, icon(tone === "info" ? "info" : "triangle-alert"),
    el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: title }), el("p", { text })));
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
  window.SharedComponents.savedNote(note, mode === "off" ? "Deactivated" : mode === "day" ? "Activated for 24 hours" : "Activated");
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
      await navigator.clipboard.writeText(text);
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
      el("li", {}, el("strong", { text: state.detailed ? "Detailed logging is active. " : "Activate detailed logging. " }),
        "It records every page request and every call to your apps.",
        el("div", { class: "field field--short" }, el("label", { for: "detail-choice", text: "Detailed logging" }), detailSelect)),
      el("li", {}, el("strong", { text: "Do the thing that went wrong again. " })),
      el("li", {}, el("strong", { text: "Copy the details and open an issue. " }), "Paste them in, and say what you expected to happen. ",
        el("div", { class: "actions" }, copy, issue))),
    el("p", { class: "small muted", text: "Starboard removes personal details before anything is written to its log: passwords, API keys and tokens, IP addresses, host and computer names, email addresses, the user name in folder paths and the dashboard's name. Read the text before you post it all the same." }),
    details);
}

function render(hasMore) {
  const list = $("#entries");
  list.removeAttribute("aria-busy");
  $("#entries-count").textContent = entries.length ? `${entries.length}${hasMore ? "+" : ""} ${entries.length === 1 ? "entry" : "entries"}, newest first` : "";
  if (!entries.length) {
    list.replaceChildren(el("p", { class: "muted", text: query || level !== "all" ? "Nothing matches." : "Nothing logged yet." }));
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
    el("tbody", {}, rows))),
  hasMore ? el("div", { class: "actions" }, el("button", { type: "button", class: "btn", onclick: () => load(true) }, "Show older entries")) : null);
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
