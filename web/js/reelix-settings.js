// Settings, Reelix: sites to search, download apps and media servers, with forms drawn from Reelix's own description
// of each setting (/{kind}/schema), so a field Reelix adds shows here without a Starboard update (DASH-154 to 156).
// Reelix keeps these behind its admin password. Starboard keeps only a manager key, so each change asks for the
// password, signs in to Reelix for that change and signs out again (starboard/reelix_admin.py). The page holds the
// typed password for 5 minutes after it was last used, in this page only, so a few changes in a row ask once.
// Uses field, section, notice and switchRow from settings.js, which loads first. 8 November 2026.

const RX_HOLD_MS = 5 * 60 * 1000;
const rxHeld = { password: "", user: "admin", timer: null };
let rxAbout = null;

function rxForget() {
  rxHeld.password = "";
  clearTimeout(rxHeld.timer);
}

function rxHold(password, user) {
  rxHeld.password = password;
  rxHeld.user = user || "admin";
  clearTimeout(rxHeld.timer);
  rxHeld.timer = setTimeout(rxForget, RX_HOLD_MS);
}

// The password dialog: what it is for, where it goes, and that nothing is kept. Resolves { password, user } or null.
async function rxAskPassword(what, error = "") {
  const pw = el("input", { class: "input", type: "password", autocomplete: "current-password", id: "rx-password" });
  const user = el("input", { class: "input", type: "text", autocomplete: "username", value: rxHeld.user || "admin", id: "rx-user", spellcheck: "false" });
  const pwField = field("Reelix password", pw, { required: true,
    hint: "If Starboard set Reelix up, it is the same as your Starboard password." });
  const more = el("details", { class: "disclosure" }, el("summary", { text: "Another Reelix user" }),
    el("div", { class: "disclosure__body" }, field("Reelix user name", user, { hint: "A Reelix user with admin rights. Starboard set Reelix up with the user admin." })));
  if (error) queueMicrotask(() => setError(pw, error));
  const where = rxAbout?.address ? ` at ${rxAbout.address}` : "";
  const message = el("div", { class: "stack-2" },
    el("p", { text: `To ${what}, Starboard signs in to Reelix${where} for this change only, then signs out.` }),
    el("p", { class: "small muted", text: "Starboard keeps neither the password nor the sign-in. This page remembers the password for 5 minutes, so a few changes in a row ask once." }));
  setTimeout(() => pw.focus(), 50);
  const ok = await confirmDialog({ title: "Enter your Reelix password", message, confirm: "Continue", fields: [pwField, more] });
  if (!ok || !pw.value) return null;
  return { password: pw.value, user: user.value.trim() || "admin" };
}

// One call to Reelix's admin settings through Starboard. Asks for the password when none is held, and again when
// Reelix refuses it. Returns the answer, or null when the person cancelled.
async function rxCall(kind, action, body, what) {
  let error = "";
  for (let tries = 0; tries < 4; tries++) {
    let creds = rxHeld.password ? { password: rxHeld.password, user: rxHeld.user } : await rxAskPassword(what, error);
    if (!creds) return null;
    try {
      const out = await api(`/api/reelix/admin/${kind}/${action}`, { method: "POST", body: { ...body, ...creds } });
      rxHold(creds.password, creds.user);
      return out;
    } catch (e) {
      if (e.status === 401 || e.status === 429) { rxForget(); error = e.message; if (e.status === 429) throw e; continue; }
      throw e;
    }
  }
  return null;
}

// Forms from the schema ------------------------------------------------------------------------------------------

