// Bring in media you already have (DASH-455, owner, 16 November 2026): one step in four parts, the same in the set-up
// guide, on its own page (Library, Bring in media; Still to set up) and in the terminal set-up
// (starboard/terminal_setup.py, step_bring). Copies only: nothing at a source is renamed, moved or deleted.
// 1. Sources, in order, with Move up and Move down (the earlier one wins when a title is in two places).
// 2. What is in each, with a correction for a whole source or one folder.
// 3. Check names: Matched, Needs a look and Left where it is, and the space needed.
// 4. Copy: what happens, then the progress (Pause, Carry on), then the report.
// Loaded after common.js and settings-core.js (notice, field, wizardFrame, stepTable, stepNamed).

const BRING_PARTS = ["bring-sources", "bring-what", "bring-names", "bring-copy"];
const BRING_KINDS = ["films", "series", "music", "books", "audiobooks"];
const BRING_WORDS = { films: "Films", series: "Series", music: "Music", books: "Books", audiobooks: "Audiobooks" };
const BRING_COUNT = { films: ["film", "films"], series: ["series", "series"], music: ["album", "albums"], books: ["book", "books"], audiobooks: ["audiobook", "audiobooks"] };
const SOURCE_ICONS = { computer: "monitor", disk: "hard-drive", smb: "network", nfs: "network", onedrive: "cloud", gdrive: "cloud" };
const SOURCE_KIND_WORDS = { computer: "Folder on this computer", disk: "Another disk", smb: "Network share (SMB)", nfs: "Network share (NFS)", onedrive: "OneDrive", gdrive: "Google Drive" };
const PHASE_WORDS = { starting: "Starting", queued: "Waiting for another copy to finish", reelix: "Waiting for Reelix to start",
  checking: "Checking each name with Reelix", downloading: "Copying down from the cloud service", copying: "Copying", adding: "Adding each title to Reelix", done: "Finished" };

function bringCount(kind, n) { return `${Number(n).toLocaleString("en-GB")} ${BRING_COUNT[kind]?.[n === 1 ? 0 : 1] || kind}`; }

// The parts of the step, for the set-up guide's step list: each part is a step in the count (WIZARD.md, section 3).
function bringInSteps(T, { skippable = true } = {}) {
  const names = BRING_PARTS.map((id) => stepNamed(T, id).title);
  return BRING_PARTS.map((id, i) => ({ id, ...stepNamed(T, id), group: "bring", groupTitle: "Bring in media", parts: names, part: i, skippable }));
}

// One part's content: { nodes, save }. ctx: { inWizard, media, go(id) }.
async function bringInStep(id, ctx = {}) {
  if (id === "bring-sources") return bringSources(ctx);
  if (id === "bring-what") return bringWhat(ctx);
  if (id === "bring-names") return bringNames(ctx);
  return bringCopy(ctx);
}

