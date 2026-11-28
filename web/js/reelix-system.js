// Reelix's own backups (Settings, General, Backup/Logs), log and scheduled tasks (System, Logs): DASH-201, 202, 203. Reelix keeps them
// behind its admin password, so each section asks for it when opened, uses it for that change only, and this page
// remembers it for 5 minutes, as Settings, Reelix does. Loaded after common.js on those two pages.

const rsHeld = { password: "", timer: null };

async function rsAsk(what, error = "") {
  const pw = el("input", { class: "input", type: "password", autocomplete: "current-password", id: "rs-password" });
  const err = el("p", { class: "field-error", role: "alert", text: error });
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

// tab: the section is a page topic (a tab of Backup/Logs) in the page's list of sections, not a block under the page.
function rsSection(id, title, about, open, label, tab) {
  const body = el("div", { class: "stack-4" });
  const show = () => body.replaceChildren(el("p", { class: "small muted", text: "Reelix keeps these behind its admin password, so Starboard asks for it first." }),
    el("div", { class: "actions" }, el("button", { type: "button", class: "btn", onclick: () => open(body, show) }, icon("lock"), label)));
  show();
  return el("section", { class: tab ? "settings-section rs-section" : "stack-4 rs-section", "aria-labelledby": `${id}-h` },
    el("div", { class: tab ? "settings-section__head" : null }, el("h2", { id: `${id}-h`, text: title }), el("p", { class: "small muted", text: about })), body);
}

function rsFailed(body, retry, e) {
  body.replaceChildren(el("div", { class: "notice", "data-tone": "danger", role: "alert" }, icon("circle-x"),
    el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: "Reelix could not be asked" }), el("p", { text: e.message }))));
  retry();
}