// Reelix's field kinds as the library's fields: text, url and path inputs, secrets, numbers, switches, selects,
// several choices as ticks, and lists as one line with commas. Advanced fields go under More settings.
function rxSchemaForm(fields, values = {}, { editing = false } = {}) {
  const read = [];
  const make = (f) => {
    const v = values[f.name] !== undefined ? values[f.name] : f.default;
    const hint = f.help ? f.help.replace(/`/g, "") : "";
    if (f.type === "bool") {
      const input = el("input", { type: "checkbox", checked: !!v });
      read.push(() => [f.name, input.checked]);
      return switchRow(f.label, hint, input);
    }
    if (f.type === "select") {
      const select = el("select", { class: "select" },
        f.required ? null : el("option", { value: "", text: "Not set" }),
        (f.options || []).map((o) => el("option", { value: String(o.value), text: String(o.label ?? o.value), selected: String(o.value) === String(v) })));
      read.push(() => [f.name, select.value]);
      return field(f.label, select, { hint, required: f.required });
    }
    if (f.type === "multi_select") {
      const chosen = new Set((Array.isArray(v) ? v : []).map(String));
      const boxes = (f.options || []).map((o) => ({ o, input: el("input", { type: "checkbox", checked: chosen.has(String(o.value)) }) }));
      read.push(() => [f.name, boxes.filter((b) => b.input.checked).map((b) => b.o.value)]);
      return el("fieldset", { class: "field" }, el("legend", { text: f.label }), hint ? el("span", { class: "hint", text: hint }) : null,
        el("div", { class: "stack-1" }, boxes.map((b) => el("label", { class: "check" }, b.input, el("span", { class: "check__text", text: String(b.o.label ?? b.o.value) })))));
    }
    const input = el("input", { class: "input", spellcheck: "false", autocomplete: "off" });
    if (f.type === "secret") {
      input.type = "password";
      input.autocomplete = "new-password";
      if (editing) input.placeholder = "Saved: leave empty to keep it";
    } else if (f.type === "number") {
      input.type = "text";
      input.inputMode = "decimal";
      input.value = v ?? "";
    } else if (f.type === "list") {
      input.value = Array.isArray(v) ? v.join(", ") : (v ?? "");
    } else {
      input.type = f.type === "url" ? "url" : "text";
      input.value = v ?? "";
    }
    if (f.placeholder && !input.placeholder) input.placeholder = f.placeholder;
    read.push(() => [f.name, f.type === "secret" && !input.value && editing ? "********" : input.value]);
    return field(f.label, input, { hint: f.type === "list" ? [hint, "Separate them with commas."].filter(Boolean).join(" ") : hint,
      required: f.required && !(editing && f.type === "secret") });
  };
  const main = fields.filter((f) => !f.advanced).map(make);
  const extra = fields.filter((f) => f.advanced).map(make);
  const node = el("div", { class: "stack-4" }, main,
    extra.length ? el("details", { class: "disclosure" }, el("summary", { text: "More settings" }), el("div", { class: "disclosure__body stack-4" }, extra)) : null);
  return { node, values: () => Object.fromEntries(read.map((r) => r())) };
}

function rxTestResult(result) {
  if (!result) return null;
  const checks = (result.checks || []).filter((c) => c.message || !c.ok);
  return notice(result.ok ? "success" : "danger", result.ok ? "The test passed" : "The test did not pass", result.message || "",
    checks.length ? el("ul", { class: "small" }, checks.map((c) => el("li", { text: `${c.ok ? "Passed" : "Failed"}: ${c.name}${c.message ? `. ${c.message}` : ""}` }))) : null);
}

// The side panel to add or change one: name, on or off, the schema's fields, then Test and Save.
function rxEditPanel(kind, words, schema, existing, done) {
  const editing = !!existing;
  const name = el("input", { class: "input", type: "text", value: existing?.name || schema.name, autocomplete: "off" });
  const on = el("input", { type: "checkbox", checked: existing ? existing.enabled : true });
  const priority = el("input", { class: "input", type: "text", inputMode: "numeric", value: String(existing?.priority ?? 25) });
  const form = rxSchemaForm(schema.fields || [], existing?.settings || {}, { editing });
  const status = el("div", { class: "stack-2", "aria-live": "polite" });
  const item = () => ({ id: existing?.id, implementation: schema.implementation, name: name.value.trim(), enabled: on.checked,
    priority: Number(priority.value) || 25, settings: form.values() });
  const test = el("button", { type: "button", class: "btn", text: "Test" });
  const save = el("button", { type: "button", class: "btn btn--primary", text: "Save" });
  const busy = (b) => { test.disabled = save.disabled = b; };
  test.addEventListener("click", async () => {
    busy(true); status.replaceChildren(el("p", { class: "muted", text: "Testing…" }));
    try { const r = await rxCall(kind, "test", { item: item() }, `test ${name.value || schema.name}`); status.replaceChildren(r ? rxTestResult(r) : ""); }
    catch (e) { status.replaceChildren(notice("danger", "Reelix could not test it", e.message)); }
    finally { busy(false); }
  });
  save.addEventListener("click", async () => {
    if (!name.value.trim()) { setError(name, "Give it a name"); name.focus(); return; }
    setError(name, "");
    busy(true); status.replaceChildren(el("p", { class: "muted", text: "Saving…" }));
    try {
      const r = await rxCall(kind, "save", { item: item() }, `save ${name.value}`);
      if (!r) { status.replaceChildren(); return; }
      panel.close();
      toast(`${r.saved?.name || name.value} saved`);
      done(r);
    } catch (e) { status.replaceChildren(notice("danger", "Not saved", e.message)); }
    finally { if (save.isConnected) busy(false); }
  });
  const about = schema.description ? el("p", { class: "small muted", text: schema.description }) : null;
  const panel = sidePanel({ title: editing ? `Change ${existing.name}` : `Add ${schema.name}`, wide: true,
    body: [el("div", { class: "stack-4" }, about,
      field("Name", name, { required: true, hint: `The name Starboard and Reelix show for this ${words.one}.` }),
      switchRow("Active", `Reelix uses this ${words.one} while it is active.`, on),
      form.node,
      el("details", { class: "disclosure" }, el("summary", { text: "Order" }), el("div", { class: "disclosure__body" },
        field("Priority", priority, { hint: "From 1 to 50. Lower comes first when two give the same thing." }))),
      status)],
    foot: [save, test] });
  return panel;
}

// The list of what can be added: a search box, and for sites, whether they need an account. Choosing one opens
// its form.
function rxAddPanel(kind, words, catalogue, chosen, { have = [], suggested = [] } = {}) {
  const query = el("input", { class: "input", type: "search", placeholder: `Search ${catalogue.length} ${words.many}`, "aria-label": `Search ${words.many}` });
  const privacy = kind === "indexers" ? el("div", { class: "segmented", role: "radiogroup", "aria-label": "Account" },
    [["all", "All"], ["public", "No account needed"], ["account", "Needs an account"]].map(([v, t], i) =>
      el("label", {}, el("input", { type: "radio", name: "rx-privacy", value: v, checked: i === 0 }), el("span", { text: t })))) : null;
  const english = el("input", { type: "checkbox", checked: kind === "indexers" && catalogue.length > 10 });
  const onlyEnglish = kind === "indexers" && catalogue.length > 10 ? el("label", { class: "check" }, english, el("span", { class: "check__text", text: "Only sites in English" })) : null;
  const added = new Set(have.map((i) => i.implementation));
  const first = new Set(suggested);
  const list = el("ul", { class: "rx-picks", role: "list" });
  const count = el("p", { class: "small muted", "aria-live": "polite" });
  const draw = () => {
    const q = query.value.trim().toLowerCase();
    const p = privacy ? $("input:checked", privacy).value : "all";
    const found = catalogue.filter((c) => (!q || `${c.name} ${c.description}`.toLowerCase().includes(q))
      && (p === "all" || (p === "public" ? c.privacy === "public" : c.privacy && c.privacy !== "public"))
      && (!english.checked || !c.language || /^en/.test(c.language)))
      .sort((a, b) => (first.has(b.implementation) - first.has(a.implementation)));
    const shown = found.slice(0, 60);
    count.textContent = found.length > shown.length ? `Showing ${shown.length} of ${found.length}. Type to narrow it down.` : `${found.length} found`;
    list.replaceChildren(...shown.map((c) => el("li", {}, el("button", { type: "button", class: "option-card rx-pick", onclick: () => chosen(c) },
      el("span", { class: "rx-pick__name" }, el("strong", { text: c.name }),
        added.has(c.implementation) ? chip("Added already", "info", "check") : first.has(c.implementation) ? chip("Suggested", "info", "star") : null,
        c.privacy ? chip(c.privacy === "public" ? "No account needed" : c.privacy === "private" ? "Needs an account" : "Partly needs an account", c.privacy === "public" ? "success" : "neutral", c.privacy === "public" ? "circle-check" : "user") : null,
        c.protocol ? chip(c.protocol === "usenet" ? "Usenet" : "Torrent", "muted", "download") : null,
        c.language && !/^en/.test(c.language) ? chip(c.language, "muted", "globe") : null),
      el("small", { text: c.description || "" })))));
  };
  query.addEventListener("input", draw);
  privacy?.addEventListener("change", draw);
  english.addEventListener("change", draw);
  draw();
  setTimeout(() => query.focus(), 50);
  return sidePanel({ title: `Add ${words.a}`, wide: true, body: [el("div", { class: "stack-4" }, query, privacy, onlyEnglish, count, list)] });
}

// One state chip for a configured one: off, cannot start, resting after failures, failed last time, or working.
function rxState(i) {
  if (i.error) return chip("Cannot start", "danger");
  if (!i.enabled) return chip("Not active", "muted");
  const until = i.status?.disabled_until ? new Date(i.status.disabled_until) : null;
  if (until && until > new Date()) return chip(`Resting until ${until.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}`, "warning");
  if (i.status?.failure_count) return chip("Failed last time", "warning");
  return chip("Working", "success");
}

function rxResults(i) {
  const s = i.stats;
  if (!s) return "";
  const parts = [`${s.queries ?? 0} ${s.queries === 1 ? "search" : "searches"}`, `${s.grabs ?? 0} chosen`];
  if (s.failures) parts.push(`${s.failures} failed`);
  if (s.avg_response_ms && s.queries) parts.push(`${(s.avg_response_ms / 1000).toFixed(1)} s each`);
  return parts.join(", ");
}

const RX_WORDS = {
  indexers: { title: "Sites to search", one: "site", a: "a site to search", many: "sites", show: "see and change the sites Reelix searches" },
  downloadclients: { title: "Download apps", one: "download app", a: "a download app", many: "download apps", show: "see and change Reelix's download apps" },
  mediaservers: { title: "Media servers", one: "media server", a: "a media server", many: "media servers", show: "see and change Reelix's media servers" },
  notifications: { title: "Notifications", one: "notification", a: "a notification", many: "notifications", show: "see and change Reelix's notifications" },
  importlists: { title: "Lists", one: "list", a: "a list", many: "lists", show: "see and change the lists Reelix follows" },
};

// One section for a kind: locked until the password is given, then the list with Add, Change, Test and Remove.
function rxKindSection(kind, description) {
  const words = RX_WORDS[kind];
  const body = el("div", { class: "stack-4", "aria-live": "polite" });
  let data = null;
  let search = null;

  const reopen = async (fn) => {
    try { await fn(); } catch (e) { body.prepend(notice("danger", "Reelix said no", e.message)); }
  };
  const open = async () => {
    body.replaceChildren(el("p", { class: "muted", text: "Asking Reelix…" }));
    try {
      const r = await rxCall(kind, "open", {}, words.show);
      if (!r) { locked(); return; }
      data = r;
      if (kind === "indexers") search = await rxCall("search", "open", {}, "see how Reelix searches");
      draw();
    } catch (e) { body.replaceChildren(notice("danger", "Reelix could not be asked", e.message), unlockButton()); }
  };
  const unlockButton = () => el("div", { class: "actions" },
    el("button", { type: "button", class: "btn", onclick: open }, icon("lock"), `Show ${words.title.toLowerCase()}`));
  const locked = () => body.replaceChildren(
    el("p", { class: "small muted", text: "Reelix keeps these behind its admin password, so Starboard asks for it before showing them." }),
    unlockButton());

  const schemaFor = async (c) => {
    if (c.fields) return c;
    return rxCall(kind, "schema", { implementation: c.implementation }, `add ${c.name}`);
  };
  const add = (c) => reopen(async () => {
    const schema = await schemaFor(c);
    if (schema) rxEditPanel(kind, words, schema, null, (r) => { data = { ...data, ...r }; draw(); });
  });
  const change = (i) => reopen(async () => {
    const c = data.catalogue.find((x) => x.implementation === i.implementation) || { implementation: i.implementation, name: i.implementation_name };
    const schema = await schemaFor(c);
    if (schema) rxEditPanel(kind, words, schema, i, (r) => { data = { ...data, ...r }; draw(); });
  });
  const testOne = (i, where) => reopen(async () => {
    where.replaceChildren(el("span", { class: "muted", text: "Testing…" }));
    const r = await rxCall(kind, "test", { item: { id: i.id, implementation: i.implementation, name: i.name, enabled: i.enabled, priority: i.priority, settings: i.settings } }, `test ${i.name}`);
    where.replaceChildren(r ? rxTestResult(r) : "");
  });
  const removeOne = (i) => reopen(async () => {
    const yes = await confirmDialog({ title: `Remove ${i.name}?`, danger: true, confirm: "Remove",
      message: `Reelix stops using ${i.name} and forgets its settings. You can add it again later.` });
    if (!yes) return;
    const r = await rxCall(kind, "remove", { id: i.id }, `remove ${i.name}`);
    if (r) { data = { ...data, ...r }; toast(`${i.name} removed`); draw(); }
  });

  const searchSettings = () => {
    if (!search) return null;
    const rows = [];
    if (search.vpn_available || search.through_vpn) {
      const vpn = el("input", { type: "checkbox", checked: search.through_vpn });
      vpn.addEventListener("change", () => reopen(async () => {
        const r = await rxCall("search", "vpn", { on: vpn.checked }, vpn.checked ? "send Reelix's searches through the VPN" : "stop sending Reelix's searches through the VPN");
        if (!r) { vpn.checked = !vpn.checked; return; }
        search = r; toast(r.done); draw();
      }));
      rows.push(switchRow("Search through the VPN", "Reelix's searches go out through Gluetun, as Prowlarr's did, so your internet provider sees only the VPN. If the VPN is down, searches wait rather than go out without it. Recommended.", vpn));
    } else {
      rows.push(el("p", { class: "small muted", text: "Reelix searches from this computer's own address. Add the VPN (Gluetun) on Settings, Your install to search through it." }));
    }
    const priv = el("input", { type: "checkbox", checked: search.allow_private });
    priv.addEventListener("change", () => reopen(async () => {
      const r = await rxCall("search", "private", { on: priv.checked }, "change which addresses Reelix may reach");
      if (!r) { priv.checked = !priv.checked; return; }
      search = r; toast(r.done); draw();
    }));
    rows.push(switchRow("Addresses on your network", "Lets Reelix reach a site at home, such as your own Jackett. Searching through the VPN needs it too. Otherwise, leave it deactivated.", priv));
    return el("div", { class: "stack-2" }, el("h3", { text: "How Reelix searches" }), rows,
      search.flaresolverr ? el("p", { class: "small muted", text: `Sites with a browser check go through FlareSolverr at ${search.flaresolverr}.` }) : null);
  };

  const draw = () => {
    const items = data.items || [];
    const rows = items.map((i) => {
      const result = el("div", {});
      return el("tr", { "data-key": String(i.id) },
        el("th", { scope: "row", "data-label": words.one[0].toUpperCase() + words.one.slice(1) }, el("strong", { text: i.name }),
          i.name !== i.implementation_name ? el("div", { class: "small muted", text: i.implementation_name }) : null, result),
        el("td", { "data-label": "State" }, rxState(i), i.error || i.status?.last_failure_reason ? el("div", { class: "small muted", text: i.error || i.status.last_failure_reason }) : null),
        kind === "indexers" ? el("td", { "data-label": "Results", class: "small", text: rxResults(i) || "Not searched yet" }) : el("td", { "data-label": "Address", class: "small" }, el("code", { text: i.settings?.url || i.settings?.host || i.settings?.base_url || "" })),
        el("td", { "data-label": "" }, menuButton(`More for ${i.name}`, [
          { label: "Change", icon: "pencil", onSelect: () => later(() => change(i)) },
          { label: "Test", icon: "activity", onSelect: () => later(() => testOne(i, result)) },
          { label: "Remove", icon: "trash-2", danger: true, onSelect: () => later(() => removeOne(i)) }])));
    });
    const table = items.length ? el("div", { class: "table-wrap", "data-stack": "" }, el("table", { class: "table table--fixed table--middle" },
      el("caption", { class: "visually-hidden", text: words.title }),
      el("colgroup", {}, el("col", { class: "col-third" }), el("col", { class: "col-quarter" }), el("col"), el("col", { class: "col-state" })),
      el("thead", {}, el("tr", {}, el("th", { scope: "col", text: words.one[0].toUpperCase() + words.one.slice(1) }), el("th", { scope: "col", text: "State" }),
        el("th", { scope: "col", text: kind === "indexers" ? "Results" : "Address" }), el("th", { scope: "col" }, el("span", { class: "visually-hidden", text: "Actions" })))),
      el("tbody", {}, rows))) : el("p", { class: "muted", text: kind === "indexers" ? "Reelix has no sites to search yet, so it cannot find anything to download. Add one below." : `Reelix has no ${words.many} yet.` });
    const buttons = el("div", { class: "actions" },
      el("button", { type: "button", class: "btn btn--primary", onclick: () => rxAddPanel(kind, words,
        kind === "indexers" ? data.catalogue.filter((c) => c.source === "definition") : data.catalogue, add,
        { have: data.items || [], suggested: data.suggested || [] }) }, icon("plus"), `Add ${words.a}`),
      kind === "indexers" ? el("button", { type: "button", class: "btn", onclick: () => rxAddPanel(kind, { ...words, a: "your own Torznab or Newznab address", many: "kinds" },
        data.catalogue.filter((c) => ["torznab", "newznab"].includes(c.implementation)), add) }, "Add your own Torznab or Newznab address") : null);
    const known = data.definitions ? el("p", { class: "small muted", text: `Reelix knows ${data.definitions.loaded} sites${data.definitions.last_sync ? `, from a list it last updated on ${formatDate(data.definitions.last_sync)}` : ""}. Nothing is added unless you add it.` }) : null;
    const offers = kind === "mediaservers" ? rxOffers(data.offers || [], (r) => { data = { ...data, ...r }; draw(); }) : null;
    // DASH-257: a download app whose address or user differs from what Starboard set up, with Repair.
    const repair = kind === "downloadclients" && data.repair?.length ? notice("warning", "Reelix cannot reach some download apps the way Starboard set them up",
      `${data.repair.join(", ")} ${data.repair.length === 1 ? "has" : "have"} a different address or user name in Reelix. Repair writes the ones Starboard made, so you need not look up a password.`,
      el("button", { type: "button", class: "btn", onclick: (e) => reopen(async () => {
        e.currentTarget.disabled = true;
        const r = await rxCall("downloadclients", "repair", {}, "repair Reelix's download apps");
        if (r) { data = { ...data, ...r }; draw(); }
      }) }, "Repair")) : null;
    redraw(body, [repair, offers, table, buttons, known, kind === "indexers" ? searchSettings() : null].filter(Boolean));
  };
  locked();
  return section(`rx-${kind}`, words.title, description, body);
}

// Jellyfin and Audiobookshelf: connected, ready to connect with the key Starboard has, or waiting for a key.
function rxOffers(offers, done) {
  return el("ul", { class: "rx-picks", role: "list" }, offers.map((o) => {
    const action = o.connected ? null : o.has_key
      ? el("button", { type: "button", class: "btn", onclick: async (e) => {
        e.currentTarget.disabled = true;
        try {
          const r = await rxCall("mediaservers", "connect", { app: o.app }, `connect Reelix to ${o.name}`);
          if (r) { (r.done || []).forEach((line) => toast(line)); done(r); }
        } catch (err) { toast(err.message); }
        finally { if (e.currentTarget?.isConnected) e.currentTarget.disabled = false; }
      } }, `Connect ${o.name}`)
      : el("a", { class: "btn btn--quiet", href: "/settings.html" }, `Add ${o.name}'s API key first`);
    return el("li", { class: "setting" },
      el("div", { class: "setting__text" }, el("span", { class: "setting__label", text: o.name }),
        el("span", { class: "setting__hint", text: o.connected ? `Reelix tells ${o.name} about new files at once (${o.url}).`
          : o.has_key ? `Starboard has ${o.name}'s key, so it can connect them for you.` : `Starboard needs ${o.name}'s API key first.` })),
      el("div", { class: "setting__control" }, o.connected ? (o.error ? chip("Cannot start", "danger") : chip("Connected", "success")) : action));
  }));
}

