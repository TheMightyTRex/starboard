// Settings, Apps, Jellyfin and Audiobookshelf.

const countWords = (n, one, many) => `${n.toLocaleString("en-GB")} ${n === 1 ? one : many}`;

// Accounts read from another app, each matched to a user here (DASH-309): setting rows, not a table with a select
// per row. The account is the label, its counts the hint, the user the control; a change saves at once and says so
// beside the select.
function accountRows(accounts, users, { caption, app, none, userOf, counts, put }) {
  return el("ul", { class: "settings-rows", "aria-label": caption }, accounts.map((a, i) => {
    const labelId = `acct-${app.toLowerCase()}-${i}`;
    const pick = el("select", { class: "select", "aria-labelledby": labelId, disabled: !users.length },
      el("option", { value: "", text: none }), users.map((u) => el("option", { value: u, text: u, selected: (userOf(a) || "") === u })));
    let before = pick.value;
    pick.addEventListener("change", async () => {
      try { await put({ [a.name]: pick.value }); before = pick.value; settingSaved(); }
      catch (err) { pick.value = before; problem(err.message); }
    });
    const hint = `${counts(a)}.${a.suggested && !userOf(a) ? ` Same name in ${app}: ${a.suggested}.` : ""}`;
    const row = settingRow(a.name, hint, pick, labelId);
    row.dataset.key = a.name;
    return row;
  }));
}

// Jellyfin ------------------------------------------------------------------
// Live TV, watch history import and user defaults: switches that apply at once, each job's last run, Run now.

const JOB_STATE = { running: ["Running", "info"], done: ["Last run worked", "success"], failed: ["Last run failed", "danger"] };

