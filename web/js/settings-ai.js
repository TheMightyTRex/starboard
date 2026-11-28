// Settings, Security, Connect an AI tool (DASH-627, release 1 of the AI assistant family).
//
// One wizard, built from the design system's shared wizard (the part wizard-steps, docs/WIZARD.md, Variants, "Step in script"):
// which AI tool, where it runs, what it may read, when the key ends, what to call it, then Check your answers. Nothing is
// turned on and no key is made until the last button. The last button asks for the password, turns AI tools on and makes one
// named key that only reads (POST /api/ai-tools/connect), and the page then shows the address and the key once, with the
// set-up for the chosen tool and how to reach Starboard away from home over Tailscale Serve, never Funnel.
// The words come from the server (starboard/ai_tools.py), so the page, the help and the tests say the same.
// Under the wizard: the keys made here (name, kind, last used, ends, Revoke), what AI tools did lately, and the off switch.
// Nothing here polls: the page reads once when it opens and again after something is changed.

const AI_PATH = "/api/v1/mcp";
const TS_NAME = /^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*\.ts\.net$/;

async function startAiTools() {
  const root = $("#ai-tools");
  root.removeAttribute("aria-busy");
  try { await drawAiTools(root, await api("/api/ai-tools")); }
  catch (e) { root.replaceChildren(notice("danger", "Could not open this page", e.message)); }
}

async function drawAiTools(root, d) {
  const status = el("div", { id: "ai-status" });
  const holder = el("div", { id: "ai-wizard", class: "stack-4" });
  const rest = el("div", { id: "ai-rest", class: "stack-4" });
  root.replaceChildren(status, holder, rest);
  const redraw = async () => {
    d = await api("/api/ai-tools");
    drawAiStatus(status, d);
    drawAiRest(rest, d, redraw);
  };
  drawAiStatus(status, d);
  drawAiRest(rest, d, redraw);
  holder.append(aiWizard(d, redraw, holder));
  SharedComponents.setupWizards(holder);
}

function drawAiStatus(box, d) {
  box.replaceChildren(d.enabled
    ? notice("success", "AI tools are on", "A tool with a key from this page can read what the key allows. Nothing can change.")
    : notice("info", "AI tools are off", "No AI tool can connect, whatever key it has. Nothing is turned on, and no key is made, until the last step of this wizard."));
}

// The wizard ----------------------------------------------------------------------------------------------------------

function aiOption(name, value, title, line, { checked = false, disabled = false, label = title, extra = null } = {}) {
  const input = el("input", { type: "radio", name, value, "data-label": label, checked, disabled });
  return el("label", { class: "option-card" }, input, el("strong", {}, title, extra), el("small", { text: line }));
}

function aiStep(id, title, question, nodes, { optional = false, required = false, error = "", help = [] } = {}) {
  return el("section", { class: "wizard__step", "data-step": id, "data-title": title, "data-optional": optional ? "" : null, "data-required": required ? "" : null, "data-error": error || null },
    el("h3", { class: "wizard__q", text: question }), ...nodes, help.length ? el("p", { class: "help-links" }, help) : null);
}

function aiHelp(question, title, ...paragraphs) {
  return helpButton(question, { title, body: paragraphs.map((p) => (typeof p === "string" ? el("p", { text: p }) : p)) });
}

function aiAddress(d, answers) {
  const base = { here: `http://localhost:${d.port}`, home: d.addresses[0] ? `http://${d.addresses[0]}:${d.port}` : "" }[answers.where];
  return answers.where === "tailscale" ? `https://${answers.tailscale}${AI_PATH}` : `${base || ""}${AI_PATH}`;
}

