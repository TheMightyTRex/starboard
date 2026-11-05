// System, Storage, Pool (DASH-87): the drives in the pool, the backup drives and the other drives, from the pool
// helper; and three jobs done in steps: Add a drive, Balance the files and Take out of the pool. Every job is
// checked first (a dry run on the server), and nothing changes until the password is typed again; erasing a drive
// also needs the end of its serial number. Starboard only asks: the helper, as root, does the work.

let state = null;
let flow = null;   // the job in progress: { kind, step, steps, ... }
let watching = 0;  // timer while a job runs

const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
const ROLE = { pool: "In the pool", parity: "Parity drive", copy: "Copy drive" };
const nameOf = (d) => `${d.model || d.name} ${formatBytes(d.size)}`;
const serialOf = (d) => (d.ends ? `serial ends ${d.ends}` : "no serial number");

function helpLink(text, page) {
  return el("a", { class: "help-link", href: `https://github.com/TheMightyTRex/starboard/blob/main/docs/help/${page}`, target: "_blank", rel: "noopener noreferrer" },
    icon("circle-help"), el("span", { text }), el("span", { class: "visually-hidden", text: " (opens in a new tab)" }));
}

function notice(tone, title, text, extra = []) {
  return el("div", { class: "notice", "data-tone": tone, role: tone === "warning" ? "note" : "status" },
    icon(tone === "warning" ? "triangle-alert" : "info"),
    el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: title }), el("p", { text }), extra));
}

// Widths are set through the style object: the page's security rules refuse style attributes.
function widthOf(node, pct) {
  node.style.width = `${pct}%`;
  return node;
}

function sized(node, styles) {
  Object.assign(node.style, styles);
  return node;
}

function meter(used, size) {
  const pct = size ? Math.round((used / size) * 100) : 0;
  const tone = pct >= 90 ? "danger" : pct >= 80 ? "warning" : null;
  return el("div", { class: "meter" },
    el("div", { class: "meter__label" }, el("span", { text: `${formatBytes(used)} of ${formatBytes(size)} used` }), el("span", { class: "numeric", text: `${pct}%` })),
    el("div", { class: "progress", "data-tone": tone, role: "img", "aria-label": `${pct}% used` }, widthOf(el("span"), pct)));
}

// Waiting for the helper ---------------------------------------------------------------------------------

async function ask(body) {
  const { request } = await api("/api/pool/ask", { method: "POST", body });
  return waitFor(request);
}

async function waitFor(request) {
  for (let i = 0; i < 90; i++) {
    const a = await api(`/api/pool/answer?id=${request}`);
    if (!a.waiting) {
      if (!a.ok) throw new Error(a.error);
      return a.result;
    }
    await new Promise((r) => setTimeout(r, i < 10 ? 500 : 1500));
  }
  throw new Error("The pool helper did not answer within two minutes. Check that it is installed (help: Add a drive to the pool)");
}

// Overview -----------------------------------------------------------------------------------------------

function poolRows(drives) {
  if (!drives.length) return el("p", { class: "muted", text: "No drives in the pool yet. Add a drive to make one." });
  return el("div", { class: "table-wrap", "data-stack": true }, el("table", { class: "table" },
    el("thead", {}, el("tr", {}, ["Drive", "Space", "State", ""].map((h, n) => el("th", { scope: "col" }, n === 3 ? el("span", { class: "visually-hidden", text: "Actions" }) : h)))),
    el("tbody", {}, drives.map((d) => {
      const pct = d.fs_size ? d.used / d.fs_size : 0;
      const st = d.fs_size == null ? chip("Not mounted", "danger") : pct >= 0.9 ? chip("Full", "danger") : pct >= 0.8 ? chip("Nearly full", "warning") : chip("Mounted", "success");
      return el("tr", {},
        el("td", { "data-label": "Drive" }, el("strong", { text: d.label }), el("br"), el("span", { class: "small muted", text: `${nameOf(d)} · ${serialOf(d)} · ${d.mount}` })),
        el("td", { "data-label": "Space" }, d.fs_size ? meter(d.used, d.fs_size) : "Not known"),
        el("td", { "data-label": "State" }, st),
        el("td", { "data-label": "Actions" }, el("button", { type: "button", class: "btn btn--compact", text: "Take out of the pool", onclick: () => startRemove(d) })));
    }))));
}

