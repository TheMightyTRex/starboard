// Settings, Apps, Reelix.

// Settings, Reelix: which version runs, and switching either way (stack.switch_reelix). Both versions use the same
// settings folder, so the library, users and settings stay. Reelix's own settings are in reelix-settings.js.
async function startReelix() {
  const root = $("#reelix-sections");
  let d;
  try { d = await api("/api/reelix/editions"); } catch (e) { root.replaceChildren(notice("danger", "Could not read the Reelix versions", e.message)); root.removeAttribute("aria-busy"); return; }
  const names = Object.fromEntries(d.editions.map((e) => [e.key, e.name]));
  const status = el("div", { class: "stack-2", "aria-live": "polite" });
  let body;
  if (!d.can_switch) {
    body = [notice("info", "Reelix was not installed here by Starboard",
      "Starboard switches the version only for a Reelix that Install apps set up. For your own Reelix, change its image in your Compose file: ghcr.io/themightytrex/reelix:lite, or ghcr.io/themightytrex/reelix:full for YouTube and Spotify downloads.")];
  } else {
    let want = d.editions.find((e) => e.key !== d.current && e.available)?.key || "";
    const now = el("strong", { text: names[d.current] || d.image });
    const cards = el("fieldset", {}, el("legend", { class: "visually-hidden", text: "Version" }),
      el("div", { class: "option-cards" }, d.editions.map((e) => {
        const radio = el("input", { type: "radio", name: "reelix-edition", value: e.key, checked: e.key === d.current, disabled: !e.available && e.key !== d.current });
        radio.addEventListener("change", () => { want = e.key; button.textContent = `Switch to ${names[e.key]}`; button.disabled = e.key === d.current; });
        const note = e.key === d.current ? "In use now" : !e.available ? "Cannot be downloaded at the moment" : e.recommended ? "Recommended" : "";
        return el("label", { class: "option-card" }, radio, el("strong", { text: e.name }), el("small", { text: e.about }), el("small", { class: "muted", text: note }));
      })));
    const password = el("input", { class: "input", type: "password", autocomplete: "current-password", required: true });
    const button = el("button", { type: "submit", class: "btn btn--primary", text: "Switch", disabled: true });
    const form = el("form", { novalidate: true }, el("div", { class: "form-stack" }, cards,
      field("Your password", password, { required: true, hint: "Switching downloads the other version and restarts Reelix, which takes a minute or two." })),
      el("div", { class: "actions" }, button));
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      setError(password, "");
      if (!want || want === d.current) return;
      if (!password.value) { setError(password, "Enter your password"); password.focus(); return; }
      button.disabled = true;
      status.replaceChildren(el("p", { class: "muted", text: `Switching to ${names[want]}…` }));
      let r;
      try { r = await api("/api/reelix/edition", { method: "POST", body: { edition: want, password: password.value } }); }
      catch (err) {
        button.disabled = false;
        status.replaceChildren();
        if (err.status === 401 || err.status === 429) { setError(password, err.message); password.focus(); }
        else status.replaceChildren(notice("danger", "Reelix was not switched", err.message));
        return;
      }
      password.value = "";
      d.current = want;
      now.textContent = names[want];
      $$("[name=reelix-edition]").forEach((x) => { x.closest("label").querySelector("small.muted").textContent = x.value === want ? "In use now" : ""; });
      if (!r.started) {
        status.replaceChildren(notice("info", "One step on the server", "Starboard changed Reelix's version but cannot start apps itself. Run this in a terminal on the server:"),
          el("pre", { class: "code-block", text: r.command }), copyButton(r.command, "Copy the command"));
        return;
      }
      for (;;) {
        await new Promise((res) => setTimeout(res, 3000));
        const j = await api("/api/stack/job").catch(() => ({}));
        if (!j.finished) continue;
        status.replaceChildren(j.ok ? notice("success", `${names[want]} is running`, "Your library, users and settings are as they were.")
          : notice("danger", "Reelix did not start", "The details follow. The old Compose file is kept in data/stack, next to the new one."),
        j.ok ? "" : el("pre", { class: "code-block", text: j.log || "" }));
        if (j.ok) setTimeout(() => startReelix(), 1500);
        return;
      }
    });
    body = [el("p", {}, "Now: ", now), form];
  }
  // A set-up that did not finish (8 November 2026): Reelix's admin account, Starboard's key, folders and download
  // apps, made with the same password as Starboard (reelix_setup.set_up, /api/reelix/setup).
  const setupParts = [];
  if (d.needs_setup) {
    const pw = el("input", { class: "input", type: "password", autocomplete: "current-password", required: true });
    const go = el("button", { type: "submit", class: "btn btn--primary", text: "Finish setting up Reelix" });
    const said = el("div", { class: "stack-2", "aria-live": "polite" });
    const form = el("form", { novalidate: true }, el("div", { class: "form-stack" },
      field("Your password", pw, { required: true, hint: "Reelix's admin account gets the same password as Starboard, so one password opens both. It is used for this and not kept." })),
      el("div", { class: "actions" }, go));
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      setError(pw, "");
      if (!pw.value) { setError(pw, "Enter your password"); pw.focus(); return; }
      go.disabled = true;
      said.replaceChildren(el("p", { class: "muted", text: "Setting up Reelix…" }));
      let r;
      try { r = await api("/api/reelix/setup", { method: "POST", body: { password: pw.value } }); }
      catch (err) {
        go.disabled = false; said.replaceChildren();
        if (err.status === 401 || err.status === 429) { setError(pw, err.message); pw.focus(); }
        else said.replaceChildren(notice("danger", "Reelix is not set up yet", err.message));
        return;
      }
      pw.value = "";
      said.replaceChildren(notice("success", "Reelix is set up", (r.done || []).join(". ")));
      announce("Reelix is set up");
      setTimeout(() => startReelix(), 4000);
    });
    setupParts.push(section("rx-setup", "Finish setting up Reelix", "Reelix runs, but its set-up did not finish: its admin account, Starboard's key, its folders and its download apps.",
      form, said));
  }
  root.replaceChildren(...setupParts,
    section("rx-version", "Version", "Which Reelix runs is part of your install: change it, and the rest of your install, on Settings, Your install.",
      el("p", {}, "Now: ", el("strong", { text: names[d.current] || d.image || "Not installed by Starboard" })),
      el("div", { class: "actions" }, el("a", { class: "btn", href: "/settings-install.html" }, icon("layers"), "Open Your install"))),
    reelixAdminSections());  // sites to search, media servers and download apps (reelix-settings.js)
  root.removeAttribute("aria-busy");
}
