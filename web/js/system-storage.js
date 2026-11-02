// Storage: free space in each folder Starboard has been given (STARBOARD_DISKS). One list, fullest first;
// each row opens a slide-out with the folder's details. The set-up hint shows only when nothing is set up.

let repo = "";
let disks = [];

const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
const timeNow = () => new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
const pctUsed = (d) => Math.round((d.used / d.total) * 100);

// "7.6 of 8 TB": the used amount in the same unit as the total.
function sizePair(used, total) {
  const units = ["B", "KB", "MB", "GB", "TB", "PB"];
  const i = total ? Math.min(Math.floor(Math.log(total) / Math.log(1024)), units.length - 1) : 0;
  const fmt = (n) => String(Number((n / 1024 ** i).toFixed(1)));
  return `${fmt(used)} of ${fmt(total)} ${units[i]}`;
}

function status(d) {
  if (d.missing) return ["warning", "Not found"];
  const pct = pctUsed(d);
  if (pct >= 98) return ["danger", "Full"];
  if (pct >= 90) return ["warning", "Nearly full"];
  return ["success", "Healthy"];
}

function bar(pct, tone) {
  const node = el("div", { class: "progress", "data-tone": tone === "success" ? null : tone, role: "img", "aria-label": `${pct}% used` }, el("span"));
  node.firstChild.style.width = `${pct}%`;
  return node;
}

const guideLink = (text, anchor) => el("a", { class: "btn", href: `https://github.com/${repo}#${anchor}`, target: "_blank", rel: "noopener noreferrer" },
  el("span", { text }), el("span", { class: "visually-hidden", text: " (opens in a new tab)" }));

function folderBody(d) {
  const [tone, word] = status(d);
  if (d.missing) {
    return [chip(word, tone),
      el("div", { class: "notice", "data-tone": "warning", role: "status" }, icon("triangle-alert"),
        el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: "Starboard cannot find this folder" }),
          el("p", { text: `Check the path for ${d.label} in STARBOARD_DISKS and that the folder is mounted into Starboard, then restart Starboard.` }))),
      repo ? guideLink("Open the set-up guide", "free-space-on-the-system-page") : null];
  }
  const pct = pctUsed(d);
  return [
    el("div", { class: "meter" },
      el("div", { class: "meter__label" }, chip(word, tone), el("span", { class: "numeric", text: `${sizePair(d.used, d.total)} used (${pct}%)` })),
      bar(pct, tone)),
    pct >= 90 ? el("div", { class: "notice", "data-tone": tone, role: "status" }, icon("triangle-alert"),
      el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: `${formatBytes(d.free)} left` }),
        el("p", { text: "Free some space or add a disk before it fills. Downloads stop when there is no room." }))) : null,
    el("dl", { class: "facts" },
      el("dt", { text: "Filesystem" }), el("dd", {}, d.filesystem ? el("span", { class: "tag", text: d.filesystem }) : "Not reported"),
      el("dt", { text: "Used" }), el("dd", { class: "numeric", text: formatBytes(d.used) }),
      el("dt", { text: "Free" }), el("dd", { class: "numeric", text: formatBytes(d.free) }),
      el("dt", { text: "Size" }), el("dd", { class: "numeric", text: formatBytes(d.total) })),
  ];
}

function openFolder(d, opener) {
  const again = el("button", { type: "button", class: "btn" }, icon("refresh-cw"), el("span", { text: "Check again" }));
  const panel = sidePanel({ title: d.label, opener, body: folderBody(d).filter(Boolean), foot: [again] });
  again.addEventListener("click", async () => {
    await load();
    const now = disks.find((x) => x.label === d.label);
    if (now) panel.body.replaceChildren(...folderBody(now).filter(Boolean));
    announce(`Checked ${d.label} again.`);
  });
}

function row(d) {
  const [tone, word] = status(d);
  const title = el("button", { type: "button", "aria-haspopup": "dialog", text: d.label, onclick: (e) => openFolder(d, e.currentTarget) });
  if (d.missing) {
    return el("li", { class: "row row--opens row--no-lead" },
      el("div", {}, el("p", { class: "row__title" }, title), el("p", { class: "row__meta", text: "Starboard cannot find this folder" })),
      el("div", { class: "row__side" }, chip(word, tone)));
  }
  const pct = pctUsed(d);
  return el("li", { class: "row row--opens row--no-lead" },
    el("div", {}, el("p", { class: "row__title" }, title), d.filesystem ? el("p", { class: "row__meta", text: `${d.filesystem} filesystem` }) : null),
    el("div", { class: "row__side" }, el("span", { class: "numeric", text: `${sizePair(d.used, d.total)} used (${pct}%) · ${formatBytes(d.free)} free` }), chip(word, tone)),
    bar(pct, tone));
}

function stat(value, label, tone) {
  return el("div", { class: "stat", "data-tone": tone ? tone[0] : null },
    el("span", { class: "stat__value", text: value }), el("span", { class: "stat__label", text: label }), tone ? chip(tone[1], tone[0]) : null);
}

