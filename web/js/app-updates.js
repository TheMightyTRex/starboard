// Updates: every app on the Apps page, in the same categories and order, with the container it runs in, the
// version installed, the newest one, and Update buttons. Checking asks each image's registry; updating downloads
// the new image and restarts the app with Docker Compose. Needs Docker access (see About and updates).

let data = null;
let config = null;
let poll = null;
let busyBefore = false;

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
  if (done?.phase === "done") return chip(done.version ? `Updated to ${done.version}` : "Updated", "success");
  if (done?.phase === "failed") return [chip("Update failed", "danger"), el("div", { class: "small", text: done.error || "" })];
  if (!row.container) return chip("No container found", "muted");
  if (row.update) return chip(row.big_change ? "Big change: check first" : "Update available", row.big_change ? "warning" : "info");
  if (row.error) return [chip("Cannot check", "muted"), el("div", { class: "small muted", text: row.error })];
  if (data.checked_at && !row.unknown) return chip("Up to date", "success");
  if (data.checked_at) return chip("Cannot check", "muted");
  return chip("Not checked yet", "neutral");
}

function actionCell(row) {
  if (!row.update || jobItem(row)) return null;
  // What is new: the changes in the waiting update, from the app's own changelog (Reelix).
  const news = row.changelog ? el("button", { type: "button", class: "btn btn--compact",
    onclick: (e) => openAppChanges({ app: row.id, name: row.name, from: row.container?.version || "", to: row.latest || "", opener: e.currentTarget }) },
    "What is new", el("span", { class: "visually-hidden", text: ` in ${row.name}` })) : null;
  const update = el("button", { type: "button", class: "btn btn--compact", // in a dense table; "Update all" is the page's one primary
    disabled: busy(), onclick: () => runUpdate([row]) }, "Update", el("span", { class: "visually-hidden", text: ` ${row.name}` }));
  return news ? el("div", { class: "updates-actions" }, news, update) : update;
}

function tableFor(rows, caption) {
  return el("div", { class: "table-wrap", "data-stack": true },
    el("table", { class: "table updates-table" },
      el("caption", { class: "visually-hidden", text: caption }),
      // The same column widths in every category's table, so the columns line up down the page.
      el("colgroup", {}, ["app", "image", "installed", "latest", "status", "actions"].map((c) => el("col", { class: `updates-table__${c}` }))),
      el("thead", {}, el("tr", {}, ["App", "Image", "Installed", "Latest", "Status"].map((h) => el("th", { scope: "col", text: h })),
        el("th", { scope: "col" }, el("span", { class: "visually-hidden", text: "Actions" })))),
      el("tbody", {}, rows.map((r) => {
        const c = r.container;
        return el("tr", {},
          el("th", { scope: "row", "data-label": "App", id: `update-${r.id}`, tabindex: "-1" },
            el("div", { class: "updates-app" }, appIcon(r, "app-icon updates-app__icon"),
              el("div", {}, el("strong", { text: r.name }),
                el("div", { class: "small muted", text: c ? `${c.name} · ${c.status || c.state}` : "Choose its container in Manage apps" })))),
          el("td", { "data-label": "Image" }, c ? el("code", { text: c.image }) : "None"),
          el("td", { "data-label": "Installed" }, c ? (c.version || (c.created ? `Built ${formatDate(c.created)}` : "Not known")) : ""),
          el("td", { "data-label": "Latest" }, r.latest || (r.update ? "Newer build" : "")),
          el("td", { "data-label": "Status" }, statusCell(r)),
          el("td", { "data-label": "Actions" }, actionCell(r)));
      }))));
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
  // Keep focus on the same button across the redraw.
  const focused = document.activeElement?.closest?.("#updates") ? document.activeElement.textContent : null;
  $("#updates").replaceChildren(...sections.map(([name, list], i) => el("section", { class: "media-section", "aria-labelledby": `ug-${i}` },
    el("h2", { class: "group-heading", id: `ug-${i}`, text: name }), tableFor(list, `Updates for ${name}`))));
  if (focused) [...$$("#updates button")].find((b) => b.textContent === focused)?.focus();

  const available = rows.filter((r) => r.update);
  const all = rows.filter(safe);
  const updateAll = $("#update-all");
  updateAll.disabled = busy() || !all.length;
  $("span", updateAll).textContent = busy() ? "Updating…" : all.length ? `Update all (${all.length})` : "Update all";
  $("#check-updates").disabled = busy();
  $("span", $("#check-updates")).textContent = data.checked_at ? "Check again" : "Check"; // "again" only after a first check
  const checked = data.checked_at ? new Date(data.checked_at * 1000).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }) : null;
  const missing = rows.filter((r) => !r.container).length;
  $("#updates-summary").textContent = busy() ? "Updating. Apps restart for a moment as they update."
    : [checked ? `Last checked at ${checked}` : "Not checked since Starboard started",
      checked ? (available.length ? `${available.length} ${available.length === 1 ? "update" : "updates"} available` : "everything is up to date") : null,
      missing ? `${missing} ${missing === 1 ? "app has" : "apps have"} no container found` : null].filter(Boolean).join(" · ");
  $("#updates-log").hidden = !data.job?.finished || !data.job.log;
  $("#updates-log-text").textContent = data.job?.log || "";

  if (busy() && !poll) poll = setInterval(refresh, 1500);
  if (!busy() && poll) { clearInterval(poll); poll = null; }
  if (busyBefore && !busy()) announce("The update has finished");
  busyBefore = busy();
}

function showUnavailable() {
  $("#updates-summary").textContent = "Updates need Docker access, which is inactive.";
  $("#check-updates").disabled = true;
  $("#updates-notice").replaceChildren(el("div", { class: "notice", role: "status" }, icon("info"),
    el("div", { class: "notice__body" },
      el("span", { class: "notice__title", text: "Starboard cannot see your containers" }),
      el("p", {}, "To check and install updates, Starboard needs access to Docker on the server. That access is full control of Docker, so it is inactive unless you choose it. ",
        el("a", { href: "/settings-updates.html#access", text: "See what Starboard can access and how to change it" }), "."))));
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
  await refresh();
  const wanted = new URLSearchParams(location.search).get("app");
  if (wanted && data.available) openFor(wanted);
});
