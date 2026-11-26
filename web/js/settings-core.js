// Settings, the part every settings page loads: the shared helpers (fields, rows, sections, topics, the
// Advanced switch, saving General) and the start, which runs each page's own part. Each page also loads its own part,
// settings-<part>.js, named in its script tags; a function used by more than one part belongs here.

let config = null;

// Small helpers ------------------------------------------------------------

// A field with its label, hint and an error tied to the control.
let fieldCount = 0;

function field(label, wrapper, { hint, span, short, required } = {}) {
  // A wrapper (a number with its unit) is shown; its input takes the label, hint and error.
  const control = wrapper.matches("input, select, textarea") ? wrapper : wrapper.querySelector("input, select, textarea") || wrapper;
  if (!control.id) control.id = `field-${++fieldCount}`;
  if (required) control.required = true;
  const hintNode = hint ? el("span", { class: "hint", id: `${control.id}-hint` }, hint) : null;
  const error = el("span", { class: "field-error", id: `${control.id}-error`, hidden: true });
  if (hintNode) control.setAttribute("aria-describedby", [hintNode.id, control.getAttribute("aria-describedby")].filter(Boolean).join(" "));
  control.fieldError = error;
  control.fieldHint = hintNode;
  return el("div", { class: short ? "field field--short" : "field", "data-span": span ? "all" : null },
    el("label", { for: control.id }, label, control.required ? requiredMark() : null), hintNode, wrapper, error);
}

function setError(control, message) {
  const error = control.fieldError;
  const ids = [control.fieldHint?.id, ...(control.moreHints || [])];
  if (message) {
    errorWords(error, message);
    error.hidden = false;
    control.setAttribute("aria-invalid", "true");
    ids.push(error.id);
  } else {
    error.hidden = true;
    error.replaceChildren();
    control.removeAttribute("aria-invalid");
  }
  const describedBy = ids.filter(Boolean).join(" ");
  if (describedBy) control.setAttribute("aria-describedby", describedBy); else control.removeAttribute("aria-describedby");
}

// The design system's error summary (20 November 2026), for a form where more than one field can be wrong: "There is
// a problem" at the top of the form, focused, with a link to each field, each field's own error under its label, and
// "Error: " at the start of the page title. errors: [[control, message]]; an empty list clears it. Starboard's own
// setError keeps each field's error node, so the summary only adds the list and the title.
function formErrors(form, errors) {
  const fields = [...form.querySelectorAll("input, select, textarea")].filter((c) => c.fieldError);
  fields.forEach((c) => setError(c, ""));
  SharedComponents.clearErrors(form);
  if (!errors.length) return;
  // showErrors finds each field's error node by its id (field() makes it), fills it with "Error: " for screen readers,
  // and adds it to aria-describedby after the hint.
  SharedComponents.showErrors(form, errors.map(([c, message]) => ({ field: c.id, message })));
  errors.forEach(([c]) => { c.fieldError.hidden = false; });
}

function switchRow(label, hint, input) {
  input.setAttribute("role", "switch");
  return el("label", { class: "switch" },
    el("span", { class: "check__text" }, el("strong", { text: label }), hint ? el("span", { class: "check__hint", text: hint }) : null), input);
}

// A settings row: label and hint on the left, the control on the right.
function settingRow(label, hint, control, labelId) {
  return el("li", { class: "setting" },
    el("div", { class: "setting__text" }, el("span", { class: "setting__label", id: labelId || null, text: label }), hint ? el("span", { class: "setting__hint" }, hint) : null),
    el("div", { class: "setting__control" }, control));
}


function section(id, title, description, ...content) {
  const chipNode = content.find((n) => n?.dataset?.headChip);  // the rule: a state chip on the title's line
  const h2 = el("h2", { id: `${id}-h`, text: title });
  return el("section", { class: "settings-section", "aria-labelledby": `${id}-h` },
    el("div", { class: "settings-section__head" }, chipNode ? titleChip(h2, chipNode) : h2,
      description ? el("p", { class: "small muted" }, description) : null),
    ...content.filter((n) => n !== chipNode));
}

// Menu 2 pages (DASH-389 to 391, owner, 13 November 2026: "The general sub menu should be on menu 2"): a Settings
// group's sections are pages of their own on the level 2 menu. A page's list of sections names the parts it shows
// (data-parts="gn-name gn-cat"); the start functions build only those where building one costs a request, and
// onlyParts leaves the rest out. A list with no data-parts shows every part, as before.
function partsOf(holder) {
  const h = typeof holder === "string" ? $(holder) : holder;
  const p = h?.dataset.parts;
  return p ? p.split(/\s+/).filter(Boolean) : null;
}

function wants(holder, id) {
  const p = partsOf(holder);
  return !p || p.includes(id);
}

function onlyParts(holder, nodes) {
  const p = partsOf(holder);
  return nodes.filter((n) => {
    if (!n) return false;
    if (!p) return true;
    const s = n.matches?.("section.settings-section") ? n : n.querySelector?.("section.settings-section");
    return !s || p.includes((s.getAttribute("aria-labelledby") || "").replace(/-h$/, ""));
  });
}

