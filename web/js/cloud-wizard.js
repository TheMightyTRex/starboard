// Connect a cloud service (DASH-452, TheMightyTRexUK, 16 November 2026): a wizard in a slide-out, opened from Copies off
// this computer. Five steps: choose a service, sign in, choose the folder, test, save. The services and their fields come
// from /cloud-services.json through the server (one list for both). Rules: design system WIZARD.md, section 9, Signing
// in to an outside service. Nothing is saved until the last step; closing part way ends the sign-in on the server (its
// helper container goes) and focus goes back to the button that opened it.

const CLOUD_STEPS = [["service", "Choose a service"], ["signin", "Sign in"], ["folder", "Choose the folder"], ["test", "Test the connection"], ["save", "Save"]];

function minutesLeft(seconds) {
  if (seconds == null) return "";
  const m = Math.ceil(seconds / 60);
  return seconds < 60 ? "Less than a minute left" : `${m} ${m === 1 ? "minute" : "minutes"} left`;
}

// Each new step: focus on its heading, with the panel at its top so the progress bar above the heading stays in view.
function focusStep(h) {
  h.focus({ preventScroll: true });
  const body = h.closest(".side-panel__body");
  if (body) body.scrollTop = 0;
}

function spelt(code) { return `Code: ${String(code).replace(/-/g, "").split("").join(", ")}`; }

function qrSvg(qr, label) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `0 0 ${qr.size} ${qr.size}`);
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", label);
  svg.setAttribute("shape-rendering", "crispEdges");
  const path = document.createElementNS(ns, "path");
  path.setAttribute("d", qr.path);  // made by the server's QR encoder: only M, h, v and z with numbers
  svg.append(path);
  return svg;
}

function labelledCopy(text, what, copied) {
  const b = el("button", { type: "button", class: "btn copy-btn--label" }, icon("copy"), "Copy", el("span", { class: "visually-hidden", text: ` ${what}` }));
  b.addEventListener("click", async () => { const ok = await copyText(text); (ok ? toast : problem)(ok ? copied : `Could not copy. It is ${text}`); });
  return b;
}

function testChecks(test, running) {
  const steps = test?.steps || [["folder", "Reach the folder"], ["write", "Write a small test file"], ["read", "Read it back"], ["remove", "Remove it"]].map(([id, label]) => ({ id, label, done: false }));
  let failedShown = false;
  return el("ul", { class: "test-checks", "aria-label": "The test" }, steps.map((s) => {
    let state = s.done ? "done" : "waiting";
    if (!s.done && test && !test.ok && !failedShown && !running) { state = "failed"; failedShown = true; }
    const words = { done: "Done", failed: "Did not work", waiting: running ? "Waiting" : "Not tried" }[state];
    return el("li", { "data-state": state }, icon({ done: "circle-check", failed: "circle-alert", waiting: "circle" }[state], 20),
      el("span", { text: s.label }), el("span", { class: "test-checks__state", text: words }));
  }));
}

// The result of a test in words, the sign-in problem told apart ("SIGNIN|...": the page offers Sign in again).
function testWords(error) {
  const text = String(error || "");
  return { signin: text.startsWith("SIGNIN|"), text: text.replace(/^SIGNIN\|/, "") };
}

