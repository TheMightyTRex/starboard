// Settings, General: names and categories, appearance, pages and lists, download hours, and logs and feedback.

// General -------------------------------------------------------------------

function countIn(group) { return config.services.filter((s) => s.group === group).length; }

function appsWord(n) { return `${n} ${n === 1 ? "app" : "apps"}`; }

// Categories are saved as a list of names, and each app keeps its category's name. Renaming or removing one
// moves the apps in it in the same save (move_apps).

function categoryRow(name, index, list) {
  const n = countIn(name);
  const items = [];
  if (index > 0) items.push({ label: "Move up", icon: "arrow-up", onSelect: () => later(() => moveCategory(index, -1)) });
  if (index < list.length - 1) items.push({ label: "Move down", icon: "arrow-down", onSelect: () => later(() => moveCategory(index, 1)) });
  if (list.length > 1) items.push({ label: "Remove", icon: "trash-2", danger: true, onSelect: () => later(() => removeCategory(name)) });
  return el("li", { class: "row" },
    el("span", { class: "app-icon", "aria-hidden": "true", text: String(index + 1) }),
    el("div", { class: "row__text" }, el("div", { class: "row__title", text: name }), el("div", { class: "row__meta", text: n ? appsWord(n) : "No apps yet" })),
    el("div", { class: "row__side" },
      el("button", { type: "button", class: "btn", onclick: () => renameCategory(name) }, icon("pencil"), "Rename", el("span", { class: "visually-hidden", text: ` ${name}` })),
      menuButton(`More actions for ${name}`, items)));
}

function renderCategories() {
  const groups = config.groups;
  redraw($("#category-list"), groups.map((g, i) => {
    const row = categoryRow(g, i, groups);
    row.dataset.key = g;
    return row;
  }));
  $("#category-add").disabled = groups.length >= 20;
  // Apps can sit in a category that is not in the list (from an older version or a restore). The Apps page
  // shows those after the listed ones; offer to add them so they can be renamed and ordered here.
  const loose = [...new Set(config.services.filter((s) => !s.background && s.group && !groups.includes(s.group)).map((s) => s.group))];
  const box = $("#category-loose");
  box.replaceChildren();
  if (loose.length) {
    const add = el("button", { type: "button", class: "btn" }, icon("plus"), loose.length === 1 ? "Add it to the list" : "Add them to the list");
    add.addEventListener("click", async () => {
      if (await saveGroups([...config.groups, ...loose].slice(0, 20), `Added ${loose.join(", ")}`)) $("#category-list .btn")?.focus();
    });
    box.append(notice("info", loose.length === 1 ? "1 more category is in use" : `${loose.length} more categories are in use`,
      `Some apps are in ${loose.join(", ")}, which ${loose.length === 1 ? "is" : "are"} not in this list. The Apps page shows ${loose.length === 1 ? "it" : "them"} after the categories here.`, add));
  }
}

async function saveGroups(groups, message, moveApps = null) {
  try {
    await saveGeneral(moveApps ? { groups, move_apps: moveApps } : { groups }, null);
    renderCategories();
    if (message) announce(message);
    return true;
  } catch (e) { problem(e.message); return false; }
}

async function moveCategory(index, by) {
  const groups = [...config.groups];
  [groups[index], groups[index + by]] = [groups[index + by], groups[index]];
  await saveGroups(groups, `${groups[index + by]} moved ${by < 0 ? "up" : "down"}, now ${index + by + 1} of ${groups.length}`);
}

async function renameCategory(name) {
  const input = el("input", { class: "input", maxlength: "40", required: true, value: name, autocomplete: "off" });
  const n = countIn(name);
  const ok = await confirmDialog({
    title: `Rename ${name}`,
    message: n ? `The ${appsWord(n)} in it move with it.` : "No apps are in it yet.",
    fields: [field("New name", input, { required: true })],
    confirm: "Rename category",
  });
  const to = input.value.trim();
  if (!ok || !to || to === name) return;
  if (config.groups.includes(to)) { problem(`There is already a category called ${to}`); return; }
  if (!(await saveGroups(config.groups.map((g) => (g === name ? to : g)), null, { from: name, to }))) return;
  toast(`Renamed ${name} to ${to}`);
  $(`#category-list [data-key="${CSS.escape(to)}"] .btn`)?.focus();
}

