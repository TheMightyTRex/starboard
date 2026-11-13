// Backup and restore: the whole server (the server's own backup job), then Starboard's settings (download,
// restore from a file or from a copy Starboard saved). The password is asked once, in the dialog that confirms.

let serverTimer = null;
let server = null;

// Small helpers ------------------------------------------------------------

function notice(tone, title, text, action) {
  const icons = { success: "circle-check", warning: "triangle-alert", danger: "circle-alert", info: "info" };
  return el("div", { class: "notice", "data-tone": tone === "info" ? null : tone, role: "status" },
    icon(icons[tone] || "info"), el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: title }), text ? el("p", {}, text) : null), action || null);
}

function facts(pairs) {
  return el("dl", { class: "facts" }, pairs.filter(([, v]) => v !== null && v !== undefined && v !== "").flatMap(([k, v]) => [el("dt", { text: k }), el("dd", {}, v)]));
}

function when(seconds) { return formatDate(seconds * 1000, true); }

function took(start, end) {
  if (!start || !end || end < start) return "";
  const minutes = Math.round((end - start) / 60);
  return minutes < 1 ? "under a minute" : `${minutes} ${minutes === 1 ? "minute" : "minutes"}`;
}

// Asks for the password in the dialog that confirms the action. A wrong password opens the dialog again with
// the error under the field. Resolves with what run() returned, or null when cancelled.
async function withPassword({ title, message, confirm, danger = false, run }) {
  let error = "";
  for (;;) {
    const input = el("input", { class: "input", id: "confirm-password", type: "password", autocomplete: "current-password", required: true });
    const errorNode = el("span", { class: "field-error", id: "confirm-password-error" }, icon("circle-alert"), el("span", { text: error }));
    errorNode.hidden = !error;
    if (error) { input.setAttribute("aria-invalid", "true"); input.setAttribute("aria-describedby", errorNode.id); }
    const asked = confirmDialog({ title, message, confirm, danger, fields: [el("div", { class: "field" }, el("label", { for: input.id, text: "Your password" }), input, errorNode)] });
    input.focus();
    if (!(await asked)) return null;
    try {
      return await run(input.value);
    } catch (e) {
      if (e.status === 401) { error = "That password is not right. Check Caps Lock and try again."; continue; }
      if (e.status === 429) { error = e.message; continue; }
      showSettingsMessage("danger", "That did not work", e.message);
      return null;
    }
  }
}

function showSettingsMessage(tone, title, text) {
  $("#settings-message").replaceChildren(tone ? notice(tone, title, text) : "");
}

// The whole server --------------------------------------------------------------

const STATUS_WORDS = { running: ["Backing up now", "info"], waiting: ["Starting", "info"], done: ["Complete", "success"], failed: ["Failed", "danger"] };

function runTime(s) { return s.finished ? when(s.finished) : s.started ? when(s.started) : "Waiting to start"; }

function openRun(opener) {
  const s = server?.status;
  if (!s) return;
  const [label, tone] = STATUS_WORDS[s.status] || [s.status, "info"];
  const message = {
    done: ["success", "The backup finished", s.summary || ""],
    failed: ["danger", "The backup failed", s.summary || `The job stopped with exit code ${s.exit ?? "unknown"}. The server's backup log says why.`],
    running: ["info", "Backing up now", "This page checks again every 5 seconds."],
    waiting: ["info", "Starting", "The server picks up the request within a minute."],
  }[s.status] || ["info", label, s.summary || ""];
  sidePanel({
    title: `Server backup, ${runTime(s)}`, opener,
    body: [
      notice(...message),
      facts([
        ["Status", chip(label, tone)],
        ["Started", s.started ? when(s.started) : "Not yet"],
        ["Finished", s.finished ? when(s.finished) : (s.status === "done" || s.status === "failed" ? "Not recorded" : "Not yet")],
        ["Took", took(s.started, s.finished)],
        ["Rebuild prompt", s.with_prompt ? "Included, and saved next to the backup" : "Not included"],
        ["Result", s.status === "done" || s.status === "failed" ? (s.summary || "No summary") : ""],
      ]),
      s.unreadable?.length ? notice("warning", `${s.unreadable.length} ${s.unreadable.length === 1 ? "thing" : "things"} could not be read`, s.unreadable.join(", ")) : null,
      s.included?.length ? el("details", { class: "disclosure" }, el("summary", { text: `What went in (${s.included.length})` }),
        el("div", { class: "disclosure__body" }, el("ul", {}, s.included.map((x) => el("li", {}, el("code", { text: x })))))) : null,
      s.runs?.length ? el("section", { class: "stack-2", "aria-labelledby": "earlier-runs" }, el("h3", { id: "earlier-runs", text: "Earlier runs" }),
        el("ul", { class: "rows" }, s.runs.map((r) => el("li", { class: "row row--no-lead" },
          el("div", { class: "row__text" }, el("div", { class: "row__title", text: runTime(r) }), el("div", { class: "row__meta", text: r.summary || "" })),
          el("div", { class: "row__side" }, chip(...(STATUS_WORDS[r.status] || [r.status || "Unknown", "muted"]))))))) : null,
      s.runs?.length ? null : el("p", { class: "small muted", text: "The server's job reports its last run only. The files it made are listed under it on the page." }),
    ].filter(Boolean),
  });
}

async function downloadServerFile(f) {
  const r = await withPassword({
    title: `Download ${f.name}?`,
    message: `${formatBytes(f.size)}. A server backup can hold API keys and private files. Keep it somewhere private.`,
    confirm: "Download",
    run: (password) => api("/api/backup/server/link", { method: "POST", body: { password, name: f.name } }),
  });
  if (!r) return;
  const link = el("a", { href: r.url, download: f.name });
  document.body.append(link);
  link.click();
  link.remove();
}

