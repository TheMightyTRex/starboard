// Settings, Apps, the media server tab, Administration (DASH-568): the media server's own admin jobs, done from Starboard so a
// person need not open its own dashboard. Each part is read from the server only when a person asks (nothing runs at rest), and
// the last part says, for every job, where it is done: Starboard, the server's own page (with a link), or nobody can through the
// server's interface. Plain lists and buttons from the design system; a change asks first when it is large and is written to the audit log.

const WHO = { starboard: ["In Starboard", "success", "circle-check"], later: ["Not in Starboard yet", "warning", "clock"],
  server: ["In the server's own page", "info", "external-link"], no: ["Not possible", "muted", "minus"] };

async function startMediaAdmin() {
  const root = $("#media-admin-sections");
  if (!root) return;
  let ov;
  try { ov = await api("/api/media-server/admin"); } catch (e) { root.replaceChildren(notice("danger", "Could not load Administration", e.message)); return; }
  root.removeAttribute("aria-busy");
  if (!ov.active) { root.replaceChildren(); return; }
  const said = el("div", { class: "stack-2", role: "status", "aria-live": "polite", id: "ma-said", tabindex: "-1" });
  const say = (tone, title, text) => said.replaceChildren(notice(tone, title, text));
  const part = (id, title, text, ...content) => el("div", { class: "stack-2", "data-part": id },
    el("h3", { id: `${id}-h`, text: title }), text ? el("p", { class: "small muted", text }) : null, ...content);
  const holder = () => el("div", { class: "stack-2", "aria-live": "polite" });
  const readButton = (label, box, draw) => {
    const b = el("button", { type: "button", class: "btn" }, icon("refresh-cw"), label);
    b.addEventListener("click", async () => {
      b.disabled = true;
      box.replaceChildren(el("p", { class: "muted", text: `Asking ${ov.name}…` }));
      try { await draw(box); } catch (err) { box.replaceChildren(notice("warning", `${ov.name} did not answer`, err.message)); }
      finally { b.disabled = false; b.focus(); }
    });
    return b;
  };
  const table = (caption, columns, rows) => el("div", { class: "table-wrap", "data-stack": true }, el("table", { class: "table table--middle" },
    el("caption", { class: "visually-hidden", text: caption }),
    el("thead", {}, el("tr", {}, columns.map((text) => el("th", { scope: "col", text })))), el("tbody", {}, rows)));
  const ask = async (path, body) => {
    try { const r = await api(path, { method: "POST", body }); announce(r.said); say("success", "Asked", r.said); return true; }
    catch (err) { say("danger", "That did not work", err.message); return false; }
  };
  const parts = [];

  if (ov.parts.includes("libraries")) {
    const box = holder();
    const draw = async (into) => {
      const { rows } = await api("/api/media-server/admin/libraries");
      const all = el("button", { type: "button", class: "btn" }, icon("scan-search"), "Scan every library");
      all.addEventListener("click", async () => { all.disabled = true; await ask("/api/media-server/admin/scan", { id: "", how: "new" }); all.disabled = false; all.focus(); });
      into.replaceChildren(rows.length ? el("ul", { class: "rows" }, rows.map((r) => {
        const scan = el("button", { type: "button", class: "btn" }, icon("scan-search"), "Scan", el("span", { class: "visually-hidden", text: ` ${r.name} for new and changed files` }));
        scan.addEventListener("click", async () => { scan.disabled = true; await ask("/api/media-server/admin/scan", { id: r.id, how: "new" }); scan.disabled = false; scan.focus(); });
        const full = el("button", { type: "button", class: "btn" }, icon("refresh-cw"), "Refresh everything", el("span", { class: "visually-hidden", text: ` in ${r.name}` }));
        full.addEventListener("click", async () => {
          if (!(await confirmDialog({ title: `Refresh everything in ${r.name}?`, confirm: "Refresh everything",
            message: `${ov.name} reads every file and every picture and detail again. This can take a long time and uses the server's processor.` }))) { full.focus(); return; }
          full.disabled = true; await ask("/api/media-server/admin/scan", { id: r.id, how: "all" }); full.disabled = false; full.focus();
        });
        return el("li", { class: "row" }, el("div", { class: "row__main" }, el("strong", { class: "row__title", text: r.name }),
          el("span", { class: "small muted", text: [r.type, r.count != null ? `${r.count.toLocaleString("en-GB")} items` : "", r.folders.join(", ")].filter(Boolean).join(" · ") })),
        el("div", { class: "row__side" }, el("div", { class: "actions" }, scan, full)));
      })) : emptyState("No libraries yet", `${ov.name} has no libraries. Add one in its own page: the list at the end says where.`), el("div", { class: "actions" }, all));
    };
    parts.push(part("ma-libraries", "Libraries", "Each library with its folders. Scan checks for new and changed files. Refresh everything reads every file again.",
      el("div", { class: "actions" }, readButton("Read the libraries", box, draw)), box));
  }
  if (ov.parts.includes("tasks")) {
    const box = holder();
    const draw = async (into) => {
      const { rows } = await api("/api/media-server/admin/tasks");
      into.replaceChildren(el("ul", { class: "rows" }, rows.map((t) => {
        const run = el("button", { type: "button", class: "btn", disabled: t.state === "running" }, icon("play"), "Run now", el("span", { class: "visually-hidden", text: ` ${t.name}` }));
        run.addEventListener("click", async () => { run.disabled = true; await ask("/api/media-server/admin/run", { id: t.id }); run.disabled = false; run.focus(); });
        return el("li", { class: "row" }, el("div", { class: "row__main" }, el("strong", { class: "row__title", text: t.name }),
          el("div", {}, chip(t.state === "running" ? "Running now" : "Not running", t.state === "running" ? "info" : "muted", t.state === "running" ? "loader" : "circle")),
          el("span", { class: "small muted", text: [t.group, `Runs ${t.when}`, t.last ? `Last: ${t.last}` : ""].filter(Boolean).join(" · ") })),
        el("div", { class: "row__side" }, run));
      })));
    };
    parts.push(part("ma-tasks", "Scheduled tasks", "What the server does by itself, and when. Run now starts one at once. Starboard shows when each runs; to change the times, use the server's own page.",
      el("div", { class: "actions" }, readButton("Read the scheduled tasks", box, draw)), box));
  }
  if (ov.parts.includes("activity")) {
    const box = holder();
    const draw = async (into) => {
      const { rows } = await api("/api/media-server/admin/activity");
      into.replaceChildren(rows.length ? table(`Recent activity in ${ov.name}`, ["When", "What", "Who"],
        rows.map((r) => el("tr", {}, el("td", { text: r.when }), el("td", { text: r.what }), el("td", { text: r.who })))) : emptyState("Nothing yet", `${ov.name} has no activity to show.`));
    };
    parts.push(part("ma-activity", "Activity", "The most recent things the server records: sign-ins, plays and changes.",
      el("div", { class: "actions" }, readButton("Read the activity", box, draw)), box));
  }
  if (ov.parts.includes("logs")) {
    const box = holder();
    const draw = async (into) => {
      const { rows } = await api("/api/media-server/admin/logs");
      const view = el("div", { class: "stack-2", "aria-live": "polite" });
      into.replaceChildren(rows.length ? el("ul", { class: "rows" }, rows.map((r) => {
        const open = el("button", { type: "button", class: "btn" }, icon("file-text"), "Show the end", el("span", { class: "visually-hidden", text: ` of ${r.name}` }));
        open.addEventListener("click", async () => {
          open.disabled = true;
          try {
            const { text } = await api(`/api/media-server/admin/log?name=${encodeURIComponent(r.name)}`);
            view.replaceChildren(el("h4", { text: r.name }), el("pre", { class: "code-block", tabindex: "0", "aria-label": `The last lines of ${r.name}`, text }));
          } catch (err) { view.replaceChildren(notice("warning", "The log did not open", err.message)); }
          finally { open.disabled = false; open.focus(); }
        });
        return el("li", { class: "row" }, el("div", { class: "row__main" }, el("strong", { class: "row__title", text: r.name }),
          el("span", { class: "small muted", text: [r.when, formatBytes(r.size)].filter(Boolean).join(" · ") })), el("div", { class: "row__side" }, open));
      })) : emptyState("No log files", `${ov.name} lists no log files.`), view);
    };
    parts.push(part("ma-logs", "Logs", "The server's own log files. Starboard shows the last 300 lines of one.",
      el("div", { class: "actions" }, readButton("Read the log files", box, draw)), box));
  }

  // Where each job is done: nothing is hidden, and a job Starboard cannot do says why.
  const base = typeof jellyfinBase === "function" ? jellyfinBase(ov.address) : "";
  const where = (c) => {
    if (!c.page) return null;
    const href = c.page.startsWith("/") ? (base ? base + c.page : "") : c.page;
    return href ? newTabLink(href, `Open ${ov.name}'s page`, { about: ov.name }) : null;
  };
  parts.push(part("ma-coverage", "Where each job is done", `Every administration job ${ov.name} has, and where to do it. Starboard does what ${ov.name}'s own interface allows; the rest is marked, with the reason.`,
    table(`Where each ${ov.name} administration job is done`, ["Job", "Where", "What to do"], ov.coverage.map((c) => {
      const [words, tone, ic] = WHO[c.who] || WHO.no;
      return el("tr", {}, el("th", { scope: "row", text: c.job }), el("td", {}, chip(words, tone, ic)), el("td", {}, el("span", { text: c.says }), where(c) ? el("div", {}, where(c)) : null));
    }))));

  root.replaceChildren(section("ms-admin", "Administration", `Run ${ov.name} from Starboard. Each part reads ${ov.name} only when you ask.`, said, ...parts));
}
