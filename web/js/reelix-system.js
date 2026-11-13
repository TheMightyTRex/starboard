// Reelix's own backups (System, Backup), log and scheduled tasks (System, Logs): DASH-201, 202, 203. Reelix keeps them
// behind its admin password, so each section asks for it when opened, uses it for that change only, and this page
// remembers it for 5 minutes, as Settings, Reelix does. Loaded after common.js on those two pages.

const rsHeld = { password: "", timer: null };

async function rsAsk(what, error = "") {
  const pw = el("input", { class: "input", type: "password", autocomplete: "current-password", id: "rs-password" });
  const err = el("p", { class: "field__error", role: "alert", text: error });
  setTimeout(() => pw.focus(), 50);
  const ok = await confirmDialog({ title: "Enter your Reelix password", confirm: "Continue",
    message: `To ${what}, Starboard signs in to Reelix for this change only, then signs out. This page remembers the password for 5 minutes.`,
    fields: [el("div", { class: "field" }, el("label", { class: "field__label", for: "rs-password", text: "Reelix password" }),
      el("p", { class: "hint", text: "If Starboard set Reelix up, it is the same as your Starboard password." }), pw, error ? err : null)] });
  return ok && pw.value ? pw.value : null;
}

async function rsCall(action, body, what) {
  let error = "";
  for (let i = 0; i < 3; i++) {
    const password = rsHeld.password || await rsAsk(what, error);
    if (!password) return null;
    try {
      const out = await api(`/api/reelix/admin/system/${action}`, { method: "POST", body: { ...body, password } });
      rsHeld.password = password;
      clearTimeout(rsHeld.timer);
      rsHeld.timer = setTimeout(() => { rsHeld.password = ""; }, 5 * 60 * 1000);
      return out;
    } catch (e) {
      if (e.status === 401) { rsHeld.password = ""; error = e.message; continue; }
      throw e;
    }
  }
  return null;
}

function rsWhen(iso) {
  return iso ? new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "";
}

function rsSection(id, title, about, open, label) {
  const body = el("div", { class: "stack-4" });
  const show = () => body.replaceChildren(el("p", { class: "small muted", text: "Reelix keeps these behind its admin password, so Starboard asks for it first." }),
    el("div", { class: "actions" }, el("button", { type: "button", class: "btn", onclick: () => open(body, show) }, icon("lock"), label)));
  show();
  return el("section", { class: "stack-4 rs-section", "aria-labelledby": `${id}-h` },
    el("div", {}, el("h2", { id: `${id}-h`, text: title }), el("p", { class: "small muted", text: about })), body);
}

function rsFailed(body, retry, e) {
  body.replaceChildren(el("div", { class: "notice", "data-tone": "danger", role: "alert" }, icon("circle-x"),
    el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: "Reelix could not be asked" }), el("p", { text: e.message }))));
  retry();
}

// Backups (DASH-201)
async function rsBackups(body, locked) {
  const draw = (r) => {
    const every = el("input", { class: "input", inputmode: "numeric", value: String(r.every), id: "rs-every" });
    const keep = el("input", { class: "input", inputmode: "numeric", value: String(r.keep), id: "rs-keep" });
    const saveSched = el("button", { type: "button", class: "btn" }, "Save the schedule");
    saveSched.addEventListener("click", async () => { try { const o = await rsCall("backup-settings", { every: every.value, keep: keep.value }, "change Reelix's backups"); if (o) { draw(o); toast(o.done); } } catch (e) { problem(e.message, saveSched); } });
    const now = el("button", { type: "button", class: "btn btn--primary" }, "Make a backup now");
    now.addEventListener("click", async () => { now.disabled = true; try { const o = await rsCall("backup-now", {}, "make a Reelix backup"); if (o) { draw(o); toast(o.done); } } catch (e) { problem(e.message, now); now.disabled = false; } });
    const rows = r.backups.map((b) => {
      const back = el("button", { type: "button", class: "btn btn--quiet btn--compact" }, "Restore", el("span", { class: "visually-hidden", text: ` ${b.name}` }));
      back.addEventListener("click", async () => {
        if (!await confirmDialog({ title: "Restore this Reelix backup?", danger: true, confirm: "Restore",
          message: `Reelix goes back to how it was on ${rsWhen(b.when)} when it starts again. What changed since then is lost.` })) return;
        try { const o = await rsCall("restore", { name: b.name }, "restore a Reelix backup"); if (o) { draw(o); toast(o.done); } } catch (e) { problem(e.message, back); }
      });
      return el("li", { class: "row row--no-lead" }, el("div", {}, el("div", { class: "row__title", text: rsWhen(b.when) }),
        el("div", { class: "row__meta", text: [b.kind === "manual" ? "Made by hand" : "Scheduled", formatBytes(b.size), b.version ? `Reelix ${b.version}` : ""].filter(Boolean).join(" · ") })),
        el("div", { class: "row__side" }, back));
    });
    body.replaceChildren(
      r.restore_waiting ? el("p", { class: "small", text: "A restore is waiting for Reelix to start again." }) : null,
      el("ul", { class: "rows" }, rows.length ? rows : [el("li", { class: "empty", text: "No backups yet." })]),
      el("div", { class: "form-grid" },
        el("div", { class: "field" }, el("label", { class: "field__label", for: "rs-every", text: "Days between backups" }), el("p", { class: "hint", text: "0 deactivates scheduled backups." }), every),
        el("div", { class: "field" }, el("label", { class: "field__label", for: "rs-keep", text: "Backups to keep" }), el("p", { class: "hint", text: "Ones made by hand are always kept." }), keep)),
      el("div", { class: "actions" }, now, saveSched),
      r.folder ? el("p", { class: "small muted", text: `Inside Reelix they are in ${r.folder}, next to its settings. Starboard's Full without media copies Reelix's library and settings itself, so these are extra copies on the same disk.` }) : null);
  };
  try { const r = await rsCall("backups", {}, "show Reelix's backups"); if (r) draw(r); else locked(); } catch (e) { rsFailed(body, locked, e); }
}