function openFile(f, opener) {
  const prompt = /\.md$/i.test(f.name);
  const save = el("button", { type: "button", class: "btn" }, icon("download"), "Download");
  save.addEventListener("click", () => downloadServerFile(f));
  sidePanel({
    foot: [save],
    title: prompt ? "Rebuild prompt" : `Server backup, ${when(f.modified)}`, opener,
    body: [
      facts([
        ["File", el("code", { text: f.name })],
        ["Saved", when(f.modified)],
        ["Size", el("span", { class: "numeric", text: formatBytes(f.size) })],
        ["Kind", prompt ? "Steps an AI assistant with a shell can follow to rebuild the server" : "Backup archive"],
      ]),
      notice("info", prompt ? "Use it on the server" : "Restore it on the server",
        prompt
          ? "Open it from the backup folder on the server, or from your copy of the backup, and give it to the assistant."
          : "Starboard cannot restore the whole server itself. Follow REBUILD-PROMPT.md, or the help article Back up the whole server."),
    ],
  });
}

function serverRow(title, meta, side, onOpen, key, iconName = "archive") {
  return el("li", { class: "row row--opens", "data-key": key },
    el("span", { class: "app-icon", "aria-hidden": "true" }, icon(iconName, 20)),
    el("div", { class: "row__text" },
      el("div", { class: "row__title" }, el("button", { type: "button", onclick: (e) => onOpen(e.currentTarget) }, title)),
      el("div", { class: "row__meta", text: meta })),
    el("div", { class: "row__side" }, side));
}

async function loadServer() {
  try { server = await api("/api/backup/server"); } catch (e) { $("#server-body").replaceChildren(notice("danger", "Could not read the server backups", e.message)); return; }
  const box = $("#server-body");
  box.removeAttribute("aria-busy");
  const s = server.status;
  const busy = s && (s.status === "running" || s.status === "waiting");
  if (!server.configured) {
    // Full without media covers a server Starboard set up; this part is only for a job of the server's own.
    box.closest("section").hidden = true;
    return;
  }
  const focusKey = box.contains(document.activeElement) ? document.activeElement.closest("[data-key]")?.dataset.key : null;
  const prompt = el("input", { type: "checkbox", role: "switch", id: "with-prompt", checked: localPrompt() });
  prompt.addEventListener("change", () => { try { localStorage.setItem("starboard.backup.prompt", prompt.checked ? "1" : "0"); } catch { /* fine */ } });
  const run = el("button", { type: "button", class: "btn", id: "server-run", disabled: busy }, icon("play"), busy ? "Backing up now" : "Back up the server now");
  run.addEventListener("click", async () => {
    try {
      await api("/api/backup/server", { method: "POST", body: { with_prompt: prompt.checked } });
      announce("Server backup started");
      await loadServer();
      $("#server-run")?.focus();
    } catch (e) { problem(e.message); }
  });
  const rows = [];
  if (s && s.status) {
    const [label, tone] = STATUS_WORDS[s.status] || [s.status, "info"];
    rows.push(serverRow(`Last backup, ${runTime(s)}`, [took(s.started, s.finished), s.with_prompt ? "with rebuild prompt" : null, s.status === "done" ? s.summary : null].filter(Boolean).join(" · ") || label,
      chip(label, tone), openRun, "run"));
  }
  for (const f of server.files) {
    rows.push(serverRow(when(f.modified), `${f.name} · ${formatBytes(f.size)}`, null, (opener) => openFile(f, opener), `file:${f.name}`, /\.md$/i.test(f.name) ? "file-text" : "archive"));
  }
  const archives = server.files.filter((f) => !/\.md$/i.test(f.name)).length;
  box.replaceChildren(
    el("div", { class: "backup-run" },
      el("label", { class: "switch" }, el("span", { class: "check__text" }, el("strong", { text: "Include a rebuild prompt" }),
        el("span", { class: "check__hint", text: "Adds REBUILD-PROMPT.md: steps an AI assistant with a shell can follow to rebuild the server from this backup." })), prompt),
      server.can_run ? run : el("p", { class: "small muted", text: "Starboard can list the backups here but cannot start one. Run the backup job on the server." })),
    rows.length ? el("ul", { class: "rows", "aria-label": "Server backups, newest first" }, rows) : el("p", { class: "muted", text: "No backup has run yet." }),
    archives ? notice("warning", "Keep a copy somewhere else", `${archives === 1 ? "The backup is" : `All ${archives} backups are`} on the server. If its disk fails, ${archives === 1 ? "it goes" : "they go"} with it. Copy the newest one to another disk or computer.`) : "");
  if (focusKey) [...box.querySelectorAll("[data-key]")].find((n) => n.dataset.key === focusKey)?.querySelector("button")?.focus();

  // While a backup runs, look again every 5 seconds.
  clearTimeout(serverTimer);
  if (busy) serverTimer = setTimeout(loadServer, 5000);
}

function localPrompt() {
  try { return localStorage.getItem("starboard.backup.prompt") !== "0"; } catch { return true; }
}

// Starboard's settings ------------------------------------------------------------

function saveFile(data) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const link = el("a", { href: URL.createObjectURL(blob), download: `starboard-settings-${new Date().toISOString().slice(0, 10)}.json` });
  document.body.append(link);
  link.click();
  setTimeout(() => { URL.revokeObjectURL(link.href); link.remove(); }, 1000);
}