function jobRun(job) {
  const when = job.finished ? new Date(job.finished * 1000).toLocaleString("en-GB", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "";
  const [words, tone] = JOB_STATE[job.state] || ["Not run yet", "muted"];
  return el("div", { class: "job-run" }, chip(words, tone),
    el("span", { class: "small muted", text: [when, job.summary].filter(Boolean).join(" · ") }));
}

async function startJellyfin() {
  const root = $("#jellyfin-sections");
  // This page is the media server's tab (DASH-565): Jellyfin's own sections draw only while Jellyfin is the one in use.
  try {
    if ((await api("/api/media-server")).active !== "jellyfin") { root.replaceChildren(); root.removeAttribute("aria-busy"); return; }
  } catch { /* draw them as before */ }
  let d;
  try { d = await api("/api/extras"); } catch (e) { root.replaceChildren(notice("danger", "Could not load", e.message)); return; }
  const jobs = Object.fromEntries(d.jobs.map((j) => [j.key, j]));
  const x = () => config.extras;
  // A switch here draws the page again, then says it saved beside the switch drawn again (settingSaved).
  const save = async (body) => {
    try { await saveGeneral({ extras: body }); return true; } catch (err) { problem(err.message); return false; }
  };
  const sw = (labelId, checked, onChange, disabled = false) => {
    const input = el("input", { type: "checkbox", role: "switch", "aria-labelledby": labelId, checked, disabled });
    input.addEventListener("change", async () => { if (!(await onChange(input.checked))) input.checked = !input.checked; else { await startJellyfin(); settingSaved(); } });
    return el("label", { class: "switch" }, input);
  };
  const runNow = (key, label, text = `Run ${label} now`) => el("button", { type: "button", class: "btn", onclick: async (e) => {
    e.currentTarget.disabled = true;
    try { await api(`/api/extras/${key}/run`, { method: "POST" }); toast(`${label} started`); setTimeout(startJellyfin, 4000); }
    catch (err) { problem(err.message); }
  } }, icon("play"), text);
  const welcome = new URLSearchParams(location.search).has("welcome");
  const jfMissing = !d.history.jellyfin;

  // Jellyfin itself
  let top = null;
  if (jfMissing) {
    const found = await api("/api/jellyfin/detect").catch(() => null);
    top = notice("info", found?.found ? `Starboard found Jellyfin ${found.found.version} at ${found.found.url}` : "Add Jellyfin first",
      found?.found && !found.in_apps
        ? "Add it in Manage apps with its API key, from Jellyfin's Dashboard, API keys."
        : "Give your Jellyfin app its API key in Manage apps, from Jellyfin's Dashboard, API keys.",
      el("a", { class: "btn", href: found?.found && !found.in_apps ? `/settings.html?add=jellyfin&url=${encodeURIComponent(found.found.url)}` : "/settings.html" }, "Manage apps"));
  }

  // Live TV: a plug-in since DASH-285 once it has moved; until then, as before.
  let livePlugin = null;
  try { livePlugin = (await api("/api/plugins")).plugins.find((x) => x.id === "livetv") || null; } catch { /* as before */ }
  const lt = jobs.livetv;
  const address = el("input", { class: "input", inputmode: "url", autocomplete: "off", value: x().livetv_address, placeholder: d.self_url });
  const addressForm = el("form", { class: "form-stack", novalidate: true },
    field("Address Jellyfin uses to reach Starboard", address, { hint: `For channel logos and Pluto streams. Blank: ${d.self_url}. Jellyfin must be able to open it, so Starboard needs home network access on.` }),
    el("div", { class: "actions" }, el("button", { type: "submit", class: "btn", text: "Save" }), savedNote("livetv-address-saved")));
  addressForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (await save({ livetv_address: address.value })) { await startJellyfin(); showSaved("livetv-address-saved"); }
  });
  // Where Jellyfin sees the files (DASH-229): blank lets Starboard work it out for an Install apps stack.
  const jfFolderForm = locationPicker({ id: "livetv-folder", label: "Live TV folder inside Jellyfin", app: "jellyfin", value: x().livetv_jellyfin_folder || "",
    hint: "Starboard adds the channels and guides to Jellyfin itself. Empty: Starboard works it out when it installed Jellyfin.",
    onChange: async (v) => { if (await save({ livetv_jellyfin_folder: v })) settingSaved(); } }).node;
  const liveRows = el("ul", { class: "settings-rows" },
    settingRow("Build Live TV channels and guide", withCost(lt.what + ". Free channels only: Samsung TV Plus, Pluto TV and Free-TV, with Sky-style numbers.", "livetv"),
      sw("lt-on-l", x().livetv, (on) => save({ livetv: on })), "lt-on-l"));
  const liveNeeds = lt.needs.length ? notice("warning", "Needs set-up on the server", `Starboard needs ${lt.needs.join(" and ")}. Run ./install.sh and say yes to Live TV.`) : null;
  const liveHelp = el("p", { class: "help-links" }, helpButton("How Jellyfin uses these files", { body: el("p", { text: "With Jellyfin's API key, Starboard adds these to Jellyfin after each run, and leaves your own alone. By hand, in Jellyfin: Dashboard, Live TV. Add a tuner of type M3U for each playlist (channels.m3u, samsung.m3u, pluto.m3u). Add an XMLTV guide for each guide file (guide.xml, guide-samsung.xml, guide-pluto.xml). Use the folder they are in inside Jellyfin." }) }));

  // Import watch history
  const h = d.history;
  const kind = el("select", { class: "select" }, [["plexdb", "A Plex database file"], ["plex", "A Plex server"], ["emby", "An Emby server"], ["jellyfin", "Another Jellyfin server"], ["json", "A history file Starboard made before"]]
    .map(([v, t]) => el("option", { value: v, text: t })));
  const url = el("input", { class: "input", inputmode: "url", autocomplete: "off", placeholder: "http://plex:32400" });
  const token = el("input", { class: "input", type: "password", autocomplete: "off" });
  const file = el("input", { type: "file", class: "input" });
  const urlField = field("Server address", url, { span: true });
  const tokenHint = el("span", {});
  const fileHint = el("span", {});
  const tokenField = field("Token or API key", token, { span: true, hint: tokenHint });
  const fileField = field("File", filePicker(file), { span: true, hint: fileHint });
  const importError = el("div", { role: "alert" });
  const showFields = () => {
    const isFile = ["plexdb", "json"].includes(kind.value);
    urlField.hidden = tokenField.hidden = isFile;
    fileField.hidden = !isFile;
    tokenHint.textContent = kind.value === "plex" ? "Your Plex token (Plex's help: Finding an authentication token). Only your own account's history is read." : "An API key from that server's Dashboard, API keys. Every user's history is read.";
    fileHint.textContent = kind.value === "plexdb" ? "A copy of com.plexapp.plugins.library.db from the Plex server (stop Plex first, or copy it with its -wal file). Every account's history is read; the copy is deleted after reading." : "history.json from an earlier import, or plex-watched.json from the old launcher.";
    url.placeholder = kind.value === "plex" ? "http://plex:32400" : "http://emby:8096";
  };
  kind.addEventListener("change", showFields);
  const importForm = el("form", { novalidate: true, class: "stack-4" },
    el("div", { class: "form-grid" }, field("Import from", kind, { span: true }), urlField, tokenField, fileField),
    el("div", { class: "actions" }, el("button", { type: "submit", class: "btn btn--primary" }, icon("import"), "Read the history")), importError);
  showFields();
  importForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    importError.replaceChildren();
    try {
      if (["plexdb", "json"].includes(kind.value)) {
        if (!file.files[0]) throw new Error("Choose a file first");
        const r = await fetch(`/api/import/upload?kind=${kind.value}`, { method: "POST", headers: { "X-Starboard": "1" }, body: file.files[0] });
        if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || "The upload did not work");
      } else {
        await api("/api/import", { method: "POST", body: { kind: kind.value, url: url.value, token: token.value } });
      }
      toast("Reading the history. This can take a few minutes.");
      const wait = setInterval(async () => { const now = await api("/api/extras"); if (!now.importing) { clearInterval(wait); startJellyfin(); } }, 3000);
    } catch (err) { importError.replaceChildren(notice("danger", "Not started", err.message)); }
  });
  const users = h.jellyfin_users;
  const whoPick = el("select", { class: "select", id: "jf-you-pick" },
    el("option", { value: "", text: "Jellyfin's first admin (the one Starboard made)" }),
    users.map((u) => el("option", { value: u, text: u, selected: (config.extras.jellyfin_user || "") === u })));
  whoPick.addEventListener("change", () => saveGeneral({ extras: { jellyfin_user: whoPick.value } }, true).catch((e) => problem(e.message)));
  const whose = field("Show what this user has watched", whoPick);
  const mapping = h.accounts.length ? accountRows(h.accounts, users, {
    caption: "Accounts and the Jellyfin user each one goes to", app: "Jellyfin", none: "Do not import", userOf: (a) => a.jellyfin_user,
    counts: (a) => `${countWords(a.films, "film", "films")}, ${countWords(a.episodes, "episode", "episodes")}, ${a.applied} applied`,
    put: (mapping) => api("/api/import/mapping", { method: "PUT", body: { mapping } }) }) : null;
  const matchSame = h.accounts.some((a) => a.suggested && !a.jellyfin_user)
    ? el("button", { type: "button", class: "btn", onclick: async () => {
      const m = Object.fromEntries(h.accounts.filter((a) => a.suggested && !a.jellyfin_user).map((a) => [a.name, a.suggested]));
      try { await api("/api/import/mapping", { method: "PUT", body: { mapping: m } }); await startJellyfin(); settingSaved(`Matched ${countWords(Object.keys(m).length, "account", "accounts")}`); }
      catch (err) { problem(err.message); }
    } }, icon("users"), "Match accounts with the same name") : null;
  const imported = h.imported ? el("p", { class: "small muted", text: `${h.source}, read ${new Date(h.imported).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}. ${h.accounts.length} ${h.accounts.length === 1 ? "account" : "accounts"}.` }) : null;
  const result = d.import_result ? notice(d.import_result.ok ? "success" : "danger", d.import_result.ok ? "History read" : "The import did not work", d.import_result.message) : null;
  const applyRows = el("ul", { class: "settings-rows" },
    settingRow("Keep applying every hour", withCost("History for films and episodes you do not have yet is applied when they arrive. Inactive: only when you choose Apply now.", "importKeep"),
      sw("im-keep-l", x().import_keep, (on) => save({ import_keep: on })), "im-keep-l"));

  // Not found
  const last = h.last;
  const missing = last && last.unmatched_count ? section("jf-missing", "Not in Jellyfin yet",
    "Either they are not in Jellyfin yet, or Jellyfin has no TMDB, IMDb or TVDB ID for them. With Keep applying on, they are picked up when they arrive.",
    el("div", { class: "table-wrap", "data-stack": true }, el("table", { class: "table" },
      el("caption", { class: "visually-hidden", text: "Films and episodes not in Jellyfin yet" }),
      el("thead", {}, el("tr", {}, ["Film or episode", "Account"].map((t) => el("th", { scope: "col", text: t })))),
      el("tbody", {}, last.unmatched.map((u) => el("tr", {}, el("th", { scope: "row", "data-label": "Film or episode", text: u.title }),
        el("td", { "data-label": "Account", text: u.account })))))),
    last.unmatched_count > last.unmatched.length ? el("p", { class: "small muted", text: `Showing the first ${last.unmatched.length} of ${last.unmatched_count}.` }) : null) : null;

  // User defaults
  const df = jobs.defaults;
  const defaultRows = el("ul", { class: "settings-rows" },
    settingRow("Give every Jellyfin user the defaults", withCost("Every hour, users who have not chosen otherwise get: Live TV opens on the Guide. New users get it too.", "defaults"),
      sw("df-on-l", x().defaults, (on) => save({ defaults: on })), "df-on-l"));

  const plugins = el("div", { class: "stack-4", "aria-busy": "true", id: "jf-plugins-list" }, el("p", { class: "muted", text: "Asking Jellyfin…" }));
  drawJellyfinPlugins(plugins);
  const metadataBox = el("div", { class: "stack-4", "aria-busy": "true" }, el("p", { class: "muted", text: "Loading…" }));
  drawJellyfinMetadata(metadataBox);

  root.removeAttribute("aria-busy");
  root.replaceChildren(...[
    welcome ? notice("success", "Starboard found Jellyfin", "These are all inactive. Activate what you want; you can change them here at any time.") : null,
    top,
    livePlugin ? section("jf-live", "Live TV", "Free channels and guides for Jellyfin's Live TV.",
      notice("info", `Live TV is a plug-in now, and ${livePlugin.state === "enabled" ? "active" : "not active"}`, "Its settings and status are on its own page.",
        el("a", { class: "btn", href: "/settings-plugin.html?id=livetv", text: "Open Live TV's settings" })))
    : section("jf-live", "Live TV", "Free channels and guides for Jellyfin's Live TV: guides refreshed daily, channels only when a list changes.", liveNeeds, liveRows, jfFolderForm, addressForm, el("div", { class: "actions" }, jobRun(lt), runNow("livetv", "Live TV")), liveHelp),
    section("jf-import", "Import watch history", "Move what people watched, and where they stopped, from Plex, Emby or another Jellyfin into this Jellyfin.",
      importForm, result, imported, mapping, matchSame ? el("div", { class: "actions" }, matchSame) : null, applyRows,
      el("div", { class: "actions" }, jobRun(jobs.import), h.accounts.length ? runNow("import", "Apply", "Apply now") : null)),
    missing,
    section("jf-plugins", "Recommended plug-ins", "Skip intros and credits, play statistics, one item for each film with several versions, and Trakt. Installed and set up through Jellyfin, one choice each.", plugins),
    section("jf-metadata", "Pictures and details", "Where Jellyfin keeps the posters, photos and details it saves.", metadataBox),
    section("jf-defaults", "User defaults", null, defaultRows, el("div", { class: "actions" }, jobRun(df), runNow("defaults", "Defaults"))),
    users.length ? section("jf-you", "Your Jellyfin user",
      "The Library shows what this Jellyfin user has watched, and Mark as watched changes it for them.", whose) : null,
  ].filter(Boolean));
}