// Old addresses keep working (DASH-389 to 391): a link to a part that is now on its own page goes there, with its
// query and anchor. Page: { part or old anchor: its page now }.
const MOVED_PARTS = {
  "/settings-general.html": Object.fromEntries([
    ...["gn-up", "coming-up", "gn-scroll", "library-views", "library-views-s"].map((k) => [k, "settings-general-lists.html"]),
    ...["discover-rows", "discover-rows-s"].map((k) => [k, "settings-general-discover.html"]),
    ...["gn-dh", "download-hours"].map((k) => [k, "settings-general-hours.html"]),
    ...["gn-logs", "logs", "gn-test", "testing", "feedback-list", "gn-logdel", "delete-logs"].map((k) => [k, "settings-general-logs.html"]),
    ...["gn-style", "gn-design", "gn-access", "style", "appearance"].map((k) => [k, "settings-general-appearance.html"]),
  ]),
  // DASH-396: Discover rows is its own page, a section per area.
  "/settings-general-lists.html": { "discover-rows": "settings-general-discover.html", "discover-rows-s": "settings-general-discover.html" },
  "/settings-downloads.html": { "dl-usenet": "settings-downloads-usenet.html", "dl-hours": "settings-downloads-hours.html" },
  "/settings-radio.html": { "radio-link": "settings-radio-link.html", "radio-library": "settings-radio-library.html", "radio-logos": "settings-radio-logos.html" },
  "/settings-general-performance.html": { "pf-pictures": "settings-general-pictures.html", "pf-danger": "settings-general-pictures.html" },
  "/settings-security.html": { "sc-pw": "settings-security-password.html", "sc-keys": "settings-security-keys.html", "sc-mcp": "settings-security-keys.html",
    "sc-ses": "settings-security-sessions.html", "sc-danger": "settings-security-sessions.html" },
};

function followMovedPart(path = location.pathname, hash = location.hash, search = location.search) {
  const moved = MOVED_PARTS[path];
  if (!moved) return null;
  let to = moved[decodeURIComponent(hash.slice(1)).replace(/-h$/, "")];
  const area = new URLSearchParams(search).get("discover");
  if (!to && area && ["/settings-general.html", "/settings-general-lists.html"].includes(path)) to = "settings-general-discover.html";
  // ?discover=tv#discover-rows-s, Discover's old link, opens that area's section (DASH-396).
  if (to === "settings-general-discover.html") return `/${to}${/^[a-z]{2,12}$/.test(area || "") ? `#dr-${area}` : ""}`;
  return to ? `/${to}${search}${hash}` : null;
}

{
  const go = () => { const to = followMovedPart(); if (to) location.replace(to); };
  go();
  addEventListener("hashchange", go);  // a link to a moved part from the page it used to be on
}

// Settings pattern 9, the danger zone: last on the page, its own section with a red edge; each button opens a
// danger dialog that says what happens.
function dangerSection(id, title, description, ...content) {
  const s = section(id, title, description, ...content);
  s.classList.add("settings-section--danger");
  return s;
}

// A settings page confirms a save beside its button ("Saved at 16:31"), not in a toast (CONTENT-DESIGN.md).
// The note has a fixed id, so it can be shown after a save that redraws the page.
function savedNote(id) {
  return el("span", { class: "saved-note", id, hidden: true });
}

function showSaved(id, text) {
  const note = document.getElementById(id);
  if (note) window.SharedComponents.savedNote(note, text);
}

// Saves General settings. saved: say so beside the control just used (settingSaved). A part that is drawn again
// after the save calls settingSaved itself once it is drawn, so the note lands beside the control drawn again.
async function saveGeneral(body, saved = false) {
  config = await api("/api/config/general", { method: "PUT", body });
  if (saved) settingSaved();
  $$("[data-site-name]").forEach((n) => { n.textContent = config.site_name; });
  return config;
}

// The whole app, as the server wants it back: a blank API key keeps the saved one.
function serviceBody(s, changes = {}) {
  const body = { ...s, ...changes };
  delete body.has_api_key;
  body.api_key = changes.api_key || "";
  if (body.link === body.url) body.link = "";
  return body;
}

// Redraws a list and keeps focus on the same control of the same row (rows carry data-key), so a row that moved
// keeps focus. (renderKeyed in common.js loses rows when render returns a new node for a key it already had.)
function redraw(root, nodes) {
  const focused = document.activeElement;
  const row = root.contains(focused) ? focused.closest("[data-key]") : null;
  const controls = (node) => [...node.querySelectorAll("button, a, input, select")];
  const at = row ? controls(row).indexOf(focused) : -1;
  root.replaceChildren(...nodes);
  if (!row) return;
  const again = [...root.querySelectorAll("[data-key]")].find((n) => n.dataset.key === row.dataset.key);
  (again && at >= 0 ? controls(again)[at] : again)?.focus({ preventScroll: true });
}

// Menu items run after the menu has closed and given focus back to its button, so a dialog returns there.
function later(fn) { setTimeout(fn, 0); }