async function download() {
  showSettingsMessage(null);
  const data = await withPassword({
    title: "Download a backup of Starboard's settings",
    message: "The file holds your apps' API keys. Keep it somewhere private.",
    confirm: "Download",
    run: (password) => api("/api/backup/settings", { method: "POST", body: { password } }),
  });
  if (!data) return;
  saveFile(data);
  toast(`Backup downloaded: ${data.services.length} apps`);
}

const KEPT = "Starboard saves a copy of the current ones first, so you can go back. Your password and sign-ins stay as they are.";

async function restoreFromFile(file) {
  showSettingsMessage(null);
  if (file.size > 2 * 1024 * 1024) { showSettingsMessage("danger", "That file is not a Starboard backup", "It is too large. Choose the file you downloaded here."); return; }
  let backup;
  try { backup = JSON.parse(await file.text()); } catch { backup = null; }
  if (!backup || backup.format !== "starboard-settings") { showSettingsMessage("danger", "That file is not a Starboard backup", "Choose a file you downloaded with Download a backup."); return; }
  const apps = Array.isArray(backup.services) ? backup.services.length : 0;
  const made = backup.created ? formatDate(backup.created, true) : null;
  const result = await withPassword({
    title: "Restore Starboard's settings?",
    message: [el("p", { text: `Your apps, categories and settings are replaced with the ones in ${file.name}${made ? `, made ${made}` : ""}, which has ${apps} ${apps === 1 ? "app" : "apps"}.` }), el("p", { text: KEPT })],
    confirm: "Restore settings", danger: true,
    run: (password) => api("/api/backup/restore", { method: "POST", body: { password, backup } }),
  });
  if (!result) return;
  showSettingsMessage("success", "Settings restored", `${result.apps} ${result.apps === 1 ? "app" : "apps"} from ${file.name}. The settings from before are in the saved copies.`);
  loadSaved();
}

async function restoreSaved(item, panel) {
  showSettingsMessage(null);
  const result = await withPassword({
    title: "Restore Starboard's settings?",
    message: [el("p", { text: `Your apps, categories and settings are replaced with the ones in the copy from ${when(item.saved)}.` }), el("p", { text: KEPT })],
    confirm: "Restore settings", danger: true,
    run: (password) => api("/api/backup/restore-saved", { method: "POST", body: { password, name: item.name } }),
  });
  if (!result) return;
  panel?.close(false);
  showSettingsMessage("success", "Settings restored", `${result.apps} ${result.apps === 1 ? "app" : "apps"} from the copy of ${when(item.saved)}. The settings from before are saved as a new copy.`);
  await loadSaved();
  $("#saved .row__title button")?.focus();
}

function openSaved(item, opener) {
  const restore = el("button", { type: "button", class: "btn btn--danger" }, icon("archive-restore"), "Restore this copy");
  const save = el("button", { type: "button", class: "btn" }, icon("download"), "Download");
  const holds = el("div", { "aria-live": "polite" }, el("p", { class: "small muted", text: "Reading what it holds…" }));
  const panel = sidePanel({
    title: `Saved copy, ${when(item.saved)}`, opener,
    body: [
      facts([["Made", when(item.saved)], ["Why", item.reason], ["Size", el("span", { class: "numeric", text: formatBytes(item.size) })], ["File", el("code", { text: item.name })]]),
      holds,
      el("p", { class: "small muted", text: "Restoring it replaces your apps, categories and settings. Your password and sign-ins stay as they are." }),
    ],
    foot: [save, restore],
  });
  restore.addEventListener("click", () => restoreSaved(item, panel));
  save.addEventListener("click", async () => {
    const data = await withPassword({
      title: "Download this saved copy",
      message: "The file holds your apps' API keys. Keep it somewhere private.",
      confirm: "Download",
      run: (password) => api("/api/backup/saved/download", { method: "POST", body: { password, name: item.name } }),
    });
    if (data) { saveFile(data); toast(`Saved copy downloaded: ${data.services.length} apps`); }
  });
  api(`/api/backup/saved?name=${encodeURIComponent(item.name)}`).then((d) => holds.replaceChildren(...[
    facts([["Apps", el("span", { class: "numeric", text: String(d.apps) })], ["Categories", d.categories.join(", ") || "None"]]),
    d.app_names.length ? el("p", { class: "small", text: d.app_names.join(", ") }) : null,
  ].filter(Boolean))).catch((e) => holds.replaceChildren(el("p", { class: "small muted", text: `Could not read it: ${e.message}` })));
}

async function loadSaved() {
  let items = [];
  try { ({ items } = await api("/api/backup/saved")); } catch (e) { $("#saved").replaceChildren(el("li", {}, notice("danger", "Could not list the saved copies", e.message))); return; }
  $("#saved").replaceChildren(...(items.length ? items.map((item) => el("li", { class: "row row--opens", "data-key": item.name },
    el("span", { class: "app-icon", "aria-hidden": "true" }, icon("history", 20)),
    el("div", { class: "row__text" },
      el("div", { class: "row__title" }, el("button", { type: "button", onclick: (e) => openSaved(item, e.currentTarget) }, when(item.saved))),
      el("div", { class: "row__meta", text: [item.reason, item.version ? `Starboard ${item.version}` : null, formatBytes(item.size)].filter(Boolean).join(" · ") })),
    el("div", { class: "row__side" },
      el("button", { type: "button", class: "btn btn--quiet btn--compact", onclick: (e) => openSaved(item, e.currentTarget) }, "Open",
        el("span", { class: "visually-hidden", text: ` the copy from ${when(item.saved)}` })))))
    : [el("li", {}, emptyState("No saved copies yet", "Starboard makes one before every restore and before an update changes the settings. To bring back a copy from elsewhere, use Restore from a file."))]));
}


