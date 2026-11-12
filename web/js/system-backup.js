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
    box.replaceChildren(el("div", { class: "empty" },
      el("p", { text: "No server backup job is set up, so Starboard cannot back up the whole server. The help article Back up the whole server explains how to set one up." })));
    $("#backup-summary").textContent = "Keep a copy of the whole server, and of Starboard's settings.";
    return;
  }
  const focusKey = box.contains(document.activeElement) ? document.activeElement.closest("[data-key]")?.dataset.key : null;
  const prompt = el("input", { type: "checkbox", role: "switch", id: "with-prompt", checked: localPrompt() });
  prompt.addEventListener("change", () => { try { localStorage.setItem("starboard.backup.prompt", prompt.checked ? "1" : "0"); } catch { /* fine */ } });
  const run = el("button", { type: "button", class: "btn btn--primary", id: "server-run", disabled: busy }, icon("play"), busy ? "Backing up now" : "Back up the server now");
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
  $("#backup-summary").textContent = s && s.status
    ? [`Last server backup ${runTime(s)}`, (STATUS_WORDS[s.status] || [s.status])[0].toLowerCase()].join(" · ")
    : "No server backup has run yet.";
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
  try { ({ items } = await api("/api/backup/saved")); } catch (e) { $("#saved").replaceChildren(el("li", { class: "empty", text: e.message })); return; }
  $("#saved").replaceChildren(...(items.length ? items.map((item) => el("li", { class: "row row--opens", "data-key": item.name },
    el("span", { class: "app-icon", "aria-hidden": "true" }, icon("history", 20)),
    el("div", { class: "row__text" },
      el("div", { class: "row__title" }, el("button", { type: "button", onclick: (e) => openSaved(item, e.currentTarget) }, when(item.saved))),
      el("div", { class: "row__meta", text: `${item.reason} · ${formatBytes(item.size)}` })),
    el("div", { class: "row__side" },
      el("button", { type: "button", class: "btn btn--danger", onclick: () => restoreSaved(item) }, "Restore", el("span", { class: "visually-hidden", text: ` the copy from ${when(item.saved)}` })))))
    : [el("li", {}, emptyState("No saved copies yet", "Starboard makes one before every restore and before an update changes the settings. To bring back a copy from elsewhere, use Restore from a file."))]));
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
  if ($("#back-command")) { showGoBack(); loadSaved(); }
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
  loadServer();
  loadSaved();
});