async function removeCategory(name) {
  const n = countIn(name);
  const others = config.groups.filter((g) => g !== name);
  const to = el("select", { class: "select" }, others.map((g) => el("option", { value: g, text: g })));
  const ok = await confirmDialog({
    title: `Remove the ${name} category?`,
    message: n ? `${appsWord(n)} ${n === 1 ? "is" : "are"} in ${name}. Choose where ${n === 1 ? "it goes" : "they go"}. The apps themselves are not changed.` : "No apps are in it. Nothing else changes.",
    fields: n ? [field("Move its apps to", to)] : [],
    confirm: "Remove category", danger: true,
  });
  if (!ok) return;
  const row = $(`#category-list [data-key="${CSS.escape(name)}"]`);
  const next = row?.nextElementSibling || row?.previousElementSibling;
  if (await saveGroups(others, null, n ? { from: name, to: to.value } : null)) {
    toast(n ? `Removed ${name}. Its apps are now in ${to.value}` : `Removed ${name}`);
    (next?.isConnected ? $(".btn", next) : $("#category-name"))?.focus();
  }
}

function startGeneral() {
  const holder = $("#general-sections");
  // Names (settings pattern 5): the server name and the dashboard name, one form with one Save at its foot.
  const siteName = el("input", { class: "input", name: "site_name", maxlength: "60", required: true, value: config.site_name });
  const serverName = el("input", { class: "input", name: "server_name", maxlength: String(config.server_name_max || 10),
    value: config.server_name || "", autocomplete: "off", spellcheck: "false" });
  const serverField = field("Server name", serverName, { hint: `Up to ${config.server_name_max || 10} characters, such as T-Rex. Shown at the start of the level 1 menu on every page. Leave it empty to show no name.`, short: true });
  const namesForm = el("form", { novalidate: true, class: "form-stack" }, serverField,
    field("Dashboard name", siteName, { required: true }),
    el("div", { class: "actions" }, el("button", { type: "submit", class: "btn", text: "Save" }), savedNote("names-saved")));
  // A count under the box, read with the hint but not announced on every key.
  const max = config.server_name_max || 10;
  const count = el("span", { class: "hint", id: `${serverName.id}-count` });
  const recount = () => { count.textContent = `${serverName.value.length} of ${max} characters`; };
  serverName.after(count);
  serverName.moreHints = [count.id];
  serverName.setAttribute("aria-describedby", `${serverName.fieldHint.id} ${count.id}`);
  serverName.addEventListener("input", recount);
  recount();
  namesForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    setError(siteName, "");
    setError(serverName, "");
    if (!siteName.value.trim()) { setError(siteName, "Enter a name for the dashboard"); siteName.focus(); return; }
    try {
      await saveGeneral({ site_name: siteName.value, server_name: serverName.value });
      showSaved("names-saved");
      document.title = document.title.replace(/ · [^·]*$/, ` · ${config.site_name}`);
      showServerName(config.server_name);
    } catch (err) { setError(serverName, err.message); serverName.focus(); }
  });

  // Categories
  const newName = el("input", { class: "input", id: "category-name", maxlength: "40", placeholder: "For example: Home", autocomplete: "off" });
  const addForm = el("form", { class: "add-row", novalidate: true }, field("New category", newName, { required: true }),
    el("button", { type: "submit", class: "btn", id: "category-add" }, icon("plus"), "Add category"));
  addForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    setError(newName, "");
    const value = newName.value.trim();
    if (!value) { setError(newName, "Enter a name for the category"); newName.focus(); return; }
    if (config.groups.includes(value)) { setError(newName, `There is already a category called ${value}`); newName.focus(); return; }
    if (await saveGroups([...config.groups, value], `Added ${value}`)) newName.value = "";
  });

  // App cards: switches that apply at once.
  const uxInput = el("input", { type: "checkbox", role: "switch", "aria-labelledby": "ux-notes-l", checked: config.ux_notes });
  uxInput.addEventListener("change", async () => {
    try {
      await saveGeneral({ ux_notes: uxInput.checked }, true);
      if (uxInput.checked) await startFeedback(); else stopFeedback();
      renderFeedback();
    } catch (err) { uxInput.checked = !uxInput.checked; problem(err.message); }
  });
  const uxSwitch = el("label", { class: "switch" }, uxInput);
  const cardSwitch = (key, labelId) => {
    const input = el("input", { type: "checkbox", role: "switch", "aria-labelledby": labelId, checked: config[key] });
    input.addEventListener("change", async () => {
      try { await saveGeneral({ [key]: input.checked }, true); }
      catch (err) { input.checked = !input.checked; problem(err.message); }
    });
    return el("label", { class: "switch" }, input);
  };

  // Default design
  // Default design: a choice, so it saves as soon as it changes (the design system's save rule).
  const designForm = el("form", {},
    el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Default design" }),
      el("div", { class: "option-cards option-cards--row" }, Object.entries(DESIGNS).map(([k, [label, help]]) => el("label", { class: "option-card" },
        el("input", { type: "radio", name: "design", value: k, checked: config.design === k }), el("strong", { text: label }), el("small", { text: help }), designPicture(k))))));
  designForm.addEventListener("change", async () => {
    const before = config.design;
    try { await saveGeneral({ design: designForm.design.value }, true); }
    catch (err) { designForm.design.value = before; problem(err.message); }
  });

  // Style (owner, 10 November 2026): the plug-in style this browser uses, and Reset style back to the standard colours.
  const styleSaid = el("p", { "aria-live": "polite" });
  const styleResetBtn = el("button", { type: "button", class: "btn" }, icon("rotate-ccw"), "Reset style");
  const styleChoose = el("button", { type: "button", class: "btn btn--quiet" }, "Choose a style");
  let styleNames = {};
  const styleShow = () => {
    const chosen = readPrefs().style;
    styleSaid.replaceChildren("This browser uses ", el("strong", { text: chosen ? (styleNames[chosen] || "a style from a plug-in that is now off") : `Starboard's own style, ${ownColoursLabel()} accent` }), ".");
    styleResetBtn.disabled = !chosen;
  };
  styleResetBtn.addEventListener("click", () => { resetStyle(); styleShow(); });
  styleChoose.addEventListener("click", () => $("[data-display-toggle]")?.click());
  document.addEventListener("stylechange", styleShow);
  addEventListener("storage", styleShow);  // changed in another tab
  if (wants(holder, "gn-style")) api("/api/styles").then((r) => { styleNames = Object.fromEntries(r.styles.map((x) => [x.value, `${x.name}, from ${x.plugin}`])); styleShow(); }).catch(styleShow);
  styleShow();
  const styleForm = wants(holder, "gn-style") ? el("div", { class: "stack-4" }, el("div", { class: "stack-2" }, styleSaid, el("div", { class: "actions" }, styleResetBtn, styleChoose)),
    ownColoursChoice("gn-own")) : null;

  // Coming up: selects that apply at once.
  const upcomingSelect = (key, labelId, options) => {
    const select = el("select", { class: "select", "aria-labelledby": labelId },
      options.map(([value, label]) => el("option", { value: String(value), text: label, selected: String(config[key]) === String(value) })));
    select.addEventListener("change", async () => {
      const before = config[key];
      try { await saveGeneral({ [key]: key === "upcoming_days" ? Number(select.value) : select.value }, true); }
      catch (err) { select.value = String(before); problem(err.message); }
    });
    return select;
  };
  const dayChoices = (config.upcoming_days_choices || [7, 14, 30, 60, 90]).map((n) => [n, n === 7 ? "1 week" : n === 14 ? "2 weeks" : `${n} days`]);

  holder.removeAttribute("aria-busy");
  holder.replaceChildren(...onlyParts(holder, [
    section("gn-name", "Names", "The server name shows at the start of the menu. The dashboard name shows in the browser tab and in alerts.", namesForm),
    el("div", { id: "categories" }, section("gn-cat", "Categories", "The headings apps sit under on the Apps page, in this order. Changes apply at once.",
      el("ul", { class: "rows", id: "category-list" }), el("div", { id: "category-loose" }), addForm)),
    section("gn-card", "App cards", "What each app card shows, for everyone. Changes apply at once.",
      el("ul", { class: "settings-rows" },
        settingRow("Home address", "In Health first and Tiles, the address is the link that opens the app. Copy it from the app's details.", cardSwitch("show_home_address", "card-home-l"), "card-home-l"),
        settingRow("Outside address", "With a copy button, when the app has one.", cardSwitch("show_outside_address", "card-out-l"), "card-out-l"))),
    el("div", { id: "coming-up" }, section("gn-up", "Coming up", "What the Coming up page shows. These apply at once.",
      el("ul", { class: "settings-rows" },
        settingRow("View", "List shows releases by day; Calendar shows them on a month. The switch on the page changes this too.",
          upcomingSelect("upcoming_view", "up-view-l", [["list", "List"], ["calendar", "Calendar"]]), "up-view-l"),
        settingRow("How far ahead", withCost("Releases from today to this far ahead, plus yesterday's.", "upcoming"),
          upcomingSelect("upcoming_days", "up-days-l", dayChoices), "up-days-l")))),
    wants(holder, "gn-dh") ? el("div", { id: "download-hours" }, downloadHoursSection("gn-dh")) : null,
    section("gn-guide", "Set-up guide", "Finds your apps and walks through what Starboard can do. Running it again changes nothing until you press Continue.",
      el("div", { class: "actions" }, el("a", { class: "btn", href: "/setup-guide.html" }, icon("play"), config.setup_guide_done ? "Run the set-up guide again" : "Run the set-up guide"),
        el("a", { class: "btn", href: "/install-apps.html" }, icon("download"), "Install apps"))),
    wants(holder, "gn-logs") ? el("div", { id: "logs" }, logsSection()) : null,
    // Appearance (owner, 13 November 2026: "Change the word Style to Appearance and add the accessibility options
    // there as well"): the own style and its colours, the default design and accessibility, together.
    styleForm && section("gn-style", "Style and colours", "A style from a plug-in is chosen in Display, for this browser only. Reset style goes back to Starboard's own style, in the colours chosen in this section, and keeps your other Display choices.", styleForm),
    section("gn-design", "Default design", "This design applies to everyone who has not chosen their own in Display.", designForm),
    wants(holder, "gn-access") ? section("gn-access", "Accessibility", "Theme, text size, motion, contrast, links and spacing for this browser, the same choices as in Display. They apply at once.", accessibilityForm()) : null,
    el("div", { id: "testing" }, section("gn-test", "Send feedback", "Report a problem or suggest something from any page. On unless you turn it off.",
      el("ul", { class: "settings-rows" },
        settingRow("Send feedback", "Feedback in the side menu, on every page, reports a problem, suggests something or checks a page for accessibility problems. Each report opens as an issue on Starboard's GitHub page, or is saved here. Turn it off to remove Feedback from the menu.",
          uxSwitch, "ux-notes-l")),
      el("div", { id: "feedback-list" }))),
    wants(holder, "gn-logdel") ? logsDangerSection() : null]));
  if ($("#category-list")) renderCategories();
  if (wants(holder, "gn-logs") || wants(holder, "gn-logdel")) loadLogLimits();
  renderFeedback();
  if (["#categories", "#coming-up", "#download-hours", "#logs", "#testing", "#delete-logs"].includes(location.hash)) $(location.hash)?.scrollIntoView();
}