// Full without media (DASH-260) ----------------------------------------------------------------------------------

function sizeWords(n) { return n == null ? "not measured" : formatBytes(n); }

async function loadFull() {
  const body = $("#full-body");
  let f;
  try { f = await api("/api/backup/full"); } catch (e) { body.replaceChildren(notice("danger", "Could not read the full backups", e.message)); return; }
  body.removeAttribute("aria-busy");
  if (!f.installed || !f.docker || f.cannot) {
    body.replaceChildren(notice("info", f.cannot ? "This Starboard cannot make full backups yet" : "Full backups are for servers Starboard set up",
      f.cannot || (!f.docker ? "Starboard needs Docker access to copy the apps' settings." : "Install apps writes the apps' folders that a full backup copies; Settings only still works.")));
    return;
  }
  const folder = locationPicker({ id: "full-folder", label: "Where the copies go", app: "host", setting: "backups", value: f.status.target || f.folder,
    hint: `On another disk than the system disk, so a copy outlives it. Starboard keeps the newest ${f.keep || 5} here.` });
  const disk = el("div", { id: "full-disk", "aria-live": "polite" });
  const pictures = el("input", { type: "checkbox", role: "switch", id: "full-pictures", "aria-labelledby": "full-pictures-l", "aria-describedby": "full-pictures-h", checked: !!f.status.pictures });
  const hint = el("span", { class: "setting__hint", id: "full-pictures-h", text: "Station logos you uploaded and Audiobookshelf's covers. Artwork the apps fetched comes back by itself and is never in it." });
  const measure = el("button", { type: "button", class: "btn btn--quiet btn--compact" }, "Work out the size");
  const sizes = el("p", { class: "small", "aria-live": "polite" });
  measure.addEventListener("click", async () => {
    measure.disabled = true;
    sizes.textContent = "Measuring the apps' settings folder…";
    try {
      const s = await api("/api/backup/full/sizes");
      const without = (s.apps?.without_pictures || 0) + s.starboard.starboard - s.starboard.starboard_pictures;
      const withPics = (s.apps?.with_pictures || 0) + s.starboard.starboard;
      sizes.textContent = `About ${formatBytes(without)} before it is compressed, ${formatBytes(withPics)} with your pictures. Databases shrink to about a third.`;
    } catch (e) { sizes.textContent = e.message; }
    finally { measure.disabled = false; }
  });
  const make = el("button", { type: "button", class: "btn btn--primary" }, icon("archive"), "Make a full backup");
  make.addEventListener("click", () => openMakeFull(folder.input.value.trim(), pictures.checked, make));
  const state = el("div", { "aria-live": "polite" });
  const list = el("ul", { class: "rows", "aria-label": "Full backups in the folder, newest first" });
  body.replaceChildren(
    folder.node, disk,
    el("ul", { class: "settings-rows" }, el("li", { class: "setting" },
      el("div", { class: "setting__text" }, el("span", { class: "setting__label", id: "full-pictures-l", text: "Pictures you added" }), hint),
      el("div", { class: "setting__control" }, el("label", { class: "switch" }, pictures)))),
    el("div", { class: "actions" }, measure), sizes,
    el("div", { class: "actions" }, make), state,
    el("h3", { text: "Full backups in the folder" }), list,
    el("p", { class: "small muted", text: "To restore one, install Starboard on the new server and choose Restore a backup in the set-up. Each app stops for a moment while its own folder is copied." }));
  const showState = (s) => {
    if (s.state === "running") state.replaceChildren(notice("info", "Making a full backup", `${s.step || "Starting"}. You can leave this page.`));
    else if (s.state === "failed") state.replaceChildren(notice("danger", "The full backup did not finish", s.error));
    else if (s.state === "done") state.replaceChildren(notice("success", `Made ${formatDate(s.finished * 1000, true)}`, `${formatBytes(s.size)} in ${s.file}.`));
    else state.replaceChildren();
    make.disabled = s.state === "running";
  };
  // Which disk the folder is on (DASH-260): said plainly, and a warning when it is the system disk.
  const showDisk = (d) => {
    if (!d) { disk.replaceChildren(); return; }
    if (!d.system) { disk.replaceChildren(el("p", { class: "small", text: `On ${d.name} (${d.mount}), not the system disk.` })); return; }
    disk.replaceChildren(d.others
      ? notice("warning", "This folder is on the system disk", `If that disk fails, the backups go with it. Choose a folder on ${d.others === 1 ? "the other disk" : `one of the other ${d.others} disks`}, such as one under /mnt.`)
      : notice("warning", "This computer has only the system disk", "If it fails, the backups go with it. Copy each new backup to a USB disk or another computer."));
  };
  const showList = async () => {
    try {
      const r = await api(`/api/backup/full/found?folder=${encodeURIComponent(folder.input.value.trim())}`);
      showDisk(r.disk);
      list.replaceChildren(...(r.found.length ? r.found.map((b) => el("li", { class: "row row--no-lead" },
        el("div", {}, el("div", { class: "row__title", text: formatDate(b.created, true) }),
          el("div", { class: "row__meta", text: [formatBytes(b.size), `${b.apps.length} apps`, b.version ? `Starboard ${b.version}` : ""].filter(Boolean).join(" · ") })),
        el("div", { class: "row__side" }, chip(b.pictures ? "With your pictures" : "Without pictures", "muted")))) :
        [el("li", {}, emptyState("No full backups here yet", "Make one, and it appears here."))]));
    } catch (e) { list.replaceChildren(el("li", {}, notice("danger", "Could not look in the folder", e.message))); }
  };
  showState(f.status);
  showList();
  folder.input.addEventListener("change", showList);
  let was = f.status.state;
  const poll = setInterval(async () => {
    if (!document.body.contains(state)) { clearInterval(poll); return; }
    if (!make.disabled) return;
    try {
      const s = (await api("/api/backup/full")).status;
      showState(s);
      if (was === "running" && s.state !== "running") showList();
      was = s.state;
    } catch { /* try again next time */ }
  }, 3000);
  document.addEventListener("full-backup-started", () => { make.disabled = true; was = "running"; showState({ state: "running" }); });
}

