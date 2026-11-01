// Apps: every app with its status checked by the server. Health first (the default) groups apps by status,
// with the ones not responding at the top; the other designs group them by your groups.

let config = null;
let statuses = {};
let health = null;

const design = () => document.documentElement.dataset.design;

function statusChip(s) {
  if (!s) return chip("Checking", "neutral");
  return s.state === "up" ? chip("Running", "success") : chip("Not responding", "danger");
}

function appItem(s) {
  const st = statuses[s.id];
  const item = el("li", { class: "app", "data-state": st ? st.state : "checking" },
    el("div", { class: "app__top" },
      el("span", { class: "app__icon", "aria-hidden": "true", text: monogram(s.name) }),
      el("h3", { class: "app__name" }, el("a", { href: s.link, target: "_blank", rel: "noopener noreferrer" }, s.name, el("span", { class: "visually-hidden", text: " (opens in a new tab)" })))),
    s.description ? el("p", { class: "app__desc", text: s.description }) : null,
    el("div", { class: "app__meta" },
      el("span", { class: "app__group-label", text: s.group || "Other" }),
      statusChip(st),
      el("span", { class: "app__version num", text: st && st.version ? `v${st.version}` : "" }),
      el("span", { class: "app__ms num", text: st && st.ms !== undefined ? `${st.ms} ms` : "" })));
  return item;
}

function appList(items, headingId) {
  return el("ul", { class: "apps", "aria-labelledby": headingId },
    el("li", { class: "apps-head", "aria-hidden": "true" }, el("span", { text: "App" }), el("span", { text: "Group" }), el("span", { text: "Status" }), el("span", { text: "Version" }), el("span", { text: "Reply" })),
    items.map(appItem));
}

function groupsOf(services) {
  if (design() === "health") {
    const down = services.filter((s) => statuses[s.id]?.state === "down");
    const checking = services.filter((s) => !statuses[s.id]);
    const up = services.filter((s) => statuses[s.id]?.state === "up");
    return [["Not responding", down], ["Checking", checking], ["Running", up]].filter(([, items]) => items.length);
  }
  const groups = [...config.groups];
  for (const s of services) if (s.group && !groups.includes(s.group)) groups.push(s.group);
  const out = groups.map((g) => [g, services.filter((s) => s.group === g)]);
  out.push(["Other", services.filter((s) => !s.group)]);
  return out.filter(([, items]) => items.length);
}

function renderApps() {
  const root = $("#app-groups");
  root.replaceChildren();
  const services = config.services.filter((s) => s.enabled);
  if (!services.length) {
    root.append(el("div", { class: "empty" },
      el("p", { text: "No apps yet." }),
      el("p", {}, el("a", { href: "/settings.html#apps", text: "Add your first app in Settings" }))));
    $("#apps-summary").textContent = "Add your apps in Settings to see them here.";
    return;
  }
  groupsOf(services).forEach(([title, items], i) => {
    const headingId = `group-${i}`;
    root.append(el("section", { class: "app-group" }, el("h2", { class: "app-group__title", id: headingId, text: title }), appList(items, headingId)));
  });
}

async function checkStatus() {
  const button = $("#check-now");
  button.disabled = true;
  $("#apps-summary").textContent = "Checking your apps…";
  try {
    const { items } = await api("/api/status");
    statuses = Object.fromEntries(items.map((i) => [i.id, i]));
    renderApps();
    const up = items.filter((i) => i.state === "up").length;
    const down = items.length - up;
    const time = new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
    const text = `${up} of ${items.length} running${down ? ` · ${down} not responding` : ""} · checked at ${time}`;
    $("#apps-summary").textContent = text;
    announce(text);
  } catch (e) {
    $("#apps-summary").textContent = e.message;
  } finally {
    button.disabled = false;
  }
}

async function showAttention() {
  try {
    health = health || await api("/api/health");
    const box = $("#attention");
    const serious = health.items.filter((i) => i.level === "error" || i.level === "warning");
    if (!serious.length) { box.hidden = true; return; }
    box.replaceChildren(el("div", { class: "notice", "data-tone": "warning" },
      el("strong", { text: `${serious.length} ${serious.length === 1 ? "warning" : "warnings"} from your apps. ` }),
      el("a", { href: "/system.html#health-title", text: "See what needs attention" })));
    box.hidden = false;
  } catch { /* the System page shows the details */ }
}

startPage().then(async () => {
  config = await api("/api/config");
  renderApps();
  $("#check-now").addEventListener("click", checkStatus);
  document.addEventListener("designchange", renderApps);
  checkStatus();
  showAttention();
});