// Called by startReelix in settings.js: the sections, after Version.
// Naming and background work (DASH-188, DASH-200): the folder and file names Reelix gives films and series, with an
// example of each that changes as you type, and how hard Reelix works in the background.
function rxLibrarySection() {
  const body = el("div", { class: "stack-4", "aria-live": "polite" });
  const labels = { movie_folder_format: ["Film folder", "movie_folder"], movie_file_format: ["Film file", "movie_file"],
    series_folder_format: ["Series folder", "series_folder"], season_folder_format: ["Season folder", "season_folder"],
    standard_episode_format: ["Episode file", "standard_episode"] };
  const open = async () => {
    body.replaceChildren(el("p", { class: "muted", text: "Asking Reelix…" }));
    try {
      const r = await rxCall("library", "open", {}, "show Reelix's naming");
      if (!r) { locked(); return; }
      draw(r);
    } catch (e) { body.replaceChildren(notice("danger", "Reelix could not be asked", e.message), unlock()); }
  };
  const unlock = () => el("div", { class: "actions" }, el("button", { type: "button", class: "btn", onclick: open }, icon("lock"), "Show naming and background work"));
  const locked = () => body.replaceChildren(el("p", { class: "small muted", text: "Reelix keeps these behind its admin password, so Starboard asks for it before showing them." }), unlock());
  const draw = (r) => {
    const inputs = {};
    const examples = {};
    const rows = Object.entries(labels).map(([k, [label, ex]]) => {
      inputs[k] = el("input", { class: "input", value: r.naming[k] || "", spellcheck: "false", autocomplete: "off" });
      examples[k] = el("code", { class: "small", text: r.preview[ex] || "" });
      return el("div", { class: "stack-2" }, field(label, inputs[k]), el("p", { class: "small muted" }, "Example: ", examples[k]));
    });
    const errors = el("div");
    const pace = el("select", { class: "select" }, r.paces.map((p) => el("option", { value: p.value, text: p.label, selected: p.value === r.pace })));
    let timer = null;
    const typed = () => Object.fromEntries(Object.entries(inputs).map(([k, i]) => [k, i.value]));
    const refresh = () => {
      clearTimeout(timer);
      timer = setTimeout(async () => {
        try {
          const p = await rxCall("library", "preview", { naming: typed() }, "show an example");
          if (!p) return;
          for (const [k, [, ex]] of Object.entries(labels)) examples[k].textContent = p[ex] || "";
          errors.replaceChildren(p.errors?.length ? notice("warning", "Reelix cannot use this yet", p.errors.map((e) => e.message).join(". ")) : "");
        } catch (e) { errors.replaceChildren(notice("danger", "No example", e.message)); }
      }, 600);
    };
    Object.values(inputs).forEach((i) => i.addEventListener("input", refresh));
    const note = savedNote("rx-library-saved");
    const save = el("button", { type: "button", class: "btn btn--primary" }, "Save");
    save.addEventListener("click", async () => {
      save.disabled = true;
      try {
        const out = await rxCall("library", "save", { naming: typed(), pace: pace.value }, "change Reelix's naming");
        if (out) { draw(out); showSaved("rx-library-saved"); }
      } catch (e) { errors.replaceChildren(notice("danger", "Not saved", e.message)); }
      finally { save.disabled = false; }
    });
    body.replaceChildren(
      el("p", { class: "small muted" }, "Words in braces are filled in by Reelix, such as ", el("code", { text: "{Movie Title}" }), " and ",
        el("code", { text: "{season}" }), ". Changes apply to files Reelix moves from now on."),
      ...rows, errors,
      field("Background work", pace, { hint: "How hard Reelix works on scans and refreshes. Light suits a small server: playing stays smooth. Changing How much it does in Settings, Performance does not change this." }),
      el("div", { class: "actions" }, save, note));
  };
  locked();
  return section("rx-library", "Naming and background work", "The names Reelix gives film and series folders and files, and how hard it works in the background.", body);
}

