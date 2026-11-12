// Downloads, From a link (DASH-217): paste a YouTube or Spotify link, see what it holds, choose sound or video, and
// follow the queue with Cancel and Try again. Reelix's full version does the downloading; it keeps this behind its
// admin password, so Starboard asks for it (rxCall in reelix-settings.js).

// settings.js starts the page (header, menus, sign-in); this only fills it.
document.addEventListener("DOMContentLoaded", async () => {
  const root = $("#direct");
  let about = {};
  try { about = await api("/api/reelix/admin/about"); } catch { /* said below */ }
  root.removeAttribute("aria-busy");
  if (about.edition !== "full") {
    root.replaceChildren(notice("info", "This needs the full version of Reelix", "Switch to it in Settings, Your install, then come back."));
    return;
  }
  rxAbout = about;
  const link = el("input", { class: "input", id: "direct-link", type: "url", placeholder: "https://", autocomplete: "off", spellcheck: "false" });
  const mode = el("select", { class: "select", id: "direct-mode" }, [["audio", "Sound only (music, podcasts)"], ["video", "Video"]].map(([v, t]) => el("option", { value: v, text: t })));
  const seen = el("div", { "aria-live": "polite" });
  const look = el("button", { type: "button", class: "btn" }, "See what it holds");
  const get = el("button", { type: "button", class: "btn btn--primary" }, icon("download"), "Download");
  const list = el("ul", { class: "rows" });
  const body = () => ({ url: link.value.trim(), mode: mode.value, playlist: true });
  const showQueue = (r) => list.replaceChildren(...(r.items.length ? r.items.map((d) => {
    const act = (what, label) => { const b = el("button", { type: "button", class: "btn btn--quiet btn--compact" }, label);
      b.addEventListener("click", async () => { try { const o = await rxCall("direct", "change", { id: d.id, what }, "change a download"); if (o) showQueue(o); } catch (e) { problem(e.message, b); } }); return b; };
    return el("li", { class: "row row--no-lead" }, el("div", {}, el("div", { class: "row__title", text: d.url }),
      el("div", { class: "row__meta", text: [d.source === "spotify" ? "Spotify" : "YouTube", d.state, d.progress != null ? `${Math.round(d.progress * 100)}%` : "", d.message].filter(Boolean).join(" · ") })),
      el("div", { class: "row__side" }, ["queued", "running", "downloading"].includes(d.state) ? act("cancel", "Cancel") : d.state === "failed" ? act("retry", "Try again") : null));
  }) : [el("li", { class: "empty", text: "Nothing downloaded from a link yet." })]));
  look.addEventListener("click", async () => {
    setError(link, "");
    try { const r = await rxCall("direct", "preview", body(), "look at the link"); if (r) seen.replaceChildren(el("p", {}, el("strong", { text: r.title || "Found" })),
      el("ul", {}, r.items.slice(0, 20).map((t) => el("li", { text: t }))), r.more ? el("p", { class: "small muted", text: "And more." }) : null); }
    catch (e) { setError(link, e.message); link.focus(); }
  });
  get.addEventListener("click", async () => {
    setError(link, "");
    try { const r = await rxCall("direct", "start", body(), "download from the link"); if (r) { showQueue(r); toast(r.done); link.value = ""; seen.replaceChildren(); } }
    catch (e) { setError(link, e.message); link.focus(); }
  });
  const open = el("button", { type: "button", class: "btn" }, icon("lock"), "Show the downloads");
  open.addEventListener("click", async () => { try { const r = await rxCall("direct", "queue", {}, "show the downloads"); if (r) { showQueue(r); open.hidden = true; } } catch (e) { problem(e.message, open); } });
  root.replaceChildren(
    section("dl-link", "Paste a link", "A video, a playlist, a song or an album. Download only what you have the right to.",
      el("div", { class: "form-stack" }, field("Link", link, { hint: "From youtube.com, youtu.be or open.spotify.com." }), field("What to keep", mode)),
      el("div", { class: "actions" }, get, look), seen),
    section("dl-queue", "Downloads from links", "Newest first. Finished music goes into the folder set in Settings, Reelix.", list, el("div", { class: "actions" }, open)));
});
