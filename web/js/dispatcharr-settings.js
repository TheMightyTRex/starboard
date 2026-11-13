// Settings, Apps, Dispatcharr (DASH-228): Dispatcharr set up from Starboard, so nobody signs in to it. Starboard makes
// its admin and a key for itself, adds the person's IPTV playlist and guide, makes channels from the playlist and adds
// Dispatcharr to Jellyfin as an HDHomeRun tuner with its guide. Starboard's own Live TV stays the Live TV of every
// install; Dispatcharr is the add-on for paid IPTV (DASH-222).

function dpDone(lines) {
  // What was done, beside the control that was used (settings pattern 2), else to screen readers.
  settingSaved((lines || []).filter(Boolean).join(". ") || "Saved");
}

async function dpSend(path, method, body, control) {
  try {
    const out = await api(path, { method, body });
    dpDraw(out.state, control?.id);
    dpDone(out.done);
    return out;
  } catch (err) { problem(err.message, control); return null; }
}

function dpConnect(s) {
  const pw = el("input", { class: "input", type: "password", id: "dp-password", autocomplete: "current-password" });
  const go = el("button", { type: "submit", class: "btn btn--primary", id: "dp-connect" }, icon("link"), "Set up Dispatcharr");
  const form = el("form", { class: "form-stack", novalidate: true },
    field("Your Starboard password", pw, { required: true,
      hint: "Dispatcharr's admin is admin, with this password, as in your other apps. Starboard then keeps a key for Dispatcharr, not the password." }),
    el("div", { class: "actions" }, go));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    setError(pw, "");
    if (!pw.value) { setError(pw, "Type your Starboard password"); pw.focus(); return; }
    go.disabled = true;
    try {
      const out = await api("/api/dispatcharr/connect", { method: "POST", body: { password: pw.value } });
      dpDraw(out.state, "dp-kind-m3u");
      dpDone(out.done);
    } catch (err) {
      if (err.status === 401 || err.status === 429) { setError(pw, err.message); pw.focus(); }
      else problem(err.message, go);
    } finally { go.disabled = false; }
  });
  return section("dp-connect", "Set up Dispatcharr", `Dispatcharr is installed at ${s.address}. Starboard makes its admin and a key for itself.`, form);
}

function dpSource(s) {
  const src = s.source || { kind: "m3u", url: "", username: "", max_streams: 0 };
  const kind = (value, label, hint) => el("label", { class: "option-card" },
    el("input", { type: "radio", name: "dp-kind", id: `dp-kind-${value}`, value, checked: src.kind === value }),
    el("strong", { text: label }), el("small", { text: hint }));
  const kinds = el("fieldset", { class: "stack-2" }, el("legend", { class: "field__label", text: "What your provider gave you" }),
    el("div", { class: "option-cards" },
      kind("m3u", "Playlist address", "One address that ends in .m3u or .m3u8, or has get.php in it."),
      kind("xc", "Xtream Codes", "A server address with a user name and password.")));
  const url = el("input", { class: "input", id: "dp-url", type: "url", value: src.url, autocomplete: "off", spellcheck: "false", inputmode: "url" });
  const user = el("input", { class: "input", id: "dp-user", value: src.username, autocomplete: "off", spellcheck: "false" });
  const pass = el("input", { class: "input", id: "dp-pass", type: "password", autocomplete: "new-password",
    placeholder: s.source?.kind === "xc" ? "Set. Leave empty to keep it" : "" });
  const guide = el("input", { class: "input", id: "dp-guide", type: "url", value: s.guide?.url || "", autocomplete: "off", spellcheck: "false", inputmode: "url" });
  const most = el("input", { class: "input", id: "dp-most", type: "number", min: "0", max: "50", step: "1", value: String(src.max_streams || 0) });
  const urlField = field("Playlist address", url, { required: true });
  const userField = field("User name", user, { required: true });
  const passField = field("Password", pass, { hint: "Dispatcharr keeps it. Starboard does not." });
  const save = el("button", { type: "submit", class: "btn btn--primary", id: "dp-save" }, "Save");
  const form = el("form", { class: "form-stack", novalidate: true }, kinds, urlField, userField, passField,
    field("Guide address (optional)", guide, { hint: "An XMLTV address, often ending in .xml or .xml.gz, or xmltv.php. Without one, channels have no programmes." }),
    field("Streams at once", most, { short: true, hint: "How many your provider lets you watch at the same time. 0 means no limit." }),
    el("div", { class: "actions" }, save));
  const show = () => {
    const xc = form.querySelector("input[name=dp-kind]:checked")?.value === "xc";
    userField.hidden = !xc;
    passField.hidden = !xc;
    urlField.querySelector("label").firstChild.textContent = xc ? "Server address" : "Playlist address";
  };
  form.addEventListener("change", (e) => { if (e.target.name === "dp-kind") show(); });
  show();
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    for (const c of [url, user, guide, most]) setError(c, "");
    const xc = form.querySelector("input[name=dp-kind]:checked").value === "xc";
    if (!url.value.trim()) { setError(url, xc ? "Type your IPTV server's address" : "Type your playlist address"); url.focus(); return; }
    if (xc && !user.value.trim()) { setError(user, "Type the user name your IPTV provider gave you"); user.focus(); return; }
    save.disabled = true;
    await dpSend("/api/dispatcharr", "PUT", { kind: xc ? "xc" : "m3u", url: url.value.trim(), username: user.value.trim(), password: pass.value,
      guide: guide.value.trim(), max_streams: Number(most.value || 0) }, save);
    save.disabled = false;
  });
  const status = s.source && s.source.message
    ? notice(s.source.status === "error" ? "warning" : "info", "What Dispatcharr says about your playlist", s.source.message) : null;
  return section("dp-source", "Your IPTV source", "Your provider's playlist and guide. Starboard adds them to Dispatcharr.", status, form);
}

