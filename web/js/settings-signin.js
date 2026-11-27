// Settings, Security, Sign-in (DASH-512): a two-step code, single sign-on (OpenID Connect) and whether the password
// works. All three are off until set up here. Every change asks for the password again. The secrets are only ever
// said to exist ("kept on this server"): the browser is never sent them back.

const SSO_WHY = {
  tested: ["success", "Test sign-in worked", "Your provider signed you in, and Starboard recognised you. Now you can allow single sign-on."],
  failed: ["danger", "Single sign-on did not work", "Check the details you entered, and the provider's own log. Starboard's log, under System, Logs, says why on its side."],
  nomatch: ["warning", "That account is not the one allowed", "Your provider signed someone in, but the email or claim did not match what you entered."],
  denied: ["warning", "The provider refused", "The provider did not allow the sign-in."],
  expired: ["warning", "The test ran out of time", "Start the test again."],
};

function signinQr(qr, label) {
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

// The password, asked for in a dialog, for every change here (as API keys are made).
async function askPassword({ title, message, confirm, danger = false, extra = [] }) {
  const pw = passwordInput("signin-password");
  const ok = await confirmDialog({ title, message, confirm, danger,
    fields: [...extra.map((f) => f.node), passwordField(pw)] });
  return ok ? { password: pw.value, extra: extra.map((f) => f.input.value) } : null;
}

async function startSignin() {
  const holder = $("#signin-sections");
  let st;
  const base = () => (st.redirect_default || `${location.origin}/api/oidc/callback`);
  const load = async () => { st = await api("/api/security/signin"); };
  try { await load(); } catch (e) { holder.replaceChildren(notice("danger", "Could not read the sign-in settings", e.message)); return; }
  const draw = () => {
    holder.removeAttribute("aria-busy");
    holder.replaceChildren(...[totpSection(), ssoSection(), passwordSection(), reachSection()]);
  };

  // Two-step code ---------------------------------------------------------------------------------------------
  function totpSection() {
    const on = st.totp.enabled;
    const state = headChip(on ? "On" : "Off", on ? "success" : "muted");
    const body = [];
    if (!on) {
      const go = el("button", { type: "button", class: "btn btn--primary" }, icon("shield-check"), "Set up a two-step code");
      go.addEventListener("click", () => setUpTotp(go));
      body.push(el("div", { class: "actions" }, go, savedNote("totp-saved")));
    } else {
      const again = el("button", { type: "button", class: "btn" }, icon("refresh-cw"), "Make new recovery codes");
      again.addEventListener("click", () => newCodes(again));
      const off = el("button", { type: "button", class: "btn btn--danger" }, icon("x"), "Deactivate the two-step code");
      off.addEventListener("click", async () => {
        const r = await askPassword({ title: "Deactivate the two-step code?", message: "Signing in then needs only the password. The recovery codes stop working.", confirm: "Deactivate", danger: true });
        if (!r) return;
        try { st = { ...st, ...(await api("/api/security/totp/off", { method: "POST", body: { password: r.password } })) }; draw(); showSaved("totp-saved", "Two-step code deactivated"); }
        catch (e) { problem(e.message, off); }
      });
      body.push(el("p", { class: "small", id: "recovery-left", text: `${st.totp.recovery_left} of 8 recovery codes left. Each works once.` }),
        el("div", { class: "actions" }, again, off, savedNote("totp-saved")));
    }
    return section("sc-2fa", "Two-step code", "After the password, Starboard asks for the 6 digit code from an authenticator app on your phone. It is off until you set it up.", state, ...body);
  }

  async function setUpTotp(opener) {
    const r = await askPassword({ title: "Set up a two-step code", message: "Your password first. Then Starboard shows a QR code to scan with an authenticator app.", confirm: "Continue" });
    if (!r) return;
    let made;
    try { made = await api("/api/security/totp/start", { method: "POST", body: { password: r.password } }); }
    catch (e) { problem(e.message, opener); return; }
    const code = el("input", { class: "input", id: "totp-code", inputmode: "numeric", autocomplete: "one-time-code", maxlength: "8", spellcheck: "false" });
    const form = el("form", { class: "form-stack", id: "totp-form", novalidate: true },
      el("div", { class: "qr-card qr-card--stack" },
        el("figure", { class: "qr-card__code" }, signinQr(made.qr, "QR code for your authenticator app")),
        el("div", { class: "qr-card__text" },
          el("p", { text: "Scan the QR code with an authenticator app (any that makes time-based codes). Cannot scan? Enter this key in the app instead:" }),
          el("div", { class: "command" }, el("code", { class: "code-block", id: "totp-key", text: made.secret }), copyButton(made.secret.replace(/ /g, ""), "the key")))),
      field("Code from the app", code, { hint: "6 digits. It changes every 30 seconds." }));
    const go = el("button", { type: "submit", class: "btn btn--primary", form: "totp-form", text: "Check the code and activate" });
    const cancel = el("button", { type: "button", class: "btn", text: "Cancel" });
    const panel = sidePanel({ title: "Set up a two-step code", opener, body: [form], foot: [go, cancel] });
    setTimeout(() => code.focus(), 0);
    cancel.addEventListener("click", () => panel.close());
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      setError(code, "");
      if (!code.value.trim()) { setError(code, "Enter the 6 digit code from the app"); code.focus(); return; }
      try {
        const done = await api("/api/security/totp/confirm", { method: "POST", body: { code: code.value } });
        st = { ...st, ...done.status };
        showCodes(panel, done.codes);
        draw();
      } catch (err) { setError(code, err.message); code.focus(); }
    });
  }

  // Shown once; the server keeps only hashes.
  function showCodes(panel, codes) {
    const text = codes.join("\n");
    const list = el("ul", { class: "recovery-codes", "aria-label": "Recovery codes" }, codes.map((c) => el("li", {}, el("code", { text: c }))));
    const done = el("button", { type: "button", class: "btn btn--primary", text: "I have saved them" });
    done.addEventListener("click", () => { panel.close(); showSaved("totp-saved", "Two-step code activated"); });
    panel.setTitle("Save your recovery codes");
    panel.body.replaceChildren(
      notice("warning", "Save these now", "Starboard shows them only this once. Each works once, if you lose your phone. Keep them somewhere safe, such as a password manager."),
      list, el("div", { class: "actions" }, el("button", { type: "button", class: "btn", onclick: async () => { const ok = await copyText(text); (ok ? toast : problem)(ok ? "Copied the recovery codes" : "Could not copy them"); } }, icon("copy"), "Copy all the codes")));
    panel.setFoot([done]);
    done.focus();
  }

  async function newCodes(opener) {
    const code = el("input", { class: "input", id: "new-codes-code", inputmode: "numeric", autocomplete: "one-time-code", maxlength: "8" });
    const r = await askPassword({ title: "Make new recovery codes?", message: "The old codes stop working. Starboard asks for a code from the app, to be sure it is you.", confirm: "Make new codes",
      extra: [{ input: code, node: el("div", { class: "field" }, el("label", { for: code.id, text: "Code from the app" }), code) }] });
    if (!r) return;
    try {
      const done = await api("/api/security/totp/recovery", { method: "POST", body: { password: r.password, code: r.extra[0] } });
      st = { ...st, ...done.status };
      const panel = sidePanel({ title: "Save your recovery codes", opener, body: [el("div")], foot: [] });
      showCodes(panel, done.codes);
      draw();
    } catch (e) { problem(e.message, opener); }
  }

  // Single sign-on ---------------------------------------------------------------------------------------------
  function ssoSection() {
    const o = st.oidc;
    const state = headChip(o.enabled ? "On" : o.configured ? "Set up, not on" : "Off", o.enabled ? "success" : "muted");
    const f = {
      name: el("input", { class: "input", id: "sso-name", value: o.name || "", maxlength: "40", autocomplete: "off", placeholder: "Authentik" }),
      issuer: el("input", { class: "input", id: "sso-issuer", value: o.issuer, autocomplete: "off", spellcheck: "false", placeholder: "https://auth.example.org/application/o/starboard/" }),
      client_id: el("input", { class: "input", id: "sso-client", value: o.client_id, autocomplete: "off", spellcheck: "false" }),
      client_secret: el("input", { class: "input", id: "sso-secret", type: "password", autocomplete: "new-password", placeholder: o.has_secret ? "Kept. Leave blank to keep it" : "" }),
      redirect_uri: el("input", { class: "input", id: "sso-redirect", value: o.redirect_uri || base(), autocomplete: "off", spellcheck: "false" }),
      claim: el("select", { class: "select", id: "sso-claim" }, [["email", "A verified email address"], ["preferred_username", "Username (preferred_username)"], ["sub", "Subject (sub)"], ["other", "Another claim"]].map(([v, t]) => el("option", { value: v, text: t }))),
      other: el("input", { class: "input", id: "sso-other", autocomplete: "off", spellcheck: "false", placeholder: "groups" }),
      value: el("input", { class: "input", id: "sso-value", value: o.value, autocomplete: "off", spellcheck: "false" }),
    };
    const known = ["email", "preferred_username", "sub"];
    f.claim.value = known.includes(o.claim) ? o.claim : "other";
    f.other.value = known.includes(o.claim) ? "" : o.claim;
    const otherField = field("Claim name", f.other, { hint: "The name of the claim in the ID token. A list, such as groups, matches when it holds the value." });
    otherField.hidden = f.claim.value !== "other";
    f.claim.addEventListener("change", () => { otherField.hidden = f.claim.value !== "other"; });
    const form = el("form", { class: "form-stack", id: "sso-form", novalidate: true },
      field("Name on the sign-in button", f.name, { hint: "For example Authentik, Authelia, Keycloak or Google." }),
      field("Issuer address", f.issuer, { hint: "The OpenID Connect issuer of your provider. It must start with https://, because anyone on a network could answer for a provider on http:// and sign in as you. Starboard reads its description from there." }),
      field("Client ID", f.client_id),
      field("Client secret", f.client_secret, { hint: "Kept on this server like an app's key, and never shown again. If you change the issuer address, enter the secret again: the saved one is never given to a different provider." }),
      field("Redirect address", f.redirect_uri, { hint: "Give your provider exactly this address as the redirect (callback) address. Starboard sends people nowhere else." }),
      field("Who may sign in", f.claim, { hint: "Starboard has one account. Choose how it recognises you in the provider's ID token. A verified email address is the strongest choice, and so is the subject (sub). A username or another claim is weaker: a provider may let people choose it for themselves." }),
      otherField,
      field("The value that is you", f.value, { hint: "For a verified email, your address. The provider must say it has checked it." }));
    const save = el("button", { type: "submit", class: "btn btn--primary", text: "Save and check the provider" });
    form.append(el("div", { class: "actions" }, save, savedNote("sso-saved")));
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const r = await askPassword({ title: "Save single sign-on", message: "Saving turns single sign-on off until you have tested it again.", confirm: "Save" });
      if (!r) return;
      try {
        st = { ...st, ...(await api("/api/security/oidc/save", { method: "POST", body: {
          password: r.password, name: f.name.value, issuer: f.issuer.value, client_id: f.client_id.value, client_secret: f.client_secret.value,
          redirect_uri: f.redirect_uri.value, claim: f.claim.value === "other" ? f.other.value : f.claim.value, value: f.value.value } })) };
        draw();
        showSaved("sso-saved", "Saved. The provider answered");
      } catch (err) { problem(err.message, save); }
    });
    const parts = [state, form];
    if (o.configured) {
      const test = el("a", { class: "btn", href: "/api/oidc/start?test=1" }, icon("key-round"), "Test sign-in");
      const allow = el("input", { type: "checkbox", role: "switch", id: "sso-on", checked: o.enabled, "aria-labelledby": "sso-on-l", "aria-describedby": "sso-on-h" });
      if (!o.tested && !o.enabled) allow.setAttribute("aria-disabled", "true");
      allow.addEventListener("change", async () => {
        const want = allow.checked;
        if (want && !o.tested) { allow.checked = false; problem("Run the test sign-in first. It must work before you turn this on", allow); return; }
        allow.checked = !want;
        const r = await askPassword({ title: want ? "Allow single sign-on?" : "Deactivate single sign-on?", confirm: want ? "Allow" : "Deactivate", danger: !want,
          message: want ? "The sign-in page then offers a button for your provider, beside the password." : "The button goes. The password works again, even if you had deactivated it." });
        if (!r) { allow.focus(); return; }
        try { st = { ...st, ...(await api("/api/security/oidc/enable", { method: "POST", body: { password: r.password, enabled: want } })) }; draw(); showSaved("sso-saved", want ? "Single sign-on is on" : "Single sign-on is off"); }
        catch (err) { problem(err.message, allow); }
      });
      const remove = el("button", { type: "button", class: "btn btn--danger" }, icon("trash-2"), "Remove single sign-on");
      remove.addEventListener("click", async () => {
        const r = await askPassword({ title: "Remove single sign-on?", message: "Starboard forgets the provider and the client secret. The password works again.", confirm: "Remove", danger: true });
        if (!r) return;
        try { st = { ...st, ...(await api("/api/security/oidc/remove", { method: "POST", body: { password: r.password } })) }; draw(); showSaved("sso-saved", "Single sign-on removed"); }
        catch (err) { problem(err.message, remove); }
      });
      parts.push(el("ul", { class: "settings-rows" },
        settingRow("Test sign-in", el("span", { id: "sso-test-h", text: o.tested ? "The last test worked." : "Sends you to your provider and back, to check every step. It does not sign anyone in." }), el("div", { class: "actions" }, test), "sso-test-l"),
        settingRow("Allow single sign-on", el("span", { id: "sso-on-h", text: "Shows a button on the sign-in page. Needs a working test first." }), el("label", { class: "switch" }, allow), "sso-on-l")),
        el("div", { class: "actions" }, remove));
    }
    return section("sc-sso", "Single sign-on", "Sign in with your own identity provider (OpenID Connect), such as Authentik, Authelia, Keycloak or Google. Off until you set it up and test it. It does not ask for Starboard's two-step code: your provider's own checks apply.", ...parts);
  }

  // Password sign-in -------------------------------------------------------------------------------------------
  function passwordSection() {
    const on = st.password_login;
    const sw = el("input", { type: "checkbox", role: "switch", id: "pw-on", checked: on, "aria-labelledby": "pw-on-l", "aria-describedby": "pw-on-h" });
    sw.addEventListener("change", async () => {
      const want = sw.checked;
      sw.checked = !want;
      const r = await askPassword({ title: want ? "Allow the password again?" : "Deactivate password sign-in?", confirm: want ? "Allow the password" : "Deactivate password sign-in", danger: !want,
        message: want ? "The sign-in page shows the password form again." : "Only single sign-on opens Starboard after this. If it ever stops working, run ./reset-sign-in.sh on the server." });
      if (!r) { sw.focus(); return; }
      try { st = { ...st, ...(await api("/api/security/password-login", { method: "POST", body: { password: r.password, allowed: want } })) }; draw(); showSaved("pw-saved", want ? "Password sign-in is on" : "Password sign-in is off"); }
      catch (err) { problem(err.message, sw); }
    });
    const can = st.oidc.enabled && st.oidc.tested;
    return section("sc-pwoff", "Password sign-in", "The password works unless you deactivate it on purpose. You can only do that once single sign-on is on and its test worked.",
      el("ul", { class: "settings-rows" }, settingRow("Allow signing in with the password",
        el("span", { id: "pw-on-h", text: can || !on ? "Single sign-on is set up, so you may turn this off." : "Activate and test single sign-on first." }), el("label", { class: "switch" }, sw), "pw-on-l")),
      el("div", { class: "actions" }, savedNote("pw-saved")));
  }

  // The way back in ---------------------------------------------------------------------------------------------
  function reachSection() {
    const cmd = "./reset-sign-in.sh";
    return section("sc-reach", "If you are locked out", "On the server, in the Starboard folder, one command deactivates the two-step code and single sign-on and allows the password again. It signs everyone out, and keeps your password, apps and settings.",
      el("div", { class: "command" }, el("code", { class: "code-block", text: cmd }), copyButton(cmd, "the command")));
  }

  draw();
  const result = new URLSearchParams(location.search).get("sso");
  if (SSO_WHY[result]) {
    const [tone, title, text] = SSO_WHY[result];
    holder.prepend(notice(tone, title, text));
    history.replaceState(null, "", location.pathname);
  }
}