async function load() {
  try {
    const sys = await api("/api/system");
    disks = sys.disks;
    const box = $("#storage");
    const stats = $("#storage-stats");
    if (!disks.length) {
      stats.replaceChildren();
      box.replaceChildren(el("div", { class: "empty" }, icon("hard-drive", 32),
        el("h2", { text: "No folders set up yet" }),
        el("p", { text: "Starboard shows free space for the folders listed in STARBOARD_DISKS, each mounted read-only. Add them to the compose file and restart Starboard." }),
        repo ? guideLink("Open the set-up guide", "free-space-on-the-system-page") : null));
      $("#storage-summary").textContent = "Not set up";
      return;
    }
    const found = disks.filter((d) => !d.missing);
    const missing = disks.length - found.length;
    const total = found.reduce((t, d) => t + d.total, 0);
    const used = found.reduce((t, d) => t + d.used, 0);
    const full = found.filter((d) => pctUsed(d) >= 90).length;
    stats.replaceChildren(
      stat(formatBytes(total), "Total space"),
      stat(formatBytes(used), `Used (${total ? Math.round((used / total) * 100) : 0}%)`),
      stat(String(full), "Folders over 90% full", full ? ["warning", "Nearly full"] : null),
      missing ? stat(String(missing), missing === 1 ? "Folder not found" : "Folders not found", ["warning", "Not found"]) : null);
    const sorted = [...disks].sort((a, b) => (b.missing ? 101 : pctUsed(b)) - (a.missing ? 101 : pctUsed(a)));
    let list = $("ul.rows", box);
    if (!list) { list = el("ul", { class: "rows", "aria-label": "Folders, fullest first" }); box.replaceChildren(list); }
    renderKeyed(list, sorted, (d) => d.label, (d) => row(d));
    const parts = [plural(disks.length, "folder", "folders")];
    if (full) parts.push(`${full} nearly full`);
    if (missing) parts.push(`${missing} not found`);
    parts.push(`updated at ${timeNow()}`);
    $("#storage-summary").textContent = parts.join(" · ");
  } catch (e) {
    $("#storage-summary").textContent = `Could not load storage: ${e.message}`;
  }
}

// What is using the space: on demand; the server walks the folders in the background and keeps the answer.
let usageTimer = null;

function renderUsage(u) {
  $("#usage-panel").hidden = !disks.length;
  const button = $("#usage-run");
  button.disabled = !!u.running;
  $("span", button).textContent = u.running ? "Working it out…" : u.finished ? "Work it out again" : "Work it out now";
  $("#usage-when").textContent = u.running ? "Reading the folders now" : u.finished ? `Worked out ${formatDate(u.finished * 1000, true)}` : "Not worked out yet";
  clearTimeout(usageTimer);
  if (u.running) usageTimer = setTimeout(loadUsage, 5000);
  if (!u.folders) { $("#usage").replaceChildren(); return; }
  $("#usage").replaceChildren(...u.folders.map((f) => {
    const total = f.items.reduce((t, i) => t + i.bytes, 0) || 1;
    return el("section", { class: "sys-block", "aria-label": f.label },
      el("h3", { text: f.label }),
      el("ul", { class: "meter-list" }, f.items.slice(0, 12).map((i) => el("li", {},
        el("div", { class: "meter__label" }, el("span", { text: i.name }), el("span", { class: "numeric", text: formatBytes(i.bytes) })),
        el("div", { class: "progress", role: "presentation" }, el("span", { style: `width:${Math.max(1, (i.bytes / total) * 100)}%` }))))));
  }));
}

async function loadUsage() {
  try { renderUsage(await api("/api/usage")); } catch { /* the folders above still show */ }
}

// Drives in this computer, from the SMART job's lsblk.json: unmounted partitions and Windows file systems stand out.
async function loadDevices() {
  let d;
  try { d = await api("/api/disk-health"); } catch { return; }
  $("#devices-panel").hidden = !d.devices?.length;
  if (!d.devices?.length) return;
  const rows = d.devices.flatMap((disk) => disk.parts.map((p) => {
    const fs = (p.fs || "").toLowerCase();
    const notes = [];
    if (!p.mounted.length) notes.push(chip("Not mounted", "muted"));
    if (fs === "ntfs" || fs === "exfat" || fs === "vfat") notes.push(chip("Windows file system: slower on Linux", "warning"));
    return el("tr", {},
      el("td", { "data-label": "Drive" }, el("strong", { text: disk.model || disk.name }), el("span", { class: "small muted", text: ` ${p.name}` })),
      el("td", { "data-label": "Size", class: "numeric", text: p.size ? formatBytes(p.size) : "" }),
      el("td", { "data-label": "File system", text: p.fs || "None" }),
      el("td", { "data-label": "Mounted at" }, p.mounted.length ? el("code", { text: p.mounted.join(", ") }) : "Nowhere"),
      el("td", { "data-label": "Notes" }, ...notes));
  }));
  $("#devices").replaceChildren(el("div", { class: "table-wrap", "data-stack": true }, el("table", { class: "table" },
    el("caption", { class: "visually-hidden", text: "Drives and partitions" }),
    el("thead", {}, el("tr", {}, ["Drive", "Size", "File system", "Mounted at", "Notes"].map((h) => el("th", { scope: "col", text: h })))),
    el("tbody", {}, rows))));
}

startPage().then((session) => {
  $("#usage-run").addEventListener("click", async () => {
    try { renderUsage(await api("/api/usage", { method: "POST" })); announce("Working out what is using the space."); }
    catch (e) { toast(e.message); }
  });
  repo = session?.repo || "";
  const refresh = $("#refresh");
  refresh.replaceChildren(icon("refresh-cw"), el("span", { text: "Check again" }));
  refresh.addEventListener("click", async () => { await load(); announce("Checked again."); });
  load().then(loadUsage);
  loadDevices();
});