// Reports saved with Save in Starboard (and notes from the older Note an issue button), newest first.
async function renderFeedback() {
  const box = $("#feedback-list");
  if (!box) return;
  if (!config.ux_notes) { box.replaceChildren(); return; }
  let notes;
  try { notes = (await api("/api/ux-notes")).notes; } catch (e) { box.replaceChildren(notice("danger", "Could not load the saved reports", e.message)); return; }
  if (!notes.length) { box.replaceChildren(el("p", { class: "muted", text: "No reports saved in Starboard yet." })); return; }
  const open = notes.filter((n) => n.status !== "fixed").length;
  const download = el("button", { type: "button", class: "btn" }, icon("download"), "Download all");
  download.addEventListener("click", () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(notes, null, 2)], { type: "application/json" }));
    const a = el("a", { href: url, download: `starboard-feedback-${new Date().toISOString().slice(0, 10)}.json` });
    document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  const setStatus = async (n, status) => {
    try { await api("/api/ux-notes/update", { method: "POST", body: { id: n.id, status } }); toast(status === "fixed" ? "Marked fixed" : "Marked open"); renderFeedback(); }
    catch (e) { problem(e.message); }
  };
  const remove = async (n) => {
    if (!(await confirmDialog({ title: "Remove this report?", message: n.title || n.what, confirm: "Remove report", danger: true }))) return;
    try { await api("/api/ux-notes/remove", { method: "POST", body: { id: n.id } }); toast("Report removed"); renderFeedback(); }
    catch (e) { problem(e.message); }
  };
  const row = (n) => {
    const fixed = n.status === "fixed";
    const title = n.title || String(n.what || "").split("\n")[0];
    const meta = [n.page, n.part, n.when && formatDate(n.when, true), fixed ? "Fixed" : "Open"].filter(Boolean).join(" · ");
    const body = n.markdown || n.what || "";
    const details = body && body !== title ? el("details", {}, el("summary", { text: "The full report" }), el("pre", { class: "code-block", text: body })) : null;
    const li = el("li", { class: "row" },
      el("div", { class: "row__text" }, el("div", { class: "row__title", text: title }), el("div", { class: "row__meta", text: meta }), details),
      el("div", { class: "row__side" },
        el("button", { type: "button", class: "btn", onclick: () => setStatus(n, fixed ? "open" : "fixed") }, icon(fixed ? "rotate-ccw" : "check"), fixed ? "Mark open" : "Mark fixed"),
        menuButton(`More actions for ${title}`, [{ label: "Remove", icon: "trash-2", danger: true, onSelect: () => later(() => remove(n)) }])));
    li.dataset.key = n.id;
    return li;
  };
  const list = el("ul", { class: "rows" });
  redraw(list, notes.slice().reverse().map(row));
  box.replaceChildren(
    el("h3", { text: `Saved in Starboard: ${notes.length} ${notes.length === 1 ? "report" : "reports"}, ${open} open` }),
    list, el("div", { class: "actions" }, download));
}

