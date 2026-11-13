// Settings, Radio (owner, 12 November 2026): where radio programmes come from (Reelix's sources, behind its admin
// password), and the station logos you added. More sources and a search by genre follow in Reelix (RFX-93 onwards).

function radioSourcesSection() {
  const body = el("div", { class: "stack-4" });
  const unlock = () => el("div", { class: "actions" }, el("button", { type: "button", class: "btn", onclick: open }, icon("lock"), "Show the sources"));
  const locked = () => body.replaceChildren(el("p", { class: "small muted", text: "Reelix keeps these behind its admin password, so Starboard asks for it before showing them." }), unlock());
  async function open() {
    body.replaceChildren(el("p", { class: "muted", text: "Asking Reelix…" }));
    try { const r = await rxCall("radio", "sources", {}, "show the radio sources"); if (!r) { locked(); return; } draw(r); }
    catch (e) { body.replaceChildren(notice("danger", "Reelix could not be asked", e.message), unlock()); }
  }
  function draw(s) {
    // Switches and choices apply at once (settings pattern 2); the Podcast Index key and secret are typed, so they
    // have one Save at the foot (pattern 5).
    let saved = s;
    const send = (extra = {}) => rxCall("radio", "sources-save", {
      on: $$("input[name=src]", body).filter((i) => i.checked).map((i) => i.value),
      catchup: $$("input[name=catchup]", body).filter((i) => i.checked).map((i) => i.value),
      country: $("#radio-country", body).value, language: $("#radio-language", body).value,
      podcastindex_key: saved.podcastindex_key, podcastindex_secret: "", ...extra }, "save the radio sources");
    const now = async (control, undo) => {
      try { const out = await send(); if (out) { saved = out.state; settingSaved(); return; } }
      catch (err) { problem(err.message, control); }
      undo();
    };
    const rows = s.sources.map((src) => {
      const id = `radio-src-${src.id}`;
      const input = el("input", { type: "checkbox", role: "switch", name: "src", value: src.id, checked: src.on, "aria-labelledby": `${id}-l` });
      input.addEventListener("change", () => now(input, () => { input.checked = !input.checked; }));
      const row = settingRow(src.name, src.about + (src.search ? "" : " Added by its address, not searched."), el("label", { class: "switch" }, input), `${id}-l`);
      if (!src.catchup) return row;
      // RFX-96: catch-up downloads, off unless switched on, with what the source's terms say.
      const catchId = `radio-catch-${src.id}`;
      const catchInput = el("input", { type: "checkbox", role: "switch", name: "catchup", value: src.id, checked: src.catchup_on, "aria-labelledby": `${catchId}-l` });
      catchInput.addEventListener("change", () => {
        // Catch-up needs its source on: turning catch-up on turns the source on too, in the same save.
        const turnedOn = catchInput.checked && !input.checked;
        if (turnedOn) input.checked = true;
        now(catchInput, () => { catchInput.checked = !catchInput.checked; if (turnedOn) input.checked = false; });
      });
      const catchRow = settingRow(`Catch-up downloads from ${src.name}`,
        `Fetches wanted episodes from ${src.name}'s own pages with yt-dlp (the full Reelix). ${src.risk || "For your personal use only."}`,
        el("label", { class: "switch" }, catchInput), `${catchId}-l`);
      catchRow.classList.add("setting--sub");
      return [row, catchRow];
    }).flat();
    const choice = (id, label, list, value, hint) => {
      const select = el("select", { class: "select", id, "aria-labelledby": `${id}-l` }, list.map(([v, t]) => el("option", { value: v, text: t, selected: v === value })));
      let was = select.value;
      select.addEventListener("change", () => now(select, () => { select.value = was; }).then(() => { was = select.value; }));
      return settingRow(label, hint, select, `${id}-l`);
    };
    const key = el("input", { class: "input", id: "pi-key", value: s.podcastindex_key, autocomplete: "off", spellcheck: "false" });
    const secret = el("input", { class: "input", id: "pi-secret", type: "password", autocomplete: "new-password",
      placeholder: s.podcastindex_secret_set ? "Set. Leave empty to keep it" : "" });
    const save = el("button", { type: "submit", class: "btn" }, "Save");
    const form = el("form", { class: "form-stack", novalidate: true },
      el("h3", { text: "Podcast Index" }),
      el("p", { class: "hint", text: "A free key and secret from podcastindex.org (Sign up for an API key). Reelix keeps the secret." }),
      field("Key", key), field("Secret", secret),
      el("div", { class: "actions" }, save, savedNote("radio-pi-saved")));
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      save.disabled = true;
      try {
        const out = await send({ podcastindex_key: key.value.trim(), podcastindex_secret: secret.value });
        if (out) { saved = out.state; secret.value = ""; showSaved("radio-pi-saved"); }
      } catch (err) { problem(err.message, save); }
      finally { save.disabled = false; }
    });
    body.replaceChildren(el("ul", { class: "settings-rows" }, rows,
      choice("radio-country", "Country searches prefer", s.countries, s.country, "Shows from this country come first."),
      choice("radio-language", "Language searches prefer", s.languages, s.language, "")), form);
  }
  locked();
  return section("radio-sources", "Sources", "Where Reelix finds radio programmes when you search or follow a show.", body);
}