function aiWizard(d, redraw, holder) {
  const clientsById = Object.fromEntries(d.clients.map((c) => [c.id, c]));
  const cards = d.clients.filter((c) => c.id !== "openai-compatible");
  const home = d.addresses[0];
  const nameInput = el("input", { class: "input", id: "ai-name", autocomplete: "off", maxlength: "60", "data-recommended": clientsById[cards[0].id].name_suggestion, value: cards[0].name_suggestion });
  let nameEdited = false;
  nameInput.addEventListener("input", () => { nameEdited = true; });
  const tsInput = el("input", { class: "input", id: "ai-ts", autocomplete: "off", spellcheck: "false", inputmode: "url" });
  const tsField = field("Your server's Tailscale name", tsInput, { hint: "Run tailscale serve status on the server. The name ends in .ts.net." });
  tsField.hidden = true;
  const password = el("input", { class: "input", id: "ai-password", type: "password", autocomplete: "current-password" });

  // 1. Which tool
  const openai = clientsById["openai-compatible"];
  const s1 = aiStep("tool", "AI tool", "Which AI tool will you connect?", [
    el("fieldset", { class: "option-cards" }, el("legend", { class: "visually-hidden", text: "AI tool" }),
      ...cards.map((c) => aiOption("tool", c.id, c.name, c.line))),
    notice("info", "Does your tool say it is OpenAI compatible?", openai.steps[0] + " " + openai.steps[1]),
  ], { required: true, error: "Choose the AI tool you will connect",
    help: [aiHelp("What is MCP?", "What is MCP?", "MCP is the Model Context Protocol. It is a standard way for an AI tool to ask a program for facts. Starboard speaks it, so a tool that speaks it can ask which apps have a problem, what is downloading and how full the disks are.",
      "The tool asks. Starboard answers from what it already knows, hides private details and marks the answer as data. The tool cannot change anything.")] });

  // 2. Where it runs
  const s2 = aiStep("where", "Where it runs", "Where does the AI tool run?", [
    el("fieldset", { class: "option-cards" }, el("legend", { class: "visually-hidden", text: "Where the AI tool runs" }),
      aiOption("where", "here", "On this server", "The tool and Starboard are on the same computer. Nothing leaves it."),
      aiOption("where", "home", "On another computer in my home", home ? "It reaches Starboard across your home network." : "Turn on access from your home network in Settings, Security first.",
        { disabled: !home || !d.network_access }),
      aiOption("where", "tailscale", "Away from home, over Tailscale", "Private to your own devices. Needs Tailscale on this server and on that computer.")),
    tsField,
    notice("warning", "Starboard is never put on the public internet for this", "Do not open a port on your router and do not use Tailscale Funnel. Both let anyone on the internet try to reach Starboard. Tailscale Serve shares it only with your own devices."),
  ], { required: true, error: "Choose where the AI tool runs",
    help: [aiHelp("What is Tailscale?", "What is Tailscale?", "Tailscale joins your own devices into one private network, wherever they are. Tailscale Serve then shares a program on one device with the others, over HTTPS, and with no one else.",
      "Tailscale Funnel does the opposite: it shares a program with the whole internet. Never use Funnel for Starboard.")] });
  s2.querySelectorAll("input[name=where]").forEach((r) => r.addEventListener("change", () => {
    tsField.hidden = s2.querySelector("input[name=where]:checked")?.value !== "tailscale";
    if (tsField.hidden) { tsInput.value = ""; setError(tsInput, ""); }
  }));

  // 3. What it may read
  const boxes = d.scopes.map((s) => {
    const input = el("input", { type: "checkbox", value: s.id, id: `ai-scope-${s.id}`, "data-label": s.title, checked: s.default });
    return el("label", { class: "check", for: input.id }, input, el("span", { class: "check__text" }, el("strong", { text: s.title }), el("span", { class: "check__hint", text: s.what })));
  });
  const s3 = aiStep("reads", "What it may read", "What may the AI tool read?", [
    el("fieldset", { class: "form-stack" }, el("legend", { class: "visually-hidden", text: "What the AI tool may read" }), ...boxes),
    notice("info", "Whatever you choose, the key never lets the tool:", "", { after: el("ul", { class: "plain-list" }, d.cannot.map((t) => el("li", { text: t }))) }),
  ], { required: true, error: "Choose at least one thing the AI tool may read",
    help: [aiHelp("Why are some of these off?", "Why are some of these off?", "Give an AI tool only what it needs. Library titles are text that anyone can write, so a title could hold instructions meant to trick a tool. Logs can hold a lot of detail. Updates tell a tool what is out of date.",
      "You can make another key later with more, and revoke this one.")] });

  // 4. When the key ends
  const s4 = aiStep("ends", "When the key ends", "When should the key stop working?", [
    el("fieldset", { class: "option-cards" }, el("legend", { class: "visually-hidden", text: "When the key ends" }),
      ...d.ends.map((e) => aiOption("ends", e.id, e.title.replace(" (recommended)", ""), { 30: "Good for trying a tool.", 90: "A new key every three months. Starboard shows when one is about to end.", 365: "Make a new key once a year.", never: "The key works until you revoke it." }[e.id],
        { checked: e.id === "90", label: e.title.replace(" (recommended)", ""), extra: e.id === "90" ? el("span", { class: "wizard__tag", "data-tag": "recommended", text: "Recommended" }) : null }))),
  ], { optional: true });
  s4.querySelector("input[value='90']").dataset.recommended = "";

  // 5. Its name
  const s5 = aiStep("name", "Name", "What should the key be called?", [
    field("Name", nameInput, { hint: "It shows in the list of keys and in the audit log. Name it after the tool and the computer, such as Claude Desktop on the laptop." }),
  ], { optional: true });
  s1.querySelectorAll("input[name=tool]").forEach((r) => r.addEventListener("change", () => {
    if (!nameEdited) nameInput.value = clientsById[r.value].name_suggestion;
    nameInput.dataset.recommended = clientsById[r.value].name_suggestion;
  }));

  // 6. Check your answers
  const can = el("div", { class: "stack-2", id: "ai-can" });
  const pwField = field("Your Starboard password", password, { hint: "Starboard asks again, because this turns something on and makes a key." });
  const check = el("section", { class: "wizard__step wizard__check", "data-step": "check" }, el("h3", { class: "wizard__q", text: "Check your answers" }), can, pwField);

  const progress = el("div", { class: "meter wizard-progress" }, el("div", { class: "meter__label" }, el("span", { class: "wizard__count" }), el("span", { class: "numeric" })),
    el("div", { class: "progress", role: "progressbar", "aria-label": "Progress" }, el("span")));
  const stepList = el("ol", { class: "steps", "aria-label": "Steps" }, ["AI tool", "Where it runs", "What it may read", "When the key ends", "Name", "Check your answers"].map((t) => el("li", {}, t, el("span", { class: "visually-hidden" }))));
  const foot = el("div", { class: "wizard__foot" },
    el("button", { class: "btn btn--primary", type: "button", "data-wizard-act": "next", text: "Continue" }),
    el("button", { class: "btn", type: "button", "data-wizard-act": "back", hidden: true, text: "Back" }),
    el("button", { class: "btn btn--quiet", type: "button", "data-wizard-act": "skip", text: "Skip this step" }),
    el("button", { class: "btn btn--primary", type: "button", "data-wizard-act": "finish", hidden: true, text: d.enabled ? "Make the key" : "Turn on AI tools and make the key" }));
  const box = el("div", { class: "wizard", "data-wizard": "connect-ai-tool", "data-mode": "new", "data-finish": d.enabled ? "Make the key" : "Turn on AI tools and make the key", "data-review": "Check your answers" },
    progress, stepList, s1, s2, s3, s4, s5, check, foot);
  const wrap = el("section", { class: "panel stack-3", "aria-labelledby": "ai-wiz-h" }, el("h2", { id: "ai-wiz-h", text: "Connect an AI tool" }),
    el("p", { class: "muted", text: "Five questions, then you check them. Starboard changes nothing until the last button." }), box);

  const answers = () => {
    const pick = (n) => box.querySelector(`input[name=${n}]:checked`)?.value || "";
    const tool = pick("tool");
    return { tool, where: pick("where"), tailscale: tsInput.value.trim().toLowerCase().replace(/^https?:\/\//, "").replace(/[/.]+$/, "").split("/")[0],
      scopes: boxes.map((b) => b.querySelector("input")).filter((i) => i.checked).map((i) => i.value),
      ends: pick("ends") || "90", name: nameInput.value.trim() || (clientsById[tool]?.name_suggestion || "AI tool") };
  };
  const tsProblem = (a) => (a.where !== "tailscale" ? "" : !a.tailscale ? "Enter your server's Tailscale name" : !TS_NAME.test(a.tailscale) ? "Enter the whole name, such as <your-server>.<your-tailnet>.ts.net" : "");
  const sayCan = () => {
    const a = answers();
    can.replaceChildren(el("h4", { text: "What this key will be able to do" }),
      el("ul", { class: "plain-list" }, d.scopes.filter((s) => a.scopes.includes(s.id)).map((s) => el("li", { text: s.what }))),
      el("h4", { text: "What it will never be able to do" }), el("ul", { class: "plain-list" }, d.cannot.map((t) => el("li", { text: t }))),
      el("p", { class: "small muted", text: `Address it will use: ${aiAddress(d, a)}` }));
  };
  // A name typed for Tailscale is checked when the answers are shown. A wrong one sends the person back to that question,
  // with the shared wizard's own error summary (WIZARD.md section 11), as a missing answer does.
  box.addEventListener("wizard-step", (e) => {
    if (e.detail.step !== "check") return;
    sayCan();
    setTimeout(() => {
      const wrong = tsProblem(answers());
      if (!wrong) return;
      box.querySelector(".wizard-summary--check a[href$='-where']")?.click();
      setTimeout(() => SharedComponents.showErrors(s2, [{ field: "ai-ts", message: wrong }]), 0);
    }, 0);
  });
  box.addEventListener("wizard-finish", async () => {
    const a = answers();
    SharedComponents.clearErrors(check);
    if (!password.value) { SharedComponents.showErrors(check, [{ field: "ai-password", message: "Enter your Starboard password" }]); return; }
    const go = box.querySelector("[data-wizard-act=finish]");
    go.disabled = true;
    try {
      const r = await api("/api/ai-tools/connect", { method: "POST", body: { name: a.name, scopes: a.scopes, expires_days: a.ends, client: a.tool, password: password.value } });
      password.value = "";
      aiResult(holder, d, r, a, redraw, clientsById[a.tool]);
      redraw();
    } catch (err) {
      SharedComponents.showErrors(check, [{ field: err.status === 401 || err.status === 429 ? "ai-password" : "ai-password", message: err.message }]);
    } finally { go.disabled = false; }
  });
  return wrap;
}

// The result: the address and the key once, what the key can do, and the set-up -----------------------------------------

function aiFill(text, address, key) {
  return text.replaceAll("{{address}}", address).replaceAll("{{key}}", key);
}

function aiCommand(label, snippet, address, key) {
  const shown = aiFill(snippet.text, address, `${key.slice(0, 15)}••••••••`);  // the key is in the secret field above, not written out here
  const full = aiFill(snippet.text, address, key);
  const copy = el("button", { type: "button", class: "btn copy-btn--label" }, icon("copy"), "Copy", el("span", { class: "visually-hidden", text: ` ${label}, with the key in it` }));
  copy.addEventListener("click", async () => { const ok = await copyText(full); (ok ? toast : problem)(ok ? `Copied ${label}` : "Could not copy. Select the text and copy it yourself"); });
  const id = `ai-snip-${label.replace(/\W+/g, "-").toLowerCase()}`;
  return el("div", { class: "stack-1" }, el("p", { class: "small", id, text: snippet.label }),
    el("div", { class: "command" }, el("pre", { class: "code-block", tabindex: "0", "aria-labelledby": id, text: shown }), copy));
}

function aiResult(holder, d, r, a, redraw, client) {
  const address = aiAddress(d, a);
  const head = el("h2", { id: "ai-done-h", tabindex: "-1", text: "Your AI tool is ready to connect" });
  const value = el("input", { class: "input secret-field__input", id: "ai-key-made", type: "password", readonly: true, autocomplete: "off", spellcheck: "false" });
  value.value = r.key;
  const copyKey = el("button", { type: "button", class: "btn btn--primary", "data-secret-copy": "" }, icon("copy"), "Copy", el("span", { class: "visually-hidden", text: " the key" }));
  const secret = el("div", { class: "secret-field", "data-secret": "", "data-name": "API key" }, value,
    el("button", { type: "button", class: "btn", "data-secret-show": "", "aria-controls": "ai-key-made" }, icon("eye"), "Show"), copyKey);
  const ends = r.item.expires_at ? new Date(r.item.expires_at).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" }) : "Never";
  const addr = el("div", { class: "address" }, el("code", { text: address }), copyButton(address, "the address"));
  const test = el("button", { type: "button", class: "btn", text: "Check that it answers" });
  const said = el("p", { class: "small", role: "status", "aria-live": "polite" });
  test.addEventListener("click", async () => {
    test.disabled = true;
    said.textContent = "Asking Starboard…";
    try {
      const reply = await fetch(AI_PATH, { method: "POST", headers: { Authorization: `Bearer ${r.key}`, "Content-Type": "application/json" }, body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "tools/list" }) });
      const body = await reply.json();
      said.textContent = reply.ok && body.result ? `Starboard answered. This key can use ${body.result.tools.length} tools: ${body.result.tools.map((t) => t.title).join(", ")}. This checks the key from this page, not the path from your other computer.`
        : `Starboard did not accept the key: ${body.detail || body.title || reply.status}`;
    } catch { said.textContent = "Starboard did not answer. Reload the page and check the key again."; }
    test.disabled = false;
  });
  const setup = client && client.id !== "openai-compatible" ? [
    el("h3", { text: `Set up ${client.name}` }), el("p", { class: "muted", text: `You need: ${client.needs}` }),
    el("ol", { class: "steps-list" }, client.steps.map((t) => el("li", { text: t }))),
    ...client.snippets.map((s) => aiCommand(client.name, s, address, r.key)),
    client.note_http && address.startsWith("http:") ? notice("info", "A plain http address", client.note_http) : null] : [];
  const away = [el("h3", { text: a.where === "tailscale" ? "Reach Starboard over Tailscale Serve" : "Using it away from home" }),
    el("p", { class: "muted", text: d.tailscale.title }), el("ol", { class: "steps-list" }, d.tailscale.steps.map((t) => el("li", { text: t })))];
  const again = el("button", { type: "button", class: "btn", text: "Connect another AI tool" });
  again.addEventListener("click", () => { holder.replaceChildren(aiWizard(d, redraw, holder)); SharedComponents.setupWizards(holder); });
  holder.replaceChildren(el("section", { class: "panel stack-3", "aria-labelledby": "ai-done-h" }, head,
    notice("success", r.turned_on_now ? "AI tools are on, and the key is made" : "The key is made", "Starboard shows the key only now. Copy it before you leave this page: it cannot be shown again."),
    el("dl", { class: "facts facts--addresses" }, el("dt", { text: "Address" }), el("dd", {}, addr), el("dt", { text: "Key" }), el("dd", {}, secret),
      el("dt", { text: "Name" }), el("dd", { text: r.item.name }), el("dt", { text: "Ends" }), el("dd", { text: ends }),
      el("dt", { text: "May" }), el("dd", { text: "Read only" })),
    el("h3", { text: "What this key can do" }), el("ul", { class: "plain-list" }, d.scopes.filter((s) => a.scopes.includes(s.id)).map((s) => el("li", { text: s.what }))),
    el("h3", { text: "What it can never do" }), el("ul", { class: "plain-list" }, d.cannot.map((t) => el("li", { text: t }))),
    ...setup, ...away,
    el("div", { class: "actions" }, test, again), said));
  SharedComponents.setupSecrets(holder);
  head.focus();
}