// 1. Sources, in order ---------------------------------------------------------------------------------------------------
async function bringSources(ctx) {
  let d;
  try { d = await api("/api/bring-in"); } catch (e) { return { nodes: [notice("danger", "Could not read your sources", e.message)], save: async () => false }; }
  if (ctx.media && ctx.media !== d.media) {
    try { d = await api("/api/bring-in/sources", { method: "PUT", body: { sources: d.sources, media: ctx.media } }); } catch { /* the media folder is read again later */ }
  }
  const status = el("p", { class: "visually-hidden", role: "status" });
  const list = el("ol", { class: "sortable bring-sources", "aria-label": "Sources, the first one wins" });
  const empty = emptyState("No sources yet", "Add the folders, disks, shares or cloud services your media is in now.");
  const save = async (sources = d.sources) => {
    d = await api("/api/bring-in/sources", { method: "PUT", body: { sources } });
    return d;
  };
  const row = (s, i) => {
    const change = el("button", { type: "button", class: "btn btn--quiet btn--compact", "aria-haspopup": "dialog" }, "Change folder",
      el("span", { class: "visually-hidden", text: ` for ${s.name}` }));
    change.addEventListener("click", () => pickFor(s, change));
    const remove = el("button", { type: "button", class: "btn btn--quiet btn--compact" }, "Remove", el("span", { class: "visually-hidden", text: ` ${s.name}` }));
    remove.addEventListener("click", async () => {
      d = await save(d.sources.filter((x) => x.id !== s.id));
      draw();
      announce(`${s.name} taken off the list. Nothing was changed there.`);
      (list.querySelector(".sortable__row button") || add).focus();
    });
    const move = (dir) => el("button", { type: "button", class: "btn btn--quiet btn--compact", "data-move": dir },
      icon(dir === "up" ? "arrow-up" : "arrow-down"), el("span", { class: "visually-hidden", text: `Move ${s.name} ${dir}` }));
    return el("li", { class: "sortable__row", "data-value": s.id },
      el("span", { class: "sortable__handle", "aria-hidden": "true" }, icon("grip-vertical")),
      el("span", { class: "sortable__label bring-source" }, el("span", { class: "bring-source__order", "aria-hidden": "true", text: String(i + 1) }),
        icon(SOURCE_ICONS[s.kind] || "folder"),
        el("span", { class: "bring-source__text" }, el("span", { class: "bring-source__name", text: s.name }),
          el("span", { class: "bring-source__meta", text: `${SOURCE_KIND_WORDS[s.kind]}, read only${i === 0 && d.sources.length > 1 ? ". Wins when a title is in two places" : ""}` }))),
      el("span", { class: "bring-source__actions" }, change, remove),
      el("span", { class: "sortable__moves" }, move("up"), move("down")));
  };
  const draw = () => {
    list.replaceChildren(...d.sources.map(row));
    list.hidden = !d.sources.length;
    empty.hidden = !!d.sources.length;
  };
  list.addEventListener("sortable-change", async (e) => {
    const order = e.detail.order;
    d = await save(order.map((id) => d.sources.find((s) => s.id === id)).filter(Boolean));
    [...list.children].forEach((li, i) => { li.querySelector(".bring-source__order").textContent = String(i + 1); });
  });
  // Adding: the folder picker on its places screen. A share asks for its address first; a cloud service signs in.
  const addFolder = async (path, place, replacing = null) => {
    const kind = place.startsWith("disk:") ? "disk" : place.startsWith("cloud:") ? place.slice(6) : place.startsWith("share:") ? null : "computer";
    let next;
    if (kind) next = replacing ? d.sources.map((x) => x.id === replacing.id ? { ...x, kind, path } : x) : [...d.sources, { kind, path }];
    else next = d.sources.map((x) => x.id === place.slice(6) ? { ...x, path } : x);
    try { d = await save(next); draw(); announce(`Added ${path || "the whole share"}`); }
    catch (e) { problem(e.message, add); }
  };
  const onPlace = (p) => {
    if (p.kind === "add-share") shareForm(add, async (share) => {
      try { d = await save([...d.sources, share]); draw(); const s = d.sources[d.sources.length - 1];
        folderBrowser("", add, (path, place) => addFolder(path, place), { purpose: "bring-in", place: `share:${s.id}` }); }
      catch (e) { problem(e.message, add); }
    });
    else if (p.kind === "cloud") cloudSignIn(p, add, () => folderBrowser("", add, (path, place) => addFolder(path, place), { purpose: "bring-in", place: p.id }));
  };
  const pickFor = (s, opener) => {
    if (s.kind === "smb" || s.kind === "nfs") folderBrowser(s.path || "/", opener, (path, place) => addFolder(path, place), { purpose: "bring-in", place: `share:${s.id}` });
    else if (s.kind === "onedrive" || s.kind === "gdrive") folderBrowser(s.path || "/", opener, (path, place) => addFolder(path, place, s), { purpose: "bring-in", place: `cloud:${s.kind}` });
    else folderBrowser(s.path, opener, (path, place) => addFolder(path, place, s), { purpose: "bring-in", onPlace });
  };
  const add = el("button", { type: "button", class: "btn", id: "bring-add", "aria-haspopup": "dialog" }, icon("plus"), "Add a source");
  add.addEventListener("click", () => folderBrowser("", add, (path, place) => addFolder(path, place), { purpose: "bring-in", onPlace }));
  const holder = el("div", { class: "stack-3" }, list, empty, status, el("div", { class: "actions" }, add));
  draw();
  window.SharedComponents?.setupSortables?.(holder);  // Move up, Move down and the handle, once for the list
  const nodes = [
    holder,
    el("p", { class: "small muted", text: "Starboard only reads these places: it copies from them and never renames, moves or deletes anything there. When the same title is in two places, the one higher in the list is brought in." }),
    el("p", { class: "help-links" },
      helpButton("What is a network share?", { body: [el("p", { text: "A folder another computer or a NAS shares on your network. Windows and most NAS boxes share with SMB; Linux often with NFS. Starboard connects to it read only, so nothing there can change." })], title: "What is a network share?" }),
      helpButton("Why does the order matter?", { body: [el("p", { text: "When the same film, episode, album or book is in two places, Starboard brings in the copy from the place higher in the list. It leaves the other where it is. Put the place with your best copies first." })], title: "Why does the order matter?" })),
  ];
  return { nodes, save: async () => {
    // In the set-up, Continue with nothing added skips the step, as Enter does in the terminal set-up.
    if (!d.sources.length && ctx.inWizard) return "skip";
    if (!d.sources.length) { problem("Add at least one source first", add); add.focus(); return false; }
    await save();
    return true;
  } };
}

// A network share: SMB or NFS, its address and, for SMB, a user name and password (kept by Starboard only).
function shareForm(opener, done) {
  const kind = el("select", { class: "input", id: "share-kind" }, el("option", { value: "smb", text: "SMB (Windows, most NAS boxes)" }), el("option", { value: "nfs", text: "NFS (Linux)" }));
  const address = el("input", { class: "input", id: "share-address", spellcheck: "false", autocomplete: "off", placeholder: "//192.0.2.20/media" });
  const user = el("input", { class: "input", id: "share-user", autocomplete: "off" });
  const pass = el("input", { class: "input", id: "share-pass", type: "password", autocomplete: "new-password" });
  const smbOnly = el("div", { class: "stack-3" }, field("User name", user, { hint: "Leave it empty for a share anyone can read." }),
    field("Password", pass, { hint: "Kept by Starboard only, never shown again." }));
  kind.addEventListener("change", () => { smbOnly.hidden = kind.value !== "smb"; address.placeholder = kind.value === "smb" ? "//192.0.2.20/media" : "192.0.2.20:/export/media"; });
  const go = el("button", { type: "button", class: "btn btn--primary", text: "Connect read only" });
  const cancel = el("button", { type: "button", class: "btn", text: "Cancel" });
  const panel = sidePanel({ title: "Add a network share", opener, body: [el("div", { class: "stack-4" },
    el("p", { class: "muted", text: "Starboard mounts the share read only, so nothing there can be changed." }),
    field("Kind of share", kind), field("Address", address, { hint: "Such as //192.0.2.20/media for SMB, or 192.0.2.20:/export/media for NFS.", required: true }), smbOnly)],
  foot: [go, cancel] });
  cancel.addEventListener("click", () => panel.close());
  go.addEventListener("click", () => {
    if (!address.value.trim()) { setError(address, "Enter the share's address"); address.focus(); return; }
    panel.close();
    done({ kind: kind.value, address: address.value.trim(), user: kind.value === "smb" ? user.value.trim() : "", password: kind.value === "smb" ? pass.value : "", path: "" });
  });
  address.focus();
}