function openMakeFull(folder, pictures, opener) {
  const pw1 = el("input", { class: "input", id: "full-pw-1", type: "password", autocomplete: "new-password", minlength: "10" });
  const pw2 = el("input", { class: "input", id: "full-pw-2", type: "password", autocomplete: "new-password" });
  const mine = el("input", { class: "input", id: "full-mine", type: "password", autocomplete: "current-password" });
  const field = (label, input, hint) => el("div", { class: "field" }, el("label", { for: input.id, text: label }),
    hint ? el("span", { class: "hint", id: `${input.id}-hint`, text: hint }) : null, input, el("span", { class: "field-error", id: `${input.id}-error`, hidden: true }));
  if (pw1) pw1.setAttribute("aria-describedby", "full-pw-1-hint");
  const go = el("button", { type: "submit", class: "btn btn--primary", form: "full-form", text: "Make it" });
  const cancel = el("button", { type: "button", class: "btn", text: "Cancel" });
  const form = el("form", { class: "form-stack", id: "full-form", novalidate: true },
    el("p", { text: `Into ${folder}, ${pictures ? "with" : "without"} the pictures you added.` }),
    field("A password for the backup", pw1, "At least 10 characters. Write it down: without it, nobody can open the backup, Starboard included."),
    field("The same password again", pw2), field("Your Starboard password", mine));
  const panel = sidePanel({ title: "Make a full backup", opener, body: [form], foot: [go, cancel] });
  cancel.addEventListener("click", () => panel.close());
  const say = (input, text) => { const e = $(`#${input.id}-error`); e.textContent = text; e.hidden = !text; input.setAttribute("aria-invalid", text ? "true" : "false"); if (text) input.focus(); };
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    [pw1, pw2, mine].forEach((i) => say(i, ""));
    if (pw1.value.length < 10) { say(pw1, "Use at least 10 characters"); return; }
    if (pw1.value !== pw2.value) { say(pw2, "The two passwords are not the same"); return; }
    go.disabled = true;
    try {
      await api("/api/backup/full", { method: "POST", body: { password: mine.value, backup_password: pw1.value, folder, pictures } });
      panel.close();
      document.dispatchEvent(new Event("full-backup-started"));
    } catch (err) { say(/password/i.test(err.message) && /not right|attempts/i.test(err.message) ? mine : pw1, err.message); }
    finally { go.disabled = false; }
  });
  pw1.focus();
}

// Copies off this computer (DASH-380) -----------------------------------------------------------------------------
// One form with one Save (a share's password and rclone's config are secrets): where the copies go, the details for
// that place and how many to keep there, with Starboard's password. Test and Copy the newest now answer in the live
// status line under the form; focus stays on the button that was used.

const COPY_KINDS = [
  ["off", "Off", "Full backups stay only in their own folder."],
  ["disk", "Another disk", "A USB disk or a second disk in this computer."],
  ["smb", "A Windows or NAS share", "SMB, such as //192.168.1.20/backups."],
  ["nfs", "An NFS share", "Such as 192.168.1.20:/export/backups."],
  ["rclone", "A cloud remote", "Your own rclone remote, such as Backblaze B2, Google Drive or OneDrive."],
];

function copyField(label, input, hint) {
  if (hint) input.setAttribute("aria-describedby", `${input.id}-hint`);
  return el("div", { class: "field" }, el("label", { for: input.id, text: label }),
    hint ? el("span", { class: "hint", id: `${input.id}-hint`, text: hint }) : null, input);
}

function copyState(s) {
  if (!s || s.state === "none" || !s.state) return el("p", { class: "small muted", text: "No copy has been made yet." });
  if (s.state === "running") return notice("info", "Copying now", `${s.file ? `${s.file.split("/").pop()} to ${s.where || "the other place"}` : "To the other place"}. You can leave this page.`);
  if (s.state === "failed") return notice("danger", `The last copy did not work${s.finished ? `, ${formatDate(s.finished * 1000, true)}` : ""}`, s.error || "");
  return notice("success", `Last copy ${formatDate(s.finished * 1000, true)}`, s.said || "");
}