// Backups (DASH-201)
async function rsBackups(body, locked) {
  const draw = (r, said = null) => {
    // Settings pattern 2 (DASH-385): selects that apply at once, each with the saved note beside it. A choice that
    // is not saved (the password dialog was closed, or Reelix refused) goes back to what it was.
    const pick = (id, value, options) => el("select", { class: "select", id, "aria-labelledby": `${id}-l`, "aria-describedby": `${id}-h` },
      (options.some(([v]) => v === value) ? options : [...options, [value, id === "rs-every" ? `Every ${value} days` : `${value} backups`]].sort((x, y) => x[0] - y[0]))
        .map(([v, text]) => el("option", { value: String(v), text, selected: v === value })));
    const every = pick("rs-every", r.every, [[0, "Off"], [1, "Every day"], [2, "Every 2 days"], [3, "Every 3 days"], [7, "Every week"], [14, "Every 2 weeks"], [30, "Every 30 days"]]);
    const keep = pick("rs-keep", r.keep, [3, 5, 7, 10, 14, 30].map((n) => [n, `${n} backups`]));
    const setting = (select, label, hint, note) => el("li", { class: "setting" },
      el("div", { class: "setting__text" }, el("span", { class: "setting__label", id: `${select.id}-l`, text: label }),
        el("span", { class: "setting__hint", id: `${select.id}-h`, text: hint })),
      el("div", { class: "setting__control" }, select, note));
    const applies = (select, was, send, after) => {
      const note = el("span", { class: "saved-note", hidden: true });
      select.addEventListener("change", async () => {
        try {
          const o = await send();
          if (!o) { select.value = String(was); select.focus(); return; }
          if (after) { after(o); return; }
          r = { ...r, ...o };
          was = select.value;
          select.focus();
          window.SharedComponents.savedNote(note);
        } catch (e) { select.value = String(was); problem(e.message, select); }
      });
      return note;
    };
    const sendSchedule = () => rsCall("backup-settings", { every: every.value, keep: keep.value }, "change Reelix's backups");
    const settings = [
      setting(every, "Make a backup", "Reelix makes these by itself. With Off, you can still make one by hand.", applies(every, r.every, sendSchedule)),
      setting(keep, "Keep the newest", "Reelix removes scheduled backups beyond this number. Ones made by hand are always kept.", applies(keep, r.keep, sendSchedule))];
    // Where they are kept (DASH-386): next to Reelix's settings, or in the media folder when that is another disk.
    const p = r.place;
    const disk = (c) => (c.disk ? `, on ${c.disk}` : "");
    let placeNote = null;
    if (p && (p.chosen === "other" || p.now === "other")) {
      // A folder someone set in Reelix's own configuration file: said, and left alone.
      placeNote = el("p", { class: "small muted", text: `Reelix keeps its backups in ${p.other || "a folder set in its own configuration file"}. You did not choose that here, so Starboard leaves it as it is.` });
    } else if (p && (!p.same_disk || p.chosen === "media")) {
      const [beside, media] = p.choices;
      const where = el("select", { class: "select", id: "rs-place", "aria-labelledby": "rs-place-l", "aria-describedby": "rs-place-h" },
        [["settings", `Next to its settings${disk(beside)}`], ["media", `In the media folder${disk(media)}`]]
          .map(([v, text]) => el("option", { value: v, text, selected: v === p.chosen })));
      const note = applies(where, p.chosen, () => rsCall("backup-place", { place: where.value }, "change where Reelix keeps its backups"),
        (o) => { draw(o); $("#rs-place")?.focus(); const n = $("#rs-place")?.parentElement.querySelector(".saved-note"); if (n) window.SharedComponents.savedNote(n); announce(o.done); });
      settings.push(setting(where, "Where Reelix keeps them",
        `${media.folder} is on another disk than Reelix's settings, so a failed system disk does not take the backups with it. The backups already made move with the choice. Reelix uses the new folder once it has restarted.`, note));
    } else if (p && p.same_disk) {
      placeNote = el("p", { class: "small muted", text: `Reelix can keep its backups next to its settings or in the media folder. Here both are on the same disk (${p.choices[0].disk || p.choices[0].mount}), so moving them would not protect them. Full without media, on this page, can go to any disk and holds Reelix's library and settings too.` });
    }
    const now = el("button", { type: "button", class: "btn btn--primary", id: "rs-backup-now" }, "Make a backup now");
    // The new backup is in the list: said, with focus back on the button (R5).
    now.addEventListener("click", async () => { now.disabled = true; try { const o = await rsCall("backup-now", {}, "make a Reelix backup"); if (o) { draw(o); $("#rs-backup-now")?.focus(); announce(o.done); } } catch (e) { problem(e.message, now); now.disabled = false; } });
    const rows = r.backups.map((b) => {
      // It opens a danger dialog, so it is a danger button (design system: danger is shown before and after).
      const back = el("button", { type: "button", class: "btn btn--danger btn--compact" }, icon("archive-restore"), "Restore", el("span", { class: "visually-hidden", text: ` ${b.name}` }));
      back.addEventListener("click", async () => {
        if (!await confirmDialog({ title: "Restore this Reelix backup?", danger: true, confirm: "Restore",
          message: [el("p", { text: `Reelix goes back to how it was on ${rsWhen(b.when)}. What changed in Reelix since then is lost.` }),
            el("p", { text: "The restore happens when Reelix restarts. Restart Reelix appears beside the backups once you confirm; until then nothing changes." })] })) return;
        // The restore happens later, when Reelix starts again, so it stays a toast (section 10, Toasts).
        try { const o = await rsCall("restore", { name: b.name }, "restore a Reelix backup"); if (o) { draw(o); toast(o.done); } } catch (e) { problem(e.message, back); }
      });
      return el("li", { class: "row row--no-lead" }, el("div", {}, el("div", { class: "row__title", text: rsWhen(b.when) }),
        el("div", { class: "row__meta", text: [b.kind === "manual" ? "Made by hand" : "Scheduled", formatBytes(b.size), b.version ? `Reelix ${b.version}` : ""].filter(Boolean).join(" · ") })),
        el("div", { class: "row__side" }, back));
    });
    // Restart where it is needed (DASH-470): a restore waits for Reelix to start again, so Restart Reelix is here.
    // It restarts Reelix's container (as Manage apps, Restart) and follows Reelix until it answers again.
    const restore = !r.restore_waiting ? null : r.service
      ? restartNotice({ title: "A restore is waiting for Reelix to start again", name: "Reelix",
        text: "Reelix goes back to the backup you chose when it starts again.",
        what: "Reelix stops, then restores the backup as it starts again. Searches, requests and downloads it was handling carry on once it is back.",
        restart: () => api(`/api/services/${encodeURIComponent(r.service)}/restart`, { method: "POST" }),
        back: async () => (await api(`/api/status?id=${encodeURIComponent(r.service)}`)).items?.[0]?.state === "up",
        done: async () => {
          const o = await rsCall("backups", {}, "show Reelix's backups");
          if (!o) return null;
          draw(o, o.restore_waiting ? { tone: "warning", title: "Restore still waiting", text: "Reelix answers again, and still lists the restore as waiting. Check Reelix's log in Logs." }
            : { tone: "success", title: "Done", text: "Reelix restarted and restored the backup." });
          return $("#rs-restored");
        } })
      : el("p", { class: "small", text: "A restore is waiting for Reelix to start again. Add Reelix in Manage apps to restart it from here." });
    const note = said ? el("div", { class: "notice", "data-tone": said.tone, id: "rs-restored", tabindex: "-1" }, icon(said.tone === "success" ? "circle-check" : "triangle-alert"),
      el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: said.title }), el("p", { text: said.text }))) : null;
    // A changed folder waits for Reelix to start again, as a restore does (DASH-386, DASH-470).
    const moving = p && p.restart && !r.restore_waiting && r.service
      ? restartNotice({ title: "The new backup folder waits for Reelix to restart", name: "Reelix",
        text: `Reelix keeps its backups ${p.chosen === "media" ? "in the media folder" : "next to its settings"} once it has restarted. Until then it lists none of the ones that moved.`,
        what: "Reelix stops and starts again. Searches, requests and downloads it was handling carry on once it is back.",
        restart: () => api(`/api/services/${encodeURIComponent(r.service)}/restart`, { method: "POST" }),
        back: async () => (await api(`/api/status?id=${encodeURIComponent(r.service)}`)).items?.[0]?.state === "up",
        done: async () => {
          const o = await rsCall("backups", {}, "show Reelix's backups");
          if (!o) return null;
          draw(o, o.place?.restart ? { tone: "warning", title: "Still the old folder", text: "Reelix answers again, and still uses the folder from before. Check Reelix's log in Logs." }
            : { tone: "success", title: "Done", text: `Reelix restarted and keeps its backups in ${o.folder}.` });
          return $("#rs-restored");
        } })
      : p && p.restart && !r.restore_waiting ? el("p", { class: "small", text: "The new backup folder waits for Reelix to restart. Add Reelix in Manage apps to restart it from here." }) : null;
    const onSameDisk = !p || p.now !== "media";
    body.replaceChildren(...[note, restore, moving,
      el("ul", { class: "rows" }, rows.length ? rows : [el("li", { class: "empty", text: "No backups yet." })]),
      el("div", { class: "actions" }, now),
      el("ul", { class: "settings-rows" }, settings), placeNote,
      r.folder ? el("p", { class: "small muted", text: onSameDisk
        ? `Inside Reelix they are in ${r.folder}, next to its settings. Starboard's Full without media copies Reelix's library and settings itself, so these are extra copies on the same disk.`
        : `Inside Reelix they are in ${r.folder}, in the media folder. Starboard's Full without media copies Reelix's library and settings itself, so these are extra copies.` }) : null].filter(Boolean));  // replaceChildren writes a null as the word "null"
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
    // The row says Running: said, as the page shows it (R5).
    run.addEventListener("click", async () => { run.disabled = true; try { const o = await rsCall("run-task", { task: t.kind }, "run a Reelix task"); if (o) { draw(o); announce(o.done); } } catch (e) { problem(e.message, run); run.disabled = false; } });
    return el("li", { class: "row row--no-lead" }, el("div", {}, el("div", { class: "row__title", text: t.name }),
      el("div", { class: "row__meta", text: [t.last ? `Last ${rsWhen(t.last)}` : "Not run yet", t.next ? `next ${rsWhen(t.next)}` : "", t.on ? "" : "Deactivated"].filter(Boolean).join(" · ") }),
      t.error ? el("div", { class: "row__meta", text: `Last time: ${t.error}` }) : null), el("div", { class: "row__side" }, run));
  })));
  try { const r = await rsCall("tasks", {}, "show Reelix's tasks"); if (r) draw(r); else locked(); } catch (e) { rsFailed(body, locked, e); }
}

startPage().then(() => {
  const page = $("main .page");
  if (!page) return;
  if (location.pathname.endsWith("/settings-general-backup.html")) {
    const mine = rsSection("rs-backups", "Reelix's backups", "Reelix backs up its own library and settings. Make one, change how often, or go back to one.", rsBackups, "Show Reelix's backups", true);
    // The fifth tab, after the Starboard backups and before Logs.
    const tabs = $("#backup-sections");
    if (tabs) tabs.append(mine); else page.append(mine);
  } else {
    page.append(rsSection("rs-log", "Reelix's log", "What Reelix did, newest last, to find out why something did not work.", rsLogs, "Read Reelix's log"),
      rsSection("rs-tasks", "Reelix's scheduled tasks", "What Reelix does on its own, such as refreshing the library, with Run now.", rsTasks, "Show Reelix's tasks"));
  }
});
