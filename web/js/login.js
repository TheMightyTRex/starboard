// Sign in, or choose the first password with the setup code.

startPage().then((session) => {
  const form = $("#login-form");
  const setup = form.dataset.mode === "setup";
  if (session && setup && !session.needs_setup) location.replace("/login.html");
  if (session && !setup && session.needs_setup) location.replace("/setup.html");
  if (session && session.signed_in) location.replace("/index.html");
  if (setup && session && form.site_name && !form.site_name.value) form.site_name.value = session.site_name;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const error = $("#auth-error");
    error.textContent = "";
    if (setup && form.password.value !== form.confirm.value) { error.textContent = "The two passwords are different"; return; }
    const button = $("button[type=submit]", form);
    button.disabled = true;
    try {
      if (setup) await api("/api/setup", { method: "POST", body: { token: form.token.value, password: form.password.value, remember: form.remember.checked, site_name: form.site_name.value } });
      else await api("/api/login", { method: "POST", body: { password: form.password.value, remember: form.remember.checked } });
      const next = new URLSearchParams(location.search).get("next") || "/index.html";
      location.href = /^\/(?![/\\])/.test(next) ? next : "/index.html";
    } catch (err) {
      error.textContent = err.message;
      form.password.focus();
    } finally {
      button.disabled = false;
    }
  });
});
