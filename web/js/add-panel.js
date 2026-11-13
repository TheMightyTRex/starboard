// The Add slide-out (moved here 12 November 2026 so Search and Discover share it): quality, folder and, for books,
// ebook or audiobook; Follow for a radio show. r is a lookup row: {kind, key, title, year, detail, image, overview}.

function smallCover(src, title, className = "cover cover--result") {
  const box = el("div", { class: className, "aria-hidden": "true" });
  if (src) {
    const img = el("img", { src, alt: "", loading: "lazy", decoding: "async" });
    img.addEventListener("error", () => img.replaceWith(el("span", { class: "lib-cover-title", text: title })), { once: true });
    box.append(img);
  } else box.append(el("span", { class: "lib-cover-title", text: title }));
  return box;
}

function addPanel(r, button) {
  const radio = r.kind === "radio";
  const ids = { p: "add-profile", f: "add-folder", s: "add-search", e: "add-error", fe: "add-ebook", fa: "add-audiobook", fo: "add-follow" };
  const profile = el("select", { class: "select", id: ids.p }, el("option", { text: "Loading…" }));
  const folder = el("select", { class: "select", id: ids.f }, el("option", { text: "Loading…" }));
  const search = el("input", { type: "checkbox", id: ids.s, checked: true });
  const ebook = el("input", { type: "checkbox", id: ids.fe, checked: !r.audiobook });  // Discover, Audiobooks: audiobook only
  const audio = el("input", { type: "checkbox", id: ids.fa, checked: true });
  const follow = el("select", { class: "select", id: ids.fo }, el("option", { value: "all", text: "Every episode, old and new" }),
    el("option", { value: "from_now_on", text: "New episodes only" }));
  const error = el("p", { class: "field-error", id: ids.e, role: "alert" });
  const verb = radio ? "Follow" : "Add";
  const submit = el("button", { type: "submit", form: "add-form", class: "btn btn--primary", disabled: !radio }, icon(radio ? "radio" : "plus"), radio ? "Follow this show" : "Add to Reelix");
  const fields = radio
    ? [el("div", { class: "field" }, el("label", { for: ids.fo, text: "Get" }), follow)]
    : [el("div", { class: "field" }, el("label", { for: ids.p, text: "Quality" }), profile),
      el("div", { class: "field" }, el("label", { for: ids.f, text: "Folder" }), folder),
      r.kind === "books" ? el("fieldset", {}, el("legend", { text: "Get it as" }),
        el("label", { class: "check", for: ids.fe }, ebook, el("span", { class: "check__text", text: "Ebook" })),
        el("label", { class: "check", for: ids.fa }, audio, el("span", { class: "check__text", text: "Audiobook" }))) : null,
      el("label", { class: "check", for: ids.s }, search, el("span", { class: "check__text", text: "Start looking for it now" }))];
  const form = el("form", { id: "add-form", class: "media-panel-section", novalidate: true }, ...fields.filter(Boolean), error);
  const panel = sidePanel({
    title: `${verb} ${r.title}`, opener: button,
    body: [el("div", { class: "side-panel__lead" }, smallCover(r.image, r.title, "cover"),
      el("div", { class: "media-panel-lead__text" }, el("h3", { text: r.year ? `${r.title} (${r.year})` : r.title }),
        r.detail ? el("span", { class: "small muted", text: r.detail }) : null)),
    r.overview ? el("p", { text: r.overview }) : null, form].filter(Boolean),
    foot: [submit, el("button", { type: "button", class: "btn btn--quiet", "data-closes": true, text: "Cancel" })],
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    submit.disabled = true;
    error.textContent = "";
    const options = radio ? { follow: follow.value } : {
      profile_id: Number(profile.value) || null, folder_id: Number(folder.value) || null, search: search.checked,
      formats: [ebook.checked ? "ebook" : "", audio.checked ? "audiobook" : ""].filter(Boolean),
    };
    if (r.kind === "books" && !options.formats.length) { error.textContent = "Choose ebook, audiobook or both"; submit.disabled = false; return; }
    try {
      const done = await api("/api/library/add", { method: "POST", body: { kind: r.kind, key: r.key, options } });
      panel.close();
      r.added = true;  // Search's filters draw the row again: it stays Added (DASH-301)
      const added = chip(radio ? "Following" : "Added", "success");
      button.replaceWith(added);
      toast(radio ? `Following ${done.title}. Its episodes appear in Radio within a few minutes`
        : `Added ${done.title} to Reelix. It appears in ${done.tab === "tv" ? "TV" : done.tab[0].toUpperCase() + done.tab.slice(1)} within a few minutes`);
      added.closest("li")?.querySelector("h4")?.setAttribute("tabindex", "-1");
      added.closest("li")?.querySelector("h4")?.focus();
    } catch (e) {
      error.textContent = e.message;
      submit.disabled = false;
    }
  });
  if (!radio) {
    api(`/api/library/add-options?kind=${r.kind}`).then((o) => {
      profile.replaceChildren(...o.profiles.map((p) => el("option", { value: p.id, text: p.name })));
      folder.replaceChildren(...o.folders.map((f) => el("option", { value: f.id, text: f.free ? `${f.path} (${formatBytes(f.free)} free)` : f.path })));
      if (!o.folders.length) { error.textContent = "Reelix has no folder for this kind yet. Add one in Settings, Reelix."; return; }
      submit.disabled = false;
    }).catch((e) => { error.textContent = e.message; });
  }
}

