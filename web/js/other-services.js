// Other services: background services with no web page (a VPN, a database, a backup job) and whether they
// are running. Same rows and the same app details slide-out (app-details.js) as the apps; each row says in
// words how Starboard checks it, such as "Follows qBittorrent".

const services = () => (AppDetails.state.config?.services || []).filter((s) => s.enabled && s.background);

// An icon that suits the service, from its name; the words beside it carry the meaning.
function leadIcon(s) {
  const name = `${s.name} ${s.type}`.toLowerCase();
  const kind = /vpn|wireguard|gluetun|tunnel/.test(name) ? "shield-check"
    : /backup|restic|borg|duplicati/.test(name) ? "archive"
    : /postgres|mysql|maria|redis|database|\bdb\b/.test(name) ? "database"
    : /disk|smart|storage/.test(name) ? "hard-drive" : "server-cog";
  return el("span", { class: "app-icon", "aria-hidden": "true" }, icon(kind, 20));
}

function meta(s) {
  const st = AppDetails.state.status[s.id];
  const parts = [];
  const target = s.follows ? AppDetails.service(s.follows) : null;
  if (target || st?.follows) parts.push(`Follows ${target ? target.name : st.follows}`, "no web page");
  else if (s.url) parts.push(shortUrl(reachableUrl(s.url)), st?.ms !== undefined ? `replied in ${st.ms} ms` : null);
  else parts.push("No address, and it follows no other app, so Starboard cannot check it");
  if (st?.state === "down" && st.message) parts.push(st.message);
  return parts.filter(Boolean).join(" · ");
}

function row(s, old) {
  const words = AppDetails.status(s);
  return AppDetails.morph(old, el("li", { class: "row row--lead row--opens", "data-state": words.state },
    leadIcon(s),
    el("div", {}, el("div", { class: "row__title" }, AppDetails.opener(s)), el("div", { class: "row__meta", text: meta(s) })),
    el("div", { class: "row__side" }, chip(words.label, words.tone))));
}

function render() {
  const list = services();
  const empty = !list.length;
  $("#services-empty").hidden = !empty;
  $("#services").hidden = empty;
  $("#add-service").hidden = empty; // the empty state has the one Add button
  $("#check-now").hidden = empty;
  renderKeyed($("#services"), list, (s) => s.id, row);
  $("#services-summary").textContent = summary(list);
}

function summary(list) {
  const { state } = AppDetails;
  if (!list.length) return "No services yet";
  if (!state.loaded.has("status")) return state.errors.status ? `Services not checked: ${state.errors.status}` : "Checking your services…";
  const count = (st) => list.filter((s) => AppDetails.status(s).state === st).length;
  const parts = [`${list.length} ${list.length === 1 ? "service" : "services"}`, `${count("up")} running`];
  if (count("down")) parts.push(`${count("down")} not responding`);
  if (count("unknown") + count("checking")) parts.push(`${count("unknown") + count("checking")} not checked`);
  parts.push(`checked at ${AppDetails.clock(state.checkedAt)}`);
  return parts.join(" · ");
}

async function check() {
  const button = $("#check-now");
  button.disabled = true;
  button.setAttribute("aria-busy", "true");
  $("#services-summary").textContent = "Checking your services…";
  await AppDetails.load("status");
  button.disabled = false;
  button.removeAttribute("aria-busy");
  announce(summary(services()));
}

startPage().then(async () => {
  try {
    await AppDetails.load("config", "status");
  } catch (e) {
    $("#services-summary").textContent = `Could not load your services: ${e.message}`;
    return;
  }
  AppDetails.onChange(render);
  render();
  announce(summary(services()));
  AppDetails.openFromAddress();
  $("#check-now").addEventListener("click", check);
  if (services().some((s) => s.url || s.outside_link)) AppDetails.load("outside");
});