// Log (DASH-202)
async function rsLogs(body, locked) {
  const level = el("select", { class: "select", id: "rs-level" }, [["", "Everything"], ["error", "Errors"], ["warn", "Warnings and errors"], ["info", "Information"]].map(([v, t]) => el("option", { value: v, text: t })));
  const out = el("pre", { class: "code-block rs-log" });
  const load = async () => {
    try {
      const r = await rsCall("logs", { level: level.value, lines: 300 }, "read Reelix's log");
      if (!r) { locked(); return; }
      out.textContent = r.lines.map((l) => `${l.when ? new Date(l.when).toLocaleTimeString("en-GB") : ""} ${l.level.toUpperCase().padEnd(5)} ${l.message}`).join("\n") || "Nothing in the log.";
    } catch (e) { rsFailed(body, locked, e); }
  };
  level.addEventListener("change", load);
  body.replaceChildren(el("div", { class: "field" }, el("label", { class: "field__label", for: "rs-level", text: "Show" }), level), out,
    el("div", { class: "actions" }, el("button", { type: "button", class: "btn", onclick: load }, icon("refresh-cw"), "Read again")));
  await load();
}

// Scheduled tasks (DASH-203)
async function rsTasks(body, locked) {
  const draw = (r) => body.replaceChildren(el("ul", { class: "rows" }, r.tasks.map((t) => {
    const run = el("button", { type: "button", class: "btn btn--quiet btn--compact", disabled: t.running }, t.running ? "Running" : "Run now",
      el("span", { class: "visually-hidden", text: ` ${t.name}` }));
    run.addEventListener("click", async () => { run.disabled = true; try { const o = await rsCall("run-task", { task: t.kind }, "run a Reelix task"); if (o) { draw(o); toast(o.done); } } catch (e) { problem(e.message, run); run.disabled = false; } });
    return el("li", { class: "row row--no-lead" }, el("div", {}, el("div", { class: "row__title", text: t.name }),
      el("div", { class: "row__meta", text: [t.last ? `Last ${rsWhen(t.last)}` : "Not run yet", t.next ? `next ${rsWhen(t.next)}` : "", t.on ? "" : "Off"].filter(Boolean).join(" · ") }),
      t.error ? el("div", { class: "row__meta", text: `Last time: ${t.error}` }) : null), el("div", { class: "row__side" }, run));
  })));
  try { const r = await rsCall("tasks", {}, "show Reelix's tasks"); if (r) draw(r); else locked(); } catch (e) { rsFailed(body, locked, e); }
}

startPage().then(() => {
  const page = $("main .page");
  if (!page) return;
  if (location.pathname.endsWith("/system-backup.html")) {
    page.append(rsSection("rs-backups", "Reelix's backups", "Reelix backs up its own library and settings. Make one, change how often, or go back to one.", rsBackups, "Show Reelix's backups"));
  } else {
    page.append(rsSection("rs-log", "Reelix's log", "What Reelix did, newest last, to find out why something did not work.", rsLogs, "Read Reelix's log"),
      rsSection("rs-tasks", "Reelix's scheduled tasks", "What Reelix does on its own, such as refreshing the library, with Run now.", rsTasks, "Show Reelix's tasks"));
  }
});
