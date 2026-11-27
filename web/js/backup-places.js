// Where backups go (several places, 26 November 2026), on Settings, General, Backup/Logs.
// Every place a copy can go is listed with its own switch, keep count and last copy in words and a shape. A cloud service
// is connected by the wizard (cloud-wizard.js), as many times as you like; a folder, an SMB share, an NFS share or your own
// rclone remote has one form in a slide-out. A backup counts as safe only when each place that is on has read it back.
// The server's settings zip goes to the same places, encrypted first. Nothing here runs until the page is open.

const PLACE_KINDS = [
  ["disk", "Folder on this server or the pool", "A USB disk, a second disk or the pool, as a folder."],
  ["smb", "Network share (SMB)", "A Windows computer or a NAS, such as //192.168.1.20/backups."],
  ["nfs", "Network share (NFS)", "Such as 192.168.1.20:/export/backups."],
];
const KIND_ICON = { disk: "hard-drive", smb: "network", nfs: "server", rclone: "cloud" };
// Google Drive and OneDrive have no logo here (27 November 2026): Google allows only its own unchanged logo and Microsoft
// allows its logos only with a licence, so each shows the plain cloud icon and its full name. Add the official, unchanged
// mark here only when the owner has it from the company (docs/LOGOS.md).
const BRAND_LOGOS = ["dropbox", "b2", "s3", "webdav"];

// The logo of a service (the plain name always sits beside it, so it is decorative for a screen reader) or, for a place
// on this network, a plain icon. The brand logos load from one small file, only on this page.
function placeLogo(place, serviceId) {
  const id = serviceId || (place && place.kind === "rclone" ? place.service : "");
  const span = el("span", { class: "place-logo", "aria-hidden": "true" });
  if (BRAND_LOGOS.includes(id)) {
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("class", "place-logo__img");
    svg.setAttribute("width", "24"); svg.setAttribute("height", "24"); svg.setAttribute("focusable", "false");
    const use = document.createElementNS(ns, "use");
    use.setAttribute("href", `/icons/services.svg#s-${id}`);
    svg.append(use);
    span.append(svg);
  } else {
    span.append(icon(serviceId ? "plug" : KIND_ICON[place?.kind] || "cloud", 24));
  }
  return span;
}

function placeField(label, input, hint) {
  if (hint) input.setAttribute("aria-describedby", `${input.id}-hint`);
  return el("div", { class: "field" }, el("label", { for: input.id, text: label }),
    hint ? el("span", { class: "hint", id: `${input.id}-hint`, text: hint }) : null, input);
}

// The last copy to one place: a shape and words, never colour alone.
function placeState(p) {
  const s = p.status || {};
  let more = "";
  if (p.enabled && s.state === "done" && s.finished) more = ` ${formatDate(s.finished * 1000, true)}`;
  if (p.enabled && s.state === "failed" && s.error) more = `: ${s.error}`;
  const tone = !p.enabled ? "muted" : s.state === "done" ? "success" : s.state === "failed" ? "danger" : "neutral";
  return el("p", { class: "place-state", "data-tone": tone }, icon(p.shape || "circle", 18), el("strong", { text: p.state_word }), more ? el("span", { class: "muted", text: more }) : null);
}

// Test connection: the result beside the place, kept by the server so it shows when the page is opened again.
function testedLine(t) {
  if (!t) return el("p", { class: "small muted", text: "Not tested yet." });
  const at = t.at ? formatDate(t.at * 1000, true) : "";
  if (t.ok) {
    return el("p", { class: "tested", "data-tone": "success" }, icon("circle-check", 20), el("strong", { text: "Connected" }),
      el("span", { class: "muted", text: `Tested ${at}${t.free != null ? `, ${formatBytes(t.free)} free` : ""}${t.count != null ? `, ${t.count} full ${t.count === 1 ? "backup" : "backups"} there` : ""}` }));
  }
  const text = String(t.error || "The test did not work").replace(/^SIGNIN\|/, "");
  return el("div", { class: "stack-2" }, el("p", { class: "tested", "data-tone": "danger" }, icon("circle-alert", 20), el("strong", { text: "Not connected" }),
    el("span", { class: "muted", text: `Tested ${at}` })), el("p", { text }));
}

