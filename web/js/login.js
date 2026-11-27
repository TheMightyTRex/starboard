// Sign in, or choose the first password with the set-up code. Errors show under the field they are about.

function showFieldError(input, message) {
  const error = $(`#${input.id}-error`);
  const hint = $(`#${input.id}-hint`);
  if (!error) return false;
  errorWords(error, message);
  error.hidden = false;
  input.setAttribute("aria-invalid", "true");
  input.setAttribute("aria-describedby", [hint?.id, error.id].filter(Boolean).join(" "));
  input.focus();
  return true;
}

function clearErrors(form) {
  $$(".field-error", form).forEach((n) => { n.hidden = true; n.replaceChildren(); });
  $$("[aria-invalid]", form).forEach((input) => {
    input.removeAttribute("aria-invalid");
    const hint = $(`#${input.id}-hint`);
    if (hint) input.setAttribute("aria-describedby", hint.id); else input.removeAttribute("aria-describedby");
  });
}

function showFormError(message) {
  const box = $("#auth-error");
  errorWords(box, message);
  box.hidden = false;
}

startPage().then((session) => {
  const form = $("#login-form");
  const setup = form.dataset.mode === "setup";
  if (session && setup && !session.needs_setup) location.replace("/login.html");
  if (session && !setup && session.needs_setup) location.replace("/setup.html");
  if (session && session.signed_in) location.replace("/dashboard.html");
  if (setup && session && form.site_name && !form.site_name.value) form.site_name.value = session.site_name;
  // get-starboard.sh opens this page with the code after #, which never leaves the browser; fill it in, then
  // take it out of the address bar.
  const given = /^#code=([A-Za-z0-9_-]{4,64})$/.exec(location.hash);
  if (given) {
    if (setup && form.token) {
      // Filled in by the installer's link: read only, with a note, and the cursor goes to the next question.
      form.token.value = given[1];
      form.token.readOnly = true;
      $("#token-hint").textContent = "Filled in by the installer. Starboard uses it automatically to continue the set-up, so there is nothing to enter here.";
      form.site_name?.focus();
    }
    history.replaceState(null, "", location.pathname + location.search);
  }
  // Single sign-on (DASH-512): a button when the owner has turned it on, and no password form if the password is off.
  if (!setup && session) {
    const sso = $("#sso");
    if (session.sso) {
      sso.hidden = false;
      $("#sso-label").textContent = `Sign in with ${session.sso.name}`;
      $("#sso-link").addEventListener("click", (ev) => {
        ev.preventDefault();  // the box is passed on in the address, never the password
        const q = $("#remember").checked ? "?remember=1" : "";
        location.href = `/api/oidc/start${q}`;
      });
    }
    if (session.password_login === false) {
      form.hidden = true;
      sso.hidden = false;
      $("#sso-off-note").hidden = false;
    } else if (session.sso) {
      $("#sso-or").hidden = false;
    }
    const why = { failed: "Single sign-on did not work. Try again, or sign in with your password.", nomatch: "That account is not the one allowed to sign in to this dashboard.",
      denied: "Single sign-on was cancelled or refused by the provider.", expired: "That sign-in ran out of time. Try again.", limited: "Too many attempts. Wait 15 minutes and try again.",
      off: "Single sign-on is not activated." }[new URLSearchParams(location.search).get("sso")];
    if (why) { showFormError(why); }
  }
  const codeForm = $("#code-form");
  codeForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearErrors(codeForm);
    const input = $("#code");
    if (!input.value.trim()) { showFieldError(input, "Enter the code from your authenticator app, or a recovery code"); return; }
    const button = $("button[type=submit]", codeForm);
    button.disabled = true;
    try {
      await api("/api/login/code", { method: "POST", body: { challenge: codeForm.dataset.challenge, code: input.value } });
      goOn();
    } catch (err) {
      if (/password again/i.test(err.message)) {  // the password step ran out: back to the start
        codeForm.hidden = true;
        form.hidden = false;
        form.password.value = "";
        showFieldError(form.password, err.message);
      } else showFieldError(input, err.message);
      input.value = "";
    } finally {
      button.disabled = false;
    }
  });
  // Only a page on this dashboard: the address is resolved first, so tricks like "/\t/evil.example" fail.
  const goOn = () => {
    let next = "/dashboard.html";
    try {
      const asked = new URL(new URLSearchParams(location.search).get("next") || "/dashboard.html", location.origin);
      if (asked.origin === location.origin) next = asked.pathname + asked.search + asked.hash;
    } catch { /* not an address: go to Apps */ }
    location.href = next;
  };
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearErrors(form);
    if (setup) {
      if (!form.token.value.trim()) { showFieldError(form.token, "Enter the set-up code. It is in the installer's output or the server log."); return; }
      if (!form.site_name.value.trim()) { showFieldError(form.site_name, "Enter a name for the dashboard"); return; }
      if (form.password.value.length < 10) { showFieldError(form.password, `Use at least 10 characters. This one has ${form.password.value.length}.`); return; }
      if (form.password.value !== form.confirm.value) { showFieldError(form.confirm, "The two passwords are different. Enter it again."); return; }
    } else if (!form.password.value) {
      showFieldError(form.password, "Enter your password");
      return;
    }
    const button = $("button[type=submit]", form);
    button.disabled = true;
    try {
      let answer = null;
      if (setup) await api("/api/setup", { method: "POST", body: { token: form.token.value, password: form.password.value, remember: form.remember.checked, site_name: form.site_name.value } });
      else answer = await api("/api/login", { method: "POST", body: { password: form.password.value, remember: form.remember.checked } });
      if (setup) { location.href = "/setup-guide.html"; return; }  // set-up goes on to the guide: find apps, choose what runs
      if (answer?.needs_code) {  // the password was right; the second step is next, in the same place
        form.hidden = true;
        $("#sso").hidden = true;
        form.password.value = "";
        codeForm.dataset.challenge = answer.challenge;
        codeForm.hidden = false;
        announce("Password accepted. Enter your two-step code.");
        $("#code").focus();
        return;
      }
      goOn();
    } catch (err) {
      const m = err.message;
      if (!setup) showFieldError(form.password, /not right/i.test(m) ? "That password is not right. Check Caps Lock and try again." : m);
      else if (/set-?up code/i.test(m)) {
        // A code from the link that is refused (an old link, say) can be typed instead.
        if (form.token.readOnly) { form.token.readOnly = false; $("#token-hint").textContent = "In the installer's output, or run docker compose logs starboard on the server."; }
        showFieldError(form.token, m);
      }
      else if (/name/i.test(m)) showFieldError(form.site_name, m);
      else if (/password is already set/i.test(m)) showFormError(m);
      else if (/password|characters/i.test(m)) showFieldError(form.password, m);
      else showFormError(m);
    } finally {
      button.disabled = false;
    }
  });
});
