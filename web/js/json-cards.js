// Custom cards for any service's JSON (DASH-555): System, Apps, Other services lists them and opens the slide-out where one
// is made: a name, the address, an optional key, how often it may be asked, and the fields to show (chosen from what the
// address answers, each with a label, a unit and a rule for its status). Nothing here asks a service at rest: the list
// shows what was last learned, a card is asked when the dashboard shows it, and the buttons here ask once when pressed.

const JSON_CARDS = { list: null };
const RULE_WORDS = { "": "No rule", above: "Good when the value is more than", below: "Good when the value is less than", equals: "Good when the value is",
  not_equals: "Good when the value is not", contains: "Good when the value contains", not_contains: "Good when the value does not contain" };
const REFRESH_WORDS = { 60: "1 minute", 300: "5 minutes", 900: "15 minutes", 1800: "30 minutes", 3600: "1 hour" };
const BAD_WORDS = { warning: "Needs attention", problem: "Not working" };
const STATE_CHIP = { ok: ["Healthy", "success"], warning: ["Needs attention", "warning"], problem: ["Not working", "danger"] };

function jsonCardState(last) {
  if (!last) return ["Not checked", "muted"];
  if (last.problem) return ["Not working", "danger"];
  return STATE_CHIP[last.state] || ["Answering", "success"];
}

function jsonCardRow(c) {
  const [words, tone] = jsonCardState(c.last);
  const meta = [shortUrl(c.url), `${c.fields.length} ${c.fields.length === 1 ? "field" : "fields"}`, `asked at most every ${REFRESH_WORDS[c.refresh] || "minute"}`,
    c.last ? `last asked ${timeAgo((c.last.asked || 0) * 1000)}` : "not asked yet in this run"];
  if (c.last?.problem) meta.push(c.last.problem);
  return el("li", { class: "row row--lead row--opens", "data-key": c.id },
    el("span", { class: "app-icon", "aria-hidden": "true" }, icon("list", 20)),
    el("div", {}, el("div", { class: "row__title" }, el("button", { type: "button", "aria-haspopup": "dialog", "data-json-card": c.id, text: c.name,
      onclick: (e) => jsonCardEditor(c, e.currentTarget) })), el("div", { class: "row__meta", text: meta.join(" · ") })),
    el("div", { class: "row__side" }, chip(words, tone)));
}

async function jsonCardsLoad() {
  try { JSON_CARDS.list = await api("/api/json-cards"); } catch (e) {
    $("#json-cards").replaceChildren(el("li", { class: "row row--no-lead" }, el("p", { role: "alert", text: `Could not load your custom cards: ${e.message}` })));
    return;
  }
  jsonCardsDraw();
}

function jsonCardsDraw() {
  const l = JSON_CARDS.list;
  $("#json-cards").replaceChildren(...l.cards.map(jsonCardRow));
  $("#json-cards-empty").hidden = !!l.cards.length;
  $("#add-json-card").disabled = l.cards.length >= l.max;
  const id = "json-outside";
  const box = el("input", { type: "checkbox", role: "switch", id, checked: l.allow_outside, "aria-describedby": `${id}-h` });
  box.addEventListener("change", async () => {
    const want = box.checked;
    try {
      JSON_CARDS.list = await api("/api/json-cards/allow-outside", { method: "POST", body: { allow: want } });
      jsonCardsDraw();
      settingSaved(want ? "Allowed" : "Home network only");
      $(`#${id}`)?.focus();
    } catch (e) { box.checked = !want; problem(e.message, box); }
  });
  $("#json-cards-settings").replaceChildren(el("li", { class: "setting" },
    el("div", { class: "setting__text" }, el("label", { class: "setting__label", for: id, text: "Allow addresses outside your home network" }),
      el("span", { class: "setting__hint", id: `${id}-h`, text: "Not active: a custom card asks only this computer and your home network (10.x, 172.16 to 172.31, 192.168.x, and Tailscale's 100.64 to 100.127). Active: it may also ask public addresses, and a key is then sent over https:// only. Cloud metadata and link-local addresses are never asked." })),
    el("div", { class: "setting__control" }, el("label", { class: "switch", for: id }, box))));
}

