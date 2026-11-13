// Storage: free space in each folder Starboard has been given (STARBOARD_DISKS). One list, fullest first;
// each row opens a slide-out with the folder's details. The set-up hint shows only when nothing is set up.

let repo = "";
let disks = [];
let members = new Set();
let poolsFound = {};
let usage = null;
let perf = {};

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
    return [headChip(word, tone),
      el("div", { class: "notice", "data-tone": "warning", role: "status" }, icon("triangle-alert"),
        el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: "Starboard cannot find this folder" }),
          el("p", { text: `Check the path for ${d.label} in STARBOARD_DISKS and that the folder is mounted into Starboard, then restart Starboard.` }))),
      repo ? guideLink("Open the set-up guide", "free-space-on-the-system-page") : null];
  }
  const pct = pctUsed(d);
  return [
    headChip(word, tone),
    el("div", { class: "meter" },
      el("div", { class: "meter__label" }, el("span", { class: "numeric", text: `${sizePair(d.used, d.total)} used (${pct}%)` })),
      bar(pct, tone)),
    pct >= 90 ? el("div", { class: "notice", "data-tone": tone, role: "status" }, icon("triangle-alert"),
      el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: `${formatBytes(d.free)} left` }),
        el("p", { text: "Free some space or add a disk before it fills. Downloads stop when there is no room." }))) : null,
    el("dl", { class: "facts" },
      el("dt", { text: "Folder" }), el("dd", {}, d.path ? el("code", { text: d.path }) : "Not reported"),
      el("dt", { text: "Filesystem" }), el("dd", {}, d.filesystem ? el("span", { class: "tag", text: d.filesystem }) : "Not reported"),
      d.source ? el("dt", { text: d.source.startsWith("/dev/") ? "Disk" : "Made from" }) : null,
      d.source ? el("dd", {}, d.source.startsWith("/dev/") ? el("a", { href: "/system-disks.html", text: d.source }) : el("code", { text: d.source })) : null,
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
    if (now) panel.setBody(folderBody(now));
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
    el("div", { class: "row__side" }, chip(word, tone), el("span", { class: "numeric", text: `${sizePair(d.used, d.total)} used (${pct}%) · ${formatBytes(d.free)} free` })),
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
    members = new Set(Object.values(sys.pools || {}).flat());
    poolsFound = sys.pools || {};
    // A pool's drives are inside the pool: count the pool once.
    const found = disks.filter((d) => !d.missing && !members.has(d.label));
    const missing = disks.filter((d) => d.missing).length;
    const total = found.reduce((t, d) => t + d.total, 0);
    const used = found.reduce((t, d) => t + d.used, 0);
    const full = disks.filter((d) => !d.missing && pctUsed(d) >= 90).length;
    stats.replaceChildren(...[
      stat(formatBytes(total), "Total space"),
      stat(formatBytes(used), `Used (${total ? Math.round((used / total) * 100) : 0}%)`),
      stat(String(full), members.size ? "Drives or folders over 90% full" : "Folders over 90% full", full ? ["warning", "Nearly full"] : null),
      missing ? stat(String(missing), missing === 1 ? "Folder not found" : "Folders not found", ["warning", "Not found"]) : null].filter(Boolean));
    const sorted = [...disks].filter((d) => !members.has(d.label)).sort((a, b) => (b.missing ? 101 : pctUsed(b)) - (a.missing ? 101 : pctUsed(a)));
    let list = $("ul.rows", box);
    if (!list) { list = el("ul", { class: "rows", "aria-label": "Folders, fullest first" }); box.replaceChildren(list); }
    renderKeyed(list, sorted, (d) => d.label, (d) => row(d));
    const parts = members.size ? [plural(disks.length - members.size, "folder", "folders"), plural(members.size, "drive in a pool", "drives in a pool")]
      : [plural(disks.length, "folder", "folders")];
    if (full) parts.push(`${full} nearly full`);
    if (missing) parts.push(`${missing} not found`);
    parts.push(`updated at ${timeNow()}`);
    $("#storage-summary").textContent = parts.join(" · ");
    renderCharts();
  } catch (e) {
    $("#storage-summary").textContent = `Could not load storage: ${e.message}`;
  }
}

// What is using the space: on demand; the server walks the folders in the background and keeps the answer.
let usageTimer = null;