function backupRow(d) {
  const night = state.nightly?.results?.find((r) => r.what === (d.use === "parity" ? "parity" : d.label));
  const when = state.nightly?.at ? formatDate(state.nightly.at * 1000, true) : null;
  const result = !night ? chip("Not checked yet", "muted") : night.state === "done" ? chip("Up to date", "success", "shield-check")
    : night.state === "skipped" ? chip("Check skipped", "warning") : chip("Check failed", "danger");
  const how = d.use === "parity" ? "Parity with SnapRAID" : "Copy with rsync";
  return el("li", { class: "row row--no-lead" },
    el("div", {}, el("p", { class: "row__title" }, `${d.label} `, el("span", { class: "small muted", text: `${nameOf(d)} · ${serialOf(d)}` })),
      el("p", { class: "row__meta", text: `${how} · checked every night at ${state.check_at}${when ? ` · last ${when}` : ""}${night?.say ? ` · ${night.say}` : ""}` })),
    el("div", { class: "row__side" }, result, el("button", { type: "button", class: "btn btn--compact", text: "Stop using", onclick: () => startRemove(d) })));
}

function spareRow(d) {
  const what = d.blocked || (d.files ? `Has files: ${d.parts.filter((p) => p.fs).map((p) => `${p.fs}${p.mounted.length ? `, mounted at ${p.mounted[0]}` : ""}`).join("; ")}` : "Empty");
  return el("li", { class: "row row--no-lead" },
    el("div", {}, el("p", { class: "row__title" }, `${nameOf(d)} `, el("span", { class: "small muted", text: `${serialOf(d)} · ${d.path}` })),
      el("p", { class: "row__meta", text: what })),
    el("div", { class: "row__side" }, d.use === "free"
      ? el("button", { type: "button", class: "btn btn--compact", text: "Use this drive", onclick: () => startAdd(d) })
      : chip(d.use === "system" ? "System drive" : "Not offered", "muted", "lock")));
}

function jobView(job) {
  if (!job) return null;
  const words = { running: ["Running", "info", "hourglass"], done: ["Finished", "success"], failed: ["Failed", "danger"], stopped: ["Stopped", "warning"] }[job.state] || ["", "muted"];
  const what = { add: "Add a drive", remove: "Take out of the pool", balance: "Balance the files" }[job.action] || "Change";
  const parts = [el("p", {}, chip(words[0], words[1], words[2]), ` ${what}${job.of ? `: ${job.moved} of ${plural(job.of, "folder", "folders")} moved` : ""}${job.paused ? ", paused for download hours" : ""}`)];
  if (job.current) parts.push(el("p", { class: "small muted", text: `Now moving ${job.current}` }));
  if (job.of) {
    const pct = Math.round((job.moved / job.of) * 100);
    parts.push(el("div", { class: "progress", role: "img", "aria-label": `${pct}% done` }, widthOf(el("span"), pct)));
  }
  parts.push(el("ul", { class: "rows", "aria-label": "Steps done" }, job.steps.map((s) => el("li", { class: "row row--no-lead" },
    el("p", {}, chip({ done: "Done", failed: "Failed", skipped: "Stopped" }[s.state] || s.state, { done: "success", failed: "danger", skipped: "warning" }[s.state] || "muted"), ` ${s.say}`)))));
  if (job.state === "running") parts.push(el("div", { class: "actions" }, el("button", { type: "button", class: "btn", text: "Stop after this folder", onclick: stopJob })));
  return parts;
}

async function stopJob() {
  try {
    await api("/api/pool/stop", { method: "POST" });
    toast("Stopping after the folder being moved now");
  } catch (e) { toast(e.message, { tone: "info" }); }
}