function dpChannels(s) {
  const facts = el("dl", { class: "facts" }, ...[["Streams in your playlist", s.streams], ["Channels in Dispatcharr", s.channels]]
    .flatMap(([k, v]) => [el("dt", { text: k }), el("dd", { text: String(v) })]));
  let action = null;
  if (s.source && !s.channels) {
    const make = el("button", { type: "button", class: "btn", id: "dp-make" }, icon("list-plus"), "Make channels");
    make.addEventListener("click", async () => { make.disabled = true; await dpSend("/api/dispatcharr/channels", "POST", {}, make); make.disabled = false; });
    action = el("div", { class: "actions" }, make);
  }
  const say = !s.source ? "Add your IPTV source first."
    : s.channels ? "Choose and order channels in Dispatcharr, Channels. Jellyfin shows what Dispatcharr offers."
      : `Jellyfin sees channels, not streams. Make channels turns up to ${s.most_channels} streams into channels; choose fewer in Dispatcharr later.`;
  return section("dp-channels", "Channels", say, facts, action);
}

function dpJellyfin(s) {
  const j = s.jellyfin || {};
  let body;
  if (j.connected === null) {
    body = notice("info", "Jellyfin is not connected to Starboard", "Add Jellyfin's API key in Settings, Apps, Manage apps, then come back here.");
  } else if (j.connected) {
    body = notice("success", "Jellyfin has Dispatcharr", "As an HDHomeRun tuner, with Dispatcharr's guide linked to it. Watch in Jellyfin, Live TV.");
  } else {
    const add = el("button", { type: "button", class: "btn", id: "dp-jellyfin" }, icon("tv"), "Add to Jellyfin");
    add.addEventListener("click", async () => { add.disabled = true; await dpSend("/api/dispatcharr/jellyfin", "POST", {}, add); add.disabled = false; });
    body = el("div", { class: "stack-2" },
      el("p", { text: j.tuner ? "Jellyfin has the tuner but not the guide yet." : "Jellyfin does not have Dispatcharr yet. Saving your source adds it." }),
      el("div", { class: "actions" }, add));
  }
  return section("dp-jellyfin", "Jellyfin", "Dispatcharr as a tuner in Jellyfin, with its guide.", body);
}

function dpDraw(s, focusId) {
  const box = $("#dispatcharr-sections");
  box.removeAttribute("aria-busy");
  if (!s.installed) {
    box.replaceChildren(section("dp-none", "Dispatcharr is not installed", null,
      notice("info", "Add Dispatcharr in Your install", "It is an add-on for paid IPTV. Starboard's own Live TV needs no add-on.",
        el("a", { class: "btn", href: "/settings-install.html" }, "Your install"))));
    return;
  }
  if (!s.connected) { box.replaceChildren(dpConnect(s)); return; }
  const others = s.others?.length ? el("p", { class: "small muted", text: `Dispatcharr also has sources you added yourself: ${s.others.join(", ")}. Starboard leaves them as they are.` }) : null;
  box.replaceChildren(...[dpSource(s), dpChannels(s), dpJellyfin(s), others].filter(Boolean));
  if (focusId) document.getElementById(focusId)?.focus();
}

async function startDispatcharr() {
  try { dpDraw(await api("/api/dispatcharr")); }
  catch (e) {
    $("#dispatcharr-sections").removeAttribute("aria-busy");
    $("#dispatcharr-sections").replaceChildren(notice("warning", "Dispatcharr did not answer", e.message));
  }
}