// The form for a folder, a share or your own rclone remote, in a slide-out. place is null to add one.
function openPlaceForm(opener, place, kind, onSaved) {
  const adding = !place;
  const k = place ? place.kind : kind;
  const kindName = PLACE_KINDS.find((x) => x[0] === k)?.[1] || (k === "rclone" ? "Your own rclone remote" : "A place");
  const id = (n) => `place-${n}`;
  const name = el("input", { class: "input", id: id("name"), value: place?.name || "", maxlength: "60", autocomplete: "off", spellcheck: "false" });
  const keep = el("input", { class: "input input--narrow", id: id("keep"), type: "number", min: "1", max: "50", value: String(place?.keep || 5), inputmode: "numeric" });
  const keepSettings = el("input", { class: "input input--narrow", id: id("keep-settings"), type: "number", min: "1", max: "50", value: String(place?.keep_settings || 2), inputmode: "numeric" });
  const mine = el("input", { class: "input", id: id("mine"), type: "password", autocomplete: "current-password" });
  const fields = [placeField("Name", name, "Optional. A short name for the list, such as Pool disk or The NAS.")];
  let get = () => ({});
  if (k === "disk") {
    const folder = locationPicker({ id: id("folder"), label: "Folder", app: "host", setting: "backups", value: place?.folder || "",
      hint: "Not the folder the full backups are made in. A USB disk must be plugged in when a backup is made." });
    fields.push(folder.node);
    get = () => ({ folder: folder.input.value.trim() });
  } else if (k === "smb") {
    const smb = el("input", { class: "input", id: id("smb"), value: place?.smb || "", spellcheck: "false", autocomplete: "off", placeholder: "//192.168.1.20/backups" });
    const user = el("input", { class: "input", id: id("smb-user"), value: place?.smb_user || "", spellcheck: "false", autocomplete: "off" });
    const pass = el("input", { class: "input", id: id("smb-password"), type: "password", autocomplete: "new-password" });
    fields.push(placeField("Share", smb, "As //computer/share, with a folder after it if you like."),
      placeField("User name", user, "Leave empty for a share anyone on your network may write to."),
      placeField("Password", pass, place?.smb_password_set ? "Kept. Leave empty to keep it." : "The share's own password, kept by Starboard only."));
    get = () => ({ smb: smb.value.trim(), smb_user: user.value.trim(), smb_password: pass.value });
  } else if (k === "nfs") {
    const nfs = el("input", { class: "input", id: id("nfs"), value: place?.nfs || "", spellcheck: "false", autocomplete: "off", placeholder: "192.168.1.20:/export/backups" });
    fields.push(placeField("Share", nfs, "As computer:/folder. The share must let this computer write."));
    get = () => ({ nfs: nfs.value.trim() });
  } else {
    const remote = el("input", { class: "input", id: id("remote"), value: place?.remote || "", spellcheck: "false", autocomplete: "off", placeholder: "mycloud:starboard-backups" });
    const config = el("textarea", { class: "input", id: id("config"), rows: "5", spellcheck: "false", autocomplete: "off" });
    fields.push(placeField("Remote and folder", remote, "As name:folder, the remote's name as it is in your rclone.conf."),
      placeField("The remote's part of rclone.conf", config, place?.rclone_config_set ? "Kept. Leave empty to keep it, or paste it again to change it."
        : "Paste the lines from [name] to the next [ ]. Kept by Starboard only."));
    get = () => ({ remote: remote.value.trim(), rclone_config: config.value });
  }
  fields.push(placeField("Keep the newest full backups", keep, "How many stay there. Older ones there are removed."),
    placeField("Keep the newest server settings backups", keepSettings, "Each one is large, so the default is 2."),
    placeField("Your Starboard password", mine, "Asked each time, as a share's password and rclone's config are kept."));
  const errorBox = el("div", { id: id("error"), tabindex: "-1" });
  const save = el("button", { type: "submit", class: "btn btn--primary", id: id("save") }, adding ? "Add this place" : "Save this place");
  const form = el("form", { class: "form-stack", novalidate: true }, ...fields, errorBox, el("div", { class: "actions" }, save));
  const panel = sidePanel({ title: adding ? `Add: ${kindName}` : `Change ${place.title}`, opener, body: [form] });
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorBox.replaceChildren();
    save.disabled = true;
    try {
      await api("/api/backup/copies", { method: "PUT", body: { password: mine.value, id: adding ? "new" : place.id, kind: k, name: name.value.trim(),
        keep: Number(keep.value), keep_settings: Number(keepSettings.value), ...get() } });
      panel.close();
      await onSaved(adding ? "places-add" : null);
      announce(adding ? "Added: each new full backup is copied there" : "Saved");
    } catch (err) {
      errorBox.replaceChildren(el("div", { class: "notice", "data-tone": "danger", role: "alert" }, icon("circle-alert"),
        el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: "Not saved" }), el("p", { text: err.message }))));
      (err.status === 401 || err.status === 429 ? mine : errorBox).focus();
      save.disabled = false;
    }
  });
}

