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

function startRadioSettings() {
  const holder = $("#radio-sections");
  holder.removeAttribute("aria-busy");
  holder.replaceChildren(radioSourcesSection(), radioLogosSection());
}
