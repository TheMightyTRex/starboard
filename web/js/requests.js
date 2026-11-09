// Requests: what people asked for in Seerr (or Jellyseerr, Overseerr), newest first, with Approve and Decline.
// Without Seerr, Reelix's own requests (DASH-157), with Retry for one that failed.

let pendingOnly = true;

function when(iso) {
  return iso ? new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "";
}

function row(r) {
  const what = r.kind === "Series" && r.seasons.length ? `Series, ${r.seasons.length === 1 ? `season ${r.seasons[0]}` : `${r.seasons.length} seasons`}` : r.kind;
  const retry = r.retry ? [el("button", { type: "button", class: "btn", onclick: (e) => act(r, "retry", e.currentTarget) },
    icon("refresh-cw"), "Try again", el("span", { class: "visually-hidden", text: ` ${r.title}` }))] : [];
  const actions = r.pending ? [
    el("button", { type: "button", class: "btn", onclick: (e) => act(r, "approve", e.currentTarget) },
      icon("check"), "Approve", el("span", { class: "visually-hidden", text: ` ${r.title}` })),
    el("button", { type: "button", class: "btn btn--danger", onclick: (e) => act(r, "decline", e.currentTarget) },
      icon("x"), "Decline", el("span", { class: "visually-hidden", text: ` ${r.title}` })),
  ] : [];
  return el("li", { class: "row row--no-lead", "data-key": String(r.id) },
    el("div", {}, el("div", { class: "row__title", text: r.year ? `${r.title} (${r.year})` : r.title }),
      el("div", { class: "row__meta", text: [what, r.by ? `asked for by ${r.by}` : "", when(r.when), r.media].filter(Boolean).join(" · ") })),
    el("div", { class: "row__side" }, chip(r.status, r.tone), ...actions, ...retry));
}

function render(d) {
  if (!d.configured) {
    $("#requests-summary").textContent = "No Reelix or Seerr app with an API key yet.";
    $("#requests-notice").replaceChildren(el("div", { class: "notice", role: "status" }, icon("info"), el("div", { class: "notice__body" },
      el("span", { class: "notice__title", text: "Add Reelix or Seerr to see requests here" }),
      el("p", {}, "In ", el("a", { href: "/settings.html", text: "Manage apps" }), ", add Reelix, or your Seerr, Jellyseerr or Overseerr app, with its API key."))));
    $("#requests").replaceChildren();
    return;
  }
  $("#requests-notice").replaceChildren();
  source = d.source || "seerr";
  const open = $("#requests-open");
  open.hidden = !d.link;
  open.href = reachableUrl(d.link);
  $("span", open).textContent = `Open ${d.name}`;
  $("#requests-summary").textContent = `${d.pending} waiting for approval${pendingOnly ? "" : ` · the newest ${d.items.length}`}`;
  const list = $("#requests");
  if (!d.items.length) list.replaceChildren(el("li", { class: "empty", text: pendingOnly ? "Nothing is waiting for approval." : "No requests yet." }));
  else renderKeyed(list, d.items, (r) => String(r.id), row);
}

async function load(fresh = false) {
  try {
    render(await api(`/api/requests?${pendingOnly ? "pending=1" : ""}${fresh ? "&fresh=1" : ""}`));
  } catch (e) {
    $("#requests-summary").textContent = `Could not ask Seerr: ${e.message}`;
  }
}

let source = "";
async function act(r, action, button) {
  let reason = "";
  if (action === "decline") {
    const why = el("input", { class: "input", id: "decline-why", maxlength: "500" });
    const ok = await confirmDialog({ title: `Decline ${r.title}?`, message: `${r.by || "The person who asked"} sees that it was declined. This cannot be undone here.`,
      confirm: "Decline", danger: true, fields: source === "reelix" ? [el("div", { class: "field" }, el("label", { class: "field__label", for: "decline-why", text: "Why (optional)" }),
        el("p", { class: "hint", text: "They see this with the answer." }), why)] : [] });
    if (!ok) return;
    reason = why.value.trim();
  }
  button.disabled = true;
  try {
    await api(`/api/requests/${r.id}/${action}`, { method: "POST", body: { reason } });
    toast({ approve: `Approved ${r.title}`, decline: `Declined ${r.title}`, retry: `Trying ${r.title} again` }[action]);
    await load(true);
    $("#requests button")?.focus();
  } catch (e) {
    problem(`Not done: ${e.message}`);
    button.disabled = false;
  }
}

startPage().then(() => {
  const chips = [$("#show-pending"), $("#show-all")];
  chips.forEach((c) => c.addEventListener("click", () => {
    pendingOnly = c.id === "show-pending";
    chips.forEach((x) => x.setAttribute("aria-pressed", String(x === c)));
    load();
  }));
  $("#requests-refresh").addEventListener("click", async () => { await load(true); announce($("#requests-summary").textContent); });
  load();
});