// The key for the server settings copies is shown once, in words you can store: copy it, or save it as a file.
function showKeyCard(card, opener) {
  const box = el("textarea", { class: "input", id: "key-card", rows: "12", readonly: true, "aria-label": "The key and how to open a copy", spellcheck: "false" });
  box.value = card.text;
  const copy = el("button", { type: "button", class: "btn", id: "key-copy" }, icon("copy"), "Copy the key");
  copy.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(card.text); announce("The key is copied"); } catch (e) { box.select(); announce("Select the text and copy it"); }
  });
  const file = el("button", { type: "button", class: "btn", id: "key-file" }, icon("download"), "Save the key as a file");
  file.addEventListener("click", () => {
    const url = URL.createObjectURL(new Blob([card.text], { type: "text/plain" }));
    const a = el("a", { href: url, download: "starboard-server-settings-key.txt" });
    document.body.append(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    announce("The key is saved as a file");
  });
  return confirmDialog({ title: "Keep this key safe", confirm: "I have stored it", cancel: "Close", careful: true,
    message: el("div", { class: "stack-3" },
      el("p", { text: "Starboard shows this once. Without it, the encrypted server settings copies cannot be opened, even by Starboard on a new server." }),
      el("p", { text: "Store it in your password manager, and keep a printed or written copy somewhere that is not this server. Do not store it only in the cloud service the copies go to." }),
      box, el("div", { class: "actions" }, copy, file)) });
}