// Logs (DASH-451, owner, 16 November 2026: "Can we also have limits on the logs with a setting for it and a way to
// delete them all"): how long and how much, what they take now, detailed logging, and the apps' own limit from Docker.
// The figures come from /api/logs/limits once the page is drawn (loadLogLimits); nothing is asked again on a timer.
let logLimits = null;

const LOG_DAYS = [[7, "7 days"], [14, "14 days"], [30, "30 days"], [60, "60 days"], [90, "90 days"], [180, "180 days"], [365, "A year"]];

const LOG_SIZES = [[10, "10 MB"], [25, "25 MB"], [50, "50 MB"], [100, "100 MB"], [250, "250 MB"], [500, "500 MB"]];

function logsSection() {
  const saveLimit = async (key, value) => {
    await saveGeneral({ logs: { [key]: Number(value) } }, true);
    await loadLogLimits();
  };
  return section("gn-logs", "Logs", "What Starboard did and every problem it met, on System, Logs. Personal details (passwords, API keys, addresses, names) are removed before anything is written.",
    el("ul", { class: "settings-rows" },
      settingRow("Keep logs for", withCost("Older days are removed when a new day starts, and at once when you change this.", "logKeep"),
        logPick("lg-keep-l", LOG_DAYS, config.logs.keep_days, (v) => saveLimit("keep_days", v)), "lg-keep-l"),
      settingRow("No more than", withCost("All of Starboard's logs together. When they reach this, the oldest days are removed, whichever limit comes first.", "logSize"),
        logPick("lg-size-l", LOG_SIZES, config.logs.max_mb ?? 50, (v) => saveLimit("max_mb", v)), "lg-size-l"),
      settingRow("Detailed logging", withCost("For reporting a problem: adds every page request and every call to your apps, and the full detail of errors. Personal details are still removed.", "logDetail"),
        logPick("lg-detail-l", [["off", "Off"], ["day", "For 24 hours"], ["on", "Until I turn it off"]], config.logs.detail,
          (v) => saveGeneral({ logs: { detail: v } }, true)), "lg-detail-l")),
    el("div", { class: "stack-2" },
      el("h3", { text: "What the limits cover" }),
      el("p", { class: "small", text: "Starboard's own log, one file a day, with the lines from its jobs, updates and plug-ins. Also the API's audit log and the last Starboard update's log. Plug-ins keep no log files in Starboard." }),
      el("p", { class: "small", id: "logs-now", text: "Checking the logs…" })),
    el("div", { class: "stack-2" },
      el("h3", { text: "The apps' own logs" }),
      el("p", { class: "small", id: "logs-apps", text: "Asking Docker…" })),
    el("div", { class: "actions" }, el("a", { class: "btn", href: "/system-logs.html" }, icon("scroll-text"), "Open the logs")));
}