// Download hours (DASH-389, DASH-390): one field shown in two places, Settings, General, Download hours and
// Settings, Downloads, Download hours. Both use this function and save the one setting (download_hours), so they
// stay in step. A switch and two selects, each applying at once.
function downloadHoursSection(id) {
  const hoursList = Array.from({ length: 24 }, (_, h) => [h, `${String(h).padStart(2, "0")}:00`]);
  const hoursSelect = (key, labelId) => {
    const select = el("select", { class: "select", "aria-labelledby": labelId },
      hoursList.map(([h, label]) => el("option", { value: String(h), text: label, selected: config.download_hours[key] === h })));
    select.addEventListener("change", async () => {
      const before = config.download_hours[key];
      try {
        await saveGeneral({ download_hours: { [key]: Number(select.value) } }, true);
      } catch (err) { select.value = String(before); problem(err.message); }
    });
    return select;
  };
  const hoursOn = el("input", { type: "checkbox", role: "switch", "aria-labelledby": "dh-on-l", checked: config.download_hours.enabled });
  hoursOn.addEventListener("change", async () => {
    try {
      await saveGeneral({ download_hours: { enabled: hoursOn.checked } }, true);
    } catch (err) { hoursOn.checked = !hoursOn.checked; problem(err.message); }
  });
  const clients = config.services.filter((s) => ["qbittorrent", "sabnzbd"].includes(s.type) && s.has_api_key);
  return section(id, "Download hours", "Starboard pauses qBittorrent, NZBGet, SABnzbd and Soulseek (slskd) outside these hours, in the server's local time, and starts again only what it paused. Seeding is left alone. These apply at once.",
    clients.length ? null : notice("info", "No download apps yet", "Add qBittorrent, NZBGet, SABnzbd or Soulseek (slskd) with its API key in Manage apps, so Starboard can pause and resume them."),
    el("ul", { class: "settings-rows" },
      settingRow("Only download between set hours", withCost("Inactive: downloads run at any time.", "hours"), el("label", { class: "switch" }, hoursOn), "dh-on-l"),
      settingRow("Start", "Downloads start at this hour.", hoursSelect("start", "dh-start-l"), "dh-start-l"),
      settingRow("End", "Downloads pause at this hour. An end before the start runs overnight.", hoursSelect("end", "dh-end-l"), "dh-end-l")));
}

// What a setting costs on the server, measured on a home server in November 2026 (an 8-core processor, about
// 10,000 films and episodes). Shown under each switch that uses processor time or memory, so a small server
// can keep only what it needs. Idle Starboard: about 16 MB and 0.01% of the processor (docs/TESTING.md).
const COSTS = {
  hours: "Costs about: one small check a minute, under 0.01% of the processor, no extra memory.",
  upcoming: "Costs about: one request to each app when Coming up opens, kept for 10 minutes. Further ahead means a bigger answer, still well under a second.",
  watch: "Costs about: 0.02 seconds of processor per check (every 5 minutes, under 0.01% overall) and under 1 MB of memory for the history. Deactivating it saves that, and keeps nothing running in the background.",
  every: "Every minute costs five times as much as every 5 minutes; every hour, a twelfth.",
  host: "Costs about: 2 milliseconds of processor a minute (0.003% overall) for all the readings together, measured with every one on, and no extra memory. Nothing runs while every one is deactivated.",
  weekly: "Costs about: one message a week. Nothing noticeable.",
  livetv: "Costs about: under 2 seconds of processor a day to refresh the guides. Testing every stream takes about a minute once a week, or when a channel list changes. It uses up to 35 MB more memory while it runs. Nothing in between. Deactivating it saves all of that.",
  importKeep: "Costs about: 1 second of processor and up to 40 MB more memory for about 20 seconds an hour, while it reads your Jellyfin library. Deactivating it saves that; Apply now still works.",
  defaults: "Costs about: two small requests per Jellyfin user an hour. Nothing noticeable.",
  listeningKeep: "Costs about: one reading of your Audiobookshelf library and users an hour. Each reading uses under a second of processor and a few MB more memory while it runs. Deactivating it saves that; Apply now still works.",
  history: "Costs about: one reading of the server's own counters each time, under 0.01% of the processor. A day of readings takes up to 1.5 MB of memory. Inactive: the System charts have no history.",
  scheduleEvery: "Every minute catches a new download straight away; every 5 minutes uses a fifth of the requests.",
  downloadsRefresh: "Each update asks each download app once (shared for 10 seconds). Slower, or off, means fewer requests while Downloads is open.",
  monitorRefresh: "Each reading takes under a thousandth of a second on the server. Slower means fewer readings while Monitor is open.",
  cardNumbers: "Costs about: one small request per app when Apps opens, shared for a minute. Deactivating it saves that.",
  usage: "Costs about: each run reads every file name in your folders (a few minutes for 30 TB, mostly disk reading, under 20 MB of memory). It costs nothing between runs. Starboard skips the disks inside a pool, so a pool is read once. Every night or every week keeps one sleeping thread; the other choices keep none.",
  spaceLog: "Costs about: one size check of each folder a day, taken when a page or the history asks anyway, and a few kilobytes a year. Nothing noticeable.",
  logKeep: "Costs about: a few kilobytes a day on disk (about 100 KB a month for a quiet server). Nothing in memory.",
  logSize: "Costs about: nothing between days. Starboard counts what it writes as it writes it, so the size is only checked when the count passes the limit.",
  logDetail: "Costs about: one short line per page request and per call to your apps, about 1 to 5 MB a day on a busy dashboard. For 24 hours deactivates itself, so it cannot fill the disk.",
  storageRefresh: "Each update checks the size of each folder, under a thousandth of a second. Inactive means only when you open the page or press Check again.",
  posters: "Costs about: a small download per new poster, kept for a week (a few megabytes on disk).",
  icons: "Costs about: one download per app, once.",
};

