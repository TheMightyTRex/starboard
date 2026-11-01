// Apps: every app by category, with its status checked by the server. Health first (the default) also puts
// apps that are not responding in their own group at the top.

let config = null;
let statuses = {};
let health = null;
let outside = {};  // outside address checks, by app

const design = () => document.documentElement.dataset.design;

function statusChip(s) {
  if (!s) return chip("Checking", "neutral");
  return s.state === "up" ? chip("Running", "success") : chip("Not responding", "danger");
}

function addressLine(kind, url, appName) {
  return el("div", { class: "address" },
    el("span", { class: "address__label", text: kind }),
    el("span", { class: "address__value num", text: shortUrl(url) }),
    copyButton(url, `${kind.toLowerCase()} address for ${appName}`));
}

function addresses(s, home) {
  const lines = [];
  if (config.show_home_address && home) lines.push(addressLine("Home", home, s.name));
  if (config.show_outside_address && s.outside_link) {
    const line = addressLine("Outside", s.outside_link, s.name);
    const o = outside[s.id];
    if (o) {
      // A small dot with words for screen readers and a tooltip; the Network page has the details.
      const words = o.reachable ? "Reachable" : "Not reachable";
      line.insertBefore(el("span", { class: "reach-dot", "data-tone": o.reachable ? "success" : "warning", title: words },
        el("span", { class: "visually-hidden", text: `${words}. ` })), line.querySelector(".address__value"));
    }
    lines.push(line);
  }
  return lines.length ? el("div", { class: "app__addresses" }, lines) : null;
}

function appItem(s) {
  const st = statuses[s.id];
  const home = reachableUrl(s.link);
  const item = el("li", { class: "app", "data-state": st ? st.state : "checking" },
    el("div", { class: "app__top" },
      appIcon(s),
      el("h3", { class: "app__name" }, el("a", { href: home, target: "_blank", rel: "noopener noreferrer" }, s.name, el("span", { class: "visually-hidden", text: " (opens in a new tab)" })))),
    s.description ? el("p", { class: "app__desc", text: s.description }) : null,
    addresses(s, home),
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
  // Health first: anything not responding on top, then the categories as usual.
  const health = design() === "health";
  const down = health ? services.filter((s) => statuses[s.id]?.state === "down") : [];
  if (down.length) services = services.filter((s) => !down.includes(s));
  const groups = [...config.groups];
  for (const s of services) if (s.group && !groups.includes(s.group)) groups.push(s.group);
  const out = groups.map((g) => [g, services.filter((s) => s.group === g)]);
  if (down.length) out.unshift(["Not responding", down]);
  out.push(["Other", services.filter((s) => !s.group)]);
  return out.filter(([, items]) => items.length);
}

function renderApps() {
  const root = $("#app-groups");
  root.replaceChildren();
  const services = config.services.filter((s) => s.enabled && !s.background);
  if (!services.length) {
    root.append(el("div", { class: "empty" },
      el("p", { text: "No apps yet." }),
      el("p", {}, el("a", { href: "/settings.html", text: "Add your first app in Settings" }))));
    setStat("stat-running", "No apps yet", "Add your apps in Settings");
    return;
  }
  groupsOf(services).forEach(([title, items], i) => {
    const headingId = `group-${i}`;
    root.append(el("section", { class: "app-group" }, el("h2", { class: "app-group__title", id: headingId, text: title }), appList(items, headingId)));
  });
}

function setStat(id, value, label, tone) {
  const card = $(`#${id}`);
  card.dataset.tone = tone || "";
  $(".stat__value", card).textContent = value;
  $(".stat__label", card).textContent = label;
}

async function checkStatus() {
  const button = $("#check-now");
  button.disabled = true;
  setStat("stat-running", "Checking…", "Your apps");
  try {
    const { items } = await api("/api/status");
    statuses = Object.fromEntries(items.map((i) => [i.id, i]));
    renderApps();
    const mine = items.filter((i) => config.services.some((s) => s.id === i.id && !s.background));
    const up = mine.filter((i) => i.state === "up").length;
    const time = new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
    setStat("stat-running", `${up} of ${mine.length} running`, `Checked at ${time}`, up === mine.length ? "success" : "danger");
    announce(`${up} of ${mine.length} running, checked at ${time}`);
  } catch (e) {
    setStat("stat-running", "Not checked", e.message, "warning");
  } finally {
    button.disabled = false;
  }
}

async function checkOutside() {
  const card = $("#stat-outside");
  const withOutside = config.services.filter((s) => s.enabled && !s.background && s.outside_link);
  if (!withOutside.length) {
    setStat("stat-outside", "Not set up", "Add an outside address to an app in Settings");
    return;
  }
  setStat("stat-outside", "Checking…", "Outside access");
  try {
    const { items } = await api("/api/outside");
    outside = Object.fromEntries(items.map((i) => [i.id, i]));
    const ok = items.filter((i) => i.reachable).length;
    setStat("stat-outside", `${ok} of ${items.length} reachable`, "Outside access, checked from the server", ok === items.length ? "success" : "warning");
    renderApps();
  } catch (e) {
    setStat("stat-outside", "Not checked", e.message, "warning");
  }
  card.title = "Some routers cannot reach their own outside address from inside the home network. Check from a phone on mobile data if this looks wrong.";
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
  $("#check-now").addEventListener("click", () => { checkStatus(); checkOutside(); });
  document.addEventListener("designchange", renderApps);
  checkStatus();
  checkOutside();
  showAttention();
});
