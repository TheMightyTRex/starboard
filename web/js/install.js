// Install apps: a guide that sets up a media server stack in groups (Movies, TV, Ebooks and so on). It writes a
// Compose file and a .env file, shows them, and starts the apps only when you press Start and give your password.
// Loaded only by install-apps.html, after settings.js (it uses field, notice, wizardFrame and appFinder).

async function startInstall() {
  const root = $("#install");
  root.removeAttribute("aria-busy");
  const fromGuide = new URLSearchParams(location.search).get("from") === "guide";
  let data;
  try { data = await api("/api/stack"); } catch (e) { root.replaceChildren(notice("danger", "Could not look", e.message)); return; }
  const apps = Object.fromEntries(data.apps.map((a) => [a.key, a]));
  const state = {
    groups: new Set(data.groups.filter((g) => g.default).map((g) => g.key)),
    apps: new Set(data.apps.filter((a) => a.default && !a.installed && a.groups.some((g) => data.groups.find((x) => x.key === g).default)).map((a) => a.key)),
    config_dir: data.defaults.config_dir, data_dir: data.defaults.data_dir,
    puid: data.defaults.puid, pgid: data.defaults.pgid, tz: data.defaults.tz,
    vpn: { provider: "", type: "wireguard" }, moving: new Set(), written: null,
  };
  const steps = [
    { id: "groups", title: "What to set up", question: "What do you want your server to do?",
      intro: "Tick a group to add its apps; open it to change which apps. Apps already running here are left as they are." },
    { id: "folders", title: "Folders", question: "Where should the apps keep things?",
      intro: "One media folder holds downloads and the library together, so finished downloads move instantly." },
    ...(data.servers.length ? [{ id: "moving", title: "Moving over", question: "Bring things over from the apps you have?",
      intro: "Starboard found these on this computer. Nothing is copied or changed until the new apps are running and you choose." }] : []),
    { id: "review", title: "Check", question: "Check what will be written", skippable: false },
    { id: "start", title: "Start", question: "Start the apps", skippable: false },
  ];
  const finishTo = fromGuide ? "/setup-guide.html" : "/index.html";

  const go = async (index) => {
    const step = steps[index];
    let save = async () => true;
    let loading = true;
    step.nodes = [el("p", { class: "muted", text: "Loading…" })];
    const frame = () => wizardFrame({ root, steps, index, busy: loading,
      continueText: step.id === "review" ? "Write the files" : step.id === "start" ? (fromGuide ? "Back to the set-up guide" : "Go to Apps") : "Continue",
      onBack: () => go(index - 1), onSkip: () => go(index + 1),
      onContinue: async (e) => {
        const button = e.currentTarget;
        button.disabled = true;
        try { if (await save()) { if (step.id === "start") location.href = finishTo; else go(index + 1); } } catch (err) { toast(err.message); }
        finally { if (button.isConnected) button.disabled = false; }
      } });
    frame();
    const content = await installStep(step.id, state, data, apps);
    step.nodes = content.nodes;
    save = content.save;
    loading = false;
    frame().heading.focus();
  };
  go(0);
}

function memoryText(mb) { return mb >= 1000 ? `${(mb / 1000).toFixed(1)} GB` : `${mb} MB`; }