async function loadCopies(focusId) {
  const body = $("#copies-body");
  let c;
  try { c = await api("/api/backup/copies"); } catch (e) { body.replaceChildren(notice("danger", "Could not read where the copies go", e.message)); return; }
  body.removeAttribute("aria-busy");
  const kinds = el("fieldset", { class: "option-cards" }, el("legend", { text: "Where the copies go" }),
    COPY_KINDS.map(([value, title, text]) => el("label", { class: "option-card" },
      el("input", { type: "radio", name: "copies-kind", value, checked: value === c.kind }),
      el("strong", { text: title }), el("small", { text }))));
  const folder = locationPicker({ id: "copies-folder", label: "Folder on the other disk", app: "host", setting: "backups", value: c.folder,
    hint: "Not the folder the full backups are made in. A USB disk must be plugged in when a backup is made." });
  const smb = el("input", { class: "input", id: "copies-smb", value: c.smb, spellcheck: "false", autocomplete: "off", placeholder: "//192.168.1.20/backups" });
  const smbUser = el("input", { class: "input", id: "copies-smb-user", value: c.smb_user, spellcheck: "false", autocomplete: "off" });
  const smbPassword = el("input", { class: "input", id: "copies-smb-password", type: "password", autocomplete: "new-password" });
  const nfs = el("input", { class: "input", id: "copies-nfs", value: c.nfs, spellcheck: "false", autocomplete: "off", placeholder: "192.168.1.20:/export/backups" });
  const remote = el("input", { class: "input", id: "copies-remote", value: c.remote, spellcheck: "false", autocomplete: "off", placeholder: "mycloud:starboard-backups" });
  const config = el("textarea", { class: "input", id: "copies-rclone-config", rows: "5", spellcheck: "false", autocomplete: "off" });
  const keep = el("input", { class: "input input--narrow", id: "copies-keep", type: "number", min: "1", max: "50", value: String(c.keep), inputmode: "numeric" });
  const mine = el("input", { class: "input", id: "copies-mine", type: "password", autocomplete: "current-password" });
  const groups = {
    disk: el("div", { class: "stack-2", "data-kind": "disk" }, folder.node),
    smb: el("div", { class: "stack-2", "data-kind": "smb" },
      copyField("Share", smb, "As //computer/share, with a folder after it if you like."),
      copyField("User name", smbUser, "Leave empty for a share anyone on your network may write to."),
      copyField("Password", smbPassword, c.smb_password_set ? "Kept. Leave empty to keep it." : "The share's own password, kept by Starboard only.")),
    nfs: el("div", { class: "stack-2", "data-kind": "nfs" }, copyField("Share", nfs, "As computer:/folder. The share must let this computer write.")),
    rclone: el("div", { class: "stack-2", "data-kind": "rclone" },
      copyField("Remote and folder", remote, "As name:folder, the remote's name as it is in your rclone.conf."),
      copyField("The remote's part of rclone.conf", config, c.rclone_config_set
        ? "Kept. Leave empty to keep it, or paste it again to change it."
        : "Paste the lines from [name] to the next [ ]. rclone config file shows where rclone.conf is. Kept by Starboard only.")),
  };
  const keepField = el("div", { class: "stack-2" }, copyField("Keep the newest", keep, "How many full backups stay at the other place. Older ones there are removed."));
  const errorBox = el("div", { id: "copies-error", tabindex: "-1" });
  const save = el("button", { type: "submit", class: "btn btn--primary", id: "copies-save" }, "Save where the copies go");
  const form = el("form", { class: "form-stack", id: "copies-form", novalidate: true }, kinds, ...Object.values(groups), keepField,
    copyField("Your Starboard password", mine, "Asked each time, as the share's password and rclone's config are kept."), errorBox,
    el("div", { class: "actions" }, save));
  const show = () => {
    const kind = form.querySelector("input[name=copies-kind]:checked")?.value || "off";
    for (const [k, node] of Object.entries(groups)) node.hidden = k !== kind;
    keepField.hidden = kind === "off";
  };
  kinds.addEventListener("change", show);
  const state = el("div", { id: "copies-state", "aria-live": "polite" }, copyState(c.status));
  const test = el("button", { type: "button", class: "btn", id: "copies-test" }, icon("plug"), "Test the other place");
  const now = el("button", { type: "button", class: "btn", id: "copies-now" }, icon("copy"), "Copy the newest now");
  const stop = el("button", { type: "button", class: "btn btn--quiet", id: "copies-stop" }, "Stop making copies");
  const running = c.status?.state === "running";
  test.disabled = now.disabled = running;
  const active = c.kind !== "off";
  body.replaceChildren(form,
    active ? el("h3", { text: `Copies go to ${c.where}` }) : "",
    active ? el("div", { class: "actions" }, test, now, stop) : "",
    state);
  show();

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorBox.replaceChildren();
    const kind = form.querySelector("input[name=copies-kind]:checked")?.value || "off";
    save.disabled = true;
    try {
      await api("/api/backup/copies", { method: "PUT", body: { password: mine.value, kind, folder: folder.input.value.trim(), smb: smb.value.trim(),
        smb_user: smbUser.value.trim(), smb_password: smbPassword.value, nfs: nfs.value.trim(), remote: remote.value.trim(),
        rclone_config: config.value, keep: Number(keep.value) } });
      await loadCopies("copies-save");
      announce(kind === "off" ? "Saved: no copies are made" : "Saved: each new full backup is copied there");
    } catch (err) {
      errorBox.replaceChildren(el("div", { class: "notice", "data-tone": "danger", role: "alert" }, icon("circle-alert"),
        el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: "Not saved" }), el("p", { text: err.message }))));
      (err.status === 401 || err.status === 429 ? mine : errorBox).focus();
      save.disabled = false;
    }
  });
  test.addEventListener("click", async () => {
    test.disabled = true;
    state.replaceChildren(notice("info", "Testing", `Writing a small file to ${c.where} and removing it again.`));
    try {
      const r = await api("/api/backup/copies/test", { method: "POST" });
      state.replaceChildren(notice("success", "The other place works", r.said));
    } catch (err) { state.replaceChildren(notice("danger", "The test did not work", err.message)); }
    finally { test.disabled = false; test.focus(); }
  });
  now.addEventListener("click", async () => {
    now.disabled = true;
    try {
      await api("/api/backup/copies/now", { method: "POST" });
      announce("Copying the newest full backup");
      await loadCopies("copies-now");
    } catch (err) { state.replaceChildren(notice("danger", "Not copied", err.message)); now.disabled = false; now.focus(); }
  });
  stop.addEventListener("click", async () => {
    const r = await withPassword({
      title: "Stop making copies off this computer?",
      message: "New full backups stay only in their own folder. The share's password and rclone's config are removed from Starboard. Copies already made stay where they are.",
      confirm: "Stop making copies", danger: true,
      run: (password) => api("/api/backup/copies/forget", { method: "POST", body: { password } }),
    });
    if (!r) return;
    await loadCopies();
    $("input[name=copies-kind]:checked")?.focus();
    announce("Copies off this computer stopped");
  });
  if (focusId) $(`#${focusId}`)?.focus();
  if (running) {
    setTimeout(async () => {
      if (!document.body.contains(state)) return;
      const was = body.contains(document.activeElement) ? document.activeElement.id : null;
      await loadCopies(was);
    }, 3000);
  }
}