async function cloudWizard({ opener = document.activeElement, startAt = "service", serviceId = null, folder = "", dest = null, onSaved } = {}) {
  let list;
  try { list = await api("/api/backup/cloud/services"); } catch (e) { problem(e.message, opener); return; }
  const services = list.services;
  const st = { service: services.find((s) => s.id === serviceId) || null, way: list.last_way === "phone" ? "phone" : "browser", sess: null,
    folder: folder || "starboard-backups", folders: null, folderChoice: folder ? "existing" : "new", saved: false, closed: false, timer: 0, at: 0, last: "" };
  const panel = sidePanel({ title: "Connect a cloud service", opener, wide: true, body: [], onClose: () => {
    st.closed = true;
    clearTimeout(st.timer);
    if (!st.saved && st.sess) { api("/api/backup/cloud/cancel", { method: "POST" }).catch(() => {}); announce("Closed: nothing was saved"); }
  } });
  panel.layer.dataset.wizard = "cloud";

  const svc = () => st.service;
  const phoneOffered = () => !!(svc()?.signin === "oauth" && svc()?.phone);

  function frame(index, heading, parts, foot) {
    const [, name] = CLOUD_STEPS[index];
    const left = CLOUD_STEPS.length - index - 1;
    const h = el("h3", { tabindex: "-1", id: "cloud-step-heading", text: heading });
    const progress = el("div", { class: "wizard-progress meter" },
      el("div", { class: "meter__label" }, el("span", { text: `Connect a cloud service · step ${index + 1} of ${CLOUD_STEPS.length} · ${name}` }),
        el("span", { class: "numeric", text: left ? `${left} to go` : "Last step" })),
      el("div", { class: "progress", role: "progressbar", "aria-label": "Connect a cloud service", "aria-valuemin": "1", "aria-valuemax": String(CLOUD_STEPS.length),
        "aria-valuenow": String(index + 1), "aria-valuetext": `Step ${index + 1} of ${CLOUD_STEPS.length}: ${name}` },
        el("span")));
    progress.querySelector(".progress > span").style.width = `${Math.round(((index + 1) / CLOUD_STEPS.length) * 100)}%`;  // the policy blocks style attributes
    // The help opens in a new tab: a second slide-out would close this one (and end the sign-in).
    const help = el("div", { class: "help-links" }, helpCentreLink("topics/copy-backups-to-a-cloud-service.md", "Help with this step"));
    panel.body.replaceChildren(el("div", { class: "wizard stack-4", "data-step": CLOUD_STEPS[index][0] }, progress, h, ...parts.filter(Boolean), help));
    panel.setFoot(foot.filter(Boolean));
    return h;
  }
  function backButton(to) {
    const b = el("button", { type: "button", class: "btn", text: "Back" });
    b.addEventListener("click", to);
    return b;
  }
  function errorNotice(text, actions = []) {
    return el("div", { class: "notice", "data-tone": "danger", role: "alert", id: "cloud-error", tabindex: "-1" }, icon("circle-alert"),
      el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: "That did not work" }), el("p", { text })), ...actions);
  }
  function fieldError(input, text) {
    const id = `${input.id}-error`;
    let node = document.getElementById(id);
    if (!node) {
      node = el("span", { class: "field-error", id }, icon("circle-alert"), el("span"));
      input.after(node);
    }
    node.lastChild.textContent = text || "";
    node.hidden = !text;
    input.setAttribute("aria-invalid", text ? "true" : "false");
    const describedBy = new Set((input.getAttribute("aria-describedby") || "").split(" ").filter(Boolean));
    if (text) describedBy.add(id); else describedBy.delete(id);
    input.setAttribute("aria-describedby", [...describedBy].join(" "));
    if (text) input.focus();
  }

  // Step 1: choose a service -------------------------------------------------------------------------------------
  function stepService() {
    st.at = 0;
    const cards = el("fieldset", { class: "option-cards option-cards--row", id: "cloud-services" }, el("legend", { class: "visually-hidden", text: "Cloud service" }),
      services.map((s) => el("label", { class: "option-card" },
        el("input", { type: "radio", name: "cloud-service", value: s.id, checked: s.id === svc()?.id }),
        el("strong", { text: s.name }), el("small", { text: s.line }))));
    const err = el("p", { class: "field-error", id: "cloud-service-error", hidden: true }, icon("circle-alert"), el("span", { text: "Choose a service" }));
    const go = el("button", { type: "button", class: "btn btn--primary", text: "Continue" });
    go.addEventListener("click", () => {
      const v = cards.querySelector("input:checked")?.value;
      if (!v) { err.hidden = false; cards.querySelector("input")?.focus(); return; }
      const changed = st.service?.id !== v;
      st.service = services.find((s) => s.id === v);
      if (changed) { st.sess = null; st.folders = null; st.test = null; }
      stepSignin();
    });
    const h = frame(0, "Where should the copies go?", [
      el("p", { text: "Starboard copies each new full backup there and keeps the newest few. The backups are encrypted with your backup password before they leave this computer." }),
      cards, err], [go]);
    focusStep(h);
  }

  // Step 2: sign in -------------------------------------------------------------------------------------------------
  async function startSignin() {
    clearTimeout(st.timer);
    st.sess = { state: "starting" };
    st.last = "";
    drawSignin();
    try {
      st.sess = await api("/api/backup/cloud/start", { method: "POST", body: { service: svc().id, way: st.way, dest } });
    } catch (e) {
      st.sess = { state: "failed", error: e.message };
    }
    if (st.closed) return;
    drawSignin(true);
    follow();
  }
  function follow() {
    clearTimeout(st.timer);
    if (st.closed || !st.sess || !["starting", "link", "checking", "phone"].includes(st.sess.state)) return;
    st.timer = setTimeout(async () => {
      try { st.sess = await api("/api/backup/cloud/session"); } catch { /* ask again */ }
      if (st.closed) return;
      if (st.sess.state === "signed-in") {
        announce(st.way === "phone" && svc().signin === "oauth" ? `Approved on your phone. Signed in to ${svc().name}` : `Signed in to ${svc().name}`);
        stepFolder();
        return;
      }
      drawSignin(st.sess.state !== st.last);
      follow();
    }, st.sess.state === "phone" ? 2000 : 1500);
  }

  function drawSignin(changed = true) {
    st.at = 1;
    const s = svc();
    const sess = st.sess || { state: "none" };
    // Only the time left changes while waiting: the step is not drawn again, so focus and the pasted address stay.
    if (!changed && $("#cloud-time-left")) { $("#cloud-time-left").textContent = minutesLeft(sess.seconds_left); return; }
    st.last = sess.state;
    const parts = [];
    let foot = [backButton(() => { cancelSession(); stepService(); })];
    if (s.signin === "oauth") {
      parts.push(el("p", { text: `Sign in with ${s.name}'s own page. Starboard never receives your password: ${s.name} gives it a key for your files, which it keeps on this computer only.` }));
      if (phoneOffered()) parts.push(wayCards());
      if (sess.state === "starting") parts.push(waiting("Getting the sign-in ready…", sess.seconds_left));
      else if (sess.state === "link") { const [card, go] = linkCard(sess); parts.push(card); foot = [go, ...foot]; }
      else if (sess.state === "checking") parts.push(waiting(`Checking the sign-in with ${s.name}…`, sess.seconds_left));
      else if (sess.state === "phone") parts.push(phoneCard(sess));
      else if (sess.state === "failed" || sess.state === "expired") {
        const again = el("button", { type: "button", class: "btn", id: "cloud-try-again", text: "Try again" });
        again.addEventListener("click", startSignin);
        parts.push(errorNotice(sess.error || "The sign-in did not finish.", [again]));
      }
    } else {
      const [form, go] = detailsForm(s);
      parts.push(form);
      foot = [go, ...foot];
    }
    const h = frame(1, s.signin === "oauth" ? `Sign in to ${s.name}` : s.signin === "paste" ? "Paste your own rclone remote" : `Connect to ${s.name}`, parts, foot);
    if (sess.state === "failed" || sess.state === "expired") {
      $("#cloud-error")?.focus();
    } else if (changed && sess.state !== "phone" && sess.state !== "checking") focusStep(h);
  }

  function wayCards() {
    const ways = [["phone", "Complete on the phone", "Scan a QR code and sign in on your phone. Starboard waits by itself."],
      ["browser", "Complete in this browser", "Open the sign-in page here, then paste back the address it ends on."]];
    const box = el("fieldset", { class: "option-cards option-cards--row", id: "cloud-way" }, el("legend", { class: "field__label", text: "How do you want to sign in?" }),
      ways.map(([v, title, line]) => el("label", { class: "option-card" },
        el("input", { type: "radio", name: "cloud-way", value: v, checked: st.way === v }), el("strong", { text: title }), el("small", { text: line }))));
    box.addEventListener("change", (e) => {
      st.way = e.target.value;
      startSignin().then(() => $(`input[name=cloud-way][value=${st.way}]`)?.focus());
    });
    return box;
  }

  function waiting(words, seconds) {
    return el("div", { class: "signin-wait" },
      el("div", { class: "signin-wait__words" }, el("span", { role: "status", id: "cloud-wait-words", text: words }),
        el("span", { class: "muted", id: "cloud-time-left", text: minutesLeft(seconds) })),
      el("div", { class: "progress progress--busy", role: "progressbar", "aria-label": words.replace(/…$/, ""), "aria-valuetext": "Waiting" }, el("span")));
  }

  function linkCard(sess) {
    const s = svc();
    const paste = el("input", { class: "input", id: "cloud-answer", spellcheck: "false", autocomplete: "off", inputmode: "url", "aria-describedby": "cloud-answer-hint" });
    const card = el("div", { class: "signin-card" }, el("ol", { class: "signin-steps" },
      el("li", {}, el("p", { text: `Open ${s.name}'s sign-in page, sign in and allow Starboard to use your files.` }),
        el("p", {}, el("a", { class: "btn", id: "cloud-open-signin", href: sess.link, target: "_blank", rel: "noopener noreferrer" },
          icon("external-link"), "Open the sign-in page", el("span", { class: "visually-hidden", text: ` for ${s.name} (opens in a new tab)` })))),
      el("li", {}, el("p", { text: "Finish every check the service asks for, such as a code from your phone or approving the sign-in in an app. Your browser then shows a page that does not load, such as This site cannot be reached. That is expected: its address holds the answer. It starts like this:" }),
        el("code", { class: "signin-example", text: "http://127.0.0.1:53682/?state=…&code=…" })),
      el("li", {}, el("div", { class: "field" }, el("label", { for: "cloud-answer", text: "Paste that whole address" }),
        el("span", { class: "hint", id: "cloud-answer-hint", text: "From the browser's address bar. It goes only to this sign-in, which then ends." }), paste))),
    el("p", { class: "small muted", text: "Why: the sign-in answers an address on the computer that asked for it. Starboard runs in its own container, so you carry the answer across." }),
    waitingLine(sess));
    const go = el("button", { type: "button", class: "btn btn--primary", id: "cloud-answer-go", text: "Continue" });
    const send = async () => {
      fieldError(paste, "");
      if (!paste.value.trim()) { fieldError(paste, "Paste the address from the browser's address bar"); return; }
      go.disabled = true;
      try {
        st.sess = await api("/api/backup/cloud/answer", { method: "POST", body: { id: st.sess.id, address: paste.value } });
        announce(`Checking the sign-in with ${s.name}`);
        drawSignin(true);
        follow();
      } catch (e) {
        go.disabled = false;
        if (e.data && "field" in e.data) fieldError(paste, e.message);  // the address itself: said beside the field
        else { st.sess = await api("/api/backup/cloud/session").catch(() => ({ state: "failed", error: e.message })); drawSignin(true); }
      }
    };
    go.addEventListener("click", send);
    paste.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); send(); } });
    return [card, go];
  }
  function waitingLine(sess) {
    return el("p", { class: "small muted" }, el("span", { id: "cloud-time-left", text: minutesLeft(sess.seconds_left) }), ". After that, select Try again for a new sign-in.");
  }

  function phoneCard(sess) {
    const page = sess.page.replace(/^https:\/\//, "");
    return el("div", { class: "signin-card" },
      el("div", { class: "qr-card" },
        el("figure", { class: "qr-card__code" }, qrSvg(sess.qr, `QR code for ${page}`)),
        el("div", { class: "qr-card__text" },
          el("p", { text: "Scan the QR code with your phone's camera, or open this page on any device:" }),
          el("p", {}, el("span", { class: "address" }, el("a", { href: sess.page, target: "_blank", rel: "noopener noreferrer" }, page,
            el("span", { class: "visually-hidden", text: " (opens in a new tab)" })), copyButton(sess.page, "the address"))),
          el("p", { text: `Enter this code there, then sign in and allow Starboard to use your files in ${svc().name}:` }),
          el("p", { class: "device-code" }, el("span", { class: "device-code__value", "aria-label": spelt(sess.user_code), text: sess.user_code }),
            labelledCopy(sess.user_code, "the code", "Code copied")))),
      waiting("Waiting for you to sign in on your phone…", sess.seconds_left),
      el("p", { class: "small muted", text: "Starboard moves on by itself when you have allowed it. You can close the phone's page after that." }));
  }

  function detailsForm(s) {
    const form = el("form", { class: "form-stack", id: "cloud-details", novalidate: true });
    const inputs = {};
    if (s.signin === "paste") {
      inputs.remote = el("input", { class: "input", id: "cloud-f-remote", spellcheck: "false", autocomplete: "off", placeholder: "mycloud:starboard-backups", "aria-describedby": "cloud-f-remote-hint" });
      inputs.config = el("textarea", { class: "input", id: "cloud-f-config", rows: "6", spellcheck: "false", autocomplete: "off", "aria-describedby": "cloud-f-config-hint" });
      form.append(
        el("div", { class: "field" }, el("label", { for: "cloud-f-remote", text: "Remote and folder" }), el("span", { class: "hint", id: "cloud-f-remote-hint", text: "As name:folder, the remote's name as it is in your rclone.conf." }), inputs.remote),
        el("div", { class: "field" }, el("label", { for: "cloud-f-config", text: "The remote's part of rclone.conf" }),
          el("span", { class: "hint", id: "cloud-f-config-hint", text: "The lines from [name] to the next [ ]. The command rclone config file shows where rclone.conf is. Kept by Starboard only." }), inputs.config));
    } else {
      for (const f of s.fields) {
        const id = `cloud-f-${f.id}`;
        let input;
        if (f.kind === "choice") {
          input = el("select", { class: "select", id }, f.choices.map(([v, t]) => el("option", { value: v, text: t })));
        } else {
          input = el("input", { class: "input", id, type: f.kind === "secret" ? "password" : "text", spellcheck: "false",
            autocomplete: f.kind === "secret" ? "new-password" : f.kind === "user" ? "username" : "off", value: f.default || "",
            inputmode: f.kind === "port" ? "numeric" : f.kind === "url" ? "url" : null, required: f.required });
        }
        if (f.hint) input.setAttribute("aria-describedby", `${id}-hint`);
        inputs[f.id] = input;
        form.append(el("div", { class: "field" }, el("label", { for: id }, f.label, f.required ? el("span", { class: "field__required", "aria-hidden": "true", text: "*" }) : null),
          f.hint ? el("span", { class: "hint", id: `${id}-hint`, text: f.hint }) : null, input));
      }
      form.append(el("p", { class: "required-key" }, el("span", { class: "field__required", text: "*" }), "= Required"));
    }
    const go = el("button", { type: "submit", class: "btn btn--primary", form: "cloud-details", id: "cloud-details-go", text: "Continue" });
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      Object.values(inputs).forEach((i) => fieldError(i, ""));
      $("#cloud-error")?.remove();
      go.disabled = true;
      const values = Object.fromEntries(Object.entries(inputs).map(([k, i]) => [k, i.value]));
      try {
        if (!st.sess?.id) st.sess = await api("/api/backup/cloud/start", { method: "POST", body: { service: s.id, dest } });
        announce("Checking the details with rclone");
        st.sess = await api("/api/backup/cloud/details", { method: "POST", body: { id: st.sess.id, values } });
        announce(`Details accepted for ${s.name}`);
        stepFolder();
      } catch (err) {
        go.disabled = false;
        const field = err.data?.field;
        if (field && inputs[field]) fieldError(inputs[field], err.message);
        else { form.after(errorNotice(err.message)); $("#cloud-error").focus(); }
      }
    });
    return [form, go];
  }

  function cancelSession() {
    clearTimeout(st.timer);
    if (st.sess?.id) api("/api/backup/cloud/cancel", { method: "POST" }).catch(() => {});
    st.sess = null;
  }

  function stepSignin() {
    if (svc().signin === "oauth") { if (!phoneOffered()) st.way = "browser"; startSignin(); }
    else { st.sess = null; drawSignin(true); }
  }

  // Step 3: choose the folder -----------------------------------------------------------------------------------------
  async function stepFolder() {
    st.at = 2;
    clearTimeout(st.timer);
    const s = svc();
    const name = el("input", { class: "input", id: "cloud-new-folder", value: st.folder, spellcheck: "false", autocomplete: "off", "aria-describedby": "cloud-new-folder-hint" });
    const listBox = el("div", { id: "cloud-folder-list" }, waiting(`Reading the folders in ${s.name}…`, null));
    const go = el("button", { type: "button", class: "btn btn--primary", text: "Continue to the test" });
    const h = frame(2, `Where in ${s.name}?`, [
      s.folder_note ? el("p", { text: s.folder_note }) : null,
      el("fieldset", { class: "stack-3" }, el("legend", { class: "field__label", text: "Folder for the backups" }),
        el("label", { class: "check" }, el("input", { type: "radio", name: "cloud-folder", value: "", "data-new": "1", checked: st.folderChoice === "new" }),
          el("span", { class: "check__text" }, "Make a new folder (recommended)", el("span", { class: "check__hint", text: "Keeps the backups apart from your other files." }))),
        el("div", { class: "field" }, el("label", { for: "cloud-new-folder", text: "Name of the new folder" }),
          el("span", { class: "hint", id: "cloud-new-folder-hint", text: "Letters, numbers, spaces, dots and dashes, with / between folders." }), name),
        listBox)], [go, backButton(() => { cancelSession(); stepSignin(); })]);
    focusStep(h);
    try {
      const got = await api("/api/backup/cloud/folders", { method: "POST", body: { id: st.sess.id } });
      st.folders = got.folders;
      listBox.replaceChildren(...(got.folders.length ? [el("p", { class: "small muted", text: `Or use a folder that is there already (${got.folders.length}):` }),
        ...got.folders.map((f) => el("label", { class: "check" }, el("input", { type: "radio", name: "cloud-folder", value: f, checked: st.folderChoice === "existing" && st.folder === f }),
          el("span", { class: "check__text", text: f })))] : [el("p", { class: "small muted", text: `${s.name} has no folders Starboard can open.` })]));
    } catch (e) {
      const w = testWords(e.message);
      listBox.replaceChildren(el("p", { class: "small muted", text: `Starboard could not list the folders: ${w.text}. A new folder still works.` }),
        w.signin ? signinAgainButton() : null);
    }
    go.addEventListener("click", () => {
      const chosen = panel.body.querySelector("input[name=cloud-folder]:checked");
      const isNew = !chosen || chosen.dataset.new;
      const value = isNew ? name.value.trim().replace(/^\/+|\/+$/g, "") : chosen.value;
      if (isNew && !value) { fieldError(name, "Enter a name for the new folder"); return; }
      st.folder = value;
      st.folderChoice = isNew ? "new" : "existing";
      stepTest();
    });
    name.addEventListener("input", () => { const r = panel.body.querySelector("input[data-new]"); if (r) r.checked = true; });
  }

  function signinAgainButton() {
    const b = el("button", { type: "button", class: "btn", id: "cloud-signin-again", text: "Sign in again" });
    b.addEventListener("click", () => { cancelSession(); stepSignin(); });
    return b;
  }

  // Step 4: test -------------------------------------------------------------------------------------------------------
  async function stepTest() {
    st.at = 3;
    const s = svc();
    const where = `${s.name}, ${st.folder}`;
    const status = el("p", { role: "status", id: "cloud-test-status", text: `Testing ${where}…` });
    const box = el("div", { id: "cloud-test-box", class: "stack-3" }, testChecks(null, true));
    const go = el("button", { type: "button", class: "btn btn--primary", id: "cloud-test-go", text: "Continue", disabled: true });
    const again = el("button", { type: "button", class: "btn", id: "cloud-test-again", text: "Test again" });
    const h = frame(3, "Test the connection", [
      el("p", { text: `Starboard makes the folder if it is not there, writes a small file, reads it back and removes it, so a backup copy will work.` }),
      status, box], [go, again, backButton(stepFolder)]);
    focusStep(h);
    go.addEventListener("click", stepSave);
    again.addEventListener("click", stepTest);
    again.disabled = true;
    try {
      st.sess = await api("/api/backup/cloud/test", { method: "POST", body: { id: st.sess.id, folder: st.folder } });
    } catch (e) {
      st.sess = { ...st.sess, test: { ok: false, error: e.message } };
    }
    if (st.closed || st.at !== 3) return;
    const t = st.sess.test || { ok: false };
    again.disabled = false;
    const w = testWords(t.error);
    box.replaceChildren(testChecks(t, false), t.ok
      ? notice("success", "Connected", `Starboard can write to ${where}.${t.free != null ? ` ${formatBytes(t.free)} free there.` : ""}`)
      : el("div", { class: "notice", "data-tone": "danger", id: "cloud-error", tabindex: "-1" }, icon("circle-alert"),
        el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: "The test did not work" }), el("p", { text: w.text })),
        w.signin ? signinAgainButton() : null));
    status.textContent = t.ok ? `Connected: Starboard can write to ${where}` : `The test did not work: ${w.text}`;
    status.className = "visually-hidden";  // said once; the checks and the notice show it
    go.disabled = !t.ok;
    (t.ok ? go : $("#cloud-error"))?.focus();
  }

  // Step 5: save ------------------------------------------------------------------------------------------------------
  function stepSave() {
    st.at = 4;
    const s = svc();
    const keep = el("input", { class: "input input--narrow", id: "cloud-keep", type: "number", min: "1", max: "50", value: String(list.keep || 5), inputmode: "numeric", "aria-describedby": "cloud-keep-hint" });
    const mine = el("input", { class: "input", id: "cloud-password", type: "password", autocomplete: "current-password", "aria-describedby": "cloud-password-hint" });
    const row = (what, answer, to) => {
      const b = el("button", { type: "button", class: "btn btn--quiet" }, "Change", el("span", { class: "visually-hidden", text: ` ${what.toLowerCase()}` }));
      b.addEventListener("click", to);
      return el("tr", {}, el("th", { scope: "row", "data-label": "What", text: what }), el("td", { "data-label": "Your answer", text: answer }), el("td", { "data-label": "" }, b));
    };
    const signedIn = s.signin === "oauth" ? (st.sess.account ? `Signed in as ${st.sess.account}` : `Signed in${st.way === "phone" ? " on your phone" : " in this browser"}`) : s.signin === "paste" ? "Your own rclone.conf" : "With the details you entered";
    const table = el("div", { class: "table-wrap", "data-stack": true }, el("table", { class: "table table--fixed table--middle" },
      el("caption", { class: "visually-hidden", text: "What will be saved" }),
      el("colgroup", {}, el("col", { class: "col-quarter" }), el("col"), el("col", { class: "col-state" })),
      el("thead", {}, el("tr", {}, el("th", { scope: "col", text: "What" }), el("th", { scope: "col", text: "Your answer" }), el("th", { scope: "col" }, el("span", { class: "visually-hidden", text: "Change" })))),
      el("tbody", {}, row("Service", s.name, () => { cancelSession(); stepService(); }), row("Sign-in", signedIn, () => { cancelSession(); stepSignin(); }),
        row("Folder", st.folder, stepFolder))));
    const go = el("button", { type: "submit", class: "btn btn--primary", form: "cloud-save", id: "cloud-save-go", text: "Save and finish" });
    const form = el("form", { class: "form-stack", id: "cloud-save", novalidate: true },
      el("div", { class: "field" }, el("label", { for: "cloud-keep", text: "Keep the newest" }),
        el("span", { class: "hint", id: "cloud-keep-hint", text: `How many full backups stay in ${s.name}. Older ones there are removed. From 1 to 50.` }), keep),
      el("div", { class: "field" }, el("label", { for: "cloud-password", text: "Your Starboard password" }),
        el("span", { class: "hint", id: "cloud-password-hint", text: "Asked each time where the copies go changes." }), mine));
    const h = frame(4, "Check and save", [table, form,
      el("p", { class: "small muted", text: "After saving, each new full backup is copied there. Test connection on the page checks it again at any time." })],
    [go, backButton(stepTest)]);
    focusStep(h);
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      fieldError(keep, ""); fieldError(mine, "");
      const n = Number(keep.value);
      if (!Number.isInteger(n) || n < 1 || n > 50) { fieldError(keep, "Give a number from 1 to 50"); return; }
      if (!mine.value) { fieldError(mine, "Enter your Starboard password"); return; }
      go.disabled = true;
      try {
        await api("/api/backup/cloud/save", { method: "POST", body: { id: st.sess.id, keep: n, password: mine.value } });
        st.saved = true;
        panel.close();
        announce(`Saved: each new full backup is copied to ${s.name}, ${st.folder}`);
        onSaved?.();
      } catch (err) {
        go.disabled = false;
        if (err.status === 401 || err.status === 429 || /password/i.test(err.message)) fieldError(mine, err.message);
        else { form.after(errorNotice(err.message)); $("#cloud-error").focus(); }
      }
    });
  }

  if (startAt === "signin" && st.service) stepSignin(); else stepService();
}
