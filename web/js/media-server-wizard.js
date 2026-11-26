// The switch wizard (DASH-565, owner, 26 November 2026): opened from Settings, Apps, the media server tab, by Switch with help.
// Three steps in one slide-out: how to switch (import your own media, migrate from the old server, or start fresh), which media
// server, and what will happen. Nothing changes until the last step's own button, which uses the same check and way back as
// Use this media server. Loaded only by that tab, and only drawn when it is opened.

const WIZARD_WAYS = [
  { id: "own", name: "Import your own media", text: "Point the new media server at the same folders. Nothing is copied from the old one." },
  { id: "migrate", name: "Migrate from your old media server", text: "Bring libraries, users and what was watched across, as far as the new media server can take them." },
  { id: "fresh", name: "Start fresh", text: "The new media server begins empty. The old one stays added." },
];
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
    const parts = [el("h4", { text: p.mode_name }), list(p.moves), el("h4", { text: "What cannot move" }), list(p.cannot_move),
      el("h4", { text: "What keeps working with no change" }), list(p.unaffected)];
    if (p.plugins.length) parts.push(el("h4", { text: "Plug-ins that need a media server" }), rows(p.plugins));
    if (p.features.length) parts.push(el("h4", { text: "Parts of Starboard and your apps that talk to the media server" }), rows(p.features));
    next.textContent = p.to ? `Switch to ${p.to_name}` : "Use no media server";
    next.disabled = !ok || p.same;
    next.onclick = async () => {
      next.disabled = true;
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

  step1();
  return panel;
}