// When backups are made (DASH-17) ---------------------------------------------------------------------------------
// Settings pattern 3: four choice cards that apply at once, with the saved note under them. Then one status line: when
// the next one is, and what it makes, with at most one button.

const SCHEDULES = [
  ["off", "Off", "Starboard makes no backup by itself."],
  ["manual", "Manual", "You make each backup on this page. Starboard reminds you when the newest is more than 30 days old."],
  ["weekly", "Weekly", "Every Sunday at 03:00. The newest 4 are kept."],
  ["nightly", "Nightly", "Every night at 03:00. The newest 7 are kept."],
];

async function loadSchedule(focusAfter) {
  const body = $("#schedule-body");
  let s, full = null;
  try {
    [s, full] = await Promise.all([api("/api/backup/schedule"), api("/api/backup/full").catch(() => null)]);
  } catch (e) { body.replaceChildren(notice("danger", "Could not read when backups are made", e.message)); return; }
  body.removeAttribute("aria-busy");
  const canFull = !!(full && full.installed && full.docker && !full.cannot);
  const note = el("span", { class: "saved-note", id: "schedule-saved", hidden: true });
  const cards = el("fieldset", { class: "option-cards" }, el("legend", { class: "visually-hidden", text: "When backups are made" }),
    SCHEDULES.map(([value, title, text]) => el("label", { class: "option-card" },
      el("input", { type: "radio", name: "backup-schedule", value, checked: value === s.mode, onchange: () => chooseSchedule(value) }),
      el("strong", { text: title }), el("small", { text }))));
  body.replaceChildren(cards, note, scheduleState(s, canFull));
  if (focusAfter) $(`input[name=backup-schedule][value=${focusAfter}]`)?.focus();
}

function scheduleState(s, canFull) {
  const scheduled = s.mode === "weekly" || s.mode === "nightly";
  const parts = [];
  if (scheduled) {
    const makes = [s.key ? "a full backup without media" : null, s.server_job ? "the server's own backup" : null].filter(Boolean);
    const next = s.next ? formatDate(s.next * 1000, true) : "not worked out yet";
    if (makes.length) parts.push(notice("info", `Next backup: ${next}`, `It makes ${makes.join(", then ")}.${s.last_run ? ` Last time, ${formatDate(s.last_run * 1000, true)}: ${s.last_result}` : ""}`));
    else parts.push(notice("warning", "Nothing to back up yet", canFull
      ? "Scheduled full backups need the backup password, kept by Starboard so it can make them with nobody there."
      : "Starboard did not set up your apps and no backup job on the server is set up, so there is nothing it can make by itself.",
    canFull ? el("button", { type: "button", class: "btn btn--compact", id: "keep-key", onclick: (e) => openKeepKey(e.currentTarget) }, "Keep the backup password") : null));
  } else if (s.remind) {
    parts.push(notice("warning", s.newest ? "Your newest backup is more than 30 days old" : "No backup has been made yet",
      s.newest ? `It was made ${formatDate(s.newest * 1000, true)}. Make one below.` : "Make one below."));
  }
  if (s.key) {
    const forget = el("button", { type: "button", class: "btn btn--quiet btn--compact", id: "forget-key" }, "Forget it");
    forget.addEventListener("click", () => forgetKey());
    parts.push(el("div", { class: "notice", role: "status" }, icon("key-round"), el("div", { class: "notice__body" },
      el("span", { class: "notice__title", text: "Starboard keeps the key for scheduled full backups" }),
      el("p", { text: `Made from your backup password, never the password itself. Copies go to ${s.key.folder}, ${s.key.pictures ? "with" : "without"} the pictures you added.` })), forget));
  } else if (scheduled && canFull && (s.server_job)) {
    parts.push(el("div", { class: "actions" }, el("button", { type: "button", class: "btn btn--compact", id: "keep-key", onclick: (e) => openKeepKey(e.currentTarget) }, "Also make full backups")));
  }
  return el("div", { class: "stack-2", "aria-live": "polite" }, ...parts);
}

async function chooseSchedule(value) {
  try {
    await api("/api/config/general", { method: "PUT", body: { backup_schedule: value } });
  } catch (e) { problem(e.message); await loadSchedule(); return; }
  await loadSchedule(value);
  const note = $("#schedule-saved");
  if (note) window.SharedComponents.savedNote(note);
  const s = SCHEDULES.find(([v]) => v === value);
  announce(`Saved: ${s ? s[1] : value}`);
}