function logsNowText(s) {
  if (!s || !s.files) return "There are no logs yet.";
  return `Now: ${logBytes(s.bytes)}${s.days ? `, ${s.days} ${s.days === 1 ? "day" : "days"} since ${logDay(s.oldest)}` : ""}.`;
}

function logsAppsText(a) {
  if (!a || !a.available) return "Starboard cannot reach Docker, so it cannot say how long the apps keep their logs.";
  const each = a.max_size ? `${a.max_file} ${a.max_file === "1" ? "file" : "files"} of ${a.max_size.replace(/^(\d+)([kmg])$/i, (m, n, u) => `${n} ${u.toUpperCase()}B`)}` : "";
  const words = [];
  if (a.capped && each) words.push(`Docker keeps each app's log to ${each}${a.per_app ? ` (${formatBytes(a.per_app)} at most)` : ""}. Docker's settings set this (daemon.json on the server), which Starboard cannot change.`);
  else words.push("Docker does not limit the apps' logs here.");
  if (a.uncapped?.length) words.push(`${a.uncapped.length === 1 ? "1 app has" : `${a.uncapped.length} apps have`} no limit: ${a.uncapped.slice(0, 8).join(", ")}${a.uncapped.length > 8 ? " and more" : ""}.`);
  words.push("Apps and plug-ins Starboard installs get 3 files of 10 MB each in their own set-up. Delete all logs leaves the apps' logs alone.");
  return words.join(" ");
}

