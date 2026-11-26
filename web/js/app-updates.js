// Updates: every app on the Apps page, in the same categories and order, with the container it runs in, the
// version installed and the newest one. Update all is the page's one action; to update some, tick them and use
// Update chosen in the selection bar (DESIGN-SYSTEM.md section 10: no Update on every row). Checking asks each image's registry; updating downloads
// the new image and restarts the app with Docker Compose. Needs Docker access (see About and updates).

let data = null;
let config = null;
let poll = null;
let busyBefore = false;
const chosen = new Set(); // ids ticked for Update chosen

const PHASE = {
  queued: "Waiting to start", downloading: "Downloading", downloaded: "Downloaded, waiting to install",
  installing: "Installing", done: "Updated", failed: "Update failed",
};

function jobItem(row) {
  return row.container && data.job && !data.job.finished ? data.job.items[row.container.name] : null;
}

function lastResult(row) {
  return row.container && data.job?.finished ? data.job.items[row.container.name] : null;
}

const busy = () => !!(data?.job && !data.job.finished);
const safe = (r) => r.update && !r.big_change;

function statusCell(row) {
  const item = jobItem(row);
  if (item) {
    const words = item.phase === "downloading" ? `${PHASE.downloading}, ${Math.round(item.pct)}%` : PHASE[item.phase] || item.phase;
    let bar = null;
    if (item.phase === "downloading") {
      bar = el("div", { class: "progress", role: "progressbar", "aria-label": `Downloading ${row.name}`,
        "aria-valuenow": String(Math.round(item.pct)), "aria-valuemin": "0", "aria-valuemax": "100" }, el("span"));
      bar.firstChild.style.width = `${item.pct}%`;  // set in script: the page's policy blocks style attributes
    }
    return [chip(words, "info"), bar];
  }
  const done = lastResult(row);
  // The chip holds no version (DASH-309, R3): the version is in the small line beside it.
  if (done?.phase === "done") return [chip("Updated", "success"), done.version ? el("div", { class: "small muted", text: `Now ${done.version}` }) : null];
  if (done?.phase === "failed") return [chip(...STATUS.failed), el("div", { class: "small", text: done.error || "" })];
  if (!row.container) return chip("No container found", "muted");
  if (row.update) return chip(...(row.big_change ? STATUS.checkFirst : STATUS.updateAvailable));
  if (row.error) return [chip("Cannot check", "muted"), el("div", { class: "small muted", text: row.error })];
  if (data.checked_at && !row.unknown) return chip(...STATUS.upToDate);
  if (data.checked_at) return chip("Cannot check", "muted");
  return chip(...STATUS.notChecked);
}

function actionCell(row) {
  if (!row.update || jobItem(row)) return null;
  // What is new: the changes in the waiting update, from the app's own changelog (Reelix).
  return row.changelog ? el("button", { type: "button", class: "btn btn--compact",
    onclick: (e) => openAppChanges({ app: row.id, name: row.name, from: row.container?.version || "", to: row.latest || "", opener: e.currentTarget }) },
    "What is new", el("span", { class: "visually-hidden", text: ` in ${row.name}` })) : null;
}

// A tick for each app with an update; the selection bar updates the ticked ones.
function chooseBox(row) {
  if (!row.update || jobItem(row)) { chosen.delete(row.id); return null; }
  const box = el("input", { type: "checkbox", id: `choose-${row.id}`, class: "updates-choose", "aria-label": `Choose ${row.name}`,
    checked: chosen.has(row.id), disabled: busy() });
  box.addEventListener("change", () => { if (box.checked) chosen.add(row.id); else chosen.delete(row.id); selectionBar(); });
  return box;
}

function selectionBar() {
  const n = chosen.size;
  $("#updates-chosen").hidden = !n;
  $("#updates-chosen-text").textContent = `${n} chosen`;
  $("#update-chosen").disabled = busy() || !n;
}

function tableFor(rows, caption) {
  // The same table every list of updates uses (update-table.js); Apps has an Image column as well.
  return updateTable({ caption, nameLabel: "App", extra: [{ key: "image", label: "Image" }], rows: rows.map((r) => {
    const c = r.container;
    return { id: r.id, thId: `update-${r.id}`,
      name: el("div", { class: "updates-app" }, chooseBox(r), appIcon(r, "app-icon updates-app__icon"),
        el("div", {}, el("strong", { text: r.name }),
          el("div", { class: "small muted", text: c ? `${c.name} · ${c.status || c.state}` : "Choose its container in Manage apps" }))),
      extra: { image: c ? el("code", { text: c.image }) : "None" },
      installed: c ? (c.version || (c.created ? `Built ${formatDate(c.created)}` : "Not known")) : "",
      latest: r.latest || (r.update ? "Newer build" : ""), status: statusCell(r), actions: actionCell(r) };
  }) });
}