function jsonCardsStart() {
  $("#add-json-card").addEventListener("click", (e) => jsonCardEditor(null, e.currentTarget));
  return jsonCardsLoad();
}

// What a card shows, as the dashboard shows it: a small table of keys and values, each with its own status when it has a rule.
function jsonCardTable(rows) {
  return el("dl", { class: "facts json-card__facts" }, rows.flatMap((r) => {
    const st = STATE_CHIP[r.state];
    return [el("dt", { text: r.label }), el("dd", {}, r.value, r.unit ? ` ${r.unit}` : null, st ? " " : null, st ? chip(st[0], st[1]) : null)];
  }));
}

function jsonCardEditor(card, opener) {
  const isNew = !card;
  const list = JSON_CARDS.list;
  const chosen = (card?.fields || []).map((f) => ({ path: f.path, label: f.label, unit: f.unit || "", op: f.rule?.op || "", value: f.rule?.value || "", bad: f.rule?.bad || "warning" }));
  let n = 0;
  const uid = (name) => `jc-${name}-${++n}`;
  const f = {
    name: el("input", { type: "text", class: "input", id: "jc-name", value: card?.name || "", maxlength: "40", autocomplete: "off", "aria-required": "true" }),
    url: el("input", { type: "url", class: "input", id: "jc-url", value: card?.url || "", maxlength: "300", autocomplete: "off", spellcheck: "false", placeholder: "http://192.168.1.20:8080/api/status", "aria-required": "true", "aria-describedby": "jc-url-h" }),
    key: el("input", { type: "password", class: "input", id: "jc-key", autocomplete: "off", spellcheck: "false", "aria-describedby": "jc-key-h", placeholder: card?.has_key ? "Saved: leave blank to keep it" : "" }),
    style: el("select", { class: "select", id: "jc-style" }, Object.entries(list.key_styles).map(([v, t]) => el("option", { value: v, text: t, selected: v === (card?.key_style || "x-api-key") }))),
    refresh: el("select", { class: "select", id: "jc-refresh", "aria-describedby": "jc-refresh-h" }, list.refresh.map((v) => el("option", { value: v, text: REFRESH_WORDS[v], selected: v === (card?.refresh || 60) }))),
    clear: el("input", { type: "checkbox", id: "jc-clear" }),
  };
  const status = el("p", { class: "small", role: "status", id: "jc-status" });
  const choices = el("div", { class: "stack-2", id: "jc-choices" });
  const chosenBox = el("div", { class: "stack-2", id: "jc-chosen" });
  const preview = el("div", { class: "stack-2", id: "jc-preview", "aria-live": "polite" });

  const field = (label, control, hint, id) => el("div", { class: "field" }, el("label", { for: control.id, text: label }), control, hint ? el("p", { class: "hint", id, text: hint }) : null);
  const form = el("form", { class: "stack-4", novalidate: true, id: "jc-form" },
    field("Name", f.name, "Shown at the top of the card."),
    field("Address", f.url, "The address of the service's JSON answer. Your home network only, unless you allow others in Other services.", "jc-url-h"),
    el("div", { class: "field" }, el("label", { for: "jc-key", text: "Key (optional)" }), f.key,
      el("p", { class: "hint", id: "jc-key-h", text: card?.has_key ? "A key is saved. It is never shown again, and it goes only to this address." : "Kept on this server like your apps' keys, and sent only to this address." })),
    card?.has_key ? el("label", { class: "check", for: "jc-clear" }, f.clear, el("span", { class: "check__text", text: "Remove the saved key" })) : null,
    field("How the key is sent", f.style),
    field("Ask no more often than", f.refresh, "The answer is kept for this long, however many people have the dashboard open. Nothing is asked while no dashboard shows the card.", "jc-refresh-h"),
    el("div", { class: "stack-2" },
      el("h3", { text: "Fields to show" }),
      el("p", { class: "small muted", text: "Ask the address once to find out what it answers, then tick the fields you want. Or enter a field's path, such as data.queue.total." }),
      el("div", { class: "actions" }, el("button", { type: "button", class: "btn", id: "jc-ask" }, icon("search"), "Ask the address for its fields")),
      status, choices,
      el("div", { class: "field" }, el("label", { for: "jc-path", text: "Add a field by its path" }),
        el("div", { class: "actions" }, el("input", { type: "text", class: "input", id: "jc-path", maxlength: "200", autocomplete: "off", spellcheck: "false", placeholder: "data.queue.total" }),
          el("button", { type: "button", class: "btn", id: "jc-add-path" }, "Add"))),
      chosenBox),
    preview);
  const save = el("button", { type: "submit", form: "jc-form", class: "btn btn--primary" }, icon("check"), isNew ? "Add card" : "Save");
  const foot = [save, el("button", { type: "button", class: "btn", "data-closes": true, text: "Cancel" })];
  let panel;

  const label = (path) => path.split(".").pop();
  const addField = (path) => { if (!chosen.some((c) => c.path === path)) chosen.push({ path, label: label(path), unit: "", op: "", value: "", bad: "warning" }); };

  function drawChosen(focusAt) {
    chosenBox.replaceChildren(
      el("h3", { id: "jc-chosen-h", text: `On the card (${chosen.length})` }),
      ...(chosen.length ? [] : [el("p", { class: "small muted", text: "No fields chosen yet." })]),
      ...chosen.map((c, i) => {
        const p = `jc-f${i}`;
        const label = el("input", { type: "text", class: "input", id: `${p}-label`, value: c.label, maxlength: "40", autocomplete: "off" });
        const unit = el("input", { type: "text", class: "input", id: `${p}-unit`, value: c.unit, maxlength: "12", autocomplete: "off", "aria-describedby": `${p}-unit-h` });
        const op = el("select", { class: "select", id: `${p}-op` }, Object.entries(RULE_WORDS).map(([v, t]) => el("option", { value: v, text: t, selected: v === c.op })));
        const value = el("input", { type: "text", class: "input", id: `${p}-value`, value: c.value, maxlength: "60", autocomplete: "off" });
        const bad = el("select", { class: "select", id: `${p}-bad` }, Object.entries(BAD_WORDS).map(([v, t]) => el("option", { value: v, text: t, selected: v === c.bad })));
        const more = el("div", { class: "stack-2", hidden: !c.op }, field("Value to compare with", value), field("Otherwise show", bad));
        label.addEventListener("input", () => { c.label = label.value; });
        unit.addEventListener("input", () => { c.unit = unit.value; });
        value.addEventListener("input", () => { c.value = value.value; });
        bad.addEventListener("change", () => { c.bad = bad.value; });
        op.addEventListener("change", () => { c.op = op.value; more.hidden = !c.op; });
        const move = (by) => () => { const j = i + by; [chosen[i], chosen[j]] = [chosen[j], chosen[i]]; drawChosen(`jc-f${j}-${by < 0 ? "up" : "down"}`); announce(`${c.label || c.path} moved ${by < 0 ? "earlier" : "later"}, now number ${j + 1} of ${chosen.length}`); };
        const up = el("button", { type: "button", class: "icon-btn", id: `${p}-up`, "aria-label": `Move ${c.label || c.path} earlier`, disabled: i === 0, onclick: move(-1) }, icon("arrow-up"));
        const down = el("button", { type: "button", class: "icon-btn", id: `${p}-down`, "aria-label": `Move ${c.label || c.path} later`, disabled: i === chosen.length - 1, onclick: move(1) }, icon("arrow-down"));
        const remove = el("button", { type: "button", class: "btn btn--quiet btn--compact", id: `${p}-remove`, onclick: () => {
          chosen.splice(i, 1);
          drawChosen(chosen.length ? `jc-f${Math.min(i, chosen.length - 1)}-label` : "jc-path");
          for (const box of choices.querySelectorAll("input[data-path]")) box.checked = chosen.some((x) => x.path === box.dataset.path);
          announce(`${c.label || c.path} removed`);
        } }, "Remove", el("span", { class: "visually-hidden", text: ` ${c.label || c.path}` }));
        return el("fieldset", { class: "stack-2 json-card__field" }, el("legend", { text: c.path }),
          field("Label", label), field("Unit (optional)", unit, "Such as GB, items or %. Shown after a number or a word.", `${p}-unit-h`),
          field("Status rule", op), more, el("div", { class: "actions" }, up, down, remove));
      }));
    if (focusAt) document.getElementById(focusAt)?.focus();
  }

  function drawChoices(found, more) {
    const filter = el("input", { type: "search", class: "input", id: "jc-filter", autocomplete: "off", "aria-describedby": "jc-count" });
    const count = el("p", { class: "small muted", id: "jc-count", role: "status" });
    const rows = found.map((x, i) => {
      const id = `jc-pick-${i}`;
      const box = el("input", { type: "checkbox", id, "data-path": x.path, checked: chosen.some((c) => c.path === x.path) });
      box.addEventListener("change", () => {
        if (box.checked) addField(x.path); else chosen.splice(chosen.findIndex((c) => c.path === x.path), 1);
        drawChosen();
        announce(`${box.checked ? "Added" : "Removed"} ${x.path}. ${chosen.length} on the card`);
      });
      return el("li", { class: "row row--no-lead", "data-find": `${x.path} ${x.sample}`.toLowerCase() },
        el("label", { class: "check", for: id }, box, el("span", { class: "check__text" }, el("code", { text: x.path }), el("span", { class: "row__meta", text: x.sample }))));
    });
    const showCount = () => {
      const q = filter.value.trim().toLowerCase();
      let shown = 0;
      for (const r of rows) { r.hidden = !!q && !r.dataset.find.includes(q); if (!r.hidden) shown++; }
      count.textContent = `${shown} of ${found.length} fields${more ? " (the first ones; type a path to add another)" : ""}`;
    };
    filter.addEventListener("input", showCount);
    showCount();
    choices.replaceChildren(field("Find a field", filter), count, el("ul", { class: "rows json-card__choices", "aria-label": "Fields the address answers with" }, rows));
  }

  const body = () => ({ id: card?.id, name: f.name.value, url: f.url.value, key: f.key.value, key_style: f.style.value, refresh: Number(f.refresh.value), clear_key: f.clear.checked });

  $("#jc-ask", form).addEventListener("click", async (e) => {
    const button = e.currentTarget;
    if (!f.url.value.trim()) { problem("Enter the address first", f.url); return; }
    button.setAttribute("aria-disabled", "true");
    status.textContent = "Asking the address…";
    try {
      const got = await api("/api/json-cards/probe", { method: "POST", body: body() });
      status.textContent = got.fields.length ? `It answered with ${got.type === "list" ? "a list" : "an object"}. Choose the fields to show.` : "It answered, but with no fields to choose.";
      drawChoices(got.fields, got.more);
    } catch (err) { status.textContent = ""; problem(err.message, button); } finally { button.removeAttribute("aria-disabled"); }
  });
  $("#jc-add-path", form).addEventListener("click", () => {
    const input = $("#jc-path", form);
    const path = input.value.trim().replace(/\[(\d+)\]/g, ".$1").replace(/^\./, "");
    if (!path) { problem("Enter the path to a field, such as data.queue.total", input); return; }
    if (chosen.some((c) => c.path === path)) { problem("That field is already on the card", input); return; }
    if (chosen.length >= 20) { problem("A card shows 20 fields at most", input); return; }
    addField(path);
    input.value = "";
    drawChosen(`jc-f${chosen.length - 1}-label`);
    announce(`Added ${path}`);
  });
  $("#jc-path", form).addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); $("#jc-add-path", form).click(); } });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!f.name.value.trim()) { problem("Enter a name for the card", f.name); f.name.focus(); return; }
    if (!f.url.value.trim()) { problem("Enter the address of the service's JSON", f.url); f.url.focus(); return; }
    if (!chosen.length) { problem("Choose at least one field to show", $("#jc-ask", form)); $("#jc-ask", form).focus(); return; }
    const fields = chosen.map((c) => ({ path: c.path, label: c.label, unit: c.unit, rule: c.op ? { op: c.op, value: c.value, bad: c.bad } : null }));
    save.setAttribute("aria-disabled", "true");
    try {
      const done = await api("/api/json-cards", { method: "POST", body: { ...body(), fields } });
      JSON_CARDS.list = { ...JSON_CARDS.list, cards: done.cards, allow_outside: done.allow_outside };
      jsonCardsDraw();
      panel.close();
      const note = $("#json-cards-saved");
      if (note) window.SharedComponents.savedNote(note, isNew ? "Added. Put it on the dashboard with Edit dashboard, Add a card" : "Saved");
      announce(isNew ? `${done.card.name} added. Put it on the dashboard with Edit dashboard, then Add a card.` : `${done.card.name} saved.`);
      setTimeout(() => ($(`[data-json-card="${done.card.id}"]`) || $("#add-json-card"))?.focus(), 0);
    } catch (err) {
      const near = /address|home network|http|redirect|different server/i.test(err.message) ? f.url : /name/i.test(err.message) ? f.name : save;
      problem(err.message, near);
    } finally { save.removeAttribute("aria-disabled"); }
  });

  if (card) {
    const ask = el("button", { type: "button", class: "btn", id: "jc-now" }, icon("refresh-cw"), "Ask now");
    ask.addEventListener("click", async () => {
      ask.setAttribute("aria-disabled", "true");
      preview.replaceChildren(el("p", { class: "small muted", text: "Asking…" }));
      try {
        const got = await api(`/api/json-cards/${card.id}/answer?fresh=1`);
        preview.replaceChildren(el("h3", { text: "What the card shows now" }), got.problem ? el("p", { role: "alert", text: got.problem }) : jsonCardTable(got.items));
        const i = JSON_CARDS.list.cards.findIndex((c) => c.id === card.id);
        if (i >= 0) { JSON_CARDS.list.cards[i].last = { state: got.state, problem: got.problem, asked: got.asked }; jsonCardsDraw(); }
      } catch (err) { preview.replaceChildren(); problem(err.message, ask); } finally { ask.removeAttribute("aria-disabled"); }
    });
    const remove = el("button", { type: "button", class: "btn btn--danger", id: "jc-remove" }, icon("trash-2"), "Remove card");
    remove.addEventListener("click", async () => {
      const yes = await confirmDialog({ title: `Remove ${card.name}?`, message: "The card goes from Other services and from the dashboard. The service itself is not touched. The saved key is forgotten.", confirm: "Remove", danger: true });
      if (!yes) { remove.focus(); return; }
      try {
        JSON_CARDS.list = await api("/api/json-cards/delete", { method: "POST", body: { id: card.id } });
        jsonCardsDraw();
        panel.close();
        announce(`${card.name} removed.`);
        setTimeout(() => ($("#json-cards [data-json-card]") || $("#add-json-card"))?.focus(), 0);
      } catch (err) { problem(err.message, remove); }
    });
    foot.push(ask, remove);
  }

  panel = sidePanel({ title: isNew ? "Add a custom card" : card.name, opener, wide: true, body: [form], foot });
  drawChosen();
}
