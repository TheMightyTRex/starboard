// Install apps: a guide that sets up a media server (an *arr stack) for someone who has never done it, in groups
// such as Movies, TV and Ebooks. It explains each part, picks sensible apps and folders, writes a Compose file and
// a .env file, starts the apps only when you press Start and give your password, then talks you through connecting
// them. "Advanced settings" shows every app, the settings folder, user and group numbers, and the files themselves.
// Loaded by install-apps.html and setup-guide.html, after settings.js (it uses field, setError, notice, wizardFrame and appFinder).

// VPN providers, the same file the terminal set-up reads (web/vpn-providers.json): Gluetun's name, the provider's
// own spelling and its site.
let vpnProviders = null;
// The note for providers whose link is an affiliate link (the same words as vpn_ad in starboard/terminal_setup.py).
function vpnAd(names) {
  return `the ${names.join(" and ")} link is an affiliate link. If you sign up through it, ${names.join(" or ")} pays a small commission towards Starboard's development. You pay the same price.`;
}
async function loadVpnProviders() {
  if (!vpnProviders) {
    try { vpnProviders = (await (await fetch("/vpn-providers.json", { cache: "no-cache" })).json()).providers; } catch { vpnProviders = []; }
  }
  return vpnProviders;
}

// Sites to search (DASH-155): Reelix's built-in public sites and the step's words, the same file the terminal
// set-up reads (web/reelix-sites.json), so both ask the same questions in the same order.
let reelixSites = null;
// The TMDB key, language and Usenet server questions: the same words as the terminal set-up (web/setup-answers.json).
let setupAnswers = null;
async function loadSetupAnswers() {
  if (!setupAnswers) setupAnswers = await (await fetch("/setup-answers.json", { cache: "no-cache" })).json();
  return setupAnswers;
}

// A Test button and the line that says how it went, for the TMDB key and the Usenet server.
function testButton(label, run) {
  const said = el("div", { role: "status", "aria-live": "polite" });
  const button = el("button", { type: "button", class: "btn btn--secondary" }, label);
  button.addEventListener("click", async () => {
    button.disabled = true;
    said.replaceChildren(el("p", { class: "small muted", text: "Testing…" }));
    try {
      const r = await run();
      said.replaceChildren(r.ok ? notice("success", "It works", r.message) : notice("danger", "It did not work", r.message));
    }
    catch (e) { said.replaceChildren(notice("danger", "It did not work", e.message)); }
    finally { button.disabled = false; }
  });
  return el("div", { class: "stack-2" }, el("div", {}, button), said);
}

async function loadReelixSites() {
  if (!reelixSites) {
    try { reelixSites = await (await fetch("/reelix-sites.json", { cache: "no-cache" })).json(); } catch { reelixSites = { sites: [], words: {} }; }
  }
  return reelixSites;
}

function sitesSummary(sites, list) {
  const names = Object.fromEntries((list?.sites || []).map((s) => [s.id, s.name]));
  const words = [...(sites?.builtin || []).map((i) => names[i] || i.split(":").pop()),
    ...(sites?.own || []).map((o) => {
      let host = o.url;
      try { host = new URL(o.url).hostname; } catch { /* shown as typed */ }
      return `${o.name || host} (${o.kind === "newznab" ? "Newznab" : "Torznab"})`;
    })];
  return words.join(", ") || "None yet: add them later in Settings, Reelix";
}

// One Install apps flow for two places (DASH-269): this page on its own, for adding apps later, and inside the set-up
// guide, whose new install runs these steps in its own wizard with one step count. installFlow loads what the steps
// need and lists them; installStep draws one.
async function installFlow({ chosenMedia = "" } = {}) {
  const data = await api("/api/stack");
  const apps = Object.fromEntries(data.apps.map((a) => [a.key, a]));
  const T = await stepTable();  // the step names the terminal set-up uses too
  // Reelix, or Reelix with YouTube and Spotify downloads: the second only when it can be downloaded now.
  let editions = [];
  try { editions = (await api("/api/reelix/editions")).editions.filter((e) => e.available); } catch { /* Reelix it is */ }
  editions.sort((a, b) => b.recommended - a.recommended);
  data.reelix_editions = editions;
  let advanced = false;
  try { advanced = localStorage.getItem("install-advanced") === "1"; } catch { /* private window */ }
  const state = {
    advanced, chosenMedia,
    heldPassword: "",  // the password typed on the Check step, reused by Start the apps; this page only, never stored
    groups: new Set(data.groups.filter((g) => g.default).map((g) => g.key)),
    apps: new Set(data.apps.filter((a) => a.default && !a.installed && a.groups.some((g) => data.groups.find((x) => x.key === g).default)).map((a) => a.key)),
    config_dir: data.defaults.config_dir, data_dir: chosenMedia || data.defaults.data_dir,
    puid: data.defaults.puid, pgid: data.defaults.pgid, tz: data.defaults.tz,
    vpn: { provider: "", type: "wireguard" }, moving: new Set(), written: null, pool: null, reelix_edition: "lite",
    install: "basics", installApplied: false, usenet: "nzbget", sites: { builtin: [], own: [] },
    tmdb: "", language: "English", usenetServer: null,
  };
  // The steps follow the choices: VPN only when Gluetun is ticked, Usenet only when SABnzbd or NZBGet is, Moving over
  // only when there is something to move. Check and Start are listed apart, so the guide can put How much it does
  // between them and the rest (DASH-265).
  const before = () => [
    { id: "groups", ...stepNamed(T, "apps"), skippable: false,
      intro: "Tick what you want. Starboard picks the apps for each one; you can see and change them with Advanced settings." },
    ...(state.chosenMedia ? [] : [{ id: "folders", ...stepNamed(T, "folders"), skippable: false,
      intro: "One media folder holds your downloads and your library together, so a finished download moves into the library instantly." }]),
    ...(state.apps.has("gluetun") ? [{ id: "vpn", ...stepNamed(T, "vpn"), skippable: false,
      intro: "Downloads go through your VPN, so your internet provider sees only the VPN. You need an account with a VPN provider." }] : []),
    ...(state.apps.has("sabnzbd") || state.apps.has("nzbget") ? [{ id: "usenet", ...stepNamed(T, "usenet"), skippable: false }] : []),
    ...(state.apps.has("reelix") ? [{ id: "sites", ...stepNamed(T, "sites"), skippable: false },
      { id: "films", ...stepNamed(T, "films"), skippable: false }] : []),
    ...(data.servers.length ? [{ id: "moving", ...stepNamed(T, "moving"),
      intro: "Starboard found these on this computer. Nothing is copied or changed until the new apps are running and you choose." }] : []),
  ];
  const finish = () => [
    { id: "review", ...stepNamed(T, "check"), skippable: false },
    { id: "start", ...stepNamed(T, "start-apps"), skippable: false },
  ];
  return { state, data, apps, T, before, finish, ids: () => new Set([...before(), ...finish()].map((x) => x.id)) };
}

async function startInstall() {
  const root = $("#install");
  root.removeAttribute("aria-busy");
  const params = new URLSearchParams(location.search);
  const fromGuide = params.get("from") === "guide";
  // An older link from the set-up guide's Storage step carries the media folder already (DASH-103): use it.
  const chosenMedia = fromGuide && /^\/[A-Za-z0-9._/-]{0,250}$/.test(params.get("media") || "") ? params.get("media") : "";
  let flow;
  try { flow = await installFlow({ chosenMedia }); } catch (e) { root.replaceChildren(notice("danger", "Could not look", e.message)); return; }
  // DASH-173: once the server is set up, Install apps opens on what is installed; the wizard is a choice.
  if (!fromGuide && !params.get("wizard") && config?.setup_guide_done) {
    const chosen = new Set(flow.data.chosen || []);
    const have = flow.data.apps.filter((a) => chosen.has(a.key));
    const more = flow.data.apps.filter((a) => !chosen.has(a.key) && !a.installed);
    const again = el("a", { class: "btn", href: "/install-apps.html?wizard=1" }, icon("play"), "Run the set-up again");
    $(".page-head .page-head__summary")?.replaceChildren("What is installed, and what you can add.");
    root.replaceChildren(
      section("ia-have", "Installed", `${have.length} ${have.length === 1 ? "app" : "apps"} that Starboard installed and runs.`,
        el("ul", { class: "rows" }, have.map((a) => el("li", { class: "row row--no-lead" },
          el("div", {}, el("div", { class: "row__title", text: a.name }), el("div", { class: "row__meta", text: a.notes || "" })))))),
      more.length ? section("ia-more", "You can add", "Optional apps for what your server does. Adding them runs the set-up with them ticked.",
        el("ul", { class: "rows" }, more.map((a) => el("li", { class: "row row--no-lead" },
          el("div", {}, el("div", { class: "row__title", text: a.name }), el("div", { class: "row__meta", text: a.notes || "" })),
          el("div", { class: "row__side" }, el("a", { class: "btn btn--quiet btn--compact", href: `/install-apps.html?wizard=1&add=${encodeURIComponent(a.key)}` },
            "Add", el("span", { class: "visually-hidden", text: ` ${a.name}` }))))))) : null,
      section("ia-change", "Change your install", "Basics or Full, the Usenet app and the Reelix version are on Settings, Your install. The set-up asks every question again and changes nothing until you write the files.",
        el("div", { class: "actions" }, el("a", { class: "btn btn--primary", href: "/settings-install.html" }, "Open Your install"), again)));
    return;
  }
  const adding = params.get("add");
  if (adding && flow.apps[adding]) { flow.state.apps.add(adding); flow.state.install = "custom"; }
  const { state, data, apps, T } = flow;
  const build = () => [{ id: "welcome", ...stepNamed(T, "welcome"), skippable: false }, ...flow.before(), ...flow.finish()];
  const finishTo = fromGuide ? "/setup-guide.html" : "/index.html";

  const go = async (id) => {
    const steps = build();
    const index = Math.max(0, steps.findIndex((s) => s.id === id));
    const step = steps[index];
    let save = async () => true;
    let loading = true;
    step.nodes = [el("p", { class: "muted", text: "Loading…" })];
    const frame = () => wizardFrame({ root, steps, index, busy: loading,
      continueText: { welcome: "Begin", review: "Write the files", start: fromGuide ? "Back to the set-up guide" : "Go to Apps" }[step.id] || "Continue",
      onBack: () => go(steps[index - 1].id), onSkip: () => go(steps[index + 1].id),
      onContinue: async (e) => {
        const button = e.currentTarget;
        button.disabled = true;
        try {
          if (await save()) {
            if (step.id === "start") location.href = finishTo;
            else { const next = build(); go(next[next.findIndex((s) => s.id === step.id) + 1].id); }
          }
        } catch (err) { problem(err.message); }
        finally { if (button.isConnected) button.disabled = false; }
      } });
    frame();
    const content = await installStep(step.id, state, data, apps, go);
    if (!content) return;  // the step was drawn again by a newer go(), such as after Basics was applied
    step.nodes = content.nodes;
    save = content.save;
    loading = false;
    frame().heading.focus();
  };
  go("welcome");
}

