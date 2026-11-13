// Activity, Requests, Issues (DASH-208): what people reported about a film or series, with its thread of comments,
// Comment, Resolve and Reopen. From Reelix.

let issuesShown = "open";

function issueWhen(iso) {
  return iso ? new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "";
}

// The thread and the comment form are in the issue's slide-out, not open inside the row (DASH-309, R6): the row
// keeps its state and Resolve or Reopen; its title opens the slide-out (a row that opens, R1).
function openIssue(i, opener) {
  const name = i.year ? `${i.title} (${i.year})` : i.title;
  const thread = el("div", { class: "stack-2", "aria-live": "polite" }, el("p", { class: "muted", text: "Reading the comments…" }));
  const box = el("textarea", { class: "input", rows: "3", id: `issue-${i.id}-reply`, maxlength: "4000" });
  const send = el("button", { type: "button", class: "btn btn--primary" }, "Add comment");
  const panel = sidePanel({ title: name, opener, body: [
    headChip(i.open ? "Open" : "Resolved", i.open ? "warning" : "success"),
    el("p", { class: "small muted", text: [i.kind, i.where, i.type, i.by ? `reported by ${i.by}` : "", issueWhen(i.when)].filter(Boolean).join(" · ") }),
    i.message ? el("p", { text: i.message }) : null,
    el("h3", { text: "Comments" }), thread,
    el("div", { class: "field" }, el("label", { class: "field__label", for: box.id, text: `Your comment on ${name}` }), box)].filter(Boolean),
  foot: [send] });
  const draw = (full) => thread.replaceChildren(full.thread.length ? el("ul", { class: "rows" }, full.thread.map((c) => el("li", { class: "row row--no-lead" },
    el("div", {}, el("div", { class: "row__title", text: c.message }), el("div", { class: "row__meta", text: [c.by, issueWhen(c.when)].filter(Boolean).join(" · ") })))))
    : el("p", { class: "muted", text: "No comments yet." }));
  const read = async () => { try { draw(await api(`/api/issues/${i.id}`)); } catch (e) { thread.replaceChildren(el("p", { text: e.message })); } };
  send.addEventListener("click", async () => {
    if (!box.value.trim()) { problem("Write a comment first", box); box.focus(); return; }
    send.disabled = true;
    try {
      await api(`/api/issues/${i.id}/comment`, { method: "POST", body: { message: box.value } });
      box.value = "";
      await read();
      announce("Comment added");  // the thread shows it; no toast as well (DASH-309, R5)
      box.focus();
      issuesLoad();
    } catch (e) { problem(e.message, send); }
    finally { send.disabled = false; }
  });
  read();
  return panel;
}

function issueRow(i) {
  const name = i.year ? `${i.title} (${i.year})` : i.title;
  const change = el("button", { type: "button", class: i.open ? "btn" : "btn btn--quiet" }, i.open ? "Resolve" : "Reopen",
    el("span", { class: "visually-hidden", text: ` ${name}` }));
  change.addEventListener("click", () => issueAct(i, i.open ? "resolve" : "reopen", change));
  const title = el("button", { type: "button", "aria-haspopup": "dialog", text: name, onclick: (e) => openIssue(i, e.currentTarget) });
  return el("li", { class: "row row--opens row--no-lead", "data-key": String(i.id) },
    el("div", {},
      el("h3", { class: "row__title" }, title),
      el("div", { class: "row__meta", text: [i.kind, i.where, i.type, i.by ? `reported by ${i.by}` : "", issueWhen(i.when), i.comments ? `${i.comments} ${i.comments === 1 ? "comment" : "comments"}` : ""].filter(Boolean).join(" · ") })),
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
    await issuesLoad();
    announce({ comment: "Comment added", resolve: `Resolved: ${i.title}`, reopen: `Reopened: ${i.title}` }[action]);  // the row shows it (R5)
  } catch (e) { problem(e.message, button); button.disabled = false; }
}

startPage().then(() => {
  // One of several (DASH-309, R4): a segmented control; the radios keep focus and the arrow keys.
  $("#issues-filters").addEventListener("change", (e) => { issuesShown = e.target.value; issuesLoad(); });
  issuesLoad();
});