// Jellyfin's metadata outside its settings folder (DASH-431): new installs have it there already; an install made
// before moves on request, with the password, in a task dialog (Jellyfin stops for a few minutes; nothing is deleted).
async function drawJellyfinMetadata(holder) {
  let d;
  try { d = await api("/api/jellyfin/metadata"); } catch (e) { holder.replaceChildren(notice("danger", "Could not read where Jellyfin keeps them", e.message)); return; }
  holder.removeAttribute("aria-busy");
  if (d.moved) {
    holder.replaceChildren(el("p", { text: "Outside its settings folder, in /metadata (the jellyfin-metadata folder beside its settings). Jellyfin then watches fewer folders, and new files in Films and TV show without a scan." }));
    return;
  }
  if (!d.can_move) {
    holder.replaceChildren(el("p", { class: "small muted", text: `In its settings folder. ${d.why}, so Starboard cannot move them.` }));
    return;
  }
  const go = el("button", { type: "button", class: "btn" }, icon("folder-input"), "Move them out of the settings folder…");
  go.addEventListener("click", async () => {
    const pw = el("input", { class: "input", type: "password", id: "jf-metadata-pw", autocomplete: "current-password" });
    const ok = await confirmDialog({ title: "Move Jellyfin's pictures and details?", confirm: "Move them",
      message: "Jellyfin stops for a few minutes while they move to the jellyfin-metadata folder beside its settings, then starts again. A link stays at the old address, so every picture still shows. Nothing is deleted.",
      fields: [el("div", { class: "field" }, el("label", { for: pw.id, text: "Your Starboard password" }), pw)] });
    if (!ok) return;
    try {
      const r = await api("/api/jellyfin/metadata/move", { method: "POST", body: { password: pw.value } });
      const job = taskJob({ title: "Moving Jellyfin's pictures and details", url: r.job, failedWord: "Stopped here", returnTo: "jf-metadata-h" });
      job.open();
      await job.follow((x) => ({ title: x.title, text: x.text }));
      drawJellyfinMetadata(holder);
    } catch (err) { problem(err.message, go); }
  });
  holder.replaceChildren(
    el("p", { text: "In its settings folder, which Jellyfin watches. On a large library that uses up the computer's folder watches, and new files in Films and TV may not show until a scan." }),
    el("div", { class: "actions" }, go));
}