// Picture quality (DASH-196, agreed by the owner on 10 November 2026). A: choose a level, HD recommended. B: what the
// level does, in words. C, under Advanced settings: change the level, with its qualities best first (Move up, Move
// down or drag; a tick for each), a Stop upgrading here line, extras as Prefer, Neutral or Never, and the largest file.
function rxQualitySection() {
  const body = el("div", { class: "stack-4" });
  const unlock = () => el("div", { class: "actions" }, el("button", { type: "button", class: "btn", onclick: open }, icon("lock"), "Show picture quality"));
  const locked = () => body.replaceChildren(el("p", { class: "small muted", text: "Reelix keeps these behind its admin password, so Starboard asks for it before showing them." }), unlock());
  async function open() {
    body.replaceChildren(el("p", { class: "muted", text: "Asking Reelix…" }));
    try { const r = await rxCall("quality", "open", {}, "show picture quality"); if (!r) { locked(); return; } draw(r); }
    catch (e) { body.replaceChildren(notice("danger", "Reelix could not be asked", e.message), unlock()); }
  }
  const words = (list, none) => (list.length ? list.join(", ") : none);
  const summary = (lvl) => el("dl", { class: "facts", id: "rx-quality-words" },
    el("dt", { text: "Accepts" }), el("dd", { text: words(lvl.accepts, "Nothing ticked") }),
    el("dt", { text: "Stops upgrading at" }), el("dd", { text: lvl.upgrades ? (lvl.stops_at || "The best it accepts") : "Does not upgrade" }),
    el("dt", { text: "Prefers" }), el("dd", { text: words(lvl.prefers, "Nothing in particular") }),
    el("dt", { text: "Never takes" }), el("dd", { text: words(lvl.never, "Nothing is ruled out") }),
    el("dt", { text: "Upgrades" }), el("dd", { text: lvl.upgrades ? "Yes, when a better copy comes out" : "No, it keeps the first copy" }));
  const editor = (lvl, save) => {
    const name = (row) => row.label;
    const move = (label, dir) => el("button", { type: "button", class: "icon-btn", "data-move": dir, "aria-label": `Move ${label} ${dir}` }, icon(dir === "up" ? "arrow-up" : "arrow-down"));
    const ticks = {};
    const rowNode = (row) => {
      const tick = el("input", { type: "checkbox", checked: row.allowed, "aria-label": `Accept ${name(row)}` });
      ticks[row.key] = tick;
      return el("li", { class: row.allowed ? "sortable__row" : "sortable__row sortable__row--off", "data-value": row.key },
        el("span", { class: "sortable__handle", "aria-hidden": "true" }, icon("grip-vertical")),
        el("label", { class: "sortable__label check" }, tick, el("span", { class: "check__text", text: name(row) })),
        el("span", { class: "sortable__moves" }, move(name(row), "up"), move(name(row), "down")));
    };
    const stopRow = el("li", { class: "sortable__row sortable__row--marker", "data-value": "stop" },
      el("span", { class: "sortable__handle", "aria-hidden": "true" }, icon("grip-vertical")),
      el("span", { class: "sortable__label", text: "Stop upgrading here" }),
      el("span", { class: "sortable__moves" }, move("Stop upgrading here", "up"), move("Stop upgrading here", "down")));
    const list = el("ol", { class: "sortable", id: "rx-quality-order", "aria-label": `${lvl.title}: qualities, best first` });
    lvl.rows.forEach((row) => { if (row.key === lvl.stop) list.append(stopRow); list.append(rowNode(row)); });
    if (!list.contains(stopRow)) list.prepend(stopRow);
    Object.values(ticks).forEach((t) => t.addEventListener("change", () => t.closest(".sortable__row").classList.toggle("sortable__row--off", !t.checked)));
    const extras = lvl.extras.map((x) => el("fieldset", { class: "rx-extra" }, el("legend", { text: x.name }),
      el("div", { class: "segmented" }, ["prefer", "neutral", "never"].map((c) =>
        el("label", {}, el("input", { type: "radio", name: `rx-extra-${x.id}`, value: c, checked: x.choice === c }), el("span", { text: c[0].toUpperCase() + c.slice(1) }))))));
    const upgrades = el("input", { type: "checkbox", id: "rx-quality-upgrades", checked: lvl.upgrades });
    const largest = el("input", { class: "input", id: "rx-quality-largest", inputmode: "decimal", value: lvl.largest_gb ?? "", autocomplete: "off" });
    const go = el("button", { type: "button", class: "btn btn--primary" }, `Save ${lvl.title}`);
    go.addEventListener("click", () => {
      setError(largest, "");
      const changes = {
        order: [...list.children].map((r) => r.dataset.value),
        allowed: Object.fromEntries(Object.entries(ticks).map(([k, t]) => [k, t.checked])),
        upgrades: upgrades.checked,
        extras: Object.fromEntries(lvl.extras.map((x) => [x.id, (body.querySelector(`input[name="rx-extra-${x.id}"]:checked`) || {}).value || "neutral"])),
        largest_gb: largest.value.trim(),
      };
      save(changes, go);
    });
    return el("div", { class: "stack-4", "data-advanced": "" },
      el("h3", { text: `Change ${lvl.title}` }),
      el("p", { class: "small muted", text: "Qualities best first. Tick the ones to accept. Reelix upgrades a film until it has a ticked quality under Stop upgrading here." }),
      list,
      el("label", { class: "check" }, upgrades, el("span", { class: "check__text", text: "Upgrade when a better copy comes out" })),
      lvl.extras.length ? el("div", { class: "stack-2" }, el("h4", { text: "Extras" }),
        el("p", { class: "small muted", text: "Prefer picks a release with it when there is a choice. Never refuses a release with it." }), ...extras) : null,
      field("Largest file, in GB", largest, { hint: "Leave it empty for no limit. Films over this size are not downloaded." }),
      el("div", { class: "actions" }, go));
  };
  const draw = (r) => {
    let shown = r.chosen;
    const render = () => {
      const lvl = r.levels.find((l) => l.id === shown) || r.levels[0];
      if (!lvl) { body.replaceChildren(notice("info", "Reelix has no picture quality levels", "Add one in Reelix itself, then come back.")); return; }
      const save = async (changes, control) => {
        control.disabled = true;
        try { const out = await rxCall("quality", "save", { id: lvl.id, changes }, `save ${lvl.title}`); if (out) { r = out; render(); toast(out.done.join(". ")); } }
        catch (e) { problem(e.message, control); }
        finally { control.disabled = false; }
      };
      const cards = el("div", { class: "option-cards option-cards--row", role: "radiogroup", "aria-label": "Level for new films and series" },
        r.levels.map((l) => {
          const pick = el("input", { type: "radio", name: "rx-level", value: String(l.id), checked: l.id === r.chosen });
          pick.addEventListener("change", async () => {
            try { const out = await rxCall("quality", "choose", { id: l.id }, "choose the level"); if (out) { r = out; shown = l.id; render(); toast(out.done.join(". ")); } }
            catch (e) { problem(e.message, pick); }
          });
          return el("label", { class: "option-card" }, pick, el("span", { class: "stack-1 rx-level" },
            l.recommended ? el("span", { class: "chip", "data-tone": "info", text: "Recommended" }) : null,
            el("strong", { text: l.title }), el("span", { class: "small muted", text: l.line || l.name })));
        }));
      body.replaceChildren(
        el("div", { class: "stack-2" }, el("h3", { text: "Choose a level" }),
          el("p", { class: "small muted", text: "For films and series added from now on. 4K needs about four times the space of HD." }), cards),
        el("div", { class: "stack-2" }, el("h3", { text: `What ${lvl.title} does` }), summary(lvl)),
        editor(lvl, save));
      SharedComponents.setupSortables(body);
      if (typeof applyAdvanced === "function") applyAdvanced();
    };
    render();
  };
  locked();
  return section("rx-quality", "Picture quality", "How good films and series should be, and how far Reelix upgrades them.", body);
}