// A cloud service: the cloud backup wizard's sign-in (DASH-452), asking only to read. OneDrive offers Complete on the
// phone when Starboard has its own sign-in at Microsoft, and Complete in this browser; Google Drive only Complete in this
// browser, as reading files already in a Drive needs drive.readonly, which Google's phone sign-in does not allow. Once
// signed in, the remote is kept for Bring in media only, and the picker opens in the service's folders.
function cloudSignIn(place, opener, then) {
  const ways = place.ways || ["browser"];
  const st = { way: ways[0], sess: null, timer: 0, closed: false };
  const body = el("div", { class: "stack-4" });
  const close = el("button", { type: "button", class: "btn", text: "Back to sources" });
  const panel = sidePanel({ title: `Sign in to ${place.name}`, opener, wide: true, body: [body], foot: [close],
    onClose: () => { st.closed = true; clearTimeout(st.timer); if (st.sess && st.sess.state !== "signed-in") api("/api/bring-in/cloud/cancel", { method: "POST" }).catch(() => {}); } });
  close.addEventListener("click", () => panel.close());
  const left = (s) => s == null ? "" : s < 60 ? "Less than a minute left" : `${Math.ceil(s / 60)} minutes left`;
  const waiting = (words) => el("div", { class: "signin-wait" }, el("div", { class: "signin-wait__words" },
    el("span", { role: "status", text: words }), el("span", { class: "muted", id: "bring-cloud-left", text: left(st.sess?.seconds_left) })),
  el("div", { class: "progress progress--busy", role: "progressbar", "aria-label": words.replace(/…$/, ""), "aria-valuetext": "Waiting" }, el("span")));
  const draw = (focusIt = false) => {
    const s = st.sess || { state: "none" };
    const parts = [el("p", { text: `Starboard asks ${place.name} only to read your files. It copies them down, brings them in, and never changes anything there. Starboard never receives your password.` })];
    if (ways.length > 1) {
      const cards = el("fieldset", { class: "option-cards option-cards--row" }, el("legend", { class: "field__label", text: "How do you want to sign in?" }),
        [["phone", "Complete on the phone", "Scan a QR code and sign in on your phone. Starboard waits by itself."],
          ["browser", "Complete in this browser", "Open the sign-in page here, then paste back the address it ends on."]].map(([v, title, line]) =>
          el("label", { class: "option-card" }, el("input", { type: "radio", name: "bring-cloud-way", value: v, checked: st.way === v }), el("strong", { text: title }), el("small", { text: line }))));
      cards.addEventListener("change", (e) => { st.way = e.target.value; begin(); });
      parts.push(cards);
    } else if (place.service === "gdrive") {
      parts.push(el("p", { class: "small muted", text: "Google only lets apps read your existing files when you sign in in a browser. So Starboard does not offer Complete on the phone for Google Drive." }));
    }
    if (s.state === "starting" || s.state === "checking") parts.push(waiting(s.state === "starting" ? "Getting the sign-in ready…" : `Checking the sign-in with ${place.name}…`));
    else if (s.state === "link") {
      const paste = el("input", { class: "input", id: "bring-cloud-answer", spellcheck: "false", autocomplete: "off", inputmode: "url" });
      const go = el("button", { type: "button", class: "btn btn--primary", text: "Continue" });
      const send = async () => {
        if (!paste.value.trim()) { problem("Paste the address from the browser's address bar", paste); return; }
        try { st.sess = await api("/api/bring-in/cloud/answer", { method: "POST", body: { id: st.sess.id, address: paste.value } }); draw(); follow(); }
        catch (e) { problem(e.message, paste); }
      };
      go.addEventListener("click", send);
      paste.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); send(); } });
      parts.push(el("div", { class: "signin-card" }, el("ol", { class: "signin-steps" },
        el("li", {}, el("p", { text: `Open ${place.name}'s sign-in page, sign in and allow Starboard to read your files.` }),
          el("p", {}, el("a", { class: "btn", href: s.link, target: "_blank", rel: "noopener noreferrer" }, icon("external-link"), "Open the sign-in page",
            el("span", { class: "visually-hidden", text: ` for ${place.name} (opens in a new tab)` })))),
        el("li", {}, el("p", { text: "Your browser then shows a page that does not load. That is expected: its address holds the answer. It starts like this:" }),
          el("code", { class: "signin-example", text: "http://127.0.0.1:53682/?state=…&code=…" })),
        el("li", {}, el("div", { class: "field" }, el("label", { for: "bring-cloud-answer", text: "Paste that whole address" }), paste), el("div", { class: "actions" }, go)))));
    } else if (s.state === "phone" && typeof qrSvg === "function") {
      const page = s.page.replace(/^https:\/\//, "");
      parts.push(el("div", { class: "signin-card" }, el("div", { class: "qr-card" }, el("figure", { class: "qr-card__code" }, qrSvg(s.qr, `QR code for ${page}`)),
        el("div", { class: "qr-card__text" }, el("p", { text: "Scan the QR code with your phone's camera, or open this page on any device:" }),
          el("p", {}, el("span", { class: "address" }, el("a", { href: s.page, target: "_blank", rel: "noopener noreferrer" }, page, el("span", { class: "visually-hidden", text: " (opens in a new tab)" })), copyButton(s.page, "the address"))),
          el("p", { text: `Enter this code there, then sign in and allow Starboard to read your files in ${place.name}:` }),
          el("p", { class: "device-code" }, el("span", { class: "device-code__value", "aria-label": spelt(s.user_code), text: s.user_code }), labelledCopy(s.user_code, "the code", "Code copied")))),
      waiting("Waiting for you to sign in on your phone…")));
    } else if (s.state === "failed" || s.state === "expired") {
      const again = el("button", { type: "button", class: "btn", text: "Try again" });
      again.addEventListener("click", begin);
      parts.push(el("div", { class: "notice", "data-tone": "danger", role: "alert" }, icon("circle-alert"), el("div", { class: "notice__body" },
        el("span", { class: "notice__title", tabindex: "-1", id: "bring-cloud-error", text: "Not signed in" }), el("p", { text: s.error || "The sign-in did not finish." }), el("div", { class: "actions" }, again))));
    }
    body.replaceChildren(...parts);
    if (focusIt) (body.querySelector("#bring-cloud-error") || body.querySelector("a.btn, input:not([type=radio])") || body.querySelector("input"))?.focus();
  };
  const follow = () => {
    clearTimeout(st.timer);
    if (st.closed || !st.sess || !["starting", "link", "checking", "phone"].includes(st.sess.state)) return;
    st.timer = setTimeout(async () => {
      const was = st.sess.state;
      try { st.sess = await api("/api/bring-in/cloud/session"); } catch { /* ask again */ }
      if (st.closed) return;
      if (st.sess.state === "signed-in") {
        try { await api("/api/bring-in/cloud/keep", { method: "POST", body: { service: place.service, id: st.sess.id } }); }
        catch (e) { st.sess = { state: "failed", error: e.message }; draw(true); return; }
        announce(`Signed in to ${place.name}, read only`);
        st.closed = true;
        panel.close();
        then?.();
        return;
      }
      if (st.sess.state !== was) draw(true); else { const n = body.querySelector("#bring-cloud-left"); if (n) n.textContent = left(st.sess.seconds_left); }
      follow();
    }, st.sess.state === "phone" ? 2000 : 1500);
  };
  const begin = async () => {
    st.sess = { state: "starting" };
    draw();
    try { st.sess = await api("/api/bring-in/cloud/start", { method: "POST", body: { service: place.service, way: st.way } }); }
    catch (e) { st.sess = { state: "failed", error: e.message }; }
    if (st.closed) return;
    draw(true);
    follow();
  };
  begin();
}

