// App logs on System, Logs (DASH-223): each app's latest lines, in place of Dozzle. Only for people signed in to
// Starboard; keys, passwords, addresses and names are hidden by the server before they reach the page.
document.addEventListener("DOMContentLoaded", async () => {
  const box = $("#applogs");
  if (!box) return;
  let r;
  try { r = await api("/api/app-logs"); } catch { return; }
  if (!r.available || !r.apps.length) return;
  box.hidden = false;
  const pick = el("select", { class: "select", id: "applogs-app" }, r.apps.map((a) => el("option", { value: a.name, text: a.state === "running" ? a.name : `${a.name} (${a.state})` })));
  const lines = el("select", { class: "select", id: "applogs-lines" }, [["100", "Last 100 lines"], ["300", "Last 300 lines"], ["1000", "Last 1,000 lines"]]
    .map(([v, t]) => el("option", { value: v, text: t, selected: v === "300" })));
  const find = el("input", { class: "input", type: "search", id: "applogs-find", placeholder: "Only lines with…", autocomplete: "off" });
  const show = el("button", { type: "button", class: "btn btn--primary", text: "Show" });
  const said = el("p", { class: "small muted", "aria-live": "polite" });
  const out = el("pre", { class: "log-lines", tabindex: "0", "aria-label": "App log lines" });
  const copy = el("button", { type: "button", class: "btn", text: "Copy" });
  const label = (text, input) => el("div", { class: "field" }, el("label", { for: input.id, text }), input);
  const load = async () => {
    show.disabled = true;
    try {
      const q = new URLSearchParams({ tail: lines.value, find: find.value.trim() });
      const got = await api(`/api/app-logs/${encodeURIComponent(pick.value)}?${q}`);
      out.textContent = got.lines.join("\n") || "Nothing to show.";
      said.textContent = `${got.lines.length} ${got.lines.length === 1 ? "line" : "lines"} from ${got.name}, newest last.`;
      out.scrollTop = out.scrollHeight;
    } catch (e) { said.textContent = e.message; }
    finally { show.disabled = false; }
  };
  show.addEventListener("click", load);
  find.addEventListener("keydown", (e) => { if (e.key === "Enter") load(); });
  copy.addEventListener("click", async () => { try { await navigator.clipboard.writeText(out.textContent); toast("Log lines copied"); } catch { /* the lines can be selected by hand */ } });
  $("#applogs-body").replaceChildren(
    el("div", { class: "form-stack" }, label("App", pick), label("How many", lines), label("Only lines with", find)),
    el("div", { class: "actions" }, show, copy), said, out);
});