// Recommended Jellyfin plug-ins (DASH-404): one choice each, installed and set up through Jellyfin's own API. The
// section draws itself again on its own, so a choice never redraws the rest of the page.
const PLUGIN_STATE = { Active: ["Active", "success"], Restart: ["Active after a restart", "warning"], Disabled: ["Deactivated", "muted"],
  Malfunctioned: ["Not working", "danger"], NotSupported: ["Not for this Jellyfin", "danger"], Superseded: ["Replaced by a newer version", "muted"], Superceded: ["Replaced by a newer version", "muted"] };

async function drawJellyfinPlugins(holder, result = null) {
  let d;
  try { d = await api("/api/jellyfin/plugins"); } catch (e) { holder.replaceChildren(notice("danger", "Could not read Jellyfin's plug-ins", e.message)); return; }
  holder.removeAttribute("aria-busy");
  if (!d.connected) {
    holder.replaceChildren(notice("info", d.problem ? "Jellyfin did not answer" : "Add Jellyfin first", d.problem || "Give your Jellyfin app its API key in Manage apps, from Jellyfin's Dashboard, API keys."));
    return;
  }
  const status = el("div", { class: "stack-2" },
    result ? notice(result.ok ? "success" : "danger", result.ok ? "Done" : "Jellyfin did not do it", result.text) : null,
    d.finished?.length ? notice("success", "Set up after the restart", d.finished.join(". ") + ".") : null);
  // Restart where it is needed (DASH-470): followed until Jellyfin answers again, then the section is drawn again
  // with what Starboard finished after the restart, and focus goes to that result.
  const why = "Plug-ins are added and removed when Jellyfin starts. Starboard finishes their set-up after the restart.";
  const restart = !d.restart ? null : d.can_restart
    ? restartNotice({ title: "Jellyfin needs a restart", text: why, ...jellyfinRestart(d.name, async () => {
      await drawJellyfinPlugins(holder, { ok: true, text: `${d.name} restarted.` });
      const result = $(".notice", holder);
      result?.setAttribute("tabindex", "-1");
      return result;
    }) })
    : notice("warning", "Jellyfin needs a restart", `${why} Jellyfin cannot restart itself here: use Restart in its More actions menu in Manage apps.`);
  const groups = d.groups.map((g) => {
    const name = `jf-plugin-${g.id}`;
    const radios = g.choices.map((c) => ({ c, input: el("input", { type: "radio", name, value: c.id, checked: c.id === g.chosen, disabled: !c.available }) }));
    const installed = g.installed.length ? el("div", { class: "stack-1" }, g.installed.map((p) => {
      const [words, tone] = PLUGIN_STATE[p.status] || [p.status || "Installed", "muted"];
      return el("p", { class: "small" }, "Installed: ", el("strong", { text: `${p.name} ${p.version}` }), " ", chip(words, tone));
    })) : el("p", { class: "small muted", text: "Not installed." });
    const apply = el("button", { type: "submit", class: "btn" }, "Apply this choice");
    const form = el("form", { class: "stack-4", novalidate: true, "data-key": g.id },
      el("fieldset", {}, el("legend", { class: "field__label", text: `${g.title}: what to use` }),
        el("div", { class: "option-cards" }, radios.map(({ c, input }) => el("label", { class: "option-card" }, input,
          el("strong", { text: c.package && c.id !== "none" ? `${c.label}: ${c.package}` : c.label }), c.hint ? el("small", { text: c.hint }) : null, c.cost ? el("small", { class: "setting__cost", text: c.cost }) : null)))),
      el("div", { class: "actions" }, apply));
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const picked = radios.find((r) => r.input.checked)?.c.id;
      if (!picked) return;
      apply.disabled = true;
      apply.textContent = "Asking Jellyfin…";
      try {
        const r = await api("/api/jellyfin/plugins", { method: "POST", body: { group: g.id, choice: picked } });
        await drawJellyfinPlugins(holder, { ok: true, text: r.done.join(". ") + "." });
      } catch (err) { await drawJellyfinPlugins(holder, { ok: false, text: err.message }); }
    });
    return el("div", { class: "stack-2" },
      el("h3", { text: g.title }), el("p", { text: g.what }), installed, form,
      g.cost ? el("p", { class: "small muted" }, el("span", { class: "setting__cost", text: g.cost })) : null);
  });
  if (result) announce(result.text);
  holder.replaceChildren(status, restart || "", el("p", { class: "small muted", text: `${d.name} ${d.version}. Starboard installs through Jellyfin's own plug-in catalogue, adding a plug-in's repository when Jellyfin does not have it. Another choice deactivates the old plug-in; nothing is uninstalled.` }), ...groups);
}