// The basics (DASH-226): films and series information, picture quality, language and who can ask, in the approved
// order. Each change saves at once; the TMDB key has its own Test and Save.
function rxBasicsSection() {
  const body = el("div", { class: "stack-4", "aria-live": "polite" });
  const unlock = () => el("div", { class: "actions" }, el("button", { type: "button", class: "btn", onclick: open }, icon("lock"), "Show the basic settings"));
  const locked = () => body.replaceChildren(el("p", { class: "small muted", text: "Reelix keeps these behind its admin password, so Starboard asks for it before showing them." }), unlock());
  async function open() {
    body.replaceChildren(el("p", { class: "muted", text: "Asking Reelix…" }));
    try { const r = await rxCall("basics", "open", {}, "show Reelix's basic settings"); if (!r) { locked(); return; } draw(r); }
    catch (e) { body.replaceChildren(notice("danger", "Reelix could not be asked", e.message), unlock()); }
  }
  const save = async (changes, what, control) => {
    if (control) control.disabled = true;
    try { const r = await rxCall("basics", "save", { changes }, what); if (r) { draw(r); toast(r.done.join(". ") || "Saved"); } }
    catch (e) { problem(e.message, control); }
    finally { if (control) control.disabled = false; }
  };
  const draw = (r) => {
    const key = el("input", { class: "input", type: "password", autocomplete: "off", spellcheck: "false", id: "rx-tmdb" });
    const said = el("div", { "aria-live": "polite" });
    const test = el("button", { type: "button", class: "btn" }, "Test the key");
    test.addEventListener("click", async () => {
      try { const t = await rxCall("basics", "test-tmdb", { tmdb: key.value.trim() }, "test the key"); if (t) said.replaceChildren(notice("success", "It works", t.message)); }
      catch (e) { said.replaceChildren(notice("danger", "It did not work", e.message)); }
    });
    const keep = el("button", { type: "button", class: "btn btn--primary" }, "Save the key");
    keep.addEventListener("click", () => key.value.trim() ? save({ tmdb: key.value.trim() }, "save the TMDB key", keep) : setError(key, "Paste the key first"));
    const lang = el("select", { class: "select", id: "rx-language" }, r.languages.map((c) => el("option", { value: c.value, text: c.label, selected: c.value === r.language })));
    lang.addEventListener("change", () => save({ language: lang.value }, "change the language", lang));
    const who = el("select", { class: "select", id: "rx-who" }, r.whos.map((w) => el("option", { value: w.value, text: w.label, selected: w.value === r.who })));
    who.addEventListener("change", () => save({ who: who.value }, "change who can ask", who));
    body.replaceChildren(
      el("div", { class: "stack-2" }, el("h3", { text: "Films and series information" }),
        el("p", { class: "small muted", text: "A free key from The Movie Database. Without it Reelix uses open data and matches fewer titles." }),
        el("p", {}, chip(r.tmdb ? "Connected" : "No key yet", r.tmdb ? "success" : "warning")),
        field(r.tmdb ? "Change the key" : "TMDB key", key, { hint: "Paste the API Read Access Token or the API key from themoviedb.org, Settings, API." }),
        el("div", { class: "actions" }, keep, test), said),
      field("Language", lang, { hint: "Reelix skips releases in other languages, unless you choose any language." }),
      field("Who can ask", who, { hint: "For people who get a Reelix account from now on. Settings, Reelix, People changes those who have one." }));
  };
  locked();
  return section("rx-basics", "Basic settings", "What Reelix looks for, and how good it should be.", body);
}