async function installStep(id, state, data, apps) {
  let nodes = [];
  let save = async () => true;
  if (id === "groups") {
    const total = el("p", { class: "small muted", "aria-live": "polite" });
    const count = () => {
      const mb = [...state.apps].reduce((n, k) => n + apps[k].memory, 0);
      total.textContent = `${state.apps.size} ${state.apps.size === 1 ? "app" : "apps"} ticked, using about ${memoryText(mb)} of memory together when idle.`;
    };
    const appBoxes = {};
    const groupRow = (g) => {
      const own = data.apps.filter((a) => a.groups[0] === g.key);
      const shared = data.apps.filter((a) => a.groups.includes(g.key) && a.groups[0] !== g.key);
      const groupBox = el("input", { type: "checkbox", checked: state.groups.has(g.key) });
      const list = el("div", { class: "switch-list install-apps", hidden: !state.groups.has(g.key) }, own.map((a) => {
        const box = el("input", { type: "checkbox", checked: state.apps.has(a.key), disabled: a.installed });
        appBoxes[a.key] = box;
        box.addEventListener("change", () => { if (box.checked) state.apps.add(a.key); else state.apps.delete(a.key); count(); });
        const busyPort = a.ports.find((p) => !p.free);
        const hint = [a.installed ? "Already running here" : "", a.notes,
          a.groups.length > 1 ? `Also for ${a.groups.slice(1).map((k) => data.groups.find((x) => x.key === k).name.toLowerCase()).join(", ")}` : "",
          busyPort && !a.installed ? `Port ${busyPort.port} is in use, so it will use the next free one` : "",
          a.later ? "Starts once you add its settings file" : "", `About ${memoryText(a.memory)}`].filter(Boolean).join(" · ");
        return el("label", { class: "check" }, box, el("span", { class: "check__text" }, el("strong", { text: a.name }), el("span", { class: "check__hint", text: hint })));
      }), shared.map((a) => el("p", { class: "small muted", text: `${a.name} is under ${data.groups.find((x) => x.key === a.groups[0]).name}.` })));
      groupBox.addEventListener("change", () => {
        list.hidden = !groupBox.checked;
        if (groupBox.checked) state.groups.add(g.key); else state.groups.delete(g.key);
        own.filter((a) => !a.installed).forEach((a) => {
          const on = groupBox.checked && a.default;
          appBoxes[a.key].checked = on;
          if (on) state.apps.add(a.key); else state.apps.delete(a.key);
        });
        count();
      });
      return el("div", { class: "install-group" },
        el("label", { class: "option-card" }, groupBox, el("strong", { text: g.name }), el("small", { text: g.about })), list);
    };
    const kinds = [["media", "Media"], ["core", "Watching and downloading"], ["extras", "Extras"]];
    nodes = [...kinds.map(([kind, name]) => el("fieldset", { class: "stack-2" }, el("legend", { class: "h3", text: name }),
      el("div", { class: "option-cards" }, data.groups.filter((g) => g.kind === kind).map(groupRow)))), total];
    count();
    save = async () => {
      if (!state.apps.size) { toast("Tick at least one app, or skip this guide"); return false; }
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
    nodes = [el("div", { class: "form-stack" },
      field("Settings folder", cfg, { span: true, hint: "Each app gets its own folder inside it, such as …/config/sonarr." }),
      radios.length ? el("fieldset", { class: "stack-2" }, el("legend", { text: "Media folder" }),
        el("p", { class: "small muted", text: "Your other apps already use these. Choosing one points the new apps at your media where it is; nothing is moved." }),
        el("div", { class: "option-cards" }, radios.map(({ m, input }) => el("label", { class: "option-card" }, input,
          el("strong", { text: m.path }), el("small", { text: `Used by ${m.used_by.join(", ")}` }))),
          el("label", { class: "option-card" }, otherRadio, el("strong", { text: "Another folder" }), el("small", { text: "Type it below." }))))
        : null,
      field(radios.length ? "Other media folder" : "Media folder", other, { span: true, hint: "Starboard makes media (movies, tv, books and so on) and downloads inside it." }),
      el("details", {}, el("summary", { text: "User, group and time zone" }), el("div", { class: "form-stack" },
        field("User number (PUID)", puid, { short: true, hint: "The apps run as this user, so you own their files. Starboard's own user by default." }),
        field("Group number (PGID)", pgid, { short: true }),
        field("Time zone", tz, { hint: "Such as Europe/London." })))),
    ];
    let vpn = {};
    if (state.apps.has("gluetun")) {
      vpn = {
        provider: el("input", { class: "input", value: state.vpn.provider, placeholder: "such as mullvad", autocomplete: "off" }),
        type: el("select", { class: "input" }, el("option", { value: "wireguard", text: "WireGuard" }), el("option", { value: "openvpn", text: "OpenVPN" })),
        wireguard_private_key: el("input", { class: "input", type: "password", autocomplete: "off" }),
        wireguard_addresses: el("input", { class: "input", autocomplete: "off", placeholder: "from your provider, ending /32" }),
        openvpn_user: el("input", { class: "input", autocomplete: "off" }),
        openvpn_password: el("input", { class: "input", type: "password", autocomplete: "off" }),
        countries: el("input", { class: "input", placeholder: "such as Netherlands" }),
      };
      vpn.type.value = state.vpn.type;
      nodes.push(el("fieldset", { class: "form-stack" }, el("legend", { class: "h3", text: "VPN" }),
        el("p", { class: "small muted", text: "From your VPN provider's WireGuard or OpenVPN page. They go in the .env file on this computer only, never in Starboard's settings." }),
        field("Provider", vpn.provider, { hint: "As Gluetun names it." }), field("Connection", vpn.type),
        field("WireGuard private key", vpn.wireguard_private_key), field("WireGuard address", vpn.wireguard_addresses),
        field("OpenVPN user name", vpn.openvpn_user), field("OpenVPN password", vpn.openvpn_password),
        field("Countries", vpn.countries, { hint: "Optional." })));
    }
    save = async () => {
      state.config_dir = cfg.value.trim();
      const picked = radios.find((r) => r.input.checked);
      state.data_dir = picked ? picked.m.path : other.value.trim();
      Object.assign(state, { puid: Number(puid.value), pgid: Number(pgid.value), tz: tz.value.trim() });
      state.vpn = Object.fromEntries(Object.entries(vpn).map(([k, input]) => [k, input.value.trim()]));
      try { await api("/api/stack/preview", { method: "POST", body: body(state) }); return true; }
      catch (e) { toast(e.message); return false; }
    };
  } else if (id === "moving") {
    const offers = [];
    const has = (keys) => data.servers.filter((s) => keys.includes(s.key));
    const history = has(["plex", "emby"]);
    if (history.length && state.apps.has("jellyfin")) {
      offers.push({ id: "history", title: "Watch history", text: `What everyone has watched in ${history.map((s) => s.name).join(" and ")}, into Jellyfin. Settings, Jellyfin, Import, once Jellyfin is set up.` });
    }
    const listening = has(["plex", "jellyfin"]);
    if (listening.length && state.apps.has("audiobookshelf")) {
      offers.push({ id: "listening", title: "Listening progress", soon: true, text: `Where everyone is in each audiobook, from ${listening.map((s) => s.name).join(" and ")}. Coming soon: it needs the books scanned in first.` });
    }
    const arrs = has(["sonarr", "radarr", "lidarr"]);
    const newArrs = ["sonarr", "radarr", "lidarr", "bookshelf"].filter((k) => state.apps.has(k));
    if (arrs.length && newArrs.length) {
      offers.push({ id: "settings", title: "App settings", soon: true, text: `Download clients, tags and naming from your ${arrs.map((s) => s.name).join(", ")} into the new ${newArrs.map((k) => apps[k].name).join(", ")}. Coming soon. For now, add the new apps in Prowlarr (search sites) and Profilarr (quality settings).` });
    }
    if (!offers.length) offers.push({ id: "none", title: "Nothing to bring over", soon: true, text: "None of the apps you ticked can take anything from the ones you have." });
    const boxes = offers.map((o) => {
      const input = el("input", { type: "checkbox", checked: !o.soon && state.moving.has(o.id), disabled: !!o.soon });
      return { o, input, node: el("label", { class: "option-card" }, input, el("strong", { text: o.soon && o.id !== "none" ? `${o.title} (coming soon)` : o.title }), el("small", { text: o.text })) };
    });
    nodes = [el("div", { class: "option-cards" }, boxes.map((b) => b.node)),
      el("p", { class: "small muted", text: "Your media itself stays where it is: choose its folder on the Folders step." })];
    save = async () => { state.moving = new Set(boxes.filter((b) => b.input.checked).map((b) => b.o.id)); return true; };
  } else if (id === "review") {
    let p;
    try { p = await api("/api/stack/preview", { method: "POST", body: body(state) }); }
    catch (e) { return { nodes: [notice("danger", "Something needs changing", e.message)], save: async () => false }; }
    nodes = [
      el("p", { text: `Starboard writes two files into its own data folder (data/stack), keeping any older ones. Nothing starts yet.` }),
      el("h3", { text: "Apps" }), el("p", { text: [...state.apps].map((k) => apps[k].name).join(", ") }),
      p.moved.length ? notice("warning", "Some ports moved", p.moved.join(". ") + ".") : null,
      p.later.length ? notice("info", "Started later", `${p.later.join(", ")} ${p.later.length === 1 ? "needs its" : "need their"} own settings file first, so ${p.later.length === 1 ? "it is" : "they are"} written but not started.`) : null,
      el("h3", { text: "Folders it makes" }), el("ul", {}, p.folders.map((f) => el("li", {}, el("code", { text: f })))),
      el("h3", { text: "Settings (.env)" }),
      el("dl", { class: "facts" }, Object.entries(p.env_shown).flatMap(([k, v]) => [el("dt", {}, el("code", { text: k })), el("dd", { text: v || "(empty)" })])),
      el("details", {}, el("summary", { text: "Show the Compose file" }), el("pre", { class: "code-block", text: p.compose })),
    ].filter(Boolean);
    save = async () => {
      state.written = await api("/api/stack/write", { method: "POST", body: body(state) });
      toast("Files written");
      return true;
    };
  } else if (id === "start") {
    const w = state.written || {};
    const log = el("pre", { class: "code-block", hidden: true });
    const status = el("div", { "aria-live": "polite" });
    const after = el("div", { class: "stack-4" });
    const showAfter = async () => {
      const finder = await appFinder();
      const add = el("button", { type: "button", class: "btn btn--primary", hidden: !finder.add }, icon("plus"), "Add the ticked apps to Starboard");
      add.addEventListener("click", async () => { add.disabled = true; try { if (await finder.add()) add.hidden = true; } catch (e) { toast(e.message); } finally { add.disabled = false; } });
      const next = [
        el("li", { text: "Open each new app once to set it up (Jellyfin and Seerr ask for an admin account)." }),
        state.apps.has("prowlarr") ? el("li", { text: "In Prowlarr, add your search sites, then Settings, Apps: add Sonarr, Radarr and the others, so it shares the sites with them." }) : null,
        state.moving.has("history") ? el("li", {}, "Import watch history: ", el("a", { href: "/settings-jellyfin.html", text: "Settings, Jellyfin" }), ".") : null,
      ].filter(Boolean);
      after.replaceChildren(el("h3", { text: "Add them to Starboard" }), finder.box, add, el("h3", { text: "Next" }), el("ol", {}, next));
    };
    if (w.can_start) {
      const pw = el("input", { class: "input", type: "password", autocomplete: "current-password" });
      const startBtn = el("button", { type: "button", class: "btn btn--primary" }, icon("play"), "Start the apps");
      const form = el("div", { class: "form-stack" },
        el("p", { text: "Starboard asks Docker to download each app and start it, using a short-lived helper. This can take several minutes on the first run." }),
        field("Your Starboard password", pw, { hint: "Starting apps changes this computer, so Starboard checks it is you." }), el("div", { class: "actions" }, startBtn));
      startBtn.addEventListener("click", async () => {
        startBtn.disabled = true;
        try {
          await api("/api/stack/start", { method: "POST", body: { password: pw.value } });
          form.hidden = true;
          status.replaceChildren(el("p", { class: "muted", text: "Downloading and starting the apps…" }));
          for (;;) {
            await new Promise((r) => setTimeout(r, 3000));
            const j = await api("/api/stack/job");
            if (!j.finished) continue;
            log.textContent = j.log; log.hidden = false;
            status.replaceChildren(j.ok ? notice("success", "The apps are running", "The log is below.") : notice("danger", "Something did not start", "Read the log below, change what it says, and run this guide again."));
            if (j.ok) await showAfter();
            break;
          }
        } catch (e) { toast(e.message); startBtn.disabled = false; }
      });
      nodes = [form, status, log, after];
    } else {
      nodes = [notice("info", "Run one command", "Starboard does not have Docker access, so it cannot start apps itself. On this computer, run:"),
        el("pre", { class: "code-block", text: w.command || "" }), copyButton(w.command || "", "Copy the command"),
        el("p", { class: "small muted", text: "Then come back here: Starboard finds the new apps and adds them." }),
        el("div", { class: "actions" }, el("button", { type: "button", class: "btn", onclick: (e) => { e.currentTarget.hidden = true; showAfter(); } }, icon("search"), "Find the new apps"))
        , after];
    }
  }
  return { nodes, save };
}

function body(state) {
  return { apps: [...state.apps], config_dir: state.config_dir, data_dir: state.data_dir, puid: state.puid, pgid: state.pgid, tz: state.tz, vpn: state.vpn };
}