function withCost(hint, key) {
  return el("span", {}, hint, el("span", { class: "setting__cost", text: COSTS[key] }));
}

// Search for new apps ---------------------------------------------------------
// Finds apps on this computer that are not in Manage apps yet, and adds the ones you tick. Used by Manage apps
// (a slide-out) and by the set-up wizard (a step). onAdded gets the server's answer.

// With expect (the keys of apps just started), it looks again until each one it can recognise answers, for up to 4
// minutes: an app opens its port a while after it starts (Radarr and Sonarr can take over a minute).
async function appFinder(onAdded, { expect = null, shown = null } = {}) {
  const box = el("div", { class: "stack-4", "aria-busy": "true" }, el("p", { class: "muted", text: "Finding apps on this computer…" }));
  let found;
  try {
    found = await api("/api/discover");
    const began = Date.now();
    const missing = () => (expect || []).filter((k) => (found.known || []).includes(k) && !found.items.some((i) => i.key === k));
    while (expect && missing().length && Date.now() - began < 240000) {
      shown?.(`Waiting for the apps to answer: ${found.items.length} found, ${missing().length} still starting…`);
      await new Promise((r) => setTimeout(r, 5000));
      found = await api("/api/discover");
    }
  } catch (e) { box.replaceChildren(notice("danger", "Could not check this computer for apps", e.message)); return { box, add: null }; }
  const fresh = found.items.filter((i) => !i.already);
  const known = found.items.filter((i) => i.already);
  if (!fresh.length) {
    box.replaceChildren(notice("success", "Nothing new found", `Every app Starboard recognises on this computer is already in your list${known.length ? ` (${known.length})` : ""}. Add others by hand with Add an app.`));
    return { box, add: null };
  }
  const picks = fresh.map((i) => {
    const input = el("input", { type: "checkbox", checked: true });
    const label = el("label", { class: "check" }, input, el("span", { class: "check__text" }, el("strong", { text: i.name }),
      el("span", { class: "check__hint", text: [i.url.replace("http://", ""), i.background ? "background service" : "",
        i.needs_key ? (i.can_read_key ? "API key can be read for you" : "needs its API key") : ""].filter(Boolean).join(" · ") })));
    return { i, input, label };
  });
  const anyKey = fresh.some((i) => i.can_read_key);
  const add = async () => {
    const items = picks.filter((p) => p.input.checked).map((p) => ({ ...p.i, read_key: anyKey }));
    if (!items.length) { problem("Tick the apps to add"); return null; }
    const r = await api("/api/discover/add", { method: "POST", body: { items } });
    config = r.config;
    toast(`Added ${r.added.length} ${r.added.length === 1 ? "app" : "apps"}`);
    onAdded?.(r);
    return r;
  };
  box.replaceChildren(...[
    el("p", { text: `Found ${fresh.length} ${fresh.length === 1 ? "app" : "apps"} that ${fresh.length === 1 ? "is" : "are"} not in your list yet${known.length ? `, and ${known.length} you already have` : ""}. Untick any you do not want.` }),
    el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Apps to add" }), el("div", { class: "switch-list" }, picks.map((p) => p.label))),
    anyKey ? el("p", { class: "small muted", text: "Starboard reads each app's API key from its own settings through Docker, so there is nothing to copy. The keys stay on the server." }) : null,
    !found.docker ? el("p", { class: "small muted", text: "With Docker access (./install.sh --docker) Starboard could also read API keys for you and find apps on other ports." }) : null,
  ].filter(Boolean));
  return { box, add, ticked: () => picks.filter((p) => p.input.checked).length };
}

// The set-up's step names and questions, the same file the terminal set-up reads (web/setup-steps.json), so a step
// is called the same in both.
let STEP_TABLE = null;

async function stepTable() {
  if (!STEP_TABLE) {
    try {
      const r = await fetch("/setup-steps.json", { cache: "no-cache" });
      STEP_TABLE = Object.fromEntries((await r.json()).steps.map((x) => [x.id, x]));
    } catch { STEP_TABLE = {}; }
  }
  return STEP_TABLE;
}

function stepNamed(table, id) {
  const x = table[id] || {};
  return { title: x.title || id, question: x.question || "", help: x.help || "" };
}