// A section that opens behind the Reelix password (the same pattern as the others), drawn by `draw(answer, body)`.
function rxLockedSection(id, title, about, kind, openBody, draw, what) {
  const body = el("div", { class: "stack-4", "aria-live": "polite" });
  const unlock = () => el("div", { class: "actions" }, el("button", { type: "button", class: "btn", onclick: open }, icon("lock"), `Show ${title.toLowerCase()}`));
  const locked = () => body.replaceChildren(el("p", { class: "small muted", text: "Reelix keeps these behind its admin password, so Starboard asks for it before showing them." }), unlock());
  async function open() {
    body.replaceChildren(el("p", { class: "muted", text: "Asking Reelix…" }));
    try { const r = await rxCall(kind, "open", openBody, what); if (!r) { locked(); return; } draw(r, body); }
    catch (e) { body.replaceChildren(notice("danger", "Reelix could not be asked", e.message), unlock()); }
  }
  locked();
  return section(id, title, about, body);
}

// Information, Files, Requests, Books and Music (DASH-193, 195, 197): one form each, from Reelix's own settings.
function rxFormSection(name, title, about) {
  const draw = (r, body) => {
    const read = [];
    const rows = r.fields.map((f) => {
      const id = `rx-${name}-${f.key}`;
      let input;
      if (f.type === "bool") {
        input = el("input", { type: "checkbox", id, checked: !!f.value });
        read.push(() => [f.key, input.checked]);
        return switchRow(f.label, f.hint, input);
      }
      if (f.type === "select") {
        input = el("select", { class: "select", id }, f.choices.map((c) => el("option", { value: c.value, text: c.label, selected: c.value === f.value })));
      } else {
        input = el("input", { class: "input", id, type: f.type === "secret" ? "password" : "text", autocomplete: "off", spellcheck: "false",
          inputmode: f.type.includes("number") ? "numeric" : null, value: f.value ?? "" });
      }
      read.push(() => [f.key, input.value]);
      return field(f.label, input, { hint: f.hint });
    });
    const save = el("button", { type: "button", class: "btn btn--primary" }, "Save");
    const note = savedNote(`rx-${name}-saved`);
    save.addEventListener("click", async () => {
      save.disabled = true;
      try {
        const out = await rxCall("form", "save", { name, values: Object.fromEntries(read.map((fn) => fn())) }, `change ${title.toLowerCase()}`);
        if (out) { draw(out, body); showSaved(`rx-${name}-saved`); }
      } catch (e) { problem(e.message, save); }
      finally { save.disabled = false; }
    });
    body.replaceChildren(el("div", { class: "form-stack" }, ...rows), el("div", { class: "actions" }, save, note));
  };
  return rxLockedSection(`rx-${name}`, title, about, "form", { name }, draw, `show ${title.toLowerCase()}`);
}

