// Settings, Manage apps, Copy app settings: choose the apps and the parts, check what would be copied (with a
// box for each password the old app keeps hidden), then Copy. Uses settings.js's field, notice and section.

const PART_HINTS = {
  tags: "Every tag, by name.",
  formats: "Custom formats the new app does not have, by name.",
  profiles: "Quality profiles the new app does not have, with their custom format scores.",
  folders: "Root folders. Each folder must exist inside the new app's container.",
  clients: "Download clients and remote path mappings. Passwords are asked for below.",
  naming: "Replaces the new app's naming with the old app's.",
  media: "Replaces the new app's media management (hard links, file permissions, recycling bin).",
};
const STATE_WORDS = { add: ["Will be added", "info"], there: ["Already there", "muted"], replace: ["Will be replaced", "warning"] };

async function startCopy() {
  const root = $("#copy-sections");
  let d;
  try { d = await api("/api/copy-settings"); } catch (e) { root.replaceChildren(notice("danger", "Could not load", e.message)); return; }
  root.removeAttribute("aria-busy");
  const ready = d.apps.filter((a) => a.has_api_key);
  const kinds = new Set(ready.map((a) => a.type));
  const pairs = [...kinds].filter((k) => ready.filter((a) => a.type === k).length >= 2);
  if (!pairs.length) {
    root.replaceChildren(notice("info", "Add the new app first",
      "Copying needs two apps of the same kind (two Sonarr, two Radarr or two Lidarr) in Manage apps, each with its API key.",
      el("a", { class: "btn", href: "/settings.html" }, "Manage apps")));
    return;
  }

  const option = (a) => el("option", { value: a.id, text: a.name });
  const from = el("select", { class: "select" }, ready.filter((a) => pairs.includes(a.type)).map(option));
  const to = el("select", { class: "select" });
  const fillTo = () => {
    const kind = ready.find((a) => a.id === from.value)?.type;
    to.replaceChildren(...ready.filter((a) => a.type === kind && a.id !== from.value).map(option));
  };
  from.addEventListener("change", () => { fillTo(); clearPreview(); });
  to.addEventListener("change", () => clearPreview());
  fillTo();

  const boxes = Object.entries(d.parts).map(([key, title]) => {
    const input = el("input", { type: "checkbox", value: key, checked: !["naming", "media"].includes(key) });
    input.addEventListener("change", () => clearPreview());
    return { key, input, node: el("label", { class: "check" }, input,
      el("span", { class: "check__text" }, el("strong", { text: title }), el("span", { class: "check__hint", text: PART_HINTS[key] }))) };
  });
  const parts = () => boxes.filter((b) => b.input.checked).map((b) => b.key);

  const previewBox = el("div", { class: "stack-4", "aria-live": "polite" });
  const resultBox = el("div", { role: "status" });
  let secretInputs = [];
  function clearPreview() { previewBox.replaceChildren(); resultBox.replaceChildren(); secretInputs = []; }

  const checkButton = el("button", { type: "submit", class: "btn" }, icon("list-checks"), "Check what will be copied");
  const form = el("form", { novalidate: true, class: "stack-4" },
    el("div", { class: "form-grid" }, field("Copy from", from), field("Copy to", to)),
    el("fieldset", { class: "form-stack" }, el("legend", { text: "What to copy" }), boxes.map((b) => b.node)),
    el("div", { class: "actions" }, checkButton));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearPreview();
    checkButton.disabled = true;
    try { showPreview(await api("/api/copy-settings/preview", { method: "POST", body: { from: from.value, to: to.value, parts: parts() } })); }
    catch (err) { previewBox.replaceChildren(notice("danger", "Cannot copy", err.message)); }
    finally { checkButton.disabled = false; }
  });

  function showPreview(p) {
    const tables = p.parts.map((part) => el("div", { class: "stack-2" }, el("h3", { text: part.title }),
      part.items.length ? el("div", { class: "table-wrap", "data-stack": true }, el("table", { class: "table" },
        el("caption", { class: "visually-hidden", text: part.title }),
        el("thead", {}, el("tr", {}, ["Name", "What happens"].map((t) => el("th", { scope: "col", text: t })))),
        el("tbody", {}, part.items.map((it) => {
          const [words, tone] = STATE_WORDS[it.state];
          return el("tr", {}, el("th", { scope: "row", "data-label": "Name", text: it.kind && it.kind.toLowerCase() !== it.name.toLowerCase() ? `${it.name} (${it.kind})` : it.name }),
            el("td", { "data-label": "What happens" }, chip(words, tone)));
        })))) : el("p", { class: "small muted", text: "Nothing to copy." })));
    const needs = p.parts.flatMap((part) => part.items.filter((it) => it.needs?.length));
    secretInputs = needs.flatMap((it) => it.needs.map((n) => {
      const input = el("input", { class: "input", type: "password", autocomplete: "off" });
      return { client: it.name, field: n.field, input, node: field(`${it.name}: ${n.label}`, input) };
    }));
    const secrets = secretInputs.length ? el("div", { class: "stack-2" }, el("h3", { text: "Passwords the old app keeps hidden" }),
      el("p", { class: "small muted", text: "Apps never send these back. Type each one, or leave it empty: that client is added inactive, and you add the password in the new app later." }),
      el("div", { class: "form-stack" }, secretInputs.map((s) => s.node))) : null;
    const adding = p.parts.some((part) => part.items.some((it) => it.state !== "there"));
    const copyButton = el("button", { type: "button", class: "btn btn--primary", disabled: !adding }, icon("copy"), "Copy");
    copyButton.addEventListener("click", async () => {
      copyButton.disabled = true;
      const given = {};
      secretInputs.forEach((s) => { if (s.input.value) (given[s.client] ||= {})[s.field] = s.input.value; });
      try {
        const r = await api("/api/copy-settings/apply", { method: "POST", body: { from: from.value, to: to.value, parts: parts(), secrets: given } });
        secretInputs.forEach((s) => { s.input.value = ""; });
        resultBox.replaceChildren(notice(r.problems.length ? "warning" : "success", r.problems.length ? "Copied, with problems" : "Copied",
          [...r.lines, ...r.problems].join(". ") + "."));
        (r.problems.length ? problem : toast)(r.problems.length ? "Copied, with problems" : "Settings copied");
      } catch (err) { resultBox.replaceChildren(notice("danger", "Not copied", err.message)); copyButton.disabled = false; }
    });
    previewBox.replaceChildren(...[...tables, secrets, notice("info", "Indexers", p.note),
      el("div", { class: "actions" }, copyButton), resultBox].filter(Boolean));
  }

  root.replaceChildren(
    section("cp-choose", "What to copy", "Both apps must be the same kind and the same major version.", form),
    previewBox);
}