function render() {
  const drives = state.drives || [];
  const inPool = drives.filter((d) => d.use === "pool");
  const backups = drives.filter((d) => d.use === "parity" || d.use === "copy");
  const others = drives.filter((d) => !["pool", "parity", "copy"].includes(d.use));
  const free = state.space ? state.space.size - state.space.used : inPool.reduce((n, d) => n + (d.free || 0), 0);
  const size = inPool.reduce((n, d) => n + (d.fs_size || d.size), 0);
  $("#pool-summary").textContent = inPool.length
    ? `${plural(inPool.length, "drive makes", "drives make")} one folder, ${state.pool}: ${formatBytes(size)}, ${formatBytes(free)} free. ${plural(backups.length, "backup drive", "backup drives")}.`
    : "No pool yet. A pool joins drives into one folder for your media.";
  $("#pool-actions").hidden = !!state.handmade?.mount;
  $("#balance").hidden = inPool.length < 2;
  $("#pool-stats").replaceChildren(
    el("div", { class: "stat", "data-tone": inPool.length ? "success" : null }, el("span", { class: "stat__value", text: String(inPool.length) }), el("span", { class: "stat__label", text: "Drives in the pool" })),
    el("div", { class: "stat" }, el("span", { class: "stat__value", text: formatBytes(free) }), el("span", { class: "stat__label", text: "Free" })),
    el("div", { class: "stat", "data-tone": backups.length ? "success" : "warning" }, el("span", { class: "stat__value", text: String(backups.length) }),
      el("span", { class: "stat__label", text: backups.length ? "Backup drives" : "No backup drive" })));
  $("#in-pool-panel").hidden = !!state.handmade?.mount;
  $("#in-pool").replaceChildren(poolRows(inPool));
  $("#backup-panel").hidden = !backups.length;
  $("#backups").replaceChildren(...backups.map(backupRow));
  $("#spare-panel").hidden = !others.length;
  $("#spare").replaceChildren(...others.map(spareRow));
  const job = state.job;
  $("#job-panel").hidden = !job;
  // A change still running goes first, under the tiles; a finished one goes last.
  if (job?.state === "running") $("#pool-stats").after($("#job-panel"));
  else $("#overview").append($("#job-panel"));
  if (job) {
    $("#job").replaceChildren(...jobView(job));
    $("#job-when").textContent = formatDate((job.finished || job.started) * 1000, true);
  }
  clearTimeout(watching);
  if (job?.state === "running") watching = setTimeout(load, 3000);
}

async function load() {
  try {
    state = await api("/api/pool");
    const n = $("#pool-notice");
    if (!state.set_up) {
      $("#pool-summary").textContent = "The pool helper is not set up.";
      $("#overview").hidden = true;
      n.replaceChildren(notice("info", "Set up the pool helper first",
        state.why === "no answer" ? "Starboard has a folder for the pool helper, but the helper has not answered yet. Check that it is installed."
          : "The pool helper makes the pool. It runs on the server with the right to change drives, which Starboard itself never has. Run ./install.sh again and say yes to Drive pools.",
        [el("p", {}, helpLink("Add a drive to the pool", "topics/add-a-drive-to-the-pool.md"))]));
      return;
    }
    $("#overview").hidden = !!flow;
    n.replaceChildren(...(state.handmade?.mount ? [notice("info", "This pool was made outside Starboard",
      `Starboard found a pool at ${state.handmade.mount} that it did not make, so it only shows it and changes nothing.`)] : []));
    if (!flow) render();
  } catch (e) {
    $("#pool-summary").textContent = `Could not read the pool: ${e.message}`;
  }
}

// Steps --------------------------------------------------------------------------------------------------

const FLOWS = {
  add: { title: "Add a drive", steps: ["Choose a drive", "What it is for", "Check", "Confirm", "Done"] },
  balance: { title: "Balance the files", steps: ["How to balance", "Check", "Confirm", "Done"] },
  remove: { title: "Take out of the pool", steps: ["Check", "Confirm", "Done"] },
};

