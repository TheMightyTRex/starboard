// Updates that run with a password, the same on every page that starts them (owner, 26 November 2026: "use the same
// layout and behaviour for every place that lists updates"): the words for each run and state, the password dialog, and
// Install all updates, with its plan, its held-back list and its live panel. Settings, Updates, Settings, Plug-ins, Manage
// and Updates, Plug-ins all use updateBatchPanel; it runs the batch the server already has (update_batch.py: one at a
// time, each with its copy first, health check and way back).

const RUN_WORDS = { updated: ["Updated", "success"], "up-to-date": STATUS.upToDate, "rolled-back": ["Rolled back", "info"],
  "went-back": ["Went back by itself", "warning"], refused: ["Not updated", "warning"], failed: STATUS.failed, running: STATUS.updating,
  "some-updated": ["Some updated", "warning"] };

// Each update's state in Install all updates (DASH-454): words, tone and icon, so the state never rests on colour.
const BATCH_WORDS = { waiting: STATUS.waiting, working: STATUS.updating, done: STATUS.done,
  "went-back": STATUS.wentBack, failed: STATUS.failed, skipped: STATUS.notStarted,
  held: STATUS.heldBack };

const byWords = (by) => (by === "automatic" ? "by itself" : String(by || "").startsWith("api") ? "from the API" : "by you");

// The password dialog every update and Roll back uses: what happens, then the Starboard password. send(password)
// does the request; a wrong password asks again in the same dialog. Returns send's answer, or null when cancelled.
async function updateWithPassword({ title, steps, confirm, send }) {
  const input = el("input", { class: "input", id: `up-pw-${Date.now()}`, type: "password", autocomplete: "current-password", required: true });
  const err = el("span", { class: "field-error", id: `${input.id}-error`, hidden: true });
  input.setAttribute("aria-describedby", err.id);
  const what = el("div", { class: "stack-2" }, el("ul", {}, steps.map((t) => el("li", { text: t }))), el("p", { text: "Enter your Starboard password to go ahead." }));
  for (;;) {
    const asked = confirmDialog({ title, message: what, confirm, fields: [el("div", { class: "field" }, el("label", { for: input.id, text: "Your Starboard password" }), input, err)] });
    if (!(await asked)) return null;
    try { return await send(input.value); } catch (e) {
      if (e.status === 401 || e.status === 429) {
        err.textContent = e.status === 401 ? "That password is not right. Check Caps Lock and try again." : e.message;
        err.hidden = false; input.setAttribute("aria-invalid", "true"); input.value = "";
        continue;
      }
      throw e;
    }
  }
}