// The server's settings zip ------------------------------------------------------------------------------------------
function zipPart(z, reload) {
  if (!z) return null;
  const key = z.key.set;
  const make = el("button", { type: "button", class: "btn btn--primary", id: "zip-key" }, icon("key-round"), "Make the key");
  make.addEventListener("click", async (e) => {
    const r = await withPassword({ title: "Make the key for the server settings copies?",
      message: "Starboard makes two long phrases and shows them once. You store them. Starboard keeps a copy in its own folder only so it can encrypt the next copy; it is never in a backup.",
      confirm: "Make the key", run: (password) => api("/api/backup/settings-zip/key", { method: "POST", body: { password } }) });
    if (!r) return;
    await showKeyCard(r.card, e.currentTarget);
    await reload("zip-copy");
  });
  const now = el("button", { type: "button", class: "btn", id: "zip-copy" }, icon("copy"), "Copy the newest server settings backup now");
  now.disabled = !key || !z.newest || z.places.every((p) => !p.enabled) || z.places.some((p) => p.state === "running");
  now.addEventListener("click", async () => {
    now.disabled = true;
    try { await api("/api/backup/settings-zip/copy", { method: "POST", body: {} }); announce("Encrypting and copying the server settings backup"); await reload("zip-copy"); }
    catch (err) { announce(`Not copied: ${err.message}`); $("#zip-status")?.replaceChildren(notice("danger", "Not copied", err.message)); now.disabled = false; now.focus(); }
  });
  const rows = z.places.map((p) => el("li", { class: "row" }, placeLogo({ kind: "disk" }, null),
    el("div", { class: "row__text" }, el("div", { class: "row__title", text: p.title }),
      el("div", { class: "row__meta" }, el("span", { class: "place-state", "data-tone": p.state === "done" ? "success" : p.state === "failed" ? "danger" : "neutral" },
        icon(p.shape, 18), el("strong", { text: p.enabled ? p.state_word : "Deactivated" }), p.error ? el("span", { class: "muted", text: `: ${p.error}` }) : null)))));
  return el("div", { class: "stack-3", id: "zip-part" },
    el("h3", { id: "zip-h", text: "Server settings backup, encrypted" }),
    el("p", { class: "small muted", text: "The server's own backup job writes a zip of the apps' settings with API keys and passwords. Starboard sends it to the same places, but only after encrypting it with rclone crypt, and only after its key is made. The plain file is never uploaded." }),
    key ? notice("success", "The key is kept", `Made ${when(z.key.made)}. You hold the other copy: without it the copies cannot be opened.`)
      : notice("warning", "No key yet", "Nothing is sent until the key is made, so the settings zip stays on this computer only."),
    z.newest ? el("p", { class: "small", text: `Newest: ${z.newest.name} (${formatBytes(z.newest.size)}).` }) : el("p", { class: "small muted", text: "No server settings backup was found in the server backups folder." }),
    z.places.length ? el("ul", { class: "rows", "aria-labelledby": "zip-h" }, rows) : null,
    el("div", { class: "actions" }, key ? now : make),
    el("div", { id: "zip-status", "aria-live": "polite" }));
}

