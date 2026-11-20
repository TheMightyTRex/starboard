// Settings, Performance: the preset and pictures.

const USAGE_CHOICES = [["ask", "Only when I press Sort by type"], ["open", "When I open Storage, if over a day old"], ["nightly", "Every night at 3 am"], ["weekly", "Every week, at 3 am"], ["off", "Off"]];

const STORAGE_REFRESH = [[0, "Only when I press Check again"], [60, "Every minute"], [300, "Every 5 minutes"]];

// Performance ---------------------------------------------------------------
// Presets set every optional piece of background work at once; changing one by hand makes it Custom.

// small, balanced and everything come from the server (config.preset_about), shared with the terminal set-up.
const PRESET_WORDS = {
  custom: "Your own choices. Changing anything here or on another Settings page makes it Custom.",
};

async function startPerformance() {
  const root = $("#performance-sections");
  const me = wants(root, "pf-now") ? await api("/api/self").catch(() => null) : null;
  const perf = () => config.performance;
  const redraw = () => startPerformance();
  const save = async (body) => {
    try { await saveGeneral(body); await redraw(); settingSaved(); return true; } catch (err) { problem(err.message); return false; }
  };
  const sw = (labelId, checked, onChange) => {
    const input = el("input", { type: "checkbox", role: "switch", "aria-labelledby": labelId, checked });
    input.addEventListener("change", async () => { if (!(await onChange(input.checked))) input.checked = !input.checked; });
    return el("label", { class: "switch" }, input);
  };
  const pick = (labelId, options, value, onChange) => {
    const select = el("select", { class: "select", "aria-labelledby": labelId },
      options.map(([v, t]) => el("option", { value: String(v), text: t, selected: String(v) === String(value) })));
    select.addEventListener("change", () => onChange(select.value, select.selectedOptions[0].text));
    return select;
  };

  // Now
  const count = (n, one, many) => `${n} ${n === 1 ? one : many}`;
  const span = (secs) => secs < 3600 ? count(Math.max(1, Math.round(secs / 60)), "minute", "minutes")
    : secs < 172800 ? count(Math.round(secs / 3600), "hour", "hours") : count(Math.round(secs / 86400), "day", "days");
  const threadWords = (names) => {
    const checks = names.filter((n) => /^apps_\d+$/.test(n)).length;
    const requests = names.filter((n) => /process_request_thread/.test(n)).length;
    const own = names.filter((n) => !/^apps_\d+$|process_request_thread|serve_forever|MainThread/.test(n));
    return [`${names.length} threads`, own.length ? `background: ${own.join(", ")}` : "no background work",
      checks ? `${checks} app ${checks === 1 ? "check" : "checks"} waiting` : "", requests ? `${requests} answering ${requests === 1 ? "a page" : "pages"}` : ""].filter(Boolean).join(" · ");
  };
  const now = me ? el("dl", { class: "facts" },
    el("dt", { text: "Memory" }), el("dd", { class: "numeric", text: formatBytes(me.memory) }),
    el("dt", { text: "Processor" }), el("dd", { class: "numeric", text: `${me.cpu_percent < 0.1 ? "under 0.1" : me.cpu_percent < 10 ? me.cpu_percent.toFixed(1) : Math.round(me.cpu_percent)}% on average, over the ${span(me.running_seconds)} since it started` }),
    el("dt", { text: "Running" }), el("dd", { text: threadWords(me.threads) })) : null;

  // Presets
  const presetForm = el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Preset" }),
    el("div", { class: "option-cards option-cards--row" }, ["small", "balanced", "everything", "custom"].map((k) => {
      const input = el("input", { type: "radio", name: "preset", value: k, checked: perf().preset === k });
      input.addEventListener("change", () => { if (k !== "custom") save({ preset: k }); });
      return el("label", { class: "option-card" }, input, el("strong", { text: k === "custom" ? "Custom" : config.presets[k] }), el("small", { text: k === "custom" ? PRESET_WORDS.custom : config.preset_about[k] }));
    })));

  // Background work
  const w = config.watch;
  const x = config.extras;
  const background = el("ul", { class: "settings-rows" },
    settingRow("System history", withCost("Readings for the charts on System, Overview.", "history"),
      el("div", { class: "inline-save" }, pick("pf-hist-every", [[60, "Every minute"], [300, "Every 5 minutes"], [900, "Every 15 minutes"]], perf().history_every,
        (v, t) => save({ performance: { history_every: Number(v) } })),
        sw("pf-hist-l", perf().history, (on) => save({ performance: { history: on } }))), "pf-hist-l"),
    settingRow("Watching and alerts", withCost("Checks your apps with no page open and sends alerts. Where alerts go: Settings, Alerts.", "watch"),
      el("div", { class: "inline-save" }, pick("pf-watch-every", [[1, "Every minute"], [5, "Every 5 minutes"], [10, "Every 10 minutes"], [15, "Every 15 minutes"], [30, "Every 30 minutes"], [60, "Every hour"]], w.every,
        (v, t) => save({ watch: { every: Number(v) } })),
        sw("pf-watch-l", w.enabled, (on) => save({ watch: { enabled: on } }))), "pf-watch-l"),
    settingRow("Download hours check", withCost("How often Starboard checks qBittorrent, NZBGet, SABnzbd and Soulseek (slskd) while download hours are active (Settings, Downloads, Download hours).", "scheduleEvery"),
      pick("pf-sched-l", [[60, "Every minute"], [300, "Every 5 minutes"]], perf().schedule_every,
        (v, t) => save({ performance: { schedule_every: Number(v) } })), "pf-sched-l"),
    settingRow("Live TV white logos", withCost("Only matters while the Live TV plug-in is active (Settings, Plug-ins).", "white"),
      sw("pf-white-l", x.white_logos, (on) => save({ extras: { white_logos: on } })), "pf-white-l"),
    settingRow("Keep applying imported history", withCost("Settings, Apps, Jellyfin, Import watch history.", "importKeep"),
      sw("pf-imp-l", x.import_keep, (on) => save({ extras: { import_keep: on } })), "pf-imp-l"),
    settingRow("Jellyfin user defaults", withCost("Settings, Apps, Jellyfin, User defaults.", "defaults"),
      sw("pf-def-l", x.defaults, (on) => save({ extras: { defaults: on } })), "pf-def-l"),
    settingRow("Keep applying listening progress", withCost("Settings, Apps, Audiobookshelf, Copy listening progress.", "listeningKeep"),
      sw("pf-listen-l", x.listening_keep, (on) => save({ extras: { listening_keep: on } })), "pf-listen-l"),
    settingRow("Work out what uses the space", withCost("Sorts your storage by type (TV, films, books and so on) for the charts on System, Storage.", "usage"),
      pick("pf-usage-l", USAGE_CHOICES, perf().usage_every, (v, t) => save({ performance: { usage_every: v } })), "pf-usage-l"),
    settingRow("Daily record of used space", withCost("For the Space used over time chart and its forecast on System, Storage.", "spaceLog"),
      sw("pf-space-l", perf().space_log, (on) => save({ performance: { space_log: on } })), "pf-space-l"),
    settingRow("Posters on Coming up and the Library", withCost("Inactive: Coming up shows each app's icon, and the Library shows titles on plain tiles.", "posters"),
      sw("pf-post-l", config.show_posters, (on) => save({ show_posters: on })), "pf-post-l"));

  // Pages
  const pages = el("ul", { class: "settings-rows" },
    settingRow("Downloads page updates", withCost("While Downloads is open and in view.", "downloadsRefresh"),
      pick("pf-dl-l", [[0, "Only when I press Check again"], [10, "Every 10 seconds"], [15, "Every 15 seconds"], [30, "Every 30 seconds"], [60, "Every minute"]], perf().downloads_refresh,
        (v, t) => save({ performance: { downloads_refresh: Number(v) } })), "pf-dl-l"),
    settingRow("Storage page updates", withCost("While Storage is open and in view.", "storageRefresh"),
      pick("pf-st-l", STORAGE_REFRESH, perf().storage_refresh, (v, t) => save({ performance: { storage_refresh: Number(v) } })), "pf-st-l"),
    settingRow("Monitor page readings", withCost("While Monitor is open and in view.", "monitorRefresh"),
      pick("pf-mon-l", [[2, "Every 2 seconds"], [5, "Every 5 seconds"], [10, "Every 10 seconds"]], perf().monitor_refresh,
        (v, t) => save({ performance: { monitor_refresh: Number(v) } })), "pf-mon-l"),
    settingRow("Numbers on app cards", withCost("Such as 3 in the queue or 120 wanted, on Apps.", "cardNumbers"),
      sw("pf-num-l", perf().card_numbers, (on) => save({ performance: { card_numbers: on } })), "pf-num-l"));

  root.removeAttribute("aria-busy");
  root.replaceChildren(...onlyParts(root, [
    now ? section("pf-now", "Starboard now", "Measured on this server while this page is open.", now) : null,
    section("pf-preset", "Preset", "Sets every setting on this page at once. Features you chose for what they do, such as Live TV and download hours, stay as they are.", presetForm),
    section("pf-bg", "Background work", "Runs with no page open. Each part's thread exists only while it is active.", background),
    section("pf-pages", "While a page is open", "Only while the page is open and in view; a hidden tab asks for nothing.", pages),
    ...(wants(root, "pf-pictures") ? picturesSection() : []),
  ]));
}

