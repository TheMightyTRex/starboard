// Settings, Apps, Tdarr (owner, 10 November 2026, DASH-306): Tdarr's basic choices from Starboard, which gives Tdarr
// its key, so nobody signs in to Tdarr. Libraries, what it does, how many at once and when; what it has done so far.

function tdSection(id, title, desc, ...content) {
  return el("section", { class: "settings-section", "aria-labelledby": `${id}-h` },
    el("h2", { id: `${id}-h`, text: title }), desc ? el("p", { class: "settings-section__desc", text: desc }) : null, ...content);
}

function tdChoice(name, value, label, hint, checked) {
  return el("label", { class: "option-card" }, el("input", { type: "radio", name, value, checked }), el("strong", { text: label }),
    el("small", { text: hint }));
}

async function tdDraw(said) {
  const box = $("#tdarr-sections");
  let s;
  try { s = await api("/api/tdarr"); }
  catch (e) {
    // No key yet: Starboard gives Tdarr one (Tdarr restarts once), so nobody signs in to Tdarr.
    const go = el("button", { type: "button", class: "btn btn--primary" }, icon("link"), "Connect Tdarr");
    go.addEventListener("click", async () => {
      go.disabled = true;
      go.textContent = "Connecting… Tdarr restarts once";
      try { const r = await api("/api/services/read-keys", { method: "POST" });
        if (!r.found.includes("Tdarr")) throw new Error("Tdarr did not take a key. Check it is running in Apps."); tdDraw("Connected"); }
      catch (err) { problem(err.message, go); go.disabled = false; go.textContent = "Connect Tdarr"; }
    });
    box.removeAttribute("aria-busy");
    box.replaceChildren(el("div", { class: "notice", role: "status" }, icon("info"),
      el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: "Tdarr is not connected yet" }),
        el("p", { text: "Connect gives Tdarr a key that Starboard keeps, so you never sign in to Tdarr. Tdarr restarts once." })), go));
    return;
  }
  const form = el("form", { class: "stack-4" });
  const libs = el("fieldset", { class: "stack-2" }, el("legend", { class: "field__label", text: "Libraries" }),
    ...[["films", "Films", "/media/movies"], ["series", "Series", "/media/tv"]].map(([k, label, folder]) => el("label", { class: "check" },
      el("input", { type: "checkbox", name: `lib-${k}`, checked: s.libraries[k] || !Object.values(s.libraries).some(Boolean) }),
      el("span", { class: "check__text" }, el("strong", { text: label }), el("span", { class: "check__hint", text: folder })))));
  const mode = el("fieldset", { class: "stack-2" }, el("legend", { class: "field__label", text: "What Tdarr does" }),
    el("div", { class: "option-cards" },
      tdChoice("mode", "save_space", "Save space", "Converts to H.265 and keeps the new file only when it is smaller. Same picture, often half the size.", s.mode === "save_space"),
      tdChoice("mode", "check_only", "Check files only", "Finds damaged files and changes nothing.", s.mode === "check_only"),
      tdChoice("mode", "off", "Off", "Tdarr does nothing until you choose again.", s.mode === "off")));
  const atOnce = el("select", { class: "select", id: "td-at-once" }, [1, 2, 3, 4].map((n) =>
    el("option", { value: String(n), text: n === 1 ? "1 at a time (lightest)" : `${n} at a time`, selected: (s.at_once || 1) === n })));
  const when = el("fieldset", { class: "stack-2" }, el("legend", { class: "field__label", text: "When" }),
    el("div", { class: "option-cards" },
      tdChoice("when", "any", "Any time", "Starts on new files straight away.", !s.night),
      tdChoice("when", "night", "Overnight", "Midnight to 07:00, so the server stays quick in the day.", s.night)));
  const save = el("button", { type: "submit", class: "btn btn--primary" }, "Save");
  form.append(libs, mode, el("div", { class: "field" }, el("label", { class: "field__label", for: "td-at-once", text: "Conversions at once" }),
    el("p", { class: "hint", text: "Each one uses about one processor core while it runs." }), atOnce), when, el("div", { class: "actions" }, save));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    save.disabled = true;
    try {
      const out = await api("/api/tdarr", { method: "PUT", body: { mode: form.mode.value, at_once: Number(atOnce.value), night: form.when.value === "night",
        libraries: { films: form["lib-films"].checked, series: form["lib-series"].checked } } });
      toast(out.done.join(". "));
      tdDraw(out.done.join(". "));
    } catch (err) { problem(err.message, save); save.disabled = false; }
  });
  const done = el("dl", { class: "facts" }, ...[["Files Tdarr knows", s.files], ["Converted", s.converted], ["Checked", s.checked],
    ["Space saved", `${s.saved_gb} GB`]].flatMap(([k, v]) => [el("dt", { text: k }), el("dd", { text: String(v) })]));
  box.removeAttribute("aria-busy");
  box.replaceChildren(
    said ? el("div", { class: "notice", "data-tone": "success", role: "status" }, icon("circle-check"),
      el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: "Saved" }), el("p", { text: said }))) : null,
    tdSection("td-choices", "What Tdarr does", "Starboard writes these into Tdarr; Tdarr's own page still shows everything.", form),
    tdSection("td-done", "So far", s.other_libraries.length ? `Tdarr also has libraries you made yourself: ${s.other_libraries.join(", ")}. Starboard leaves them as they are.` : null, done));
}

startPage().then(() => tdDraw());