// The batch for one page. mount: where the panel goes (it replaces what is there while the batch runs); result: where a
// notice goes; ready(): how many updates the page says are ready; kinds: only these kinds, such as ["plugin"], or none
// for everything; onSettled(followed): the page draws itself again (followed is false when the batch ended before the
// page opened); onClosed(id): the page after Close. Returns { install(opener), show(batch, focus), running(), node() }.
function updateBatchPanel({ mount, result, ready, kinds, onSettled, onClosed }) {
  let shown = null;
  const planLine = (i) => (i.kind === "jellyfin-plugins" ? `${i.name}: ${i.note || "Jellyfin installs any new versions it has"}, and restarts once at the end, when nobody is watching`
    : i.from && i.to ? `${i.name} ${i.from} to ${i.to}` : `${i.name} ${i.to}`.trim());
  // The dialog counts what will run (Jellyfin's plug-ins as one), as the panel does; the page button counts what is
  // ready. These sentences join the two: "4 of the 6 updates ready, plus Jellyfin's plug-ins. They install one at a
  // time, in this order."
  const introText = (plan) => {
    const known = plan.items.filter((i) => i.kind !== "jellyfin-plugins").length, ready = readyNow;
    const jf = plan.items.length > known ? ", plus Jellyfin's plug-ins" : "";
    const which = known === ready ? `${ready === 1 ? "The update is" : `All ${ready} updates are`} ready${jf}` : `${known} of the ${ready} updates are ready${jf}`;
    if (plan.items.length === 1) return `${which}. If it does not work, it goes back by itself.`;
    return `${which}. They install one at a time, in this order. One that does not work goes back by itself, and the rest carry on.`;
  };
  let readyNow = 0;
  const installAll = async (opener, only = null) => {
    readyNow = only ? only.length : ready();
    let password = "";
    let plan;
    try {
      plan = await updateWithPassword({ title: "Install all updates", confirm: "Continue",
        steps: ["Starboard checks each waiting update, then shows you what will install before anything does.",
          "They install one at a time, each with a copy first, a check afterwards and the way back.",
          ...(kinds ? [] : ["Starboard updates last. It restarts, and this page reconnects by itself."])],
        send: async (pw) => { const r = await api("/api/updates/all/plan", { method: "POST", body: { password: pw, kinds } }); password = pw; return r; } });
    } catch (e) {
      const box = notice("danger", "Starboard could not list the updates", e.message);
      box.setAttribute("tabindex", "-1"); result.replaceChildren(box); box.focus();
      return;
    }
    if (!plan) { opener?.focus(); return; }
    if (only) plan = { ...plan, items: plan.items.filter((i) => only.includes(i.target)), held: plan.held.filter((h) => only.includes(h.target)) };
    plan.count = plan.items.length;
    const held = plan.held.length ? [el("h3", { text: `Held back for you (${plan.held.length})` }),
      el("ul", { class: "update-plan" }, plan.held.map((h) => el("li", {}, el("strong", { text: `${h.name} ${h.to}`.trim() }), `: ${h.why}.`.replace(/\.\.$/, "."))))] : [];
    if (!plan.count) {
      const box = notice("info", "Nothing can install all at once", "Each update waiting needs you to choose it on its own.");
      box.setAttribute("tabindex", "-1");
      result.replaceChildren(box, ...held);
      box.focus();
      return;
    }
    const words = `${plan.items.length} ${plan.items.length === 1 ? "update" : "updates"}`;  // what the list shows, as the panel counts
    const message = el("div", { class: "stack-2" },
      el("p", { text: introText(plan) }),
      el("ol", { class: "update-plan" }, plan.items.map((i) => el("li", { text: planLine(i) }))),
      ...held);
    const ok = await confirmDialog({ title: `Install ${words}`, message, confirm: `Install ${words}` });
    if (!ok) { opener?.isConnected && opener.focus(); return; }
    try {
      const r = await api("/api/updates/all/start", { method: "POST", body: { password, targets: plan.items.map((i) => i.target), kinds } });
      password = "";
      showBatch(r.batch, true);
    } catch (e) {
      password = "";
      const box = notice("danger", "The updates did not start", e.message);
      box.setAttribute("tabindex", "-1"); result.replaceChildren(box); box.focus();
    }
  };
  // The batch's panel: each update with its state in words and an icon, the count, what is happening now, a polite
  // live region for each change, and the result at the end. It asks every 2 seconds while the batch runs, and keeps
  // asking while Starboard restarts (no answer for about a minute), then shows how it ended. The words say whether it
  // is still working (#161): "Installing updates" and "4 of 5 done" over a moving bar, then how it ended, with Close.
  const batchEnd = (v) => (v.state === "updated" ? "All updates finished" : v.state === "failed" ? "The updates stopped" : "Some updates did not install");
  const showBatch = (b, focus = false) => {
    const head = el("h3", { id: "update-all-h", tabindex: "-1", text: b.finished ? "Install all updates finished" : "Installing all updates" });
    const count = el("span", { class: "numeric" });
    const label = el("span", { text: b.finished ? batchEnd(b) : "Installing updates" });
    const bar = el("div", { class: `progress${b.finished ? "" : " progress--running"}`, role: "progressbar", "aria-labelledby": "update-all-count", "aria-valuemin": "0" }, el("span"));
    const meter = el("div", { class: "meter" }, el("div", { class: "meter__label", id: "update-all-count" }, label, count), bar);
    const now = el("p", { class: "task-now small", role: "status" });
    const list = el("ul", { class: "task-list", "aria-label": "Each update" });
    const res = el("div", { class: "stack-2" });
    const live = el("div", { class: "visually-hidden", role: "status", "aria-live": "polite" });
    const node = el("section", { class: "update-all", "aria-labelledby": "update-all-h" }, head, meter, now, list, res, live);
    const states = new Map();
    let running = !b.finished, misses = 0;
    const draw = (v) => {
      count.textContent = `${v.ended} of ${v.count} done`;
      label.textContent = v.finished ? batchEnd(v) : "Installing updates";
      bar.classList.toggle("progress--running", !v.finished);
      bar.setAttribute("aria-valuemax", String(v.count || 1));
      bar.setAttribute("aria-valuenow", String(v.ended));
      bar.setAttribute("aria-valuetext", `${v.finished ? batchEnd(v) : "Installing updates"}, ${v.ended} of ${v.count} done`);
      // DASH-489: while it runs the bar is never empty: 1% from the first moment, then each update that ends adds its
      // share. The count in aria-valuenow and the words stay the true count (0 of 5 until the first one ends).
      const share = v.count ? Math.round((100 * v.ended) / v.count) : 100;
      bar.firstChild.style.width = `${v.finished ? share : Math.max(1, share)}%`;
      const changes = [];
      list.replaceChildren(...v.items.map((i) => {
        const [word, tone, ic] = BATCH_WORDS[i.state] || BATCH_WORDS.waiting;
        const li = el("li", { class: "task-list__item", "data-state": i.state },
          el("span", { class: "task-list__name", text: i.label }), chip(word, tone, ic),
          i.detail ? el("span", { class: "task-list__detail small muted", text: i.detail }) : null);
        if (i.state === "working") li.setAttribute("aria-current", "step");
        const before = states.get(i.target);
        if (before && before !== i.state) changes.push(`${i.label}: ${word}`);
        states.set(i.target, i.state);
        return li;
      }));
      if (changes.length) live.textContent = changes.join(". ");
      now.textContent = v.finished ? "" : v.said ? `Now: ${v.said}` : "";
      now.hidden = v.finished || !v.said;
    };
    const end = async (v, followed = true) => {
      running = false;
      head.textContent = "Install all updates finished";
      label.textContent = batchEnd(v);
      bar.classList.remove("progress--running");
      const tone = v.state === "updated" ? "success" : v.state === "failed" ? "danger" : "warning";
      const title = batchEnd(v);
      const box = notice(tone, title, v.said);
      box.setAttribute("tabindex", "-1");
      // Close (DASH-473): takes the finished panel away for good, and focus goes to Ready to update's heading.
      const close = el("button", { type: "button", class: "btn", id: "update-all-close" }, icon("x"), "Close",
        el("span", { class: "visually-hidden", text: " Install all updates" }));
      close.addEventListener("click", () => closeBatch(b.id));
      res.replaceChildren(box, el("div", { class: "actions" }, close));
      if (!followed) { onSettled(false); return; }  // ended before the page opened: shown with the button, nothing announced or moved
      live.textContent = `${title}. ${v.said}`;
      const there = document.activeElement === document.body || node.contains(document.activeElement);
      await onSettled(true);
      if (there) box.focus();  // focus moves to the result only from the panel, never away from what you are doing
    };
    const look = async () => {
      let v = null;
      try { v = await api(`/api/updates/all/${b.id}`); misses = 0; } catch { misses += 1; }
      if (v) { draw(v); if (v.finished) { end(v); return; } }
      else if (misses === 1) { now.hidden = false; now.textContent = "Starboard is restarting. This reconnects by itself."; }
      setTimeout(look, v ? 2000 : 3000);
    };
    draw(b);
    shown = { id: b.id, node, running: () => running };
    mount.replaceChildren(node);
    if (focus) head.focus();
    if (b.finished) end(b, false); else setTimeout(look, 2000);
  };

  // Close on the finished panel: Starboard is told, so the panel does not come back when the page opens again; it
  // goes from the page even when that cannot be saved. Focus moves to Ready to update, and the change is announced.
  const closeBatch = async (id) => {
    try { await api(`/api/updates/all/${id}/close`, { method: "POST" }); } catch { /* closed on this page only */ }
    shown = null;
    onClosed(id);
  };
  return { install: installAll, show: showBatch, running: () => !!shown?.running(), node: () => shown?.node || null };
}