// continuePlain: the step's own main action in its body is the one primary in view (DASH-309, R9), so the foot's
// button is plain, as on Install apps' last step.
function wizardFrame({ root, steps, index, onBack, onSkip, onContinue, continueText = "Continue", busy = false, continuePlain = false }) {
  const step = steps[index];
  const list = el("ol", { class: "steps steps--collapse", "aria-label": "Steps" }, steps.map((st, i) => el("li", {
    "data-done": i < index ? "" : null, "aria-current": i === index ? "step" : null }, st.title,
    i < index ? el("span", { class: "visually-hidden", text: ", done" }) : i === index ? el("span", { class: "visually-hidden", text: ", current step" }) : null)));
  const short = el("p", { class: "steps__short", text: `Step ${index + 1} of ${steps.length}: ${step.title}` });
  // A step in parts (WIZARD.md, section 3): the parts under the step list, done ones ticked, the current outlined.
  const sub = step.group ? el("ol", { class: "steps steps--sub", "aria-label": `${step.groupTitle}, in ${step.parts.length} parts` }, step.parts.map((name, i) => el("li", {
    "data-done": i < step.part ? "" : null, "aria-current": i === step.part ? "step" : null }, name,
    i < step.part ? el("span", { class: "visually-hidden", text: ", done" }) : i === step.part ? el("span", { class: "visually-hidden", text: ", current part" }) : null))) : null;
  const cont = el("button", { type: "button", class: continuePlain ? "btn" : "btn btn--primary", disabled: busy, onclick: onContinue }, continueText);
  const foot = el("div", { class: "wizard__foot" }, cont,
    index > 0 ? el("button", { type: "button", class: "btn", onclick: onBack }, "Back") : null,
    step.skippable === false ? null : el("button", { type: "button", class: "btn btn--quiet", onclick: onSkip }, "Skip this step"));
  const heading = el("h2", { id: "wiz-h", tabindex: "-1", text: step.question });
  root.replaceChildren(list, short, ...(sub ? [sub] : []), el("section", { class: "panel", "aria-labelledby": "wiz-h" },
    el("div", { class: "stack-1" }, heading, step.intro ? el("p", { class: "muted", text: step.intro }) : null),
    ...step.nodes.filter((n) => !n?.classList?.contains("help-links")), stepHelp(step), foot));
  return { heading, cont };
}

// The step's help at the bottom of the step, above the buttons (LIBRARY.md, Help links): the step's own help
// ("Which one is right for me?") first, then its article in the help centre (web/setup-steps.json, the same for
// the terminal set-up), in one row.
function stepHelp(step) {
  const links = step.nodes.filter((n) => n?.classList?.contains("help-links")).flatMap((n) => [...n.childNodes]);
  if (step.help) links.push(helpButton("Help with this step", { page: step.help, title: `Help: ${step.question}`, back: "Back to set-up" }));
  return links.length ? el("p", { class: "help-links" }, links) : null;
}

// A long change's dialog (DASH-252, 13 November 2026): Move them into Reelix, Take over my apps, Roll back and Clear
// away the old apps run for minutes. This opens the library's dialog with a working bar (still, with less motion), a
// task list (each app or step with its state, and what it is doing), what is happening now, and the result at the
// end. Closing it does not stop the work: the step on the page says it is still running, with Show progress.
// taskJob({ title, url, failedWord }) returns { open(), running(), node, done: Promise of the last job }.
const TASK_WORDS = { waiting: STATUS.waiting, working: STATUS.inProgress, done: STATUS.done, failed: STATUS.failed, skipped: STATUS.notStarted };

let taskJobCount = 0;

