// Find all wanted (owner, 26 November 2026): one button on every Library tab and every Wanted page. It counts first, asks
// with a dialog that says how many and what happens, then shows its progress in words and a bar, with Stop, and ends with a
// summary. Starboard runs the search on the server (starboard/find_wanted.py), so it goes on when this page is closed.
// Limits are the server's: 10 at a time, one group a minute, at most 100 in a run, nothing searched in the last day,
// one run at a time, 15 minutes between runs, and a wait while Download hours pause downloads.

const FIND_NOUN = { films: ["film", "films"], tv: ["episode", "episodes"], music: ["album", "albums"], books: ["book", "books"],
  audiobooks: ["audiobook", "audiobooks"], radio: ["episode", "episodes"] };
const FIND_KIND = { films: "movie", tv: "episode", music: "album", books: "ebook", audiobooks: "audiobook" };
const findWanted = ([one, many]) => [`wanted ${one}`, `wanted ${many}`];
const findPlural = (n, [one, many]) => `${n.toLocaleString("en-GB")} ${n === 1 ? one : many}`;

// The button, with the count when Reelix can say it cheaply (one small request; radio says it in the dialog).
function findButton(tab, { onRun } = {}) {
  const button = el("button", { type: "button", class: "btn btn--primary", "data-find-all": tab }, icon("search"), "Find all wanted");
  button.addEventListener("click", () => findAllWanted(tab, button));
  if (FIND_KIND[tab]) {
    api(`/api/wanted?which=missing&kind=${FIND_KIND[tab]}&page=1`).then((r) => {
      button.replaceChildren(icon("search"), `Find all wanted (${r.total.toLocaleString("en-GB")})`);
      if (!r.total) { button.disabled = true; button.title = "Nothing is wanted"; }
    }).catch(() => {});
  }
  onRun?.(button);
  return button;
}

// Radio has no cheap count of wanted episodes, so its button says how many shows have some, from the Wanted filter.
function findRadioCount(shows) {
  const button = document.querySelector('[data-find-all="radio"]');
  if (!button) return;
  button.replaceChildren(icon("search"), `Find all wanted (${findPlural(shows, ["show", "shows"])})`);
  button.disabled = !shows;
  button.title = shows ? "" : "Nothing is wanted";
}

function findPanel(anchor) {
  let panel = document.getElementById("find-panel");
  if (!panel) { panel = el("section", { id: "find-panel", class: "find-panel", "aria-labelledby": "find-panel-h", tabindex: "-1" }); anchor.after(panel); }
  return panel;
}

async function findAllWanted(tab, button) {
  button.disabled = true; button.setAttribute("aria-busy", "true");
  let plan;
  try { plan = await api(`/api/find-wanted?tab=${tab}`); }
  catch (e) { problem(e.message, button); button.disabled = false; button.removeAttribute("aria-busy"); return; }
  button.disabled = false; button.removeAttribute("aria-busy");
  button.focus();  // a disabled button loses focus: the question must give it back to this one
  if (plan.run?.state === "running") { findShow(tab, button, plan.run); return; }
  if (!plan.to_search) {
    announce(plan.wanted ? "Everything wanted was searched for in the last day" : "Nothing is wanted");
    toast(plan.wanted ? `Everything wanted was searched for in the last day (${plan.left_out} left out)` : "Nothing is wanted");
    return;
  }
  const noun = plan.noun;
  const what = tab === "radio" ? `the wanted episodes of ${findPlural(plan.to_search, ["show", "shows"])}` : findPlural(plan.to_search, findWanted(noun));
  const minutes = plan.minutes <= 1 ? "about a minute" : `about ${plan.minutes} minutes`;
  const lines = [
    `${findPlural(plan.wanted, noun)} ${plan.wanted === 1 ? "is" : "are"} wanted.${plan.left_out ? ` Starboard left out ${plan.left_out} that it searched for in the last day.` : ""}`,
    plan.more ? `${plan.more.toLocaleString("en-GB")} more wait for the next search, because one search covers ${plan.max_run} at most.` : "",
    `Starboard asks for ${plan.group} at a time, with one minute between groups. This takes ${minutes}.`,
    "You can stop at any time and leave this page. The search carries on without it.",
  ].filter(Boolean);
  const ok = await confirmDialog({ title: `Find ${what}?`, confirm: tab === "radio" ? `Find ${findPlural(plan.to_search, ["show", "shows"])}` : `Find ${findPlural(plan.to_search, findWanted(noun))}`,
    message: el("div", { class: "stack-2" },
      el("p", { text: tab === "radio" ? "Reelix searches for the wanted episodes of each show, a few shows at a time." : `Reelix searches its sites for each wanted ${noun[0]}, a few at a time, and sends the best match it finds to your download app.` }),
      el("ul", {}, lines.map((t) => el("li", { text: t })))) });
  if (!ok) return;
  try { const r = await api("/api/find-wanted", { method: "POST", body: { tab } }); findShow(tab, button, r.run); }
  catch (e) { problem(e.message, button); }
}

