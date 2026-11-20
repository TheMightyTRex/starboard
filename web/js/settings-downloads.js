// Settings, Downloads: the VPN, Usenet and download hours.

// Settings, Downloads (DASH-226): the VPN (provider, connection, countries, key), the Usenet provider's server with
// Test, and download hours. The same words as the set-ups (web/setup-answers.json). Each is its own level 2 page
// (DASH-390); Download hours is the same field as Settings, General, Download hours (downloadHoursSection), so it
// asks the server for nothing more.
async function startDownloadsSettings() {
  const root = $("#downloads-sections");
  if (!wants(root, "dl-vpn") && !wants(root, "dl-usenet")) {
    root.replaceChildren(...onlyParts(root, [downloadHoursSection("dl-hours")]));
    root.removeAttribute("aria-busy");
    return;
  }
  let d;
  try { d = await api("/api/downloads/settings"); } catch (e) { root.replaceChildren(notice("danger", "Could not read the download settings", e.message)); root.removeAttribute("aria-busy"); return; }
  const words = await setupWords();
  const parts = [];
  if (d.vpn.on) {
    const provider = el("input", { class: "input", value: d.vpn.provider, spellcheck: "false", autocomplete: "off", id: "dl-vpn-provider" });
    const type = el("select", { class: "select", id: "dl-vpn-type" }, [["wireguard", "WireGuard"], ["openvpn", "OpenVPN"]].map(([v, t]) => el("option", { value: v, text: t, selected: d.vpn.type === v })));
    const countries = el("input", { class: "input", value: d.vpn.countries, placeholder: "such as Netherlands", id: "dl-vpn-countries" });
    const key = el("input", { class: "input", type: "password", autocomplete: "off", id: "dl-vpn-key" });
    const address = el("input", { class: "input", autocomplete: "off", placeholder: "ends with /32", id: "dl-vpn-address" });
    const user = el("input", { class: "input", autocomplete: "off", id: "dl-vpn-user" });
    const password = el("input", { class: "input", type: "password", autocomplete: "current-password", id: "dl-vpn-pw" });
    // Only the fields for the chosen connection, as in the set-ups.
    const addressField = field("WireGuard address", address, { hint: "Only when it changed; leave it empty to keep it." });
    const userField = field("OpenVPN user name", user, { hint: "Leave it empty to keep the one there is." });
    const showType = () => { addressField.hidden = type.value !== "wireguard"; userField.hidden = type.value !== "openvpn"; };
    type.addEventListener("change", showType);
    showType();
    const save = el("button", { type: "button", class: "btn btn--primary" }, "Save and restart the VPN");
    const said = el("div", { "aria-live": "polite" });
    save.addEventListener("click", async () => {
      if (!password.value) { setError(password, "Enter your Starboard password"); password.focus(); return; }
      save.disabled = true;
      const vpn = { provider: provider.value.trim().toLowerCase(), type: type.value, countries: countries.value.trim() };
      if (type.value === "wireguard") Object.assign(vpn, { wireguard_private_key: key.value.trim(), wireguard_addresses: address.value.trim() });
      else Object.assign(vpn, { openvpn_user: user.value.trim(), openvpn_password: key.value.trim() });
      try {
        const r = await api("/api/downloads/vpn", { method: "POST", body: { password: password.value, vpn } });
        password.value = ""; key.value = "";
        said.replaceChildren(notice("success", "Saved", r.said), ...(r.command ? [el("pre", { class: "code-block", text: r.command })] : []));
      } catch (e) { said.replaceChildren(notice("danger", "Not saved", e.message)); }
      finally { save.disabled = false; }
    });
    parts.push(section("dl-vpn", "VPN", "Downloads go through your VPN, so your internet provider can tell only that you use a VPN.",
      el("div", { class: "form-stack" },
        field("VPN provider", provider, { hint: "As Gluetun's list writes it, such as surfshark or protonvpn." }), field("Connection", type),
        field("Countries", countries, { hint: "Optional. A nearby country is fastest." }),
        field(d.vpn.has_secret ? "New WireGuard key or OpenVPN password" : "WireGuard key or OpenVPN password", key, { hint: d.vpn.has_secret ? "Leave it empty to keep the one there is." : "" }),
        addressField, userField,
        field("Your Starboard password", password, { required: true, hint: "Saving restarts the VPN, and the apps that go through it, for a moment." })),
      el("div", { class: "actions" }, save), said, vpnRemoveBlock()));
  } else if (wants(root, "dl-vpn") && d.vpn.state?.installed && d.vpn.state?.downloads) {
    parts.push(await vpnAddSection(d));
  }
  if (d.usenet.app) {
    const w = words.usenet;
    const inputs = { host: el("input", { class: "input", id: "dl-u-host", autocomplete: "off", spellcheck: "false" }), ssl: el("input", { type: "checkbox", checked: true }),
      port: el("input", { class: "input", inputmode: "numeric", value: "563", id: "dl-u-port" }), username: el("input", { class: "input", id: "dl-u-user", autocomplete: "off" }),
      password: el("input", { class: "input", type: "password", id: "dl-u-pw", autocomplete: "new-password" }), connections: el("input", { class: "input", inputmode: "numeric", value: "8", id: "dl-u-conn" }) };
    const server = () => ({ host: inputs.host.value.trim(), ssl: inputs.ssl.checked, port: inputs.port.value.trim(), username: inputs.username.value.trim(),
      password: inputs.password.value, connections: inputs.connections.value.trim() });
    const said = el("div", { "aria-live": "polite" });
    const test = el("button", { type: "button", class: "btn" }, w.test);
    test.addEventListener("click", async () => {
      said.replaceChildren(el("p", { class: "small muted", text: "Testing…" }));
      const r = await api("/api/setup/test-usenet", { method: "POST", body: { server: server() } });
      said.replaceChildren(r.ok ? notice("success", "It works", r.message) : notice("danger", "It did not work", r.message));
    });
    const add = el("button", { type: "button", class: "btn btn--primary" }, `Add it to ${d.usenet.app}`);
    add.addEventListener("click", async () => {
      add.disabled = true;
      try { said.replaceChildren(notice("success", "Saved", (await api("/api/downloads/usenet", { method: "POST", body: { server: server() } })).said)); }
      catch (e) { said.replaceChildren(notice("danger", "Not saved", e.message)); }
      finally { add.disabled = false; }
    });
    parts.push(section("dl-usenet", "Usenet provider", `${d.usenet.app} downloads from your Usenet provider's server.`,
      el("p", { class: "small", text: d.usenet.servers.length ? `In ${d.usenet.app} now: ${d.usenet.servers.join(", ")}.` : `${d.usenet.app} has no server yet.` }),
      el("div", { class: "form-stack" }, el("p", { class: "small muted", text: w.server_intro }),
        field(w.host, inputs.host, { hint: w.host_hint }), el("label", { class: "check" }, inputs.ssl, el("span", { text: w.ssl })),
        field(w.port, inputs.port, { hint: w.port_hint }), field(w.username, inputs.username), field(w.password, inputs.password),
        field(w.connections, inputs.connections, { hint: w.connections_hint })),
      el("div", { class: "actions" }, add, test), said));
  }
  if (wants(root, "dl-hours")) parts.push(downloadHoursSection("dl-hours"));
  const yourInstall = el("a", { href: "/settings-install.html", text: "Settings, Your install" });
  if (!d.vpn.on && d.vpn.state?.downloads) { /* the VPN section says it: No VPN, with Add a VPN */ }
  else if (!d.vpn.on && wants(root, "dl-vpn") && partsOf(root)) parts.unshift(notice("info", "No VPN yet", el("span", {}, "Your install has no VPN. Add one in ", yourInstall, ".")));
  else if (!d.usenet.app && wants(root, "dl-usenet") && partsOf(root)) parts.unshift(notice("info", "No Usenet app yet", el("span", {}, "Your install has no Usenet app. Add one in ", yourInstall, ".")));
  else if (!d.vpn.on && !d.usenet.app && !d.vpn.state?.downloads) parts.unshift(notice("info", "Nothing to set here yet", "Your install has no VPN and no Usenet app. Add them in Settings, Your install."));
  root.replaceChildren(...onlyParts(root, parts));
  root.removeAttribute("aria-busy");
}