function taskJob({ title, url, failedWord = STATUS.failed[0], intro = "", returnTo = "" }) {
  const id = `task-job-${++taskJobCount}`;
  const words = { ...TASK_WORDS, failed: [failedWord, "danger"] };
  const heading = el("h2", { class: "panel-header__title", id: `${id}-h`, text: title, tabindex: "-1" });
  const close = el("button", { type: "button", class: "icon-btn", "aria-label": `Close ${title}` }, icon("x", 20));
  const label = el("span", { text: `${title}…` });
  const count = el("span", { class: "numeric" });
  const bar = el("div", { class: "progress progress--busy", role: "progressbar", "aria-labelledby": `${id}-bar`, "aria-valuetext": "Starting" }, el("span"));
  const meter = el("div", { class: "meter" }, el("div", { class: "meter__label", id: `${id}-bar` }, label, count), bar);
  const now = el("p", { class: "task-now small" });
  const list = el("ul", { class: "task-list", "aria-label": "Steps" });
  const result = el("div", { class: "stack-2" });
  const live = el("div", { class: "visually-hidden", role: "status", "aria-live": "polite" });
  const shut = el("button", { type: "button", class: "btn", text: "Close" });
  const shutHint = el("p", { class: "small muted", text: "Closing this does not stop it. The page shows it is still running." });
  const dialog = el("dialog", { class: "dialog dialog--scroll task-dialog", "aria-labelledby": `${id}-h` },
    el("div", { class: "panel-header" }, heading, close),
    el("div", { class: "dialog__body" }, intro ? el("p", { text: intro }) : null, meter, now, list, result, live),
    el("div", { class: "dialog__foot" }, shut, shutHint));
  close.addEventListener("click", () => dialog.close());
  shut.addEventListener("click", () => dialog.close());
  let opener = null;
  // Focus goes back to what opened it; when the page was drawn again meanwhile, to the step's heading.
  dialog.addEventListener("close", () => {
    if (finished) setTimeout(() => dialog.remove(), 0);  // nothing more to show once it has finished
    if (opener?.isConnected) { opener.focus(); return; }
    const head = returnTo && document.getElementById(returnTo);
    if (head) { head.setAttribute("tabindex", "-1"); head.focus(); }
  });
  // The page's own line while it runs: still running, with Show progress to open the dialog again.
  const showAgain = el("button", { type: "button", class: "btn", text: "Show progress" });
  showAgain.addEventListener("click", () => open());
  const pageLine = el("div", { class: "notice", role: "status" }, icon("info"),
    el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: `${title}: still running` }),
      el("p", { text: "It carries on if you close the dialog or leave this page." })), showAgain);
  const states = new Map();
  let finished = false;
  let lastNow = "";
  const draw = (j) => {
    const tasks = j.tasks || [];
    const doneCount = tasks.filter((t) => ["done", "failed", "skipped"].includes(t.state)).length;
    count.textContent = tasks.length ? `${doneCount} of ${tasks.length}` : "";
    bar.setAttribute("aria-valuetext", tasks.length ? `${doneCount} of ${tasks.length} steps` : "Starting");
    const items = tasks.map((t) => {
      const [word, tone] = words[t.state] || words.waiting;
      const li = el("li", { class: "task-list__item", "data-state": t.state },
        el("span", { class: "task-list__name", text: t.label }), chip(word, tone),
        t.detail ? el("span", { class: "task-list__detail small muted", text: t.detail }) : null);
      if (t.state === "working") li.setAttribute("aria-current", "step");
      const before = states.get(t.id);
      if (before && before !== t.state && t.state !== "working") live.textContent = `${t.label}: ${word}`;
      states.set(t.id, t.state);
      return li;
    });
    list.replaceChildren(...items);
    const nowText = j.now || (j.step && !j.finished ? `${j.step}…` : "");
    if (nowText !== lastNow) { now.textContent = nowText ? `Now: ${nowText}` : ""; now.hidden = !nowText; lastNow = nowText; }
  };
  const end = (j, onResult) => {
    finished = true;
    const tasks = j.tasks || [];
    const bad = tasks.filter((t) => t.state === "failed" || t.state === "skipped");
    const ok = j.ok !== false && !bad.length && !j.error;
    bar.classList.remove("progress--busy");
    bar.firstChild.style.width = "100%";
    if (!ok) bar.dataset.tone = j.ok === false ? "danger" : "warning";
    label.textContent = ok ? "Finished" : j.ok === false ? "Stopped" : "Finished, with things that need attention";
    now.textContent = "";
    now.hidden = true;
    shutHint.hidden = true;
    shut.textContent = "Done";
    const summary = onResult ? onResult(j, ok) : null;
    const box = notice(ok ? "success" : j.ok === false ? "danger" : "warning", summary?.title || (ok ? "Finished" : "Not everything finished"),
      summary?.text || (j.notes || []).join(". ") || j.error || "");
    box.setAttribute("tabindex", "-1");
    result.replaceChildren(...[box, j.ok === false && j.log ? el("details", {}, el("summary", { text: "Show the details" }), el("pre", { class: "code-block", text: j.log })) : null].filter(Boolean));
    live.textContent = `${title}: ${summary?.title || (ok ? "finished" : "not everything finished")}`;
    pageLine.replaceWith(el("span"));  // the page draws its own result
    if (dialog.open) box.focus();
  };
  const open = () => {
    opener = document.activeElement instanceof HTMLElement && !dialog.contains(document.activeElement) ? document.activeElement : opener;
    if (!dialog.isConnected) document.body.append(dialog);
    if (!dialog.open) dialog.showModal();
    heading.focus();
  };
  // Follows the job until it finishes: every two seconds while it runs, never afterwards (lightweight first).
  const follow = (onResult) => new Promise((resolve) => {
    const look = async () => {
      const j = await api(url).catch(() => null);
      if (j) draw(j);
      if (j && j.finished) { end(j, onResult); resolve(j); return; }
      setTimeout(look, 2000);
    };
    look();
  });
  return { open, follow, pageLine, dialog, running: () => !finished };
}

// Advanced settings (DASH-225): every Settings page opens with only its basic settings; one switch at the top shows
// the rest. The choice is saved with Starboard's settings, so it holds on every Settings page and every device.
// The basic settings are the approved table (FULL-INSTALL-AND-APP-SETUP section 3); the sections listed here are the
// advanced ones, marked as each page draws them.
const ADVANCED_SECTIONS = new Set([
  "gn-cat", "gn-card", "gn-up", "gn-logs", "gn-logdel", "gn-design", "gn-guide",  // General
  "sc-ses",  // Security
  "in-how", "tk",  // Your install
  "rx-mediaservers", "rx-downloadclients", "rx-library", "rx-folders", "rx-information", "rx-files", "rx-requests",
  "rx-notifications", "rx-importlists", "rx-people", "rx-books", "rx-music",  // Reelix
  "jf-defaults", "jf-import", "jf-missing", "jf-you",  // Jellyfin
  "ls-copy", "ls-missing",  // Audiobookshelf
  "al-what", "al-week", "al-watch", "al-host",  // Alerts
  "pf-bg", "pf-pages", "pf-now",  // Performance
]);

