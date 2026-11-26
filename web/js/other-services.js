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
  await AppDetails.checkAgain("status");
  button.disabled = false;
  button.removeAttribute("aria-busy");
  announce(summary(services()));
}

// Starboard's own jobs: the Jellyfin and Audiobookshelf jobs, download hours and watching, with their state and a link to their settings.
const JOB_ICON = { livetv: "tv", import: "import", defaults: "users", hours: "clock", watch: "bell" };

async function renderOwnJobs() {
  let extras = null, hours = null;
  try { [extras, hours] = await Promise.all([api("/api/extras"), api("/api/schedule").catch(() => null)]); } catch { return; }
  const cfg = AppDetails.state.config;
  const rows = extras.jobs.map((j) => ({ key: j.key, title: j.title, what: j.what, on: j.enabled, state: j.state, summary: j.summary, link: j.page || "/settings-jellyfin.html" }));
  rows.push({ key: "hours", title: "Download hours", what: "Pauses qBittorrent, NZBGet and SABnzbd outside the hours you set", on: !!hours?.enabled, link: "/settings-downloads-hours.html" });
  rows.push({ key: "watch", title: "Watching and alerts", what: "Checks your apps every few minutes and sends alerts", on: !!cfg?.watch?.enabled, link: "/settings-general-alerts.html" });
  renderKeyed($("#own-jobs"), rows, (r) => r.key, (r) => {
    const [words, tone] = !r.on ? STATUS.inactive : r.state === "failed" ? STATUS.failed : r.state === "running" ? STATUS.inProgress : STATUS.active;
    return el("li", { class: "row row--lead", "data-key": r.key },
      el("span", { class: "app-icon", "aria-hidden": "true" }, icon(JOB_ICON[r.key] || "server-cog", 20)),
      el("div", {}, el("div", { class: "row__title" }, el("a", { href: r.link, text: r.title })),
        el("div", { class: "row__meta", text: [r.what, r.on && r.summary ? r.summary : ""].filter(Boolean).join(" · ") })),
      el("div", { class: "row__side" }, chip(words, tone)));
  });
}

// Why is this here? (DASH-557, owner, 23 November 2026): what the last search for new apps learned, for each app it found
// (what found it and what it matched on) and each app it did not (the addresses it tried, what answered, and why that
// was not a match). It reads a small saved answer; it searches nothing again. Opened by a button, closed with Escape.
async function openWhy(opener) {
  const panel = sidePanel({ title: "Why is this here?", opener, wide: true, body: [el("p", { class: "muted", text: "Loading…" })],
    foot: [helpCentreLink("topics/why-is-this-here.md")] });
  let last;
  try { last = (await api("/api/discover/last")).last; }
  catch (e) { panel.body.replaceChildren(el("p", { role: "alert", text: `Could not load what the last search learned: ${e.message}` })); return; }
  panel.body.replaceChildren(...whyBody(last));
}

function whyBody(last) {
  if (!last) {
    return [el("p", { text: "Starboard has not searched for apps on this server yet, so there is nothing to explain." }),
      el("p", {}, "Search for them in ", el("a", { href: "/settings.html" }, "Settings, Apps, Manage apps"), ", then open this again.")];
  }
  const found = last.found || [], missing = last.missing || [];
  const list = (rows) => el("ul", { class: "rows" }, rows);
  return [
    el("p", { class: "small muted", text: `Last search ${timeAgo(last.at * 1000)}. ${last.docker ? "Docker access was on, so every port a container publishes was tried as well as each app's usual port."
      : "Docker access was off, so only each app's usual port was tried."} Opening this searches nothing again.` }),
    el("h3", { text: `Found (${found.length})` }),
    found.length ? list(found.map((f) => el("li", { class: "row row--no-lead" },
      el("div", {}, el("div", { class: "row__title", text: f.name }),
        el("div", { class: "row__meta", text: `Found by: ${(f.found_by || []).join("; ") || "its address"}` }),
        el("div", { class: "row__meta", text: `Matched on: ${f.match || "its answer"}` }),
        el("div", { class: "row__meta", text: `Address tried: ${f.url}${f.container ? ` · container ${f.container}` : ""}` })),
      el("div", { class: "row__side" }, f.already ? chip("In Starboard", "success") : chip("Not added", "muted"))))) : el("p", { class: "small muted", text: "It found no app." }),
    el("h3", { text: `Not found (${missing.length})` }),
    el("p", { class: "small muted", text: "Each app Starboard knows that the search did not find, with the addresses it tried and what answered." }),
    missing.length ? list(missing.map((m) => el("li", { class: "row row--no-lead" },
      el("div", {}, el("div", { class: "row__title", text: m.name }),
        (m.tried || []).map((t) => el("div", { class: "row__meta", text: `${t.url.replace("http://", "")}: ${t.answer || "not tried"}${t.reason ? `. ${t.reason}` : ""}` })))))) : null,
  ].filter(Boolean);
}

startPage().then(async () => {
  jsonCardsStart();  // custom cards (DASH-555): the list asks no service; it shows what was last learned
  try {
    await AppDetails.load("config", "status");
  } catch (e) {
    $("#services-summary").textContent = `Could not load your services: ${e.message}`;
    return;
  }
  AppDetails.onChange(render);
  render();
  renderOwnJobs();
  announce(summary(services()));
  AppDetails.openFromAddress();
  $("#check-now").addEventListener("click", check);
  $("#why-here").addEventListener("click", (e) => openWhy(e.currentTarget));
  if (services().some((s) => s.url || s.outside_link)) AppDetails.load("outside");
});