function render() {
  const rows = data.items;
  const groups = [...(config.groups || [])];
  const sections = [];
  for (const g of groups) {
    const inGroup = rows.filter((r) => !r.background && r.group === g);
    if (inGroup.length) sections.push([g, inGroup]);
  }
  const loose = rows.filter((r) => !r.background && !groups.includes(r.group));
  if (loose.length) sections.push(["Other apps", loose]);
  const background = rows.filter((r) => r.background);
  if (background.length) sections.push(["Other services", background]);
  // Keep focus on the same button or tick across the redraw.
  const active = document.activeElement?.closest?.("#updates") ? document.activeElement : null;
  const focused = active && !active.id ? active.textContent : null;
  const focusedId = active?.id || null;
  $("#updates").replaceChildren(...sections.map(([name, list], i) => el("section", { class: "media-section", "aria-labelledby": `ug-${i}` },
    el("h2", { class: "group-heading", id: `ug-${i}`, text: name }), tableFor(list, `Updates for ${name}`))));
  if (focusedId) document.getElementById(focusedId)?.focus();
  else if (focused) [...$$("#updates button")].find((b) => b.textContent === focused)?.focus();
  selectionBar();

  const available = rows.filter((r) => r.update);
  const all = rows.filter(safe);
  const updateAll = $("#update-all");
  updateAll.disabled = busy() || !all.length;
  $("span", updateAll).textContent = busy() ? "Updating…" : all.length ? `Update all (${all.length})` : "Update all";
  $("#check-updates").disabled = busy();
  $("span", $("#check-updates")).textContent = data.checked_at ? "Check again" : "Check"; // "again" only after a first check
  const missing = rows.filter((r) => !r.container).length;
  $("#updates-summary").textContent = busy() ? "Updating. Apps restart for a moment as they update."
    : updateSummary({ checkedAt: data.checked_at || 0, restored: !!data.restored, count: available.length,
      extra: missing ? [`${missing} ${missing === 1 ? "app has" : "apps have"} no container found`] : [] });
  $("#updates-log").hidden = !data.job?.finished || !data.job.log;
  $("#updates-log-text").textContent = data.job?.log || "";

  if (busy() && !poll) poll = setInterval(() => { if (!document.hidden) refresh(); }, 1500); // a hidden tab waits
  if (!busy() && poll) { clearInterval(poll); poll = null; }
  if (busyBefore && !busy()) announce("The update has finished");
  busyBefore = busy();
}

function showUnavailable() {
  $("#updates-summary").textContent = "Updates need Docker access, which is inactive.";
  $("#check-updates").disabled = true;
  $("#updates-notice").replaceChildren(el("div", { class: "notice", role: "status" }, icon("info"),
    el("div", { class: "notice__body" },
      el("span", { class: "notice__title", text: "Starboard cannot reach your apps' containers" }),
      el("p", {}, "To check and install updates, Starboard needs access to Docker on the server. That access is full control of Docker, so it is inactive unless you choose it. ",
        el("a", { href: "/settings-updates.html#access", text: "What Starboard can access, and how to change it" }), "."))));
}

async function refresh() {
  try {
    data = await api("/api/containers");
    if (!data.available) return showUnavailable();
    render();
    if (!busy()) appChangeNotices(); // the versions were just compared, so a finished update shows its notice
  } catch (e) {
    $("#updates-summary").textContent = e.message;
  }
}

async function check() {
  const button = $("#check-updates");
  button.disabled = true;
  $("#updates-summary").textContent = "Checking for updates. This asks each image's registry and can take a minute.";
  try {
    data = await api("/api/containers/check", { method: "POST" });
    render();
    announce($("#updates-summary").textContent);
  } catch (e) {
    $("#updates-summary").textContent = `Could not check: ${e.message}`;
  } finally {
    button.disabled = busy();
  }
}

async function runUpdate(rows) {
  const names = rows.map((r) => r.name);
  const list = names.length > 2 ? `${names.slice(0, -1).join(", ")} and ${names.at(-1)}` : names.join(" and ");
  const ok = await confirmDialog({
    title: rows.length === 1 ? `Update ${names[0]}?` : `Update ${rows.length} apps?`,
    message: `${list} ${rows.length === 1 ? "restarts" : "restart"} for a moment. Anything that depends on ${rows.length === 1 ? "it" : "them"} restarts too.`,
    confirm: rows.length === 1 ? `Update ${names[0]}` : `Update ${rows.length} apps`,
  });
  if (!ok) return;
  try {
    data = await api("/api/containers/update", { method: "POST", body: { ids: rows.map((r) => r.id) } });
    chosen.clear();
    render();
    announce(`Updating ${list}`);
  } catch (e) {
    problem(`Not started: ${e.message}`);
  }
}

// ?app=storyarr (Storyarr's Upgrade now, through BOOK_UPGRADE_URL): check straight away and go to that app.
async function openFor(wanted) {
  await check();
  const key = wanted.toLowerCase();
  const row = (data.items || []).find((r) => r.id.toLowerCase() === key || r.name.toLowerCase() === key);
  const cell = row && document.getElementById(`update-${row.id}`);
  if (!cell) return;
  cell.scrollIntoView({ block: "center" });
  cell.focus({ preventScroll: true });
  announce(row.update ? `${row.name} can be updated to ${row.latest || "a newer build"}` : `${row.name} is up to date`);
}

startPage().then(async () => {
  config = await api("/api/config").catch(() => ({ groups: [] }));
  $("#check-updates").addEventListener("click", check);
  $("#update-all").addEventListener("click", () => runUpdate(data.items.filter(safe)));
  $("#update-chosen").addEventListener("click", () => runUpdate(data.items.filter((r) => chosen.has(r.id) && r.update)));
  $("#clear-chosen").addEventListener("click", () => {
    chosen.clear();
    render();
    announce("None chosen");
    $("#updates input.updates-choose")?.focus();
  });
  await refresh();
  document.addEventListener("visibilitychange", () => { if (!document.hidden && poll) refresh(); }); // catch up at once
  const wanted = new URLSearchParams(location.search).get("app");
  if (wanted && data.available) openFor(wanted);
});