function radioLogosSection() {
  const body = el("div", { class: "stack-4" }, el("p", { class: "muted", text: "Loading…" }));
  const draw = (s) => {
    const file = el("input", { type: "file", id: "radio-logo-zip", accept: ".zip,application/zip", class: "input" });
    const add = el("button", { type: "submit", class: "btn" }, icon("upload"), "Add logos");
    const form = el("form", { class: "form-stack", novalidate: true },
      field("A zip of station logos", file, { hint: "PNG, JPEG or WebP pictures named after their stations, such as BBC-Radio-4.png. A file with the same name replaces the one you have." }),
      el("div", { class: "actions" }, add, savedNote("radio-logos-saved")));
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      setError(file, "");
      const f = file.files[0];
      if (!f) { setError(file, "Choose a zip file"); file.focus(); return; }
      add.disabled = true;
      try {
        const r = await fetch("/api/library/radio-logos?tab=radio", { method: "POST", headers: { "Content-Type": "application/zip", "X-Starboard": "1", Accept: "application/json" }, body: f, credentials: "same-origin" });
        const out = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(out.error || `Starboard answered ${r.status}`);
        const words = `Added ${out.added} logo${out.added === 1 ? "" : "s"}${out.skipped ? `; ${out.skipped} other file${out.skipped === 1 ? "" : "s"} left out` : ""}`;
        draw(await api("/api/library/radio-logos?tab=radio"));
        showSaved("radio-logos-saved", words);
      } catch (err) { setError(file, err.message); file.focus(); }
      finally { add.disabled = false; }
    });
    body.replaceChildren(...[
      el("dl", { class: "facts" }, el("dt", { text: "Logos" }), el("dd", { text: s.logos.toLocaleString("en-GB") }),
        el("dt", { text: "Your stations with a logo" }), el("dd", { text: `${s.matched} of ${s.stations}` })),
      s.missing.length ? el("p", { class: "small", text: `No logo yet: ${s.missing.join(", ")}.` }) : null,
      el("p", { class: "small muted", text: "Logos are kept on this server only. Each one belongs to its broadcaster." }),
      form].filter(Boolean));
  };
  api("/api/library/radio-logos?tab=radio").then((s) => draw(s)).catch((e) => body.replaceChildren(notice("info", "Could not look", e.message)));
  return section("radio-logos", "Station logos", "Shown on Library, Radio, Stations, light or dark to suit the page.", body);
}