// 2. What is in each -----------------------------------------------------------------------------------------------------
async function bringWhat(ctx) {
  const d = await api("/api/bring-in");
  const said = el("p", { class: "small muted", role: "status" });
  const box = el("div", { class: "stack-5" });
  const nodes = [said, box, el("p", { class: "help-links" },
    helpButton("How does Starboard know?", { body: [el("p", { text: "By the kind of each file (a video, music, a book) and the shape of the folders. Season folders and S01E01 in names are series. An author's folder of audio files is an audiobook, and so on. Subtitles, artwork and .nfo files travel with their film or episode. System files and leftovers such as thumbs.db, .txt and .url files stay where they are." })], title: "How does Starboard know?" }))];
  const fixSelect = (s, folder, current, label) => {
    const sel = el("select", { class: "input", "aria-label": label },
      el("option", { value: "", text: folder ? "As found" : "As found, folder by folder" }),
      ...BRING_KINDS.map((k) => el("option", { value: k, text: `All ${BRING_WORDS[k].toLowerCase()}` })),
      el("option", { value: "leave", text: "Leave it where it is" }));
    sel.value = current || "";
    sel.addEventListener("change", async () => {
      try { s.look = await api("/api/bring-in/fix", { method: "PUT", body: { source: s.id, folder, kind: sel.value } }); drawOne(s); announce(`${label}: ${sel.selectedOptions[0].text}`); }
      catch (e) { problem(e.message, sel); }
    });
    return sel;
  };
  const cards = {};
  const drawOne = (s) => {
    const l = s.look;
    const card = cards[s.id];
    if (!l) return;
    const found = BRING_KINDS.filter((k) => l.found[k]);
    const rows = found.map((k) => el("tr", {}, el("th", { scope: "row", text: BRING_WORDS[k] }), el("td", { text: bringCount(k, l.found[k].titles) }), el("td", { text: formatBytes(l.found[k].size) })));
    if (l.other.files) rows.push(el("tr", { class: "muted" }, el("th", { scope: "row", text: "Other files" }), el("td", { text: `${l.other.files.toLocaleString("en-GB")} left where they are` }), el("td", { text: formatBytes(l.other.size) })));
    const folderRows = (l.folders || []).slice(0, 60).map((f) => el("tr", {},
      el("th", { scope: "row", class: "bring-folder" }, icon("folder"), el("span", { text: f.path })),
      el("td", { text: formatBytes(f.size) }),
      el("td", { text: Object.entries(f.kinds).map(([k, n]) => bringCount(k, n)).join(", ") || "No media" }),
      el("td", {}, fixSelect(s, f.path, f.fix, `What is in ${f.path}`))));
    card.replaceChildren(
      el("div", { class: "title-chip" }, el("h3", { text: s.name }), chip("Read only", "neutral", "lock")),
      found.length || l.other.files ? el("div", { class: "table-wrap", "data-stack": "" }, el("table", { class: "table table--middle" },
        el("caption", { class: "visually-hidden", text: `What Starboard found in ${s.name}` }),
        el("thead", {}, el("tr", {}, el("th", { scope: "col", text: "Kind" }), el("th", { scope: "col", text: "Found" }), el("th", { scope: "col", text: "Size" }))),
        el("tbody", {}, rows))) : emptyState("No media found here", "Choose another folder in the sources, or change Everything in it is."),
      el("div", { class: "field bring-whole" }, el("label", { for: `whole-${s.id}`, text: "Everything in it is" }),
        Object.assign(fixSelect(s, "", l.fix, `Everything in it is, for ${s.name}`), { id: `whole-${s.id}` })),
      folderRows.length ? el("details", { class: "fold", open: (l.folders || []).length <= 8 ? true : null },
        el("summary", {}, `Folders in it (${(l.folders || []).length})`),
        el("div", { class: "table-wrap", "data-stack": "" }, el("table", { class: "table table--middle bring-folders" },
          el("caption", { class: "visually-hidden", text: `Folders in ${s.name}` }),
          el("thead", {}, el("tr", {}, el("th", { scope: "col", text: "Folder" }), el("th", { scope: "col", text: "Size" }), el("th", { scope: "col", text: "What is in it" }), el("th", { scope: "col", text: "Change" }))),
          el("tbody", {}, folderRows)))) : null);
  };
  // Linking (owner, 16 November 2026): only for films and series in a folder on the same disk as the media folder,
  // off to start with, offered once a look has found some.
  const linkBox = el("div", { hidden: true });
  const showLinks = async () => {
    let now;
    try { now = await api("/api/bring-in"); } catch { return; }
    if (!now.link_offered && !now.hardlinks) { linkBox.hidden = true; return; }
    const links = el("input", { type: "checkbox", id: "bring-links", checked: now.hardlinks });
    links.addEventListener("change", async () => {
      try { await api("/api/bring-in/sources", { method: "PUT", body: { sources: now.sources, hardlinks: links.checked } }); announce(links.checked ? "Films and series on the same disk will be linked" : "Everything will be copied"); }
      catch (e) { problem(e.message, links); }
    });
    linkBox.replaceChildren(el("div", { class: "check bring-links" }, links, el("label", { for: "bring-links", class: "check__text" },
      el("strong", { text: "Link films and series on the same disk instead of copying them" }),
      el("span", { class: "check__hint", text: "Uses no extra space. The library file is then the same file as the original, so anything that changes it changes the original too. Music, books and audiobooks are always copied. If a link cannot be made (a pool's disks underneath can differ), the file is copied instead and the report says so." }))));
    linkBox.hidden = false;
  };
  nodes.splice(2, 0, linkBox);
  for (const s of d.sources) {
    cards[s.id] = el("section", { class: "card bring-what stack-3", "aria-label": s.name });
    box.append(cards[s.id]);
  }
  const lookAll = async () => {
    let n = 0;
    for (const s of d.sources) {
      n += 1;
      if (s.look) { drawOne(s); continue; }
      said.textContent = `Reading ${n} of ${d.sources.length}: ${s.name}…`;
      cards[s.id].replaceChildren(el("h3", { text: s.name }), el("p", { class: "muted", text: "Reading…" }));
      try { s.look = await api("/api/bring-in/look", { method: "POST", body: { source: s.id } }); drawOne(s); }
      catch (e) { cards[s.id].replaceChildren(el("h3", { text: s.name }), notice("danger", "Could not read", e.message)); }
    }
    said.textContent = `Read ${d.sources.length} ${d.sources.length === 1 ? "source" : "sources"}.`;
    showLinks();
  };
  lookAll();
  return { nodes, save: async () => true };
}