async function loadCopies(focusId) {
  const body = $("#copies-body");
  let c, z = null, list = null;
  try { c = await api("/api/backup/copies"); } catch (e) { body.replaceChildren(notice("danger", "Could not read where the backups go", e.message)); return; }
  try { z = await api("/api/backup/settings-zip"); } catch (e) { z = null; }
  try { list = await api("/api/backup/cloud/services"); } catch (e) { list = null; }
  body.removeAttribute("aria-busy");
  const places = c.destinations || [];
  const reload = (id) => loadCopies(id);
  const running = places.some((p) => p.status?.state === "running") || (z?.places || []).some((p) => p.state === "running");

  // Safe or not, in words, first.
  const safe = c.safe || { safe: false, words: "" };
  const summary = el("div", { id: "places-safe", role: "status" },
    places.length ? notice(safe.safe ? "success" : "warning", safe.safe ? "Safe" : "Not yet safe", safe.words.replace(/^(Safe|Not yet safe): /, "").replace(/^./, (ch) => ch.toUpperCase())) : notice("warning", "Only on this computer", "No place is set up for copies. Add one under Add a place."));

  // The places.
  const rows = places.map((p) => {
    const sw = el("input", { type: "checkbox", role: "switch", id: `place-on-${p.id}`, checked: p.enabled, "aria-label": `Copy backups to ${p.title}` });
    sw.addEventListener("change", async () => {
      sw.disabled = true;
      try {
        await api("/api/backup/copies/enabled", { method: "POST", body: { id: p.id, on: sw.checked } });
        announce(`${p.title}: ${sw.checked ? "on" : "off"}`);
        await reload(sw.id);
      } catch (err) { sw.checked = !sw.checked; sw.disabled = false; announce(`Not changed: ${err.message}`); }
    });
    const test = el("button", { type: "button", class: "btn", id: `place-test-${p.id}` }, icon("plug"), "Test", el("span", { class: "visually-hidden", text: ` ${p.title}` }));
    test.addEventListener("click", async () => {
      test.disabled = true; test.setAttribute("aria-busy", "true");
      announce(`Testing ${p.title}`);
      try {
        const r = await api("/api/backup/copies/test", { method: "POST", body: { id: p.id } });
        await reload(test.id);
        announce(r.tested?.ok ? `Connected: ${p.title}` : `Not connected: ${p.title}. ${String(r.tested?.error || "").replace(/^SIGNIN\|/, "")}`);
      } catch (err) {
        test.disabled = false; test.removeAttribute("aria-busy");
        $(`#place-tested-${p.id}`)?.replaceChildren(notice("danger", "The test did not run", err.message));
        announce(`The test did not run: ${err.message}`); test.focus();
      }
    });
    const edit = el("button", { type: "button", class: "btn", id: `place-edit-${p.id}` }, icon("pencil"), "Change", el("span", { class: "visually-hidden", text: ` ${p.title}` }));
    edit.addEventListener("click", (e) => {
      if (p.kind === "rclone" && p.service) {
        cloudWizard({ opener: e.currentTarget, startAt: "signin", serviceId: p.service, dest: p.id, folder: (p.remote.split(":")[1] || ""), onSaved: () => reload(edit.id) });
      } else openPlaceForm(e.currentTarget, p, p.kind, reload);
    });
    const needsSignin = p.tested && !p.tested.ok && String(p.tested.error || "").startsWith("SIGNIN|") && p.service;
    const remove = el("button", { type: "button", class: "btn btn--quiet", id: `place-remove-${p.id}` }, icon("trash-2"), "Remove", el("span", { class: "visually-hidden", text: ` ${p.title}` }));
    remove.addEventListener("click", async () => {
      const r = await withPassword({ title: `Remove ${p.title}?`,
        message: "New backups are no longer copied there, and Starboard forgets its password or sign-in. Copies already made stay where they are.",
        confirm: "Remove this place", danger: true, run: (password) => api("/api/backup/copies/forget", { method: "POST", body: { id: p.id, password } }) });
      if (!r) return;
      await reload("places-add");
      announce(`Removed ${p.title}`);
    });
    const busy = p.status?.state === "running";
    test.disabled = busy;
    return el("li", { class: "place", id: `place-${p.id}` },
      el("div", { class: "place__head" }, placeLogo(p),
        el("div", { class: "place__text" }, el("h4", { class: "place__title", text: p.title }),
          el("p", { class: "small muted", text: `${p.service_name && p.service_name !== p.title ? `${p.service_name}, ` : ""}${p.kind === "rclone" ? p.where_words : `${p.kind_words}: ${p.where}`}${p.account ? `, signed in as ${p.account}` : ""}. Keeps the newest ${p.keep} full ${p.keep === 1 ? "backup" : "backups"}.` })),
        el("label", { class: "switch place__switch" }, sw, el("span", { class: "visually-hidden", text: `Copy backups to ${p.title}` }))),
      placeState(p),
      el("div", { id: `place-tested-${p.id}` }, testedLine(p.tested)),
      el("div", { class: "actions" }, test, needsSignin ? (() => {
        const again = el("button", { type: "button", class: "btn", id: `place-signin-${p.id}` }, "Sign in again", el("span", { class: "visually-hidden", text: ` to ${p.title}` }));
        again.addEventListener("click", (e) => cloudWizard({ opener: e.currentTarget, startAt: "signin", serviceId: p.service, dest: p.id, folder: (p.remote.split(":")[1] || ""), onSaved: () => reload(again.id) }));
        return again;
      })() : null, edit, remove));
  });
  const list0 = places.length
    ? el("ul", { class: "places", "aria-labelledby": "places-h" }, rows)
    : el("p", { class: "small muted", text: "No places yet." });

  // Add a place: every kind of place there can be, each with its logo and its plain name.
  const addButtons = [];
  const count = (pred) => places.filter(pred).length;
  const addCard = (logo, title, text, extra, onPick, id) => {
    const b = el("button", { type: "button", class: "place-add", id }, logo, el("span", { class: "place-add__text" }, el("strong", { text: title }), el("small", { text }),
      extra ? el("small", { class: "muted", text: extra }) : null));
    b.addEventListener("click", (e) => onPick(e.currentTarget));
    addButtons.push(el("li", {}, b));
  };
  for (const [kind, title, text] of PLACE_KINDS) {
    const n = count((p) => p.kind === kind);
    addCard(placeLogo({ kind }), title, text, n ? `${n} added` : "", (opener) => openPlaceForm(opener, null, kind, reload), `place-add-${kind}`);
  }
  for (const s of (list?.services || [])) {
    const n = count((p) => p.kind === "rclone" && (p.service === s.id || (s.id === "own" && !p.service)));
    addCard(placeLogo(null, s.id), s.name, s.line, n ? `${n} connected` : "", (opener) =>
      cloudWizard({ opener, startAt: "signin", serviceId: s.id, onSaved: () => reload("places-add") }), `place-add-${s.id}`);
  }
  const addSection = el("div", { class: "stack-3" }, el("h3", { id: "places-add", tabindex: "-1", text: "Add a place" }),
    el("p", { class: "small muted", text: places.length >= (c.max_places || 8) ? "Starboard keeps up to 8 places. Remove one to add another." : "Choose where else a backup can go. You can add the same kind of place more than once, such as two cloud accounts." }),
    el("ul", { class: "place-adds", "aria-labelledby": "places-add" }, addButtons));
  if (places.length >= (c.max_places || 8)) for (const b of addSection.querySelectorAll("button")) b.disabled = true;

  // Copy now, and the detailed log.
  const now = el("button", { type: "button", class: "btn", id: "copies-now" }, icon("copy"), "Copy the newest full backup now");
  now.disabled = running || !places.some((p) => p.enabled);
  const state = el("div", { id: "copies-state", "aria-live": "polite" });
  now.addEventListener("click", async () => {
    now.disabled = true;
    try { await api("/api/backup/copies/now", { method: "POST", body: {} }); announce("Copying the newest full backup"); await reload("copies-now"); }
    catch (err) { state.replaceChildren(notice("danger", "Not copied", err.message)); now.disabled = false; now.focus(); }
  });
  const detailed = el("input", { type: "checkbox", role: "switch", id: "copies-detailed", "aria-labelledby": "copies-detailed-l", "aria-describedby": "copies-detailed-h", checked: !!c.detailed_log });
  const detailedRow = el("ul", { class: "settings-rows" }, el("li", { class: "setting" },
    el("div", { class: "setting__text" }, el("span", { class: "setting__label", id: "copies-detailed-l", text: "Detailed log for backup connections" }),
      el("span", { class: "setting__hint", id: "copies-detailed-h",
        text: "Writes each step of a test, a copy and connecting a cloud service to Starboard's log, on System, Logs, with the service's own words. Passwords, keys and sign-in codes are left out. Use it to find out why a connection does not work." })),
    el("div", { class: "setting__control" }, el("label", { class: "switch" }, detailed))));
  detailed.addEventListener("change", async () => {
    try {
      await api("/api/backup/copies/detailed", { method: "POST", body: { on: detailed.checked } });
      announce(detailed.checked ? "Detailed log for backup connections is on" : "Detailed log for backup connections is off");
    } catch (err) { detailed.checked = !detailed.checked; announce(`Not saved: ${err.message}`); }
  });

  body.replaceChildren(summary, el("h3", { id: "places-h", text: "Places backups go to" }), list0,
    el("div", { class: "actions" }, now), state, addSection, zipPart(z, reload) || "", detailedRow);
  if (focusId) $(`#${focusId}`)?.focus();
  if (running) {
    setTimeout(async () => {
      if (!document.body.contains(summary)) return;
      const was = body.contains(document.activeElement) ? document.activeElement.id : null;
      await loadCopies(was);
    }, 3000);
  }
}
