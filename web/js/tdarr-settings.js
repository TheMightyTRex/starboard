// Settings, Apps, Tdarr (owner, 10 November 2026, DASH-306): Tdarr's basic choices from Starboard, which gives Tdarr
// its key, so nobody signs in to Tdarr. Libraries, what it does, how many at once and when; what it has done so far.

// Settings pattern 1: a heading, one line about it, then the content.
function tdSection(id, title, desc, ...content) {
  return el("section", { class: "settings-section", "aria-labelledby": `${id}-h` },
    el("div", { class: "settings-section__head" }, el("h2", { id: `${id}-h`, text: title }), desc ? el("p", { class: "small muted", text: desc }) : null),
    ...content.filter(Boolean));
}

function tdNotice(tone, title, text, action) {
  return el("div", { class: "notice", "data-tone": tone, role: "status" }, icon(tone === "info" ? "info" : "circle-alert"),
    el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: title }), el("p", { text })), action || null);
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
      // Tdarr restarts to take its key and needs a little while to answer again (owner's server, 12 November 2026:
      // the first try asked too soon), so wait for it, up to 90 seconds.
      try {
        await api("/api/services/read-keys", { method: "POST" });
        go.textContent = "Waiting for Tdarr to restart…";
        let ok = false;
        for (let i = 0; i < 30 && !ok; i += 1) {
          try { await api("/api/tdarr"); ok = true; } catch { await new Promise((r) => setTimeout(r, 3000)); }
        }
        if (!ok) throw new Error("Tdarr did not answer after restarting. Check it is running in Apps, then try again.");
        tdDraw("Connected. Starboard keeps Tdarr's key");
      }
      catch (err) { problem(err.message, go); go.disabled = false; go.textContent = "Connect Tdarr"; }
    });
    box.removeAttribute("aria-busy");
    box.replaceChildren(tdNotice("info", "Tdarr is not connected yet", "Connect gives Tdarr a key Starboard keeps, so you never sign in to Tdarr; it restarts once.", go));
    return;
  }
  // Every choice applies at once and says so beside itself (settings pattern 2): there is nothing to type here.
  const form = el("form", { class: "stack-4", novalidate: true });
  let saved = s;
  const send = async (control) => {
    try {
      await api("/api/tdarr", { method: "PUT", body: { mode: form.mode.value, at_once: Number(atOnce.value), night: form.when.value === "night",
        libraries: { films: form["lib-films"].checked, series: form["lib-series"].checked } } });
      settingSaved();
    } catch (err) { problem(err.message, control); tdDraw(); }
  };
  const libs = el("fieldset", { class: "stack-2" }, el("legend", { class: "field__label", text: "Libraries" }),
    ...[["films", "Films", "/media/movies"], ["series", "Series", "/media/tv"]].map(([k, label, folder]) => el("label", { class: "check" },
      el("input", { type: "checkbox", name: `lib-${k}`, checked: saved.libraries[k] || !Object.values(saved.libraries).some(Boolean) }),
      el("span", { class: "check__text" }, el("strong", { text: label }), el("span", { class: "check__hint", text: `Tdarr sees it as ${folder}` })))));
  const mode = el("fieldset", { class: "stack-2" }, el("legend", { class: "field__label", text: "What Tdarr does" }),
    el("div", { class: "option-cards" },
      tdChoice("mode", "save_space", "Save space", "Converts to H.265 and keeps the new file only when it is smaller. Same picture, often half the size.", s.mode === "save_space"),
      tdChoice("mode", "check_only", "Check files only", "Finds damaged files and changes nothing.", s.mode === "check_only"),
      tdChoice("mode", "off", "Off", "Tdarr does nothing until you choose again.", s.mode === "off")));
  const atOnce = el("select", { class: "select", id: "td-at-once", "aria-labelledby": "td-at-once-l" }, [1, 2, 3, 4].map((n) =>
    el("option", { value: String(n), text: n === 1 ? "1 at a time (lightest)" : `${n} at a time`, selected: (s.at_once || 1) === n })));
  const when = el("fieldset", { class: "stack-2" }, el("legend", { class: "field__label", text: "When" }),
    el("div", { class: "option-cards" },
      tdChoice("when", "any", "Any time", "Starts on new files straight away.", !s.night),
      tdChoice("when", "night", "In quiet hours", `${s.quiet_hours || "01:00 to 06:00"}${s.quiet_from_download_hours ? ", your download hours" : ""}, so the server stays quick in the day.`, s.night)));
  form.append(libs, mode, el("ul", { class: "settings-rows" }, el("li", { class: "setting" },
    el("div", { class: "setting__text" }, el("span", { class: "setting__label", id: "td-at-once-l", text: "Conversions at once" }),
      el("span", { class: "setting__hint", text: "Each one uses about one processor core while it runs." })),
    el("div", { class: "setting__control" }, atOnce))), when);
  form.addEventListener("change", (e) => send(e.target));
  form.addEventListener("submit", (e) => e.preventDefault());
  const done = el("dl", { class: "facts" }, ...[["Files Tdarr knows", s.files], ["Converted", s.converted], ["Checked", s.checked],
    ["Space saved", `${s.saved_gb} GB`]].flatMap(([k, v]) => [el("dt", { text: k }), el("dd", { text: String(v) })]));
  box.removeAttribute("aria-busy");
  box.replaceChildren(
    said ? el("div", { class: "notice", "data-tone": "success", role: "status" }, icon("circle-check"),
      el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: said }))) : null,
    tdSection("td-choices", "What Tdarr does", "Starboard writes these into Tdarr; Tdarr's own page still shows everything.", form),
    tdSection("td-done", "So far", s.other_libraries.length ? `Tdarr also has libraries you made yourself: ${s.other_libraries.join(", ")}. Starboard leaves them as they are.` : null, done));
}

startPage().then(() => tdDraw());