function memoryText(mb) { return mb >= 1000 ? `${(mb / 1000).toFixed(1)} GB` : `${mb} MB`; }

// The first problem found: shown by its field, which gets focus. Returns false so a save can return it.
function stop(control, message) {
  if (control.fieldError) setError(control, message); else problem(message, control);
  control.focus();
  return false;
}

function clearError(control) {
  if (control.fieldError) setError(control, "");
}

async function installStep(id, state, data, apps, go) {
  let nodes = [];
  let save = async () => true;
  const groupName = (k) => data.groups.find((x) => x.key === k)?.name || k;

  if (id === "welcome") {
    const adv = el("input", { type: "checkbox", checked: state.advanced });
    nodes = [
      el("p", { text: "A media server is a few apps that work together. Each one does one job, and they pass work to each other:" }),
      el("ol", { class: "stack-1" },
        el("li", {}, el("strong", { text: "Find and choose. " }), "Reelix keeps a list of the films, series, books, music and radio you want, searches the sites that list them, and picks the best copy when it appears. The people you share with can ask for things in it too."),
        el("li", {}, el("strong", { text: "Download. " }), "qBittorrent (or SABnzbd) downloads it, through your VPN if you have one."),
        el("li", {}, el("strong", { text: "Sort. " }), "Reelix renames the finished file and moves it into your library."),
        el("li", {}, el("strong", { text: "Watch and listen. " }), "Jellyfin plays your films and series on TVs, phones and browsers; Audiobookshelf plays audiobooks.")),
      el("p", { text: "This guide picks the apps for what you want, sets up the folders, writes the set-up file and starts the apps. Starboard sets Reelix up and connects it to the download apps for you; the rest it shows you step by step. It takes about 15 minutes; the downloads take longer." }),
      el("h3", { text: "You need" }),
      el("ul", {}, el("li", { text: "A folder or drive with room for your media." }),
        el("li", { text: "Docker on this computer (it is, if Starboard runs in Docker)." }),
        el("li", { text: "Optional: a VPN account, to keep your downloads private." })),
      el("label", { class: "check" }, adv, el("span", { class: "check__text" }, el("strong", { text: "Advanced settings" }),
        el("span", { class: "check__hint", text: "Show every app in each group, the settings folder, the user and group numbers and time zone, and the files before they are written. The defaults suit most people." }))),
    ];
    save = async () => {
      state.advanced = adv.checked;
      try { localStorage.setItem("install-advanced", adv.checked ? "1" : "0"); } catch { /* private window */ }
      return true;
    };
  } else if (id === "groups") {
    // Basics, Full install or Everything (stack.INSTALLS), or Choose myself. The first time, Basics is applied.
    const applyInstall = async (key) => {
      const c = await api("/api/stack/install", { method: "POST", body: { install: key, usenet: state.usenet } });
      state.install = key;
      state.installName = c.name;
      state.apps = new Set(c.apps);
      state.groups = new Set(c.groups.filter((g) => data.groups.some((x) => x.key === g)));
      state.reelix_edition = c.reelix_edition;
      state.installNote = c.note || "";
      remember({ health: !!c.disk_health });  // the set-up guide's disk health answer starts from this
      state.installApplied = true;
    };
    if (!state.installApplied && state.install !== "custom") {
      try { await applyInstall(state.install); } catch { state.install = "custom"; }
      return go("groups");  // drawn again, so the list of steps follows Basics (its VPN and Usenet steps)
    }
    const total = el("p", { class: "small muted", "aria-live": "polite" });
    let afterCount = () => {};
    const count = () => {
      afterCount();
      const mb = [...state.apps].reduce((n, k) => n + apps[k].memory, 0);
      total.textContent = `${state.apps.size} ${state.apps.size === 1 ? "app" : "apps"}, using about ${memoryText(mb)} of memory together when idle.`;
    };
    const appBoxes = {};
    const error = el("div", { role: "alert" });
    const needsNote = el("div", { "aria-live": "polite" });
    // Ticks what the ticked apps need (stack.NEEDS); a list of options means one of them, the first if none.
    const addNeeds = () => {
      const added = [];
      let changed = true;
      while (changed) {
        changed = false;
        for (const k of [...state.apps]) {
          for (const opts of (data.needs || {})[k] || []) {
            if (opts.some((o) => state.apps.has(o) || apps[o]?.installed)) continue;
            const pick = opts.find((o) => apps[o]) || opts[0];
            if (!apps[pick]) continue;
            state.apps.add(pick); added.push([pick, k]); changed = true;
            if (appBoxes[pick]) appBoxes[pick].checked = true;
            apps[pick].groups.forEach((g) => state.groups.add(g));
          }
        }
      }
      needsNote.replaceChildren(...(added.length ? [notice("info", "Also ticked", added.map(([p, k]) => `${apps[p].name}, which ${apps[k].name} needs`).join("; ") + ".")] : []));
      return added;
    };
    const chooseMyself = () => {
      if (state.install === "custom") return;
      state.install = "custom";
      const r = document.getElementById("install-custom");
      if (r) r.checked = true;
    };
    const groupRow = (g) => {
      const own = data.apps.filter((a) => a.groups[0] === g.key);
      const shared = data.apps.filter((a) => a.groups.includes(g.key) && a.groups[0] !== g.key);
      const groupBox = el("input", { type: "checkbox", checked: state.groups.has(g.key) });
      const includes = el("small", { class: "muted" });
      const showIncludes = () => {
        const names = own.filter((a) => state.apps.has(a.key)).map((a) => a.name);
        includes.textContent = names.length ? `With ${names.join(", ")}` : "";
      };
      const list = el("div", { class: "switch-list install-apps", hidden: !(state.advanced && state.groups.has(g.key)) }, own.map((a) => {
        const box = el("input", { type: "checkbox", checked: state.apps.has(a.key), disabled: a.installed });
        appBoxes[a.key] = box;
        box.addEventListener("change", () => {
          chooseMyself();
          if (box.checked) state.apps.add(a.key); else state.apps.delete(a.key);
          addNeeds(); count(); showIncludes();
        });
        const busyPort = a.ports.find((p) => !p.free);
        const hint = [a.installed ? "Already running here" : "", a.notes,
          a.groups.length > 1 ? `Also for ${a.groups.slice(1).map((k) => groupName(k).toLowerCase()).join(", ")}` : "",
          busyPort && !a.installed ? `Port ${busyPort.port} is in use, so it will use the next free one` : "",
          a.later ? "Starts once you add its settings file" : "", `About ${memoryText(a.memory)}`].filter(Boolean).join(" · ");
        return el("label", { class: "check" }, box, el("span", { class: "check__text" }, el("strong", { text: a.name }), el("span", { class: "check__hint", text: hint })));
      }), shared.map((a) => el("p", { class: "small muted", text: `${a.name} is under ${groupName(a.groups[0])}.` })));
      groupBox.addEventListener("change", () => {
        chooseMyself();
        error.replaceChildren();
        list.hidden = !(state.advanced && groupBox.checked);
        if (groupBox.checked) state.groups.add(g.key); else state.groups.delete(g.key);
        own.filter((a) => !a.installed).forEach((a) => {
          const on = groupBox.checked && a.default;
          appBoxes[a.key].checked = on;
          if (on) state.apps.add(a.key); else state.apps.delete(a.key);
        });
        addNeeds();
        count();
        showIncludes();
      });
      showIncludes();
      return el("div", { class: "install-group" },
        el("label", { class: "option-card" }, groupBox, el("strong", { text: g.name }), el("small", { text: g.about }), includes), list);
    };
    const kinds = [["media", "Media"], ["core", "Watching and downloading"], ["extras", "Extras"]];
    // Which Reelix, shown while Reelix is ticked. Both keep the same settings, so Settings, Reelix switches later.
    const which = el("fieldset", { class: "stack-2" }, el("legend", { class: "h3", text: "Which Reelix?" }),
      el("div", { class: "option-cards" }, data.reelix_editions.map((e) => {
        const radio = el("input", { type: "radio", name: "reelix-edition", value: e.key, checked: state.reelix_edition === e.key });
        radio.addEventListener("change", () => { state.reelix_edition = e.key; });
        return el("label", { class: "option-card" }, radio,
          el("strong", { text: e.name + (e.recommended ? " (recommended)" : "") }), el("small", { text: e.about }));
      })), el("p", { class: "small muted", text: "You can switch either way later in Settings, Reelix. Your library and settings stay." }));
    const showWhich = () => { which.hidden = data.reelix_editions.length < 2 || !state.apps.has("reelix"); };
    afterCount = showWhich;
    const installs = [...(data.installs || []), { key: "custom", name: "Choose myself", about: "Tick each group below, and with Advanced settings each app." }];
    const whatToInstall = el("fieldset", { class: "stack-2" }, el("legend", { class: "h3", text: "What to install" }),
      el("div", { class: "option-cards" }, installs.map((i) => {
        const radio = el("input", { type: "radio", name: "install", id: `install-${i.key}`, value: i.key, checked: state.install === i.key });
        radio.addEventListener("change", async () => {
          if (i.key === "custom") { state.install = "custom"; return; }
          try { await applyInstall(i.key); } catch (e) { error.replaceChildren(notice("danger", "Could not choose that", e.message)); return; }
          go("groups");
        });
        return el("label", { class: "option-card" }, radio,
          el("strong", { text: i.name + (i.recommended ? " (recommended)" : "") }), el("small", { text: i.about }));
      })),
      ...(state.installNote ? [notice("info", "Reelix Lite for now", state.installNote)] : []),
      // Full install and Everything: NZBGet (lighter) or SABnzbd for Usenet. Basics always has NZBGet.
      ...((data.installs || []).find((i) => i.key === state.install)?.usenet_choice ? [el("fieldset", { class: "stack-2" },
        el("legend", { class: "h3", text: "Usenet app" }),
        el("div", { class: "option-cards option-cards--row" }, [
          { k: "nzbget", n: "NZBGet (recommended)", t: "Light on memory and processor." },
          { k: "sabnzbd", n: "SABnzbd", t: "If you know it already, or want its own extras." }].map(({ k, n, t }) => {
          const r = el("input", { type: "radio", name: "usenet", id: `usenet-${k}`, value: k, checked: state.usenet === k });
          r.addEventListener("change", async () => {
            state.usenet = k;
            try { await applyInstall(state.install); } catch (e) { error.replaceChildren(notice("danger", "Could not choose that", e.message)); return; }
            go("groups");
          });
          return el("label", { class: "option-card" }, r, el("strong", { text: n }), el("small", { text: t }));
        })))] : []),
      el("p", { class: "small muted", text: "The groups below show what is ticked. Changing any of them makes it your own choice." }));
    nodes = [whatToInstall, ...kinds.map(([kind, name]) => el("fieldset", { class: "stack-2" }, el("legend", { class: "h3", text: name }),
      el("div", { class: "option-cards" }, data.groups.filter((g) => g.kind === kind).map(groupRow)))), which, needsNote, total, error];
    count();
    save = async () => {
      if (!state.apps.size) { error.replaceChildren(notice("danger", "Nothing ticked", "Tick at least one thing for your server to do.")); return false; }
      const findable = ["reelix", "radarr", "sonarr", "lidarr", "bookshelf", "storyarr", "kapowarr"].some((k) => state.apps.has(k));
      const downloader = ["qbittorrent", "nzbget", "sabnzbd"].some((k) => state.apps.has(k) || apps[k]?.installed);
      if (findable && !downloader && !state.warnedDownloads) {
        state.warnedDownloads = true;
        error.replaceChildren(notice("warning", "Nothing to download with", "Tick Downloads too, so the apps have something to download with. Or choose Continue again to go on without it."));
        return false;
      }
      // DASH-131: torrents without a VPN are asked about once, in plain words (the terminal set-up asks the same).
      if (state.apps.has("qbittorrent") && !state.apps.has("gluetun") && !apps.gluetun?.installed && !state.warnedVpn) {
        state.warnedVpn = true;
        const w = (await loadSetupAnswers()).novpn;
        error.replaceChildren(notice("warning", w.title, `${w.text} ${w.browser}`));
        return false;
      }
      return true;
    };
  } else if (id === "folders") {
    const cfg = el("input", { class: "input", value: state.config_dir, spellcheck: "false", autocomplete: "off" });
    const other = el("input", { class: "input", value: state.data_dir, spellcheck: "false", autocomplete: "off" });
    const radios = data.existing_media.map((m) => ({ m, input: el("input", { type: "radio", name: "media", value: m.path, checked: m.path === state.data_dir }) }));
    const otherRadio = el("input", { type: "radio", name: "media", value: "", checked: !radios.some((r) => r.input.checked) });
    const puid = el("input", { class: "input", inputmode: "numeric", value: state.puid });
    const pgid = el("input", { class: "input", inputmode: "numeric", value: state.pgid });
    const tz = el("input", { class: "input", value: state.tz, spellcheck: "false" });
    const poolBox = el("div", { class: "stack-2" });
    const showPool = () => poolBox.replaceChildren(...(state.pool ? [notice("info", `Pool: ${state.pool.path}`,
      `Made from ${state.pool.mounts.join(", ")}. Run these commands on the server before you start the apps.`),
      el("pre", { class: "code-block", text: state.pool.commands }), copyButton(state.pool.commands, "Copy the commands")] : []));
    const poolButton = el("button", { type: "button", class: "btn" }, icon("layers"), state.pool ? "Change the pool" : "Join several drives into one");
    poolButton.addEventListener("click", async () => {
      const made = await poolDialog(data.drives, state.pool);
      if (!made) return;
      state.pool = made;
      otherRadio.checked = true;
      other.value = made.path;
      showPool();
      announce(`The media folder is now the pool, ${made.path}`);
    });
    showPool();
    nodes = [el("div", { class: "form-stack" },
      radios.length ? el("fieldset", { class: "stack-2" }, el("legend", { text: "Media folder" }),
        el("p", { class: "small muted", text: "Your other apps already use these. Choosing one points the new apps at your media where it is; nothing is moved." }),
        el("div", { class: "option-cards" }, radios.map(({ m, input }) => el("label", { class: "option-card" }, input,
          el("strong", { text: m.path }), el("small", { text: `Used by ${m.used_by.join(", ")}` }))),
          el("label", { class: "option-card" }, otherRadio, el("strong", { text: "Another folder" }), el("small", { text: "Type it below." }))))
        : null,
      folderField({ input: other, label: radios.length ? "Other media folder" : "Media folder", required: !radios.length,
        hint: "A folder on the drive with the most room, such as /srv/media, typed or chosen with Browse. Starboard makes movies, tv, books and downloads folders inside it." }).node,
      el("div", { class: "stack-2" },
        el("p", { class: "small muted", text: "Several drives? A pool joins them into one folder, so the apps see one big drive. Nothing on them is erased." }),
        el("div", { class: "actions" }, poolButton), poolBox),
      state.advanced ? folderField({ input: cfg, label: "Settings folder", required: true, hint: "Each app gets its own folder inside it, such as …/config/sonarr. Back this folder up." }).node : null,
      state.advanced ? el("fieldset", { class: "form-stack" }, el("legend", { text: "User, group and time zone" }),
        field("User number (PUID)", puid, { required: true, short: true, hint: "The apps run as this user, so you own their files. Starboard's own user by default." }),
        field("Group number (PGID)", pgid, { required: true, short: true }),
        field("Time zone", tz, { required: true, hint: "Such as Europe/London." })) : null),
    ];
    save = async () => {
      [cfg, other, puid, pgid, tz].forEach(clearError);
      const picked = radios.find((r) => r.input.checked);
      const media = picked ? picked.m.path : other.value.trim();
      if (!/^\/[\w./-]+$/.test(media)) return stop(other, "Enter the full path of a folder, starting with /, such as /srv/media");
      if (state.advanced) {
        if (!/^\/[\w./-]+$/.test(cfg.value.trim())) return stop(cfg, "Enter the full path of a folder, starting with /");
        if (!(Number(puid.value) > 0 && Number(puid.value) < 65536)) return stop(puid, "Enter a number from 1 to 65535");
        if (!(Number(pgid.value) > 0 && Number(pgid.value) < 65536)) return stop(pgid, "Enter a number from 1 to 65535");
        if (!/^[A-Za-z0-9_+/-]{1,40}$/.test(tz.value.trim())) return stop(tz, "Enter a time zone such as Europe/London");
      }
      state.data_dir = media;
      if (state.advanced) Object.assign(state, { config_dir: cfg.value.trim(), puid: Number(puid.value), pgid: Number(pgid.value), tz: tz.value.trim() });
      // The folders are checked here; the VPN on its own step.
      try { await api("/api/stack/preview", { method: "POST", body: body({ ...state, apps: new Set([...state.apps].filter((k) => k !== "gluetun")) }) }); return true; }
      catch (e) { return stop(other, e.message); }
    };
  } else if (id === "vpn") {
    // One card per provider with its site (opens in a new tab), then "Another one". Nothing is chosen for you.
    const providers = await loadVpnProviders();
    const known = providers.some((v) => v.id === state.vpn.provider);
    const pickName = `vpn-provider-${Date.now()}`;
    const other = el("input", { class: "input", autocomplete: "off", spellcheck: "false", value: known ? "" : (state.vpn.provider || ""), id: "vpn-other" });
    const otherBox = el("div", { class: "form-stack" }, field("Its name, as Gluetun's list writes it", other, { required: true },
      { hint: "Gluetun's list of providers is on its wiki, under Providers. Type the name in small letters, such as mullvad." }));
    // An affiliate link (affiliate: true) is marked as paid and says so: "Ad" on the card, and the note under the hint.
    const card = (id, name, site, affiliate) => {
      const link = site ? newTabLink(site, new URL(site).host.replace(/^www\./, ""), { about: `${name}'s site${affiliate ? ", affiliate link" : ""}` }) : null;
      if (link && affiliate) link.rel = "noopener noreferrer sponsored";
      return el("label", { class: "option-card" },
        el("input", { type: "radio", name: pickName, value: id, checked: id === "other" ? (!known && !!state.vpn.provider) : state.vpn.provider === id }),
        el("strong", { text: name }),
        link ? el("small", {}, link) : el("small", { text: "Type its name below" }),
        affiliate ? el("small", { class: "muted", "aria-hidden": "true", text: "Ad: affiliate link" }) : null);
    };
    const paid = providers.filter((v) => v.affiliate).map((v) => v.name);
    const provider = el("fieldset", { "aria-required": "true" }, el("legend", { class: "field__label" }, "VPN provider", requiredMark()),
      el("p", { class: "hint", text: "Choose the one you have an account with. Each link opens the provider's site in a new tab." }),
      paid.length ? el("p", { class: "small" }, el("strong", { text: "Ad: " }), vpnAd(paid)) : null,
      el("div", { class: "option-cards option-cards--row" }, providers.map((v) => card(v.id, v.name, v.site, v.affiliate)),
        card("other", "Another one that Gluetun supports", "")));
    const picked = () => $(`input[name="${pickName}"]:checked`, provider)?.value || "";
    const showOther = () => { otherBox.hidden = picked() !== "other"; };
    provider.addEventListener("change", showOther);
    showOther();
    const type = el("fieldset", { class: "segmented" }, el("legend", { class: "visually-hidden", text: "Connection" }),
      [["wireguard", "WireGuard"], ["openvpn", "OpenVPN"]].map(([v, t]) => el("label", {},
        el("input", { type: "radio", name: "vpn-type", value: v, checked: (state.vpn.type || "wireguard") === v }), el("span", { text: t }))));
    const inputs = {
      wireguard_private_key: el("input", { class: "input", type: "password", autocomplete: "off", value: state.vpn.wireguard_private_key || "" }),
      wireguard_addresses: el("input", { class: "input", autocomplete: "off", placeholder: "ends with /32", value: state.vpn.wireguard_addresses || "" }),
      openvpn_user: el("input", { class: "input", autocomplete: "off", value: state.vpn.openvpn_user || "" }),
      openvpn_password: el("input", { class: "input", type: "password", autocomplete: "off", value: state.vpn.openvpn_password || "" }),
    };
    const countries = el("input", { class: "input", placeholder: "such as Netherlands", value: state.vpn.countries || "" });
    const wg = el("div", { class: "form-stack" },
      field("WireGuard private key", inputs.wireguard_private_key, { required: true, hint: "On your provider's site, make a WireGuard configuration (sometimes called a config file or a device). Copy the PrivateKey line." }),
      field("WireGuard address", inputs.wireguard_addresses, { required: true, hint: "The Address line from the same configuration, ending /32." }));
    const ovpn = el("div", { class: "form-stack" },
      field("OpenVPN user name", inputs.openvpn_user, { required: true, hint: "Your provider's OpenVPN or service user name. It is often not the one you sign in to their website with." }),
      field("OpenVPN password", inputs.openvpn_password, { required: true }));
    const kind = () => $("input:checked", type)?.value || "wireguard";
    // DASH-233: NordVPN hides its WireGuard key; an access token from Nord Account fetches it (the terminal asks too).
    const nordToken = el("input", { class: "input", type: "password", autocomplete: "off", spellcheck: "false" });
    const nord = el("details", { class: "disclosure" }, el("summary", { text: "Get the key from NordVPN with an access token" }),
      el("div", { class: "disclosure__body stack-2" },
        el("p", { class: "small", text: "In Nord Account, choose NordVPN, then Manual setup, and make an access token. Starboard uses it once to fetch your key and does not keep it." }),
        field("NordVPN access token", nordToken),
        testButton("Get my key", async () => {
          const r = await api("/api/setup/nordvpn-key", { method: "POST", body: { token: nordToken.value.trim() } });
          if (r.ok) { inputs.wireguard_private_key.value = r.key; inputs.wireguard_addresses.value = r.address; nordToken.value = ""; }
          return r;
        })));
    wg.prepend(nord);
    const showNord = () => { nord.hidden = picked() !== "nordvpn"; };
    provider.addEventListener("change", showNord);
    showNord();
    const showType = () => { wg.hidden = kind() !== "wireguard"; ovpn.hidden = kind() !== "openvpn"; };
    type.addEventListener("change", showType);
    showType();
    // DASH-132: a Gluetun already running outside Starboard's apps. Its details are read on the server when the files
    // are written; the key or password never comes to this page.
    let existing = null;
    try { existing = (await api("/api/stack/existing-vpn")).vpn; } catch { /* no Docker access: type them */ }
    const reuse = existing?.complete ? el("input", { type: "checkbox", checked: !!state.vpn.use_existing || !state.vpn.provider }) : null;
    const typed = el("div", { class: "stack-4" });
    const showTyped = () => { typed.hidden = !!reuse?.checked; };
    reuse?.addEventListener("change", showTyped);
    const reuseBox = reuse ? el("div", { class: "stack-2" },
      el("label", { class: "option-card" }, reuse,
        el("strong", { text: `Use the VPN from ${existing.name}, already on this computer (recommended)` }),
        el("small", { text: `${providers.find((v) => v.id === existing.provider)?.name || existing.provider}, ${existing.type === "openvpn" ? "OpenVPN" : "WireGuard"}${existing.countries ? `, ${existing.countries}` : ""}. Starboard copies its key into the new set-up, so you need not type it.` }))) : null;
    nodes = [reuseBox, typed];
    typed.append(provider, el("div", { class: "form-stack" },
      otherBox,
      el("div", { class: "field" }, el("span", { class: "field__label", text: "Connection" }),
        el("span", { class: "hint", text: "WireGuard is quicker and simpler. Use OpenVPN only if your provider has no WireGuard." }), type),
      wg, ovpn,
      field("Countries", countries, { hint: "Optional. Where the VPN connects; a nearby country is fastest." }),
      el("p", { class: "small muted", text: "These go in the .env file on this computer only, never in Starboard's settings or its logs." })));
    nodes = nodes.filter(Boolean);
    showTyped();
    save = async () => {
      if (reuse?.checked) {
        state.vpn = { use_existing: existing.name, provider: existing.provider, type: existing.type, countries: existing.countries };
        try { await api("/api/stack/preview", { method: "POST", body: body(state) }); return true; }
        catch (e) { return stop(reuse, e.message); }
      }
      [other, ...Object.values(inputs)].forEach(clearError);
      if (!picked()) return stop($("input", provider), "Choose your VPN provider");
      const p = picked() === "other" ? other.value.trim().toLowerCase() : picked();
      if (!/^[a-z0-9 _-]{2,40}$/.test(p)) return stop(other, "Enter your VPN provider's name, such as mullvad");
      const need = kind() === "wireguard" ? ["wireguard_private_key", "wireguard_addresses"] : ["openvpn_user", "openvpn_password"];
      for (const k of need) if (!inputs[k].value.trim()) return stop(inputs[k], "Enter this from your VPN provider");
      if (kind() === "wireguard" && !/\/\d{1,3}$/.test(inputs.wireguard_addresses.value.trim())) return stop(inputs.wireguard_addresses, "Enter the address with its /32 at the end");
      state.vpn = { provider: p, type: kind(), countries: countries.value.trim(),
        ...Object.fromEntries(need.map((k) => [k, inputs[k].value.trim()])) };
      try { await api("/api/stack/preview", { method: "POST", body: body(state) }); return true; }
      catch (e) { return stop($("input", provider), e.message); }
    };
  } else if (id === "usenet") {
    // The same step as the terminal set-up's Usenet step (DASH-142): it asks first, and shows the providers only to
    // someone who has none. The rules for what Usenet may be used for show whatever the answer.
    const choices = [["none", "No, show me some providers"], ["have", "Yes, I have one"], ["later", "Not now: torrents are enough for now"]];
    const more = el("div", { class: "stack-2", "aria-live": "polite" });
    // DASH-183: the provider's server, tested here and written into the Usenet app once it runs.
    const uw = (await loadSetupAnswers()).usenet;
    const last = state.usenetServer || {};
    const usenetApp = state.apps.has("sabnzbd") ? "SABnzbd" : "NZBGet";
    const inputs = {
      host: el("input", { class: "input", autocomplete: "off", spellcheck: "false", value: last.host || "" }),
      ssl: el("input", { type: "checkbox", checked: last.ssl !== false }),
      port: el("input", { class: "input", inputmode: "numeric", autocomplete: "off", value: String(last.port || 563) }),
      username: el("input", { class: "input", autocomplete: "off", spellcheck: "false", value: last.username || "" }),
      password: el("input", { class: "input", type: "password", autocomplete: "new-password", value: last.password || "" }),
      connections: el("input", { class: "input", inputmode: "numeric", autocomplete: "off", value: String(last.connections || 8) }),
    };
    inputs.ssl.addEventListener("change", () => {
      if (["563", "119", ""].includes(inputs.port.value.trim())) inputs.port.value = inputs.ssl.checked ? "563" : "119";
    });
    const server = () => ({ host: inputs.host.value.trim(), ssl: inputs.ssl.checked, port: inputs.port.value.trim(),
      username: inputs.username.value.trim(), password: inputs.password.value, connections: inputs.connections.value.trim() });
    const serverBox = el("div", { class: "form-stack" },
      el("p", { text: uw.server_intro }),
      field(uw.host, inputs.host, { hint: uw.host_hint }),
      el("label", { class: "check" }, inputs.ssl, el("span", { text: uw.ssl })),
      field(uw.port, inputs.port, { hint: uw.port_hint }),
      field(uw.username, inputs.username),
      field(uw.password, inputs.password),
      field(uw.connections, inputs.connections, { hint: uw.connections_hint }),
      testButton(uw.test, () => api("/api/setup/test-usenet", { method: "POST", body: { server: server() } })),
      el("p", { class: "small muted", text: uw.later.replace("{app}", usenetApp) }));
    const show = (v) => {
      state.usenetHave = v;
      const how = el("p", { class: "help-links" }, helpButton("How to add a provider's server", { page: "topics/choose-a-usenet-provider.md" }));
      more.replaceChildren(...(v === "none" ? [
        el("p", { class: "small" }, el("strong", { text: "Ad: " }), USENET_AD),
        el("ul", { "aria-label": "Usenet providers (affiliate links)" }, USENET.map(([name, url]) => el("li", {},
          el("a", { href: url, target: "_blank", rel: "noopener noreferrer sponsored" }, name,
            el("span", { class: "visually-hidden", text: " (affiliate link, opens in a new tab)" }))))), how]
        : v === "have" ? [serverBox, how]
        : [el("p", { text: "The Usenet app is installed anyway. Add a provider whenever you like." }), how]),
      usenetRights());
    };
    const fieldset = el("fieldset", {}, el("legend", { text: "Do you have a Usenet provider?" }),
      el("div", { class: "option-cards" }, choices.map(([v, t]) => el("label", { class: "option-card" },
        el("input", { type: "radio", name: "usenet-have", value: v, checked: v === (state.usenetHave || "none") }), el("strong", { text: t })))));
    fieldset.addEventListener("change", (e) => show(e.target.value));
    show(state.usenetHave || "none");
    // DASH-247: a SABnzbd already running: its servers move into NZBGet when Starboard takes it over.
    let already = null;
    try { already = await api("/api/stack/existing-usenet"); } catch { /* no Docker access */ }
    const moves = already?.hosts?.length && usenetApp === "NZBGet" ? notice("info", "Your Usenet provider comes with you",
      `Your SABnzbd uses ${already.hosts.join(" and ")}. When Starboard takes over your apps, ${already.hosts.length === 1 ? "it moves" : "they move"} into NZBGet, so you need not type ${already.hosts.length === 1 ? "it" : "them"} again.`) : null;
    if (moves && !state.usenetHave) { state.usenetHave = "later"; $(`input[value="later"]`, fieldset).checked = true; show("later"); }
    nodes = [el("p", { text: USENET_ABOUT.replaceAll("SABnzbd", usenetApp) }), moves, fieldset, more].filter(Boolean);
    save = async () => {
      if (state.usenetHave !== "have") { state.usenetServer = null; return true; }
      const s = server();
      setError(inputs.host, "");
      if (!s.host) { state.usenetServer = null; return true; }  // added later in the Usenet app
      state.usenetServer = s;
      return true;
    };
  } else if (id === "sites") {
    // The same questions, in the same order and words, as the terminal set-up's step_sites: Reelix's built-in sites
    // (none ticked unless chosen), then your own Torznab or Newznab address. Added once Reelix runs.
    const list = await loadReelixSites();
    const w = list.words;
    const boxes = list.sites.map((s) => ({ s, input: el("input", { type: "checkbox", checked: state.sites.builtin.includes(s.id) }) }));
    const own = state.sites.own[0] || {};
    const kinds = ["", "torznab", "newznab"];
    const url = el("input", { class: "input", type: "url", value: own.url || "", autocomplete: "off", spellcheck: "false", placeholder: "https://" });
    const key = el("input", { class: "input", type: "password", value: own.api_key || "", autocomplete: "off" });
    const ownBox = el("div", { class: "stack-4" }, field(w.address, url, { required: true }), field(w.key, key));
    const which = el("fieldset", {}, el("legend", { text: w.own_question }),
      el("div", { class: "option-cards" }, w.own_choices.map((t, i) => el("label", { class: "option-card" },
        el("input", { type: "radio", name: "own-site", value: kinds[i], checked: (own.kind || "") === kinds[i] }), el("strong", { text: t })))));
    const showOwn = () => { ownBox.hidden = !$("input:checked", which).value; };
    which.addEventListener("change", showOwn);
    showOwn();
    nodes = [
      el("p", { text: w.intro }),
      state.apps.has("gluetun") ? el("p", { class: "small", text: w.vpn }) : null,
      el("fieldset", {}, el("legend", { text: "Reelix's built-in sites, no account needed" }),
        el("div", { class: "option-cards option-cards--row" }, boxes.map((b) => el("label", { class: "option-card" },
          b.input, el("strong", { text: b.s.name }), el("small", { text: b.s.lists }))))),
      which, ownBox,
      notice("info", "What you may download", w.rights),
      el("p", { class: "help-links" }, helpButton("How to choose sites to search", { page: "topics/choose-sites-to-search.md" })),
    ].filter(Boolean);
    save = async () => {
      const kind = $("input:checked", which).value;
      setError(url, "");
      if (kind && !/^https?:\/\/[^\s/]+/.test(url.value.trim())) return stop(url, "Enter the site's address, starting http:// or https://");
      state.sites = { builtin: boxes.filter((b) => b.input.checked).map((b) => b.s.id),
        own: kind ? [{ kind, url: url.value.trim(), api_key: key.value.trim() }] : [] };
      return true;
    };
  } else if (id === "films") {
    // DASH-178 and DASH-189: the same questions, words and order as the terminal set-up's step_films. Both answers
    // are written into Reelix once it runs.
    const w = await loadSetupAnswers();
    const key = el("input", { class: "input", type: "password", autocomplete: "off", spellcheck: "false", value: state.tmdb || "" });
    const langs = el("fieldset", {}, el("legend", { text: w.language.question }),
      el("div", { class: "option-cards" }, w.language.choices.map((c) => el("label", { class: "option-card" },
        el("input", { type: "radio", name: "release-language", value: c.value, checked: (state.language ?? "English") === c.value }),
        el("strong", { text: c.label }), el("small", { text: c.hint })))));
    nodes = [
      el("h3", { text: w.tmdb.title }),
      el("p", { text: w.tmdb.intro }),
      el("p", { class: "small" }, w.tmdb.how, " ", el("a", { href: w.tmdb.link, target: "_blank", rel: "noopener noreferrer" }, "themoviedb.org",
        el("span", { class: "visually-hidden", text: " (opens in a new tab)" }))),
      field(w.tmdb.question, key, { hint: w.tmdb.hint }),
      testButton(w.tmdb.test, () => api("/api/setup/test-tmdb", { method: "POST", body: { key: key.value.trim() } })),
      el("h3", { text: w.language.title }),
      el("p", { text: w.language.intro }),
      langs,
    ];
    save = async () => {
      const v = key.value.trim();
      setError(key, "");
      if (v && !/^([0-9a-f]{32}|eyJ[\w-]+\.[\w-]+\.[\w-]+)$/.test(v)) return stop(key, "That does not look like a TMDB key. Paste the API Read Access Token or the API key from themoviedb.org, Settings, API");
      state.tmdb = v;
      state.language = $("input:checked", langs)?.value ?? "English";
      return true;
    };
  } else if (id === "moving") {
    const offers = [];
    const has = (keys) => data.servers.filter((s) => keys.includes(s.key));
    const history = has(["plex", "emby"]);
    if (history.length && state.apps.has("jellyfin")) {
      offers.push({ id: "history", title: "Watch history", text: `What everyone has watched in ${history.map((s) => s.name).join(" and ")}, into Jellyfin. Settings, Apps, Jellyfin, Import, once Jellyfin is set up.` });
    }
    const listening = has(["plex", "jellyfin", "emby"]);
    if (listening.length && state.apps.has("audiobookshelf")) {
      offers.push({ id: "listening", title: "Listening progress", text: `Where everyone is in each audiobook, from ${listening.map((s) => s.name).join(" and ")}, into Audiobookshelf. Settings, Apps, Audiobookshelf, once it has scanned in your books.` });
    }
    const arrs = has(["sonarr", "radarr", "lidarr"]);
    const newArrs = ["sonarr", "radarr", "lidarr"].filter((k) => state.apps.has(k));
    if (arrs.length && newArrs.length) {
      offers.push({ id: "settings", title: "App settings", text: `Tags, quality settings, folders, download clients and naming from your ${arrs.map((s) => s.name).join(", ")} into the new ${newArrs.map((k) => apps[k].name).join(", ")}. Settings, Apps, Manage apps, Copy app settings, once they are running. Add the new apps in Prowlarr for search sites.` });
    }
    if (!offers.length) offers.push({ id: "none", title: "Nothing to bring over", soon: true, text: "None of the apps you ticked can take anything from the ones you have." });
    const boxes = offers.map((o) => {
      const input = el("input", { type: "checkbox", checked: !o.soon && state.moving.has(o.id), disabled: !!o.soon });
      return { o, input, node: el("label", { class: "option-card" }, input, el("strong", { text: o.title }), el("small", { text: o.text })) };
    });
    nodes = [el("div", { class: "option-cards" }, boxes.map((b) => b.node)),
      el("p", { class: "small muted", text: "Your media itself stays where it is: choose its folder on the Folders step." })];
    save = async () => { state.moving = new Set(boxes.filter((b) => b.input.checked).map((b) => b.o.id)); return true; };
  } else if (id === "review") {
    let p;
    try { p = await api("/api/stack/preview", { method: "POST", body: body(state) }); }
    catch (e) { return { nodes: [notice("danger", "Something needs changing", e.message)], save: async () => false }; }
    const change = (step, what) => el("button", { type: "button", class: "btn btn--quiet", onclick: () => go(step) }, "Change",
      el("span", { class: "visually-hidden", text: ` ${what}` }));
    // One table: what, your answer, and Change to go back to that step (stacks into cards on phones).
    const row = (label, value, step) => [el("tr", {}, el("th", { scope: "row", "data-label": "What", text: label }),
      el("td", { "data-label": "Your answer" }, value), el("td", { "data-label": "" }, change(step, label.toLowerCase())))];
    const vpnName = (await loadVpnProviders()).find((v) => v.id === state.vpn.provider)?.name || state.vpn.provider;
    const picked = data.groups.filter((g) => state.groups.has(g.key)).map((g) => g.name).join(", ") || "None";
    const moving = [...state.moving].map((m) => ({ history: "Watch history", listening: "Listening progress", settings: "App settings" })[m]).filter(Boolean).join(", ");
    nodes = [
      el("p", { text: "Nothing is written or started until you choose Write the files. You can change anything first." }),
      el("div", { class: "table-wrap", "data-stack": "" }, el("table", { class: "table table--fixed table--middle" },
        el("caption", { class: "visually-hidden", text: "What will be set up" }),
        el("colgroup", {}, el("col", { class: "col-quarter" }), el("col"), el("col", { class: "col-state" })),
        el("thead", {}, el("tr", {}, el("th", { scope: "col", text: "What" }), el("th", { scope: "col", text: "Your answer" }),
          el("th", { scope: "col" }, el("span", { class: "visually-hidden", text: "Change" })))),
        el("tbody", {},
        ...row("Install", state.install === "custom" ? "Your own choice" : (state.installName || "Basics"), "groups"),
        ...row("What it does", picked, "groups"),
        ...row("Apps", [...state.apps].map((k) => apps[k].name).join(", "), "groups"),
        ...(state.apps.has("reelix") && state.reelix_edition === "full" ? row("Reelix", "With YouTube and Spotify downloads", "groups")
          : state.apps.has("reelix") && state.installNote ? row("Reelix", state.installNote, "groups") : []),
        ...row("Media folder", el("code", { text: state.data_dir }), "folders"),
        ...(state.pool ? row("Pool", `${state.pool.path}, from ${state.pool.mounts.length} drives (run its commands first)`, "folders") : []),
        ...(state.advanced ? row("Settings folder", el("code", { text: state.config_dir }), "folders") : []),
        ...(state.apps.has("reelix") ? row("Sites to search", sitesSummary(state.sites, await loadReelixSites()), "sites") : []),
        ...(state.apps.has("reelix") ? row("TMDB key", state.tmdb ? "Added" : "None for now: Reelix uses open data", "films") : []),
        ...(state.apps.has("reelix") ? row("Language of releases", (await loadSetupAnswers()).language.choices.find((c) => c.value === state.language)?.label || "English", "films") : []),
        ...(state.usenetServer ? row("Usenet server", state.usenetServer.host, "usenet") : []),
        ...(state.apps.has("gluetun") ? row("VPN", `${vpnName}, ${state.vpn.type === "openvpn" ? "OpenVPN" : "WireGuard"}${state.vpn.countries ? `, ${state.vpn.countries}` : ""}`, "vpn") : []),
        ...(data.servers.length ? row("Moving over", moving || "Nothing", "moving") : [])))),
      p.moved.length ? notice("warning", "Some ports moved", p.moved.join(". ") + ".") : null,
      p.later.length ? notice("info", "Started later", `${p.later.join(", ")} ${p.later.length === 1 ? "needs its" : "need their"} own settings file first, so ${p.later.length === 1 ? "it is" : "they are"} written but not started.`) : null,
      p.hooks?.length ? el("p", { class: "small muted", text: `Before System, Apps, Updates changes ${p.hooks.map((k) => apps[k].name).join(" or ")}, it backs up ${p.hooks.length === 1 ? "its" : "their"} database first. If the backup fails, the update stops.` }) : null,
      el("details", { class: "disclosure", open: state.advanced }, el("summary", { text: "The files Starboard writes" }), el("div", { class: "disclosure__body stack-4" },
        el("p", { class: "small", text: "Two files in Starboard's data folder (data/stack): compose.yaml lists the apps; .env holds your settings and secrets. Older ones are kept." }),
        el("h3", { text: "Folders it makes" }), el("ul", {}, p.folders.map((f) => el("li", {}, el("code", { text: f })))),
        el("h3", { text: "Settings (.env)" }),
        el("div", { class: "table-wrap", "data-stack": "" }, el("table", { class: "table table--fixed" },
          el("caption", { class: "visually-hidden", text: "Settings in the .env file" }),
          el("colgroup", {}, el("col", { class: "col-third" }), el("col")),
          el("thead", {}, el("tr", {}, el("th", { scope: "col", text: "Setting" }), el("th", { scope: "col", text: "Value" }))),
          el("tbody", {}, Object.entries(p.env_shown).map(([k, v]) => el("tr", {},
            el("th", { scope: "row", "data-label": "Setting" }, el("code", { text: k })), el("td", { "data-label": "Value", text: v || "(empty)" })))))),
        el("h3", { text: "compose.yaml" }), el("pre", { class: "code-block", text: p.compose }))),
    ].filter(Boolean);
    // Writing decides which apps run, so it asks for the password, as starting does.
    const writePassword = el("input", { class: "input", type: "password", autocomplete: "current-password", required: true, id: "write-password" });
    nodes.push(field("Your Starboard password", writePassword, { required: true, hint: "Needed to write the files: they decide which apps run on this computer." }));
    save = async () => {
      setError(writePassword, "");
      if (!writePassword.value) { setError(writePassword, "Enter your Starboard password"); writePassword.focus(); return false; }
      try {
        state.written = await api("/api/stack/write", { method: "POST", body: { ...body(state), password: writePassword.value } });
        state.heldPassword = writePassword.value;  // for Start the apps a minute later; kept in this page only, never stored
      } catch (e) {
        if (e.status === 401 || e.status === 429) { setError(writePassword, e.message); writePassword.focus(); return false; }
        throw e;
      }
      toast("Files written");
      return true;
    };
  } else if (id === "start") {
    const w = state.written || {};
    const log = el("pre", { class: "code-block", hidden: true });
    const status = el("div", { class: "stack-2", "aria-live": "polite" });
    const after = el("div", { class: "stack-4" });
    const showAfter = async (settle = false) => {
      const waiting = el("span", { text: "Waiting for the apps to answer…" });
      if (settle) {
        // One bar while the apps open their ports; Starboard adds them by itself too, so leaving the page is fine.
        after.replaceChildren(el("h3", { text: "Add them to Starboard" }),
          el("div", { class: "meter" }, el("div", { class: "meter__label", "aria-live": "polite" }, waiting),
            el("div", { class: "progress progress--busy", role: "progressbar", "aria-label": "Waiting for the apps to answer", "aria-valuetext": "Working" }, el("span"))),
          el("p", { class: "small muted", text: "Starboard adds them when they answer, even if you carry on with the set-up." }));
      }
      const finder = await appFinder(undefined, { expect: settle ? [...state.apps] : null, shown: (t) => { waiting.textContent = t; } });
      const add = el("button", { type: "button", class: "btn btn--primary", hidden: !finder.add }, icon("plus"), "Add the ticked apps to Starboard");
      add.addEventListener("click", async () => { add.disabled = true; try { if (await finder.add()) add.hidden = true; } catch (e) { problem(e.message); } finally { add.disabled = false; } });
      after.replaceChildren(el("h3", { text: "Add them to Starboard" }), finder.box, add, ...connectGuide(state, apps),
        el("h3", { text: "Still to set up" }),
        el("p", { text: "Starboard sets up the rest by itself in the next few minutes. Anything it cannot do is listed on the Apps page, with a link to where to do it, until it is done." }));
    };
    const poolFirst = state.pool ? notice("warning", "Make the pool first", `Run the pool commands from the Folders step on the server before you start, so ${state.pool.path} exists.`) : null;
    if (w.can_start || w.starter) {
      const pw = el("input", { class: "input", type: "password", autocomplete: "current-password", value: state.heldPassword });
      const startBtn = el("button", { type: "button", class: "btn btn--primary" }, icon("play"), "Start the apps");
      const form = el("div", { class: "form-stack" },
        el("p", { text: w.can_start
          ? "Starboard asks Docker to download each app and start it, using a short-lived helper. This can take several minutes on the first run."
          : "The Run first window on this computer downloads each app and starts it, so keep that window open. This can take several minutes on the first run." }),
        field("Your Starboard password", pw, { required: true, hint: state.heldPassword ? "Filled in from the Check step. Starting apps changes this computer, so Starboard checks it is you."
          : "Starting apps changes this computer, so Starboard checks it is you." }),
        el("div", { class: "actions" }, startBtn));
      startBtn.addEventListener("click", async () => {
        clearError(pw);
        if (!pw.value) { stop(pw, "Enter your Starboard password"); return; }
        startBtn.disabled = true;
        try {
          await api("/api/stack/start", { method: "POST", body: { password: pw.value } });
          state.heldPassword = "";
          form.hidden = true;
          // One bar for the job, updated in place; a problem goes below it (WIZARD.md section 5, A job's progress).
          const words = el("span", { text: "Downloading and starting the apps. Please wait, this can take some time…" });
          const time = el("span", { class: "numeric nowrap", text: "0 min 00 s" });
          // After the timer: how many apps are on the computer, then how many are running (from Docker).
          const count = el("span", { class: "numeric nowrap" });
          const counted = (p) => !p ? "" : p.installed < p.total ? `${p.installed} of ${p.total} installed` : `${p.running} of ${p.total} running`;
          const bar = el("div", { class: "progress progress--busy", role: "progressbar", "aria-label": "Starting the apps",
            "aria-valuetext": "Working" }, el("span"));
          status.replaceChildren(el("div", { class: "meter" }, el("div", { class: "meter__label" }, words,
            el("span", { class: "nowrap" }, time, count)), bar));
          const began = Date.now();
          for (;;) {
            await new Promise((r) => setTimeout(r, 3000));
            const secs = Math.round((Date.now() - began) / 1000);
            time.textContent = `${Math.floor(secs / 60)} min ${String(secs % 60).padStart(2, "0")} s`;
            const j = await api("/api/stack/job");
            const n = counted(j.progress);
            count.textContent = n ? ` · ${n}` : "";
            if (n) bar.setAttribute("aria-valuetext", n);
            if (!j.finished) continue;
            log.textContent = j.log;
            bar.classList.remove("progress--busy");
            bar.firstChild.style.width = "100%";
            if (j.ok) {
              words.textContent = "The apps are running.";
              bar.setAttribute("aria-valuetext", "Done");
              status.append(notice("success", "The apps are running", "Now connect them: the steps are below."));
              await showAfter(true);
            } else {
              // The bar stays where it stopped, marked; the problem and its choices are below it.
              words.textContent = "Downloading and starting the apps did not finish.";
              bar.dataset.tone = "danger";
              bar.setAttribute("aria-valuetext", "Did not finish");
              const again = el("button", { type: "button", class: "btn btn--primary" }, "Try again");
              const details = el("button", { type: "button", class: "btn", "aria-expanded": "false" }, "Show the details");
              const leave = el("a", { class: "btn btn--quiet", href: "/index.html" }, "Stop");
              const problemBox = el("div", { class: "stack-2", id: "start-problem" },
                notice("danger", "Something did not start", "Docker stopped before every app was running. Try again often works after a slow download; the details show the last lines Docker wrote."),
                el("div", { class: "actions" }, again, details, leave));
              bar.setAttribute("aria-describedby", "start-problem");
              status.append(problemBox);
              details.addEventListener("click", () => {
                log.hidden = !log.hidden;
                details.setAttribute("aria-expanded", String(!log.hidden));
                details.textContent = log.hidden ? "Show the details" : "Hide the details";
              });
              again.addEventListener("click", () => {
                status.replaceChildren();
                log.hidden = true;
                form.hidden = false;
                startBtn.disabled = false;
                pw.focus();
              });
              problemBox.querySelector(".notice__title, strong")?.setAttribute("tabindex", "-1");
              problemBox.querySelector(".notice__title, strong")?.focus();
            }
            break;
          }
        } catch (e) {
          if (e.status === 401 || e.status === 429) stop(pw, e.message); else problem(e.message);
          startBtn.disabled = false;
        }
      });
      nodes = [poolFirst, form, status, log, after].filter(Boolean);
    } else {
      // The command is the same for every install (the write step sends it too), so it shows even before then.
      const command = w.command || "cd ~/starboard && ./install.sh --start-apps";
      const help = "https://themightytrex.github.io/starboard/help/topics/connect-with-ssh.html";
      nodes = [poolFirst, notice("info", "Run one command in a terminal",
          "Starboard does not have Docker access, so it cannot start the apps itself. Run this command in a terminal on the server: open Terminal on the server itself, or connect to it from another computer with SSH."),
        el("p", { class: "small" }, "It may ask for the password you use to sign in to the server. ",
          el("a", { href: help, target: "_blank", rel: "noopener noreferrer" }, "How to open a terminal on the server", icon("external-link"), el("span", { class: "visually-hidden", text: " (opens in a new tab)" }))),
        el("pre", { class: "code-block", text: command }), copyButton(command, "Copy the command"),
        el("p", { class: "small muted", text: "Then come back here: Starboard finds the new apps and adds them, and shows you how to connect them." }),
        el("div", { class: "actions" }, el("button", { type: "button", class: "btn", onclick: (e) => { e.currentTarget.hidden = true; showAfter(); } }, icon("search"), "Find the new apps")),
        after].filter(Boolean);
    }
  }
  return { nodes, save };
}