function show(step) {
  flow.step = step;
  const f = FLOWS[flow.kind];
  const total = f.steps.length;
  $("#overview").hidden = true;
  $("#pool-actions").hidden = true;
  $("#wizard").hidden = false;
  $("#pool-title").textContent = flow.kind === "remove" ? `Take out ${flow.drive.label}` : f.title;
  $("#pool-summary").textContent = "";
  $("#wizard-where").textContent = `${f.title} · step ${step + 1} of ${total} · ${f.steps[step]}`;
  $("#wizard-left").textContent = step + 1 === total ? "Last step" : `${total - step - 1} to go`;
  const bar = $("#wizard-bar");
  bar.setAttribute("aria-valuemax", total);
  bar.setAttribute("aria-valuenow", step + 1);
  bar.setAttribute("aria-valuetext", `Step ${step + 1} of ${total}: ${f.steps[step]}`);
  bar.firstElementChild.style.width = `${Math.round(((step + 1) / total) * 100)}%`;
  $("#wizard-steps").replaceChildren(...f.steps.map((s, n) => n < step
    ? el("li", { "data-done": true }, s, el("span", { class: "visually-hidden", text: ", done" }))
    : n === step ? el("li", { "aria-current": "step" }, s, el("span", { class: "visually-hidden", text: ", current step" })) : el("li", { text: s })));
  const [body, foot] = VIEWS[flow.kind][step]();
  $("#wizard-body").replaceChildren(...body.flat().filter(Boolean));
  $("#wizard-foot").replaceChildren(...foot);
  $("#wizard-body h2")?.focus();
}

function close() {
  flow = null;
  $("#wizard").hidden = true;
  $("#pool-title").textContent = "Pool";
  load();
  $("#pool-title").focus?.();
}

const btn = (text, onclick, cls = "btn") => el("button", { type: "button", class: cls, text, onclick });
const heading = (text) => el("h2", { tabindex: "-1", text });
const back = () => btn("Back", () => show(flow.step - 1));
const cancel = () => btn("Cancel", close, "btn btn--quiet");

function optionCards(legend, name, items, chosen, onPick) {
  return el("fieldset", { class: "option-cards" }, el("legend", { text: legend }),
    items.map((it) => el("label", { class: "option-card" },
      el("input", { type: "radio", name, value: it.value, checked: it.value === chosen, disabled: it.disabled, onchange: () => onPick(it.value) }),
      el("strong", { text: it.title }), el("small", { text: it.text }))));
}

function checkView(plan) {
  const steps = el("ol", { class: "changes" }, plan.steps.map((s) => el("li", {}, s.danger ? chip("Erases the drive", "danger", "triangle-alert") : null, ` ${s.say}`)));
  const commands = plan.steps.flatMap((s) => s.commands || []);
  const moves = plan.moves || [];
  return [
    notice("info", "Dry run: nothing has changed yet", `The pool helper checked this on the server at ${new Date(plan.made * 1000).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}. These are the changes it will make, in order. The check is good for 15 minutes.`),
    steps,
    plan.drives ? balanceTable(plan.drives) : null,
    commands.length ? el("details", { class: "disclosure" }, el("summary", { text: "The exact commands" }), el("div", { class: "disclosure__body" }, el("pre", { class: "code-block", text: commands.join("\n") }))) : null,
    moves.length ? el("details", { class: "disclosure" }, el("summary", { text: `The ${plural(moves.length, "folder", "folders")} it moves` }),
      el("div", { class: "disclosure__body" }, el("pre", { class: "code-block", text: moves.slice(0, 200).map((m) => `${m.from} to ${m.to}: ${m.path} (${formatBytes(m.bytes)})`).join("\n") + (moves.length > 200 ? `\nand ${moves.length - 200} more` : "") }))) : null,
  ];
}

function balanceTable(drives) {
  return el("div", { class: "table-wrap", "data-stack": true }, el("table", { class: "table" },
    el("caption", { class: "visually-hidden", text: "Each drive before and after" }),
    el("thead", {}, el("tr", {}, ["Drive", "Now", "After"].map((h) => el("th", { scope: "col", text: h })))),
    el("tbody", {}, drives.map((d) => el("tr", {}, el("td", { "data-label": "Drive", text: `${d.label}, ${formatBytes(d.size)}` }),
      el("td", { "data-label": "Now" }, meter(d.before, d.size)), el("td", { "data-label": "After" }, meter(d.after, d.size)))))));
}

async function runCheck(body) {
  $("#wizard-foot").replaceChildren(el("p", { class: "muted", role: "status", text: "Checking on the server" }));
  try {
    flow.plan = await ask(body);
    show(flow.step + 1);
  } catch (e) {
    $("#wizard-foot").replaceChildren(back(), cancel());
    problem(e.message, $("#wizard-body"));
  }
}

