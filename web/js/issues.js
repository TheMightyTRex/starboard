// Activity, Requests, Issues (DASH-208): what people reported about a film or series, with its thread of comments,
// Comment, Resolve and Reopen. From Reelix.

let issuesShown = "open";

function issueWhen(iso) {
  return iso ? new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "";
}

function issueRow(i) {
  const name = i.year ? `${i.title} (${i.year})` : i.title;
  const thread = el("div", { class: "stack-2" });
  const details = el("details", { class: "disclosure" },
    el("summary", {}, el("span", { text: i.comments ? `Comments (${i.comments})` : "Comment" })),
    el("div", { class: "disclosure__body stack-2" }, thread));
  const drawThread = (full) => {
    const box = el("textarea", { class: "input", rows: "3", id: `issue-${i.id}-reply`, maxlength: "4000" });
    const send = el("button", { type: "button", class: "btn btn--compact" }, "Add comment");
    send.addEventListener("click", () => issueAct(i, "comment", send, box.value));
    thread.replaceChildren(
      ...(full.thread.length ? [el("ul", { class: "rows" }, full.thread.map((c) => el("li", { class: "row row--no-lead" },
        el("div", {}, el("div", { class: "row__title", text: c.message }), el("div", { class: "row__meta", text: [c.by, issueWhen(c.when)].filter(Boolean).join(" · ") })))))] : []),
      el("label", { class: "field__label", for: box.id, text: `Your comment on ${name}` }), box, el("div", { class: "actions" }, send));
  };
  details.addEventListener("toggle", async () => {
    if (!details.open || thread.childElementCount) return;
    thread.replaceChildren(el("p", { class: "muted", text: "Reading the comments…" }));
    try { drawThread(await api(`/api/issues/${i.id}`)); } catch (e) { thread.replaceChildren(el("p", { text: e.message })); }
  });
  const change = el("button", { type: "button", class: i.open ? "btn" : "btn btn--quiet" }, i.open ? "Resolve" : "Reopen",
    el("span", { class: "visually-hidden", text: ` ${name}` }));
  change.addEventListener("click", () => issueAct(i, i.open ? "resolve" : "reopen", change));
  return el("li", { class: "row row--no-lead", "data-key": String(i.id) },
    el("div", { class: "stack-2" },
      el("h3", { class: "row__title", text: name }),
      el("div", { class: "row__meta", text: [i.kind, i.where, i.type, i.by ? `reported by ${i.by}` : "", issueWhen(i.when)].filter(Boolean).join(" · ") }),
      i.message ? el("p", { text: i.message }) : null, details),
    el("div", { class: "row__side" }, chip(i.open ? "Open" : "Resolved", i.open ? "warning" : "success"), change));
}

async function issuesLoad() {
  const list = $("#issues");
  try {
    const r = await api(`/api/issues?status=${issuesShown}`);
    $("#issues-summary").textContent = `${r.open} open`;
    list.replaceChildren(...(r.items.length ? r.items.map(issueRow) : [el("li", { class: "empty", text: issuesShown === "open" ? "No open issues." : "No issues." })]));
  } catch (e) {
    $("#issues-summary").textContent = e.message;
    list.replaceChildren();
  }
}

async function issueAct(i, action, button, message = "") {
  button.disabled = true;
  try {
    await api(`/api/issues/${i.id}/${action}`, { method: "POST", body: { message } });
    toast({ comment: "Comment added", resolve: `Resolved: ${i.title}`, reopen: `Reopened: ${i.title}` }[action]);
    await issuesLoad();
  } catch (e) { problem(e.message, button); button.disabled = false; }
}

startPage().then(() => {
  const chips = $$("#issues-filters button");
  chips.forEach((c) => c.addEventListener("click", () => {
    issuesShown = c.dataset.status;
    chips.forEach((x) => x.setAttribute("aria-pressed", String(x === c)));
    issuesLoad();
  }));
  issuesLoad();
});