// Joining drives into one folder with mergerfs. Starboard cannot do it itself (it needs the server's password), so
// it writes the commands. Nothing on the drives is erased; files stay where they are and show in the pool too.
async function poolDialog(drives, current) {
  const path = el("input", { class: "input", value: current?.path || "/srv/pool", spellcheck: "false" });
  const typed = el("textarea", { class: "input", rows: "3", spellcheck: "false", placeholder: "/srv/disk1\n/srv/disk2" });
  const boxes = (drives || []).map((d) => ({ d, input: el("input", { type: "checkbox", checked: !!current?.mounts.includes(d.mount) }) }));
  const choose = boxes.length
    ? el("fieldset", { class: "form-stack" }, el("legend", { text: "Drives to join" }), boxes.map(({ d, input }) => el("label", { class: "check" }, input,
      el("span", { class: "check__text" }, el("strong", { text: d.mount }), el("span", { class: "check__hint", text: [d.size, d.fs, d.model, d.label].filter(Boolean).join(" · ") })))))
    : field("Drives to join", typed, { hint: "Starboard has no list of this computer's drives (it comes with Disk health). Type the folder each drive is mounted at, one a line." });
  const ok = await confirmDialog({
    title: "Join several drives into one",
    message: "A pool (mergerfs) shows several drives as one folder. New files go to the drive with the most room. Nothing on the drives is erased or moved.",
    fields: [choose, field("Pool folder", path, { required: true, hint: "Where the joined folder appears, such as /srv/pool. This becomes your media folder." })],
    confirm: "Use these drives",
  });
  if (!ok) return null;
  const mounts = boxes.length ? boxes.filter((b) => b.input.checked).map((b) => b.d.mount) : typed.value.split("\n").map((s) => s.trim()).filter(Boolean);
  const where = path.value.trim();
  if (mounts.length < 2 || !mounts.every((m) => /^\/[\w./-]+$/.test(m)) || !/^\/[\w./-]+$/.test(where)) {
    problem("Choose at least two drives, and a pool folder starting with /");
    return null;
  }
  const line = `${mounts.join(":")} ${where} fuse.mergerfs defaults,allow_other,use_ino,cache.files=off,moveonenospc=true,category.create=mfs,minfreespace=20G,fsname=mergerfs 0 0`;
  const commands = [
    "# On the server. sudo asks for your password.",
    "sudo apt install mergerfs",
    `sudo mkdir -p ${where}`,
    "sudo cp /etc/fstab /etc/fstab.before-pool",
    `echo '${line}' | sudo tee -a /etc/fstab`,
    `sudo mount ${where}`,
    `df -h ${where}`,
  ].join("\n");
  return { path: where, mounts, commands };
}