// Under the wizard: keys, activity and the off switch ---------------------------------------------------------------------

function drawAiRest(box, d, redraw) {
  const when = (t) => new Date(t).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
  const list = el("ul", { class: "rows" }, d.keys.length ? d.keys.map((k) => {
    const revoke = el("button", { type: "button", class: "btn btn--danger btn--compact" }, icon("trash-2"), "Revoke", el("span", { class: "visually-hidden", text: ` ${k.name}` }));
    revoke.addEventListener("click", async () => {
      if (!await confirmDialog({ title: `Revoke ${k.name}?`, message: "The AI tool using this key stops working at once. You can make another key.", confirm: "Revoke", danger: true })) return;
      try { await api(`/api/keys/${k.id}`, { method: "DELETE" }); await redraw(); showSaved("ai-keys-saved", `${k.name} revoked`); }
      catch (e) { problem(e.message, revoke); }
    });
    const kind = (d.clients.find((c) => c.id === k.client) || {}).name || "AI tool";
    const meta = [kind, "Read only", k.last_used_at ? `last used ${new Date(k.last_used_at).toLocaleString("en-GB")}` : "not used yet", k.expires_at ? `ends ${when(k.expires_at)}` : "never ends"].join(" · ");
    return el("li", { class: "row row--no-lead" }, el("div", {}, el("div", { class: "row__title", text: k.name }), el("div", { class: "row__meta", text: meta }),
      el("div", { class: "row__meta", text: `May read: ${k.can.join(", ") || "everything except logs and updates"}` })),
      el("div", { class: "row__side" }, k.expires_at && new Date(k.expires_at) - Date.now() < 14 * 864e5 ? chip("Ends soon", "warning") : k.last_used_at ? chip("In use", "success") : chip("Not used yet", "muted"), revoke));
  }) : [el("li", {}, emptyState("No keys made here yet", "The wizard on this page makes one for each AI tool."))]);
  const off = el("button", { type: "button", class: "btn btn--danger" }, "Turn off AI tools");
  off.addEventListener("click", async () => {
    if (!await confirmDialog({ title: "Turn off AI tools?", message: "Every AI tool stops at once, whatever key it has. The keys stay until you revoke them.", confirm: "Turn off AI tools", danger: true })) return;
    try { await saveGeneral({ mcp_enabled: false }, true); await redraw(); } catch (e) { problem(e.message, off); }
  });
  const activity = d.activity.length ? el("ul", { class: "rows" }, d.activity.map((a) => el("li", { class: "row row--no-lead" },
    el("div", {}, el("div", { class: "row__title", text: a.what }), el("div", { class: "row__meta", text: `${a.who} · ${a.time ? new Date(a.time).toLocaleString("en-GB") : ""}` }))))) : emptyState("Nothing yet", "What AI tools do, and when keys are made or revoked, shows here. Starboard never writes what was asked or answered.");
  box.replaceChildren(
    section("ai-keys", "Keys for AI tools", "One key for each tool. A key never shows again after the wizard, and Starboard keeps only a scrambled copy of it.", list, el("div", { class: "actions" }, savedNote("ai-keys-saved")),
      el("p", { class: "small muted" }, "Keys you made yourself are on ", el("a", { href: "/settings-security-keys.html", text: "API keys" }), ".")),
    section("ai-activity", "What AI tools did lately", "The newest 30 lines of the audit log about AI tools.", activity),
    d.enabled ? section("ai-off", "Turn off AI tools", "Every AI tool stops at once. Keys stay until you revoke them.", el("div", { class: "actions" }, off)) : null);
}
