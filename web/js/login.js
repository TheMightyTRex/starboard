// Sign in, or choose the first password with the setup code. Errors show under the field they are about.

function showFieldError(input, message) {
  const error = $(`#${input.id}-error`);
  const hint = $(`#${input.id}-hint`);
  if (!error) return false;
  error.replaceChildren(icon("circle-alert"), el("span", { text: message }));
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
  box.replaceChildren(icon("circle-alert"), el("span", { text: message }));
  box.hidden = false;
}

startPage().then((session) => {
  const form = $("#login-form");
  const setup = form.dataset.mode === "setup";
  if (session && setup && !session.needs_setup) location.replace("/login.html");
  if (session && !setup && session.needs_setup) location.replace("/setup.html");
  if (session && session.signed_in) location.replace("/index.html");
  if (setup && session && form.site_name && !form.site_name.value) form.site_name.value = session.site_name;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearErrors(form);
    if (setup) {
      if (!form.token.value.trim()) { showFieldError(form.token, "Enter the setup code. It is in the installer's output or the server log."); return; }
      if (!form.site_name.value.trim()) { showFieldError(form.site_name, "Enter a name for the dashboard"); return; }
      if (form.password.value.length < 10) { showFieldError(form.password, `Use at least 10 characters. This one has ${form.password.value.length}.`); return; }
      if (form.password.value !== form.confirm.value) { showFieldError(form.confirm, "The two passwords are different. Type it again."); return; }
    } else if (!form.password.value) {
      showFieldError(form.password, "Enter your password");
      return;
    }
    const button = $("button[type=submit]", form);
    button.disabled = true;
    try {
      if (setup) await api("/api/setup", { method: "POST", body: { token: form.token.value, password: form.password.value, remember: form.remember.checked, site_name: form.site_name.value } });
      else await api("/api/login", { method: "POST", body: { password: form.password.value, remember: form.remember.checked } });
      if (setup) { location.href = "/setup-guide.html"; return; }  // set-up goes on to the guide: find apps, choose what runs
      // Only a page on this dashboard: the address is resolved first, so tricks like "/\t/evil.example" fail.
      let next = "/index.html";
      try {
        const asked = new URL(new URLSearchParams(location.search).get("next") || "/index.html", location.origin);
        if (asked.origin === location.origin) next = asked.pathname + asked.search + asked.hash;
      } catch { /* not an address: go to Apps */ }
      location.href = next;
    } catch (err) {
      const m = err.message;
      if (!setup) showFieldError(form.password, /not right/i.test(m) ? "That password is not right. Check Caps Lock and try again." : m);
      else if (/setup code/i.test(m)) showFieldError(form.token, m);
      else if (/name/i.test(m)) showFieldError(form.site_name, m);
      else if (/password is already set/i.test(m)) showFormError(m);
      else if (/password|characters/i.test(m)) showFieldError(form.password, m);
      else showFormError(m);
    } finally {
      button.disabled = false;
    }
  });
});
