// The set-up pages: the set-up guide, the upgrade guide, Install apps, Settings, Apps, Your install and Settings,
// Updates (updating Starboard and its apps).

// One section of a settings page: an h2, a one-line description and its content.
function pageSection(id, title, description, ...content) { return section(id, title, description, ...content); }

// What Starboard can access: a row per kind of access, with a switch, a link or the installer command.
async function renderAccess() {
  const list = $("#access-rows");
  let items;
  try { items = (await api("/api/access")).items; } catch (e) { list.replaceChildren(el("li", { class: "setting", text: e.message })); return; }
  // On or off as an icon beside the name: a tick or an empty ring (never colour alone), with the word in
  // hidden text and in the tooltip. Rows with a switch show their state in the switch itself.
  const stateIcon = (on) => el("span", { class: "status-icon", "data-tone": on ? "success" : "muted", tabindex: "0", "data-tooltip": on ? "On" : "Off" },
    icon(on ? "circle-check" : "circle"), el("span", { class: "visually-hidden", text: on ? ", active" : ", inactive" }));
  const row = (a, control, withIcon) => {
    const labelId = `acc-${a.key}-l`;
    return el("li", { class: "setting" },
      el("div", { class: "setting__text" },
        el("span", { class: "setting__label", id: labelId }, a.title, withIcon ? stateIcon(a.on) : null),
        el("span", { class: "setting__hint" }, a.what, a.cost ? el("span", { class: "setting__cost", text: `Costs about: ${a.cost[0].toLowerCase()}${a.cost.slice(1)}` }) : null)),
      el("div", { class: "setting__control" }, control));
  };
  list.replaceChildren(...items.map((a) => {
    if (a.change === "setting" && a.setting && a.setting !== "update_check") {
      const input = el("input", { type: "checkbox", role: "switch", "aria-labelledby": `acc-${a.key}-l`, checked: config[a.setting] });
      input.addEventListener("change", async () => {
        try { await saveGeneral({ [a.setting]: input.checked }, true); }
        catch (err) { input.checked = !input.checked; problem(err.message); }
      });
      return row(a, el("label", { class: "switch" }, input), false);
    }
    if (a.change === "installer") {
      const command = `./install.sh ${a.on ? a.off_flag : a.on_flag}`;
      return row(a, el("div", { class: "access-change" },
        el("span", { class: "small", text: a.on ? "To deactivate it, run on the server:" : "To activate it, run on the server:" }),
        el("div", { class: "command" }, el("code", { class: "code-block", text: command }), copyButton(command, `the command for ${a.title}`))), true);
    }
    if (a.change === "readme") {
      return row(a, el("span", { class: "small access-change", text: "Set up by hand: read Backup and restore in the README." }), true);
    }
    const where = a.link?.startsWith("#") ? null : a.link;
    return row(a, where ? el("a", { class: "btn", href: where }, a.change === "apps" ? "Manage apps" : "Change it", el("span", { class: "visually-hidden", text: ` for ${a.title}` }))
      : el("span", { class: "small access-change", text: "Use this section's switch" }), true);
  }));
  list.removeAttribute("aria-busy");
  if (location.hash === "#access") $("#access").scrollIntoView();
}

