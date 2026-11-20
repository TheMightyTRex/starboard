// Settings, Security: who can open the dashboard, the password, API keys and signing out everywhere.

// Security ------------------------------------------------------------------

async function startSecurity() {
  // Who can open the dashboard
  const access = el("input", { type: "checkbox", role: "switch", "aria-labelledby": "net-l", "aria-describedby": "net-result" });
  const result = el("span", { id: "net-result" });
  const addresses = el("dl", { class: "facts facts--addresses", "aria-label": "Addresses that open Starboard" });
  const forced = el("p", { class: "small muted", hidden: true });
  let network;
  const showNetwork = () => {
    access.checked = network.network_access;
    result.textContent = network.network_access
      ? "Active: phones and other computers on your home network can reach the sign-in page."
      : "Inactive: only the computer Starboard runs on can open it.";
    const rows = [["This computer", `http://localhost:${network.port}`]];
    if (network.network_access) for (const a of network.addresses) rows.push(["Phones and other computers", `http://${a}:${network.port}`]);
    addresses.replaceChildren(...rows.flatMap(([label, u]) => [el("dt", { text: label }), el("dd", {}, el("code", { text: u }), copyButton(u, `the address for ${label.toLowerCase()}`))]));
    if (network.forced_by) {
      access.disabled = true;
      forced.hidden = false;
      forced.textContent = `Set by ${network.forced_by} on the server, so it cannot be changed here.`;
    }
  };
  try { if (!wants("#security-sections", "sc-who")) throw new Error("not on this page"); network = await api("/api/network"); }
  catch { network = { network_access: config.network_access, addresses: [], port: location.port || 80, you_are_on_this_computer: false }; }
  access.addEventListener("change", async () => {
    const want = access.checked;
    if (!want) {
      access.checked = true;
      const ok = await confirmDialog({
        title: "Deactivate access from your home network?",
        message: network.you_are_on_this_computer
          ? el("p", { text: "Phones and other computers lose access straight away. Only this computer, the server, can open Starboard after this." })
          : notice("warning", "You are using another device", "This phone or computer loses access straight away. Only the server itself can open Starboard after this."),
        confirm: "Deactivate network access", danger: true,
      });
      if (!ok) { access.focus(); return; }
      access.checked = false;
    }
    try {
      await saveGeneral({ network_access: want }, true);
      network.network_access = want;
      showNetwork();
      setTimeout(async () => { try { network = await api("/api/network"); showNetwork(); } catch { /* this device lost access */ } }, 1500);
    } catch (e) { access.checked = !want; problem(e.message); }
  });

  // Password
  const current = el("input", { class: "input", type: "password", autocomplete: "current-password", required: true });
  const fresh = el("input", { class: "input", type: "password", autocomplete: "new-password", required: true });
  const again = el("input", { class: "input", type: "password", autocomplete: "new-password", required: true });
  const pwForm = el("form", { novalidate: true },
    el("div", { class: "form-stack" },
      field("Current password", current, { required: true }),
      field("New password", fresh, { required: true }),
      field("Enter the new password again", again, { required: true })),
    el("div", { class: "actions" }, el("button", { type: "submit", class: "btn btn--primary", text: "Change password" }), savedNote("password-saved")));
  pwForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    [current, fresh, again].forEach((c) => setError(c, ""));
    if (!current.value) { setError(current, "Enter your current password"); current.focus(); return; }
    if (fresh.value.length < 10) { setError(fresh, `Use at least 10 characters. This one has ${fresh.value.length}.`); fresh.focus(); return; }
    if (fresh.value !== again.value) { setError(again, "The two new passwords are different. Enter the new one again."); again.focus(); return; }
    try {
      await api("/api/password", { method: "POST", body: { current: current.value, new: fresh.value } });
      pwForm.reset();
      showSaved("password-saved", "Password changed. Everyone else is signed out");
    } catch (err) {
      if (err.status === 401 || err.status === 429) { setError(current, err.message); current.focus(); }
      else { setError(fresh, err.message); fresh.focus(); }
    }
  });

  // Sessions
  const days = el("input", { class: "input", inputmode: "numeric", "aria-labelledby": "days-l", "aria-describedby": "days-h", value: String(config.session_days) });
  const daysError = el("span", { class: "field-error", id: "days-e", hidden: true });
  const secure = el("input", { type: "checkbox", role: "switch", "aria-labelledby": "secure-l", "aria-describedby": "secure-h", checked: config.secure_cookies });
  secure.addEventListener("change", async () => {
    try { await saveGeneral({ secure_cookies: secure.checked }, true); }
    catch (err) { secure.checked = !secure.checked; problem(err.message); }
  });
  const daysForm = el("form", { novalidate: true, id: "session-form" });
  daysForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    daysError.hidden = true;
    days.removeAttribute("aria-invalid");
    days.setAttribute("aria-describedby", "days-h");
    const fail = (m) => {
      daysError.replaceChildren(icon("circle-alert"), el("span", { text: m }));
      daysError.hidden = false;
      days.setAttribute("aria-invalid", "true");
      days.setAttribute("aria-describedby", "days-h days-e");
      days.focus();
    };
    const n = Number(days.value);
    if (!Number.isInteger(n) || n < 1 || n > 90) { fail("Enter a whole number of days from 1 to 90"); return; }
    try { await saveGeneral({ session_days: n }, true); }
    catch (err) { fail(err.message); }
  });
  const everywhere = el("button", { type: "button", class: "btn btn--danger", text: "Sign out everywhere" });
  // The password again (DASH-280), so a session someone else has cannot sign everyone out.
  everywhere.addEventListener("click", async () => {
    const pw = el("input", { class: "input", type: "password", id: "end-all-password", autocomplete: "current-password", required: true });
    const ok = await confirmDialog({
      title: "Sign out everywhere?",
      message: "Every browser and phone signed in to Starboard is signed out, including this one. Everyone needs the password to sign in again.",
      confirm: "Sign out everywhere", danger: true,
      fields: [el("div", { class: "field" }, el("label", { for: pw.id, text: "Your Starboard password" }), pw)],
    });
    if (!ok) return;
    try { await api("/api/sessions/end-all", { method: "POST", body: { password: pw.value } }); }
    catch (e) { problem(e.message, everywhere); return; }
    location.href = "/login.html";
  });
  const signOut = el("button", { type: "button", class: "btn" }, icon("log-out"), "Sign out");
  signOut.addEventListener("click", async () => {
    await api("/api/logout", { method: "POST" }).catch(() => {});
    location.href = "/login.html";
  });

  const holder = $("#security-sections");
  holder.removeAttribute("aria-busy");
  holder.replaceChildren(...onlyParts(holder, [
    section("sc-who", "Who can open the dashboard", "When this is off, only the computer Starboard runs on can open it.",
      el("ul", { class: "settings-rows" },
        settingRow("Phones and other computers on your home network", result, el("label", { class: "switch" }, access), "net-l")),
      addresses, forced),
    section("sc-pw", "Password", "At least 10 characters; a short sentence of 4 or more words makes a strong password that you can remember. You stay signed in here and everyone else is signed out.", pwForm),
    section("sc-ses", "Sessions", "How long Remember me lasts, and signing out.", daysForm),
    wants(holder, "sc-keys") ? section("sc-keys", "API keys", "For other apps, scripts and AI assistants. Each key reads, or reads and manages, only what you choose, and is shown once.", apiKeys()) : null,
    wants(holder, "sc-mcp") ? section("sc-mcp", "AI assistants", "Let an AI assistant that speaks MCP, the Model Context Protocol, answer questions about your server. Nothing is shared until you activate it.", mcpAssistants()) : null]));
  daysForm.append(
      el("ul", { class: "settings-rows" },
        el("li", { class: "setting" },
          el("div", { class: "setting__text" }, el("span", { class: "setting__label", id: "days-l", text: "Remember me keeps people signed in for" }),
            el("span", { class: "setting__hint", id: "days-h", text: "1 to 90 days. Without Remember me, people are signed out when they close the browser, or after a day." })),
          el("div", { class: "setting__control" }, el("div", { class: "field" },
            el("div", { class: "inline-save" },
              el("div", { class: "input-group days-group" }, days, el("span", { class: "input-group__unit", text: "days" })),
              el("button", { type: "submit", class: "btn" }, "Save", el("span", { class: "visually-hidden", text: " how long" }))),
            daysError))),
        settingRow("Only send the sign-in cookie over HTTPS", el("span", { id: "secure-h", text: "Activate when every address you use starts with https. This applies at once." }), el("label", { class: "switch" }, secure), "secure-l"),
        settingRow("Sign out", "This browser only.", el("div", { class: "actions session-actions" }, signOut), "signout-l")));
  if (wants(holder, "sc-ses")) holder.append(dangerSection("sc-danger", "Sign out everywhere", "Every browser and phone signed in to Starboard, this one too. It asks for your password first.",
    el("div", { class: "actions" }, everywhere)));
  showNetwork();
}

