// Install apps: a guide that sets up a media server (an *arr stack) for someone who has never done it, in groups
// such as Movies, TV and Ebooks. It explains each part, picks sensible apps and folders, writes a Compose file and
// a .env file, starts the apps only when you press Start and give your password, then talks you through connecting
// them. "Advanced settings" shows every app, the settings folder, user and group numbers, and the files themselves.
// Loaded only by install-apps.html, after settings.js (it uses field, setError, notice, wizardFrame and appFinder).

const VPN_PROVIDERS = ["airvpn", "cyberghost", "expressvpn", "fastestvpn", "ivpn", "mullvad", "nordvpn", "perfect privacy",
  "privado", "private internet access", "privatevpn", "protonvpn", "purevpn", "surfshark", "torguard", "windscribe"];

async function startInstall() {
  const root = $("#install");
  root.removeAttribute("aria-busy");
  const params = new URLSearchParams(location.search);
  const fromGuide = params.get("from") === "guide";
  // The set-up guide's Storage step chose the media folder already (DASH-103): use it, and skip Folders.
  const chosenMedia = fromGuide && /^\/[A-Za-z0-9._/-]{0,250}$/.test(params.get("media") || "") ? params.get("media") : "";
  let data;
  try { data = await api("/api/stack"); } catch (e) { root.replaceChildren(notice("danger", "Could not look", e.message)); return; }
  const apps = Object.fromEntries(data.apps.map((a) => [a.key, a]));
  let advanced = false;
  try { advanced = localStorage.getItem("install-advanced") === "1"; } catch { /* private window */ }
  const state = {
    advanced,
    groups: new Set(data.groups.filter((g) => g.default).map((g) => g.key)),
    apps: new Set(data.apps.filter((a) => a.default && !a.installed && a.groups.some((g) => data.groups.find((x) => x.key === g).default)).map((a) => a.key)),
    config_dir: data.defaults.config_dir, data_dir: chosenMedia || data.defaults.data_dir,
    puid: data.defaults.puid, pgid: data.defaults.pgid, tz: data.defaults.tz,
    vpn: { provider: "", type: "wireguard" }, moving: new Set(), written: null, pool: null,
  };
  // The steps follow the choices: VPN only when Gluetun is ticked, Usenet only when SABnzbd is, Moving over only when
  // there is something to move.
  const build = () => [
    { id: "welcome", title: "Start here", question: "Set up a media server, step by step", skippable: false },
    { id: "groups", title: "What to set up", question: "What do you want your server to do?", skippable: false,
      intro: "Tick what you want. Starboard picks the apps for each one; you can see and change them with Advanced settings." },
    ...(chosenMedia ? [] : [{ id: "folders", title: "Folders", question: "Where should your media live?", skippable: false,
      intro: "One media folder holds your downloads and your library together, so a finished download moves into the library instantly." }]),
    ...(state.apps.has("gluetun") ? [{ id: "vpn", title: "VPN", question: "Connect the VPN", skippable: false,
      intro: "Downloads go through your VPN, so your internet provider sees only the VPN. You need an account with a VPN provider." }] : []),
    ...(state.apps.has("sabnzbd") ? [{ id: "usenet", title: "Usenet", question: "Your Usenet provider", skippable: false }] : []),
    ...(data.servers.length ? [{ id: "moving", title: "Moving over", question: "Bring things over from the apps you have?",
      intro: "Starboard found these on this computer. Nothing is copied or changed until the new apps are running and you choose." }] : []),
    { id: "review", title: "Check", question: "Check everything before it is written", skippable: false },
    { id: "start", title: "Start", question: "Start the apps", skippable: false },
  ];
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
        el("li", {}, el("strong", { text: "Find. " }), "Prowlarr knows the sites that list films and series, and shares them with the other apps."),
        el("li", {}, el("strong", { text: "Choose. " }), "Radarr (films), Sonarr (TV) and the others keep a list of what you want, and pick the best copy when it appears."),
        el("li", {}, el("strong", { text: "Download. " }), "qBittorrent (or SABnzbd) downloads it, through your VPN if you have one."),
        el("li", {}, el("strong", { text: "Sort. " }), "The app renames the finished file and moves it into your library."),
        el("li", {}, el("strong", { text: "Watch. " }), "Jellyfin plays your library on TVs, phones and browsers. Seerr lets the people you share with ask for things.")),
      el("p", { text: "This guide picks the apps for what you want, sets up the folders, writes the set-up file and starts the apps. Then it shows you, step by step, how to connect them. It takes about 15 minutes; the downloads take longer." }),
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
    const total = el("p", { class: "small muted", "aria-live": "polite" });
    const count = () => {
      const mb = [...state.apps].reduce((n, k) => n + apps[k].memory, 0);
      total.textContent = `${state.apps.size} ${state.apps.size === 1 ? "app" : "apps"}, using about ${memoryText(mb)} of memory together when idle.`;
    };
    const appBoxes = {};
    const error = el("div", { role: "alert" });
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
        box.addEventListener("change", () => { if (box.checked) state.apps.add(a.key); else state.apps.delete(a.key); count(); showIncludes(); });
        const busyPort = a.ports.find((p) => !p.free);
        const hint = [a.installed ? "Already running here" : "", a.notes,
          a.groups.length > 1 ? `Also for ${a.groups.slice(1).map((k) => groupName(k).toLowerCase()).join(", ")}` : "",
          busyPort && !a.installed ? `Port ${busyPort.port} is in use, so it will use the next free one` : "",
          a.later ? "Starts once you add its settings file" : "", `About ${memoryText(a.memory)}`].filter(Boolean).join(" · ");
        return el("label", { class: "check" }, box, el("span", { class: "check__text" }, el("strong", { text: a.name }), el("span", { class: "check__hint", text: hint })));
      }), shared.map((a) => el("p", { class: "small muted", text: `${a.name} is under ${groupName(a.groups[0])}.` })));
      groupBox.addEventListener("change", () => {
        error.replaceChildren();
        list.hidden = !(state.advanced && groupBox.checked);
        if (groupBox.checked) state.groups.add(g.key); else state.groups.delete(g.key);
        own.filter((a) => !a.installed).forEach((a) => {
          const on = groupBox.checked && a.default;
          appBoxes[a.key].checked = on;
          if (on) state.apps.add(a.key); else state.apps.delete(a.key);
        });
        count();
        showIncludes();
      });
      showIncludes();
      return el("div", { class: "install-group" },
        el("label", { class: "option-card" }, groupBox, el("strong", { text: g.name }), el("small", { text: g.about }), includes), list);
    };
    const kinds = [["media", "Media"], ["core", "Watching and downloading"], ["extras", "Extras"]];
    nodes = [...kinds.map(([kind, name]) => el("fieldset", { class: "stack-2" }, el("legend", { class: "h3", text: name }),
      el("div", { class: "option-cards" }, data.groups.filter((g) => g.kind === kind).map(groupRow)))), total, error];
    count();
    save = async () => {
      if (!state.apps.size) { error.replaceChildren(notice("danger", "Nothing ticked", "Tick at least one thing for your server to do.")); return false; }
      const findable = ["radarr", "sonarr", "lidarr", "bookshelf", "storyarr", "kapowarr"].some((k) => state.apps.has(k));
      const downloader = ["qbittorrent", "sabnzbd"].some((k) => state.apps.has(k) || apps[k]?.installed);
      if (findable && !downloader && !state.warnedDownloads) {
        state.warnedDownloads = true;
        error.replaceChildren(notice("warning", "Nothing to download with", "Tick Downloads too, so the apps have something to download with. Or choose Continue again to go on without it."));
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
      field(radios.length ? "Other media folder" : "Media folder", other, { span: true,
        hint: "A folder on the drive with the most room, such as /srv/media. Starboard makes movies, tv, books and downloads folders inside it." }),
      el("div", { class: "stack-2" },
        el("p", { class: "small muted", text: "Several drives? A pool joins them into one folder, so the apps see one big drive. Nothing on them is erased." }),
        el("div", { class: "actions" }, poolButton), poolBox),
      state.advanced ? field("Settings folder", cfg, { span: true, hint: "Each app gets its own folder inside it, such as …/config/sonarr. Back this folder up." }) : null,
      state.advanced ? el("fieldset", { class: "form-stack" }, el("legend", { text: "User, group and time zone" }),
        field("User number (PUID)", puid, { short: true, hint: "The apps run as this user, so you own their files. Starboard's own user by default." }),
        field("Group number (PGID)", pgid, { short: true }),
        field("Time zone", tz, { hint: "Such as Europe/London." })) : null),
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
    const provider = el("input", { class: "input", value: state.vpn.provider, list: "vpn-providers", autocomplete: "off", placeholder: "such as mullvad" });
    const list = el("datalist", { id: "vpn-providers" }, VPN_PROVIDERS.map((p) => el("option", { value: p })));
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
      field("WireGuard private key", inputs.wireguard_private_key, { hint: "On your provider's site, make a WireGuard configuration (sometimes called a config file or a device). Copy the PrivateKey line." }),
      field("WireGuard address", inputs.wireguard_addresses, { hint: "The Address line from the same configuration, ending /32." }));
    const ovpn = el("div", { class: "form-stack" },
      field("OpenVPN user name", inputs.openvpn_user, { hint: "Your provider's OpenVPN or service user name. It is often not the one you sign in to their website with." }),
      field("OpenVPN password", inputs.openvpn_password));
    const kind = () => $("input:checked", type)?.value || "wireguard";
    const showType = () => { wg.hidden = kind() !== "wireguard"; ovpn.hidden = kind() !== "openvpn"; };
    type.addEventListener("change", showType);
    showType();
    nodes = [el("div", { class: "form-stack" },
      field("VPN provider", provider, { hint: "Its name as Gluetun knows it. Start typing to choose from the list." }), list,
      el("div", { class: "field" }, el("span", { class: "field__label", text: "Connection" }),
        el("span", { class: "hint", text: "WireGuard is quicker and simpler. Use OpenVPN only if your provider has no WireGuard." }), type),
      wg, ovpn,
      field("Countries", countries, { hint: "Optional. Where the VPN connects; a nearby country is fastest." }),
      el("p", { class: "small muted", text: "These go in the .env file on this computer only, never in Starboard's settings or its logs." }))];
    save = async () => {
      [provider, ...Object.values(inputs)].forEach(clearError);
      const p = provider.value.trim().toLowerCase();
      if (!/^[a-z0-9 _-]{2,40}$/.test(p)) return stop(provider, "Enter your VPN provider, such as mullvad");
      const need = kind() === "wireguard" ? ["wireguard_private_key", "wireguard_addresses"] : ["openvpn_user", "openvpn_password"];
      for (const k of need) if (!inputs[k].value.trim()) return stop(inputs[k], "Enter this from your VPN provider");
      if (kind() === "wireguard" && !/\/\d{1,3}$/.test(inputs.wireguard_addresses.value.trim())) return stop(inputs.wireguard_addresses, "Enter the address with its /32 at the end");
      state.vpn = { provider: p, type: kind(), countries: countries.value.trim(),
        ...Object.fromEntries(need.map((k) => [k, inputs[k].value.trim()])) };
      try { await api("/api/stack/preview", { method: "POST", body: body(state) }); return true; }
      catch (e) { return stop(provider, e.message); }
    };
  } else if (id === "usenet") {
    // The same step as the terminal set-up's Your Usenet provider: nothing to answer, the providers and the rules.
    nodes = [usenetProviders()];
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
    const row = (label, value, step) => [el("dt", { text: label }), el("dd", {}, value, " ", change(step, label.toLowerCase()))];
    const picked = data.groups.filter((g) => state.groups.has(g.key)).map((g) => g.name).join(", ") || "None";
    const moving = [...state.moving].map((m) => ({ history: "Watch history", listening: "Listening progress", settings: "App settings" })[m]).filter(Boolean).join(", ");
    nodes = [
      el("p", { text: "Nothing is written or started until you choose Write the files. You can change anything first." }),
      el("dl", { class: "facts" },
        ...row("What it does", picked, "groups"),
        ...row("Apps", [...state.apps].map((k) => apps[k].name).join(", "), "groups"),
        ...row("Media folder", el("code", { text: state.data_dir }), "folders"),
        ...(state.pool ? row("Pool", `${state.pool.path}, from ${state.pool.mounts.length} drives (run its commands first)`, "folders") : []),
        ...(state.advanced ? row("Settings folder", el("code", { text: state.config_dir }), "folders") : []),
        ...(state.apps.has("gluetun") ? row("VPN", `${state.vpn.provider}, ${state.vpn.type === "openvpn" ? "OpenVPN" : "WireGuard"}${state.vpn.countries ? `, ${state.vpn.countries}` : ""}`, "vpn") : []),
        ...(data.servers.length ? row("Moving over", moving || "Nothing", "moving") : [])),
      p.moved.length ? notice("warning", "Some ports moved", p.moved.join(". ") + ".") : null,
      p.later.length ? notice("info", "Started later", `${p.later.join(", ")} ${p.later.length === 1 ? "needs its" : "need their"} own settings file first, so ${p.later.length === 1 ? "it is" : "they are"} written but not started.`) : null,
      p.hooks?.length ? el("p", { class: "small muted", text: `Before System, Apps, Updates changes ${p.hooks.map((k) => apps[k].name).join(" or ")}, it backs up ${p.hooks.length === 1 ? "its" : "their"} database first. If the backup fails, the update stops.` }) : null,
      el("details", { class: "disclosure", open: state.advanced }, el("summary", { text: "The files Starboard writes" }), el("div", { class: "disclosure__body stack-4" },
        el("p", { class: "small", text: "Two files in Starboard's data folder (data/stack): compose.yaml lists the apps; .env holds your settings and secrets. Older ones are kept." }),
        el("h3", { text: "Folders it makes" }), el("ul", {}, p.folders.map((f) => el("li", {}, el("code", { text: f })))),
        el("h3", { text: "Settings (.env)" }),
        el("dl", { class: "facts" }, Object.entries(p.env_shown).flatMap(([k, v]) => [el("dt", {}, el("code", { text: k })), el("dd", { text: v || "(empty)" })])),
        el("h3", { text: "compose.yaml" }), el("pre", { class: "code-block", text: p.compose }))),
    ].filter(Boolean);
    save = async () => {
      state.written = await api("/api/stack/write", { method: "POST", body: body(state) });
      toast("Files written");
      return true;
    };
  } else if (id === "start") {
    const w = state.written || {};
    const log = el("pre", { class: "code-block", hidden: true });
    const status = el("div", { class: "stack-2", "aria-live": "polite" });
    const after = el("div", { class: "stack-4" });
    const showAfter = async () => {
      const finder = await appFinder();
      const add = el("button", { type: "button", class: "btn btn--primary", hidden: !finder.add }, icon("plus"), "Add the ticked apps to Starboard");
      add.addEventListener("click", async () => { add.disabled = true; try { if (await finder.add()) add.hidden = true; } catch (e) { problem(e.message); } finally { add.disabled = false; } });
      after.replaceChildren(el("h3", { text: "Add them to Starboard" }), finder.box, add, ...connectGuide(state, apps));
    };
    const poolFirst = state.pool ? notice("warning", "Make the pool first", `Run the pool commands from the Folders step on the server before you start, so ${state.pool.path} exists.`) : null;
    if (w.can_start || w.starter) {
      const pw = el("input", { class: "input", type: "password", autocomplete: "current-password" });
      const startBtn = el("button", { type: "button", class: "btn btn--primary" }, icon("play"), "Start the apps");
      const form = el("div", { class: "form-stack" },
        el("p", { text: w.can_start
          ? "Starboard asks Docker to download each app and start it, using a short-lived helper. This can take several minutes on the first run."
          : "The Run first window on this computer downloads each app and starts it, so keep that window open. This can take several minutes on the first run." }),
        field("Your Starboard password", pw, { hint: "Starting apps changes this computer, so Starboard checks it is you." }), el("div", { class: "actions" }, startBtn));
      startBtn.addEventListener("click", async () => {
        clearError(pw);
        if (!pw.value) { stop(pw, "Enter your Starboard password"); return; }
        startBtn.disabled = true;
        try {
          await api("/api/stack/start", { method: "POST", body: { password: pw.value } });
          form.hidden = true;
          // One bar for the job, updated in place; a problem goes below it (WIZARD.md section 5, A job's progress).
          const words = el("span", { text: "Downloading and starting the apps. Please wait, this can take some time…" });
          const time = el("span", { class: "numeric nowrap", text: "0 min 00 s" });
          const bar = el("div", { class: "progress progress--busy", role: "progressbar", "aria-label": "Starting the apps",
            "aria-valuetext": "Working" }, el("span"));
          status.replaceChildren(el("div", { class: "meter" }, el("div", { class: "meter__label" }, words, time), bar));
          const began = Date.now();
          for (;;) {
            await new Promise((r) => setTimeout(r, 3000));
            const secs = Math.round((Date.now() - began) / 1000);
            time.textContent = `${Math.floor(secs / 60)} min ${String(secs % 60).padStart(2, "0")} s`;
            const j = await api("/api/stack/job");
            if (!j.finished) continue;
            log.textContent = j.log;
            bar.classList.remove("progress--busy");
            bar.firstChild.style.width = "100%";
            if (j.ok) {
              words.textContent = "The apps are running.";
              bar.setAttribute("aria-valuetext", "Done");
              status.append(notice("success", "The apps are running", "Now connect them: the steps are below."));
              await showAfter();
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
      nodes = [poolFirst, notice("info", "Run one command", "Starboard does not have Docker access, so it cannot start apps itself. On this computer, run:"),
        el("pre", { class: "code-block", text: w.command || "" }), copyButton(w.command || "", "Copy the command"),
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
    fields: [choose, field("Pool folder", path, { hint: "Where the joined folder appears, such as /srv/pool. This becomes your media folder." })],
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
  const host = (k) => (vpn && ["qbittorrent", "sabnzbd", "prowlarr", "flaresolverr"].includes(k) ? "gluetun" : k);
  const hostPort = (k) => Number(String(apps[k]?.ports?.[0]?.port || "0"));
  const open = (k) => el("a", { href: `${location.protocol}//${location.hostname}:${hostPort(k)}`, target: "_blank", rel: "noopener noreferrer" },
    `Open ${apps[k].name}`, el("span", { class: "visually-hidden", text: " (opens in a new tab)" }));
  const code = (t) => el("code", { text: t });
  const arrs = [["radarr", "/data/media/movies", 7878], ["sonarr", "/data/media/tv", 8989], ["lidarr", "/data/media/music", 8686], ["bookshelf", "/data/media/books", 8787]].filter(([k]) => has(k));
  const steps = [];
  if (has("qbittorrent")) {
    steps.push(el("li", {}, el("strong", { text: "qBittorrent. " }), open("qbittorrent"), ". Its first password is in its log (on the server: ", code("docker logs qbittorrent"),
      "). Sign in as ", code("admin"), ", then choose your own password in Options, Web UI. In Options, Downloads, set the default save path to ", code("/data/downloads/torrents"), "."));
  }
  if (has("sabnzbd")) {
    steps.push(el("li", {}, el("strong", { text: "SABnzbd. " }), open("sabnzbd"), ". Its first-run wizard asks for your Usenet provider. In Config, Folders, set the completed folder to ", code("/data/downloads/usenet"), ". Copy its API key from Config, General."));
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
    steps.push(el("li", {}, el("strong", { text: "Jellyfin. " }), open("jellyfin"), ". Its first-run wizard makes your account. Add a library for each kind of media, from ",
      code("/data/media"), " (Films from movies, Shows from tv, and so on)."));
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
  return { apps: [...state.apps], config_dir: state.config_dir, data_dir: state.data_dir, puid: state.puid, pgid: state.pgid, tz: state.tz, vpn: state.vpn };
}