function confirmView() {
  const plan = flow.plan;
  const drives = state.drives.filter((d) => plan.erases.includes(d.by_id));
  const fields = drives.map((d, n) => el("div", { class: "field" },
    el("label", { for: `serial-${n}` }, `Type the last 4 characters of its serial number, `, el("strong", { text: d.ends }), ", to confirm"),
    el("span", { class: "hint", id: `serial-hint-${n}`, text: "They are on the drive's label too. This makes sure you erase the drive you mean." }),
    sized(el("input", { class: "input", id: `serial-${n}`, "data-drive": d.by_id, autocomplete: "off", spellcheck: "false", "aria-describedby": `serial-hint-${n}` }), { maxWidth: "12ch" })));
  const body = [
    heading(drives.length ? `Erase ${drives.map(nameOf).join(" and ")}?` : "Make these changes?"),
    drives.length ? el("p", { text: "Everything on it is erased and cannot be got back. The other drives are not touched." })
      : el("p", { text: `${plan.steps.length} changes, as checked. You can stop a balance or a take-out between two folders.` }),
    ...fields,
    el("div", { class: "field" }, el("label", { for: "pool-password", text: "Your Starboard password" }),
      el("span", { class: "hint", id: "pool-password-hint", text: "Asked again for every change to the drives." }),
      sized(el("input", { class: "input", id: "pool-password", type: "password", autocomplete: "current-password", "aria-describedby": "pool-password-hint" }), { maxWidth: "28ch" })),
  ];
  const go = async (e) => {
    const confirm = Object.fromEntries($$("[data-drive]").map((i) => [i.dataset.drive, i.value.trim()]));
    const password = $("#pool-password").value;
    if (!password) return inlineError($("#pool-password"), "Type your password");
    const bad = drives.find((d, n) => $(`#serial-${n}`).value.replace(/[^a-z0-9]/gi, "").toUpperCase() !== d.ends);
    if (bad) return inlineError($(`#serial-${drives.indexOf(bad)}`), `Type ${bad.ends}, the last 4 characters of the serial number`);
    e.target.disabled = true;
    try {
      const { request } = await api("/api/pool/apply", { method: "POST", body: { plan: plan.id, password, confirm } });
      await waitFor(request);
      show(flow.step + 1);
    } catch (err) {
      e.target.disabled = false;
      if (err.status === 401 || err.status === 429) inlineError($("#pool-password"), err.message);
      else problem(err.message, $("#wizard-body"));
    }
  };
  const label = drives.length ? (flow.kind === "add" ? `Erase and ${flow.role === "pool" ? "add to the pool" : "use as a backup drive"}` : "Erase")
    : { add: "Add the drive", balance: "Start balancing", remove: "Take it out" }[flow.kind];
  return [body, [btn(label, go, drives.length ? "btn btn--primary btn--danger" : "btn btn--primary"), back(), cancel()]];
}

function doneView() {
  const body = [heading("Working on it"), el("div", { id: "done-job" }, el("p", { class: "muted", text: "Starting" }))];
  const follow = async () => {
    try {
      state = await api("/api/pool");
      const job = state.job;
      if (!job || job.id !== flow.plan.id) return setTimeout(follow, 1500);
      $("#done-job").replaceChildren(...jobView(job));
      const h = $("#wizard-body h2");
      if (job.state === "running") return setTimeout(follow, 2500);
      h.textContent = job.state === "done" ? "Finished" : job.state === "stopped" ? "Stopped" : "It did not finish";
      announce(h.textContent);
      const pool = state.drives.filter((d) => d.use === "pool");
      const fills = pool.filter((d) => d.fs_size).map((d) => d.used / d.fs_size);
      if (flow.kind === "add" && fills.length > 1 && Math.max(...fills) - Math.min(...fills) > 0.2) {
        $("#done-job").append(notice("info", "The drives are uneven", "New files go to the emptiest drive, so this evens out over time. To even it out now, balance the files."));
        $("#wizard-foot").prepend(btn("Balance the files", startBalance, "btn btn--primary"));
      }
    } catch { setTimeout(follow, 3000); }
  };
  setTimeout(follow, 500);
  return [body, [btn("Back to Pool", close, "btn")]];
}

