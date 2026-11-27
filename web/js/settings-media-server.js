// Settings, Apps, the media server tab (DASH-565; side by side, DASH-586): the tab is named for the media server in use (Jellyfin, Plex or Emby; Media
// server when there is none). It says whether it is set up, has a check that it answers, the choice of another one or none
// and the way back for 24 hours. Starboard never switches by itself; a new choice is checked first. Jellyfin's own sections
// (settings-jellyfin.js) draw above these while Jellyfin is in use; Plex and Emby have their address and token in Manage apps.

const HOURS = (until) => Math.max(1, Math.ceil((until - Date.now() / 1000) / 3600));

async function startMediaServer() {
  const root = $("#media-server-sections");
  let ms;
  try { ms = await api("/api/media-server"); } catch (e) { root.replaceChildren(notice("danger", "Could not load the media server", e.message)); return; }
  root.removeAttribute("aria-busy");
  const name = ms.name || "Media server";
  const title = $("#ms-title");
  if (title) title.textContent = name;
  document.title = document.title.replace(/^[^·]*/, `${name} `);
  const summary = $("#ms-summary");
  if (summary) summary.textContent = ms.active === "jellyfin" ? "Live TV, moving your watch history to Jellyfin, defaults for every user, and which media server Starboard uses."
    : ms.active ? `${name} is the media server Starboard shows on the dashboard, in Library, in Activity and in System. Choose another one under Choose a media server, or check that ${name} answers.`
      : "No media server is in use. Choose one under Choose a media server: Starboard shows the one you choose on the dashboard, in Library, in Activity and in System.";
  const said = el("div", { class: "stack-2", role: "status", "aria-live": "polite", id: "ms-said", tabindex: "-1" });
  const say = (kind, title, text, ...more) => { said.replaceChildren(notice(kind, title, text), ...more.filter(Boolean)); };
  const current = ms.available.find((a) => a.id === ms.active);

  // A part of the one section: its own heading and words (an h3, whose id a link or a test can name).
  const part = (id, title, text, ...content) => el("div", { class: "stack-2", "data-part": id },
    el("h3", { id: `${id}-h`, text: title }), text ? el("p", { class: "small muted", text }) : null, ...content);

  // In use ----------------------------------------------------------------------------------------------------------
  const check = el("button", { type: "button", class: "btn", disabled: !current }, icon("activity"), "Check it now",
    current ? el("span", { class: "visually-hidden", text: ` ${current.name}` }) : null);
  check.addEventListener("click", async () => {
    check.disabled = true;
    say("info", "Checking…", `Asking ${current.name} to answer.`);
    try {
      const r = await api("/api/media-server/check", { method: "POST", body: { id: ms.active } });
      say(r.ok ? "success" : "warning", r.ok ? `${r.name} answered` : `${r.name} did not answer`, r.said);
    } catch (err) { say("danger", "The check did not run", err.message); }
    finally { check.disabled = false; check.focus(); }
  });
  const using = part("ms-use", "In use", current
    ? `${current.name} is your media server. ${ms.configured ? "It is set up." : "It is not set up yet: add its address and key in Settings, Manage apps."}`
    : "No media server is in use. The dashboard panel, Library's Play and Watched and Activity's now playing are not drawn until you choose one.",
    el("p", {}, chip(...(current ? (ms.configured ? ["In use", "success", "circle-check"] : ["Not set up", "warning", "triangle-alert"]) : ["None", "muted", "minus"]))),
    el("div", { class: "actions" }, check),
    said);

  // Its own settings: Jellyfin has its sections above; Plex and Emby keep their address and token in Manage apps ------------
  let own = null;
  if (current && ms.active !== "jellyfin") {
    const app = (typeof config !== "undefined" && config?.services || []).find((s) => s.type === ms.active);
    own = part("ms-own", `Your ${current.name}`, app
      ? `${current.name} is kept in Manage apps as ${app.name}, with its address and ${ms.active === "plex" ? "token" : "key"}. The key is never shown again after saving.`
      : `${current.name} is not in Manage apps yet. Add it with its address and ${ms.active === "plex" ? "token" : "key"} so Starboard can ask it for its libraries, what is playing and what was added.`,
      el("div", { class: "actions" }, app
        ? el("a", { class: "btn", href: `/settings.html?edit=${encodeURIComponent(app.id)}` }, icon("pencil"), `Edit ${app.name}`)
        : el("a", { class: "btn btn--primary", href: `/settings.html?add=${encodeURIComponent(ms.active)}` }, icon("plus"), `Add ${current.name}`)),
      el("p", { class: "small muted", text: `Play, Watched, Live TV and the other Jellyfin tools stay with Jellyfin: ${current.name} is read only for now.` }));
  }

  // Side by side (DASH-586): Jellyfin, Plex and Emby can all be installed to try. One is in use; each of the others is "installed, not in
  // use" once it is set up, and can be checked here without switching. One that is not installed links to Install apps.
  const stateOf = (a) => a.id === ms.active ? ["In use", "success", "circle-check"]
    : a.set_up ? ["Installed, not in use", "info", "circle-check"]
      : a.has_app ? ["Added, not set up", "warning", "triangle-alert"] : ["Not installed", "muted", "minus"];
  const sideRows = ms.available.map((a) => {
    const [words, tone, ic] = stateOf(a);
    const row = el("li", { class: "row", "data-server": a.id }, el("div", { class: "row__main" },
      el("strong", { class: "row__title", text: a.name }), el("div", {}, chip(words, tone, ic)),
      el("span", { class: "small muted", text: a.id === ms.active ? "Starboard shows this one on the dashboard, in Library, in Activity and in System."
        : a.set_up ? "Starboard asks it nothing until you use it, so it costs your computer only what the server itself uses."
          : a.has_app ? `Add its ${a.id === "plex" ? "token" : "key"} in Manage apps so Starboard can ask it to answer.` : "Add it from Install apps, or add one you already run in Manage apps." })));
    const acts = el("div", { class: "actions" });
    if (a.set_up && a.id !== ms.active) {
      const b = el("button", { type: "button", class: "btn" }, icon("activity"), "Check it now", el("span", { class: "visually-hidden", text: ` ${a.name}` }));
      b.addEventListener("click", async () => {
        b.disabled = true;
        say("info", "Checking…", `Asking ${a.name} to answer. Nothing changes.`);
        try { const r = await api("/api/media-server/check", { method: "POST", body: { id: a.id } }); say(r.ok ? "success" : "warning", r.ok ? `${r.name} answered` : `${r.name} did not answer`, r.said); }
        catch (err) { say("danger", "The check did not run", err.message); } finally { b.disabled = false; b.focus(); }
      });
      acts.append(b);
    } else if (!a.has_app) {
      acts.append(el("a", { class: "btn", href: "/install-apps.html" }, icon("plus"), `Install ${a.name}`, el("span", { class: "visually-hidden", text: " with Starboard" })));
    } else if (!a.set_up) {
      acts.append(el("a", { class: "btn", href: `/settings.html?edit=${encodeURIComponent((config?.services || []).find((s) => s.type === a.id)?.id || "")}` }, icon("pencil"), `Edit ${a.name}`));
    }
    row.append(acts);
    return row;
  });
  const side = part("ms-side", "Installed side by side", "You can run Jellyfin, Plex and Emby together to try them. Only one is in use at a time.", el("ul", { class: "rows" }, sideRows));

  // Choose ----------------------------------------------------------------------------------------------------------
  const options = [...ms.available.map((a) => ({ id: a.id, name: a.name, added: ms.added.includes(a.id) })), { id: "", name: "None", added: true }];
  const radios = options.map((o) => ({ o, input: el("input", { type: "radio", name: "ms-choice", value: o.id, id: `ms-choice-${o.id || "none"}`, checked: o.id === ms.active, disabled: !o.added }) }));
  const note = (o) => o.id === "" ? "Starboard draws no media server panel. Nothing is removed: the one you had stays added."
    : !o.added ? `${o.name} is not added yet. Add it from the catalogue's Media servers first.`
    : o.id === ms.active ? "In use now." : `Starboard asks ${o.name} to answer first. If it does not, nothing changes.`;
  const choose = el("button", { type: "submit", class: "btn btn--primary", text: "Use this media server" });
  const form = el("form", { class: "form-stack", novalidate: true },
    el("fieldset", { class: "stack-2" }, el("legend", { text: "Media server to use" }),
      el("div", { class: "option-cards" }, radios.map(({ o, input }) => el("label", { class: "option-card", for: input.id }, input,
        el("strong", { text: o.name }), el("small", { text: note(o) }))))),
    el("div", { class: "actions" }, choose));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const picked = radios.find((r) => r.input.checked)?.o;
    if (!picked || picked.id === ms.active) { say("info", "Nothing to change", `${picked ? picked.name : "That choice"} is already in use.`); return; }
    const ok = await confirmDialog({ title: picked.id ? `Use ${picked.name}?` : "Use no media server?", confirm: picked.id ? `Use ${picked.name}` : "Use none",
      message: picked.id ? `Starboard checks that ${picked.name} answers first. ${current ? `${current.name} stays added, and you can go back to it for 24 hours.` : ""}`
        : `${current ? current.name : "The media server"} stays added, and you can go back to it for 24 hours.` });
    if (!ok) { radios.find((r) => r.o.id === ms.active)?.input.focus(); return; }
    choose.disabled = true;
    try {
      const r = await api("/api/media-server/choose", { method: "POST", body: { id: picked.id } });
      announce(r.said);
      await startMediaServer();
      $("#ms-said")?.replaceChildren(notice("success", "Changed", r.said));
      $("#ms-said")?.focus();  // focus goes to what was said, not back to the top of the page
    } catch (err) { say("warning", "Nothing changed", err.message); choose.disabled = false; choose.focus(); }
  });
  // Switch with help: the wizard that says what would move, what cannot and what waits, before anything changes.
  const wizard = el("button", { type: "button", class: "btn" }, icon("arrow-up-down"), "Switch with help");
  wizard.addEventListener("click", () => openSwitchWizard(ms, wizard, async (words) => {
    await startMediaServer();
    $("#ms-said")?.replaceChildren(notice("success", "Changed", words));
    $("#ms-said")?.focus();
  }));
  const pick = part("ms-choose", "Choose a media server", "Starboard checks a media server before it uses it, never switches by itself and keeps the one you had added.", form,
    el("p", { class: "small muted", text: "Moving over from another media server? The wizard lists what moves, what cannot, and which plug-ins and apps need attention first." }), el("div", { class: "actions" }, wizard));

  // The way back -----------------------------------------------------------------------------------------------------
  let back = null;
  if (ms.back) {
    const go = el("button", { type: "button", class: "btn" }, icon("undo-2"), ms.back.id ? `Go back to ${ms.back.name}` : "Go back to no media server");
    go.addEventListener("click", async () => {
      go.disabled = true;
      try { const r = await api("/api/media-server/back", { method: "POST" }); announce(r.said); await startMediaServer(); $("#ms-said")?.replaceChildren(notice("success", "Changed back", r.said)); $("#ms-said")?.focus(); }
      catch (err) { say("danger", "It did not change back", err.message); go.disabled = false; go.focus(); }
    });
    back = part("ms-back", "The way back", `You changed your media server. For about ${HOURS(ms.back.until)} more ${HOURS(ms.back.until) === 1 ? "hour" : "hours"} you can go back to ${ms.back.name || "no media server"} in one step.`,
      el("div", { class: "actions" }, go));
  }
  root.replaceChildren(section("ms-section", "Media server", "The media server Starboard shows on the dashboard, in Library, in Activity and in System. Starboard uses one at a time.",
    ...[using, own, side, pick, back].filter(Boolean)));
}