// One wizard step's content: { nodes, save }. Shared by the set-up guide and the upgrade guide.
async function stepContent(id, root, step = {}) {
  const types = (t) => config.services.filter((s) => s.enabled !== false && t.includes(s.type));
  if (id.startsWith("bring-") && typeof bringInStep === "function") return bringInStep(id, { inWizard: true, media: guideMemory().media || "", go: step.goTo });
  let nodes = [];
  let save = async () => true;
  if (id === "install") {
    const have = el("input", { type: "radio", name: "install", checked: true });
    const fresh = el("input", { type: "radio", name: "install" });
    nodes = [el("div", { class: "option-cards" },
      el("label", { class: "option-card" }, have, el("strong", { text: "Use the apps I have" }), el("small", { text: "Starboard finds them on the next step." })),
      el("label", { class: "option-card" }, fresh, el("strong", { text: "Install apps for me" }),
        el("small", { text: "Choose groups such as Movies, TV, Ebooks and Audiobooks. Starboard writes the files, shows them, and starts the apps when you say. It also offers to bring over what your current apps have." })))];
    save = async () => {
      if (!fresh.checked) return true;
      location.href = "/install-apps.html?from=guide";
      return false;
    };
  } else if (id === "place") {
    // Where you are (DASH-259): the same list, order and help as the terminal set-up and the Run first script
    // (starboard/places.py). A list moved through with the arrow keys and chosen with Enter; typing letters jumps.
    const data = await api("/api/setup/place");
    const want = guideMemory().tz || data.tz;
    const select = el("select", { class: "select", id: "guide-place" }, data.locations.map((p) =>
      el("option", { value: p.tz, text: `${p.title}${p.tz === want ? (guideMemory().tz ? " (your last answer)" : " (recommended)") : ""} · ${p.tz}`, selected: p.tz === want })));
    nodes = [field("Where is this computer?", select, { span: true,
        hint: "Its clock is set to your time zone, so download hours, schedules and the log use your time. Your keyboard is suggested from it next." }),
      el("p", { class: "help-links" }, helpButton("Which one is right for me?", { back: "Back to set-up", body: [
        el("p", { text: "Choose the country, or the part of a large country, this computer is in. It sets the time zone, which download hours, schedules, the log and the apps use, and suggests the keyboard on the next step." }),
        el("p", { text: "A place that is not in the list: choose Other, Coordinated Universal Time, or keep the time zone the computer has." })] }))];
    save = async () => {
      const p = data.locations.find((x) => x.tz === select.value) || data.locations[0];
      remember({ tz: p.tz, placeKeyboard: p.keyboard, keyboard: p.tz === guideMemory().tz ? guideMemory().keyboard : "" });
      return true;
    };
  } else if (id === "keyboard") {
    // Your keyboard (DASH-259) with where the symbols are when the layout set does not match it (DASH-112).
    const data = await api("/api/setup/place");
    const m = guideMemory();
    const found = data.found?.keyboard || "";
    const want = m.keyboard || (found && found !== "us" ? found : "") || ((m.tz || data.tz) === data.tz ? data.keyboard : m.placeKeyboard) || data.keyboard;
    const boards = [...data.keyboards].sort((a, b) => (b.id === want) - (a.id === want));
    const select = el("select", { class: "select", id: "guide-keyboard" }, boards.map((b) =>
      el("option", { value: b.id, text: b.title + (b.id === want ? (m.keyboard ? " (your last answer)" : " (recommended)") : ""), selected: b.id === want })));
    const where = el("div", { class: "stack-1", id: "guide-symbols", "aria-live": "polite" });
    const showSymbols = () => {
      const b = data.keyboards.find((x) => x.id === select.value);
      where.replaceChildren(...(b?.symbols?.length
        ? [el("p", { class: "small", text: b.symbols[0] }), el("ul", { class: "small" }, b.symbols.slice(1).map((line) => el("li", { text: line }))),
          el("p", { class: "small muted", text: data.set_it_right })]
        : [el("p", { class: "small muted", text: "Once the right layout is set, every key types what is marked on it." })]));
    };
    select.addEventListener("change", showSymbols);
    showSymbols();
    nodes = [field("Which keyboard do you have?", select, { span: true,
        hint: "The keyboard plugged into this computer, by the language printed on its keys. The UK one has £ above 3 and # ~ beside Enter." }),
      el("details", { class: "disclosure" }, el("summary", { text: "A symbol such as | or \\ does not come out as marked" }), el("div", { class: "disclosure__body" }, where))];
    save = async () => {
      const r = await api("/api/setup/place", { method: "POST", body: { tz: guideMemory().tz || data.tz, keyboard: select.value } });
      remember({ keyboard: select.value, hostTz: r.change.timezone, hostKb: r.change.keyboard });
      if (r.change.timezone || r.change.keyboard) await saveHost();
      return true;
    };
  } else if (id === "cleanup") {
    // Clean up (DASH-77), at the end of all three jobs. Moving to the holding folder deletes nothing: only the person
    // deletes for good, in System, Clean up (owner rule). The same words and answers as the terminal set-up.
    const found = await api("/api/cleanup");
    const items = found.left_over.filter((i) => i.movable);
    const name = `cleanup-${Date.now()}`;
    const choices = [{ value: "hold", title: "Move them to the holding folder (recommended)", about: "Nothing is deleted. Put each back, or delete it for good, in System, Clean up." },
      { value: "leave", title: "Leave them where they are", about: "System, Clean up lists them, to do later." }].map(({ value, title, about }, n) =>
      ({ value, input: el("input", { type: "radio", name, value, checked: n === 0 }), title, about }));
    nodes = [el("p", { text: `${items.length} ${items.length === 1 ? "thing" : "things"} left over, ${formatBytes(items.reduce((t, i) => t + i.size, 0))} in all:` }),
      el("ul", { class: "small" }, items.slice(0, 8).map((i) => el("li", { text: `${i.what}, ${formatBytes(i.size)}${i.at_least ? " or more" : ""}` }))),
      items.length > 8 ? el("p", { class: "small muted", text: `${items.length - 8} more, listed in System, Clean up.` }) : null,
      el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Clean up what is left over?" }),
        el("div", { class: "option-cards" }, choices.map((c) => el("label", { class: "option-card" }, c.input, el("strong", { text: c.title }), el("small", { text: c.about }))))),
      el("p", { class: "help-links" }, helpButton("What is this?", { back: "Back to set-up", body: [
        el("p", { text: "What earlier versions, removed plug-ins and old backups left behind. Moving them to the holding folder deletes nothing: each can be put back, or deleted for good by you, in System, Clean up. Starboard never deletes them by itself." })] }))];
    save = async () => {
      if (choices[0].input.checked && items.length) {
        const r = await api("/api/cleanup/hold", { method: "POST", body: { ids: items.map((i) => i.id) } });
        toast(`Moved ${r.moved.length} to the holding folder. Delete them for good, when you are sure, in System, Clean up.`);
      }
      return true;
    };
  } else if (id === "how-to-start") {  // not "start": that is Install apps' Start the apps step, drawn by install.js
    // How to start: the same question, answers and help as the terminal set-up (starboard/start.py).
    const found = await api("/api/setup/start");
    const name = `start-${Date.now()}`;
    const chosen = guideMemory().start || found.recommended;
    const radios = found.choices.map((c) => ({ c, input: el("input", { type: "radio", name, value: c.key, checked: c.key === chosen }) }));
    const file = el("input", { type: "file", class: "input", accept: ".json,application/json", id: "guide-backup-file" });
    const password = el("input", { type: "password", class: "input", autocomplete: "current-password", id: "guide-backup-password" });
    // Two kinds of backup (DASH-260): Settings only, a file from this browser; Full without media, a file on this
    // computer's disks, found with the location picker and opened with its own password.
    const kindName = `restore-kind-${Date.now()}`;
    const kinds = [["full", "Full without media", "Starboard, its plug-ins and every app's settings, from a .starboard file on this computer."],
      ["settings", "Settings only", "Starboard's settings from a .json file you downloaded."]].map(([value, title, about]) =>
      ({ value, input: el("input", { type: "radio", name: kindName, value, checked: value === "full" }), title, about }));
    const where = locationPicker({ id: "guide-full-folder", label: "Folder with your full backups", app: "host", setting: "backups",
      hint: "Such as /mnt/pool/backups/starboard on the disk you kept." });
    const fullList = el("div", { class: "stack-2", "aria-live": "polite" });
    const backupPassword = el("input", { type: "password", class: "input", autocomplete: "off", id: "guide-full-password" });
    let fullChoice = null;
    const showFound = async () => {
      fullList.replaceChildren(el("p", { class: "small muted", text: "Looking…" }));
      try {
        const r = await api(`/api/backup/full/found?folder=${encodeURIComponent(where.input.value.trim())}`);
        if (!r.found.length) { fullChoice = null; fullList.replaceChildren(emptyState("No full backups in this folder", "Choose the folder they are in with Browse.")); return; }
        const group = `full-pick-${Date.now()}`;
        fullList.replaceChildren(el("fieldset", {}, el("legend", { class: "field__label", text: "Which backup" }),
          el("div", { class: "option-cards" }, r.found.slice(0, 5).map((b, n) => {
            const input = el("input", { type: "radio", name: group, value: b.path, checked: n === 0 });
            input.addEventListener("change", () => { if (input.checked) fullChoice = b.path; });
            return el("label", { class: "option-card" }, input, el("strong", { text: formatDate(b.created, true) + (n === 0 ? " (newest)" : "") }),
              el("small", { text: [formatBytes(b.size), `${b.apps.length} apps: ${b.apps.join(", ")}`, b.pictures ? "with your pictures" : "without pictures"].join(" · ") }));
          }))));
        fullChoice = r.found[0].path;
      } catch (e) { fullChoice = null; fullList.replaceChildren(notice("danger", "Could not read the folder", e.message)); }
    };
    where.input.addEventListener("change", showFound);
    const fullBox = el("div", { class: "form-stack" }, where.node, fullList,
      field("The backup's password", backupPassword, { required: true, hint: "The one chosen when the backup was made.", span: true }));
    const fileBox = el("div", { class: "form-stack", hidden: true },
      field("Backup file", filePicker(file), { required: true, hint: "From Settings, General, Backup and restore, Settings only, Download a backup.", span: true }));
    kinds.forEach(({ value, input }) => input.addEventListener("change", () => { if (input.checked) { fullBox.hidden = value !== "full"; fileBox.hidden = value !== "settings"; } }));
    const restoreBox = el("div", { class: "form-stack", hidden: chosen !== "restore" },
      el("fieldset", {}, el("legend", { class: "field__label", text: "What kind of backup" }),
        el("div", { class: "option-cards" }, kinds.map((k) => el("label", { class: "option-card" }, k.input, el("strong", { text: k.title }), el("small", { text: k.about }))))),
      fullBox, fileBox,
      field("Your Starboard password", password, { required: true, hint: "The one you chose. Starboard checks it before it restores.", span: true }));
    setTimeout(() => { if (where.input.value) showFound(); }, 0);
    radios.forEach(({ input }) => input.addEventListener("change", () => { restoreBox.hidden = input.value !== "restore" || !input.checked; }));
    nodes = [found.found.length ? notice("info", "Found on this computer", found.found.join(", ")) : null,
      el("fieldset", {}, el("legend", { class: "visually-hidden", text: "How to start" }),
        el("div", { class: "option-cards" }, radios.map(({ c, input }) => el("label", { class: "option-card" }, input,
          el("strong", { text: c.title + (c.recommended ? " (recommended)" : "") }), el("small", { text: c.about }))))),
      restoreBox,
      el("p", { class: "help-links" }, helpButton("Which one is right for me?", { back: "Back to set-up",
        body: found.choices.map((c) => el("p", {}, el("strong", { text: `${c.title}: ` }), c.help)) }))];
    save = async () => {
      const key = radios.find((r) => r.input.checked)?.input.value || found.recommended;
      if (key === "restore" && kinds.find((k) => k.input.checked)?.value === "full") {
        if (!fullChoice) { showProblemNear(where.input, "Choose the folder with your full backups."); return false; }
        if (backupPassword.value.length < 10) { showProblemNear(backupPassword, "Enter the backup's password."); return false; }
        announce("Restoring: this takes a few minutes for the apps' settings.");
        let done;
        try { done = await api("/api/backup/full/restore", { method: "POST", body: { file: fullChoice, backup_password: backupPassword.value, password: password.value } }); }
        catch (e) { showProblemNear(/backup|password does not open/i.test(e.message) ? backupPassword : password, e.message); return false; }
        config = done.config;
        announce(`Restored: ${done.apps} apps and the settings of ${done.folders.length} apps. Next, where your media is, then the apps start.`);
        remember({ restoreInstall: done.install || null, start: key });
        return true;
      }
      if (key === "restore") {
        if (!file.files.length) { showProblemNear(file, "Choose the backup file."); return false; }
        let backup;
        try { backup = JSON.parse(await file.files[0].text()); } catch { showProblemNear(file, "That file is not a Starboard backup."); return false; }
        const done = await api("/api/backup/restore", { method: "POST", body: { backup, password: password.value } });
        config = done.config;
        announce(`Restored: ${done.apps} apps, with your categories, design and alerts.`);
        // DASH-268: the backup's apps are not on this computer: Storage, the VPN's secrets, then Check bring them back.
        remember({ restoreInstall: done.install || null });
      }
      remember({ start: key });
      return true;
    };
  } else if (id === "where") {
    // Storage: the main disk, a separate disk or a pool; the folder is made when the apps start. As the terminal.
    const found = await api("/api/setup/storage");
    const name = `where-${Date.now()}`;
    const mem = guideMemory();
    const chosen = mem.where || found.recommended;
    const folder = el("input", { class: "input", spellcheck: "false", autocomplete: "off", id: "guide-media-folder",
      value: mem.media || (found.choices.find((c) => c.key === chosen) || found.choices[0]).folder });
    const radios = found.choices.map((c) => ({ c, input: el("input", { type: "radio", name, value: c.key, checked: c.key === chosen }) }));
    radios.forEach(({ c, input }) => input.addEventListener("change", () => { if (input.checked) folder.value = c.folder; }));
    nodes = [el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Where your media goes" }),
      el("div", { class: "option-cards" }, radios.map(({ c, input }) => el("label", { class: "option-card" }, input,
        el("strong", { text: c.title + (c.recommended ? " (recommended)" : "") }), el("small", { text: c.about }))))),
      folderField({ input: folder, label: "Media folder", required: true, hint: "Made for you when the apps start. Enter it, or choose it with Browse." }).node,
      el("p", { class: "small muted", text: found.help })];
    save = async () => {
      const picked = radios.find((r) => r.input.checked)?.c || found.choices[0];
      if (picked.key === "pool" && !picked.ready) {
        showProblemNear(folder, "The pool helper is not set up yet. Choose another place for now, and make the pool later on System, Storage, Pool.");
        return false;
      }
      remember({ where: picked.key, media: folder.value.trim(), at: "after-apps" });
      await saveHost();
      // DASH-269: Install apps' steps follow in this wizard, with the media folder chosen here (no Folders step).
      if (typeof installFlow !== "function") { location.href = `/install-apps.html?from=guide&media=${encodeURIComponent(folder.value.trim())}`; return false; }
      document.dispatchEvent(new CustomEvent("guide-media", { detail: folder.value.trim() }));
      return true;
    };
  } else if (id === "drives") {
    // Your drives (DASH-87, DASH-271): the terminal set-up's question. The drives are chosen on System, Storage, Pool,
    // where the pool helper makes each change; coming back, the guide carries on from the next step.
    let pool = {};
    try { pool = await api("/api/pool"); } catch { /* shown as no drives */ }
    const drives = pool.drives || [];
    const inPool = drives.filter((d) => d.use === "pool");
    const free = drives.filter((d) => d.use === "free");
    const count = (n, one, many) => `${n} ${n === 1 ? one : many}`;
    const name = `drives-${Date.now()}`;
    const yes = el("input", { type: "radio", name, value: "yes", checked: true });
    const no = el("input", { type: "radio", name, value: "no" });
    nodes = [
      inPool.length ? notice("success", `The pool is at ${pool.pool || "/mnt/pool"}`, `With ${count(inPool.length, "disk", "disks")}.`) : null,
      free.length
        ? el("p", { text: `Starboard found ${count(free.length, "disk", "disks")} besides the system disk and any disk in use.` })
        : notice("info", "There is no other disk to add", "Add disks later on System, Storage, Pool."),
      free.length ? el("fieldset", {}, el("legend", { class: "h3", text: inPool.length ? "Add disks to the pool now?" : "Make a pool from your disks now?" }),
        el("div", { class: "option-cards" },
          el("label", { class: "option-card" }, yes, el("strong", { text: "Yes (recommended)" }), el("small", { text: "Choose the disks on System, Storage, Pool, then come back to the set-up." })),
          el("label", { class: "option-card" }, no, el("strong", { text: "No: later, on System, Storage, Pool" }), el("small", { text: "The set-up carries on." })))) : null,
    ].filter(Boolean);
    save = async () => {
      if (!free.length || !yes.checked) return true;
      remember({ at: "after-drives" });
      location.href = "/system-pool.html?from=guide";
      return false;
    };
  } else if (id === "storage") {
    // The Storage page: the same words and answers as the terminal set-up (web/setup-answers.json, DASH-271).
    const p = config.performance;
    const w = (await setupWords()).storage_page;
    const radios = w.usage.map((c) => ({ v: c.value, input: el("input", { type: "radio", name: "usage-every", value: c.value, checked: p.usage_every === c.value }), t: c.label }));
    const refresh = el("select", { class: "select", id: "guide-st-refresh" }, w.refresh.map((c) => el("option", { value: String(c.value), text: c.label, selected: Number(c.value) === p.storage_refresh })));
    const daily = el("input", { type: "checkbox", checked: p.space_log !== false });
    nodes = [
      el("fieldset", { class: "stack-2" }, el("legend", { class: "h3", text: w.usage_question }),
        el("p", { class: "small muted", text: COSTS.usage }),
        el("div", { class: "option-cards" }, radios.map((r) => el("label", { class: "option-card" }, r.input, el("strong", { text: r.t }))))),
      field(w.refresh_question, refresh, { hint: w.refresh_hint }),
      el("label", { class: "check" }, daily, el("span", { class: "check__text" }, el("strong", { text: w.daily_question }),
        el("span", { class: "check__hint", text: w.daily_hint }))),
    ];
    save = async () => {
      const picked = radios.find((r) => r.input.checked);
      await saveGeneral({ performance: { usage_every: picked ? picked.v : "ask", storage_refresh: Number(refresh.value), space_log: daily.checked } });
      return true;
    };
  } else if (id === "apps") {
    const finder = await appFinder();
    nodes = [finder.box];
    save = async () => (finder.add && finder.ticked() ? !!(await finder.add()) : true);  // nothing ticked: just go on
  } else if (id === "keys") {
    // Starboard reads each key from the app's own files first (owner, 10 November 2026: nothing to type during
    // set-up). A box shows only for an app whose key it could not read.
    let read = { found: [], missing: [] };
    try { read = await api("/api/services/read-keys", { method: "POST", body: {} }); config = read.config; } catch { /* the boxes below still work */ }
    const rows = types(Object.keys(KEY_PLACE)).filter((s) => !s.has_api_key).map((s) => {
      const input = el("input", { class: "input", type: "password", autocomplete: "off", "aria-label": `API key for ${s.name}` });
      return { s, input, node: field(`${s.name} API key`, input, { hint: `In ${s.name}: ${KEY_PLACE[s.type]}.`, span: true }) };
    });
    const got = read.found.length ? notice("success", `Starboard has ${read.found.length === 1 ? "the key" : "the keys"} for ${read.found.join(", ")}`,
      read.found.length === 1 ? "It read it from the app's own settings, so there is nothing to type for it." : "It read them from each app's own settings, so there is nothing to type for them.") : null;
    nodes = rows.length
      ? [got, el("p", { text: `Starboard could not read ${rows.length === 1 ? "this key" : "these keys"} itself, so ${rows.length === 1 ? "it is" : "they are"} asked for here.` }),
        el("div", { class: "form-stack" }, rows.map((r) => r.node)), el("p", { class: "small muted", text: "Leave a field empty to add that key later in Manage apps." })].filter(Boolean)
      : [got || notice("success", "Starboard has every key it needs", "There is nothing to enter here.")];
    save = async () => {
      for (const r of rows.filter((x) => x.input.value.trim())) {
        const saved = await api("/api/services", { method: "POST", body: serviceBody(r.s, { api_key: r.input.value.trim() }) });
        config = saved.config;
      }
      return true;
    };
  } else if (id === "jellyfin") {
    const box = (key, label, hint) => {
      const input = el("input", { type: "checkbox", checked: !!config.extras[key] });
      return { key, input, node: el("label", { class: "check" }, input, el("span", { class: "check__text" }, el("strong", { text: label }), el("span", { class: "check__hint", text: hint }))) };
    };
    const picks = [box("livetv", "Live TV channels and guide", "Free channels for Jellyfin's Live TV, with guides. Needs Jellyfin's Live TV folder (./install.sh asks)."),
      box("import_keep", "Bring in watch history", "From Plex, Emby or another Jellyfin. You choose where from in Settings, Apps, Jellyfin."),
      box("defaults", "Defaults for every user", "Live TV opens on the Guide for everyone who has not chosen otherwise.")];
    // DASH-399: Audio description, unticked, in the same words as the terminal set-up (web/setup-answers.json).
    const ad = (await setupWords()).audio_description;
    picks.push(box("audio_description", ad.label, ad.hint));
    nodes = [el("div", { class: "switch-list" }, picks.map((x) => x.node))];
    save = async () => {
      await saveGeneral({ extras: Object.fromEntries(picks.map((x) => [x.key, x.input.checked])) });
      if (picks[0].input.checked && !config.livetv_ready) {
        const stack = await api("/api/stack");
        remember({ livetv: `${stack.defaults.config_dir}/jellyfin/iptv` });
        await saveHost();
      }
      return true;
    };
  } else if (id === "hours") {
    const on = el("input", { type: "checkbox", checked: config.download_hours.enabled });
    const hour = (v) => el("select", { class: "select" }, Array.from({ length: 24 }, (_, h) => el("option", { value: String(h), text: `${String(h).padStart(2, "0")}:00`, selected: h === v })));
    const start = hour(config.download_hours.start);
    const end = hour(config.download_hours.end);
    nodes = [el("label", { class: "check" }, on, el("span", { class: "check__text" }, el("strong", { text: "Yes, only download between" }))),
      el("div", { class: "form-grid" }, field("From", start), field("Until", end))];
    save = async () => { await saveGeneral({ download_hours: { enabled: on.checked, start: Number(start.value), end: Number(end.value) } }); return true; };
  } else if (id === "updates") {
    // DASH-417, DASH-422: which parts may update by themselves: Reelix only when it is being installed, Jellyfin's
    // plug-ins only with Jellyfin. Each deactivated unless chosen; the same words and order as the terminal set-up
    // (web/setup-answers.json, terminal_setup.update_parts).
    const w = (await setupWords()).updates;
    const box = (key, label, hint) => {
      const input = el("input", { type: "checkbox", checked: !!config[key] });
      return { key, input, node: el("label", { class: "check" }, input, el("span", { class: "check__text" }, el("strong", { text: label }), el("span", { class: "check__hint", text: hint }))) };
    };
    const picks = w.parts.filter((p) => p.when === "always" || (step.has || {})[p.when]).map((p) => box(p.key, p.label, p.hint));
    nodes = [el("p", { text: w.intro }), el("p", { class: "small muted", text: w.later }),
      el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Install updates automatically" }), el("div", { class: "switch-list" }, picks.map((x) => x.node)))];
    save = async () => { await saveGeneral(Object.fromEntries(picks.map((x) => [x.key, x.input.checked]))); return true; };
  } else if (id === "alerts") {
    const kinds = [["", "Not now", "No alerts. Starboard does not watch in the background."], ["ntfy", "ntfy", "A free push service with a phone app; you choose a private topic."],
      ["gotify", "Gotify", "Your own push server."], ["webhook", "A webhook", "Starboard posts JSON to an address you choose."]];
    const name = `alert-${Date.now()}`;
    const radios = kinds.map(([v, t, h]) => {
      const input = el("input", { type: "radio", name, value: v, checked: (config.watch.enabled ? config.watch.channel.kind : "") === v });
      return el("label", { class: "option-card" }, input, el("strong", { text: t }), el("small", { text: h }));
    });
    const url = el("input", { class: "input", inputmode: "url", autocomplete: "off", value: config.watch.channel.url || "", placeholder: "https://ntfy.sh/a-long-private-name" });
    const token = el("input", { class: "input", type: "password", autocomplete: "off" });
    const health = el("input", { type: "checkbox", checked: guideMemory().health !== false });
    nodes = [el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Where alerts go" }), el("div", { class: "option-cards" }, radios)),
      el("div", { class: "form-grid" }, field("Address", url, { span: true }), field("Token (if it needs one)", token, { span: true })),
      el("label", { class: "check" }, health, el("span", { class: "check__text" }, el("strong", { text: "Check each disk's health every 30 minutes" }),
        el("span", { class: "check__hint", text: "A small script reads each disk's health report as root, so Starboard can warn you before a disk fails. It is set up on the server with one command at the end." })))];
    // A restore brought its alerts back: only disk health is asked, as in the terminal (DASH-265).
    const restored = (guideMemory().start || "new") === "restore";
    if (restored) nodes = nodes.slice(2);
    save = async () => {
      const kind = root.querySelector(`input[name="${name}"]:checked`)?.value || "";
      if (!restored) await saveGeneral({ watch: kind ? { enabled: true, channel: { kind, url: url.value, token: token.value } } : { enabled: false } });
      remember({ health: health.checked });
      await saveHost();
      return true;
    };
  } else if (id === "movehow") {
    // DASH-266: the same words as the terminal set-up (web/setup-answers.json).
    const w = (await setupWords()).move;
    const name = `movehow-${Date.now()}`;
    const into = guideMemory().moveInto !== false;
    nodes = [el("fieldset", {}, el("legend", { class: "visually-hidden", text: "What happens to them" }), el("div", { class: "option-cards" },
      [["into", w.into, w.into_about, into], ["keep", w.keep, w.keep_about, !into]].map(([v, t, about, on]) => el("label", { class: "option-card" },
        el("input", { type: "radio", name, value: v, checked: on }), el("strong", { text: t }), el("small", { text: about })))))];
    save = async () => { remember({ moveInto: root.querySelector(`input[name="${name}"]:checked`)?.value === "into" }); return true; };
  } else if (id === "move") {
    // DASH-266: the move itself, the same section as Settings, Your install: move into Reelix, then Starboard runs them.
    nodes = [takeoverSection()];
  } else if (id === "docker") {
    // DASH-139, DASH-267: the same words as the terminal set-up (web/setup-answers.json). For a move, Yes is
    // recommended, because the move needs it; for a new install, No, with what that means.
    const w = (await setupWords()).docker;
    const move = (guideMemory().start || "new") !== "new";
    const name = `docker-${Date.now()}`;
    const chosen = guideMemory().docker;
    const cards = (move ? [["yes", w.yes, true], ["no", w.no, false]] : [["no", w.no, true], ["yes", w.yes, false]]).map(([v, t, rec]) =>
      el("label", { class: "option-card" }, el("input", { type: "radio", name, value: v, checked: chosen === undefined ? rec : (chosen ? v === "yes" : v === "no") }),
        el("strong", { text: t + (rec ? " (recommended)" : "") })));
    nodes = [el("p", { text: w.intro }), el("p", { text: move ? w.move : w.without }),
      el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Docker access" }), el("div", { class: "option-cards" }, cards))];
    save = async () => {
      const yes = root.querySelector(`input[name="${name}"]:checked`)?.value === "yes";
      remember({ docker: yes });
      await saveHost();
      return true;
    };
  } else if (id === "preset") {
    const name = `preset-${Date.now()}`;
    // The recommended preset at the top and marked, as in the terminal set-up.
    const rec = config.preset_recommended || "balanced";
    const order = [rec, ...["small", "balanced", "everything"].filter((k) => k !== rec)];
    const current = config.performance.preset === "custom" ? rec : config.performance.preset;
    const radios = order.map((k) => el("label", { class: "option-card" },
      el("input", { type: "radio", name, value: k, checked: current === k }),
      el("strong", { text: config.presets[k] + (k === rec ? " (recommended)" : "") }), el("small", { text: config.preset_about[k] })));
    nodes = [el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Preset" }), el("div", { class: "option-cards" }, radios))];
    save = async () => { await saveGeneral({ preset: root.querySelector(`input[name="${name}"]:checked`).value }); return true; };
  } else if (id === "shadows") {
    // Remove drop shadows (DASH-536): the same words, order and default as the terminal set-up (web/setup-answers.json).
    // The default comes from Starboard (GET /api/shadows/default), the one place that knows it; always asked.
    const w = (await setupWords()).shadows;
    const edition = typeof step.reelix === "function" ? step.reelix() : "";
    const d = await api(`/api/shadows/default${edition ? `?reelix=${encodeURIComponent(edition)}` : ""}`);
    const name = `shadows-${Date.now()}`;
    const wants = config.shadows_answered ? !!config.shadows_off : d.off;
    const lite = d.off;
    const choices = [[true, w.remove, w.remove_about], [false, w.keep, w.keep_about]];
    if (!lite) choices.reverse();  // the recommended answer first
    const cards = choices.map(([value, label, about]) => el("label", { class: "option-card" },
      el("input", { type: "radio", name, value: String(value), checked: wants === value }),
      el("strong", { text: label + (value === lite ? ` (${lite ? w.reason_lite : w.reason_full})` : "") }), el("small", { text: about })));
    nodes = [el("p", { text: w.intro }), el("p", { class: "muted", text: lite ? w.lite : w.full }),
      el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Remove drop shadows" }), el("div", { class: "option-cards" }, cards))];
    save = async () => {
      const off = root.querySelector(`input[name="${name}"]:checked`)?.value === "true";
      await saveGeneral({ shadows_off: off });
      setShadowsOff(off);
      return true;
    };
  } else if (id === "names") {
    nodes = [notice("info", "Starboard answers only to names it knows", "It opens at IP addresses (such as this server's), localhost and this computer's own name. If you open it with another name, such as your own domain, add that name to STARBOARD_ALLOWED_HOSTS in .env on the server and run ./update.sh."),
      el("p", { class: "small muted", text: "This stops a trick called DNS rebinding, where a web page reaches Starboard through a name it controls." })];
  }
  return { nodes, save };
}

// Set-up guide ----------------------------------------------------------------
// What the guide chose, kept while it hands over to Install apps and back (this tab only).
function guideMemory() {
  try { return JSON.parse(sessionStorage.getItem("starboard-guide") || "{}"); } catch { return {}; }
}

function remember(values) {
  try { sessionStorage.setItem("starboard-guide", JSON.stringify({ ...guideMemory(), ...values })); } catch { /* private window */ }
}

// The changes to this computer, for ./install.sh: the same options as the terminal set-up (starboard/start.py).
async function saveHost() {
  const m = guideMemory();
  return api("/api/setup/host", { method: "POST", body: { media: m.media || "", livetv: m.livetv || "", health: m.health !== false, docker: !!m.docker,
    timezone: m.hostTz || "", keyboard: m.hostKb || "" } });
}

function showProblemNear(input, message) {
  problem(message, input);
  input.focus();
}

// The library's wizard: a step list, one question per step, Continue saves it, Back, Skip this step, and Keep the
// defaults and finish at the top. Steps that do not apply (no Jellyfin, no download apps) are left out.
// Opened after the first password, and from Settings, General, Set-up guide.

const KEY_PLACE = {
  sonarr: "Settings, General, API key", radarr: "Settings, General, API key", lidarr: "Settings, General, API key",
  readarr: "Settings, General, API key", prowlarr: "Settings, General, API key", bazarr: "Settings, General, API key",
  qbittorrent: "Options, Web UI, API key (5.2 or later)", sabnzbd: "Config, General, API Key",
  jellyfin: "Dashboard, API keys", seerr: "Settings, General, API key", audiobookshelf: "Settings, API Keys (an admin's key)",
};

async function startGuide() {
  const root = $("#guide");
  root.removeAttribute("aria-busy");
  const types = (t) => config.services.filter((s) => s.enabled !== false && t.includes(s.type));
  const head = $(".page-head");
  if (!$("#guide-finish", head)) {
    head.append(el("div", { class: "actions" }, el("button", { type: "button", class: "btn btn--quiet", id: "guide-finish", onclick: () => go(steps.length - 1) }, "Keep the defaults and finish")));
  }
  const T = await stepTable();
  let steps = [];
  let index = 0;
  let hasDisks = false;
  try { hasDisks = (await api("/api/system")).disks.length > 0; } catch { /* leave the step out */ }
  // DASH-271: Your drives, as in the terminal set-up, when the pool is chosen and the pool helper is ready.
  let poolReady = false;
  try { poolReady = !!(await api("/api/setup/storage")).choices.find((c) => c.key === "pool")?.ready; } catch { /* left out */ }
  // DASH-259: Where you are and Your keyboard come first, unless the Run first script asked both just before; then
  // its answers are saved for the set-up, as the terminal set-up does.
  let placeAsked = true;
  try {
    const place = await api("/api/setup/place");
    if (place.answered) {
      placeAsked = false;
      await api("/api/setup/place", { method: "POST", body: { tz: place.tz, keyboard: place.keyboard } });
    }
  } catch { placeAsked = false; }
  // DASH-77: Clean up comes last in each job when something is left over.
  let leftOver = false;
  try { leftOver = (await api("/api/cleanup")).left_over.some((i) => i.movable); } catch { /* left out */ }
  let dockerAccess = true;  // asked only when Starboard does not have it (DASH-139, DASH-267)
  try { dockerAccess = !!(await api("/api/stack")).docker; } catch { /* not asked */ }
  // DASH-269: a new install runs Install apps' steps here, in this wizard, with one step count (install.js).
  let flow = null;
  // DASH-536: Drop shadows, straight after How much it does. The install it is about to write decides the default, asked
  // of Starboard (the terminal set-up asks the same): the chosen Reelix, "none" without one, nothing for the install that runs now.
  const shadowsStep = () => ({ id: "shadows", ...stepNamed(T, "shadows"), intro: "You can change it later in Display.",
    reelix: () => (flow ? (flow.state.apps.has("reelix") ? flow.state.reelix_edition || "lite" : "none") : "") });
  // DASH-266: a move into Reelix runs the same steps, to put Reelix beside the old apps first, unless Reelix is there.
  let reelixThere = config.services.some((x) => x.icon === "reelix");
  try { reelixThere = reelixThere || !!(await api("/api/reelix/move")).sources?.length; } catch { /* as if not */ }
  const moveInto = () => (guideMemory().start || "new") !== "new" && (guideMemory().start || "new") !== "restore" && guideMemory().moveInto !== false;
  const needFlow = () => ((guideMemory().start || "new") === "new" || (moveInto() && !reelixThere) ||
    ((guideMemory().start || "new") === "restore" && !!guideMemory().restoreInstall)) && typeof installFlow === "function";
  const loadFlow = async () => {
    if (!needFlow()) return;
    if (!flow) {
      try { flow = await installFlow({ chosenMedia: guideMemory().media || "" }); } catch (e) { problem(e.message); return; }
    }
    const install = (guideMemory().start || "new") === "restore" ? guideMemory().restoreInstall : null;
    if (install && !flow.fromBackup) {  // the backup's choice; nothing is asked again but the folder and the VPN's secrets
      flow.fromBackup = true;
      Object.assign(flow.state, { apps: new Set(install.apps || []), install: "custom", installApplied: true,
        config_dir: install.config_dir || flow.state.config_dir, puid: install.puid ?? flow.state.puid, pgid: install.pgid ?? flow.state.pgid,
        tz: install.tz || flow.state.tz, reelix_edition: install.reelix_edition || "lite",
        vpn: { ...(install.vpn || {}), provider: install.vpn?.provider || "", type: install.vpn?.type || "wireguard", countries: install.vpn?.countries || "",
          wireguard_addresses: install.vpn?.wireguard_addresses || "" } });  // a full backup brings the VPN's secrets too
    }
  };
  await loadFlow();
  document.addEventListener("guide-media", (e) => { if (flow) { flow.state.chosenMedia = e.detail; flow.state.data_dir = e.detail; } });

  // The agreed order (DASH-103), the same as the terminal set-up: each thing is decided before what depends on it.
  const build = () => {
    const list = [];
    const start = guideMemory().start || "new";
    if (placeAsked) {
      list.push({ id: "place", ...stepNamed(T, "place"), skippable: false },
        { id: "keyboard", ...stepNamed(T, "keyboard"), skippable: false });
    }
    list.push({ id: "how-to-start", ...stepNamed(T, "start"), skippable: false,
      intro: "A new media server, the apps you already run, or a backup." });
    if (start === "restore") {
      // DASH-265, DASH-268: the backup brought the settings back, so they are not asked again. When its apps are not
      // on this computer, Storage, the VPN (its secrets are not in backups) and Check bring them back.
      const install = guideMemory().restoreInstall;
      if (install && flow) {
        list.push({ id: "where", ...stepNamed(T, "storage"), skippable: false, intro: "The backup's apps go back with their media in this folder." },
          ...flow.before().filter((x) => x.id === "vpn"), ...flow.finish());
      }
      list.push({ id: "alerts", ...stepNamed(T, "alerts"), intro: "Disk health is a change to this computer, so it is asked again." });
      if (leftOver) list.push({ id: "cleanup", ...stepNamed(T, "cleanup"), intro: "What earlier versions, removed plug-ins and old backups left behind." });
      list.push({ id: "finish", ...stepNamed(T, "finish"), skippable: false });
      return list;
    }
    if (start === "new") {
      list.push({ id: "where", ...stepNamed(T, "storage"), skippable: false,
        intro: "Your films, series, books and downloads go in one media folder. Next, choose what your server does." });
      if (guideMemory().where === "pool" && poolReady) {
        list.push({ id: "drives", ...stepNamed(T, "drives"), intro: "A pool joins disks into one folder for your media; each disk stays readable on its own." });
      }
      // DASH-455: media you already have, copied into the media folder chosen just before; optional, in four parts.
      if (typeof bringInSteps === "function" && (!flow || flow.state.apps.has("reelix"))) list.push(...bringInSteps(T));
      if (flow) {
        // The agreed order (DASH-265): what to set up and its questions, How much it does, then Check and Start. No
        // Moving over here (DASH-271): the terminal set-up does not ask it, and the move is its own route.
        list.push(...flow.before().filter((x) => x.id !== "moving"), { id: "preset", ...stepNamed(T, "preset"), intro: "You can change each part in Settings, Performance." }, shadowsStep(),
          ...flow.finish());
      }
    } else {
      list.push({ id: "apps", ...stepNamed(T, "find"),
        intro: "Starboard checked this computer for apps it knows. Tick the ones to add; you can add others by hand later." });
      if (!dockerAccess) list.push({ id: "docker", ...stepNamed(T, "docker"), skippable: false });  // before anything moves
      list.push({ id: "movehow", ...stepNamed(T, "movehow"), skippable: false });
      if (moveInto()) {
        // Reelix beside the old apps first, when it is not there: the same steps as a new install, without sites (the
        // move brings them); How much it does before Check, then the move (DASH-265, DASH-266).
        const beside = flow && !reelixThere;
        if (beside) list.push(...flow.before().filter((x) => !["sites", "moving"].includes(x.id)));
        list.push({ id: "preset", ...stepNamed(T, "preset"), intro: "You can change each part in Settings, Performance." }, shadowsStep());
        if (beside) list.push(...flow.finish());
        list.push({ id: "move", ...stepNamed(T, "move"), skippable: false });
      } else {
        // Keep them as they are: How much it does straight after, as the terminal set-up asks it (DASH-271).
        list.push({ id: "preset", ...stepNamed(T, "preset"), intro: "You can change each part in Settings, Performance." }, shadowsStep());
      }
    }
    if (types(Object.keys(KEY_PLACE)).some((s) => !s.has_api_key)) {
      list.push({ id: "keys", ...stepNamed(T, "keys"),
        intro: "With its key, Starboard can show an app's queue, calendar, updates and warnings. Each key stays on the server." });
    }
    const coming = (keys) => !!flow && keys.some((k) => flow.state.apps.has(k));  // installed by this set-up
    if (types(["jellyfin"]).length || coming(["jellyfin"])) list.push({ id: "jellyfin", ...stepNamed(T, "extras"), intro: "Each one is inactive until you tick it. All are in Settings, Apps, Jellyfin later." });
    if (types(["qbittorrent", "nzbget", "sabnzbd"]).some((s) => s.has_api_key) || coming(["qbittorrent", "nzbget", "sabnzbd"])) list.push({ id: "hours", ...stepNamed(T, "hours"), intro: "Starboard pauses qBittorrent, NZBGet, SABnzbd and Soulseek (slskd) outside these hours, for example to keep the internet free in the day." });
    // DASH-417: after Download hours, so it can name the quiet hours; Reelix's choice only when Reelix is being installed.
    list.push({ id: "updates", ...stepNamed(T, "updates"), has: { reelix: coming(["reelix"]), jellyfin: coming(["jellyfin"]) } });
    list.push({ id: "alerts", ...stepNamed(T, "alerts"), intro: "Starboard checks your apps every few minutes and tells you when one stops answering or a disk has a problem." });
    if (hasDisks) list.push({ id: "storage", ...stepNamed(T, "storage-page"), intro: "Sorting the space by type reads every file, so you choose when it happens. Everything here is also in Settings, Performance." });
    if (start === "new" && !flow) list.push({ id: "preset", ...stepNamed(T, "preset"), intro: "You can change each part in Settings, Performance." }, shadowsStep());
    if (!dockerAccess && start === "new") list.push({ id: "docker", ...stepNamed(T, "docker"), skippable: false });  // the last question
    if (leftOver) list.push({ id: "cleanup", ...stepNamed(T, "cleanup"), intro: "What earlier versions, removed plug-ins and old backups left behind." });
    list.push({ id: "finish", ...stepNamed(T, "finish"), skippable: false });
    return list;
  };

  // The step after this one, found in the list as it is now: a step can drop out once it is done (the keys step,
  // when no key is missing), and counting on by one would skip the next step (VM test).
  const after = (id, at) => {
    const list = build();
    const here = list.findIndex((x) => x.id === id);
    return go(here >= 0 ? here + 1 : at);
  };
  const go = async (i) => {
    await loadFlow();
    steps = build();
    index = Math.max(0, Math.min(i, steps.length - 1));
    const step = steps[index];
    step.nodes = [el("p", { class: "muted", text: "Loading…" })];
    step.goTo = (sid) => go(Math.max(0, build().findIndex((x) => x.id === sid)));  // Change on a check table
    let save = async () => true;
    let loading = true;  // Continue waits until the step has loaded, so a quick click cannot skip it
    const frame = () => wizardFrame({ root, steps, index, busy: loading,
      continueText: step.id === "finish" ? "Go to Apps" : step.id === "review" && flow?.ids().has("review") ? "Write the files" : "Continue",
      onBack: () => go(index - 1), onSkip: () => step.group ? after(steps.filter((x) => x.group === step.group).pop().id, index) : after(step.id, index),
      onContinue: async (e) => {
        const button = e.currentTarget;  // the event forgets it once the save has been awaited
        button.disabled = true;
        try {
          const saved = await save();
          if (saved === "skip" && step.group) after(steps.filter((x) => x.group === step.group).pop().id, index);  // an optional step left empty
          else if (saved) { if (step.id === "finish") location.href = "/index.html"; else after(step.id, index); }
        }
        catch (err) { problem(err.message); }
        finally { if (button.isConnected) button.disabled = false; }
      } });
    frame();
    $("#guide-summary").textContent = `Step ${index + 1} of ${steps.length} · about 3 minutes · you can change everything later in Settings`;

    let content;
    if (flow && flow.ids().has(step.id)) {
      // An Install apps step: drawn by install.js; it may ask for another step by its id (Change, or after Basics).
      const goTo = (id) => {
        const list = build();
        const want = id === "folders" && !list.some((x) => x.id === "folders") ? "where" : id;  // the guide's Storage chose the folder
        return go(Math.max(0, list.findIndex((x) => x.id === want)));
      };
      content = await installStep(step.id, flow.state, flow.data, flow.apps, goTo);
      if (!content) return;  // drawn again by a newer go()
      if (step.id === "start") {
        const started = content.save;
        content.save = async () => {
          const ok = await started();
          try { config = await api("/api/config"); } catch { /* the next steps use what they have */ }
          return ok;
        };
      }
    } else {
      content = await stepContent(step.id, root, step);
    }
    if (step.id !== "finish") { step.nodes = content.nodes; save = content.save; }
    if (step.id === "finish") {
      await saveGeneral({ setup_guide_done: true });
      const apps = config.services.filter((s) => !s.background).length;
      const keyless = types(Object.keys(KEY_PLACE)).filter((s) => !s.has_api_key).map((s) => s.name);
      const uw = (await setupWords()).updates;  // DASH-417, as the terminal says it
      const facts = [
        ["Apps", `${apps} ${apps === 1 ? "app" : "apps"}${keyless.length ? `; still without a key: ${keyless.join(", ")}` : ""}`, "/settings.html"],
        ["Jellyfin extras", ["livetv", "import_keep", "defaults", "audio_description"].filter((k) => config.extras[k]).map((k) => ({ livetv: "Live TV", import_keep: "history import", defaults: "user defaults", audio_description: "audio description (to install in Settings, Plug-ins)" })[k]).join(", ") || "None", "/settings-jellyfin.html"],
        [uw.summary, updatesSummary(uw, config), "/settings-updates.html"],
        ["Download hours", config.download_hours.enabled ? `${String(config.download_hours.start).padStart(2, "0")}:00 to ${String(config.download_hours.end).padStart(2, "0")}:00` : "Deactivated", "/settings-downloads-hours.html"],
        ["Alerts", config.watch.enabled ? `Activated, to ${config.watch.channel.kind || "nowhere yet"}` : "Deactivated", "/settings-alerts.html"],
        ["How much it does", config.presets[config.performance.preset] || "Custom", "/settings-performance.html"],
        ...(config.shadows_answered ? [[(await setupWords()).shadows.summary, config.shadows_off ? "Removed" : "Kept", "/settings-general-appearance.html"]] : []),
      ];
      step.nodes = [el("dl", { class: "facts" }, facts.flatMap(([k, v, href]) => [el("dt", { text: k }),
        el("dd", {}, v, " · ", el("a", { href }, "Change", el("span", { class: "visually-hidden", text: ` ${k.toLowerCase()}` })))]))];
      try {
        const host = await api("/api/setup/host");
        if (host.command && host.starter) {
          const make = el("button", { type: "button", class: "btn btn--primary", "aria-haspopup": "dialog" }, icon("play"), "Make the change now");
          make.addEventListener("click", () => hostChange(make));
          step.nodes.push(el("h3", { text: "One change to the server, made for you" }),
            el("p", { class: "muted", text: "Free space for your media folder, disk health, the Live TV folder and Docker access need the installer on the server. Starboard's helper on the server makes the change, and shows how it goes here, so you do not need to go to the server." }),
            el("div", { class: "actions" }, make));
        } else if (host.command) {
          step.nodes.push(el("h3", { text: "One change to make on the server" }),
            el("p", { class: "muted", text: "Free space for your media folder, disk health, the Live TV folder and Docker access need the installer on the server. In a terminal there, in the Starboard folder, run:" }),
            el("pre", { class: "code-block", text: host.command }), copyButton(host.command, "Copy the command"));
        }
      } catch { /* nothing to change on the server */ }
    }
    loading = false;
    const { heading } = frame();
    heading.focus();
  };
  const mem = guideMemory();
  if (mem.at === "after-apps") {
    remember({ at: "" });
    const list = build();
    go(list.findIndex((s) => s.id === "where") + 1);
  } else if (mem.at === "after-drives") {
    // Back from System, Storage, Pool (DASH-271): on with the step after Your drives.
    remember({ at: "" });
    const list = build();
    go(list.findIndex((s) => s.id === "drives") + 1);
  } else {
    go(0);
  }
}

// Upgrade guide -----------------------------------------------------------------
// After an upgrade that brings settings to choose: What is new, one step per choice, Finish. "Remind me later"
// hides the notice in this browser until the next time it opens; "Keep the defaults and finish" ends it now.

async function startUpgrade() {
  const root = $("#upgrade");
  root.removeAttribute("aria-busy");
  const r = await api("/api/releases");
  const p = r.pending;
  const titles = { storage: "Storage", apps: "New apps", keys: "API keys", jellyfin: "Jellyfin", hours: "Download hours", alerts: "Alerts", preset: "How much it does", names: "Names it answers to" };
  const questions = { storage: "How should Storage keep up to date?", apps: "Add apps Starboard can now find?", keys: "Give Starboard their API keys?", jellyfin: "Use Starboard's Jellyfin extras?",
    hours: "Only download at set hours?", alerts: "Get an alert when something stops?", preset: "How much should Starboard do in the background?", names: "Do you open Starboard with another name?" };
  const steps = [{ id: "new", title: "What is new", question: `What is new in ${p.to}` },
    ...p.review.map((id) => ({ id, title: titles[id] || id, question: questions[id] || titles[id] })),
    { id: "done", title: "Finish", question: "Update finished", skippable: false }];
  // In the slide-out (?panel=1), finishing or Remind me later tells the page around it, which closes the slide-out.
  const inPanel = document.documentElement.classList.contains("in-panel");
  const leave = (what) => { if (inPanel) window.parent.postMessage({ starboard: what }, location.origin); else location.href = "/index.html"; };
  const finish = async () => { await api("/api/releases/seen", { method: "POST" }); leave("upgrade-done"); };
  const head = $(".page-head");
  if (!$("#upgrade-later", head)) {
    head.append(el("div", { class: "actions" },
      el("button", { type: "button", class: "btn btn--quiet", id: "upgrade-later", onclick: () => { try { sessionStorage.setItem(`upgrade-later-${p.to}`, "1"); } catch { /* fine */ } leave("upgrade-later"); } }, "Remind me later"),
      el("button", { type: "button", class: "btn btn--quiet", onclick: finish }, "Keep the defaults and finish")));
  }
  const go = async (index) => {
    const step = steps[index];
    let save = async () => true;
    step.nodes = [el("p", { class: "muted", text: "Loading…" })];
    let loading = true;
    const frame = () => wizardFrame({ root, steps, index, busy: loading, continueText: step.id === "done" ? "Go to Apps" : "Continue",
      onBack: () => go(index - 1), onSkip: () => go(index + 1),
      onContinue: async (e) => {
        const button = e.currentTarget;
        button.disabled = true;
        try { if (await save()) { if (step.id === "done") await finish(); else go(index + 1); } } catch (err) { problem(err.message); }
        finally { if (button.isConnected) button.disabled = false; }
      } });
    frame();
    $("#upgrade-summary").textContent = `From ${p.from} to ${p.to} · ${steps.length} steps · ./update.sh saved your settings first`;
    if (step.id === "new") step.nodes = p.releases.slice().reverse().map((rel) => releaseNotes(rel, 3));
    else if (step.id === "done") step.nodes = [el("p", { text: "Everything else carries on as it was. The release notes stay under the version in the footer." })];
    else { const c = await stepContent(step.id, root); step.nodes = c.nodes; save = c.save; }
    loading = false;
    frame().heading.focus();
  };
  if (!p.releases.length) {
    root.replaceChildren(notice("success", "Nothing to do", `Starboard ${r.current} has nothing new to choose.`), el("div", { class: "actions" }, el("a", { class: "btn", href: "/index.html", text: "Go to Apps" })));
    return;
  }
  go(0);
}

// Update settings (the footer's About and updates) ---------------------------------

async function startAbout() {
  const top = $("#version-notice");
  const check = el("input", { type: "checkbox", role: "switch", "aria-labelledby": "check-l", "aria-describedby": "check-h", checked: config.update_check });
  let v = null;
  const showVersion = () => {
    if (!v) return;
    const latest = (v.latest || "").replace(/^v/, "");
    const repo = /^[\w.-]+\/[\w.-]+$/.test(v.repo || "") ? v.repo : "";
    const notes = repo && v.latest ? el("a", { class: "btn", href: `https://github.com/${repo}/releases/tag/${encodeURIComponent(v.latest)}`, target: "_blank", rel: "noopener noreferrer" },
      "Release notes", el("span", { class: "visually-hidden", text: " (opens in a new tab)" })) : null;
    let box;
    if (latest && isNewer(latest, v.current)) box = notice("info", `Version ${latest} is out`, `You have ${v.current}. Read what changed, then choose Update now, or run the update command on the server.`, notes);
    else if (latest) box = notice("success", "You have the newest version", `Version ${v.current}.`);
    else if (!repo) box = notice("info", `You have version ${v.current}`, "Starboard cannot check for new versions, because STARBOARD_REPO is not set on the server.");
    else if (!config.update_check) box = notice("info", `You have version ${v.current}`, "Checking for new versions is inactive. Activate Check GitHub for new releases to find out when one is out.");
    else box = notice("info", `You have version ${v.current}`, "GitHub did not answer, so Starboard does not know yet whether a newer version is out.");
    box.classList.add("notice--page");
    top.replaceChildren(box);
    const facts = $("#about-facts");
    facts.replaceChildren(el("dt", { text: "Version" }), el("dd", { class: "numeric", text: v.current }));
    if (v.since) facts.append(el("dt", { text: "Running since" }), el("dd", { text: new Date(v.since * 1000).toLocaleString("en-GB", { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" }) }));
    if (repo) facts.append(el("dt", { text: "Source code" }), el("dd", {}, el("a", { href: `https://github.com/${repo}`, target: "_blank", rel: "noopener noreferrer" }, "Starboard on GitHub", el("span", { class: "visually-hidden", text: " (opens in a new tab)" }))));
    facts.append(el("dt", { text: "Support" }), el("dd", {}, el("a", { href: DISCORD_INVITE, target: "_blank", rel: "noopener noreferrer" }, "Discord support server", el("span", { class: "visually-hidden", text: " (opens in a new tab)" }), icon("external-link"))));
  };
  check.addEventListener("change", async () => {
    try {
      await saveGeneral({ update_check: check.checked }, true);
      v = await api("/api/version");
      showVersion();
    } catch (e) { check.checked = !check.checked; problem(e.message); }
  });
  $("#update-check-row").replaceChildren(settingRow("Check GitHub for new releases", el("span", { id: "check-h", text: "Activated: Starboard checks every 6 hours at most and shows a notice at the top." }), el("label", { class: "switch" }, check), "check-l"));
  $("#update-command").append(copyButton("./update.sh", "the update command"));
  await startSelfUpdate();
  startUpdatesPlace();
  renderAccess();
  try { v = await api("/api/version"); } catch { /* no notice */ }
  showVersion();
}

// The Updates answer in the set-up's summary (DASH-422), as terminal_setup.updates_summary says it: the parts
// chosen, such as "Starboard, Reelix and plug-ins", or Deactivated.
function updatesSummary(w, cfg) {
  const names = w.parts.filter((p) => cfg[p.key]).map((p) => p.short);
  if (!names.length) return w.summary_none;
  const text = names.length === 1 ? names[0] : `${names.slice(0, -1).join(", ")} ${w.summary_and} ${names[names.length - 1]}`;
  return text[0].toUpperCase() + text.slice(1);
}

let selfUpdateAsk = null;  // Update now's dialog, for Starboard's row in Ready to update (DASH-420)

let updatesRefresh = null;  // draws Ready to update and Recent updates again, after Starboard's own update

// Settings, Updates (DASH-420, DASH-422): the one place for updates. Ready to update lists everything Starboard can
// update (Starboard, Reelix, the other apps, plug-ins and Jellyfin's plug-ins) from what it already knows, with the
// same Update words and dialog everywhere; Update by themselves sets each part and the hours; Recent updates says
// what each update did and what is new. Nothing here asks the internet: GitHub, the registries and the catalogues
// are read by their own checks (DASH-421).
const RUN_WORDS = { updated: ["Updated", "success"], "up-to-date": STATUS.upToDate, "rolled-back": ["Rolled back", "info"],
  "went-back": ["Went back by itself", "warning"], refused: ["Not updated", "warning"], failed: STATUS.failed, running: STATUS.updating,
  "some-updated": ["Some updated", "warning"] };

// Each update's state in Install all updates (DASH-454): words, tone and icon, so the state never rests on colour.
const BATCH_WORDS = { waiting: STATUS.waiting, working: STATUS.updating, done: STATUS.done,
  "went-back": STATUS.wentBack, failed: STATUS.failed, skipped: STATUS.notStarted,
  held: STATUS.heldBack };

const byWords = (by) => (by === "automatic" ? "by itself" : String(by || "").startsWith("api") ? "from the API" : "by you");

// The password dialog every update and Roll back uses: what happens, then the Starboard password. send(password)
// does the request; a wrong password asks again in the same dialog. Returns send's answer, or null when cancelled.
async function updateWithPassword({ title, steps, confirm, send }) {
  const input = el("input", { class: "input", id: `up-pw-${Date.now()}`, type: "password", autocomplete: "current-password", required: true });
  const err = el("span", { class: "field-error", id: `${input.id}-error`, hidden: true });
  input.setAttribute("aria-describedby", err.id);
  const what = el("div", { class: "stack-2" }, el("ul", {}, steps.map((t) => el("li", { text: t }))), el("p", { text: "Enter your Starboard password to go ahead." }));
  for (;;) {
    const asked = confirmDialog({ title, message: what, confirm, fields: [el("div", { class: "field" }, el("label", { for: input.id, text: "Your Starboard password" }), input, err)] });
    if (!(await asked)) return null;
    try { return await send(input.value); } catch (e) {
      if (e.status === 401 || e.status === 429) {
        err.textContent = e.status === 401 ? "That password is not right. Check Caps Lock and try again." : e.message;
        err.hidden = false; input.setAttribute("aria-invalid", "true"); input.value = "";
        continue;
      }
      throw e;
    }
  }
}

async function startUpdatesPlace() {
  const list = $("#updates-list");
  if (!list) return;
  const summary = $("#up-list-summary"), result = $("#updates-result"), recent = $("#updates-recent"), auto = $("#updates-auto");
  const allBox = $("#updates-all");
  let data = null, jelly = null, batchShown = null, checked = null, checking = false, jellyRestart = null;
  const load = async () => { data = await api("/api/updates"); };
  try { await load(); } catch (e) { list.removeAttribute("aria-busy"); summary.textContent = `Starboard could not list the updates: ${e.message}`; return; }

  const ended = (j, title) => {
    const tone = j.ok ? "success" : j.ok === null ? "warning" : "danger";
    const box = notice(tone, j.title || title, j.text || "");
    box.setAttribute("tabindex", "-1");
    result.replaceChildren(box);
    return box;
  };
  const follow = (title, url) => {
    const job = taskJob({ title, url, failedWord: "Stopped here", returnTo: "up-list-h" });
    job.open();
    result.replaceChildren(job.pageLine);
    job.follow((j) => ({ title: j.title, text: j.text })).then(async (j) => {
      const box = ended(j, title);
      await refresh();
      if (!job.dialog.open) box.focus();
    });
  };
  const startApp = async (t, opener) => {
    const steps = t.kind === "reelix"
      ? ["A copy of Reelix's settings is made first.", `Reelix ${t.latest || "newest"} is installed.`, "If it does not answer healthy within 5 minutes, it goes back to the version before by itself."]
      : t.kind === "jellyfin-plugins"
        ? ["A copy of Jellyfin's plug-ins folder is made first.", "Jellyfin installs the new versions of its plug-ins.", "Jellyfin restarts when nobody is watching, and each plug-in must start.", "Jellyfin keeps no older version, so a plug-in that does not start is deactivated by Jellyfin and you are told."]
        : [`A copy of ${t.name}'s settings is made first.`, `${t.name} ${t.latest || "newest"} is installed.`, "If it does not run within 2 minutes, it goes back to the version before by itself."];
    try {
      const r = await updateWithPassword({ title: `Update ${t.name}`, steps, confirm: "Update now",
        send: (password) => api("/api/updates/start", { method: "POST", body: { target: t.id, password } }) });
      if (r) follow(`Updating ${t.name}`, r.job);
      else opener?.focus();
    } catch (e) {
      const box = notice("danger", `${t.name} was not updated`, e.message);
      box.setAttribute("tabindex", "-1");
      result.replaceChildren(box);
      box.focus();
    }
  };

  const action = (t) => {
    if (t.kind === "starboard") {
      if (!t.update_available || !t.can_update || !selfUpdateAsk) return null;
      const b = el("button", { type: "button", class: "btn btn--primary", "aria-haspopup": "dialog", "aria-describedby": `up-${t.id}-l` }, icon("circle-arrow-up"), "Update now");
      b.addEventListener("click", () => selfUpdateAsk());
      return b;
    }
    if (t.kind === "plugin") {
      const pid = t.id.split(":")[1];
      if (t.update_available) return el("a", { class: "btn btn--primary", href: `/settings-plugin.html?id=${encodeURIComponent(pid)}`, "aria-describedby": `up-${t.id}-l` }, "Read what is new and update");
      if (t.can_roll_back) return el("a", { class: "btn", href: `/settings-plugin.html?id=${encodeURIComponent(pid)}`, "aria-describedby": `up-${t.id}-l` }, "Roll back");
      return null;
    }
    if (!t.update_available || !t.can_update) return null;
    const b = el("button", { type: "button", class: "btn btn--primary", "aria-haspopup": "dialog", "aria-describedby": `up-${t.id}-l` }, icon("circle-arrow-up"), "Update now");
    b.addEventListener("click", () => startApp(t, b));
    return b;
  };
  const row = (t) => {
    const ready = t.update_available;
    const facts = [t.current ? `You have ${t.current}` : "Version not known", ready && t.latest ? `New: ${t.latest}` : ""].filter(Boolean).join(". ");
    const unknown = !ready && /look for updates first/i.test(t.why || "");  // no look at its image yet
    const why = ready && !t.can_update && t.kind !== "plugin" ? t.why : !ready && t.why && !/up to date|no newer version/i.test(t.why) ? t.why : "";
    const note = t.kind === "plugin" && ready && t.note ? `What is new: ${t.note}` : "";
    return el("li", { class: "setting", "data-key": t.id },
      el("div", { class: "setting__text" },
        el("span", { class: "setting__label", id: `up-${t.id}-l`, text: t.name }),
        el("span", { class: "setting__hint" }, `${facts}.`, why ? ` ${why}.`.replace(/\.\.$/, ".") : "", note ? ` ${note}` : ""),
        el("span", { class: "chips" }, ready ? chip(...STATUS.updateAvailable) : unknown ? chip(...STATUS.notChecked) : chip(...STATUS.upToDate),
          ready ? (t.automatic ? chip("Updates by itself", "muted", "clock") : chip("Waits for you", "warning", "user")) : null)),
      el("div", { class: "setting__control" }, action(t)));
  };
  const jellyRow = () => {
    if (!jelly?.connected) return null;
    const t = { id: "jellyfin-plugins", kind: "jellyfin-plugins", name: "Jellyfin's plug-ins" };
    const b = el("button", { type: "button", class: "btn", "aria-haspopup": "dialog", "aria-describedby": "up-jellyfin-plugins-l" }, icon("circle-arrow-up"), "Check for updates and install them");
    b.addEventListener("click", () => startApp(t, b));
    const own = jelly.own_schedule ? " Jellyfin also updates them by itself on its own schedule." : "";
    const found = data.jellyfin_waiting || [];
    const hint = found.length
      ? `${jelly.count} installed. New versions: ${found.map((j) => `${j.name} ${j.latest}`).join(", ")}.${own}`
      : `${jelly.count} installed. Jellyfin knows which have new versions: Check for updates asks it.${own}`;
    // Restart needed (DASH-470): new plug-in versions wait for Jellyfin's restart when someone was watching. The
    // same Restart Jellyfin stays while it works and after, so a redraw of the list keeps its status.
    if (jelly.restart && jelly.can_restart && !jellyRestart) {
      jellyRestart = restartButton(jellyfinRestart(jelly.name || "Jellyfin", async () => {
        try { jelly = await api("/api/updates/jellyfin"); } catch { /* the list stays as it was */ }
        drawList();
        return null;
      }));
    }
    const restarting = jellyRestart && (jelly.restart || jellyRestart.dataset.state) ? jellyRestart : null;
    if (!restarting) jellyRestart = null;
    const chips = [found.length ? chip("Update available", "info", "circle-arrow-up") : null, jelly.restart ? chip(...STATUS.restartNeeded) : null].filter(Boolean);
    return el("li", { class: "setting", "data-key": t.id },
      el("div", { class: "setting__text" }, el("span", { class: "setting__label", id: "up-jellyfin-plugins-l", text: t.name }),
        el("span", { class: "setting__hint", text: jelly.restart ? `${hint} New versions start when Jellyfin restarts.` : hint }),
        chips.length ? el("span", { class: "chips" }, chips) : null, restarting),
      el("div", { class: "setting__control" }, b));
  };
  const drawList = () => {
    const items = [...data.items].sort((a, b) => Number(b.update_available) - Number(a.update_available));
    const ready = [...items.filter((t) => t.update_available).map((t) => `${t.name} ${t.latest}`.trim()),
      ...(data.jellyfin_waiting || []).map((j) => `${j.name} ${j.latest} for Jellyfin`)];
    if (!checking) summary.textContent = summaryText(ready);
    list.removeAttribute("aria-busy");
    redraw(list, [...items.map(row), jellyRow(),
      // The place is said in the words as well as the link (DASH-474: read as text it said "Each app's image is on .").
      el("li", { class: "setting", "data-key": "look" }, el("div", { class: "setting__text" },
        el("span", { class: "setting__hint", text: "Check for updates, in Ready to update, checks every part again. Each app's image and its versions are in Apps, Updates." })),
        el("div", { class: "setting__control" }, el("a", { class: "btn btn--quiet", href: "/apps-updates.html" }, "Open Apps, Updates"))) ].filter(Boolean));
  };
  // What Ready to update says (a polite live region): what is ready, and after Check for updates when it looked and
  // what it could not reach.
  const summaryText = (ready) => {
    const kept = data.apps_checked;  // the apps' last look, kept across a restart (DASH-548)
    const when = checked ? `Checked at ${new Date(checked.checked_at * 1000).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}. `
      : kept ? `The apps were last checked ${checkedWhen(kept.at, kept.restored)}. ` : "";
    const what = ready.length
      ? `${ready.length} ${ready.length === 1 ? "update is" : "updates are"} ready: ${ready.join(", ")}.`
      : checked ? "Everything is up to date." : "Everything Starboard knows about is up to date.";
    const missed = (checked?.parts || []).filter((p) => !p.ok).map((p) => `${p.name}: ${p.said}.`);
    return `${when}${what}${missed.length ? ` Could not check everything. ${missed.join(" ")}` : ""}`;
  };
  const drawRecent = () => {
    const runs = data.recent || [];
    recent.replaceChildren(...(runs.length ? runs : [null]).map((r) => {
      if (!r) return el("li", { class: "setting" }, el("div", { class: "setting__text" }, el("span", { class: "setting__hint", text: "No updates have run yet." })));
      const [word, tone] = RUN_WORDS[r.state] || RUN_WORDS.failed;
      const change = r.action === "rollback" ? `Back to ${r.to}` : r.from && r.to ? `${r.from} to ${r.to}` : r.to || "";
      const when = r.started_at ? timeAgo(Date.parse(r.started_at)) : "";
      return el("li", { class: "setting" }, el("div", { class: "setting__text" },
        el("span", { class: "setting__label" }, r.name, " ", chip(word, tone)),
        el("span", { class: "setting__hint", text: [change, `${r.action === "rollback" ? "rolled back" : "updated"} ${byWords(r.by)}`, when].filter(Boolean).join(" · ") }),
        r.said ? el("span", { class: "setting__hint", text: r.said }) : null));
    }));
  };
  const drawAuto = () => {
    const a = data.auto;
    const name = `up-hours-${Date.now()}`;
    const hours = config.download_hours;
    const pad = (h) => `${String(h).padStart(2, "0")}:00`;
    const radio = (value, label, hint) => {
      const input = el("input", { type: "radio", name, value, checked: a.hours === value });
      input.addEventListener("change", async () => {
        try { await saveGeneral({ auto_update_hours: value }, true); data.auto = (await api("/api/updates")).auto; $("#up-hours-now").textContent = `Now: ${data.auto.hours_words}.`; }
        catch (e) { problem(e.message); }
      });
      return el("label", { class: "option-card" }, input, el("strong", { text: label }), el("small", { text: hint }));
    };
    const when = el("fieldset", { class: "stack-2" }, el("legend", { class: "setting__label", text: "When they update" }),
      el("div", { class: "option-cards option-cards--row" },
        radio("download", "In your download hours", hours.enabled ? `${pad(hours.start)} to ${pad(hours.end)}, while the downloads run. Set in Settings, Downloads.` : "Not set, so 01:00 to 06:00. Set them in Settings, Downloads."),
        radio("quiet", "In the quiet hours", "Always 01:00 to 06:00, whatever your download hours.")),
      el("p", { class: "small muted", id: "up-hours-now", text: `Now: ${a.hours_words}.` }));
    const rows = a.parts.map((p) => {
      const input = el("input", { type: "checkbox", id: `auto-${p.id}`, checked: p.active });
      input.addEventListener("change", async () => {
        try { await saveGeneral({ [p.key]: input.checked }, true); } catch (e) { input.checked = !input.checked; problem(e.message); }
      });
      const last = p.last ? `Last checked ${timeAgo(p.last.at * 1000)}: ${p.last.runs.length ? p.last.runs.map((r) => `${r.name} ${(RUN_WORDS[r.state] || RUN_WORDS.failed)[0].toLowerCase()}`).join(", ") : "nothing to update"}.` : "";
      const hint = `Deactivated: it waits for you, and you are told when an update is ready.${p.id === "jellyfin_plugins" && jelly && !jelly.connected ? " Needs Jellyfin with its API key in Manage apps." : ""}${last ? ` ${last}` : ""}`;
      return el("li", { class: "setting" }, switchRow(`${p.name}: update by itself`, hint, input),
        el("dl", { class: "facts small" }, el("dt", { text: "Copy first" }), el("dd", { text: p.safety.copy }),
          el("dt", { text: "Checked by" }), el("dd", { text: p.safety.check }), el("dt", { text: "Way back" }), el("dd", { text: p.safety.back })));
    });
    auto.removeAttribute("aria-busy");
    auto.replaceChildren(when, el("ul", { class: "settings-rows", "aria-label": "What may update by itself" }, rows));
  };
  // Install all updates (DASH-454): one button when more than one update waits; one password, then the list of
  // what installs (in order) and what is held back; then one panel for the batch that follows it to the end, through
  // Starboard's own restart. Nothing is asked of the internet until the password is given.
  // Check for updates and What is new (DASH-462): Check for updates asks every part now (nothing is asked on page
  // load); What is new reads every waiting update's notes only when pressed. Install all updates shows from one update.
  const waitingUpdates = () => data.items.filter((t) => t.update_available);
  const waitingCount = () => waitingUpdates().length + (data.jellyfin_waiting || []).length;
  const drawAll = () => {
    if (batchShown?.running()) return;
    const n = waitingCount();
    const had = document.activeElement?.id;
    const check = el("button", { type: "button", class: "btn", id: "check-updates-now", "aria-describedby": "install-all-hint" },
      icon("refresh-cw"), checking ? "Checking…" : "Check for updates");
    if (checking) check.setAttribute("aria-disabled", "true");
    check.addEventListener("click", () => checkNow());
    const buttons = [check];
    if (n) {
      const b = el("button", { type: "button", class: "btn btn--primary", id: "install-all", "aria-haspopup": "dialog", "aria-describedby": "install-all-hint" },
        icon("circle-arrow-up"), n === 1 ? "Install 1 update" : `Install all ${n} updates`);
      b.addEventListener("click", () => installAll(b));
      const wn = el("button", { type: "button", class: "btn", id: "whats-new", "aria-haspopup": "dialog" }, icon("sparkles"), "What is new",
        el("span", { class: "visually-hidden", text: ` in ${n === 1 ? "the update" : `the ${n} updates`}` }));
      wn.addEventListener("click", () => whatsNew(wn));
      buttons.unshift(b, wn);
    }
    const hint = n ? "One at a time, each with a copy first, a check afterwards and the way back. Starboard updates last."
      : "Check for updates asks Starboard, the apps, Reelix, the plug-ins and Jellyfin for new versions now.";
    allBox.replaceChildren(...[el("div", { class: "actions" }, ...buttons), el("p", { class: "small muted", id: "install-all-hint", text: hint }),
      batchShown?.node].filter(Boolean));
    if (had && ["check-updates-now", "install-all", "whats-new"].includes(had)) (document.getElementById(had) || check).focus();
  };
  const checkNow = async () => {
    if (checking) return;
    checking = true;
    summary.textContent = "Checking Starboard, the apps, Reelix, the plug-ins and Jellyfin for updates…";
    drawAll();
    try {
      checked = await api("/api/updates/check", { method: "POST" });
      await load();
    } catch (e) {
      checked = { checked_at: Date.now() / 1000, parts: [{ name: "Starboard", ok: false, said: e.message }] };
    }
    checking = false;
    drawList();
    drawAll();  // focus stays on Check for updates, which is drawn again in the same place
  };
  const whatsNew = async (opener) => {
    const n = waitingCount();
    const panel = sidePanel({ title: n === 1 ? "What is new in 1 update" : `What is new in ${n} updates`, opener, wide: true,
      body: [el("p", { class: "muted", role: "status", text: "Reading the notes…" })] });
    let r;
    try { r = await api("/api/updates/whats-new"); } catch (e) {
      panel.setBody([notice("danger", "Starboard could not read the notes", e.message)]);
      return;
    }
    if (!r.items.length) { panel.setBody([el("p", { text: "Nothing is waiting to update, so there is nothing new to read." })]); return; }
    const head = (i) => `${i.name} ${i.from && i.to ? `${i.from} to ${i.to}` : i.to}`.trim();
    const link = (i, words) => (i.link ? el("a", { href: i.link, target: "_blank", rel: "noopener noreferrer" }, words,
      el("span", { class: "visually-hidden", text: ` for ${i.name} (opens in a new tab)` })) : null);
    const jump = el("nav", { "aria-label": "Updates in this list" }, el("ul", {}, r.items.map((i, k) => {
      const a = el("a", { href: `#wn-${k}`, text: head(i) });
      a.addEventListener("click", (e) => { e.preventDefault(); const h = document.getElementById(`wn-${k}`); h?.scrollIntoView({ block: "start" }); h?.focus(); });
      return el("li", {}, a);
    })));
    const sections = r.items.map((i, k) => {
      const several = i.versions.length > 1;
      const about = [i.words, several ? `${i.versions.length} versions: ${i.versions.join(", ")}.` : ""].filter(Boolean).join(" ");
      const body = i.problem ? [notice("warning", "Notes not read", `${i.problem}.`.replace(/\.\.$/, ".")), i.link ? el("p", {}, link(i, "Its release page"), ".") : null]
        : i.none ? [el("p", {}, i.none, " ", link(i, "Its release page"), i.link ? "." : "")]
        : i.sections.flatMap((sec) => [el("h4", { text: sec.type }),
          el("ul", {}, sec.items.map((x) => el("li", {}, ...changeParts(x.parts),
            several && x.version ? el("span", { class: "small muted", text: ` (${x.version})` }) : null,
            x.items?.length ? changeItems(x.items) : null)))]);
      // Its own picture beside its name (DASH-475), as on its card: decorative, since the name is beside it.
      const pic = i.icon ? appIcon({ id: i.icon.service, icon: i.icon.v, name: i.name }, "app-icon app-icon--compact")
        : "logo" in i ? pluginLogo({ name: i.name, logo: i.logo }, { compact: true }) : null;
      return el("section", { class: "release-notes", "aria-labelledby": `wn-${k}` },
        el("div", { class: "release-notes__head" }, pic, el("h3", { id: `wn-${k}`, tabindex: "-1", text: head(i) })),
        about || (i.link && !i.none && !i.problem) ? el("p", { class: "small muted" }, about, about && i.link && !i.none && !i.problem ? " " : "",
          !i.none && !i.problem ? link(i, "Release page") : null) : null,
        ...body.filter(Boolean));
    });
    panel.setBody([el("p", { text: "Everything new from the version you have to the one ready, for each update. Each kind of change lists the newest first." }),
      r.items.length > 1 ? jump : null, ...sections].filter(Boolean));
  };
  const planLine = (i) => (i.kind === "jellyfin-plugins" ? `${i.name}: ${i.note || "Jellyfin installs any new versions it has"}, and restarts once at the end, when nobody is watching`
    : i.from && i.to ? `${i.name} ${i.from} to ${i.to}` : `${i.name} ${i.to}`.trim());
  // The dialog counts what will run (Jellyfin's plug-ins as one), as the panel does; the page button counts what is
  // ready. These sentences join the two: "4 of the 6 updates ready, plus Jellyfin's plug-ins. They install one at a
  // time, in this order."
  const introText = (plan) => {
    const known = plan.items.filter((i) => i.kind !== "jellyfin-plugins").length, ready = waitingUpdates().length;
    const jf = plan.items.length > known ? ", plus Jellyfin's plug-ins" : "";
    const which = known === ready ? `${ready === 1 ? "The update" : `All ${ready} updates`} ready${jf}` : `${known} of the ${ready} updates ready${jf}`;
    if (plan.items.length === 1) return `${which}. If it does not work, it goes back by itself.`;
    return `${which}. They install one at a time, in this order. One that does not work goes back by itself, and the rest carry on.`;
  };
  const installAll = async (opener) => {
    let password = "";
    let plan;
    try {
      plan = await updateWithPassword({ title: "Install all updates", confirm: "Continue",
        steps: ["Starboard checks each waiting update, then shows you what will install before anything does.",
          "They install one at a time, each with a copy first, a check afterwards and the way back.",
          "Starboard updates last. It restarts, and this page reconnects by itself."],
        send: async (pw) => { const r = await api("/api/updates/all/plan", { method: "POST", body: { password: pw } }); password = pw; return r; } });
    } catch (e) {
      const box = notice("danger", "Starboard could not list the updates", e.message);
      box.setAttribute("tabindex", "-1"); result.replaceChildren(box); box.focus();
      return;
    }
    if (!plan) { opener?.focus(); return; }
    const held = plan.held.length ? [el("h3", { text: `Held back for you (${plan.held.length})` }),
      el("ul", { class: "update-plan" }, plan.held.map((h) => el("li", {}, el("strong", { text: `${h.name} ${h.to}`.trim() }), `: ${h.why}.`.replace(/\.\.$/, "."))))] : [];
    if (!plan.count) {
      const box = notice("info", "Nothing can install all at once", "Each update waiting needs you to choose it on its own.");
      box.setAttribute("tabindex", "-1");
      result.replaceChildren(box, ...held);
      box.focus();
      return;
    }
    const words = `${plan.items.length} ${plan.items.length === 1 ? "update" : "updates"}`;  // what the list shows, as the panel counts
    const message = el("div", { class: "stack-2" },
      el("p", { text: introText(plan) }),
      el("ol", { class: "update-plan" }, plan.items.map((i) => el("li", { text: planLine(i) }))),
      ...held);
    const ok = await confirmDialog({ title: `Install ${words}`, message, confirm: `Install ${words}` });
    if (!ok) { opener?.isConnected && opener.focus(); return; }
    try {
      const r = await api("/api/updates/all/start", { method: "POST", body: { password, targets: plan.items.map((i) => i.target) } });
      password = "";
      showBatch(r.batch, true);
    } catch (e) {
      password = "";
      const box = notice("danger", "The updates did not start", e.message);
      box.setAttribute("tabindex", "-1"); result.replaceChildren(box); box.focus();
    }
  };
  // The batch's panel: each update with its state in words and an icon, the count, what is happening now, a polite
  // live region for each change, and the result at the end. It asks every 2 seconds while the batch runs, and keeps
  // asking while Starboard restarts (no answer for about a minute), then shows how it ended. The words say whether it
  // is still working (#161): "Installing updates" and "4 of 5 done" over a moving bar, then how it ended, with Close.
  const batchEnd = (v) => (v.state === "updated" ? "All updates finished" : v.state === "failed" ? "The updates stopped" : "Some updates did not install");
  const showBatch = (b, focus = false) => {
    const head = el("h3", { id: "update-all-h", tabindex: "-1", text: b.finished ? "Install all updates finished" : "Installing all updates" });
    const count = el("span", { class: "numeric" });
    const label = el("span", { text: b.finished ? batchEnd(b) : "Installing updates" });
    const bar = el("div", { class: `progress${b.finished ? "" : " progress--running"}`, role: "progressbar", "aria-labelledby": "update-all-count", "aria-valuemin": "0" }, el("span"));
    const meter = el("div", { class: "meter" }, el("div", { class: "meter__label", id: "update-all-count" }, label, count), bar);
    const now = el("p", { class: "task-now small", role: "status" });
    const list = el("ul", { class: "task-list", "aria-label": "Each update" });
    const res = el("div", { class: "stack-2" });
    const live = el("div", { class: "visually-hidden", role: "status", "aria-live": "polite" });
    const node = el("section", { class: "update-all", "aria-labelledby": "update-all-h" }, head, meter, now, list, res, live);
    const states = new Map();
    let running = !b.finished, misses = 0;
    const draw = (v) => {
      count.textContent = `${v.ended} of ${v.count} done`;
      label.textContent = v.finished ? batchEnd(v) : "Installing updates";
      bar.classList.toggle("progress--running", !v.finished);
      bar.setAttribute("aria-valuemax", String(v.count || 1));
      bar.setAttribute("aria-valuenow", String(v.ended));
      bar.setAttribute("aria-valuetext", `${v.finished ? batchEnd(v) : "Installing updates"}, ${v.ended} of ${v.count} done`);
      // DASH-489: while it runs the bar is never empty: 1% from the first moment, then each update that ends adds its
      // share. The count in aria-valuenow and the words stay the true count (0 of 5 until the first one ends).
      const share = v.count ? Math.round((100 * v.ended) / v.count) : 100;
      bar.firstChild.style.width = `${v.finished ? share : Math.max(1, share)}%`;
      const changes = [];
      list.replaceChildren(...v.items.map((i) => {
        const [word, tone, ic] = BATCH_WORDS[i.state] || BATCH_WORDS.waiting;
        const li = el("li", { class: "task-list__item", "data-state": i.state },
          el("span", { class: "task-list__name", text: i.label }), chip(word, tone, ic),
          i.detail ? el("span", { class: "task-list__detail small muted", text: i.detail }) : null);
        if (i.state === "working") li.setAttribute("aria-current", "step");
        const before = states.get(i.target);
        if (before && before !== i.state) changes.push(`${i.label}: ${word}`);
        states.set(i.target, i.state);
        return li;
      }));
      if (changes.length) live.textContent = changes.join(". ");
      now.textContent = v.finished ? "" : v.said ? `Now: ${v.said}` : "";
      now.hidden = v.finished || !v.said;
    };
    const end = async (v, followed = true) => {
      running = false;
      head.textContent = "Install all updates finished";
      label.textContent = batchEnd(v);
      bar.classList.remove("progress--running");
      const tone = v.state === "updated" ? "success" : v.state === "failed" ? "danger" : "warning";
      const title = batchEnd(v);
      const box = notice(tone, title, v.said);
      box.setAttribute("tabindex", "-1");
      // Close (DASH-473): takes the finished panel away for good, and focus goes to Ready to update's heading.
      const close = el("button", { type: "button", class: "btn", id: "update-all-close" }, icon("x"), "Close",
        el("span", { class: "visually-hidden", text: " Install all updates" }));
      close.addEventListener("click", () => closeBatch(b.id));
      res.replaceChildren(box, el("div", { class: "actions" }, close));
      if (!followed) { drawAll(); return; }  // ended before the page opened: shown with the button, nothing announced or moved
      live.textContent = `${title}. ${v.said}`;
      const there = document.activeElement === document.body || node.contains(document.activeElement);
      await refresh();
      if (there) box.focus();  // focus moves to the result only from the panel, never away from what you are doing
    };
    const look = async () => {
      let v = null;
      try { v = await api(`/api/updates/all/${b.id}`); misses = 0; } catch { misses += 1; }
      if (v) { draw(v); if (v.finished) { end(v); return; } }
      else if (misses === 1) { now.hidden = false; now.textContent = "Starboard is restarting. This reconnects by itself."; }
      setTimeout(look, v ? 2000 : 3000);
    };
    draw(b);
    batchShown = { id: b.id, node, running: () => running };
    allBox.replaceChildren(node);
    if (focus) head.focus();
    if (b.finished) end(b, false); else setTimeout(look, 2000);
  };

  // Close on the finished panel: Starboard is told, so the panel does not come back when the page opens again; it
  // goes from the page even when that cannot be saved. Focus moves to Ready to update, and the change is announced.
  const closeBatch = async (id) => {
    try { await api(`/api/updates/all/${id}/close`, { method: "POST" }); } catch { /* closed on this page only */ }
    batchShown = null;
    if (data.batch?.id === id) data.batch = null;
    drawAll();
    const h = document.getElementById("up-list-h");
    h.setAttribute("tabindex", "-1");
    h.focus();
    announce("Install all updates closed. Ready to update.");
  };
  const refresh = async () => { try { await load(); } catch { return; } drawList(); drawRecent(); drawAll(); };
  updatesRefresh = refresh;
  drawList();
  drawRecent();
  drawAuto();
  if (data.batch) showBatch(data.batch); else drawAll();
  // Jellyfin is asked only now, after the page is drawn, and only once (it is another app's API).
  try { jelly = await api("/api/updates/jellyfin"); } catch { jelly = null; }
  drawList();
  drawAuto();
}

// Update now (DASH-417): admin only, with the Starboard password, as a plug-in install asks. update.sh runs in a
// helper that outlives Starboard's restart; the task dialog follows its steps from data/self-update.log, loses touch
// while Starboard restarts and reconnects by itself, and ends with the new version or with where it went back to.
async function startSelfUpdate() {
  const box = $("#self-update");
  if (!box) return;
  let s;
  try { s = await api("/api/self-update"); } catch { return; }
  const result = el("div", { class: "stack-2", id: "self-update-result" });
  const ended = (u, focus) => {
    if (!u || !u.title) return;
    const tone = u.outcome === "updated" || u.outcome === "up-to-date" ? "success" : u.outcome === "went-back" ? "warning" : "danger";
    const guide = u.outcome === "updated" ? el("a", { class: "btn", href: "/upgrade.html" }, "What is new") : null;
    const box2 = notice(tone, u.title, u.text, guide);
    box2.setAttribute("tabindex", "-1");
    result.replaceChildren(box2);
    if (focus) box2.focus();
  };
  // Opened at once after Update now; an update already running when the page opens shows its line, with Show progress.
  const follow = (openNow = true) => {
    const job = taskJob({ title: "Updating Starboard", url: "/api/self-update/job", failedWord: "Stopped here", returnTo: "up-list-h",
      intro: "Starboard restarts during the update, so this loses touch with it for about a minute and reconnects by itself. Closing this does not stop the update." });
    if (openNow) job.open();  // first, while Update now is still there to note as the opener; focus comes back to the heading
    box.replaceChildren(job.pageLine, result);
    job.follow((j) => ({ title: j.title, text: j.text })).then(async (j) => { await updatesRefresh?.(); ended(j, !job.dialog.open); });
  };
  const ask = async () => {
    const latest = s.latest.replace(/^v/, "");
    const input = el("input", { class: "input", id: "su-password", type: "password", autocomplete: "current-password", required: true, "aria-describedby": "su-password-error" });
    const err = el("span", { class: "field-error", id: "su-password-error", hidden: true });
    const what = el("div", { class: "stack-2" },
      el("p", { text: `Starboard installs version ${latest}. You have ${s.current}.` }),
      el("ul", {}, el("li", { text: "Your settings are backed up first." }),
        el("li", { text: "Starboard restarts, and is away for about a minute." }),
        el("li", { text: `If the new version does not start, Starboard goes back to ${s.current} by itself, with your settings as they were.` })),
      el("p", { text: "Enter your Starboard password to go ahead." }));
    for (;;) {
      const asked = confirmDialog({ title: `Update Starboard to ${latest}`, message: what, confirm: "Update now",
        fields: [el("div", { class: "field" }, el("label", { for: input.id, text: "Your Starboard password" }), input, err)] });
      if (!(await asked)) return;
      try { await api("/api/self-update/start", { method: "POST", body: { password: input.value, to: s.latest } }); break; }
      catch (e) {
        if (e.status === 401 || e.status === 429) {
          err.textContent = e.status === 401 ? "That password is not right. Check Caps Lock and try again." : e.message;
          err.hidden = false; input.setAttribute("aria-invalid", "true"); input.value = "";
          continue;
        }
        result.replaceChildren(notice("danger", "Starboard was not updated", e.message));
        result.firstChild.setAttribute("tabindex", "-1");
        result.firstChild.focus();
        return;
      }
    }
    follow();
  };
  selfUpdateAsk = ask;
  const draw = () => {
    const nodes = [];
    const u = s.update;
    if (u && u.state === "running") { follow(false); return; }
    // DASH-420: Update now is Starboard's row in Ready to update (startUpdatesPlace); this box keeps its progress,
    // why it cannot be updated here, and its result.
    if (s.newer) {
      const latest = s.latest.replace(/^v/, "");
      if (!s.can) nodes.push(notice("info", `Version ${latest} can be installed on the server`, s.why));
      else if (s.skip === s.latest) nodes.push(notice("warning", `${latest} did not install last time`, "It does not update by itself to this version again. Update now tries again."));
    }
    // The last update's result, for a day after it ended (an update in the night is still there in the morning).
    // Not once Starboard has moved on to a newer version by another way (DASH-474).
    if (u && u.finished && !u.superseded && Date.now() / 1000 - u.finished < 86400) ended(u, false);
    box.replaceChildren(...nodes, result);
  };
  draw();
}

// Settings, Your install: what Starboard installed (Basics, Full install, Everything or your own choice), and changing
// it either way, with the Usenet app and which Reelix (stack.plan_change, /api/install/change). 7 November 2026.
async function startYourInstall() {
  const root = $("#install-sections");
  const facts = (pairs) => el("dl", { class: "facts" }, ...pairs.flatMap(([k, v]) => [el("dt", { text: k }), el("dd", { text: v })]));
  let d;
  try { d = await api("/api/install"); } catch (e) { root.replaceChildren(notice("danger", "Could not read your install", e.message)); root.removeAttribute("aria-busy"); return; }
  root.removeAttribute("aria-busy");
  const status = el("div", { class: "stack-2", "aria-live": "polite" });
  const how = section("in-how", "How changing works", "The same steps for a bigger install or a smaller one.",
    el("ol", { class: "stack-1" },
      el("li", { text: "Starboard keeps a copy of the set-up file in data/stack, named compose.yaml.before- and the date, so you can go back." }),
      el("li", { text: "It writes the new set-up file, with the same folders, user, time zone and VPN details, and the same passwords it made up before." }),
      el("li", { text: "It downloads the apps being added and starts them. Apps taken away stop and are removed; their settings folders stay, so adding one back later carries on where it left off." }),
      el("li", { text: "From SABnzbd to NZBGet, your Usenet servers move across: address, port, user name, password, connections and SSL. The queue and history do not. From NZBGet to SABnzbd, add your servers in SABnzbd." }),
      el("li", { text: "Reelix is given the new download app in place of the old one, and new apps are added to your dashboard as they answer." }),
      el("li", { text: "Going from the full Reelix to Lite works when Lite is on the same release or newer; Starboard says when it has to wait." })));
  if (!d.written) {
    root.replaceChildren(section("in-now", "Your install", "", notice("info", "Nothing installed by Starboard yet",
      "Install apps sets up your media server. Once it has, this page shows what is installed and changes it."),
      el("div", { class: "actions" }, el("a", { class: "btn btn--primary", href: "/install-apps.html" }, icon("download"), "Install apps"))), takeoverSection(), how);
    return;
  }
  const cur = d.current;
  const names = { basics: "Basics", full: "Full install", all: "Everything", custom: "Your own choice" };
  const editionName = (k) => (d.editions.find((e) => e.key === k) || {}).name || k;
  const usenetName = (k) => (d.usenet_apps.find((u) => u.key === k) || {}).name || "None";
  const want = { install: null, usenet: cur.usenet, reelix_edition: cur.reelix_edition };
  const now = section("in-now", "Your install now", "",
    facts([["Install", names[cur.install] || cur.install], ["Reelix", cur.reelix_edition ? editionName(cur.reelix_edition) : "Not installed"],
      ["Usenet app", usenetName(cur.usenet)], ["Apps", cur.apps.join(", ")], ["Memory when idle", `about ${(cur.memory / 1000).toFixed(1)} GB`]]),
    ...(d.last_change ? [notice("info", "Last change", (d.last_change.notes || []).join(". ") || "Finished")] : []));

  const summary = el("p", { class: "muted", "aria-live": "polite" });
  const describe = () => {
    const parts = [];
    const pick = d.installs.find((i) => i.key === want.install);
    if (pick && !pick.error) {
      if (pick.add.length) parts.push(`adds ${pick.add.join(", ")}`);
      if (pick.remove.length) parts.push(`takes away ${pick.remove.join(", ")}`);
    }
    if (want.usenet && want.usenet !== cur.usenet) parts.push(`uses ${usenetName(want.usenet)} for Usenet in place of ${usenetName(cur.usenet)}`);
    if (want.reelix_edition && want.reelix_edition !== cur.reelix_edition) parts.push(`switches Reelix to ${editionName(want.reelix_edition)}`);
    summary.textContent = parts.length ? `This change ${parts.join("; ")}.` : "Choose a change first.";
    button.disabled = !parts.length;
  };
  const installCards = el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Install" }),
    el("div", { class: "option-cards" }, d.installs.map((i) => {
      const r = el("input", { type: "radio", name: "your-install", id: `your-install-${i.key}`, value: i.key, checked: cur.install === i.key, disabled: !!i.error });
      r.addEventListener("change", () => { want.install = i.key; want.reelix_edition = i.reelix_edition; reelixRadios(); describe(); });
      const lines = i.error ? [i.error] : [i.about,
        cur.install === i.key ? "In use now" : [i.add.length ? `Adds ${i.add.join(", ")}` : "", i.remove.length ? `Takes away ${i.remove.join(", ")}` : ""].filter(Boolean).join(". ") || "Nothing to add or take away",
        // DASH-250: apps from the person's own Compose file are not added again as new, empty apps.
        (i.outside || []).length ? `${i.outside.join(", ")} already ${i.outside.length === 1 ? "runs" : "run"} from your own Compose file: ${i.outside.length === 1 ? "it joins" : "they join"} once taken over in Apps you already run` : "",
        `About ${(i.memory / 1000).toFixed(1)} GB of memory`];
      return el("label", { class: "option-card" }, r, el("strong", { text: i.name }), ...lines.filter(Boolean).map((t) => el("small", { text: t })));
    })));
  const usenetCards = cur.usenet ? el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Usenet app" }),
    el("div", { class: "option-cards option-cards--row" }, d.usenet_apps.map((u) => {
      const r = el("input", { type: "radio", name: "your-usenet", id: `your-usenet-${u.key}`, value: u.key, checked: cur.usenet === u.key });
      r.addEventListener("change", () => { want.usenet = u.key; describe(); });
      return el("label", { class: "option-card" }, r, el("strong", { text: u.name + (u.key === "nzbget" ? " (recommended)" : "") }),
        el("small", { text: u.key === "nzbget" ? "Light on memory and processor." : "More extras; uses more memory." }),
        cur.usenet === u.key ? el("small", { class: "muted", text: "In use now" }) : null);
    }))) : el("p", { class: "muted", text: "No Usenet app is installed. Full install and Everything add NZBGet." });
  const reelixBox = el("div");
  const reelixRadios = () => {
    if (!cur.reelix_edition && !want.install) { reelixBox.replaceChildren(el("p", { class: "muted", text: "Reelix is not installed." })); return; }
    reelixBox.replaceChildren(el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Reelix" }),
      el("div", { class: "option-cards option-cards--row" }, d.editions.map((e) => {
        const r = el("input", { type: "radio", name: "your-reelix", id: `your-reelix-${e.key}`, value: e.key, checked: want.reelix_edition === e.key, disabled: !e.available && e.key !== cur.reelix_edition });
        r.addEventListener("change", () => { want.reelix_edition = e.key; describe(); });
        return el("label", { class: "option-card" }, r, el("strong", { text: e.name }), el("small", { text: e.about }),
          el("small", { class: "muted", text: e.key === cur.reelix_edition ? "In use now" : !e.available ? "Cannot be downloaded at the moment" : "" }));
      }))));
  };
  reelixRadios();

  const password = el("input", { class: "input", type: "password", autocomplete: "current-password", required: true });
  const button = el("button", { type: "submit", class: "btn btn--primary", text: "Change my install", disabled: true });
  const form = el("form", { novalidate: true }, summary, el("div", { class: "form-stack" },
    field("Your password", password, { required: true, hint: "Changing downloads and starts apps, and stops the ones taken away. It takes a few minutes." })),
    el("div", { class: "actions" }, button));
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    setError(password, "");
    if (!password.value) { setError(password, "Enter your password"); password.focus(); return; }
    button.disabled = true;
    status.replaceChildren(el("p", { class: "muted", text: "Writing the new set-up…" }));
    let r;
    try {
      r = await api("/api/install/change", { method: "POST", body: { password: password.value, install: want.install,
        usenet: want.usenet !== cur.usenet ? want.usenet : null, reelix_edition: want.reelix_edition !== cur.reelix_edition ? want.reelix_edition : null } });
    } catch (err) {
      button.disabled = false; status.replaceChildren();
      if (err.status === 401 || err.status === 429) { setError(password, err.message); password.focus(); }
      else status.replaceChildren(notice("danger", "Nothing was changed", err.message));
      return;
    }
    password.value = "";
    if (!r.started) {
      status.replaceChildren(notice("info", "One step on the server", "Starboard wrote the new set-up but cannot start apps itself. Run this in a terminal on the server:"),
        el("pre", { class: "code-block", text: r.command }), copyButton(r.command, "Copy the command"),
        el("p", { class: "muted", text: "Once the apps have started, Starboard finishes off by itself within a minute: it updates the dashboard and Reelix, and moves Usenet servers if you changed the Usenet app. Keep this page open, or come back to it, to find out what was done." }));
      // DASH-141: the page shows when the command has run and Starboard is finishing off, then what was done,
      // so it never looks stuck. Starboard writes change-result.json when it has finished (data/stack).
      const waiting = el("div", { class: "meter", role: "status" },
        el("div", { class: "meter__label" }, el("span", { text: "Waiting for the command to be run on the server…" })),
        el("div", { class: "progress progress--busy", role: "progressbar", "aria-label": "Waiting for the command", "aria-valuetext": "Waiting" }, el("span")));
      status.append(waiting);
      const asked = Date.now() / 1000;
      for (let n = 0; n < 720; n++) { // an hour, as long as Starboard waits for the command itself
        await new Promise((res) => setTimeout(res, 5000));
        const d = await api("/api/install").catch(() => null);
        const done = d && d.last_change && d.last_change.finished >= asked;
        if (!done) continue;
        waiting.replaceWith(notice("success", "Your install is changed", (d.last_change.notes || []).join(". ") || "Finished: nothing else needed doing."));
        announce("Your install is changed");
        return;
      }
      waiting.replaceWith(notice("warning", "Not finished yet", "Starboard has not detected the apps starting in the last hour. Run the command on this page on the server, then open this page again."));
      return;
    }
    status.replaceChildren(el("p", { class: "muted", text: "Downloading and starting the apps…" }));
    for (;;) {
      await new Promise((res) => setTimeout(res, 3000));
      const j = await api("/api/stack/job").catch(() => ({}));
      if (!j.finished) continue;
      status.replaceChildren(j.ok ? notice("success", "Your install is changed", "Finishing off: the dashboard and Reelix are being updated. This page shows what was done.")
        : notice("danger", "The apps did not all start", "The details follow. The old set-up file is kept in data/stack."), j.ok ? "" : el("pre", { class: "code-block", text: j.log || "" }));
      if (j.ok) setTimeout(() => startYourInstall(), 20000);
      return;
    }
  });

  root.replaceChildren(now,
    section("in-change", "Change your install", "Bigger or smaller, either way. Apps you added yourself outside Starboard are not touched.",
      (d.outside || []).length ? notice("info", `${d.outside.join(", ")} ${d.outside.length === 1 ? "runs" : "run"} from your own Compose file`,
        "So a change here does not add them again as new, empty apps. Take them over in Apps you already run: then they are part of your install.",
        el("a", { class: "btn", href: "#in-takeover-h" }, "Apps you already run")) : null, installCards),
    section("in-usenet", "Usenet app", "The app that downloads from Usenet. Your Usenet servers move across from SABnzbd to NZBGet.", usenetCards),
    section("in-reelix", "Reelix", "Reelix, or Reelix with YouTube and Spotify downloads. The library, users and settings stay.", reelixBox),
    section("in-confirm", "Make the change", "", form, status), takeoverSection(), how);
  describe();
}

// Settings, Your install: apps someone already runs from their own Compose file (DASH-151, 127 to 129; 8 November
// 2026; clearer at every stage on 13 November 2026: DASH-190 to 192, 251 to 254). Step 1 moves Radarr, Sonarr and the
// others into Reelix through Reelix's own migrator (reelix_move.py); then the review, the requests route when Seerr
// runs, and the takeover into Starboard's stack, with copies of their settings and a way back (takeover.py). Once the
// takeover is kept, the apps Reelix replaced can be cleared away into the holding folder.
function takeoverSection() {
  // A step inside this section: an h3 under the section's h2.
  const section = (id, title, description, ...content) => el("div", { class: "stack-2", role: "group", "aria-labelledby": `${id}-h` },
    el("h3", { id: `${id}-h`, text: title }), description ? el("p", { class: "small muted" }, description) : null, ...content);
  const box = el("div", { class: "stack-2", "aria-busy": "true" }, el("p", { class: "muted", text: "Finding apps you already run…" }));
  const list = (items) => el("ul", { class: "stack-1" }, items.map((t) => el("li", { text: t })));
  const pw = (hint) => { const i = el("input", { class: "input", type: "password", autocomplete: "current-password", required: true }); return [i, field("Your password", i, { required: true, hint })]; };
  const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
  // Each step says what happens under its own buttons (owner, 8 November 2026). A new try clears what the last one
  // said, so an earlier wrong password never stays beside the right one (DASH-254).
  const failed = (input, err, title, out) => {
    if (err.status === 401 || err.status === 429) { setError(input, err.message); input.focus(); }
    else { out.replaceChildren(notice("danger", title, err.message)); out.scrollIntoView({ block: "nearest" }); }
  };
  const fresh = (...things) => things.forEach((t) => (t.matches?.("input") ? setError(t, "") : t.replaceChildren()));
  const needPassword = (input) => { if (input.value) return true; setError(input, "Enter your password"); input.focus(); return false; };

  // The three jobs, each with its dialog. A job already running when the page opens shows its line and dialog too.
  const moveJob = () => taskJob({ title: "Moving your apps into Reelix", url: "/api/reelix/move/job", failedWord: "Not moved", returnTo: "tk-review-h",
    intro: "Reelix reads each app in turn. Films and series move in a minute or two each; Reelix then finds their files, which can take an hour for a big library." });
  const takeJob = () => taskJob({ title: "Taking over your apps", url: "/api/takeover/job", returnTo: "in-takeover-h",
    intro: "Your apps stop for a few minutes while their settings are copied. Before anything stops, Starboard saves the way back." });
  const backJob = () => taskJob({ title: "Rolling back", url: "/api/takeover/job", returnTo: "in-takeover-h", intro: "Your old apps start again from their own Compose file, on the versions they ran." });
  const clearJob = () => taskJob({ title: "Clearing away the old apps", url: "/api/takeover/job", returnTo: "in-takeover-h", intro: "Each app stops and is removed; its settings folder goes into the holding folder." });
  const kindJob = { takeover: takeJob, rollback: backJob, clear: clearJob };

  // Drawn again after a change: focus that was in this section (or lost with the old nodes) goes to its heading.
  const redraw = async () => {
    const inside = box.contains(document.activeElement) || document.activeElement === document.body;
    await draw();
    const dialogOpen = document.querySelector("dialog[open]");
    if (inside && !dialogOpen && !box.contains(document.activeElement)) {
      const head = document.getElementById("in-takeover-h");
      if (head) { head.setAttribute("tabindex", "-1"); head.focus(); }
    }
  };
  const draw = async () => {
    let t, m;
    try { [t, m] = await Promise.all([api("/api/takeover"), api("/api/reelix/move")]); }
    catch (e) { box.replaceChildren(notice("danger", "Could not find the apps you already run", e.message)); box.removeAttribute("aria-busy"); return; }
    box.removeAttribute("aria-busy");
    const parts = [];
    // A change that is still running (started here or elsewhere): its line on the page, and its dialog on request.
    const stillRunning = (j, make, after) => {
      if (!j || !j.started || j.finished) return null;
      const job = make();
      job.follow(after).then(() => setTimeout(redraw, 1500));
      return job.pageLine;
    };
    const resultOfTake = (j, ok) => ({ title: ok ? "Starboard runs your apps now" : "Nothing was changed",
      text: (j.notes || []).join(". ") || (ok ? "Finished." : "Your old apps run again as they were.") });
    const takeRunning = stillRunning(t.job, kindJob[t.job?.kind] || takeJob, t.job?.kind === "takeover" ? resultOfTake : null);
    const moveRunning = stillRunning(m.job, moveJob, null);
    if (takeRunning) parts.push(takeRunning);

    // DASH-253: titles a move could not match, waiting until they do; shown at every stage while there are any.
    const waitingPart = t.waiting_count ? waitingSection(t) : null;

    // A takeover that can still be rolled back: Roll back, or Keep it.
    if (t.record) {
      const when = new Date(t.record.made * 1000).toLocaleString();
      const [p1, p1f] = pw("Rolling back stops the apps Starboard took over and starts your old ones from their own Compose file, on the versions they ran.");
      const back = el("button", { type: "button", class: "btn btn--danger", text: "Roll back" });
      const keep = el("button", { type: "button", class: "btn", text: "Keep it" });
      const said = el("div", { class: "stack-2", "aria-live": "polite" });
      back.addEventListener("click", async () => {
        fresh(p1, said);
        if (!needPassword(p1)) return;
        back.disabled = keep.disabled = true;
        try { await api("/api/takeover/rollback", { method: "POST", body: { password: p1.value } }); }
        catch (err) { back.disabled = keep.disabled = false; failed(p1, err, "Nothing was rolled back", said); return; }
        p1.value = "";
        const job = backJob();
        said.replaceChildren(job.pageLine);
        job.open();
        const j = await job.follow((j, ok) => ({ title: ok ? "Rolled back" : "Rolling back did not finish", text: (j.notes || []).join(". ") }));
        said.replaceChildren(notice(j.ok ? "success" : "danger", j.ok ? "Rolled back" : "Rolling back did not finish", (j.notes || []).join(". ")));
        if (j.ok) { announce("Rolled back"); setTimeout(redraw, 5000); }
        else back.disabled = keep.disabled = false;
      });
      keep.addEventListener("click", async () => {
        fresh(p1, said);
        if (!needPassword(p1)) return;
        try { await api("/api/takeover/clear", { method: "POST", body: { password: p1.value } }); }
        catch (err) { failed(p1, err, "Nothing was changed", said); return; }
        p1.value = ""; announce("Kept. The way back is put aside"); await draw();
        $("#tk-clear-h")?.setAttribute("tabindex", "-1");
        ($("#tk-clear-h") || $("#in-takeover-h"))?.focus();
      });
      parts.push(notice("info", `Starboard took over ${plural(t.record.containers.length, "app", "apps")} on ${when}`,
        "Your old settings folders, Compose file and app versions are kept, so you can go back. Keep it once everything works: the way back is then put aside, and nothing is deleted. After that, Starboard offers to clear away the apps Reelix replaced."),
        el("div", { class: "form-stack" }, p1f), el("div", { class: "actions" }, back, keep), said);
      if (waitingPart) parts.push(waitingPart);
      box.replaceChildren(...parts);
      return;
    }

    // DASH-191: after Keep it, the apps Reelix replaced can be stopped and removed, their folders into the holding folder.
    if (t.leftovers && t.leftovers.length) parts.push(clearAwaySection(t.leftovers));
    else if (t.cleared && t.cleared.length) {
      parts.push(section("tk-cleared", "Old apps cleared away", "Their settings folders are in the holding folder. Nothing was deleted: empty it yourself once you are sure.",
        list([...new Map(t.cleared.map((c) => [c.from, c])).values()].map((c) => `${c.app}: ${c.to}`))));
    }

    if (t.error) {
      parts.push(el("p", { class: "muted", text: t.error === "Starboard found no apps here to take over" ? "Starboard runs every app here: there is nothing else to take over." : t.error }));
      if (m.review) parts.push(reviewSection(m.review));
      if (t.requests) parts.push(requestsSection(t.requests));
      if (waitingPart) parts.push(waitingPart);
      box.replaceChildren(...parts);
      return;
    }
    const p = t.plan;

    // Step 1: into Reelix. Reelix has to run first: on a server set up by hand, Install apps adds it (with NZBGet)
    // next to the old apps, which stay as they are.
    const unmoved = p.unmoved || [];
    let step = 1;
    if (!(m.sources && m.sources.length) && unmoved.length) {
      parts.push(section("tk-install", `Step ${step++}: install Reelix`,
        "Reelix takes the place of " + p.unmoved_apps.join(", ") + ". Install it first, so it can read them before they stop.",
        el("p", { text: "In Install apps, choose Full install. Your apps that already run are left as they are, so it adds only the apps you do not have yet, Reelix among them. Then come back here." }),
        el("div", { class: "actions" }, el("a", { class: "btn btn--primary", href: "/install-apps.html" }, icon("download"), "Install apps"))));
    }
    if (m.needs_setup && m.sources && m.sources.length) {
      parts.push(section("tk-setup", `Step ${step}: finish setting up Reelix`,
        "Reelix runs, but its set-up did not finish, so it cannot read your apps yet.",
        el("div", { class: "actions" }, el("a", { class: "btn btn--primary", href: "/settings-reelix.html" }, icon("settings"), "Finish setting up Reelix"))));
      box.replaceChildren(...parts);
      return;
    }
    if (m.sources && m.sources.length) parts.push(moveSection(m, step++, unmoved, moveRunning));
    if (m.review) parts.push(reviewSection(m.review, step++));
    if (t.requests) parts.push(requestsSection(t.requests, step++));
    parts.push(takeSection(p, step, unmoved, !!takeRunning));
    if (waitingPart) parts.push(waitingPart);
    box.replaceChildren(...parts);

    // Step: move them into Reelix (DASH-251, DASH-254).
    function moveSection(m, n, unmoved, running) {
      const last = m.last;
      const lines = [];
      if (last && last.apps) last.apps.forEach((a) => lines.push(`${a.app}: ${a.state === "finished" ? "moved" : `not finished${a.error ? ` (${a.error})` : ""}`}${(a.not_moved || []).length ? `, ${plural(a.not_moved.length, "item", "items")} not moved` : ""}`));
      if (last && last.error) lines.push(`The move stopped: ${last.error}`);
      const [p2, p2f] = pw("Reelix's admin password is the same as Starboard's.");
      const q = m.qbittorrent || {};
      const quser = m.qbittorrent_user;
      const qbit = el("input", { class: "input", type: "password", autocomplete: "off" });
      const userLine = quser
        ? `Reelix signs in to qBittorrent as ${quser}, the user name in qBittorrent's own settings file.`
        : q.read ? "qBittorrent's settings file names no user, so Reelix signs in as admin, qBittorrent's first user name."
          : "Starboard could not read qBittorrent's settings file, so Reelix signs in as admin, qBittorrent's first user name.";
      const hold = el("input", { type: "checkbox", checked: true });
      const preview = el("button", { type: "button", class: "btn", text: "Show what moves" });
      const run = el("button", { type: "button", class: "btn btn--primary", text: "Move them into Reelix" });
      const shown = el("div", { class: "stack-2", "aria-live": "polite" });
      const said = el("div", { class: "stack-2", "aria-live": "polite" });
      if (running) { run.disabled = preview.disabled = true; said.replaceChildren(running); }
      // DASH-128: keys the apps hide that Starboard could not read from their own settings, typed here once the
      // preview has named them; kept in these fields (never stored by the page) and sent with the move.
      const keyInputs = new Map();
      const typed = () => {
        const out = {};
        keyInputs.forEach(({ source, id, input }) => { if (input.value.trim()) (out[source] ||= {})[id] = input.value.trim(); });
        return out;
      };
      const fieldWords = { apiKey: "API key", apikey: "API key", password: "password", username: "user name" };
      const keyFields = (a) => {
        if (!a.needs?.length) return null;
        const rows = a.needs.map((n) => {
          const k = `${a.source}|${n.id}`;
          if (!keyInputs.has(k)) keyInputs.set(k, { source: a.source, id: n.id, input: el("input", { class: "input", type: "password", autocomplete: "off", spellcheck: "false" }) });
          return field(`${n.name}: ${fieldWords[n.field] || n.field}`, keyInputs.get(k).input,
            { hint: `${a.app} hides it and Starboard could not read it from ${a.app}'s own settings. Copy it from the site's own pages, usually under your account or API.` });
        });
        return el("fieldset", { class: "form-stack" }, el("legend", { text: `Keys to type for ${a.app}` }), ...rows,
          el("p", { class: "small muted", text: "Choose Show what moves again to check them, or leave one empty: that site moves without its key and stays deactivated until you add it in Settings, Reelix, Sites to search." }));
      };
      const body = () => ({ password: p2.value, qbittorrent_password: qbit.value, hold: hold.checked, secrets: typed() });
      preview.addEventListener("click", async () => {
        fresh(p2, qbit, shown, said);
        if (!needPassword(p2)) return;
        preview.disabled = true; shown.replaceChildren(el("p", { class: "muted", text: "Asking Reelix what moves…" }));
        try {
          const r = await api("/api/reelix/move/preview", { method: "POST", body: body() });
          shown.replaceChildren(...r.apps.map((a) => {
            if (a.error) return notice("warning", a.app, a.error);
            const made = Object.entries(a.counts).map(([k, v]) => `${k.replace(/_/g, " ")}: ${v.create || 0} new, ${v.existing || 0} there already${v.skip ? `, ${v.skip} not moved` : ""}`);
            return el("details", { open: a.needs?.length ? true : null }, el("summary", { text: `${a.app}${a.still_missing.length ? ` (${plural(a.still_missing.length, "key", "keys")} still needed)` : ""}${a.filled ? `, ${plural(a.filled, "key", "keys")} read from its settings` : ""}` }),
              list(made), a.skipped.length ? el("p", { class: "small muted", text: "Not moved: " + a.skipped.map((s) => `${s.name} (${s.why})`).join("; ") }) : null,
              keyFields(a));
          }));
        } catch (err) { shown.replaceChildren(); failed(p2, err, "Reelix could not show what moves", shown); }
        preview.disabled = false;
      });
      run.addEventListener("click", async () => {
        fresh(p2, qbit, shown, said);
        if (!needPassword(p2)) return;
        run.disabled = preview.disabled = true;
        said.replaceChildren(el("p", { class: "muted", text: qbit.value ? "Checking qBittorrent's password, then starting…" : "Starting…" }));
        try { await api("/api/reelix/move/run", { method: "POST", body: body() }); }
        catch (err) {
          run.disabled = preview.disabled = false; said.replaceChildren();
          if (err.data?.field === "qbittorrent") { setError(qbit, err.message); qbit.focus(); return; }
          failed(p2, err, "Nothing was moved", said); return;
        }
        p2.value = ""; qbit.value = ""; keyInputs.forEach(({ input }) => { input.value = ""; });
        const job = moveJob();
        said.replaceChildren(job.pageLine);
        job.open();
        const j = await job.follow((j, ok) => ({ title: ok ? "Moved into Reelix" : j.error ? "The move stopped" : "Not everything moved",
          text: j.error ? `${j.error}. Steps after it did not start. Fix it, then choose Move them into Reelix again: what moved already is not moved twice.`
            : ok ? "Read the review: sites held off, and titles that did not move." : "What did not move is listed in the review." }));
        said.replaceChildren(notice(j.ok ? "success" : "warning", j.ok ? "Moved into Reelix" : j.error ? "The move stopped" : "Not everything moved",
          j.error ? `${j.error}. Steps after it did not start.` : "The review lists what needs attention."));
        announce(j.ok ? "Moved into Reelix" : "The move into Reelix did not all finish");
        setTimeout(redraw, 1500);
      });
      return section("tk-reelix", `Step ${n}: move them into Reelix`,
        "Reelix reads each app and adds its films, series, music, books, quality profiles, sites to search and requests. The apps themselves do not change.",
        list(m.sources.map((s) => `${s.app}${s.has_key ? "" : " (Starboard cannot read its key, so it is not moved)"}`)),
        lines.length ? notice(unmoved.length || (last && last.error) ? "warning" : "success", "Last move", lines.join(". ")) : null,
        el("div", { class: "form-stack" }, p2f,
          // DASH-129: the old apps may have needed no password, because qBittorrent lets their addresses in.
          q.allow_list?.length ? notice("info", "Your old apps did not need qBittorrent's password",
            `qBittorrent lets in addresses from ${q.allow_list.join(", ")} without one (its allow list in Options, Web UI). Reelix reaches qBittorrent by its name, from an address that may not be on that list, so give the password in this section.`) : null,
          field("qBittorrent's password (optional)", qbit, { hint: `What it is for: Reelix sends each download to qBittorrent, so it needs qBittorrent's password. ${userLine} Starboard checks it with qBittorrent first and keeps it only in Reelix. Leave it empty to connect qBittorrent later in Settings, Reelix, Download apps; a fixed address Reelix has for it, such as Gluetun's IP address, still becomes its name.` }),
          el("label", { class: "check" }, hold, el("span", { class: "check__text" }, el("strong", { text: "Hold the sites to search" }),
            el("span", { class: "check__hint", text: "Deactivated in Reelix after the move, so only your old apps search until Starboard runs your apps. Activate them in the review step." })))),
        el("div", { class: "actions" }, preview), shown,
        el("div", { class: "actions" }, run), said);
    }

    // DASH-190: after a move, the sites held off (Activate), sites Reelix cannot search yet, and titles that did not move.
    function reviewSection(r, n) {
      const [p4, p4f] = pw("Activating a site changes Reelix's settings, so Starboard checks it is you.");
      const said = el("div", { class: "stack-2", "aria-live": "polite" });
      const activate = async (ids, button) => {
        fresh(p4, said);
        if (!needPassword(p4)) return;
        button.disabled = true;
        try {
          const out = await api("/api/reelix/move/activate", { method: "POST", body: { password: p4.value, ids } });
          p4.value = "";
          announce(`Activated ${plural(out.changed, "site", "sites")}`);
          await draw();
          $("#tk-review-h")?.setAttribute("tabindex", "-1");
          $("#tk-review-h")?.focus();
        } catch (err) { button.disabled = false; failed(p4, err, "Nothing was activated", said); }
      };
      const held = r.held.map((h) => {
        const b = el("button", { type: "button", class: "btn", text: "Activate" }, el("span", { class: "visually-hidden", text: ` ${h.name}` }));
        b.addEventListener("click", () => activate([h.id], b));
        return el("li", { class: "row" }, el("div", { class: "row__text" }, el("span", { class: "row__title", text: h.name })),
          el("div", { class: "row__side" }, chip("Held", "muted"), b));
      });
      const all = el("button", { type: "button", class: "btn btn--primary", text: "Activate all" });
      all.addEventListener("click", () => activate(null, all));
      const sites = r.sites.map((s) => el("li", {}, el("strong", { text: s.name }), ` (from ${s.app}): `,
        s.no_definition ? "Reelix has no way to search this site yet. Add it by its Torznab or Newznab address, or wait for a Reelix update." : s.why));
      // Titles waiting for a match are listed once, in their own section below; here only their number.
      const waitingTitles = r.titles.filter((x) => x.waiting).length;
      const otherTitles = r.titles.filter((x) => !x.waiting);
      const shownTitles = otherTitles.slice(0, 50).map((x) => el("li", { class: "row" },
        el("div", { class: "row__text" }, el("span", { class: "row__title", text: x.name }),
          el("span", { class: "small muted", text: `${x.kind === "movie" ? "Film" : x.kind === "series" ? "Series" : x.kind === "author" ? "Author" : "Artist"} from ${x.app}: ${x.why}` })),
        el("div", { class: "row__side" },
          el("a", { class: "btn", href: `/search.html?q=${encodeURIComponent(String(x.name).replace(/\s*\(\d{4}\)$/, ""))}` }, "Add by hand",
            el("span", { class: "visually-hidden", text: ` ${x.name}` })))));
      return section("tk-review", n ? `Step ${n}: review the move` : "Review the move", "What the move left for you to check. Nothing here is urgent.",
        r.held.length ? el("h4", { text: `Sites to search held off (${r.held.length})` }) : null,
        r.held.length ? el("p", { class: "small muted", text: "Held so only your old apps searched until the switch. Activate them once Starboard runs your apps, or now if your old apps no longer search." }) : null,
        r.held.length ? el("ul", { class: "rows" }, held) : null,
        r.held.length ? el("div", { class: "form-stack" }, p4f) : null,
        r.held.length ? el("div", { class: "actions" }, all) : null, said,
        sites.length ? el("h4", { text: `Sites Reelix cannot search yet (${sites.length})` }) : null,
        sites.length ? el("ul", { class: "stack-1" }, sites) : null,
        sites.length ? el("p", {}, el("a", { href: "/settings-reelix.html#rx-indexers", text: "Add a site in Settings, Reelix, Sites to search" })) : null,
        r.titles_count ? el("h4", { text: `Titles that did not move (${r.titles_count})` }) : null,
        waitingTitles ? el("p", {}, `${plural(waitingTitles, "title is", "titles are")} waiting for a match: Starboard adds them by itself once they match. They are listed in `,
          el("a", { href: "#tk-waiting-h", text: "Titles waiting for a match" }), ".") : null,
        otherTitles.length ? el("ul", { class: "rows" }, shownTitles) : null,
        otherTitles.length > 50 ? el("p", { class: "small muted", text: `And ${otherTitles.length - 50} more.` }) : null,
        r.other.length ? el("details", {}, el("summary", { text: `Other things that did not move (${r.other.length})` }),
          list(r.other.map((o) => `${o.name} (${String(o.category).replace(/_/g, " ")}, from ${o.app}): ${o.why}`))) : null,
        !r.held.length && !sites.length && !r.titles_count && !r.other.length ? el("p", { class: "muted", text: "Everything moved, and no site is held. Nothing to review." }) : null);
    }

    // DASH-192: Seerr beside Reelix: keep it, or use Reelix's own requests. A choice saves as soon as it changes.
    function requestsSection(rq, n) {
      const name = `requests-${Date.now()}`;
      const note = savedNote("tk-requests-saved");
      const said = el("div", { class: "stack-2", "aria-live": "polite" });
      const message = el("div", { class: "stack-2" });
      const showMessage = (choice) => {
        if (!choice) { message.replaceChildren(); return; }
        const text = rq.messages[choice];
        message.replaceChildren(el("h4", { text: "A message for the people who use Seerr" }),
          el("blockquote", { class: "message-to-send" }, el("p", { text })), el("div", { class: "actions" }, copyButton(text, "the message")));
      };
      const cards = [["reelix", "Use Reelix's own requests", "People ask for films and series in Reelix. The move brought Seerr's users and requests across, and Starboard's Requests page shows them. Seerr stops when Starboard takes over your apps, so there is one app fewer to run."],
        ["seerr", "Keep Seerr", "People keep asking in Seerr as before. Starboard takes Seerr over with your other apps and points it at Reelix, in place of Radarr and Sonarr."]]
        .sort((a, b) => (b[0] === rq.recommended) - (a[0] === rq.recommended))
        .map(([v, title, about]) => {
          const r = el("input", { type: "radio", name, value: v, checked: rq.choice === v });
          r.addEventListener("change", async () => {
            said.replaceChildren();
            try {
              await api("/api/requests-route", { method: "POST", body: { choice: v } });
              // The takeover's list changes with it (Seerr taken over, or stopped), so the section is drawn again.
              await draw();
              $(`[aria-labelledby="tk-requests-h"] input[value="${v}"]`)?.focus();
              showSaved("tk-requests-saved", "Saved");
            } catch (err) { said.replaceChildren(notice("danger", "Not saved", err.message)); }
          });
          return el("label", { class: "option-card" }, r, el("strong", { text: title + (v === rq.recommended ? " (recommended)" : "") }), el("small", { text: about }));
        });
      showMessage(rq.choice);
      return section("tk-requests", n ? `Step ${n}: requests` : "Requests", "Seerr runs beside Reelix. Choose where people ask for films and series.",
        el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Where people ask for films and series" }), el("div", { class: "option-cards" }, cards)),
        note, said, rq.choice && rq.notes.length ? notice("info", rq.applied ? "Set up" : "Set up when Starboard runs your apps", rq.notes.join(". ")) : null,
        message);
    }

    // Step: take over (DASH-254: what is happening now, in the dialog).
    function takeSection(p, n, unmoved, running) {
      const cfg = el("input", { class: "input", value: p.settings_folder, autocomplete: "off", spellcheck: false });
      const media = el("input", { class: "input", value: p.media_folder, autocomplete: "off", spellcheck: false });
      const [p3, p3f] = pw("This stops your apps for a few minutes while their settings are copied.");
      const ok = el("input", { type: "checkbox" });
      const go = el("button", { type: "button", class: "btn btn--primary", text: "Take over my apps", disabled: running });
      const takeSaid = el("div", { class: "stack-2", "aria-live": "polite" });
      go.addEventListener("click", async () => {
        fresh(p3, takeSaid);
        if (!needPassword(p3)) return;
        go.disabled = true;
        takeSaid.replaceChildren(el("p", { class: "muted", text: "Saving the way back…" }));
        try { await api("/api/takeover/start", { method: "POST", body: { password: p3.value, install: p.install, usenet: p.usenet, config_dir: cfg.value, media_dir: media.value, unmoved_ok: ok.checked } }); }
        catch (err) { go.disabled = false; takeSaid.replaceChildren(); failed(p3, err, "Nothing was changed", takeSaid); return; }
        p3.value = "";
        const job = takeJob();
        takeSaid.replaceChildren(job.pageLine);
        job.open();
        const j = await job.follow(resultOfTake);
        takeSaid.replaceChildren(notice(j.ok ? "success" : "danger", j.ok ? "Starboard runs your apps now" : "Nothing was changed",
          (j.notes || []).join(". ") || (j.ok ? "Finished." : "Your old apps run again as they were.")));
        if (j.ok) { announce("Starboard runs your apps now"); setTimeout(redraw, 5000); } else go.disabled = false;
      });
      const keptLines = Object.entries(p.kept).map(([k, v]) => [k, [v.port_map && `ports ${Object.values(v.port_map).join(", ")}`, v.ports && `also ${v.ports.join(", ")}`,
        v.devices && `devices ${v.devices.join(", ")}`, v.volumes && `${v.volumes.length} folders it uses as they are`, v.image && `its own version (${v.image})`,
        v.env && `${v.env.length} of its own settings`, v.vpn === true && "through the VPN", v.vpn === false && "not through the VPN"].filter(Boolean).join(", ")]).map(([k, t]) => `${k}: ${t || "nothing extra"}`);
      return section("tk-take", `Step ${n}: Starboard runs your apps`,
        `Starboard takes over the apps in ${p.install_name}. Their settings are copied, never moved, and each keeps its port and what it relies on.`,
        el("h4", { text: "Taken over" }), list(p.take.map((a) => a.app)),
        p.replace.length ? el("h4", { text: "Stopped and removed (settings folders stay)" }) : null,
        p.replace.length ? list(p.replace.map((a) => `${a.app}, replaced by ${a.by}${unmoved.includes(a.name) ? " (not moved into Reelix yet)" : ""}`)) : null,
        p.new.length ? el("h4", { text: "Installed new" }) : null, p.new.length ? list(p.new) : null,
        p.leave.length ? el("h4", { text: "Left as they are" }) : null, p.leave.length ? list(p.leave.map((a) => `${a.name}: ${a.why}`)) : null,
        el("details", {}, el("summary", { text: `What each app keeps, and the ${p.copies.length} folders copied` }), list(keptLines),
          list(p.copies.map((c) => `${c.from} to ${c.to}`))),
        ...p.warnings.map((w) => notice("warning", "Before you start", w)),
        el("div", { class: "form-stack" },
          locationPicker({ input: cfg, label: "Settings folder", app: "host", setting: "config", hint: `Where the copies go. Not inside ${p.config_base || "your old settings folder"}.` }).node,
          locationPicker({ input: media, label: "Media folder", app: "host", setting: "media", hint: "Where your media and downloads are now. Nothing in it is moved." }).node,
          unmoved.length ? el("label", { class: "check" }, ok, el("span", { class: "check__text" }, el("strong", { text: `Stop ${p.unmoved_apps.join(", ")} without moving them into Reelix` }),
            el("span", { class: "check__hint", text: "Only if you do not need what they hold. Their settings folders stay either way." }))) : null,
          p3f),
        el("div", { class: "actions" }, go), takeSaid,
        el("p", { class: "small muted", text: "Before anything stops, Starboard saves the way back: every app's version, your Compose file and Starboard's own set-up files. Roll back appears here afterwards." }));
    }

    // DASH-191: once the takeover is kept, stop and remove the apps Reelix replaced; their folders go to the holding folder.
    function clearAwaySection(items) {
      const boxes = items.map((it) => {
        const c = el("input", { type: "checkbox", checked: true, value: it.name });
        const what = [it.container ? (it.running ? "Runs now: stopped and removed" : "Stopped: removed") : "Already removed",
          it.settings.length ? `settings folder ${it.settings.join(", ")} to the holding folder` : "no settings folder Starboard knows"].join("; ");
        return { it, c, node: el("label", { class: "check" }, c, el("span", { class: "check__text" }, el("strong", { text: it.app }), el("span", { class: "check__hint", text: what }))) };
      });
      const [p5, p5f] = pw("Stopping and removing apps changes this computer, so Starboard checks it is you.");
      const go = el("button", { type: "button", class: "btn btn--danger", text: "Clear away" });
      const said = el("div", { class: "stack-2", "aria-live": "polite" });
      go.addEventListener("click", async () => {
        fresh(p5, said);
        const names = boxes.filter((b) => b.c.checked).map((b) => b.it.name);
        if (!names.length) { said.replaceChildren(notice("warning", "Nothing chosen", "Tick at least one app to clear away.")); return; }
        if (!needPassword(p5)) return;
        const sure = await confirmDialog({ title: "Clear away the old apps?", danger: true, confirm: "Clear away",
          message: `${names.length === 1 ? "This app stops" : `These ${names.length} apps stop`} and ${names.length === 1 ? "is" : "are"} removed, and ${names.length === 1 ? "its settings folder goes" : "their settings folders go"} into a folder named starboard-holding beside your old settings folders. Nothing is deleted: empty that folder yourself once you are sure. The app versions Docker downloaded stay too, until you remove them.` });
        if (!sure) return;
        go.disabled = true;
        try { await api("/api/takeover/clear-away", { method: "POST", body: { password: p5.value, names } }); }
        catch (err) { go.disabled = false; failed(p5, err, "Nothing was cleared away", said); return; }
        p5.value = "";
        const job = clearJob();
        said.replaceChildren(job.pageLine);
        job.open();
        const j = await job.follow((j, ok) => ({ title: ok ? "Cleared away" : "Not everything was cleared away", text: (j.notes || []).join(". ") }));
        said.replaceChildren(notice(j.ok ? "success" : "warning", j.ok ? "Cleared away" : "Not everything was cleared away", (j.notes || []).join(". ")));
        announce(j.ok ? "Cleared away" : "Not everything was cleared away");
        setTimeout(redraw, 3000);
      });
      return section("tk-clear", "Clear away the apps Reelix replaced",
        "You kept the takeover, so these are no longer needed. Each stops and is removed, and its settings folder goes into the holding folder, which you empty yourself.",
        el("fieldset", { class: "stack-1" }, el("legend", { class: "visually-hidden", text: "Apps to clear away" }), ...boxes.map((b) => b.node)),
        el("div", { class: "form-stack" }, p5f), el("div", { class: "actions" }, go), said);
    }

    // DASH-253: the waiting list, with Try again now.
    function waitingSection(t) {
      const said = el("div", { class: "stack-2", "aria-live": "polite" });
      const again = el("button", { type: "button", class: "btn", text: "Try again now" });
      const rows = el("ul", { class: "rows" });
      const fill = (items) => rows.replaceChildren(...items.slice(0, 50).map((w) => {
        const ids = [w.tmdb && `TMDB ${w.tmdb}`, w.tvdb && `TVDB ${w.tvdb}`, w.imdb && `IMDb ${w.imdb}`].filter(Boolean).join(", ") || "no ids";
        const tried = w.last_try ? `Last tried ${new Date(w.last_try * 1000).toLocaleString()}${w.last_error ? `: ${w.last_error}` : ""}` : "Not tried yet";
        return el("li", { class: "row" }, el("div", { class: "row__text" }, el("span", { class: "row__title", text: w.title }),
          el("span", { class: "small muted", text: `${w.kind === "movie" ? "Film" : "Series"} from ${w.source}; ${ids}. ${tried}` })),
          el("div", { class: "row__side" }, chip("Waiting for a match", "muted"),
            el("a", { class: "btn", href: `/search.html?q=${encodeURIComponent(String(w.title).replace(/\s*\(\d{4}\)$/, ""))}` }, "Add by hand", el("span", { class: "visually-hidden", text: ` ${w.title}` }))));
      }));
      fill(t.waiting);
      const more = el("p", { class: "small muted", text: t.waiting_count > 50 ? `And ${t.waiting_count - 50} more.` : "" });
      again.addEventListener("click", async () => {
        said.replaceChildren(el("p", { class: "muted", text: "Trying each title again…" }));
        again.disabled = true;
        try {
          const r = await api("/api/reelix/waiting/retry", { method: "POST" });
          fill(r.items);
          more.textContent = r.count > 50 ? `And ${r.count - 50} more.` : "";
          said.replaceChildren(notice(r.added ? "success" : "info", r.added ? `Added ${plural(r.added, "title", "titles")} to Reelix` : "None matched yet",
            r.waiting ? `${plural(r.waiting, "title is", "titles are")} still waiting. Starboard tries again every six hours, and when a TMDB key is added.` : "Nothing is waiting now."));
        } catch (err) { said.replaceChildren(notice("danger", "Could not try again", err.message)); }
        again.disabled = false;
      });
      return section("tk-waiting", `Titles waiting for a match (${t.waiting_count})`,
        "Films and series the move into Reelix could not match. Starboard keeps the ids Radarr and Sonarr had for them and adds each to Reelix once it matches: every six hours, and as soon as a TMDB key is added.",
        rows, more, el("div", { class: "actions" }, again), said);
    }
  };
  draw();
  return pageSection("in-takeover", "Apps you already run", "Apps on this server from your own Compose file: moved into Reelix where Reelix replaces them, and run by Starboard from then on, with a way back.", box);
}

// Make the change now (owner, 10 November 2026): the set-up's change to the server, made by the Run first window,
// with its output live in a slide-out and a progress bar. The Starboard password first: only someone who knows it
// can change the server. Nobody can type commands into the server from here; the window runs only the installer.
async function hostChange(opener) {
  const input = el("input", { class: "input", id: "host-password", type: "password", autocomplete: "current-password", required: true });
  const err = el("span", { class: "field-error", id: "host-password-error", hidden: true });
  for (;;) {
    const asked = confirmDialog({ title: "Make the change to the server", message: "Starboard's helper on the server runs the installer with your answers. Enter your Starboard password to go ahead.",
      confirm: "Make the change", fields: [el("div", { class: "field" }, el("label", { for: input.id, text: "Your Starboard password" }), input, err)] });
    input.focus();
    if (!(await asked)) return;
    try { await api("/api/setup/host/apply", { method: "POST", body: { password: input.value } }); break; }
    catch (e) { err.textContent = e.status === 401 ? "That password is not right. Check Caps Lock and try again." : e.message; err.hidden = false; input.setAttribute("aria-invalid", "true"); input.value = ""; }
  }
  const bar = el("span");  // its width is set from here (a style property), which the content policy allows
  bar.style.width = "0%";
  const meter = el("div", { class: "progress", role: "progressbar", "aria-label": "Changing the server", "aria-valuemin": "0", "aria-valuemax": "100", "aria-valuenow": "0" }, bar);
  const now = el("p", { "aria-live": "polite", text: "Waiting for the helper on the server…" });
  const out = el("pre", { class: "code-block host-output", tabindex: "0", "aria-label": "What the installer says", hidden: true });
  const close = el("button", { type: "button", class: "btn", text: "Close" });
  const panel = sidePanel({ title: "Changing the server", opener, wide: true, body: [el("div", { class: "stack-4" }, now, meter, out)], foot: [close] });
  close.addEventListener("click", () => panel.close());
  let lost = 0;
  let same = "", since = Date.now();  // a step that does not move for 10 minutes has stopped (VM test N1)
  const tick = async () => {
    if (!document.body.contains(panel.layer)) return;
    let p;
    try { p = await api("/api/setup/host/progress"); lost = 0; }
    catch { lost += 1; now.textContent = "Starboard is starting again with its new settings…"; setTimeout(tick, 3000); return; }  // Docker access restarts it
    const shown = p.of ? Math.round(((p.n || 0) - (p.state === "running" ? 1 : 0)) / p.of * 100) : 0;
    out.hidden = !p.log;  // shown once the installer has said something
    if (p.log && out.textContent !== p.log) { out.textContent = p.log; out.scrollTop = out.scrollHeight; }
    if (p.state === "finished") {
      bar.style.width = "100%"; meter.setAttribute("aria-valuenow", "100");
      now.replaceChildren(notice("success", "The change is made", "Everything the set-up asked for on the server is done. You can close this."));
      close.classList.add("btn--primary");
      return;
    }
    if (p.state === "needs-password") {
      // The set-up helper never uses sudo: disk health is left for one command on the server.
      bar.style.width = "100%"; meter.setAttribute("aria-valuenow", "100");
      const cmd = "cd ~/starboard && ./install.sh --disk-health";
      now.replaceChildren(notice("warning", "One part needs the server's password", "Everything else is done. Disk health needs sudo, which Starboard never uses itself. Run this once in a terminal on the server:"),
        el("pre", { class: "code-block", text: cmd }), copyButton(cmd, "Copy the command"));
      return;
    }
    if (p.state === "failed") {
      now.replaceChildren(notice("danger", "The change stopped", "What the installer said is in the log on this page. Run first's window on the server shows it too, and the help has each error number."));
      return;
    }
    const where = `${p.state}|${p.n}|${p.name}|${(p.log || "").length}`;
    if (where !== same) { same = where; since = Date.now(); }
    if (p.state === "running" && Date.now() - since > 10 * 60 * 1000) {
      now.replaceChildren(notice("danger", "The change has stopped", "Nothing has happened for 10 minutes. What the installer said is in the log on this page. Select Make the change now again, or run ./install.sh in the Starboard folder on the server."));
      return;
    }
    bar.style.width = `${Math.max(3, Math.min(97, shown))}%`; meter.setAttribute("aria-valuenow", String(Math.max(0, shown)));
    now.textContent = p.state === "running" && p.name ? `Step ${p.n} of ${p.of}: ${p.name}` : p.window === false ? "Starboard's helper on the server is not answering. Run first or ./install.sh starts it again." : "Waiting for the helper on the server…";
    if (/sudo|password for/i.test((p.log || "").slice(-300))) now.textContent += " The Run first window on the server is asking for the server's password.";
    setTimeout(tick, 2000);
  };
  tick();
}
