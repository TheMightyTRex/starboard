// App details: the one slide-out for an app or a service, shared by System, Apps, Other services and Network.
// It shows the status, version and update, the addresses with copy buttons, the app's own warnings, Open as its
// own button and Edit (Manage apps, /settings.html?edit=<id>). The page loads the data once through
// AppDetails.load() and reads it back for its own rows, so the slide-out and the page always agree.
// The open app is in the address (?app=<id>), so Back closes it and a link can open it.

const AppDetails = (() => {
  const UPDATE_TYPES = ["sonarr", "radarr", "lidarr", "readarr", "prowlarr"];
  const state = {
    config: null, status: {}, outside: {}, updates: {}, updateErrors: {}, warnings: {}, recent: {},
    loaded: new Set(), errors: {}, checkedAt: null,
  };
  let current = null; // { id, panel, opener, pushed }
  const listeners = new Set();

  const sentence = (text) => (/[.!?]$/.test(text) ? text : `${text}.`);
  const clock = (d = new Date()) => d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  const service = (id) => state.config?.services.find((s) => s.id === id) || null;
  const hasOutside = () => state.config?.services.some((s) => s.enabled && s.outside_link);
  const hasUpdates = () => state.config?.services.some((s) => s.enabled && UPDATE_TYPES.includes(s.type));

  const fetchers = {
    config: async () => { state.config = await api("/api/config"); },
    status: async () => {
      const { items } = await api(fresh("/api/status"));
      state.status = Object.fromEntries(items.map((i) => [i.id, i]));
      state.checkedAt = new Date();
    },
    outside: async () => {
      if (!hasOutside()) { state.outside = {}; return; }
      const { items } = await api("/api/outside");
      state.outside = Object.fromEntries(items.map((i) => [i.id, i]));
    },
    updates: async () => {
      if (!hasUpdates()) { state.updates = {}; state.updateErrors = {}; return; }
      const { items, errors } = await api(fresh("/api/app-updates"));
      state.updates = Object.fromEntries(items.map((i) => [i.id, i]));
      state.updateErrors = Object.fromEntries(errors.map((e) => [e.service, e.message]));
    },
    uptime: async () => { state.uptime = await api("/api/uptime"); },
    numbers: async () => {  // the small numbers on cards: off in Settings, Performance saves a request per app
      state.numbers = state.config?.performance?.card_numbers === false ? {} : (await api(fresh("/api/numbers"))).items;
    },
    health: async () => {
      if (!hasUpdates() && !state.config?.services.some((s) => s.enabled && s.icon === "reelix")) { state.warnings = {}; return; }
      const { items, errors } = await api(fresh("/api/health"));
      state.healthErrors = Object.fromEntries((errors || []).map((e) => [e.service, e.message]));
      state.warnings = {};
      for (const item of items) (state.warnings[item.service] ||= []).push(item);
    },
  };

  // The server shares app answers for a few seconds; "Check again" asks the apps afresh.
  let asking = false;
  const fresh = (path) => (asking ? `${path}?fresh=1` : path);
  async function checkAgain(...parts) {
    asking = true;
    try { await load(...parts); } finally { asking = false; }
  }

  // load("status", "outside") fetches those parts (config first when it is not there yet).
  async function load(...parts) {
    if (!parts.length) parts = ["config", "status", "outside", "updates", "health"];
    if (!state.config && !parts.includes("config")) parts.unshift("config");
    if (parts.includes("config")) {
      try { await fetchers.config(); state.loaded.add("config"); delete state.errors.config; }
      catch (e) { state.errors.config = e.message; throw e; }
      parts = parts.filter((p) => p !== "config");
    }
    await Promise.all(parts.map(async (p) => {
      try { await fetchers[p](); state.loaded.add(p); delete state.errors[p]; }
      catch (e) { state.errors[p] = e.message; }
    }));
    listeners.forEach((fn) => fn(parts));
    if (current) fill();
  }

  // What the page and the slide-out say about one app. -----------------------------------------

  function status(s) {
    const st = state.status[s.id];
    if (!st) return { label: state.loaded.has("status") ? "Not checked" : "Checking", tone: state.loaded.has("status") ? "muted" : "neutral", state: "checking" };
    if (st.state === "up") return { label: "Running", tone: "success", state: "up" };
    if (st.state === "down") return { label: "Not responding", tone: "danger", state: "down" };
    return { label: "Not checked", tone: "muted", state: "unknown" };
  }

  function update(s) {
    const u = state.updates[s.id];
    return u?.available ? u : null;
  }

  // Reelix's own warnings come once for the whole of Reelix (DASH-176), so each of its cards shows them.
  function warnings(s) {
    if (s.icon !== "reelix") return state.warnings[s.id] || [];
    const ids = (state.config?.services || []).filter((x) => x.icon === "reelix").map((x) => x.id);
    return ids.flatMap((id) => state.warnings[id] || []);
  }

  function followers(s) {
    return (state.config?.services || []).filter((x) => x.enabled && x.follows === s.id);
  }

  // How Starboard checks a service, in words: "Follows qBittorrent", an address, or why it cannot.
  function how(s) {
    const st = state.status[s.id];
    const target = s.follows ? service(s.follows) : null;
    if (target) return `Follows ${target.name}`;
    if (st?.follows) return `Follows ${st.follows}`;
    if (s.url) return shortUrl(reachableUrl(s.url));
    return "No address, and it follows no other app, so Starboard cannot check it";
  }

  function homeAddress(s) {
    if (s.background) return s.url ? reachableUrl(s.url) : "";
    return s.link ? reachableUrl(s.link) : "";
  }

  // The button in a card or row that opens the slide-out.
  function opener(s, extra = {}) {
    return el("button", { type: "button", "data-app-open": s.id, "aria-haspopup": "dialog", onclick: (e) => open(s.id, e.currentTarget), ...extra }, s.name);
  }

  // renderKeyed in common.js fails when render() returns a new node in place of the old one (it inserts before a
  // node it has just removed), so rows are changed in place: morph(old, fresh) copies the new row into the old
  // one only when something changed, and puts focus back on the same control.
  function morph(old, fresh) {
    if (!old) return fresh;
    if (old.dataset.key !== undefined) fresh.dataset.key = old.dataset.key;
    if (old.outerHTML === fresh.outerHTML) return old;
    const controls = (node) => [...node.querySelectorAll("button, a, input, select")];
    const index = old.contains(document.activeElement) ? controls(old).indexOf(document.activeElement) : -1;
    for (const a of [...old.attributes]) old.removeAttribute(a.name);
    for (const a of [...fresh.attributes]) old.setAttribute(a.name, a.value);
    old.replaceChildren(...fresh.childNodes);
    if (index >= 0) controls(old)[index]?.focus({ preventScroll: true });
    return old;
  }

  // The app's icon, kept from the old row so a missing icon is not asked for again on every redraw.
  function iconFor(s, old) {
    const prev = old?.querySelector(`.app-icon[data-for="${CSS.escape(s.id)}"]`);
    if (prev) {
      // A copy loses the fallback to initials, so it is added again.
      const copy = prev.cloneNode(true);
      const img = copy.querySelector("img");
      if (img) {
        const fail = () => { img.remove(); copy.classList.remove("has-image"); copy.textContent = monogram(s.name); };
        if (img.complete && !img.naturalWidth) fail(); else img.addEventListener("error", fail);
      }
      return copy;
    }
    const node = appIcon(s);
    node.dataset.for = s.id;
    return node;
  }

  // The slide-out ------------------------------------------------------------------------------

  function addressRow(label, url, s, extra) {
    return [el("dt", { text: label }), el("dd", { class: "app-details__address" },
      el("code", { text: url }), copyButton(url, `${label.toLowerCase()} address for ${s.name}`), extra || null)];
  }

  function section(title, id, ...children) {
    return el("section", { class: "app-details__section", "aria-labelledby": id }, el("h3", { id, text: title }), ...children);
  }

  function body(s) {
    const st = state.status[s.id];
    const words = status(s);
    const out = [];
    const line = [];
    if (st?.state === "up" && st.ms !== undefined) line.push(`Replied in ${st.ms} ms`);
    if (st?.follows) line.push(`Follows ${st.follows}`);
    if (state.checkedAt) line.push(`checked at ${clock(state.checkedAt)}`);
    out.push(el("div", { class: "app-details__lead" }, appIcon(s),
      el("div", { class: "app-details__state" }, chip(words.label, words.tone),
        line.length ? el("span", { class: "small muted", text: line.join(" · ").replace(/^c/, "C") }) : null)));
    if (s.description) out.push(el("p", { class: "muted", text: s.description }));

    if (st?.state === "down") {
      out.push(el("div", { class: "notice", role: "status", "data-tone": "danger" }, icon("circle-alert"), el("div", { class: "notice__body" },
        el("span", { class: "notice__title", text: `Starboard could not reach ${s.name}` }),
        el("p", { text: `${sentence(st.message || "It did not answer")}${st.down_since ? ` Not responding for ${since(st.down_since)}.` : ""} Check that it is running, then select Check again.` }))));
    } else if (st?.state === "unknown" || (!st && state.loaded.has("status"))) {
      out.push(el("div", { class: "notice", role: "status", "data-tone": "warning" }, icon("triangle-alert"), el("div", { class: "notice__body" },
        el("span", { class: "notice__title", text: "Starboard cannot check this service" }),
        el("p", { text: "It has no address and follows no other app. Give it an address, or choose an app for it to follow, in Edit." }))));
    }

    const u = state.updates[s.id];
    if (u?.available) {
      out.push(el("div", { class: "notice", role: "status" }, icon("circle-arrow-up"), el("div", { class: "notice__body" },
        el("span", { class: "notice__title", text: "Update available" }),
        el("p", { text: `Version ${u.latest} is out. You have ${u.installed}. ${s.name} updates when its container image is updated.` }))));
    }

    // Addresses
    const home = homeAddress(s);
    const facts = [];
    if (home) facts.push(...addressRow("Home", home, s));
    if (s.outside_link) {
      const o = state.outside[s.id];
      const reach = !o ? (state.loaded.has("outside") ? null : chip("Checking from outside", "neutral"))
        : o.reachable ? chip("Reachable from outside", "success") : chip("Not reachable from outside", "warning");
      const note = o && !o.reachable && o.message ? el("span", { class: "small muted", text: o.message }) : null;
      facts.push(...addressRow("Outside", s.outside_link, s, reach ? el("span", { class: "app-details__reach" }, reach, note) : null));
    }
    out.push(section("Addresses", "app-details-addr", facts.length ? el("dl", { class: "facts" }, facts)
      : el("p", { class: "muted", text: s.follows ? `No address. Starboard shows the status of ${service(s.follows)?.name || "the app it follows"}.` : "No address yet. Add one in Edit." })));

    // Uptime, when Starboard watches in the background (Settings, Alerts).
    out.push(section("Uptime", "app-details-uptime", uptimeBlock(s)));

    // The last checks Starboard made of this app since it started (kept in memory, up to 20).
    if (s.url) out.push(section("Recent checks", "app-details-checks", recentBlock(s)));

    // The app's own warnings (only apps that report them).
    if (UPDATE_TYPES.includes(s.type) || s.icon === "reelix") {
      const list = warnings(s);
      let content;
      if (!state.loaded.has("health")) content = el("p", { class: "muted", text: state.errors.health ? `Could not ask ${s.name} for warnings: ${state.errors.health}` : "Asking…" });
      else if (state.healthErrors?.[s.id]) content = el("p", { class: "muted", text: `Could not ask ${s.name} for warnings: ${sentence(state.healthErrors[s.id])}` });
      else if (!list.length) content = el("p", { class: "muted", text: `${s.name} reports no warnings.` });
      else content = el("ul", { class: "rows" }, list.map((w) => el("li", { class: "row row--no-lead" },
        el("div", {}, el("div", { class: "row__title", text: w.message }),
          el("div", { class: "row__meta" }, w.first_seen ? `Since ${clockOrDay(w.first_seen)}` : "",
            /^https:\/\//.test(w.wiki || "") ? [w.first_seen ? " · " : "", el("a", { href: w.wiki, target: "_blank", rel: "noopener noreferrer" }, "How to fix it", el("span", { class: "visually-hidden", text: " (opens in a new tab)" }))] : null,
            w.fix ? [w.first_seen ? " · " : "", el("a", { href: w.fix.href, text: `Put it right in ${w.fix.label}` })] : null)),
        el("div", { class: "row__side" }, w.level === "error" ? chip("Error", "danger") : chip("Needs attention", "warning")))));
      out.push(section(`Warnings from ${s.name}`, "app-details-warn", content));
    }

    // About
    const about = [];
    if (!s.background) about.push(el("dt", { text: "Category" }), el("dd", { text: s.group || "Other" }));
    else about.push(el("dt", { text: "Kind" }), el("dd", { text: "Background service, with no web page" }));
    const version = u?.installed || st?.version;
    about.push(el("dt", { text: "Version" }), el("dd", { class: "num", text: version || "Not reported" }));
    if (u && !u.available) about.push(el("dt", { text: "Updates" }), el("dd", { text: "Up to date" }));
    else if (state.updateErrors[s.id]) about.push(el("dt", { text: "Updates" }), el("dd", { text: `Could not check: ${sentence(state.updateErrors[s.id])}` }));
    else if (!UPDATE_TYPES.includes(s.type) && !s.background) about.push(el("dt", { text: "Updates" }), el("dd", { text: `${s.name} does not say when it has an update` }));
    if (state.config.types[s.type]?.searchable) about.push(el("dt", { text: "Search" }), el("dd", { text: "Searched from Starboard's Search page" }));
    if (s.background) about.push(el("dt", { text: "Follows" }), el("dd", { text: s.follows ? (service(s.follows)?.name || "An app that is no longer set up") : "No other app" }));
    // Logs: a link to Dozzle when it is one of your apps. Starboard does not read logs itself.
    const dozzle = (state.config.services || []).find((x) => x.enabled && /dozzle/i.test(`${x.id} ${x.name} ${x.icon || ""}`) && x.link);
    if (dozzle && dozzle.id !== s.id) {
      about.push(el("dt", { text: "Logs" }), el("dd", {},
        el("a", { href: reachableUrl(dozzle.link), target: "_blank", rel: "noopener noreferrer" }, `Open ${dozzle.name}`,
          el("span", { class: "visually-hidden", text: " (opens in a new tab)" })),
        el("span", { class: "small muted", text: ` and choose ${s.container || s.id}` })));
    }
    // The sign-in Starboard made up for qBittorrent or NZBGet (DASH-184), after the Starboard password.
    if (["qbittorrent", "nzbget"].includes(s.type) && s.has_api_key) {
      const shown = el("span", { "aria-live": "polite" });
      const button = el("button", { type: "button", class: "btn btn--quiet" }, "Show its sign-in");
      button.addEventListener("click", async () => {
        const input = el("input", { class: "input", type: "password", id: `signin-pw-${s.id}`, autocomplete: "current-password" });
        const error = el("p", { class: "field__error", role: "alert" });
        if (!await confirmDialog({ title: `Show ${s.name}'s sign-in`, message: `Starboard made up ${s.name}'s sign-in when it installed it. Type your Starboard password to see it.`,
          confirm: "Show", fields: [el("div", { class: "field" }, el("label", { for: input.id, text: "Your Starboard password" }), input, error)] })) return;
        try {
          const r = await api("/api/services/sign-in", { method: "POST", body: { id: s.id, password: input.value } });
          shown.replaceChildren(el("span", { text: "User name " }), el("code", { text: r.user }), el("span", { text: ", password " }), el("code", { text: r.password }));
          button.hidden = true;
        } catch (e) { shown.replaceChildren(el("span", { class: "small", text: e.message })); }
      });
      about.push(el("dt", { text: "Sign-in" }), el("dd", {}, button, shown));
    }
    const fol = followers(s);
    about.push(el("dt", { text: "Followed by" }), el("dd", { text: fol.length ? fol.map((x) => x.name).join(", ") : "No other services" }));
    out.push(section(s.background ? "About this service" : "About this app", "app-details-about", el("dl", { class: "facts" }, about)));
    return out;
  }

  function since(t) {
    const mins = Math.max(1, Math.round((Date.now() / 1000 - t) / 60));
    if (mins < 60) return `${mins} ${mins === 1 ? "minute" : "minutes"}`;
    const hours = Math.round(mins / 60);
    return hours < 48 ? `${hours} ${hours === 1 ? "hour" : "hours"}` : `${Math.round(hours / 24)} days`;
  }

  function clockOrDay(t) {
    const d = new Date(t * 1000);
    return d.toDateString() === new Date().toDateString() ? clock(d) : d.toLocaleString("en-GB", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  }

  function recentBlock(s) {
    const rows = state.recent[s.id];
    if (!rows) {
      api(`/api/status?recent=${encodeURIComponent(s.id)}`).then((r) => { state.recent[s.id] = r.recent; if (current?.id === s.id) fill(); }).catch(() => {});
      return el("p", { class: "muted", text: "Loading…" });
    }
    if (!rows.length) return el("p", { class: "muted", text: "None since Starboard started." });
    return el("div", { class: "table-wrap", "data-stack": true }, el("table", { class: "table" },
      el("caption", { class: "visually-hidden", text: `Recent checks of ${s.name}, newest first` }),
      el("thead", {}, el("tr", {}, ["Time", "Result", "Answered in"].map((t) => el("th", { scope: "col", text: t })))),
      el("tbody", {}, rows.map((r) => el("tr", {},
        el("td", { "data-label": "Time", class: "numeric", text: clockOrDay(r.t) }),
        el("td", { "data-label": "Result" }, r.state === "up" ? chip("Running", "success") : chip("Not responding", "danger"),
          r.message ? el("div", { class: "small muted", text: r.message }) : null),
        el("td", { "data-label": "Answered in", class: "numeric", text: r.ms != null ? `${r.ms} ms` : "" }))))));
  }

  function uptimeBlock(s) {
    const u = state.uptime;
    if (!u) return el("p", { class: "muted", text: state.errors.uptime ? `Could not load the history: ${state.errors.uptime}` : "Loading…" });
    const row = u.items[s.id];
    if (!u.enabled && !row?.pct7 && row?.pct7 !== 0) {
      return el("p", { class: "muted" }, "Starboard keeps uptime history only while it watches in the background. Activate it in ",
        el("a", { href: "/settings-alerts.html", text: "Settings, Alerts" }), ".");
    }
    if (!row || row.pct24 === null) return el("p", { class: "muted", text: "No history yet. It starts with the next check." });
    const pct = (v) => `${String(v).replace(/\.0$/, "")}%`;
    const times = (n) => `${n} ${n === 1 ? "time" : "times"}`;
    const lines = [`Last 24 hours: answering ${pct(row.pct24)} of the time.`,
      row.pct7 === null ? "" : `Last 7 days: ${pct(row.pct7)}, stopped answering ${times(row.downs7)}.`,
      row.last_down ? `Last stopped ${new Date(row.last_down * 1000).toLocaleString("en-GB", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}.` : ""];
    return el("div", { class: "uptime" },
      el("p", { text: lines.filter(Boolean).join(" ") }),
      // The words above carry the meaning; the strip is a picture of the same 24 hours.
      el("div", { class: "uptime__strip", "aria-hidden": "true" }, row.slots.map((st) => el("span", { "data-state": st || "none" }))),
      el("div", { class: "uptime__scale small muted", "aria-hidden": "true" }, el("span", { text: "24 hours ago" }), el("span", { text: "Now" })));
  }

  function foot(s) {
    const st = state.status[s.id];
    const down = st?.state === "down";
    const link = !s.background && s.link ? reachableUrl(s.link) : "";
    const check = el("button", { type: "button", class: down || !link ? "btn btn--primary" : "btn btn--quiet", "data-check": true }, icon("refresh-cw"), el("span", { text: "Check again" }));
    check.addEventListener("click", async () => {
      check.disabled = true;
      check.setAttribute("aria-busy", "true");
      // This app only: its status (shared with the other pages), its recent checks, and its warnings and updates.
      try {
        const r = await api(`/api/status?id=${encodeURIComponent(s.id)}`);
        for (const row of r.items) state.status[row.id] = row;
        state.recent[s.id] = r.recent;
        state.checkedAt = new Date();
      } catch (e) { problem(e.message); }
      const more = [...(UPDATE_TYPES.includes(s.type) ? ["updates", "health"] : []), ...(s.outside_link ? ["outside"] : [])];
      if (more.length) await checkAgain(...more);
      listeners.forEach((fn) => fn(["status"]));  // the card on the page follows the slide-out
      if (current) fill();
      const again = current?.panel.foot.querySelector("[data-check]");
      if (again) { again.disabled = false; again.removeAttribute("aria-busy"); again.focus(); }
      const words = status(s);
      announce(`${s.name}: ${words.label}, checked at ${clock(state.checkedAt || new Date())}`);
    });
    const open = link ? el("a", { class: down ? "btn" : "btn btn--primary", href: link, target: "_blank", rel: "noopener noreferrer" },
      icon("external-link"), el("span", { text: `Open ${s.name}` }), el("span", { class: "visually-hidden", text: " (opens in a new tab)" })) : null;
    const edit = el("a", { class: "btn", href: `/settings.html?edit=${encodeURIComponent(s.id)}` }, icon("pencil"), el("span", { text: s.background ? "Edit service" : "Edit app" }));
    return down ? [check, open, edit] : [open, edit, check];
  }

  function fill() {
    const s = service(current.id);
    if (!s) { current.panel.close(); return; }
    current.panel.setTitle(s.name);
    const scroll = current.panel.body.scrollTop;
    current.panel.body.replaceChildren(...body(s));
    current.panel.body.scrollTop = scroll;
    // Keep the foot (and the focused button in it) unless what it offers changed.
    const next = foot(s).filter(Boolean);
    const sig = (nodes) => nodes.map((n) => `${n.className}|${n.textContent}`).join(";");
    if (sig(next) !== sig([...current.panel.foot.children])) {
      const hadFocus = current.panel.foot.contains(document.activeElement) ? document.activeElement.dataset.check !== undefined : false;
      current.panel.setFoot(next);
      if (hadFocus) current.panel.foot.querySelector("[data-check]")?.focus();
    }
  }

  function setAddress(id, push) {
    const url = new URL(location.href);
    if (id) url.searchParams.set("app", id); else url.searchParams.delete("app");
    if (push) history.pushState({ app: id }, "", url); else history.replaceState(history.state, "", url);
  }

  function open(id, openerNode = document.activeElement, { fromAddress = false } = {}) {
    const s = service(id);
    if (!s) return;
    if (current) { current.fromPop = true; current.panel.close(false); }
    const entry = { id, opener: openerNode, pushed: false, fromPop: false };
    entry.panel = sidePanel({
      title: s.name, opener: openerNode,
      onClose: () => {
        if (current === entry) current = null;
        if (entry.fromPop) return;
        if (!entry.opener?.isConnected) $(`[data-app-open="${CSS.escape(id)}"]`)?.focus();
        if (entry.pushed) history.back(); else setAddress(null, false);
      },
    });
    current = entry;
    entry.panel.setFoot(foot(s).filter(Boolean));
    fill();
    // Pages load only what they show; the slide-out asks for the rest (updates, warnings) when it opens.
    const missing = ["status", "outside", "updates", "health", "uptime"].filter((p) => !state.loaded.has(p) && !state.errors[p]);
    if (missing.length) load(...missing);
    if (!fromAddress) {
      entry.pushed = new URL(location.href).searchParams.get("app") !== id;
      setAddress(id, entry.pushed);
    }
  }

  window.addEventListener("popstate", () => {
    const id = new URL(location.href).searchParams.get("app");
    if (current && current.id !== id) { current.fromPop = true; current.panel.close(); }
    if (id && !current && state.config) open(id, null, { fromAddress: true });
  });

  // Open the app named in the address once the page has its data.
  function openFromAddress() {
    const id = new URL(location.href).searchParams.get("app");
    if (id && service(id) && !current) open(id, $(`[data-app-open="${CSS.escape(id)}"]`), { fromAddress: true });
  }

  return {
    state, load, checkAgain, status, update, warnings, how, homeAddress, opener, open, openFromAddress, service, clock, morph, iconFor, sentence,
    onChange: (fn) => listeners.add(fn),
  };
})();
