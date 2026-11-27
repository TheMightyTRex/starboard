// The switch wizard (DASH-565, owner, 26 November 2026): opened from Settings, Apps, the media server tab, by Switch with help.
// Three steps in one slide-out: how to switch (import your own media, migrate from the old server, or start fresh), which media
// server, and what will happen. Nothing changes until the last step's own button, which uses the same check and way back as
// Use this media server. Loaded only by that tab, and only drawn when it is opened.
// DASH-587: for "import your own media" and "migrate", step 3 names each library and person that would be carried across, with a tick
// for each part, and the last button does it (POST /api/media-server/migrate) while the panel says how each part went, then switches.

const WIZARD_WAYS = [
  { id: "own", name: "Import your own media", text: "Point the new media server at the same folders. Nothing is copied from the old one." },
  { id: "migrate", name: "Migrate from your old media server", text: "Bring libraries, users and what was watched across, as far as the new media server can take them." },
  { id: "fresh", name: "Start fresh", text: "The new media server begins empty. The old one stays added." },
];
const ITEM_STATE = {
  add: ["Will be added", "info", "plus"], exists: ["Already there", "muted", "circle-check"], skip: ["Left out", "muted", "minus"], cannot: ["Cannot be made", "warning", "triangle-alert"],
  done: ["Done", "success", "circle-check"], kept: ["Already there", "muted", "circle-check"], skipped: ["Left out", "muted", "minus"], failed: ["Did not work", "danger", "triangle-alert"],
};
const PART_STATE = { done: ["Done", "success", "circle-check"], partly: ["Partly done", "warning", "triangle-alert"], failed: ["Did not work", "danger", "triangle-alert"], skipped: ["Left out", "muted", "minus"], running: ["Working", "info", "refresh-cw"] };
const WIZARD_STATE = {
  works: ["Works after the switch", "success", "circle-check"],
  waiting: ["Waits after the switch", "warning", "triangle-alert"],
  repoint: ["Needs pointing at the new media server", "info", "link-2"],
};