// 3. Check names ---------------------------------------------------------------------------------------------------------
async function bringNames(ctx) {
  const said = el("p", { class: "muted", role: "status", text: "Checking each name…" });
  const space = el("div", { class: "stack-2 bring-space" });
  const listBox = el("div", { class: "stack-3" });
  const filterBox = el("div");
  const top = el("div", { class: "stack-2" });
  let state = "matched", page = null;
  const words = { matched: "Matched", look: "Needs attention", left: "Left where it is" };
  const showSpace = (sp) => {
    if (!sp) return;
    const pct = sp.free ? Math.min(100, Math.round(((sp.needed + sp.margin) / sp.free) * 100)) : 0;
    space.replaceChildren(
      el("p", { text: `${formatBytes(sp.needed)} to copy${sp.linked ? `, ${formatBytes(sp.linked)} linked (no space)` : ""}; ${sp.free != null ? `${formatBytes(sp.free)} free on the media disk` : "free space not known yet"}.` }),
      sp.free != null ? el("div", { class: "meter" }, el("div", { class: "meter__label" }, el("span", { text: "Space the copy needs" }), el("span", { text: `${pct}% of what is free` })),
        el("div", { class: "progress", "data-tone": sp.enough ? (pct > 80 ? "warning" : null) : "danger", "aria-hidden": "true" }, (() => { const s = el("span"); s.style.width = `${pct}%`; return s; })())) : null,
      sp.enough ? el("p", { class: "small muted", text: "Starboard always keeps 10 GB free." }) :
        notice("danger", "Not enough space", "Leave some titles or a source out, or free some space on the media disk, then check names again."));
  };
  const row = (r) => {
    const head = el("div", { class: "row__title" }, el("span", { text: r.title + (r.year ? ` (${r.year})` : "") }), r.kind ? el("span", { class: "small muted", text: ` · ${BRING_WORDS[r.kind]}` }) : null);
    const lines = [el("div", { class: "row__meta bring-name__from" }, el("span", { class: "visually-hidden", text: "From " }), icon("file-text"), el("span", { text: r.from }))];
    if (r.to) lines.push(el("div", { class: "row__meta bring-name__to" }, el("span", { class: "visually-hidden", text: "To " }), icon("chevron-right"), el("span", { text: r.first || r.to })));
    if (r.why) lines.push(el("div", { class: "row__meta", text: r.why }));
    const li = el("li", { class: "row row--no-lead bring-name", "data-key": r.key }, el("div", {}, head, ...lines),
      el("div", { class: "row__side small muted", text: `${r.files > 1 ? `${r.files} files, ` : ""}${formatBytes(r.size)}` }));
    if (r.state === "look") {
      const name = `choice-${r.key.replace(/[^\w-]/g, "-")}`;
      const opts = [...(r.choices || []).map((c) => el("label", { class: "check" }, el("input", { type: "radio", name, value: String(c.tmdb_id) }),
        el("span", { class: "check__text", text: `${c.title}${c.year ? ` (${c.year})` : ""}${c.in_library ? ", already in your library" : ""}` }))),
        ...(!r.choices?.length && r.kind && !["films", "series"].includes(r.kind) ? [el("label", { class: "check" }, el("input", { type: "radio", name, value: "as-is" }), el("span", { class: "check__text", text: `Bring it in as ${r.to}` }))] : []),
        el("label", { class: "check" }, el("input", { type: "radio", name, value: "leave" }), el("span", { class: "check__text", text: "Leave it where it is" }))];
      const ok = el("button", { type: "button", class: "btn btn--compact" }, "Save", el("span", { class: "visually-hidden", text: ` the choice for ${r.title}` }));
      ok.addEventListener("click", async () => {
        const v = li.querySelector(`input[name="${name}"]:checked`)?.value;
        if (!v) { problem("Choose a match, or leave it where it is", ok); return; }
        try {
          await api("/api/bring-in/choose", { method: "PUT", body: v === "leave" ? { key: r.key, leave: true } : v === "as-is" ? { key: r.key, title: r.title } : { key: r.key, tmdb_id: v } });
          const next = li.nextElementSibling || li.previousElementSibling;
          li.remove();
          await load(state, 0, false);
          announce(`${r.title}: ${v === "leave" ? "left where it is" : "matched"}`);
          (listBox.querySelector(".bring-name button, .bring-name input") || filterBox.querySelector("input:checked"))?.focus();
          void next;
        } catch (e) { problem(e.message, ok); }
      });
      li.append(el("fieldset", { class: "bring-choices" }, el("legend", { class: "small", text: "Which is it?" }), ...opts, el("div", {}, ok)));
    }
    return li;
  };
  const load = async (st, start = 0, append = false) => {
    state = st;
    page = await api(`/api/bring-in/plan?state=${encodeURIComponent(st)}&start=${start}`);
    filterBox.replaceChildren(segmentedFilter({ name: "bring-state", label: "Show", value: state,
      options: Object.keys(words).map((k) => [k, words[k], page.counts[k] || 0]), onChange: (v) => load(v) }));
    showSpace(page.space);
    const ul = append ? listBox.querySelector("ul.rows") : el("ul", { class: "rows" });
    page.items.forEach((r) => ul.append(row(r)));
    const more = page.start + page.items.length < page.total ? el("button", { type: "button", class: "btn", text: `Show ${Math.min(50, page.total - page.start - page.items.length)} more` }) : null;
    more?.addEventListener("click", () => { const first = page.items.length; load(state, page.start + 50, true).then(() => ul.children[page.start]?.querySelector("button, input")?.focus?.()); void first; });
    if (!append) listBox.replaceChildren(page.items.length ? ul : emptyState(`Nothing ${state === "look" ? "needs attention" : state === "left" ? "is left where it is" : "matched yet"}`, ""), ...(more ? [more] : []));
    else { listBox.querySelector(":scope > button")?.remove(); if (more) listBox.append(more); }
  };
  const nodes = [top, space, filterBox, listBox, el("p", { class: "help-links" },
    helpButton("Where does each file go?", { body: [el("p", { text: "Films go in Films as Title (Year). Series go in Series as Title (Year), Season 01, Title - S01E01. Music goes by artist and album. Books and audiobooks go by author and title. These are the names Reelix and Jellyfin match best. Once copied, Reelix adds each one and gives every file Reelix's own name." })], title: "Where does each file go?" }),
    helpButton("Why are some left where they are?", { body: [el("p", { text: "Samples, extras and files that are not media stay where they are. So do titles already in your library and second copies of a title (the source higher in the list wins). Exact copies of the same file are brought in once." })], title: "Why are some left where they are?" }))];
  (async () => {
    try {
      await api("/api/bring-in/check", { method: "POST" });
      await load("matched");
      const counts = page.counts;
      said.textContent = `${counts.matched} matched, ${counts.look} need attention, ${counts.left} left where they are.`;
      if (!page.checked) top.append(notice("info", "Reelix checks every name before copying", "Reelix is not running yet, so these names are read from the files. Once the apps start, Reelix checks each one before anything is copied, and holds back any it does not agree with."));
    } catch (e) { said.replaceChildren(); top.replaceChildren(notice("danger", "Could not check names", e.message)); }
  })();
  return { nodes: [said, ...nodes], save: async () => {
    if (page?.space && !page.space.enough) { problem("There is not enough space for everything. Leave some titles or a source out first", filterBox); return false; }
    return true;
  } };
}

