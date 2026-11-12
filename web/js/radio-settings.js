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
  function draw(s, said) {
    const form = el("form", { class: "stack-4", novalidate: true });
    const rows = s.sources.map((src) => {
      const input = el("input", { type: "checkbox", role: "switch", name: "src", value: src.id, checked: src.on });
      return el("li", { class: "setting" },
        el("div", { class: "setting__text" }, el("strong", { text: src.name }),
          el("span", { class: "setting__hint", text: src.about + (src.search ? "" : " Added by its address, not searched.") })),
        el("label", { class: "switch" }, el("span", { class: "visually-hidden", text: `Use ${src.name}` }), input));
    });
    const select = (id, label, list, value, hint) => field(label, el("select", { class: "select", id, name: id },
      list.map(([v, t]) => el("option", { value: v, text: t, selected: v === value }))), { hint });
    const key = el("input", { class: "input", id: "pi-key", name: "pi-key", value: s.podcastindex_key, autocomplete: "off", spellcheck: "false" });
    const secret = el("input", { class: "input", id: "pi-secret", name: "pi-secret", type: "password", autocomplete: "new-password",
      placeholder: s.podcastindex_secret_set ? "Set. Leave empty to keep it" : "" });
    const save = el("button", { type: "submit", class: "btn btn--primary" }, "Save");
    form.append(el("ul", { class: "settings-rows" }, rows),
      select("radio-country", "Country searches prefer", s.countries, s.country, "Shows from this country come first."),
      select("radio-language", "Language searches prefer", s.languages, s.language, ""),
      el("fieldset", { class: "stack-2" }, el("legend", { class: "field__label", text: "Podcast Index" }),
        el("p", { class: "hint", text: "A free key and secret from podcastindex.org (Sign up for an API key). Reelix keeps the secret." }),
        field("Key", key), field("Secret", secret)),
      el("div", { class: "actions" }, save));
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      save.disabled = true;
      try {
        const out = await rxCall("radio", "sources-save", {
          on: $$("input[name=src]", form).filter((i) => i.checked).map((i) => i.value),
          country: form["radio-country"].value, language: form["radio-language"].value,
          podcastindex_key: key.value.trim(), podcastindex_secret: secret.value }, "save the radio sources");
        if (out) { toast(out.done.join(". ")); draw(out.state, out.done.join(". ")); }
      } catch (err) { problem(err.message, save); }
      finally { save.disabled = false; }
    });
    body.replaceChildren(...[said ? notice("success", "Saved", said) : null, form].filter(Boolean));
  }
  locked();
  return section("radio-sources", "Sources", "Where Reelix finds radio programmes when you search or follow a show.", body);
}

function radioLogosSection() {
  const body = el("div", { class: "stack-4" }, el("p", { class: "muted", text: "Loading…" }));
  const draw = (s, said) => {
    const file = el("input", { type: "file", id: "radio-logo-zip", accept: ".zip,application/zip", class: "input" });
    const add = el("button", { type: "submit", class: "btn btn--primary" }, icon("upload"), "Add logos");
    const form = el("form", { class: "form-stack", novalidate: true },
      field("A zip of station logos", file, { hint: "PNG, JPEG or WebP pictures named after their stations, such as BBC-Radio-4.png. A file with the same name replaces the one you have." }),
      el("div", { class: "actions" }, add));
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
        toast(words);
        draw(await api("/api/library/radio-logos?tab=radio"), words);
      } catch (err) { setError(file, err.message); file.focus(); }
      finally { add.disabled = false; }
    });
    body.replaceChildren(...[
      said ? notice("success", "Logos added", said) : null,
      el("dl", { class: "facts" }, el("dt", { text: "Logos" }), el("dd", { text: s.logos.toLocaleString("en-GB") }),
        el("dt", { text: "Your stations with a logo" }), el("dd", { text: `${s.matched} of ${s.stations}` })),
      s.missing.length ? el("p", { class: "small", text: `No logo yet: ${s.missing.join(", ")}.` }) : null,
      el("p", { class: "small muted", text: "Logos are kept on this server only. Each one belongs to its broadcaster." }),
      form].filter(Boolean));
  };
  api("/api/library/radio-logos?tab=radio").then((s) => draw(s)).catch((e) => body.replaceChildren(notice("info", "Could not look", e.message)));
  return section("radio-logos", "Station logos", "Shown on Library, Radio, Stations, light or dark to suit the page.", body);
}

function radioComingSection() {
  return section("radio-next", "More stations and genres", "",
    el("p", { text: "Searching Global Player (LBC, Classic FM, Capital, Heart, Radio X), NTS and Mixcloud, and a search by genre across every source, need Reelix to learn them first. They are planned; until then, Apple Podcasts and podcast feeds bring most stations' shows." }));
}

function startRadioSettings() {
  const holder = $("#radio-sections");
  holder.removeAttribute("aria-busy");
  holder.replaceChildren(radioSourcesSection(), radioLogosSection(), radioComingSection());
}