function openKeepKey(opener) {
  const folder = $("#full-folder")?.value?.trim() || "";
  const pictures = !!$("#full-pictures")?.checked;
  const pw1 = el("input", { class: "input", id: "key-pw-1", type: "password", autocomplete: "new-password", minlength: "10", "aria-describedby": "key-pw-1-hint" });
  const pw2 = el("input", { class: "input", id: "key-pw-2", type: "password", autocomplete: "new-password" });
  const mine = el("input", { class: "input", id: "key-mine", type: "password", autocomplete: "current-password" });
  const field = (label, input, hint) => el("div", { class: "field" }, el("label", { for: input.id, text: label }),
    hint ? el("span", { class: "hint", id: `${input.id}-hint`, text: hint }) : null, input, el("span", { class: "field-error", id: `${input.id}-error`, hidden: true }));
  const go = el("button", { type: "submit", class: "btn btn--primary", form: "key-form", text: "Keep it" });
  const cancel = el("button", { type: "button", class: "btn", text: "Cancel" });
  const form = el("form", { class: "form-stack", id: "key-form", novalidate: true },
    el("p", { text: `Scheduled full backups go into ${folder || "the folder chosen under Full without media"}, ${pictures ? "with" : "without"} the pictures you added. To change either, change it under Full without media first.` }),
    el("p", { class: "small muted", text: "Starboard keeps a key made from the password, never the password itself, in its own folder. Anyone who can read that folder can already read your apps' keys. The backups still open only with the password." }),
    field("A password for the backups", pw1, "At least 10 characters. Write it down: without it, nobody can open the backups, Starboard included."),
    field("The same password again", pw2), field("Your Starboard password", mine));
  const panel = sidePanel({ title: "Keep the backup password", opener, body: [form], foot: [go, cancel] });
  cancel.addEventListener("click", () => panel.close());
  const say = (input, text) => { const e = $(`#${input.id}-error`); e.textContent = text; e.hidden = !text; input.setAttribute("aria-invalid", text ? "true" : "false"); if (text) input.focus(); };
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    [pw1, pw2, mine].forEach((i) => say(i, ""));
    if (pw1.value.length < 10) { say(pw1, "Use at least 10 characters"); return; }
    if (pw1.value !== pw2.value) { say(pw2, "The two passwords are not the same"); return; }
    go.disabled = true;
    try {
      await api("/api/backup/schedule/key", { method: "POST", body: { password: mine.value, backup_password: pw1.value, folder, pictures } });
      panel.close(false);
      await loadSchedule();
      $("#forget-key")?.focus();
      announce("The backup password is kept for scheduled full backups");
    } catch (err) { say(/not right|attempts/i.test(err.message) ? mine : pw1, err.message); }
    finally { go.disabled = false; }
  });
  pw1.focus();
}

async function forgetKey() {
  const r = await withPassword({
    title: "Forget the key for scheduled full backups?",
    message: "Scheduled backups then make no full backup until you keep the password again. The backups already made still open with the password.",
    confirm: "Forget it", danger: true,
    run: (password) => api("/api/backup/schedule/forget", { method: "POST", body: { password } }),
  });
  if (!r) return;
  await loadSchedule();
  $("input[name=backup-schedule]:checked")?.focus();
  announce("The key is forgotten");
}

// Settings, Updates, Restore: how many versions' copies stay (DASH-109). Settings pattern 2: a select that applies at
// once, with the saved note beside it.
async function showKeepVersions() {
  const row = $("#keep-versions");
  let config;
  try { config = await api("/api/config"); } catch { row.hidden = true; return; }
  const select = el("select", { class: "select", id: "keep-versions-select", "aria-labelledby": "keep-versions-l", "aria-describedby": "keep-versions-h" },
    [5, 10, 20].map((n) => el("option", { value: String(n), text: `${n} versions`, selected: n === config.backup_keep_versions })));
  const note = el("span", { class: "saved-note", hidden: true });
  select.addEventListener("change", async () => {
    try {
      await api("/api/config/general", { method: "PUT", body: { backup_keep_versions: Number(select.value) } });
      window.SharedComponents.savedNote(note);
      await loadSaved();
    } catch (e) { problem(e.message, select); }
  });
  row.replaceChildren(el("li", { class: "setting" },
    el("div", { class: "setting__text" }, el("span", { class: "setting__label", id: "keep-versions-l", text: "Keep the copies of the last" }),
      el("span", { class: "setting__hint", id: "keep-versions-h", text: "Older copies are removed by themselves when a new one is made. Each version can have several copies." })),
    el("div", { class: "setting__control" }, select, note)));
}

// Settings, Updates, Restore: the command to go back names the version before this one.
async function showGoBack() {
  const box = $("#back-command");
  try {
    const r = await api("/api/releases");
    const before = r.all.find((rel) => isNewer(r.current, rel.version));
    if (before) box.querySelector("code").textContent = `./update.sh --to v${before.version}`;
  } catch { /* keeps the example version */ }
  box.append(copyButton(box.querySelector("code").textContent, "the command to go back"));
}

startPage().then((session) => {
  if (!session) return;
  // The same script runs System, Backup and restore and Settings, Updates, Restore (no download or server there).
  if ($("#back-command")) { showGoBack(); loadSaved(); showKeepVersions(); }
  const picker = $("#restore-input");
  $("#restore-file").addEventListener("click", () => picker.click());
  picker.addEventListener("change", async () => {
    const file = picker.files[0];
    picker.value = "";
    if (file) await restoreFromFile(file);
    $("#restore-file").focus();
  });
  if ($("#back-command")) return;
  $("#download").addEventListener("click", download);
  loadFull().then(() => loadSchedule());
  loadCopies();
  loadServer();
  loadSaved();
});