// 4. Copy ------------------------------------------------------------------------------------------------------------
async function bringCopy(ctx) {
  const d = await api("/api/bring-in");
  const box = el("div", { class: "stack-4" });
  if (d.job && d.job.state && d.job.state !== "none") {
    bringProgress(box, d.job, ctx);
    return { nodes: [box], save: async () => true, hideContinue: !ctx.inWizard };
  }
  let page;
  try { page = await api("/api/bring-in/plan?state=matched"); } catch (e) { return { nodes: [notice("danger", "Check names first", e.message)], save: async () => false }; }
  const c = page.counts, sp = page.space;
  const change = (part, what) => el("button", { type: "button", class: "btn btn--quiet btn--compact", onclick: () => ctx.go?.(part) }, "Change", el("span", { class: "visually-hidden", text: ` ${what}` }));
  const rows = [
    ["Sources, in order", el("ol", { class: "plain-list" }, d.sources.map((s) => el("li", { text: s.name }))), "bring-sources", "the sources"],
    ["To copy", `${c.matched} ${c.matched === 1 ? "title" : "titles"}, ${formatBytes(sp.needed + sp.linked)}`, "bring-names", "what is copied"],
    ["Space", `${formatBytes(sp.needed)} needed, ${sp.free != null ? `${formatBytes(sp.free)} free` : "free space checked when it starts"}`, "bring-names", "the space"],
    ["Linking films and series", d.hardlinks ? "Active, on the same disk" : "Inactive: everything is copied", "bring-sources", "linking"],
    ["Needs attention", c.look ? `${c.look}: left where they are until you choose` : "None", "bring-names", "the titles that need attention"],
    ["Left where it is", `${c.left}`, "bring-names", "what is left where it is"],
  ];
  box.append(el("div", { class: "table-wrap", "data-stack": "" }, el("table", { class: "table table--fixed table--middle" },
    el("caption", { class: "visually-hidden", text: "Check before copying" }),
    el("thead", {}, el("tr", {}, el("th", { scope: "col", text: "What" }), el("th", { scope: "col", text: "Your answer" }), el("th", { scope: "col" }, el("span", { class: "visually-hidden", text: "Change" })))),
    el("tbody", {}, rows.map(([what, answer, part, words]) => el("tr", {}, el("th", { scope: "row", text: what }), el("td", {}, answer), el("td", {}, change(part, words))))))),
  el("p", { class: "muted", text: ctx.inWizard
    ? "The copy starts once the apps are running. It runs in the background at low priority, so the server stays quick, and you can pause it. Progress is on the dashboard and in Activity."
    : "It runs in the background at low priority, so the server stays quick. You can pause it, and it carries on after a restart. Progress is on the dashboard and in Activity." }));
  return { nodes: [box], continueText: ctx.inWizard ? "Continue" : "Start copying", save: async () => {
    const job = await api("/api/bring-in/start", { method: "POST" });
    if (!ctx.inWizard) { box.replaceChildren(); bringProgress(box, job, ctx); }
    return true;
  } };
}

