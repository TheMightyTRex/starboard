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
    redraw(body, [offers, table, buttons, known, kind === "indexers" ? searchSettings() : null].filter(Boolean));
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
      : el("a", { class: "btn btn--quiet", href: "/apps-services.html" }, `Add ${o.name}'s API key first`);
    return el("li", { class: "setting" },
      el("div", { class: "setting__text" }, el("span", { class: "setting__label", text: o.name }),
        el("span", { class: "setting__hint", text: o.connected ? `Reelix tells ${o.name} about new files at once (${o.url}).`
          : o.has_key ? `Starboard has ${o.name}'s key, so it can connect them for you.` : `Starboard needs ${o.name}'s API key first.` })),
      el("div", { class: "setting__control" }, o.connected ? (o.error ? chip("Cannot start", "danger") : chip("Connected", "success")) : action));
  }));
}

// Called by startReelix in settings.js: the sections, after Version.
function reelixAdminSections() {
  const holder = el("div", { class: "rx-admin" });
  api("/api/reelix/admin/about").then((a) => {
    rxAbout = a;
    if (!a.address) {
      holder.replaceChildren(section("rx-admin", "Sites, download apps and media servers", "",
        notice("info", "Reelix is not on your dashboard", "Add Reelix in Settings, Manage apps, or install it with Install apps, and its settings show here.")));
      return;
    }
    holder.replaceChildren(
      rxKindSection("indexers", "The sites Reelix searches for films, series, books and music. Nothing is added unless you add it."),
      rxKindSection("mediaservers", "Reelix tells Jellyfin and Audiobookshelf about each new file, so it shows in them at once."),
      rxKindSection("downloadclients", "The apps that download what Reelix chooses."));
  }).catch((e) => holder.replaceChildren(notice("danger", "Could not look", e.message)));
  return holder;
}