// Progress in words and a bar while it runs, then the summary. The words change after each group, so a screen reader
// hears one calm update a minute, not one for each poll.
function findShow(tab, button, first) {
  const head = document.querySelector(".page-head");
  const panel = findPanel(head);
  let last = -1, timer = null;
  const draw = (run) => {
    const noun = FIND_NOUN[tab];
    const unit = tab === "radio" ? ["show", "shows"] : findWanted(noun);
    if (run.state === "running") {
      const pct = run.total ? Math.round((100 * run.searched) / run.total) : 0;
      const text = run.waiting_for_hours ? "Waiting for download hours to start. The search carries on then."
        : `Searched ${run.searched} of ${findPlural(run.total, unit)}.${run.next_in ? ` The next group starts in ${run.next_in} seconds.` : ""}`;
      if (!panel.querySelector("#find-bar")) {
        panel.replaceChildren(el("h2", { class: "lib-panel-heading", id: "find-panel-h", text: tab === "radio" ? "Finding wanted episodes" : `Finding wanted ${noun[1]}` }),
          el("p", { id: "find-text", role: "status" }),
          el("div", { class: "progress", id: "find-bar", role: "progressbar", "aria-valuemin": "0", "aria-valuemax": "100" }, el("span")),
          el("div", { class: "actions" }, el("button", { type: "button", class: "btn", id: "find-stop", onclick: (e) => {
            e.currentTarget.disabled = true; api("/api/find-wanted", { method: "POST", body: { action: "stop" } }).catch(() => {}); } }, icon("pause"), "Stop"),
          el("span", { class: "small muted", text: "You can leave this page. Starboard carries on." })));
      }
      if (run.searched !== last || run.waiting_for_hours) { $("#find-text").textContent = text; last = run.searched; }
      const bar = $("#find-bar");
      bar.setAttribute("aria-valuenow", String(pct)); bar.setAttribute("aria-label", `Searched ${run.searched} of ${findPlural(run.total, unit)}`);
      bar.firstElementChild.style.width = `${pct}%`;
      return false;
    }
    const failed = run.state === "failed", stopped = run.state === "stopped";
    const title = failed ? "The search stopped" : stopped ? `Stopped after ${run.searched} of ${run.total}` : `Searched ${findPlural(run.total, unit)}`;
    const body = failed ? `${run.said || "Reelix did not answer"}. Nothing else changed. Select Find all wanted to try again.`
      : `Reelix sends what it finds to your download app, and keeps searching while you follow ${tab === "radio" ? "the shows" : "them"}.${run.still_wanted != null ? ` ${run.still_wanted.toLocaleString("en-GB")} ${run.still_wanted === 1 ? "is" : "are"} still wanted.` : ""}${stopped ? ` ${run.total - run.searched} have not been searched.` : ""}`;
    panel.replaceChildren(el("div", { class: "notice", "data-tone": failed ? "danger" : stopped ? "info" : "success", role: failed ? "alert" : "status" },
      icon(failed ? "circle-x" : stopped ? "info" : "circle-check"),
      el("div", { class: "notice__body" }, el("span", { class: "notice__title", id: "find-panel-h", text: title }), el("p", { text: body }),
        el("div", { class: "actions" }, el("a", { class: "btn", href: "/downloads.html", text: "Open Downloads" }),
          el("button", { type: "button", class: "btn btn--quiet", text: "Close", onclick: () => { panel.replaceChildren(); button.focus(); } })))));
    announce(`${title}. ${body}`);
    return true;
  };
  const tick = async () => {
    try { const r = await api("/api/find-wanted"); if (r.run?.state && draw(r.run)) clearInterval(timer); } catch { /* try again at the next tick */ }
  };
  if (!draw(first)) timer = setInterval(tick, 5000);
}

// A run that is going when a page opens shows its panel at once.
function findResume(tab, button) {
  api("/api/find-wanted").then((r) => { if (r.run?.state === "running") findShow(tab, button, r.run); }).catch(() => {});
}