// The copy's progress (WIZARD.md, A job's progress): one bar, updated in place, the words beside it, and Pause or
// Carry on. A stop says why below the bar. At the end, the report.
function bringProgress(box, job, ctx = {}) {
  const words = el("p", { class: "wizard-job__words" });
  const count = el("span", { class: "wizard-job__count" });
  const bar = el("div", { class: "progress", role: "progressbar", "aria-valuemin": "0", "aria-valuemax": "100", "aria-label": "Bringing in your media" }, el("span"));
  const problemBox = el("div", { id: "bring-problem" });
  const pause = el("button", { type: "button", class: "btn", text: "Pause" });
  const carry = el("button", { type: "button", class: "btn btn--primary", text: "Carry on" });
  const actions = el("div", { class: "actions" }, pause, carry);
  const live = el("p", { class: "visually-hidden", "aria-live": "polite" });
  let timer = 0, lastPhase = "";
  const draw = (j) => {
    if (!box.isConnected && timer) { clearInterval(timer); return; }
    if (j.state === "done") { clearInterval(timer); bringReport(box, ctx); return; }
    const pct = j.bytes_total ? Math.round((j.bytes_done / j.bytes_total) * 100) : 0;
    const phase = PHASE_WORDS[j.phase] || "Copying";
    words.replaceChildren(el("strong", { text: j.state === "paused" ? "Paused" : j.state === "stopped" ? "Stopped" : phase }),
      j.state === "running" ? el("span", { class: "muted", text: " · Copying…" }) : null,
      j.current ? el("span", { class: "muted", text: ` · ${j.current}` }) : null);
    const text = `${(j.files_done || 0).toLocaleString("en-GB")} of ${(j.files_total || 0).toLocaleString("en-GB")} files · ${formatBytes(j.bytes_done || 0)} of ${formatBytes(j.bytes_total || 0)}`;
    count.textContent = text;
    bar.setAttribute("aria-valuenow", String(pct));
    bar.setAttribute("aria-valuetext", `${phase}: ${text}`);
    bar.firstChild.style.width = `${pct}%`;
    if (j.state === "stopped") bar.dataset.tone = "danger"; else if (j.state === "paused") bar.dataset.tone = "warning"; else delete bar.dataset.tone;
    pause.hidden = !["running", "waiting"].includes(j.state);
    carry.hidden = !["paused", "stopped"].includes(j.state);
    if (j.state === "stopped" && j.error) {
      problemBox.replaceChildren(notice("danger", "The copy did not finish", j.error));
      bar.setAttribute("aria-describedby", "bring-problem");
    } else { problemBox.replaceChildren(); bar.removeAttribute("aria-describedby"); }
    if (lastPhase !== `${j.state}:${j.phase}`) { live.textContent = `${j.state === "paused" ? "Paused" : phase}. ${text}`; lastPhase = `${j.state}:${j.phase}`; }
  };
  pause.addEventListener("click", async () => { try { draw(await api("/api/bring-in/pause", { method: "POST" })); carry.focus(); } catch (e) { problem(e.message, pause); } });
  carry.addEventListener("click", async () => { try { draw(await api("/api/bring-in/carry-on", { method: "POST" })); pause.focus(); } catch (e) { problem(e.message, carry); } });
  box.replaceChildren(el("div", { class: "wizard-job stack-2" }, el("div", { class: "wizard-job__head" }, words, count), bar), problemBox, actions, live);
  draw(job);
  timer = setInterval(async () => { if (document.hidden) return; try { draw(await api("/api/bring-in/status")); } catch { /* the next look */ } }, 4000);
}