// Folders (DASH-194): the library folders for each kind, with Add and Remove.
function rxFoldersSection() {
  const draw = (r, body) => {
    const rows = r.folders.map((f) => {
      const remove = el("button", { type: "button", class: "btn btn--quiet btn--compact" }, "Remove", el("span", { class: "visually-hidden", text: ` ${f.path}` }));
      remove.addEventListener("click", async () => {
        if (!await confirmDialog({ title: `Take ${f.path} out of Reelix?`, confirm: "Take out", danger: true,
          message: "Reelix stops using this folder for new files. The files in it stay on disk." })) return;
        try { const out = await rxCall("folders", "remove", { kind: f.kind, id: f.id }, "change Reelix's folders"); if (out) { draw(out, body); toast(out.done); } }
        catch (e) { problem(e.message, remove); }
      });
      return el("li", { class: "row row--no-lead" }, el("div", {}, el("div", { class: "row__title", text: f.path }),
        el("div", { class: "row__meta", text: [f.kind_name, f.free != null ? `${formatBytes(f.free)} free` : "", f.ok ? "" : "Reelix cannot reach it"].filter(Boolean).join(" · ") })),
        el("div", { class: "row__side" }, remove));
    });
    const kind = el("select", { class: "select", id: "rx-folder-kind" }, r.kinds.map((k) => el("option", { value: k.value, text: k.label })));
    const path = el("input", { class: "input", id: "rx-folder-path", placeholder: "/data/media/", spellcheck: "false", autocomplete: "off" });
    const add = el("button", { type: "button", class: "btn" }, "Add the folder");
    add.addEventListener("click", async () => {
      try { const out = await rxCall("folders", "add", { kind: kind.value, path: path.value.trim() }, "change Reelix's folders"); if (out) { draw(out, body); toast(out.done); } }
      catch (e) { setError(path, e.message); path.focus(); }
    });
    body.replaceChildren(el("ul", { class: "rows" }, rows),
      el("div", { class: "form-stack" }, field("For", kind), field("Folder, as Reelix sees it", path, { hint: "Inside the media folder, such as /data/media/films-4k. Make the folder on disk first." })),
      el("div", { class: "actions" }, add));
  };
  return rxLockedSection("rx-folders", "Folders", "Where Reelix keeps each kind of media.", "folders", {}, draw, "show Reelix's folders");
}