// Your podcast library (DASH-212): what Audiobookshelf's Radio library holds that Reelix has not matched. Podcasts no
// followed show covers are brought in on Library, Radio; files of a followed show that match no episode are matched
// here by hand, in a slide-out per podcast. With Starboard's manager key, so no password. Nothing is polled.
const RADIO_FOLLOW_HINTS = { all: "Old and new: Reelix fills the gaps.", from_now_on: "From today on.", none: "Nothing is downloaded." };
const lengthOf = (secs) => (secs ? `${Math.floor(secs / 3600) ? `${Math.floor(secs / 3600)} h ` : ""}${Math.round((secs % 3600) / 60)} min` : "");

function radioLibrarySection() {
  const body = el("div", { class: "stack-4" }, el("p", { class: "muted", text: "Loading…" }));
  const node = section("radio-library", "Your podcast library", "What Audiobookshelf's Radio library holds that Reelix has not matched to a show or an episode.", body);
  const head = () => node.querySelector("h2");
  const openPodcast = async (g, opener) => {
    let r;
    try { r = await api(`/api/radio/review/files?key=${encodeURIComponent(g.key)}`); } catch (e) { problem(e.message, opener); return; }
    let matched = 0;
    const shown = r.files.slice(0, 100);
    const rows = shown.map((f) => {
      const num = f.season != null && f.episode != null ? `S${String(f.season).padStart(2, "0")}E${String(f.episode).padStart(2, "0")}` : f.episode != null ? `Episode ${f.episode}` : "";
      const meta = [num, f.published ? formatDate(f.published) : "", lengthOf(f.seconds), f.size ? formatBytes(f.size) : ""].filter(Boolean).join(" · ");
      const li = el("li", { class: "row row--no-lead", "data-key": `file-${f.id}` }, el("div", { class: "row__text" }, el("div", { class: "row__title", text: f.title }),
        el("div", { class: "row__meta", text: meta }), f.path ? el("div", { class: "small muted", text: f.path }) : null));
      if (!r.episodes.length) return li;
      const pick = el("select", { class: "select", "aria-label": `Episode for ${f.title}` }, el("option", { value: "", text: "Choose the episode" }),
        r.episodes.map((e) => el("option", { value: String(e.id), text: e.label })));
      const go = el("button", { type: "button", class: "btn btn--compact" }, "Match", el("span", { class: "visually-hidden", text: ` ${f.title}` }));
      go.addEventListener("click", async () => {
        if (!pick.value) { problem("Choose the episode first", pick); pick.focus(); return; }
        go.disabled = true;
        try {
          const out = await api("/api/radio/review/match", { method: "POST", body: { file: f.id, episode: Number(pick.value) } });
          matched++;
          // One file to one episode: the episode is no longer offered for the other files.
          for (const other of document.querySelectorAll("#side-panel select")) {
            if (other !== pick) other.querySelector(`option[value="${pick.value}"]`)?.remove();
          }
          const done = chip("Matched", "success");
          li.querySelector(".row__side").replaceChildren(done);
          li.querySelector(".row__title").setAttribute("tabindex", "-1");
          li.querySelector(".row__title").focus();  // the control is gone: focus stays on its row
          announce(`${out.done}: ${f.title}`);
        } catch (e) { go.disabled = false; problem(e.message, pick); }
      });
      li.append(el("div", { class: "row__side" }, pick, go));
      return li;
    });
    sidePanel({ title: r.podcast, wide: true, opener, onClose: () => { if (matched) load(); }, body: [
      el("p", { class: "small", text: r.show_id
        ? `These files are in ${r.podcast}'s folder, but Reelix could not tell which episode of ${r.show} each one is. Choose the episode, then Match.`
        : `${r.podcast} is not a show you follow, so its files have no episodes to match. Bring it in on Library, Radio first.` }),
      r.show_id && !r.episodes.length ? notice("info", "No episodes to match", `Every episode of ${r.show} Reelix knows has a file already. Read the library again after Reelix refreshes the show.`) : null,
      el("ul", { class: "rows", "aria-label": `Files of ${r.podcast} that match no episode` }, rows),
      r.files.length > shown.length ? el("p", { class: "small muted", text: `Showing ${shown.length} of ${r.files.length}. Match these, then open it again for the rest.` }) : null] });
  };
  const draw = (r) => {
    const state = !r.read ? chip("Not read yet", "warning") : r.files || r.shows_waiting ? chip("Needs you", "warning") : chip("All matched", "success");
    onTitle(head(), state);
    const again = el("button", { type: "button", class: "btn" }, icon("refresh-cw"), "Read the library again");
    again.addEventListener("click", async () => {
      again.disabled = true;
      try { const out = await api("/api/radio/review/rescan", { method: "POST" }); showSaved("radio-library-said", out.done); }
      catch (e) { problem(e.message, again); }
      finally { again.disabled = false; }
    });
    const rows = r.groups.map((g) => {
      const open = el("button", { type: "button", class: "btn btn--quiet btn--compact" }, g.show_id ? "Match by hand" : "See the files",
        el("span", { class: "visually-hidden", text: ` for ${g.podcast}` }));
      open.addEventListener("click", () => openPodcast(g, open));
      return el("li", { class: "row row--no-lead", "data-key": g.key }, el("div", {}, el("div", { class: "row__title", text: g.podcast }),
        el("div", { class: "row__meta", text: [`${g.files} ${g.files === 1 ? "file" : "files"}`, g.size ? formatBytes(g.size) : "", g.show_id ? "" : "Not a show you follow"].filter(Boolean).join(" · ") })),
        el("div", { class: "row__side" }, open));
    });
    redraw(body, [
      !r.read ? notice("warning", "Reelix has not read the library yet", "Connect Audiobookshelf's Radio library in Settings, Reelix, Radio, then read it.",
        el("a", { class: "btn", href: "/settings-reelix.html#rx-radio-h" }, "Connect it")) : null,
      r.shows_waiting ? notice("info", `${r.shows_waiting} ${r.shows_waiting === 1 ? "podcast is" : "podcasts are"} not in your library yet`,
        `${r.shows_waiting_files} files in all. Starboard finds each one on Reelix's radio sources and brings it in. Nothing is moved.`,
        el("a", { class: "btn", href: "/library-radio.html" }, "Bring them in")) : null,
      el("h3", { text: "Files that match no episode" }),
      rows.length ? el("ul", { class: "rows", "aria-label": "Podcasts with files that match no episode" }, rows)
        : emptyState("Every file is matched", r.read ? "Each file in the library belongs to an episode Reelix knows." : "Nothing to show until Reelix reads the library."),
      el("p", { class: "small muted", text: r.synced_at ? `Reelix last read the library ${formatDate(r.synced_at, true)}.` : "" }),
      el("div", { class: "actions" }, again, savedNote("radio-library-said"))].filter(Boolean));
  };
  const load = () => api("/api/radio/review").then(draw).catch((e) => body.replaceChildren(notice("info", "Reelix could not be asked", e.message)));
  load();
  return node;
}

