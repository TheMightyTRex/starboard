// Settings, People (DASH-589, single sign-on stage 1): the people who use your apps, and a long, unique password for each one
// in each app. Starboard keeps the list and the passwords. It does not yet make, pause or remove an account inside an app
// (stage 3), so the page says so, and asks the owner to say when a password has been set in the app. Nothing is read
// from an app and nothing runs between visits: the list is read when the page opens and after each change.

const PEOPLE_STATE = { active: ["Active", "success"], paused: ["Paused", "warning", "pause"], removed: ["Removed", "muted"] };
const ACCOUNT_STATE = { none: ["No account", "muted"], made: ["Password made, not set", "warning"], "in-use": ["Password set in the app", "success"] };

function peopleDate(iso) {
  return iso ? new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" }) : "";
}

function peopleTable(caption, columns, rows) {
  return el("div", { class: "table-wrap", "data-stack": true }, el("table", { class: "table table--middle" },
    el("caption", { class: "visually-hidden", text: caption }),
    el("thead", {}, el("tr", {}, columns.map((text) => el("th", { scope: "col", text })))),
    el("tbody", {}, rows)));
}

function accountWords(p) {
  const made = p.accounts.filter((a) => a.state !== "none").length;
  if (!p.accounts.length) return "No accounts yet";
  return `${made} of ${plural(p.accounts.length, "account")} with a password`;
}