// People (DASH-199): who has a Reelix account and what each may do.
function rxPeopleSection() {
  const draw = (r, body) => {
    body.replaceChildren(el("p", { class: "small", text: r.about }), el("ul", { class: "rows" }, r.people.map((p) => {
      const pick = el("select", { class: "select", "aria-label": `What ${p.name} may do` }, r.roles.map((o) => el("option", { value: o.value, text: o.label, selected: o.value === p.role })));
      pick.addEventListener("change", async () => {
        try { const out = await rxCall("people", "role", { id: p.id, role: pick.value }, "change what people may do"); if (out) { draw(out, body); toast(out.done); } }
        catch (e) { problem(e.message, pick); }
      });
      return el("li", { class: "row row--no-lead" }, el("div", {}, el("div", { class: "row__title", text: p.name }),
        el("div", { class: "row__meta", text: [p.user, p.from ? `signs in with ${p.from}` : ""].filter(Boolean).join(" · ") })), el("div", { class: "row__side" }, pick));
    })));
  };
  return rxLockedSection("rx-people", "People", "Who has a Reelix account, and what each may do.", "people", {}, draw, "show Reelix's people");
}

// YouTube and Spotify, in the full version only (DASH-216, DASH-126): on or off, the folder (inside /data, with the
// rest of the media), the tools Reelix needs, and Connect Spotify: open Spotify's page, agree, then paste the address
// it went to.
function rxDirectSection() {
  const draw = (r, body) => {
    const on = el("input", { type: "checkbox", id: "rx-direct-on", checked: r.on });
    const folder = el("input", { class: "input", id: "rx-direct-folder", value: r.folder, spellcheck: "false", autocomplete: "off" });
    const save = el("button", { type: "button", class: "btn btn--primary" }, "Save");
    save.addEventListener("click", async () => {
      try { const o = await rxCall("direct", "save", { on: on.checked, folder: folder.value.trim() }, "change YouTube and Spotify"); if (o) { draw(o, body); toast(o.done); } }
      catch (e) { setError(folder, e.message); folder.focus(); }
    });
    const sp = r.spotify;
    const address = el("input", { class: "input", id: "rx-spotify-back", autocomplete: "off", spellcheck: "false", placeholder: "https://" });
    const connect = el("button", { type: "button", class: "btn" }, sp.connected ? "Connect again" : "Connect Spotify");
    const finish = el("button", { type: "button", class: "btn btn--primary" }, "Finish connecting");
    const step2 = el("div", { class: "form-stack", hidden: true }, field("The address Spotify went to", address,
      { hint: "After you agree in Spotify, the page may not open. Copy its whole address from the address bar and paste it here." }), el("div", { class: "actions" }, finish));
    connect.addEventListener("click", async () => {
      try { const o = await rxCall("direct", "spotify-start", {}, "connect Spotify"); if (o?.url) { window.open(o.url, "_blank", "noopener"); step2.hidden = false; address.focus(); } }
      catch (e) { problem(e.message, connect); }
    });
    finish.addEventListener("click", async () => {
      try { const o = await rxCall("direct", "spotify-finish", { address: address.value.trim() }, "connect Spotify"); if (o) { draw(o, body); toast(o.done); } }
      catch (e) { setError(address, e.message); address.focus(); }
    });
    const off = sp.connected ? el("button", { type: "button", class: "btn btn--quiet" }, "Disconnect Spotify") : null;
    off?.addEventListener("click", async () => { try { const o = await rxCall("direct", "spotify-off", {}, "disconnect Spotify"); if (o) { draw(o, body); toast(o.done); } } catch (e) { problem(e.message, off); } });
    body.replaceChildren(
      r.folder_warning ? notice("warning", "Downloads go to the wrong place", r.folder_warning) : null,
      switchRow("YouTube and Spotify downloads", "Paste a link on Downloads, From a link.", on),
      field("Folder, inside /data", folder, { hint: "Such as /data/downloads/direct, or /data/media/music to put music straight into the library." }),
      el("div", { class: "actions" }, save),
      el("p", { class: "small", text: `Tools: ${r.tools.map((t) => `${t.tool} ${t.ok ? "ready" : "missing"}`).join(", ") || "not reported"}.` }),
      el("h3", { text: "Spotify" }),
      el("p", {}, chip(sp.connected ? `Connected${sp.user ? ` as ${sp.user}` : ""}` : sp.waiting ? "Waiting for you to finish" : "Not connected", sp.connected ? "success" : "muted")),
      sp.problem ? el("p", { class: "small", text: sp.problem }) : null,
      el("div", { class: "actions" }, connect, off), step2);
  };
  return rxLockedSection("rx-direct", "YouTube and Spotify", "Downloads from a YouTube or Spotify link, in the full version of Reelix.", "direct", {}, draw, "show YouTube and Spotify");
}

function reelixAdminSections() {
  const holder = el("div", { class: "rx-admin" });
  api("/api/reelix/admin/about").then((a) => {
    rxAbout = a;
    if (!a.address) {
      holder.replaceChildren(section("rx-admin", "Sites, download apps and media servers", "",
        notice("info", "Reelix is not on your dashboard", "Add Reelix in Settings, Manage apps, or install it with Install apps, and its settings show here.")));
      return;
    }
    const full = a.edition === "full";
    holder.replaceChildren(
      rxBasicsSection(),
      rxQualitySection(),
      ...(full ? [rxDirectSection()] : []),  // replaceChildren writes a null as the word "null"
      rxKindSection("indexers", "The sites Reelix searches for films, series, books and music. Nothing is added unless you add it."),
      rxKindSection("mediaservers", "Reelix tells Jellyfin and Audiobookshelf about each new file, so it shows in them at once."),
      rxKindSection("downloadclients", "The apps that download what Reelix chooses."),
      rxLibrarySection(),
      rxFoldersSection(),
      rxFormSection("information", "Information", "Where Reelix finds details about films and series."),
      rxFormSection("files", "Files", "How Reelix moves finished downloads into your library."),
      rxFormSection("requests", "Requests", "What happens when someone asks for something."),
      rxKindSection("notifications", "Where Reelix tells you what it did: Discord, email, ntfy and others."),
      rxKindSection("importlists", "Lists Reelix follows, such as a Trakt or IMDb list, to add what is on them."),
      rxPeopleSection(),
      rxFormSection("books", "Books", "How Reelix handles books and audiobooks."),
      rxFormSection("music", "Music", "How Reelix handles albums."));
  }).catch((e) => holder.replaceChildren(notice("danger", "Could not look", e.message)));
  return holder;
}