function openSwitchWizard(ms, opener, done) {
  const choices = [...ms.available.filter((a) => ms.added.includes(a.id) && a.id !== ms.active), { id: "", name: "None" }].filter((a) => a.id !== "" || ms.active);
  let way = "own";
  let target = choices[0]?.id ?? "";
  const said = el("div", { role: "status", "aria-live": "polite", class: "stack-2" });
  const next = el("button", { type: "button", class: "btn btn--primary" });
  const back = el("button", { type: "button", class: "btn" }, "Back");
  const cancel = el("button", { type: "button", class: "btn btn--quiet", "data-closes": true, text: "Cancel" });
  const panel = sidePanel({ title: "Switch media server", wide: true, opener, body: [], foot: [] });
  const heading = (text) => el("h3", { id: "wizard-step-h", tabindex: "-1", text });
  const stepTag = (n) => el("p", { class: "small muted", text: `Step ${n} of 3` });
  const show = (nodes, foot) => { panel.setBody([...nodes, said]); panel.setFoot(foot); $("#wizard-step-h")?.focus(); };

  const radios = (name, list, current, onPick) => el("fieldset", { class: "stack-2" },
    ...list.map((o) => {
      const input = el("input", { type: "radio", name, value: o.id, id: `${name}-${o.id || "none"}`, checked: o.id === current });
      input.addEventListener("change", () => onPick(o.id));
      return el("label", { class: "option-card", for: input.id }, input, el("strong", { text: o.name }), o.text ? el("small", { text: o.text }) : null);
    }));

  function step1() {
    next.textContent = "Next";
    next.onclick = () => step2();
    said.replaceChildren();
    show([stepTag(1), heading("How do you want to switch?"),
      el("p", { class: "small muted", text: "You choose now. Nothing changes until the last step, and you can go back for 24 hours afterwards." }),
      el("fieldset", { class: "stack-2" }, el("legend", { class: "visually-hidden", text: "How to switch" }), radios("wizard-way", WIZARD_WAYS, way, (id) => { way = id; }))],
    [next, cancel]);
  }

  function step2() {
    next.textContent = "Next";
    said.replaceChildren();
    if (!choices.length) {
      show([stepTag(2), heading("Which media server?"), notice("info", "There is no other media server to switch to", "Add Plex or Emby from the catalogue's Media servers tab first.")], [back, cancel]);
      back.onclick = () => step1();
      return;
    }
    next.onclick = () => step3();
    back.onclick = () => step1();
    show([stepTag(2), heading("Which media server?"),
      el("p", { class: "small muted", text: "Only media servers that are added are listed. Starboard asks the one you choose to answer on the next step." }),
      radios("wizard-target", choices.map((c) => ({ id: c.id, name: c.name, text: c.id ? "" : "Starboard draws no media server panel. Nothing is removed." })), target, (id) => { target = id; })],
    [back, next, cancel]);
  }

  const list = (items) => el("ul", { class: "plain-list" }, items.map((t) => el("li", { text: t })));
  const rows = (items) => el("ul", { class: "plain-list" }, items.map((r) => {
    const [words, tone, ic] = WIZARD_STATE[r.state] || WIZARD_STATE.works;
    return el("li", {}, el("strong", { text: `${r.name}: ` }), chip(words, tone, ic), r.why ? el("span", { class: "small muted", text: ` ${r.why}` }) : null);
  }));

  async function step3() {
    next.disabled = true;
    said.replaceChildren(notice("info", "Checking…", "Asking the media server to answer. Nothing has changed."));
    let p;
    try { p = await api("/api/media-server/plan", { method: "POST", body: { id: target, mode: way } }); }
    catch (e) { said.replaceChildren(notice("danger", "Could not plan the switch", e.message)); next.disabled = false; return; }
    next.disabled = false;
    said.replaceChildren();
    const ok = !p.to || p.same || p.check?.ok;
    const head = [stepTag(3), heading(`Switch to ${p.to_name}`)];
    if (p.same) head.push(notice("info", "Already in use", `${p.to_name} is already your media server.`));
    else if (p.to) head.push(ok ? notice("success", `${p.to_name} answered`, p.check.said) : notice("warning", `${p.to_name} did not answer`, `${(p.check?.said || "").replace(/\.?$/, ".")} Nothing has changed. Fix its address or key in Manage apps, then try again.`));
    const parts = [el("h4", { text: p.mode_name }), list(p.moves)];
    const m = p.migration || {};
    const picks = {};  // the parts a person ticks: libraries, users, history (and keep applying, for Jellyfin)
    const tick = (key, text, hint, on = true) => {
      const input = el("input", { type: "checkbox", id: `wizard-part-${key}`, checked: on });
      picks[key] = input;
      return el("div", { class: "check" }, input, el("label", { for: input.id, class: "check__text" }, el("strong", { text }), hint ? el("span", { class: "check__hint", text: hint }) : null));
    };
    const rowsOf = (items) => el("ul", { class: "plain-list" }, items.map((r) => {
      const [words, tone, ic] = ITEM_STATE[r.action] || ITEM_STATE.skip;
      return el("li", {}, el("strong", { text: `${r.name}: ` }), chip(words, tone, ic), r.why ? el("span", { class: "small muted", text: ` ${r.why}` }) : null);
    }));
    const doing = p.to && !p.same && p.mode !== "fresh" && !m.problem;
    if (doing && m.libraries?.length) parts.push(el("h4", { text: "Libraries" }), rowsOf(m.libraries), tick("libraries", "Add these libraries", "They read your media folders. Nothing is copied or moved.", m.libraries.some((x) => x.action === "add")));
    if (doing && p.mode === "migrate" && m.users?.length) parts.push(el("h4", { text: "People" }), rowsOf(m.users),
      p.to === "plex" ? null : tick("users", "Make these people", "Each gets a password nobody knows. You set a real one in the new media server's dashboard, under Users.", m.users.some((x) => x.action === "add")));
    if (doing && p.mode === "migrate" && m.history?.can) {
      parts.push(el("h4", { text: "What was watched" }), el("p", { class: "small muted", text: m.history.says }),
        tick("history", "Carry across what was watched", "Starboard reads it from the old media server and writes it into the new one. Anything already watched there is left as it is."));
      if (p.to === "jellyfin") parts.push(tick("keep", "Keep applying it every hour", "So films that Jellyfin finds later are marked too."));
    }
    parts.push(el("h4", { text: "What cannot move" }), list(p.cannot_move), el("h4", { text: "What keeps working with no change" }), list(p.unaffected));
    if (p.plugins.length) parts.push(el("h4", { text: "Plug-ins that need a media server" }), rows(p.plugins));
    if (p.features.length) parts.push(el("h4", { text: "Parts of Starboard and your apps that talk to the media server" }), rows(p.features));
    const word = !p.to ? "Use no media server" : doing && Object.keys(picks).length ? `Carry across and switch to ${p.to_name}` : `Switch to ${p.to_name}`;
    next.textContent = word;
    next.disabled = !ok || p.same;
    next.onclick = async () => {
      next.disabled = true;
      const chosen = Object.keys(picks).filter((k) => picks[k].checked);
      if (doing && chosen.length) { await migrate(p, chosen); return; }
      try {
        const r = await api("/api/media-server/choose", { method: "POST", body: { id: target } });
        announce(r.said);
        panel.close();
        done(r.said, p);
      } catch (e) { said.replaceChildren(notice("warning", "Nothing changed", e.message)); next.disabled = false; next.focus(); }
    };
    back.onclick = () => step2();
    show([...head, el("div", { class: "stack-2" }, parts)], [back, next, cancel]);
  }

  // The doing: starts the move, then reads how it is going until it ends. The panel keeps the steps in one live region.
  async function migrate(p, chosen) {
    const body = el("div", { class: "stack-2" });
    const live = el("div", { role: "status", "aria-live": "polite", class: "stack-2", id: "wizard-progress" });
    const close = el("button", { type: "button", class: "btn btn--primary", text: "Close" });
    const render = (st) => {
      const lines = (st.steps || []).map((s) => {
        const [words, tone, ic] = PART_STATE[s.state] || PART_STATE.running;
        const items = (s.items || []).filter((i) => i.state === "failed" || i.state === "skipped").slice(0, 8);
        return el("div", { class: "stack-2" }, el("h4", { text: s.title }), el("p", {}, chip(words, tone, ic), " ", s.said || ""),
          items.length ? el("ul", { class: "plain-list" }, items.map((i) => el("li", {}, el("strong", { text: `${i.name}: ` }), i.why || ""))) : null);
      });
      const head = st.state === "running" ? notice("info", "Working", "Starboard is carrying this across. You can close this panel: it carries on.")
        : st.state === "done" ? notice("success", "Finished", st.said) : notice("danger", "It stopped", st.said);
      live.replaceChildren(head, ...lines);
      return st.state !== "running";
    };
    panel.setBody([stepTag(3), heading("Carrying it across"), el("p", { class: "small muted", text: "Nothing is deleted from either media server, and your files are not touched." }), body, live]);
    panel.setFoot([close]);
    close.onclick = () => { panel.close(); if (last?.state === "done") done(last.said, p); };
    $("#wizard-step-h")?.focus();
    let last = null;
    try { last = await api("/api/media-server/migrate", { method: "POST", body: { id: target, mode: way, parts: chosen } }); }
    catch (e) { live.replaceChildren(notice("danger", "Nothing changed", e.message)); return; }
    render(last);
    for (let i = 0; i < 4000 && last.state === "running"; i++) {
      await new Promise((r) => setTimeout(r, 1500));
      try { last = await api("/api/media-server/migrate"); } catch { continue; }
      if (render(last)) break;
    }
    if (last.state === "done") announce(last.said);
    close.focus();
  }

  step1();
  return panel;
}