async function startPeople() {
  const box = $("#people-sections");
  let data = null;
  let panel = null;
  let openId = "";

  const personById = (id) => data.people.find((p) => p.id === id);
  const saved = (text) => { showSaved("people-saved", text); announce(text); };

  async function call(path, body = {}) {
    data = await api(path, { method: "POST", body });
    return data;
  }

  // The page ------------------------------------------------------------------
  function drawPage(focusId = "") {
    const add = el("button", { type: "button", class: "btn btn--primary" }, icon("user-plus"), "Add a person");
    add.addEventListener("click", () => openAdd(add));
    const live = data.people.filter((p) => p.state !== "removed");
    const gone = data.people.filter((p) => p.state === "removed");
    const manage = (p) => {
      const b = el("button", { type: "button", class: "btn btn--compact", "data-person": p.id }, icon("pencil"), "Manage", el("span", { class: "visually-hidden", text: ` ${p.name}` }));
      b.addEventListener("click", () => openPerson(p.id, b));
      return b;
    };
    const owner = el("tr", {},
      el("th", { scope: "row", "data-label": "Name" }, "You"),
      el("td", { "data-label": "Role", text: "Owner" }),
      el("td", { "data-label": "State" }, chip("Active", "success")),
      el("td", { "data-label": "Accounts", text: "Everything, with your Starboard password" }),
      el("td", { "data-label": "Manage", class: "muted", text: "Nothing to manage" }));
    const rows = [owner, ...live.map((p) => el("tr", {},
      el("th", { scope: "row", "data-label": "Name", text: p.name }),
      el("td", { "data-label": "Role", text: p.role_name }),
      el("td", { "data-label": "State" }, chip(...PEOPLE_STATE[p.state])),
      el("td", { "data-label": "Accounts", text: accountWords(p) }),
      el("td", { "data-label": "Manage" }, manage(p))))];
    const forgetWords = (p) => (p.can_forget ? "Ready to forget" : `Can be forgotten in ${plural(p.forget_in_days, "day")}`);
    const removed = gone.length ? el("details", { class: "disclosure", id: "people-removed" },
      el("summary", { text: `Removed people (${gone.length})` }),
      el("div", { class: "disclosure__body" },
        el("p", { class: "small muted", text: `Starboard keeps a removed person's record, and the passwords it made, for ${data.forget_after_days} days, in case it was a mistake. Then you can forget them for good.` }),
        peopleTable("Removed people and when each was removed", ["Name", "Role", "Removed", "Forget", "Manage"], gone.map((p) => el("tr", {},
          el("th", { scope: "row", "data-label": "Name", text: p.name }),
          el("td", { "data-label": "Role", text: p.role_name }),
          el("td", { "data-label": "Removed", text: peopleDate(p.removed_at) }),
          el("td", { "data-label": "Forget", text: forgetWords(p) }),
          el("td", { "data-label": "Manage" }, manage(p))))))) : null;
    const none = !live.length ? el("p", { class: "small muted", id: "people-none", text: "No one is here yet. Add each person who uses your apps, then make a password for each app they use." }) : null;
    const limit = live.length >= data.limit;
    if (limit) add.disabled = true;
    box.replaceChildren(
      section("people", "People", null,
        notice("info", "Starboard keeps the list and the passwords for now", "It does not yet make, pause or remove an account inside an app. You make the account in the app, set the password Starboard made, and say so here. When you pause or remove someone, stop their account working in each app yourself."),
        el("div", { class: "actions" }, add, savedNote("people-saved"), limit ? el("span", { class: "small muted", text: `Starboard keeps up to ${data.limit} people.` }) : null),
        peopleTable("People, with their role, state and accounts", ["Name", "Role", "State", "Accounts", "Manage"], rows),
        none, removed));
    box.removeAttribute("aria-busy");
    SharedComponents.setupTooltips?.();
    if (focusId) $(`[data-person="${focusId}"]`, box)?.focus();
  }

  async function reload() {
    data = await api("/api/people");
    drawPage();
  }

  // Adding and changing a person ----------------------------------------------
  function detailsForm(p) {
    const name = el("input", { class: "input", id: "person-name", autocomplete: "off", maxlength: data.name_max || 40, required: true, value: p?.name || "" });
    const email = el("input", { class: "input", id: "person-email", type: "email", autocomplete: "off", value: p?.email || "" });
    const role = el("select", { class: "select", id: "person-role" }, data.roles.map((r) => el("option", { value: r.id, text: r.name, selected: p ? p.role === r.id : r.id === "household" })));
    const roleHint = el("span", { class: "hint", id: "person-role-about" });
    const about = () => { roleHint.textContent = data.roles.find((r) => r.id === role.value)?.about || ""; };
    role.addEventListener("change", about);
    about();
    role.setAttribute("aria-describedby", "person-role-about");
    const form = el("form", { class: "form-stack", id: "person-form", novalidate: true },
      field("Name", name, { required: true, hint: "How you tell them apart. Up to 40 letters." }),
      field("Email address (optional)", email, { hint: "Only for your own notes. Starboard never sends email." }),
      el("div", { class: "field" }, el("label", { for: "person-role", text: "Role" }), role, roleHint));
    return { form, name, email, role };
  }

  function openAdd(opener) {
    const f = detailsForm(null);
    const go = el("button", { type: "submit", class: "btn btn--primary", form: "person-form", text: "Add person" });
    const cancel = el("button", { type: "button", class: "btn", text: "Cancel" });
    const p = sidePanel({ title: "Add a person", opener, body: [f.form], foot: [go, cancel] });
    setTimeout(() => f.name.focus(), 0);
    cancel.addEventListener("click", () => p.close());
    f.form.addEventListener("submit", async (e) => {
      e.preventDefault();
      go.disabled = true;
      try {
        const r = await call("/api/people", { name: f.name.value, email: f.email.value, role: f.role.value });
        p.close();
        drawPage(r.person);
        saved(r.said);
      } catch (err) { go.disabled = false; problem(err.message, go); }
    });
  }

  // One person -----------------------------------------------------------------
  function openPerson(id, opener) {
    openId = id;
    const first = !panel?.layer?.isConnected;
    const p = personById(id);
    panel = sidePanel({ title: p.name, opener, wide: true, body: personBody(p), foot: [doneButton()], onClose: () => { panel = null; openId = ""; drawPage(id); } });
    return first;
  }

  const doneButton = () => {
    const b = el("button", { type: "button", class: "btn", text: "Done" });
    b.addEventListener("click", () => panel.close());
    return b;
  };

  // Draws the open person again after a change, then puts focus back on the control that was used.
  function redraw(focusSelector, said) {
    const p = personById(openId);
    if (!panel || !p) return;
    panel.setTitle(p.name);
    panel.setBody(personBody(p));
    if (said) announce(said);
    requestAnimationFrame(() => (focusSelector ? $(focusSelector, panel.body) : null)?.focus());
  }

  function personBody(p) {
    const removed = p.state === "removed";
    const out = [];
    // Details
    const f = detailsForm(p);
    f.form.id = "person-form";
    const save = el("button", { type: "submit", class: "btn btn--primary", text: "Save details" });
    f.form.append(el("div", { class: "actions" }, save));
    if (removed) { [f.name, f.email, f.role, save].forEach((c) => { c.disabled = true; }); }
    f.form.addEventListener("submit", async (e) => {
      e.preventDefault();
      try { const r = await call(`/api/people/${p.id}`, { name: f.name.value, email: f.email.value, role: f.role.value }); redraw("#person-name", r.said); }
      catch (err) { problem(err.message, save); }
    });
    out.push(el("section", { "aria-labelledby": "person-details-h", class: "stack-4" }, el("h3", { id: "person-details-h", text: "Details" }), f.form));
    if (p.role === "child") out.push(notice("info", "Limits depend on each app", "Starboard cannot yet set a child's limits, such as age ratings or hours. Set them in each app. It will say where an app cannot limit a child."));
    // Accounts
    out.push(el("section", { "aria-labelledby": "person-accounts-h", class: "stack-4" },
      el("h3", { id: "person-accounts-h", text: "Accounts in your apps" }),
      removed ? el("p", { class: "small muted", text: "Put this person back to change their accounts." }) : accountsList(p)));
    // How to sign in
    if (!removed && p.accounts.length) {
      const print = el("button", { type: "button", class: "btn" }, icon("file-text"), "Print how to sign in");
      const printWith = el("button", { type: "button", class: "btn" }, icon("file-text"), "Print with the passwords");
      print.addEventListener("click", () => printCard(p, false, print));
      printWith.addEventListener("click", () => printCard(p, true, printWith));
      out.push(el("section", { "aria-labelledby": "person-card-h", class: "stack-4" }, el("h3", { id: "person-card-h", text: "How to sign in" }),
        el("p", { class: "small muted", text: `A page for ${p.name} with each app's address and account name. With the passwords, it asks for your Starboard password, and the page is one to keep private.` }),
        el("div", { class: "actions" }, print, printWith)));
    }
    // Pause and remove
    out.push(stateSection(p));
    return out;
  }

  function stateSection(p) {
    const list = el("ul", { class: "action-list", "aria-label": `Pause or remove ${p.name}` });
    const item = (label, hint, id, run, danger = false) => {
      const b = el("button", { type: "button", class: danger ? "btn btn--danger" : "btn", id, "aria-describedby": `${id}-hint` }, label);
      b.addEventListener("click", run);
      list.append(el("li", { class: "action-list__item" }, b, el("span", { class: "action-list__hint", id: `${id}-hint`, text: hint })));
    };
    const word = { pause: "Paused", resume: "Resumed", remove: "Removed", restore: "Put back" };
    const act = (what, after) => async () => {
      try { const r = await call(`/api/people/${p.id}/${what}`); drawPage(); redraw(after, r.said); }
      catch (err) { problem(err.message); }
    };
    if (p.state === "active") item("Pause", "Marks them paused here. Their accounts in the apps stay as they are until you stop them working there.", "person-pause", act("pause", "#person-resume"));
    if (p.state === "paused") item("Resume", "Marks them active again.", "person-resume", act("resume", "#person-pause"));
    if (p.state !== "removed") {
      item("Remove", `Moves ${p.name} to Removed people for ${data.forget_after_days} days. Starboard deletes nothing in your apps.`, "person-remove", async () => {
        if (!await confirmDialog({ title: `Remove ${p.name}?`, danger: true, confirm: "Remove",
          message: `Starboard moves ${p.name} to Removed people and keeps the record and passwords for ${data.forget_after_days} days. It does not change anything in your apps, so stop their accounts working there. You can put them back.` })) return;
        try { const r = await call(`/api/people/${p.id}/remove`); panel.close(); drawPage(); saved(r.said); }
        catch (err) { problem(err.message); }
      }, true);
    } else {
      item("Put back", "Makes them active again, with their accounts and passwords as they were.", "person-restore", async () => {
        try { const r = await call(`/api/people/${p.id}/restore`); drawPage(); redraw("#person-pause", r.said); }
        catch (err) { problem(err.message); }
      });
      item("Forget for good", p.can_forget ? "Deletes the record and every password Starboard kept for this person. Asks for your Starboard password." : `Possible in ${plural(p.forget_in_days, "day")}.`, "person-forget", async () => {
        const pw = passwordInput("person-forget-pw");
        if (!await confirmDialog({ title: `Forget ${p.name} for good?`, danger: true, confirm: "Forget for good",
          message: `Starboard deletes ${p.name}'s record and every password it kept for them. It cannot be undone. Starboard deletes nothing in your apps.`, fields: [passwordField(pw)] })) return;
        try { const r = await call(`/api/people/${p.id}/forget`, { password: pw.value }); panel.close(); drawPage(); saved(r.said); }
        catch (err) { problem(err.message); }
      }, true);
      if (!p.can_forget) $("#person-forget", list)?.setAttribute("aria-disabled", "true");
    }
    return el("section", { "aria-labelledby": "person-state-h", class: "stack-4" },
      el("h3", { id: "person-state-h", text: "Pause or remove" }), list);
  }

  // Accounts ---------------------------------------------------------------------
  function accountsList(p) {
    const byApp = new Map(p.accounts.map((a) => [a.app, a]));
    const rows = data.apps.map((a) => ({ app: a.id, name: a.name, acct: byApp.get(a.id) || null }));
    for (const a of p.accounts) if (!data.apps.some((x) => x.id === a.app)) rows.push({ app: a.app, name: a.app_name || a.app, acct: a, gone: true });
    if (!rows.length) return notice("info", "No apps to give an account in", "Add your media apps, such as Jellyfin or Audiobookshelf, in Settings, Manage apps. They appear here after that.");
    return el("ul", { class: "rows people-accounts", "aria-label": `${p.name}'s accounts` }, rows.map((r) => accountRow(p, r)));
  }

  function accountRow(p, { app, name, acct, gone }) {
    const state = acct?.state || "none";
    const meta = !acct ? "No account recorded."
      : state === "none" ? `Account name: ${acct.username}. No password made yet.`
        : state === "made" ? `Account name: ${acct.username}. ${acct.own ? "Chosen by you" : "Made"} on ${peopleDate(acct.made_at)}. Set it in ${name}, then say so.`
          : `Account name: ${acct.username}. Set in the app on ${peopleDate(acct.set_at)}.`;
    const base = `/api/people/${p.id}/accounts/${app}`;
    const rowId = `acct-${app}`;
    const buttons = [];
    const button = (label, run, extra = {}) => {
      const b = el("button", { type: "button", class: extra.primary ? "btn btn--primary btn--compact" : "btn btn--compact", id: extra.id || null },
        extra.icon ? icon(extra.icon) : null, label, el("span", { class: "visually-hidden", text: ` for ${p.name} in ${name}` }));
      b.addEventListener("click", run);
      return b;
    };
    // Make a password, or reset one: a generated one (the default) or one the owner types, and for the apps Starboard can
    // reach, "Also change it in the app". Replacing, or changing it in the app, asks for the Starboard password.
    const makeIt = async (replace) => {
      const info = data.apps.find((a) => a.id === app);
      const rule = info?.rule || { min: data.own_min, note: "" };
      const nameBox = el("input", { class: "input", id: `${rowId}-user`, autocomplete: "off", value: acct?.username || p.name });
      const radio = (value, label, hint, checked) => {
        const input = el("input", { type: "radio", name: `${rowId}-mode`, value, id: `${rowId}-mode-${value}`, checked });
        return { input, node: el("label", { class: "check", for: input.id }, input, el("span", { class: "check__text" }, el("strong", { text: label }), el("span", { class: "check__hint", text: hint }))) };
      };
      const generate = radio("generate", "Generate one", "A long random password with no characters that can be mistaken for each other. This is the best choice.", true);
      const own = radio("own", "Use my own", "Enter one you will remember, or one from your password manager.", false);
      const ownBox = el("input", { class: "input", type: "password", id: `${rowId}-own`, autocomplete: "new-password", spellcheck: "false", maxlength: 128 });
      const ownField = field("The password you want to use", ownBox, { hint: `${data.own_rules} ${rule.note}`.trim() });
      ownField.hidden = true;
      const mode = el("fieldset", { class: "form-stack" }, el("legend", { class: "field__label", text: "Password" }), generate.node, own.node);
      const also = info?.can_change ? el("input", { type: "checkbox", id: `${rowId}-also` }) : null;
      const alsoNode = also
        ? el("label", { class: "check", for: also.id }, also, el("span", { class: "check__text" }, el("strong", { text: `Also change it in ${name}` }),
          el("span", { class: "check__hint", text: `Starboard changes the password of the account called ${acct?.username || p.name} in ${name} and records it as set. The account must be there already. Asks for your Starboard password.` })))
        : el("p", { class: "small muted", text: `Starboard only records the password for ${name}. Change it in ${name} yourself, then choose It is set in the app.` });
      const pwBox = passwordInput(`${rowId}-starboard-pw`);
      const pwField = passwordField(pwBox, { hint: "Needed to replace a password or to change it in the app." });
      pwField.hidden = !replace;
      const refresh = () => {
        const mine = own.input.checked;
        ownField.hidden = !mine;
        ownBox.required = mine;
        pwField.hidden = !(replace || also?.checked);
        pwBox.required = !pwField.hidden;
      };
      generate.input.addEventListener("change", refresh);
      own.input.addEventListener("change", refresh);
      also?.addEventListener("change", refresh);
      ownBox.addEventListener("input", () => ownBox.setCustomValidity(ownBox.value.trim().length && ownBox.value.length < rule.min ? `Use at least ${rule.min} characters` : ""));
      refresh();
      const intro = replace
        ? `Choose a new password for ${p.name} in ${name}. Starboard forgets the old one.${also ? "" : ` The old one stays right in ${name} until you set the new one there.`}`
        : `Choose a password for ${p.name} in ${name}. Make the account in ${name} with this account name, then set the password there${also ? ", or let Starboard change it" : ""}.`;
      const fields = [...(replace ? [] : [field(`Account name in ${name}`, nameBox, { hint: "The name they sign in with. It can be changed later." })]), mode, ownField, alsoNode, pwField];
      if (!await confirmDialog({ title: replace ? `Reset the password for ${p.name} in ${name}?` : `Make a password for ${p.name} in ${name}`, message: intro, confirm: replace ? "Reset the password" : "Make a password", careful: replace, fields })) return;
      try {
        if (!replace && nameBox.value) await call(`${base}`, { username: nameBox.value });
        const body = { replace: !!replace, also_change: !!also?.checked };
        if (own.input.checked) body.own_password = ownBox.value;
        if (replace || body.also_change) body.password = pwBox.value;
        const r = await call(`${base}/password`, body);
        redraw(`#${rowId}-show`, `${r.said} for ${p.name} in ${name}`);
        drawPage();
      } catch (err) { problem(err.message); }
    };
    const show = async () => {
      const pw = passwordInput(`${rowId}-pw`);
      if (!await confirmDialog({ title: `Show ${p.name}'s password in ${name}?`, confirm: "Show password", message: "Starboard asks for your password each time, and never writes the password in a log.", fields: [passwordField(pw)] })) return;
      try {
        const r = await api(`${base}/reveal`, { method: "POST", body: { password: pw.value } });
        const out = el("input", { class: "input secret-field__input", id: `${rowId}-secret`, type: "password", readonly: true, autocomplete: "off", spellcheck: "false" });
        out.value = r.password;
        const copy = el("button", { type: "button", class: "btn btn--primary", "data-secret-copy": "" }, icon("copy"), "Copy", el("span", { class: "visually-hidden", text: ` password for ${p.name} in ${name}` }));
        const hide = el("button", { type: "button", class: "btn", text: "Hide" });
        const secret = el("div", { class: "secret-field", "data-secret": "", "data-name": `${p.name}'s password in ${name}` }, out,
          el("button", { type: "button", class: "btn", "data-secret-show": "", "aria-controls": out.id }, icon("eye"), "Show"), copy);
        const where = $(`#${rowId}-reveal`, panel.body);
        where.replaceChildren(field(`Account name: ${r.username}. Password`, secret), hide);
        SharedComponents.setupSecrets(where);
        hide.addEventListener("click", () => { where.replaceChildren(); out.value = ""; $(`#${rowId}-show`, panel.body)?.focus(); });
        copy.focus();
      } catch (err) { problem(err.message); }
    };
    const setIt = (done) => async () => {
      try { const r = await call(`${base}/${done ? "set" : "unset"}`); redraw(`#${rowId}-show`, done ? `Noted that ${p.name}'s password is set in ${name}` : r.said); drawPage(); }
      catch (err) { problem(err.message); }
    };
    const rename = async () => {
      const input = el("input", { class: "input", id: `${rowId}-rename`, autocomplete: "off", value: acct?.username || p.name });
      if (!await confirmDialog({ title: `Change the account name in ${name}`, confirm: "Save", message: `Starboard does not change the name inside ${name}. Change it there too.`, fields: [field(`Account name in ${name}`, input)] })) return;
      try { const r = await call(base, { username: input.value }); redraw(`#${rowId}-more .menu-wrap > button`, r.said); drawPage(); }
      catch (err) { problem(err.message); }
    };
    const dropIt = async () => {
      if (!await confirmDialog({ title: `Take ${p.name}'s ${name} account out of the list?`, danger: true, confirm: "Take out of the list",
        message: `Starboard forgets the account name and the password it kept. The account in ${name} stays until you remove it there.` })) return;
      try { const r = await call(`${base}/remove`); redraw("", r.said); drawPage(); $("#person-details-h", panel.body)?.focus(); }
      catch (err) { problem(err.message); }
    };
    if (!gone && !acct?.state?.match(/made|in-use/)) buttons.push(button("Make a password", () => makeIt(false), { primary: true, id: `${rowId}-show`, icon: "key-round" }));
    if (acct && state !== "none") buttons.push(button("Show password", show, { id: `${rowId}-show`, icon: "eye" }));
    if (state === "made") buttons.push(button("It is set in the app", setIt(true), { icon: "check" }));
    const more = [];
    if (acct) more.push({ label: "Change the account name", icon: "pencil", onSelect: rename });
    if (state === "in-use") more.push({ label: "Not set in the app any more", icon: "undo-2", onSelect: setIt(false) });
    if (state !== "none") more.push({ label: "Reset the password", icon: "refresh-cw", onSelect: () => makeIt(true) });
    if (acct) more.push({ label: "Take out of the list", icon: "trash-2", danger: true, onSelect: dropIt });
    const side = el("div", { class: "row__side", id: `${rowId}-more` }, chip(...ACCOUNT_STATE[state]), ...buttons, more.length ? menuButton(`More for ${p.name} in ${name}`, more) : null);
    return el("li", { class: "row row--no-lead" },
      el("div", {}, el("div", { class: "row__title", text: name }), el("div", { class: "row__meta", text: meta }), el("div", { id: `${rowId}-reveal`, class: "people-reveal" })),
      side);
  }

  // The printed page -----------------------------------------------------------------
  async function printCard(p, withPasswords, opener) {
    let password = "";
    if (withPasswords) {
      const pw = passwordInput("card-pw");
      if (!await confirmDialog({ title: "Print with the passwords?", confirm: "Print", careful: true,
        message: "The page holds every password Starboard kept for this person. Keep it private, and throw it away once the passwords are saved in a password manager.", fields: [passwordField(pw)] })) return;
      password = pw.value;
    }
    try {
      const apps = new Map(data.apps.map((a) => [a.id, a]));
      const lines = [];
      for (const a of p.accounts.filter((x) => x.state !== "none" || !withPasswords)) {
        const known = apps.get(a.app);
        const line = { name: a.app_name || a.app, address: known?.address || "", user: a.username, password: "" };
        if (withPasswords && a.state !== "none") line.password = (await api(`/api/people/${p.id}/accounts/${a.app}/reveal`, { method: "POST", body: { password } })).password;
        lines.push(line);
      }
      document.getElementById("sign-in-card")?.remove();
      const card = el("section", { class: "sign-in-card", id: "sign-in-card", "aria-hidden": "true" },
        el("h1", { text: `How to sign in, ${p.name}` }),
        el("p", { text: "Open each app at its address and sign in with the account name and password in the table." }),
        el("table", {}, el("thead", {}, el("tr", {}, ["App", "Address", "Account name", withPasswords ? "Password" : ""].map((t) => el("th", { scope: "col", text: t })))),
          el("tbody", {}, lines.map((l) => el("tr", {}, el("th", { scope: "row", text: l.name }), el("td", { text: l.address || "Ask the owner" }), el("td", { text: l.user }), el("td", { text: withPasswords ? l.password : "" }))))),
        withPasswords ? el("p", { text: "Keep this page private. Save each password in a password manager, then throw this page away." }) : null);
      document.body.append(card);
      document.body.classList.add("printing-card");
      const clean = () => { card.remove(); document.body.classList.remove("printing-card"); removeEventListener("afterprint", clean); opener?.focus(); };
      addEventListener("afterprint", clean);
      window.print();
    } catch (err) { problem(err.message, opener); }
  }

  try { await reload(); }
  catch (err) { box.replaceChildren(notice("danger", "Could not list the people", err.message)); box.removeAttribute("aria-busy"); }
}