async function loadLogLimits() {
  try { logLimits = await api("/api/logs/limits"); }
  catch (e) { $("#logs-now")?.replaceChildren(`The logs could not be checked: ${e.message}`); return; }
  $("#logs-now")?.replaceChildren(logsNowText(logLimits.summary));
  $("#logs-apps")?.replaceChildren(logsAppsText(logLimits.apps));
  const size = $("#logs-delete-size");
  if (size) size.textContent = logsNowText(logLimits.summary);
}

// Settings pattern 9: Delete all logs, last on the page, with the danger dialog and the password, as Sign out
// everywhere is. The result is said in the section's live region, and focus stays on the button.
function logsDangerSection() {
  const status = el("p", { class: "small", id: "logs-delete-status", role: "status" });
  const button = el("button", { type: "button", class: "btn btn--danger", id: "logs-delete" }, icon("trash-2"), "Delete all logs");
  button.addEventListener("click", async () => {
    let r;
    try { r = await deleteAllLogs(logLimits?.summary); } catch (e) { problem(e.message, button); return; }
    if (!r) return;
    logLimits = { ...(logLimits || {}), summary: r.summary };
    $("#logs-now")?.replaceChildren(logsNowText(r.summary));
    $("#logs-delete-size").textContent = logsNowText(r.summary);
    status.textContent = "";
    status.textContent = deletedLogsText(r);
    button.focus();
  });
  return el("div", { id: "delete-logs" }, dangerSection("gn-logdel", "Delete all logs", "Removes Starboard's logs now, before the limits would. It asks for your password first.",
    el("p", { class: "small", id: "logs-delete-size", text: "Checking the logs…" }),
    el("div", { class: "actions" }, button), status));
}

function logPick(labelId, options, value, onChange) {
  const select = el("select", { class: "select", "aria-labelledby": labelId },
    options.map(([v, t]) => el("option", { value: String(v), text: t, selected: String(v) === String(value) })));
  select.addEventListener("change", async () => {
    try { await onChange(select.value, select.selectedOptions[0].text); } catch (e) { problem(e.message); }
  });
  return select;
}

// Long lists (DASH-277): long lists load more by themselves, or wait for Show more. Added after General's other parts.
function generalScrollSection() {
  if (!wants("#general-sections", "gn-scroll")) return;
  const input = el("input", { type: "checkbox", role: "switch", id: "infinite-scroll", checked: config.infinite_scroll !== false });
  input.addEventListener("change", () => saveGeneral({ infinite_scroll: input.checked }, true).catch((e) => problem(e.message)));
  const box = section("gn-scroll", "Long lists", "The Library, Wanted and History.",
    el("ul", { class: "settings-rows" }, el("li", { class: "setting" }, switchRow("Load more as you scroll",
      "Inactive: a Show more button at the end instead. With Reduce motion on, the button is always used.", input))));
  const sections = $("#general-sections");
  // General's parts are usually drawn by now (startGeneral runs first), so it goes in at once; else when they are.
  const place = () => { if (sections.childElementCount && !$("#gn-scroll-h")) { sections.append(box); return true; } return false; };
  if (!place()) { const wait = new MutationObserver(() => { if (place()) wait.disconnect(); }); wait.observe(sections, { childList: true }); }
}