// Audiobookshelf ------------------------------------------------------------
// Listening progress from Plex, Jellyfin, Emby or another Audiobookshelf: read it, match each account to an
// Audiobookshelf user, apply. Laid out like Settings, Apps, Jellyfin, Import watch history.

const LISTEN_FROM = [["plex", "A Plex server"], ["jellyfin", "A Jellyfin server"], ["emby", "An Emby server"], ["audiobookshelf", "Another Audiobookshelf"]];

const LISTEN_HINT = {
  plex: "Your Plex token (Plex's help: Finding an authentication token). Only your own account is read, from music libraries with book in their name or that use the Audnexus agent.",
  jellyfin: "An API key from that server's Dashboard, API keys. Every user is read, from audiobooks in a Books library.",
  emby: "An API key from that server's Dashboard, API keys. Every user is read, from audiobooks in a Books library.",
  audiobookshelf: "An admin's API key from that server's Settings, API Keys. Every user is read.",
};

async function startListening() {
  const root = $("#listening-sections");
  let d;
  try { d = await api("/api/listening"); } catch (e) { root.replaceChildren(notice("danger", "Could not load", e.message)); return; }
  const redraw = () => startListening();
  const when = (t) => new Date(t * 1000).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

  // Audiobookshelf itself
  const top = !d.abs
    ? notice("info", "Give Audiobookshelf an admin API key first",
      "Make one in Audiobookshelf (Settings, API Keys, for an admin user) and paste it into Audiobookshelf in Manage apps.",
      el("a", { class: "btn", href: "/settings.html" }, "Manage apps"))
    : d.abs_problem ? notice("danger", "Starboard cannot reach Audiobookshelf", `${d.abs_problem}. Check its address and API key in Manage apps.`,
      el("a", { class: "btn", href: "/settings.html" }, "Manage apps")) : null;

  // Read
  const kind = el("select", { class: "select" }, LISTEN_FROM.map(([v, t]) => el("option", { value: v, text: t })));
  const url = el("input", { class: "input", inputmode: "url", autocomplete: "off" });
  const token = el("input", { class: "input", type: "password", autocomplete: "off" });
  const tokenHint = el("span", {});
  const readError = el("div", { role: "alert" });
  const showHints = () => {
    tokenHint.textContent = LISTEN_HINT[kind.value];
    url.placeholder = { plex: "http://plex:32400", jellyfin: "http://jellyfin:8096", emby: "http://emby:8096", audiobookshelf: "http://audiobookshelf:13378" }[kind.value];
  };
  kind.addEventListener("change", showHints);
  showHints();
  const readButton = el("button", { type: "submit", class: "btn btn--primary", disabled: d.reading }, icon("import"), d.reading ? "Reading…" : "Read the progress");
  const readForm = el("form", { novalidate: true, class: "stack-4" },
    el("div", { class: "form-grid" }, field("Read from", kind, { span: true }), field("Server address", url, { span: true }),
      field("Token or API key", token, { span: true, hint: tokenHint })),
    el("div", { class: "actions" }, readButton), readError);
  const waitForRead = () => { const wait = setInterval(async () => { const now = await api("/api/listening").catch(() => null); if (now && !now.reading) { clearInterval(wait); redraw(); } }, 3000); };
  readForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    readError.replaceChildren();
    try {
      await api("/api/listening/read", { method: "POST", body: { kind: kind.value, url: url.value, token: token.value } });
      toast("Reading the progress. This can take a minute or two.");
      readButton.disabled = true;
      waitForRead();
    } catch (err) { readError.replaceChildren(notice("danger", "Not started", err.message)); }
  });
  if (d.reading) waitForRead();
  const readResult = d.read_result ? notice(d.read_result.ok ? "success" : "danger", d.read_result.ok ? "Progress read" : "Reading did not work", d.read_result.message) : null;
  const imported = d.imported ? el("p", { class: "small muted", text: `${d.source}, read ${when(d.imported)}. ${d.accounts.length} ${d.accounts.length === 1 ? "account" : "accounts"}.` }) : null;

  // Match
  const users = d.abs_users;
  const mapping = d.accounts.length ? accountRows(d.accounts, users, {
    caption: "Accounts and the Audiobookshelf user each one goes to", app: "Audiobookshelf", none: "Do not copy", userOf: (a) => a.abs_user,
    counts: (a) => `${countWords(a.books, "book", "books")}, ${a.finished} finished, ${a.applied} applied`,
    put: (mapping) => api("/api/listening/mapping", { method: "PUT", body: { mapping } }) }) : null;
  const matchSame = d.accounts.some((a) => a.suggested && !a.abs_user)
    ? el("button", { type: "button", class: "btn", onclick: async () => {
      const m = Object.fromEntries(d.accounts.filter((a) => a.suggested && !a.abs_user).map((a) => [a.name, a.suggested]));
      try { await api("/api/listening/mapping", { method: "PUT", body: { mapping: m } }); await redraw(); settingSaved(`Matched ${countWords(Object.keys(m).length, "account", "accounts")}`); }
      catch (err) { problem(err.message); }
    } }, icon("users"), "Match accounts with the same name") : null;

  // Apply
  const keepInput = el("input", { type: "checkbox", role: "switch", "aria-labelledby": "ls-keep-l", checked: config.extras.listening_keep });
  keepInput.addEventListener("change", async () => {
    try { await saveGeneral({ extras: { listening_keep: keepInput.checked } }, true); }
    catch (err) { keepInput.checked = !keepInput.checked; problem(err.message); }
  });
  const applyRows = el("ul", { class: "settings-rows" },
    settingRow("Keep applying every hour", withCost("Books that are not in Audiobookshelf yet get their progress once they are scanned in. Inactive: only when you choose Apply now.", "listeningKeep"),
      el("label", { class: "switch" }, keepInput), "ls-keep-l"));
  const applyNow = d.accounts.length ? el("button", { type: "button", class: "btn", disabled: !d.abs || d.job.state === "running", onclick: async (e) => {
    e.currentTarget.disabled = true;
    try {
      await api("/api/extras/listening/run", { method: "POST" });
      toast("Applying listening progress");
      const wait = setInterval(async () => { const now = await api("/api/listening").catch(() => null); if (now && now.job.state !== "running") { clearInterval(wait); redraw(); } }, 3000);
    } catch (err) { problem(err.message); }
  } }, icon("play"), "Apply now") : null;
  const rules = el("p", { class: "help-links" }, helpButton("How Starboard copies progress", { body: [
      el("p", { text: "Each book is matched by its ASIN, then its ISBN, then its title and author, then its folder. A book in several files becomes one position: the earlier files plus the place in the current one. If the two copies differ in length, the position is scaled to fit." }),
      el("p", { text: "Progress a person already has in Audiobookshelf is never changed, and each book is copied once." }),
      el("p", { text: "Audiobookshelf keeps progress per person. Starboard uses the admin key to make a key that acts as each person, writes their progress with it, and deletes it straight away. Any key left behind stops working after 15 minutes." }),
    ] }));

  // Not found
  const last = d.last;
  const missing = last && last.unmatched_count ? section("ls-missing", "Books not found in Audiobookshelf",
    "Either they are not scanned in yet, or their details differ. Check the title, author or ASIN in Audiobookshelf; the next Apply picks them up.",
    el("div", { class: "table-wrap", "data-stack": true }, el("table", { class: "table" },
      el("caption", { class: "visually-hidden", text: "Books not found in Audiobookshelf" }),
      el("thead", {}, el("tr", {}, ["Book", "Author", "Account"].map((t) => el("th", { scope: "col", text: t })))),
      el("tbody", {}, last.unmatched.map((u) => el("tr", {}, el("th", { scope: "row", "data-label": "Book", text: u.title }),
        el("td", { "data-label": "Author", text: u.author || "Unknown" }), el("td", { "data-label": "Account", text: u.account })))))),
    last.unmatched_count > last.unmatched.length ? el("p", { class: "small muted", text: `Showing the first ${last.unmatched.length} of ${last.unmatched_count}.` }) : null) : null;

  root.removeAttribute("aria-busy");
  root.replaceChildren(...[
    top,
    section("ls-copy", "Copy listening progress", "Where everyone is in each audiobook, and what they finished, into Audiobookshelf. Copy it once Audiobookshelf has scanned in your books.",
      readForm, readResult, imported, mapping, matchSame ? el("div", { class: "actions" }, matchSame) : null, applyRows,
      el("div", { class: "actions" }, jobRun(d.job), applyNow), rules),
    missing,
  ].filter(Boolean));
}
