// App logs on System, Logs (DASH-223): each app's latest lines, in place of Dozzle. Only for people signed in to
// Starboard; keys, passwords, addresses and names are hidden by the server before they reach the page.
// Since 20 November 2026 the lines are in the design system's log viewer: search with the matches marked, the levels
// with their counts, wrap and download, drawing only the newest 1,000 that match.

// Docker puts its own time first ("2026-11-20T12:01:03.123456789Z ..."); apps write their level in many ways
// ("[ERR]", "ERROR", "level=warning", "WRN"), so the level word is looked for near the start of the line.
const APP_LOG_LEVEL = /(?:^|[\s[|(=:])(fatal|crit(?:ical)?|err(?:or)?|ftl|warn(?:ing)?|wrn|dbg|debug|trace|vrb|verbose)(?=$|[\s\]|):])/i;
function appLogLine(line) {
  const m = /^(\d{4}-\d\d-\d\dT(\d\d:\d\d:\d\d)\S*)\s(.*)$/.exec(line);
  const text = m ? m[3] : line;
  const word = (APP_LOG_LEVEL.exec(text.slice(0, 120)) || [])[1]?.toLowerCase() || "";
  const level = /^(fatal|crit|err|ftl)/.test(word) ? "error" : /^(warn|wrn)/.test(word) ? "warning"
    : /^(dbg|debug|trace|vrb|verbose)/.test(word) ? "debug" : "info";
  return { time: m ? m[2] : "", level, text };
}

document.addEventListener("DOMContentLoaded", async () => {
  const box = $("#applogs");
  if (!box) return;
  let r;
  try { r = await api("/api/app-logs"); } catch { return; }
  if (!r.available || !r.apps.length) return;
  box.hidden = false;
  const pick = el("select", { class: "select", id: "applogs-app" }, r.apps.map((a) => el("option", { value: a.name, text: a.state === "running" ? a.name : `${a.name} (${a.state})` })));
  const lines = el("select", { class: "select", id: "applogs-lines" }, [["100", "Last 100 lines"], ["300", "Last 300 lines"], ["1000", "Last 1,000 lines"]]
    .map(([v, t]) => el("option", { value: v, text: t, selected: v === "300" })));
  const show = el("button", { type: "button", class: "btn btn--primary", text: "Show" });
  const said = el("p", { class: "small muted", "aria-live": "polite" });
  const copy = el("button", { type: "button", class: "btn" }, icon("copy"), "Copy");
  const label = (text, input) => el("div", { class: "field" }, el("label", { for: input.id, text }), input);
  const level = (value, text) => el("button", { type: "button", class: "filter-chip", "aria-pressed": "true", "data-log-level": value },
    text, " ", el("span", { class: "numeric", "data-count": "" }, "0"));
  const scroller = el("div", { class: "log-view__scroll", role: "region", tabindex: "0", "aria-label": "App log lines" }, el("ol", { class: "log-view__lines" }));
  const viewer = el("div", { class: "log-view", "data-log-view": "", "data-file": "app.log" },
    el("div", { class: "log-view__bar" },
      el("div", { class: "field log-view__search" }, el("label", { class: "field__label", for: "applogs-find", text: "Only lines with" }),
        el("input", { class: "input", id: "applogs-find", type: "search", autocomplete: "off", "data-log-search": "" })),
      el("div", { class: "filter-chips", role: "group", "aria-label": "Levels to show" },
        level("error", "Errors"), level("warning", "Warnings"), level("info", "Info"), level("debug", "Debug"))),
    el("div", { class: "log-view__bar" },
      el("button", { type: "button", class: "filter-chip", "aria-pressed": "false", "data-log-wrap": "" }, "Wrap lines"),
      el("button", { type: "button", class: "btn", "data-log-download": "" }, icon("download"), "Download the lines (TXT)"), copy),
    el("p", { class: "log-view__count", "data-log-count": "" }),
    scroller);
  let view = null;
  let got = { lines: [] };
  const load = async () => {
    show.disabled = true;
    try {
      got = await api(`/api/app-logs/${encodeURIComponent(pick.value)}?${new URLSearchParams({ tail: lines.value })}`);
      viewer.dataset.file = `${got.name}.log`;
      view.clear();
      view.add(got.lines.map(appLogLine));
      scroller.scrollTop = scroller.scrollHeight; // newest last, so the newest is in view
      said.textContent = got.lines.length
        ? `${got.lines.length} ${got.lines.length === 1 ? "line" : "lines"} from ${got.name}, newest last.`
        : `Nothing to show from ${got.name}.`;
    } catch (e) { said.textContent = e.message; }
    finally { show.disabled = false; }
  };
  show.addEventListener("click", load);
  copy.addEventListener("click", async () => { if (await copyText(got.lines.join("\n"))) toast("Log lines copied"); else problem("Could not copy the log lines. Select them by hand"); });
  $("#applogs-body").replaceChildren(
    el("div", { class: "form-stack" }, label("App", pick), label("How many", lines)),
    el("div", { class: "actions" }, show), said, viewer);
  view = SharedComponents.logView(viewer);
});