// DASH-440: an install without a VPN adds one here, with the details the set-ups ask for and the same checks. Starboard
// adds Gluetun, moves the download apps behind it, and points Reelix at them; nothing is sent until Add the VPN.
async function vpnAddSection(d) {
  const w = (await setupWords()).novpn;
  let providers = [];
  try { providers = (await (await fetch("/vpn-providers.json", { cache: "no-cache" })).json()).providers || []; } catch { /* typed instead */ }
  const provider = el("select", { class: "select", id: "dl-vpn-add-provider" }, el("option", { value: "", text: "Choose your VPN provider" }),
    providers.map((v) => el("option", { value: v.id, text: v.name })), el("option", { value: "other", text: "Another one that Gluetun supports" }));
  const other = el("input", { class: "input", id: "dl-vpn-add-other", autocomplete: "off", spellcheck: "false" });
  const otherField = field("Its name, as Gluetun's list writes it", other, { hint: "Enter it in lower case, such as mullvad." });
  const type = el("select", { class: "select", id: "dl-vpn-add-type" }, [["wireguard", "WireGuard"], ["openvpn", "OpenVPN"]].map(([v, t]) => el("option", { value: v, text: t })));
  const inputs = {
    wireguard_private_key: el("input", { class: "input", type: "password", autocomplete: "off", id: "dl-vpn-add-key" }),
    wireguard_addresses: el("input", { class: "input", autocomplete: "off", placeholder: "ends with /32", id: "dl-vpn-add-address" }),
    openvpn_user: el("input", { class: "input", autocomplete: "off", id: "dl-vpn-add-user" }),
    openvpn_password: el("input", { class: "input", type: "password", autocomplete: "off", id: "dl-vpn-add-ovpn" }),
  };
  const countries = el("input", { class: "input", placeholder: "such as Netherlands", id: "dl-vpn-add-countries" });
  const password = el("input", { class: "input", type: "password", autocomplete: "current-password", id: "dl-vpn-add-pw" });
  const wg = el("div", { class: "form-stack" },
    field("WireGuard private key", inputs.wireguard_private_key, { required: true, hint: "On your provider's site, make a WireGuard configuration. Copy the PrivateKey line." }),
    field("WireGuard address", inputs.wireguard_addresses, { required: true, hint: "The Address line from the same configuration, ending /32." }));
  const ovpn = el("div", { class: "form-stack" },
    field("OpenVPN user name", inputs.openvpn_user, { required: true, hint: "Your provider's OpenVPN or service user name." }),
    field("OpenVPN password", inputs.openvpn_password, { required: true }));
  const show = () => { otherField.hidden = provider.value !== "other"; wg.hidden = type.value !== "wireguard"; ovpn.hidden = type.value !== "openvpn"; };
  provider.addEventListener("change", show);
  type.addEventListener("change", show);
  show();
  const form = el("div", { class: "form-stack", id: "dl-vpn-add", hidden: true },
    field("VPN provider", provider, { required: true }), otherField, field("Connection", type, { hint: "WireGuard is quicker and simpler. Use OpenVPN only if your provider has no WireGuard." }),
    wg, ovpn, field("Countries", countries, { hint: "Optional. A nearby country is fastest." }),
    field("Your Starboard password", password, { required: true, hint: "Adding the VPN restarts the download apps behind it, for a moment." }),
    el("p", { class: "small muted", text: "These go in the .env file on this computer only, never in Starboard's settings or its logs." }));
  const said = el("div", { "aria-live": "polite" });
  const add = el("button", { type: "button", class: "btn btn--primary", "aria-expanded": "false", "aria-controls": "dl-vpn-add" }, icon("shield-check"), w.add);
  add.addEventListener("click", async () => {
    if (form.hidden) {
      form.hidden = false;
      add.setAttribute("aria-expanded", "true");
      add.lastChild.textContent = "Add the VPN";
      provider.focus();
      return;
    }
    [provider, other, password, ...Object.values(inputs)].forEach((c) => setError(c, ""));
    const p = provider.value === "other" ? other.value.trim().toLowerCase() : provider.value;
    if (!provider.value) { setError(provider, "Choose your VPN provider"); provider.focus(); return; }
    if (!/^[a-z0-9 _-]{2,40}$/.test(p)) { setError(other, "Enter your VPN provider's name, such as mullvad"); other.focus(); return; }
    const need = type.value === "wireguard" ? ["wireguard_private_key", "wireguard_addresses"] : ["openvpn_user", "openvpn_password"];
    for (const k of need) if (!inputs[k].value.trim()) { setError(inputs[k], "Enter this from your VPN provider"); inputs[k].focus(); return; }
    if (type.value === "wireguard" && !/\/\d{1,3}$/.test(inputs.wireguard_addresses.value.trim())) { setError(inputs.wireguard_addresses, "Enter the address with its /32 at the end"); inputs.wireguard_addresses.focus(); return; }
    if (!password.value) { setError(password, "Enter your Starboard password"); password.focus(); return; }
    add.disabled = true;
    const vpn = { provider: p, type: type.value, countries: countries.value.trim(), ...Object.fromEntries(need.map((k) => [k, inputs[k].value.trim()])) };
    try {
      const r = await api("/api/downloads/vpn", { method: "POST", body: { password: password.value, vpn } });
      password.value = ""; Object.values(inputs).forEach((i) => { i.value = ""; });
      said.replaceChildren(notice("success", "VPN added", r.said), ...(r.command ? [el("pre", { class: "code-block", text: r.command })] : []));
    } catch (e) { said.replaceChildren(notice("danger", "Not added", e.message)); }
    finally { add.disabled = false; }
  });
  return section("dl-vpn", "VPN", "No VPN: downloads use your home internet address.", headChip("No VPN", "muted"),
    el("p", { class: "small", text: w.reminder }),
    el("p", { class: "small muted", text: "Adding one installs Gluetun, sends qBittorrent and the Usenet app through it, and points Reelix at them. The VPN is recommended." }),
    form, el("div", { class: "actions" }, add), said);
}