function markAdvanced(root) {
  let hidden = 0;
  // A level 2 page made only of advanced parts (Security, Sign out everywhere) shows them: the page is the choice.
  const parts = $$("[data-parts]", root).flatMap((h) => partsOf(h)).filter((id) => !id.endsWith("-danger"));
  if (parts.length && parts.every((id) => ADVANCED_SECTIONS.has(id))) return 0;
  $$("section.settings-section", root).forEach((sec) => {
    const id = (sec.getAttribute("aria-labelledby") || "").replace(/-h$/, "");
    if (ADVANCED_SECTIONS.has(id)) { sec.dataset.advanced = ""; hidden += 1; }
  });
  return hidden;
}

function advancedSwitch() {
  const main = $("main .page") || $("main");
  if (!main || $("#advanced-switch") || !$$("[id$='-sections'], #reelix-sections", main).length) return;
  const input = el("input", { type: "checkbox", role: "switch", id: "advanced-switch", checked: !!config.settings_advanced });
  const note = el("p", { class: "small muted", id: "advanced-note" });
  const apply = () => {
    document.body.classList.toggle("show-advanced", input.checked);
    const n = $$("[data-advanced]", main).length;
    // Only on a page that has advanced settings to show (Manage apps and Plug-ins have none), whether or not it is
    // on: it was left showing on those pages while on (issue #11).
    box.hidden = !n;
    const text = input.checked ? "Showing every setting. Your choice is saved for every Settings page."
      : n ? `${n} more ${n === 1 ? "section is" : "sections are"} under More settings.` : "";
    if (note.textContent !== text) note.textContent = text;  // only a real change, or the watcher below would loop
  };
  input.addEventListener("change", async () => {
    apply();
    try { await saveGeneral({ settings_advanced: input.checked }); } catch (e) { problem(e.message); }
  });
  // A small switch at the right of the page's heading, where Sign out was (owner, 12 November 2026).
  note.classList.add("visually-hidden");
  input.setAttribute("aria-describedby", "advanced-note");
  const box = el("label", { class: "switch advanced-toggle", title: "Shows everything each app can change" },
    el("span", { text: "More settings" }), input, note);
  // On the heading's line, at the right (12 November 2026: it was among the page's own buttons on Manage apps).
  const h1 = $(".page-head h1", main);
  if (h1) onTitle(h1, box); else main.prepend(box);
  // Sections are drawn as their data arrives: mark each one as it appears, and keep the note's count right.
  new MutationObserver((changes) => {
    if (changes.every((c) => box.contains(c.target))) return;  // the switch's own note changing is not a new section
    markAdvanced(main);
    apply();
  }).observe(main, { childList: true, subtree: true });
  markAdvanced(main);
  apply();
  input.addEventListener("change", () => topicTabs());
}

// Topic tabs (owner, 12 November 2026: "with long settings pages, a tab menu on each page covering each topic"):
// under the heading and description, one tab per section on a page with four sections or more, showing that section
// only. A link to a part (#rx-indexers-h) opens its tab. Sections are drawn as their data arrives, so the tabs
// follow; Advanced settings adds its sections' tabs. Not inside a slide-out, which already shows one part.
let topicCurrent = null;

