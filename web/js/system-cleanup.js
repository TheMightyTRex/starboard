// System, Clean up (DASH-77): What is left over (system-cleanup.html) and the Holding folder (system-holding.html).
// Owner rule: Starboard never deletes anything for good by itself. What is left over moves to the holding folder;
// from there the person puts each thing back, or deletes it for good after a danger dialog that says it cannot be
// undone, with their password. Sizes are read when the page opens, never in the background.

const HOLDING_PAGE = location.pathname.endsWith("system-holding.html");
const heldWhen = (t) => (t ? new Date(t * 1000).toLocaleString("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "");
let cleanup = null;

function sizeWords(i) { return `${formatBytes(i.size)}${i.at_least ? " or more" : ""}`; }

// After an action the row goes: focus moves to the same place in the list, or to the list's heading when it is empty.
function focusAfter(listId, index) {
  const buttons = $$(`#${listId} .row__side button:first-of-type`);
  const next = buttons[Math.min(index, buttons.length - 1)];
  if (next) next.focus();
  else { const h = $("#cleanup-list-h"); h.setAttribute("tabindex", "-1"); h.focus(); }
}

function renderLeftOver() {
  const items = cleanup.left_over;
  const movable = items.filter((i) => i.movable);
  $("#cleanup-summary").textContent = items.length
    ? `${items.length} ${items.length === 1 ? "thing" : "things"} left over, ${formatBytes(cleanup.left_over_size)} in all. Starboard never deletes them by itself.`
    : "Nothing is left over. Starboard lists here what earlier versions, removed plug-ins and old backups leave behind.";
  const all = el("button", { type: "button", class: "btn", disabled: !movable.length }, icon("archive"), "Move all to the holding folder");
  all.addEventListener("click", () => hold(movable.map((i) => i.id), all, 0));
  $("#cleanup-actions").replaceChildren(movable.length > 1 ? all : "");
  const list = $("#cleanup-list");
  list.removeAttribute("aria-busy");
  if (!items.length) {
    list.replaceChildren(emptyState("Nothing is left over", "The holding folder has what you moved there before.",
      el("a", { class: "btn btn--primary", href: "/system-holding.html" }, "Open the holding folder")));
    return;
  }
  list.replaceChildren(el("ul", { class: "rows" }, items.map((i, n) => el("li", { class: "row row--no-lead", "data-key": i.id },
    el("div", {}, el("div", { class: "row__title", text: i.what }),
      el("div", { class: "row__meta", text: [sizeWords(i), i.path, heldWhen(i.when)].filter(Boolean).join(" · ") })),
    el("div", { class: "row__side" }, i.movable
      ? el("button", { type: "button", class: "btn btn--compact", onclick: (e) => hold([i.id], e.currentTarget, n) },
        icon("archive"), "Move to the holding folder", el("span", { class: "visually-hidden", text: `: ${i.what}` }))
      : el("span", { class: "small muted", text: "On another disk: move or delete it there yourself" }))))));
}

async function hold(ids, button, index) {
  button.disabled = true;
  try {
    const r = await api("/api/cleanup/hold", { method: "POST", body: { ids } });
    cleanup = r;
    renderLeftOver();
    announce(`Moved ${r.moved.length} to the holding folder. Nothing was deleted.`);
    focusAfter("cleanup-list", index);
  } catch (e) { problem(e.message, button); button.disabled = false; }
}

function renderHolding() {
  const items = cleanup.holding;
  $("#cleanup-summary").textContent = items.length
    ? `${items.length} ${items.length === 1 ? "thing" : "things"}, ${formatBytes(cleanup.holding_size)} in all, in ${cleanup.holding_path}. Put each back, or delete it for good when you are sure.`
    : `Empty. What you move here from What is left over waits in ${cleanup.holding_path} until you put it back or delete it.`;
  const list = $("#cleanup-list");
  list.removeAttribute("aria-busy");
  $("#danger").hidden = !items.length;
  if (!items.length) {
    list.replaceChildren(emptyState("The holding folder is empty", "Move things here from What is left over.",
      el("a", { class: "btn btn--primary", href: "/system-cleanup.html" }, "See what is left over")));
    return;
  }
  list.replaceChildren(el("ul", { class: "rows" }, items.map((i, n) => el("li", { class: "row row--no-lead", "data-key": i.id },
    el("div", {}, el("div", { class: "row__title", text: i.what }),
      el("div", { class: "row__meta", text: [sizeWords(i), i.from ? `from ${i.from.split("/").slice(-3).join("/")}` : "", `moved here ${heldWhen(i.held)}`].filter(Boolean).join(" · ") })),
    el("div", { class: "row__side" },
      el("button", { type: "button", class: "btn btn--compact", onclick: (e) => putBack(i, e.currentTarget, n) },
        icon("undo-2"), "Put back", el("span", { class: "visually-hidden", text: `: ${i.what}` })),
      el("button", { type: "button", class: "btn btn--quiet btn--compact btn--danger", onclick: (e) => deleteForGood([i], e.currentTarget, n) },
        icon("trash-2"), "Delete for good", el("span", { class: "visually-hidden", text: `: ${i.what}` })))))));
}

async function putBack(item, button, index) {
  button.disabled = true;
  try {
    cleanup = await api("/api/cleanup/put-back", { method: "POST", body: { id: item.id } });
    renderHolding();
    announce(`${item.what} is back where it was.`);
    focusAfter("cleanup-list", index);
  } catch (e) { problem(e.message, button); button.disabled = false; }
}

// The danger dialog: what goes, how much, that it cannot be undone, and the password (DESIGN-SYSTEM.md section 9).
async function deleteForGood(items, button, index) {
  const password = el("input", { type: "password", class: "input", autocomplete: "current-password", id: `delete-password-${Date.now()}`, required: true });
  const size = formatBytes(items.reduce((t, i) => t + i.size, 0));
  const ok = await confirmDialog({
    title: items.length === 1 ? "Delete this for good?" : `Delete all ${items.length} for good?`,
    message: [el("p", { text: items.length === 1 ? `${items[0].what}, ${size}.` : `Everything in the holding folder, ${size}.` }),
      el("p", {}, el("strong", { text: "This cannot be undone." }), " It is deleted from this computer, and neither you nor Starboard can bring it back.")],
    fields: [el("div", { class: "field" }, el("label", { for: password.id, text: "Your Starboard password" }), password)],
    confirm: "Delete for good", danger: true });
  if (!ok) return;
  button.disabled = true;
  try {
    let freed = 0;
    for (const i of items) {
      const r = await api("/api/cleanup/delete", { method: "POST", body: { id: i.id, password: password.value } });
      freed += r.freed;
      cleanup = r;
    }
    renderHolding();
    announce(`Deleted for good. ${formatBytes(freed)} freed.`);
    focusAfter("cleanup-list", index);
  } catch (e) { problem(e.message, button); button.disabled = false; }
}

startPage().then(async () => {
  try { cleanup = await api("/api/cleanup"); }
  catch (e) { $("#cleanup-list").replaceChildren(emptyState("Could not look", e.message)); return; }
  if (HOLDING_PAGE) {
    renderHolding();
    const all = $("#delete-all");
    all.prepend(icon("trash-2"));
    all.addEventListener("click", () => deleteForGood(cleanup.holding, all, 0));
  } else {
    renderLeftOver();
  }
});