// API keys (DASH-274): read-only keys for /api/v1, made with the password and shown once. Settings pattern 8: each
// key a row with its state and Edit, which opens it in a slide-out with Revoke; Make a key at the foot.
// What each API key right and scope means, in the words the key form and its panel use (DASH-274).
const KEY_RIGHTS = { read: "Read only", manage: "Read and manage" };

const KEY_SCOPES = {
  apps: ["Apps", "Apps, their status, uptime, versions and updates"],
  downloads: ["Downloads", "The queue, speeds, download hours and history"],
  media: ["Media", "Coming up, recently added, what is playing and the Jellyfin jobs"],
  library: ["Library", "The Library and its search"],
  requests: ["Requests", "Requests from Seerr or Reelix"],
  system: ["System", "Processor, memory, disks, version and test alerts"],
  logs: ["Logs", "Starboard's log, with addresses, names and keys taken out, and its limits; with Read and manage, also change the limits and delete all logs. Only when ticked"],
  updates: ["Updates", "What can be updated; with Read and manage, also update Starboard, Reelix, an app or a plug-in, and roll a plug-in back. Only when ticked"],
};

function apiKeys() {
  const box = el("div", { class: "stack-4" });
  const list = el("ul", { class: "rows" });
  const when = (d) => new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
  const stateOf = (k) => {
    if (k.expires_at && new Date(k.expires_at) - Date.now() < 14 * 864e5) return chip("Ends soon", "warning");
    return k.last_used_at ? chip("In use", "success") : chip("Not used yet", "muted");
  };
  const openKey = (k, opener) => {
    const revoke = el("button", { type: "button", class: "btn btn--danger" }, icon("trash-2"), "Revoke");
    const panel = sidePanel({ title: k.name, opener, body: [el("dl", { class: "facts" },
      el("dt", { text: "Starts with" }), el("dd", { text: `${k.prefix}…` }),
      el("dt", { text: "May" }), el("dd", { text: KEY_RIGHTS[k.right] || k.right }),
      el("dt", { text: "Reads" }), el("dd", { text: k.scopes.length ? k.scopes.map((s) => (KEY_SCOPES[s] || [s])[0]).join(", ") : "Everything the API offers, except Logs and Updates" }),
      el("dt", { text: "Ends" }), el("dd", { text: k.expires_at ? when(k.expires_at) : "Never" }),
      el("dt", { text: "Last used" }), el("dd", { text: k.last_used_at ? new Date(k.last_used_at).toLocaleString("en-GB") : "Not used yet" }))],
      foot: [revoke] });
    revoke.addEventListener("click", async () => {
      if (!await confirmDialog({ title: `Revoke ${k.name}?`, message: "Anything using this key stops working at once.", confirm: "Revoke", danger: true })) return;
      try { draw((await api(`/api/keys/${k.id}`, { method: "DELETE" })).keys); panel.close(); showSaved("keys-saved", `${k.name} revoked`); }
      catch (e) { problem(e.message, revoke); }
    });
  };
  const draw = (keys) => list.replaceChildren(...(keys.length ? keys.map((k) => {
    const edit = el("button", { type: "button", class: "btn btn--quiet btn--compact" }, icon("pencil"), "Edit", el("span", { class: "visually-hidden", text: ` ${k.name}` }));
    edit.addEventListener("click", () => openKey(k, edit));
    const meta = [`${k.prefix}…`, (KEY_RIGHTS[k.right] || k.right).toLowerCase(), k.expires_at ? `ends ${when(k.expires_at)}` : "never ends"].join(" · ");
    return el("li", { class: "row row--no-lead" }, el("div", {}, el("div", { class: "row__title", text: k.name }), el("div", { class: "row__meta", text: meta })),
      el("div", { class: "row__side" }, stateOf(k), edit));
  }) : [el("li", {}, emptyState("No keys yet", "Make one for each app or script that reads Starboard."))]));
  const make = (opener) => {
    const name = el("input", { class: "input", id: "key-name", autocomplete: "off", placeholder: "Home Assistant" });
    const ends = el("select", { class: "select", id: "key-ends" }, [["90", "In 90 days"], ["365", "In a year"], ["never", "Never"]].map(([v, t]) => el("option", { value: v, text: t })));
    const right = el("select", { class: "select", id: "key-right" }, Object.entries(KEY_RIGHTS).map(([v, t]) => el("option", { value: v, text: t })));
    const boxes = Object.entries(KEY_SCOPES).map(([key, [title, hint]]) => {
      const input = el("input", { type: "checkbox", value: key, id: `key-scope-${key}` });
      return { input, node: el("label", { class: "check", for: input.id }, input,
        el("span", { class: "check__text" }, el("strong", { text: title }), el("span", { class: "check__hint", text: hint }))) };
    });
    const scopes = el("fieldset", { class: "form-stack", id: "key-scopes", "aria-describedby": "key-scopes-hint" },
      el("legend", { class: "field__label", text: "What it may read" }),
      el("span", { class: "hint", id: "key-scopes-hint", text: "Leave them all empty for everything the API offers, except Logs and Updates, which are only given when ticked. Give an AI assistant only what it needs." }),
      boxes.map((b) => b.node));
    const pw = el("input", { class: "input", id: "key-password", type: "password", autocomplete: "current-password" });
    const go = el("button", { type: "submit", class: "btn btn--primary", form: "key-form", text: "Make a key" });
    const cancel = el("button", { type: "button", class: "btn", text: "Cancel" });
    const form = el("form", { class: "form-stack", id: "key-form", novalidate: true }, field("Name it after what will use it", name),
      field("What it may do", right, { hint: "Read and manage also lets it approve requests, pause downloads and refresh the Library. It never changes settings." }),
      scopes, field("Ends", ends), field("Your Starboard password", pw));
    const panel = sidePanel({ title: "Make a key", opener, body: [form], foot: [go, cancel] });
    setTimeout(() => name.focus(), 0);  // a form in a slide-out starts in its first field
    cancel.addEventListener("click", () => panel.close());
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const r = await api("/api/keys", { method: "POST", body: { name: name.value, right: right.value, scopes: boxes.filter((b) => b.input.checked).map((b) => b.input.value), expires_days: ends.value, password: pw.value } });
        const value = el("input", { class: "input", id: "key-made", readonly: true, value: r.key, spellcheck: "false" });
        const copy = el("button", { type: "button", class: "btn btn--primary" }, icon("copy"), "Copy");
        copy.addEventListener("click", async () => { try { await navigator.clipboard.writeText(r.key); toast("Key copied"); } catch { value.select(); } });
        const done = el("button", { type: "button", class: "btn", text: "Done" });
        done.addEventListener("click", () => panel.close());
        panel.setTitle(`${r.item.name}'s key`);
        panel.body.replaceChildren(notice("success", "Copy the key now", "Starboard shows it only this once; send it as Authorization: Bearer, never in an address."),
          field("The key", value));
        panel.setFoot([copy, done]);
        value.focus(); value.select();
        draw((await api("/api/keys")).keys);
      } catch (err) { problem(err.message, go); }
    });
  };
  const add = el("button", { type: "button", class: "btn" }, icon("plus"), "Make a key");
  add.addEventListener("click", () => make(add));
  api("/api/keys").then((r) => draw(r.keys)).catch((e) => list.replaceChildren(el("li", {}, notice("danger", "Could not list the keys", e.message))));
  // The developers' pages in the help centre (DASH-275): how to start, and every route.
  const helpBase = ($("[data-help-link]")?.getAttribute("href") || "https://themightytrex.github.io/starboard/help/").replace(/(\/help\/).*$/, "$1");
  const helpLink = (page, text) => el("a", { href: `${helpBase}developers/${page}.html`, target: "_blank", rel: "noopener noreferrer" },
    text, el("span", { class: "visually-hidden", text: " (opens in a new tab)" }));
  box.append(list, el("div", { class: "actions" }, add, savedNote("keys-saved")),
    el("p", { class: "small muted" }, "What the API offers: ", helpLink("api-quickstart", "the API quickstart"), ", ",
      helpLink("api-reference", "every route"), " and ", el("a", { href: "/api/v1/openapi.json", text: "the API description (OpenAPI)" }), "."));
  return box;
}