// Add a show from a link (DASH-212): a BBC Sounds or Apple Podcasts page, or a feed address. Look it up shows the show
// and its newest episodes (nothing is saved), then Follow this show adds it, with what Reelix gets (choice cards).
function radioLinkSection() {
  const link = el("input", { class: "input", id: "radio-link", type: "url", inputmode: "url", autocomplete: "off", spellcheck: "false", placeholder: "https://" });
  const look = el("button", { type: "submit", class: "btn" }, icon("search"), "Look it up");
  const found = el("div", { class: "stack-4" });
  const form = el("form", { class: "form-stack", novalidate: true },
    field("The show's address", link, { hint: "A programme page on BBC Sounds, a show on Apple Podcasts, or a podcast feed address." }),
    el("div", { class: "actions" }, look));
  const show = (p) => {
    const name = `radio-link-follow-${Date.now()}`;
    const cards = el("fieldset", { class: "stack-2" }, el("legend", { class: "field__label", text: "What Reelix gets" }),
      el("div", { class: "option-cards" }, p.follow.map((f, i) => el("label", { class: "option-card" },
        el("input", { type: "radio", name, value: f.value, checked: i === 0 }), el("strong", { text: f.label }), el("small", { text: RADIO_FOLLOW_HINTS[f.value] || "" })))));
    const follow = el("button", { type: "button", class: "btn btn--primary" }, icon("plus"), "Follow this show");
    const facts = [p.from, p.series ? `${p.series} series` : "", `${p.episodes} ${p.episodes === 1 ? "episode" : "episodes"}`].filter(Boolean).join(" · ");
    const head = el("h3", { id: "radio-link-title", tabindex: "-1", text: p.title });
    follow.addEventListener("click", async () => {
      follow.disabled = true;
      try {
        const out = await api("/api/radio/add-link", { method: "POST", body: { link: p.link, follow: $(`input[name="${name}"]:checked`, cards).value } });
        const openShow = out.show_id ? el("a", { class: "btn", href: `/library-radio-show.html?id=${encodeURIComponent(out.show_id)}` }, "Open the show") : null;
        found.replaceChildren(notice("success", out.done, "It shows on Library, Radio, and its new episodes on Coming up.", openShow));
        $(".notice", found).removeAttribute("role");  // said once, by announce below
        const to = openShow || $(".notice", found);  // the button gone, focus goes to what replaced it
        if (!openShow) to.setAttribute("tabindex", "-1");
        to.focus();
        link.value = "";
        announce(out.done);
      } catch (e) { follow.disabled = false; problem(e.message, follow); }
    });
    // replaceChildren writes a null as the word "null", so the parts that may be missing are filtered out.
    found.replaceChildren(...[el("div", { class: "radio-link-show stack-2" },
      p.picture ? el("img", { src: p.picture, alt: "", width: "96", height: "96", class: "radio-link-show__art", loading: "lazy", referrerpolicy: "no-referrer" }) : null,
      head, facts ? el("p", { class: "small muted", text: facts }) : null, p.about ? el("p", { class: "small", text: p.about }) : null),
      p.latest.length ? el("details", { class: "disclosure" }, el("summary", { text: `Newest ${p.latest.length === 1 ? "episode" : `${p.latest.length} episodes`}` }),
        el("ul", { class: "disclosure__body small" }, p.latest.map((e) => el("li", { text: [e.title, e.when ? formatDate(e.when) : "", lengthOf(e.seconds)].filter(Boolean).join(" · ") })))) : null,
      ...(p.show_id ? [notice("info", "Already in your library", "You follow this show already.",
        el("a", { class: "btn", href: `/library-radio-show.html?id=${encodeURIComponent(p.show_id)}` }, "Open the show"))]
        : [cards, el("div", { class: "actions" }, follow)])].filter(Boolean));
    head.focus();
  };
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    setError(link, "");
    if (!/^https?:\/\/\S+$/i.test(link.value.trim())) { setError(link, "Paste the whole address, starting with https://"); link.focus(); return; }
    look.disabled = true;
    found.replaceChildren(el("p", { class: "muted", text: "Asking the show's source…" }));
    try { show(await api(`/api/radio/preview?link=${encodeURIComponent(link.value.trim())}`)); }
    catch (err) { found.replaceChildren(); setError(link, err.message); link.focus(); }
    finally { look.disabled = false; }
  });
  return section("radio-link", "Add a show from a link", "Follow a show by its page or feed, when searching does not find it.", form, found);
}

function startRadioSettings() {
  const holder = $("#radio-sections");
  holder.removeAttribute("aria-busy");
  holder.replaceChildren(radioSourcesSection(), radioLinkSection(), radioLibrarySection(), radioLogosSection());
}