// Pictures (owner, 12 November 2026): the picture cache's size, how long pictures are kept, and Clear.
function picturesSection() {
  const facts = el("dl", { class: "facts" });
  const clear = el("button", { type: "button", class: "btn btn--danger" }, icon("trash-2"), "Clear the picture cache");
  const draw = (s) => facts.replaceChildren(el("dt", { text: "Pictures kept" }), el("dd", { text: s.pictures.toLocaleString("en-GB") }),
    el("dt", { text: "Space they use" }), el("dd", { text: formatBytes(s.bytes) }),
    el("dt", { text: "Removed when not shown for" }), el("dd", { text: `${s.unused_days} days` }));
  api("/api/pictures").then(draw).catch(() => facts.replaceChildren(el("p", { class: "small muted", text: "Could not count the pictures." })));
  clear.addEventListener("click", async () => {
    if (!await confirmDialog({ title: "Clear the picture cache?", confirm: "Clear", danger: true,
      message: "Every poster, cover and logo is fetched again the next time a page shows it, so pages are slower to fill for a while. Nothing else changes." })) return;
    clear.disabled = true;
    try { const out = await api("/api/pictures/clear", { method: "POST" }); toast(`Cleared ${out.cleared.toLocaleString("en-GB")} pictures`); draw(out); }
    catch (e) { problem(e.message, clear); }
    finally { clear.disabled = false; }
  });
  return [section("pf-pictures", "Pictures", "Posters, covers and logos are fetched once and kept on this server, so your browser never calls image sites. Each is fetched again after a week when shown.", facts),
    dangerSection("pf-danger", "Clear", "Each button asks before it does anything.", el("div", { class: "actions" }, clear))];
}