function renderUsage(u) {
  usage = u;
  const off = u.every === "off";
  $("#usage-panel").hidden = !disks.length;
  const button = $("#usage-run");
  button.hidden = off;
  button.disabled = !!u.running;
  $("span", button).textContent = u.running ? "Sorting by type…" : u.finished ? "Sort by type again" : "Sort by type now";
  $("#usage-when").textContent = off ? "Off in Settings, Performance" : u.running ? "Reading the folders now" : u.finished ? `Worked out ${formatDate(u.finished * 1000, true)}` : "Not worked out yet";
  $("#usage-about").textContent = off
    ? "Working out what uses the space is inactive in Settings, Performance, so the charts show used and free space only."
    : `Starboard reads every folder to sort the space by type: ${USAGE_WORDS[u.every] || USAGE_WORDS.ask} A file shared by a download and the library counts once, for the library.`;
  clearTimeout(usageTimer);
  if (u.running) usageTimer = setTimeout(loadUsage, 5000);
  const plain = (u.folders || []).filter((f) => !["tv", "movies", "audiobooks", "music", "books"].some((k) => (f.types || {})[k] > 0));
  $("#usage").replaceChildren(...plain.map((f) => {
    const total = f.items.reduce((t, i) => t + i.bytes, 0) || 1;
    return el("section", { class: "sys-block", "aria-label": f.label },
      el("h3", { text: f.label }),
      el("ul", { class: "meter-list" }, f.items.slice(0, 12).map((i) => el("li", {},
        el("div", { class: "meter__label" }, el("span", { text: i.name }), el("span", { class: "numeric", text: formatBytes(i.bytes) })),
        bar(Math.max(1, Math.round((i.bytes / total) * 100)), "success")))));
  }));
  renderCharts();
}

const USAGE_WORDS = {
  ask: "only when you press Sort by type.",
  open: "when you open Storage, if the last answer is over a day old.",
  nightly: "every night at 3 am.",
  weekly: "once a week, at 3 am.",
};

async function runUsage() {
  try { renderUsage(await api("/api/usage", { method: "POST" })); announce("Working out what is using the space."); }
  catch (e) { problem(e.message); }
}

// The pool cards, the drives in each pool, space over time and the biggest folders.
let spaceDays = null;
function renderCharts() {
  const box = $("#storage-charts");
  if (!box) return;
  const hasMedia = (f) => ["tv", "movies", "audiobooks", "music", "books"].some((k) => (f.types || {})[k] > 0);
  const sorted = (usage?.folders || []).filter(hasMedia);
  const poolLabels = Object.keys(poolsFound);
  const main = [...new Set([...poolLabels, ...sorted.map((f) => f.label)])]
    .map((label) => disks.find((d) => d.label === label && !d.missing)).filter(Boolean);
  const off = usage?.every === "off";
  box.replaceChildren(...main.map((d) => {
    const f = sorted.find((x) => x.label === d.label);
    const when = f && usage.finished ? `Sorted by type ${formatDate(usage.finished * 1000, true)}` : off ? "Sorting by type is inactive" : "Not sorted by type yet";
    const action = off ? null : el("button", { type: "button", class: "btn", disabled: !!usage?.running, onclick: runUsage },
      icon("refresh-cw"), usage?.running ? "Sorting by type…" : f ? "Sort by type again" : "Sort by type now");
    return poolCard(d, f ? f.types : null, when, action);
  }));
  // Drives
  const drives = Object.values(poolsFound).flat().map((l) => disks.find((d) => d.label === l && !d.missing)).filter(Boolean);
  $("#drives-panel").hidden = !drives.length;
  if (drives.length) {
    $("#drives-note").textContent = `${drives.length} drives, fullest first`;
    $("#drives").replaceChildren(...drivesChart(drives, (label, opener) => openFolder(disks.find((d) => d.label === label), opener)));
  }
  // Biggest
  const biggest = sorted.flatMap((f) => f.biggest || []).sort((a, b) => b.bytes - a.bytes).slice(0, 10);
  $("#biggest-panel").hidden = !biggest.length;
  if (biggest.length) $("#biggest").replaceChildren(...biggestChart(biggest));
  renderGrowth(main[0]);
}

function renderGrowth(disk) {
  const panel = $("#growth-panel");
  if (!disk || !spaceDays || perf.space_log === false) { panel.hidden = true; return; }
  const readings = Object.keys(spaceDays).sort().map((date) => ({ date, v: spaceDays[date][disk.label] }))
    .filter((r) => r.v).map((r) => ({ date: r.date, used: r.v[0], total: r.v[1] }));
  panel.hidden = !readings.length;
  if (readings.length) $("#growth").replaceChildren(...growthChart(disk.label, readings, $("#growth").clientWidth));
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

// The growth chart is drawn at its real width (so its text stays at the token size): draw again when that changes.
let resizeTimer = null;
window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(renderCharts, 200); });

startPage().then(async (session) => {
  $("#usage-run").addEventListener("click", runUsage);
  repo = session?.repo || "";
  try { perf = (await api("/api/config")).performance || {}; } catch { perf = {}; }
  const refresh = $("#refresh");
  refresh.replaceChildren(icon("refresh-cw"), el("span", { text: "Check again" }));
  refresh.addEventListener("click", async () => { await load(); announce("Checked again."); });
  await load();
  await loadUsage();
  try { spaceDays = (await api("/api/space-history")).days; renderCharts(); } catch { /* no history yet */ }
  // When you open Storage: sort by type if the last answer is over a day old (Settings, Performance).
  if (usage && usage.every === "open" && !usage.running && (!usage.finished || Date.now() / 1000 - usage.finished > 86400)) runUsage();
  // Sizes update by themselves while the page is open and in view, or only with Check again.
  if (perf.storage_refresh) setInterval(() => { if (!document.hidden) load(); }, perf.storage_refresh * 1000);
  loadDevices();
});
