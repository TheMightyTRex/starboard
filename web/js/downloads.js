// Downloads: the queues of every app in one list, updated every 15 seconds (can be paused).

let items = [];
let filter = "All";
let timer = null;

const STATE_WORDS = {
  downloading: ["Downloading", "info"], importPending: ["Waiting to import", "neutral"], importing: ["Importing", "info"],
  imported: ["In library", "success"], importBlocked: ["Needs attention", "warning"], failedPending: ["Failed", "danger"], failed: ["Failed", "danger"],
  paused: ["Paused", "muted"], queued: ["Waiting", "neutral"], delay: ["Waiting", "neutral"], completed: ["Downloaded", "success"],
};

function words(item) {
  if (item.problem) return ["Needs attention", "warning"];
  return STATE_WORDS[item.status] || [item.status ? item.status[0].toUpperCase() + item.status.slice(1) : "Waiting", "neutral"];
}

function render() {
  const counts = { All: items.length };
  for (const i of items) { const w = words(i)[0]; counts[w] = (counts[w] || 0) + 1; }
  const filters = $("#queue-filters");
  filters.replaceChildren(...Object.entries(counts).map(([k, n]) => el("button", {
    type: "button", class: "filter-chip", "aria-pressed": String(filter === k), onclick: () => { filter = k; render(); },
  }, `${k}, ${n}`)));
  if (!counts[filter]) filter = "All";
  const list = $("#queue");
  list.replaceChildren();
  const shown = items.filter((i) => filter === "All" || words(i)[0] === filter);
  if (!shown.length) list.append(el("li", { class: "empty", text: "Nothing downloading." }));
  for (const i of shown) {
    const [label, tone] = words(i);
    const bar = el("div", { class: "progress", role: "progressbar", "aria-valuenow": String(Math.round(i.progress)), "aria-valuemin": "0", "aria-valuemax": "100", "aria-label": `${i.title}, ${Math.round(i.progress)}%` }, el("span"));
    bar.firstChild.style.width = `${i.progress}%`;
    list.append(el("li", { class: "row" },
      el("div", {},
        el("p", { class: "row__title", text: i.title }),
        el("p", { class: "row__meta num", text: [i.service_name, i.client, formatBytes(i.size), i.time_left ? `${i.time_left} left` : ""].filter(Boolean).join(" · ") }),
        ...i.messages.map((m) => el("p", { class: "row__meta", text: m }))),
      el("div", { class: "row__side" }, el("span", { class: "num", text: `${Math.round(i.progress)}%` }), chip(label, tone)),
      bar));
  }
}

async function load() {
  try {
    const data = await api("/api/queue");
    items = data.items;
    $("#queue-errors").replaceChildren(...data.errors.map((e) => el("p", { class: "notice", "data-tone": "warning", text: e.message })));
    const active = items.filter((i) => i.status === "downloading").length;
    $("#queue-summary").textContent = `${items.length} in the queue · ${active} downloading`;
    render();
  } catch (e) {
    $("#queue-summary").textContent = e.message;
  }
}

function setAuto(on) {
  const button = $("#auto-refresh");
  clearInterval(timer);
  timer = on ? setInterval(load, 15000) : null;
  button.setAttribute("aria-pressed", String(on));
  button.textContent = on ? "Pause updates" : "Resume updates";
}

startPage().then(() => {
  $("#refresh").addEventListener("click", load);
  $("#auto-refresh").addEventListener("click", () => setAuto(!timer));
  load();
  setAuto(true);
});
