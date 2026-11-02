// Backup and restore: Starboard's settings (download, restore from a file or a saved copy) and the server's
// own backup job.

let pendingRestore = null;  // { kind: "file" | "saved", value } waiting for the second press
let serverTimer = null;

function saveFile(data) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const link = el("a", { href: URL.createObjectURL(blob), download: `starboard-settings-${new Date().toISOString().slice(0, 10)}.json` });
  document.body.append(link);
  link.click();
  setTimeout(() => { URL.revokeObjectURL(link.href); link.remove(); }, 1000);
}

async function download(event) {
  event.preventDefault();
  const form = event.target;
  $("#download-error").textContent = "";
  try {
    const data = await api("/api/backup/settings", { method: "POST", body: { password: form.password.value } });
    saveFile(data);
    form.reset();
    toast(`Backup saved: ${data.services.length} apps`);
  } catch (e) {
    $("#download-error").textContent = e.message;
  }
}

function confirmFirst(kind, value, label) {
  // Two presses, as in Settings: the first explains, the second restores. No browser pop-ups.
  if (pendingRestore && pendingRestore.kind === kind && pendingRestore.value === value) { pendingRestore = null; return true; }
  pendingRestore = { kind, value };
  const box = $("#restore-confirm");
  box.textContent = `This replaces your apps and settings with ${label}. A copy of the current ones is saved first. Press Restore again to go ahead.`;
  box.hidden = false;
  box.scrollIntoView({ block: "nearest" });
  return false;
}

async function restoreFile(event) {
  event.preventDefault();
  const form = event.target;
  $("#restore-error").textContent = "";
  const file = form.file.files[0];
  if (!file) { $("#restore-error").textContent = "Choose a backup file"; return; }
  if (file.size > 2 * 1024 * 1024) { $("#restore-error").textContent = "That file is too large to be a Starboard backup"; return; }
  let backup;
  try { backup = JSON.parse(await file.text()); } catch { $("#restore-error").textContent = "That file is not a Starboard backup"; return; }
  if (!confirmFirst("file", `${file.name}:${file.size}`, `the ones in ${file.name}`)) return;
  try {
    const result = await api("/api/backup/restore", { method: "POST", body: { password: form.password.value, backup } });
    form.reset();
    $("#restore-confirm").hidden = true;
    toast(`Restored: ${result.apps} apps`);
    loadSaved();
  } catch (e) {
    $("#restore-error").textContent = e.message;
  }
}

async function restoreSaved(item) {
  const password = $("#restore-password").value;
  $("#restore-error").textContent = "";
  if (!password) {
    $("#restore-error").textContent = "Enter your password above, then press Restore on the copy again";
    $("#restore-password").focus();
    return;
  }
  if (!confirmFirst("saved", item.name, `the copy from ${formatDate(item.saved * 1000, true)}`)) return;
  try {
    const result = await api("/api/backup/restore-saved", { method: "POST", body: { password, name: item.name } });
    $("#restore-confirm").hidden = true;
    $("#restore-password").value = "";
    toast(`Restored: ${result.apps} apps`);
    loadSaved();
  } catch (e) {
    $("#restore-error").textContent = e.message;
  }
}

async function loadSaved() {
  const { items } = await api("/api/backup/saved");
  const list = $("#saved");
  list.replaceChildren(...(items.length ? items.map((item) => el("li", { class: "row" },
    el("div", {}, el("p", { class: "row__title", text: formatDate(item.saved * 1000, true) }), el("p", { class: "row__meta", text: item.reason })),
    el("div", { class: "row__side" }, el("button", { type: "button", class: "btn", onclick: () => restoreSaved(item) }, "Restore", el("span", { class: "visually-hidden", text: ` the copy from ${formatDate(item.saved * 1000, true)}` })))))
    : [el("li", { class: "empty", text: "No saved copies yet." })]));
}

const STATUS_WORDS = { running: ["Backing up now", "info"], waiting: ["Starting", "info"], done: ["Finished", "success"], failed: ["Failed", "danger"] };

async function loadServer() {
  const data = await api("/api/backup/server");
  const box = $("#server-status");
  const run = $("#server-run");
  if (!data.configured) {
    box.replaceChildren(el("p", { class: "empty", text: "No server backup job is set up. See Backup and restore in the README." }));
    run.hidden = true;
    $("#server-files").replaceChildren();
    return;
  }
  run.hidden = !data.can_run;
  const s = data.status;
  if (s && s.status) {
    const [label, tone] = STATUS_WORDS[s.status] || [s.status, "neutral"];
    const when = s.finished ? `Finished ${formatDate(s.finished * 1000, true)}` : s.started ? `Started ${formatDate(s.started * 1000, true)}` : "";
    box.replaceChildren(el("div", { class: "row" },
      el("div", {}, el("p", { class: "row__title", text: s.with_prompt ? "Last backup, with a rebuild prompt" : "Last backup" }), el("p", { class: "row__meta", text: [when, s.summary].filter(Boolean).join(" · ") })),
      el("div", { class: "row__side" }, chip(label, tone))));
    run.disabled = s.status === "running" || s.status === "waiting";
  } else {
    box.replaceChildren(el("p", { class: "hint", text: "No backup has run yet." }));
    run.disabled = false;
  }
  $("#server-files").replaceChildren(...(data.files.length ? data.files.map((f) => el("li", { class: "row" },
    el("div", {}, el("p", { class: "row__title", text: f.name }), el("p", { class: "row__meta num", text: `${formatBytes(f.size)} · ${formatDate(f.modified * 1000, true)}` }))))
    : [el("li", { class: "empty", text: "No backup files found yet." })]));
  // While a backup runs, look again every 5 seconds.
  clearTimeout(serverTimer);
  if (s && (s.status === "running" || s.status === "waiting")) serverTimer = setTimeout(loadServer, 5000);
}

startPage().then(() => {
  $("#download-form").addEventListener("submit", download);
  $("#restore-form").addEventListener("submit", restoreFile);
  $("#restore-form").addEventListener("change", () => { pendingRestore = null; $("#restore-confirm").hidden = true; });
  $("#server-run").addEventListener("click", async () => {
    try {
      await api("/api/backup/server", { method: "POST", body: { with_prompt: $("#with-prompt").checked } });
      announce("Server backup started");
      loadServer();
    } catch (e) { toast(e.message); }
  });
  loadSaved();
  loadServer();
});