// The end report: copied, needs a look, left where it is, each with what to do.
async function bringReport(box, ctx = {}) {
  let r;
  try { r = await api("/api/bring-in/report?part=copied"); } catch (e) { box.replaceChildren(notice("danger", "Could not show the report", e.message)); return; }
  const c = r.counts;
  const part = (key, title, todo, tone) => {
    const list = el("ul", { class: "rows" });
    const more = el("button", { type: "button", class: "btn", text: "Show more" });
    let start = 0;
    const fill = async () => {
      const got = await api(`/api/bring-in/report?part=${key}&start=${start}`);
      got.items.forEach((x) => list.append(el("li", { class: "row row--no-lead" }, el("div", {},
        el("div", { class: "row__title", text: x.title }),
        el("div", { class: "row__meta", text: [x.to ? `In ${x.to}` : "", x.from ? `From ${x.from}` : "", x.linked ? "linked, no space used" : "", x.why || x.note || ""].filter(Boolean).join(" · ") })))));
      start += got.items.length;
      more.hidden = start >= got.total;
    };
    more.addEventListener("click", fill);
    const n = c[key];
    const h = el("h3", { id: `bring-report-${key}` }, `${title} (${n.toLocaleString("en-GB")})`);
    const sec = el("section", { class: "stack-2 bring-report__part", "aria-labelledby": h.id, "data-tone": tone }, h, el("p", { class: "small muted", text: todo }), list, more);
    if (n) fill(); else { more.hidden = true; list.replaceWith(el("p", { class: "muted", text: "None." })); }
    return sec;
  };
  const got = el("button", { type: "button", class: "btn btn--primary", text: "Got it" });
  got.addEventListener("click", async () => { try { await api("/api/bring-in/finish", { method: "POST" }); ctx.onFinish ? ctx.onFinish() : location.reload(); } catch (e) { problem(e.message, got); } });
  const head = el("h3", { tabindex: "-1", text: "Your media is in" });
  box.replaceChildren(head,
    notice("success", `${c.copied} ${c.copied === 1 ? "title" : "titles"} brought in`, "Nothing was changed, moved or deleted at your sources. Reelix has added them and named every file its own way; Jellyfin shows them once it scans."),
    part("copied", "Copied", "In your library now. Nothing to do.", "success"),
    part("look", "Needs attention", "Not copied yet. Select Got it, then Bring in media again: these wait in Check names, under Needs attention.", "warning"),
    part("left", "Left where it is", "Not copied, with why. Nothing to do unless one of these should be in your library.", null),
    r.holding ? el("p", { class: "small muted", text: `The files copied down from cloud services are in ${r.holding}, in case you want them. Remove them when you are sure.` }) : null,
    ctx.inWizard ? null : el("div", { class: "actions" }, got));
  head.focus();
}

// The page of its own (bring-in.html): the four parts with their own step list, or the copy when one is running.
async function startBringIn() {
  const root = $("#bring-in");
  root.removeAttribute("aria-busy");
  const T = await stepTable();
  const steps = bringInSteps(T).map((s) => ({ ...s, group: null, skippable: false }));
  let d = { job: { state: "none" } };
  try { d = await api("/api/bring-in"); } catch { /* drawn below */ }
  const go = async (id) => {
    const index = Math.max(0, steps.findIndex((s) => s.id === id));
    const step = steps[index];
    step.nodes = [SharedComponents.wait("Loading this step")];
    let save = async () => true, cont = "Continue";
    const frame = (busy) => wizardFrame({ root, steps, index, busy, continueText: cont,
      onBack: () => go(steps[index - 1].id), onSkip: () => {},
      onContinue: async (e) => {
        const b = e.currentTarget;
        b.disabled = true;
        try { if (await save() && index < steps.length - 1) go(steps[index + 1].id); else if (index === steps.length - 1) go(step.id); }
        catch (err) { problem(err.message); }
        finally { if (b.isConnected) b.disabled = false; }
      } });
    frame(true);
    const content = await bringInStep(step.id, { inWizard: false, go });
    step.nodes = content.nodes;
    save = content.save;
    cont = content.continueText || (index === steps.length - 1 ? "Start copying" : "Continue");
    const f = frame(false);
    if (content.hideContinue) f.cont.hidden = true;  // the copy has its own Pause, Carry on and Got it
    f.heading.focus();
  };
  go(d.job?.state && d.job.state !== "none" ? "bring-copy" : (new URLSearchParams(location.search).get("part") || "bring-sources"));
}