// After the apps start: how to connect them, in order, with the exact addresses and folders. Apps reach each other
// by their names inside Docker; downloads that go through the VPN are reached at gluetun.
function connectGuide(state, apps) {
  const has = (k) => state.apps.has(k);
  const vpn = has("gluetun");
  const host = (k) => (vpn && ["qbittorrent", "nzbget", "sabnzbd", "prowlarr", "flaresolverr"].includes(k) ? "gluetun" : k);
  const hostPort = (k) => Number(String(apps[k]?.ports?.[0]?.port || "0"));
  const open = (k) => el("a", { href: `${location.protocol}//${location.hostname}:${hostPort(k)}`, target: "_blank", rel: "noopener noreferrer" },
    `Open ${apps[k].name}`, el("span", { class: "visually-hidden", text: " (opens in a new tab)" }));
  const code = (t) => el("code", { text: t });
  const arrs = [["radarr", "/data/media/movies", 7878], ["sonarr", "/data/media/tv", 8989], ["lidarr", "/data/media/music", 8686], ["bookshelf", "/data/media/books", 8787]].filter(([k]) => has(k));
  const steps = [];
  if (has("reelix")) {
    steps.push(el("li", {}, el("strong", { text: "Reelix. " }), "Starboard has set it up and runs it, so you do not need Reelix's own pages. Your library folders are added",
      has("qbittorrent") || has("nzbget") || has("sabnzbd") ? ", and your download apps are connected" : "", ". Then:",
      el("ul", {}, ...[
        // Until the set-ups ask for it (DASH-178), the TMDB key is the one setting still made in Reelix's own pages.
        el("li", {}, "Films and series information: add a free TMDB key, from themoviedb.org, in ",
          el("a", { href: "/settings-reelix.html#rx-basics-h", text: "Settings, Reelix, Basic settings" }), ", if you did not give it in the Films and series step."),
        el("li", {}, "Sites to search: the ones you chose are added. See each one's state, and add more, in ",
          el("a", { href: "/settings-reelix.html", text: "Settings, Reelix, Sites to search" }), "."),
        has("jellyfin") || has("audiobookshelf") ? el("li", {}, `Reelix is connected to ${[has("jellyfin") ? "Jellyfin" : "", has("audiobookshelf") ? "Audiobookshelf" : ""].filter(Boolean).join(" and ")}, so new things show up there at once. Check it, or connect again, in `,
          el("a", { href: "/settings-reelix.html#rx-mediaservers", text: "Settings, Reelix, Media servers" }), ".") : null,
      ].filter(Boolean))));
  }
  if (has("qbittorrent") && has("reelix")) {
    steps.push(el("li", {}, el("strong", { text: "qBittorrent. " }), open("qbittorrent"), ". Starboard gave it a password of its own and saved it in Reelix, so nothing to do. ",
      "To sign in to qBittorrent yourself, choose a new password in its Options, Web UI, then change it for Reelix in ",
      el("a", { href: "/settings-reelix.html#rx-downloadclients", text: "Settings, Reelix, Download apps" }), "."));
  } else if (has("qbittorrent")) {
    steps.push(el("li", {}, el("strong", { text: "qBittorrent. " }), open("qbittorrent"), ". Its first password is in its log (on the server: ", code("docker logs qbittorrent"),
      "). Sign in as ", code("admin"), ", then choose your own password in Options, Web UI. In Options, Downloads, set the default save path to ", code("/data/downloads/torrents"), "."));
  }
  if (has("nzbget")) {
    steps.push(el("li", {}, el("strong", { text: "NZBGet. " }), open("nzbget"), ". Starboard set it up: it signs in as ", code("starboard"),
      " with a password Starboard made up (", code("NZBGET_PASS"), " in ", code("data/stack/.env"), "), its downloads go in ",
      code("/data/downloads/usenet"), ", and Reelix is connected to it", has("reelix") ? "" : " once Reelix is installed",
      ". Add your Usenet provider in its Settings, News-Servers."));
  }
  if (has("sabnzbd")) {
    // Starboard writes SABnzbd's folders and API key and connects it to Reelix itself (DASH-215).
    steps.push(el("li", {}, el("strong", { text: "SABnzbd. " }), open("sabnzbd"), has("reelix")
      ? ". Starboard set its folders and API key, and connected it to Reelix. Add your Usenet provider: its first-run wizard asks for it, or Config, Servers."
      : ". Starboard set its folders and API key. Add your Usenet provider: its first-run wizard asks for it, or Config, Servers."));
  }
  for (const [k, folder, port] of arrs) {
    steps.push(el("li", {}, el("strong", { text: `${apps[k].name}. ` }), open(k), ". Choose a sign-in in the first window. Then:",
      el("ul", {}, ...[
        el("li", {}, "Settings, Media Management, Add Root Folder: ", code(folder), "."),
        has("qbittorrent") ? el("li", {}, "Settings, Download Clients, add qBittorrent: host ", code(host("qbittorrent")), ", port ", code("8080"), ", with its user name and password.") : null,
        has("sabnzbd") ? el("li", {}, "Settings, Download Clients, add SABnzbd: host ", code(host("sabnzbd")), ", port ", code("8080"), ", with its API key.") : null,
        el("li", {}, "Settings, General: copy the API key. You need it for Prowlarr and for Starboard."),
      ].filter(Boolean))));
  }
  if (has("prowlarr")) {
    steps.push(el("li", {}, el("strong", { text: "Prowlarr. " }), open("prowlarr"), ". Add your search sites in Indexers. Then in Settings, Apps, add each app with its API key:",
      el("ul", {}, arrs.map(([k, , port]) => el("li", {}, `${apps[k].name}: Prowlarr server `, code(`http://${host("prowlarr")}:9696`), `, ${apps[k].name} server `, code(`http://${k}:${port}`), "."))),
      "Prowlarr then shares the sites with all of them."));
  }
  if (has("jellyfin")) {
    // Starboard runs Jellyfin's first run itself (DASH-179): the account, the libraries and its key.
    steps.push(el("li", {}, el("strong", { text: "Jellyfin. " }), open("jellyfin"), ". Starboard set it up: sign in as ", code("admin"),
      " with your Starboard password. Its Films, Series and Music libraries are added, and Starboard has its key."));
  }
  if (has("audiobookshelf")) {
    // The same for Audiobookshelf (DASH-180): the account, the Audiobooks, Books and Radio libraries and its key.
    steps.push(el("li", {}, el("strong", { text: "Audiobookshelf. " }), open("audiobookshelf"), ". Starboard set it up: sign in as ", code("admin"),
      " with your Starboard password. Its Audiobooks, Books and Radio libraries are added, and Starboard has its key."));
  }
  if (has("seerr")) {
    steps.push(el("li", {}, el("strong", { text: "Seerr. " }), open("seerr"), ". Sign in with Jellyfin at ", code("http://jellyfin:8096"),
      ", then add Radarr and Sonarr in Settings, Services with their API keys, so requests go straight to them."));
  }
  if (has("bazarr")) {
    steps.push(el("li", {}, el("strong", { text: "Bazarr. " }), open("bazarr"), ". In Settings, connect Sonarr (", code("sonarr"), ", port 8989) and Radarr (", code("radarr"), ", port 7878) with their API keys, and choose your languages."));
  }
  steps.push(el("li", {}, el("strong", { text: "Starboard. " }), "In ", el("a", { href: "/settings.html", text: "Manage apps" }), ", give each app its API key, so Search, Downloads and Coming up work."));
  if (state.moving.has("history")) steps.push(el("li", {}, "Import watch history: ", el("a", { href: "/settings-jellyfin.html", text: "Settings, Apps, Jellyfin" }), "."));
  if (state.moving.has("settings")) steps.push(el("li", {}, "Copy settings from your old apps: ", el("a", { href: "/copy-settings.html", text: "Copy app settings" }), "."));
  if (state.moving.has("listening")) steps.push(el("li", {}, "Copy listening progress once Audiobookshelf has scanned in your books: ", el("a", { href: "/settings-audiobookshelf.html", text: "Settings, Apps, Audiobookshelf" }), "."));
  return [el("h3", { text: "Connect your apps, in this order" }),
    el("p", { class: "small muted", text: "Inside Docker the apps find each other by name (such as sonarr), not by this computer's address. Every app sees your media at /data." }),
    el("ol", { class: "stack-4" }, steps)];
}

function body(state) {
  return { apps: [...state.apps], groups: [...state.groups], config_dir: state.config_dir, data_dir: state.data_dir, puid: state.puid, pgid: state.pgid, tz: state.tz, vpn: state.vpn, reelix_edition: state.apps.has("reelix") ? state.reelix_edition : "lite", ...(state.apps.has("reelix") ? { sites: state.sites, tmdb: state.tmdb, language: state.language } : {}),
    ...(state.usenetServer && (state.apps.has("nzbget") || state.apps.has("sabnzbd")) ? { usenet_server: state.usenetServer } : {}) };
}