// Remove the VPN (DASH-440): the same warning as the set-ups, then Gluetun goes and the download apps run on their
// own network with their own ports. Cancel is the default.
function vpnRemoveBlock() {
  const password = el("input", { class: "input", type: "password", autocomplete: "current-password", id: "dl-vpn-remove-pw" });
  const said = el("div", { "aria-live": "polite" });
  const remove = el("button", { type: "button", class: "btn btn--danger", "aria-haspopup": "dialog" }, "Remove the VPN");
  remove.addEventListener("click", async () => {
    setError(password, "");
    if (!password.value) { setError(password, "Enter your Starboard password"); password.focus(); return; }
    const w = (await setupWords()).novpn;
    if (!(await noVpnWarning({ title: w.remove_title, confirm: w.remove_confirm }))) return;
    remove.disabled = true;
    try {
      const r = await api("/api/downloads/vpn/remove", { method: "POST", body: { password: password.value, understood: true } });
      password.value = "";
      said.replaceChildren(notice("success", "VPN removed", r.said), ...(r.command ? [el("pre", { class: "code-block", text: r.command })] : []));
    } catch (e) { said.replaceChildren(notice("danger", "Not removed", e.message)); }
    finally { remove.disabled = false; }
  });
  return el("div", { class: "stack-2 vpn-remove" }, el("h3", { id: "dl-vpn-remove-h", text: "Remove the VPN" }),
    el("p", { class: "small muted", text: "Downloads would then use your home internet address. Not recommended." }),
    el("div", { class: "form-stack" }, field("Your Starboard password", password, { required: true })),
    el("div", { class: "actions" }, remove), said);
}