// AI assistants over MCP (DASH-464): off until activated here. What it shares is said beside the switch; each
// assistant still needs a Read only key, and reads only what that key's scopes cover. Nothing polls.
function mcpAssistants() {
  const address = `${location.origin}/api/v1/mcp`;
  const on = el("input", { type: "checkbox", role: "switch", id: "mcp-on", "aria-labelledby": "mcp-l", "aria-describedby": "mcp-h mcp-result", checked: !!config.mcp_enabled });
  const result = el("p", { class: "small", id: "mcp-result", role: "status" });
  const where = el("dl", { class: "facts facts--addresses", "aria-label": "Address for AI assistants" },
    el("dt", { text: "Address for the assistant" }), el("dd", {}, el("code", { text: address }), copyButton(address, "the address for AI assistants")));
  const show = () => {
    result.textContent = config.mcp_enabled
      ? "Active: an assistant with a Read only key from this page can ask about your server."
      : "Inactive: no assistant can connect, whatever key it has.";
    where.hidden = !config.mcp_enabled;
  };
  on.addEventListener("change", async () => {
    try { await saveGeneral({ mcp_enabled: on.checked }, true); }
    catch (e) { on.checked = !on.checked; problem(e.message, on); }
    show();
  });
  const helpBase = ($("[data-help-link]")?.getAttribute("href") || "https://themightytrex.github.io/starboard/help/").replace(/(\/help\/).*$/, "$1");
  const helpLink = (page, text) => el("a", { href: `${helpBase}${page}.html`, target: "_blank", rel: "noopener noreferrer" },
    text, el("span", { class: "visually-hidden", text: " (opens in a new tab)" }));
  show();
  return el("div", { class: "stack-4" },
    el("ul", { class: "settings-rows" },
      settingRow("Let AI assistants connect",
        el("span", { id: "mcp-h", text: "An assistant can then read the Library, what is new, coming up and playing, downloads and their problems, requests, how each app is and disk space. It cannot change anything, never gets a password or an app's key, and each question it asks is written to the audit log. Give it a Read only key with only the scopes it needs." }),
        el("label", { class: "switch" }, on), "mcp-l")),
    result, where,
    el("p", { class: "small muted" }, "How to connect one: ", helpLink("topics/connect-an-ai-assistant-with-mcp", "Let an AI assistant answer questions"),
      ". What each tool gives back: ", helpLink("developers/mcp-tools", "MCP tools"), "."));
}