const VIEWS = {
  add: [
    () => {
      const free = state.drives.filter((d) => d.use === "free");
      if (!free.length) return [[heading("Choose a drive"), notice("info", "No drive to add", "Every drive is in the pool, a backup drive, the system drive or in use for something else. Plug in a new drive, then look again.")], [cancel()]];
      flow.drive = flow.drive || free[0];
      return [[heading("Choose a drive"),
        el("p", { class: "muted", text: "These drives are not in the pool, not a backup drive and not the system drive. Check the end of the serial number against the label on the drive." }),
        optionCards("Drive", "drive", free.map((d) => ({ value: d.by_id, title: `${nameOf(d)}, ${serialOf(d)}`,
          text: d.files ? `Has files: ${d.parts.filter((p) => p.fs).map((p) => `${formatBytes(p.size)} on ${p.fs}${p.mounted.length ? `, mounted at ${p.mounted[0]}` : ""}`).join("; ")}. ${d.path}` : `Empty. ${d.path}` })),
        flow.drive.by_id, (v) => { flow.drive = free.find((d) => d.by_id === v); }),
        el("p", { class: "help-links" }, helpLink("My drive is not listed", "topics/add-a-drive-to-the-pool.md#if-it-does-not-work"))],
      [btn("Continue to What it is for", () => show(1), "btn btn--primary"), cancel()]];
    },
    () => {
      const d = flow.drive;
      const hasFiles = !!d.files;
      const biggest = Math.max(0, ...state.drives.filter((x) => x.use === "pool").map((x) => x.size));
      flow.role = flow.role || "pool";
      if (flow.erase === undefined) flow.erase = !hasFiles;
      const roleCards = optionCards("Use it", "role", [
        { value: "pool", title: "Add it to the pool (recommended)", text: `Its space joins ${state.pool}: ${formatBytes(d.size)} more for films, series and books.` },
        { value: "parity", title: "Parity drive (recommended backup)", text: d.size >= biggest
          ? "One drive protects every drive in the pool: if one fails, SnapRAID rebuilds its files. Checked every night. It must be at least as big as the biggest pool drive: it is."
          : `Not offered: a parity drive must be at least as big as the biggest pool drive (${formatBytes(biggest)}).`, disabled: d.size < biggest || !state.drives.some((x) => x.use === "pool") },
        { value: "copy", title: "Copy drive", text: "A plain copy of the folders you choose, every night. It needs as much space as those folders. Files you delete in the pool move to a dated holding folder on it, never erased." },
      ], flow.role, (v) => { flow.role = v; if (v === "parity") flow.erase = true; show(1); });
      const keepCards = optionCards("What is on it now", "keep", [
        { value: "keep", title: "Keep its files", text: hasFiles ? "Its files appear in the pool as they are." : "Not offered: the drive has no files to keep.", disabled: !hasFiles || flow.role === "parity" },
        { value: "erase", title: "Erase it and prepare it (ext4)", text: "Everything on it is erased. ext4 copes best when the power goes off unexpectedly. You confirm by typing the end of its serial number." },
      ], flow.erase ? "erase" : "keep", (v) => { flow.erase = v === "erase"; });
      const folders = flow.role === "copy" ? el("div", { class: "field" },
        el("label", { for: "copy-folders", text: "Folders in the pool to copy, with commas between them" }),
        el("span", { class: "hint", id: "copy-folders-hint", text: "For example: media/music, photos. Leave it as media to copy all your media." }),
        el("input", { class: "input", id: "copy-folders", value: (flow.folders || ["media"]).join(", "), "aria-describedby": "copy-folders-hint" })) : null;
      const warn = flow.role !== "pool" ? notice("warning", "Not a full backup on its own", "A backup drive is in the same computer, so a fire, theft or power surge can take it too. Keep a third copy of what matters somewhere else (the 3-2-1 rule).") : null;
      return [[heading(`What is ${nameOf(d)} (${serialOf(d)}) for?`), roleCards, keepCards, folders, warn,
        el("p", { class: "help-links" }, helpLink("Pool, parity or copy: which do I need?", "topics/use-a-drive-as-a-backup-drive.md"))],
      [btn("Continue to Check", () => {
        if (folders) flow.folders = $("#copy-folders").value.split(",").map((s) => s.trim()).filter(Boolean);
        runCheck({ kind: "add", drive: d.by_id, as: flow.role, erase: flow.erase, folders: flow.folders || [] });
      }, "btn btn--primary"), back(), cancel()]];
    },
    () => [[heading("Check before anything changes"), ...checkView(flow.plan)],
      [btn("Continue to Confirm", () => show(3), flow.plan.erases.length ? "btn btn--primary btn--danger" : "btn btn--primary"), back(), cancel()]],
    confirmView,
    doneView,
  ],
  balance: [
    () => {
      const hasTool = state.tools?.["mergerfs.balance"];
      flow.engine = flow.engine || "starboard";
      if (flow.pause === undefined) flow.pause = true;
      return [[heading("How to balance"),
        el("p", { text: "Balancing moves whole folders from fuller drives to emptier ones, under the pool. The pool shows every file in the same place all the time, so the apps notice nothing." }),
        el("figure", {}, sized(el("img", { src: "/images/balance.svg", alt: "Before balancing, disk 1 is 85% full and disk 4 is empty. After, folder B has moved to disk 4 and folder C to disk 3, so each disk is between 22% and 48% full, and every folder is still whole on one drive.", width: 640, height: 580 }), { maxWidth: "100%", height: "auto" })),
        optionCards("Balancer", "engine", [
          { value: "starboard", title: "Starboard's balancer (recommended)", text: "Moves whole series, film and book folders, so a failed drive takes whole series, not a few episodes of each. Shows each drive before and after first. Nothing to install." },
          { value: "mergerfs.balance", title: "mergerfs.balance", text: hasTool ? "Moves single files until the drives are even. A series can end up spread over several drives." : "Not installed. It is an extra download from the mergerfs-tools project; the help says how.", disabled: !hasTool },
        ], flow.engine, (v) => { flow.engine = v; }),
        el("label", { class: "check" }, el("input", { type: "checkbox", id: "pause", checked: flow.pause, onchange: (e) => { flow.pause = e.target.checked; } }),
          el("span", { class: "check__text", text: "Pause during download hours (Settings, General)" })),
        el("p", { class: "small muted", text: "It runs at low priority, so playing films is not slowed. Folders changed in the last hour stay where they are." }),
        el("p", { class: "help-links" }, helpLink("How balancing works, and what happens without it", "topics/balance-the-files.md"))],
      [btn("Continue to Check", () => runCheck({ kind: "balance", engine: flow.engine, pause: flow.pause }), "btn btn--primary"), cancel()]];
    },
    () => [[heading("Check before anything moves"), ...checkView(flow.plan)],
      [btn("Continue to Confirm", () => show(2), "btn btn--primary"), back(), cancel()]],
    confirmView,
    doneView,
  ],
  remove: [
    () => [[heading(`Take ${flow.drive.label} out`), el("p", { class: "muted", role: "status", text: "Checking on the server" })], [cancel()]],
    confirmView,
    doneView,
  ],
};

function startAdd(drive) {
  flow = { kind: "add", drive: drive || null };
  show(0);
}

function startBalance() {
  flow = { kind: "balance" };
  show(0);
}

async function startRemove(drive) {
  flow = { kind: "remove", drive };
  show(0);
  try {
    flow.plan = await ask({ kind: "remove", drive: drive.by_id });
    $("#wizard-body").replaceChildren(heading("Check before anything moves"), ...checkView(flow.plan).filter(Boolean));
    $("#wizard-foot").replaceChildren(btn("Continue to Confirm", () => show(1), "btn btn--primary"), cancel());
    $("#wizard-body h2").focus();
  } catch (e) {
    $("#wizard-body").replaceChildren(heading(`Take ${drive.label} out`), notice("warning", "It cannot be taken out now", e.message));
  }
}

startPage().then(() => {
  $("#add-drive").replaceChildren(icon("plus"), el("span", { text: "Add a drive" }));
  $("#add-drive").addEventListener("click", () => startAdd());
  $("#balance").replaceChildren(icon("arrow-up-down"), el("span", { text: "Balance the files" }));
  $("#balance").addEventListener("click", startBalance);
  $("#pool-title").setAttribute("tabindex", "-1");
  load();
});