function topicTabs() {
  const main = $("main .page");
  // Every list of sections on the page (General has its own and Library views'), except where the sections are
  // one list in groups (Manage apps: apps by category, dragged between them).
  const holders = main ? $$(".settings-sections", main).filter((h) => !h.closest("[data-no-topic-tabs]")) : [];
  const holder = holders[0];
  if (!holder || IN_PANEL || holders.some((h) => h.id === "app-sections")) return;
  let off = false;
  try { off = localStorage.getItem("starboard.topic-tabs") === "off"; } catch { /* tabs on */ }
  const topics = holders.flatMap((h) => $$("section.settings-section", h)).filter((s) => !s.parentElement.closest("section.settings-section")
    && !(s.hasAttribute("data-advanced") && !document.body.classList.contains("show-advanced")) && $("h2", s));
  let nav = $("#topic-tabs");
  // A page may ask for tabs from fewer sections (data-topic-min): a plug-in's page has General and its own parts.
  const least = Math.max(2, parseInt(holder.dataset.topicMin || "4", 10) || 4);
  if (off || topics.length < least) {
    nav?.remove();
    topics.forEach((s) => s.classList.remove("topic-off"));
    return;
  }
  // Each new section gets an id no other element has: numbering by place gave a section shown by Advanced settings
  // the id of one already named, so two tabs were selected at once (found taking the 0.19 help pictures).
  let free = 0;
  topics.forEach((s) => {
    if (s.id) return;
    while (document.getElementById(`topic-${free}`)) free++;
    s.id = `topic-${free}`;
  });
  const key = topics.map((s) => `${s.id}:${$("h2", s).textContent}`).join("|");
  if (!nav) {
    nav = el("nav", { id: "topic-tabs", class: "topic-tabs", "aria-label": "Topics on this page" }, el("div", { role: "tablist", "aria-label": "Topics on this page" }));
    ($(".page-head", main) || holder).after(nav);
    // Their height, for the space the page keeps clear above what has focus while they stay under the header (app.css).
    if (window.ResizeObserver) new ResizeObserver(() => document.documentElement.style.setProperty("--topic-tabs-h", `${nav.offsetHeight}px`)).observe(nav);
  }
  const want = decodeURIComponent(location.hash.slice(1));
  const fromHash = want && topics.find((s) => s.id === want || $(`[id="${CSS.escape(want)}"]`, s));
  if (fromHash && nav.dataset.hash !== want) { topicCurrent = fromHash.id; nav.dataset.hash = want; }
  if (!topics.some((s) => s.id === topicCurrent)) topicCurrent = topics[0].id;
  const show = (id, focus) => {
    topicCurrent = id;
    topics.forEach((s) => s.classList.toggle("topic-off", s.id !== id));
    // Each section is also found by its id now, not only from when the tabs were made: a page drawn again since (a
    // plug-in's page after an update, DASH-424) has new sections, and the old ones are no longer on the page.
    $$("[role=tab]", nav).forEach((t) => document.getElementById(t.getAttribute("aria-controls"))?.classList.toggle("topic-off", t.getAttribute("aria-controls") !== id));
    $$("[role=tab]", nav).forEach((t) => {
      const on = t.getAttribute("aria-controls") === id;
      t.setAttribute("aria-selected", String(on));
      t.tabIndex = on ? 0 : -1;
      if (on && focus) t.focus();
    });
  };
  if (nav.dataset.key !== key) {
    nav.dataset.key = key;
    const list = $("[role=tablist]", nav);
    list.replaceChildren(...topics.map((s) => {
      const t = el("button", { type: "button", role: "tab", id: `${s.id}-tab`, "aria-controls": s.id, class: "topic-tabs__tab", text: $("h2", s).textContent });
      t.addEventListener("click", () => show(s.id));
      return t;
    }));
    list.onkeydown = (e) => {
      const tabs = $$("[role=tab]", list);
      const at = tabs.indexOf(document.activeElement);
      if (at < 0) return;
      const to = { ArrowRight: at + 1, ArrowLeft: at - 1, Home: 0, End: tabs.length - 1 }[e.key];
      if (to === undefined) return;
      e.preventDefault();
      const next = tabs[(to + tabs.length) % tabs.length];
      show(next.getAttribute("aria-controls"), true);
    };
    topics.forEach((s) => { s.setAttribute("role", "tabpanel"); s.setAttribute("aria-labelledby", `${s.id}-tab`); });
  }
  show(topicCurrent);
}

function watchTopics() {
  const holders = $$("main .page .settings-sections");
  if (!holders.length || IN_PANEL) return;
  let queued = false;
  const seen = new MutationObserver(() => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; topicTabs(); });
  });
  holders.forEach((h) => seen.observe(h, { childList: true, subtree: true }));
  window.addEventListener("hashchange", () => topicTabs());
  topicTabs();
}

// Each page's own part (settings-<part>.js) starts once the page and all its scripts have loaded, whatever order
// they arrive in. A start that is not on this page (its part is not loaded) is skipped.
const settingsLoaded = new Promise((done) => {
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", done, { once: true });
  else done();
});
const SETTINGS_STARTS = [["#app-sections", "startManageApps"], ["#general-sections", "startGeneral"], ["#security-sections", "startSecurity"], ["#signin-sections", "startSignin"],
  ["#alerts-sections", "startAlerts"], ["#jellyfin-sections", "startJellyfin"], ["#media-server-sections", "startMediaServer"], ["#listening-sections", "startListening"],
  ["#radio-sections", "startRadioSettings"], ["#performance-sections", "startPerformance"], ["#reelix-sections", "startReelix"],
  ["#install-sections", "startYourInstall"], ["#downloads-sections", "startDownloadsSettings"], ["#guide", "startGuide"],
  ["#upgrade", "startUpgrade"], ["#install", "startInstall"], ["#bring-in", "startBringIn"], // DASH-455
  ["#copy-sections", "startCopy"], ["#dispatcharr-sections", "startDispatcharr"], // DASH-228
  ["#version-notice", "startAbout"], ["#general-sections", "generalScrollSection"]];
Promise.all([startPage(), settingsLoaded]).then(async ([session]) => {
  if (!session) return;
  if ($("#releases-list")) { globalThis.startReleases?.(session.repo); return; }
  try { config = await api("/api/config"); } catch (e) { problem(e.message); return; }
  advancedSwitch();
  watchTopics();
  for (const [selector, start] of SETTINGS_STARTS) if ($(selector)) globalThis[start]?.();
  $("#download-rights")?.append(downloadRights());
});
