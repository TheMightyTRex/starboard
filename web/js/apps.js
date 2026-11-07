// Apps: every app by category, with its status checked by the server. Each card opens the app details
// slide-out (app-details.js); Open is its own button. Updates are a filter chip here (/index.html?show=updates),
// not a page of their own. Health first (the default design) puts apps that are not responding in their own
// group at the top; designs.css lays the same cards out for the other four designs.

const FILTERS = [
  { key: "down", label: "Not responding", test: (s) => AppDetails.status(s).state === "down" },
  { key: "updates", label: "Update available", test: (s) => !!AppDetails.update(s) },
  { key: "warnings", label: "Has warnings", test: (s) => AppDetails.warnings(s).length > 0 },
];
const pressed = new Set((new URLSearchParams(location.search).get("show") || "").split(",").filter((k) => FILTERS.some((f) => f.key === k)));
let nameFilter = "";

const design = () => document.documentElement.dataset.design;
const apps = () => (AppDetails.state.config?.services || []).filter((s) => s.enabled && !s.background);

// Cards -------------------------------------------------------------------------------------

function card(s, old) {
  const { config } = AppDetails.state;
  const words = AppDetails.status(s);
  const st = AppDetails.state.status[s.id];
  const u = AppDetails.update(s);
  const warn = AppDetails.warnings(s);
  const o = AppDetails.state.outside[s.id];
  const home = s.link ? reachableUrl(s.link) : "";
  const down = words.state === "down";
  const numbersOff = config.performance?.card_numbers === false;
  // Status, update, then a box for warning and outside chips. Status board keeps them together; Health first and
  // Tiles show the status beside the name, the update in the strip and the rest in their own row.
  const chips = el("span", { class: "card__chips" }, el("span", { class: "card__state" }, chip(words.label, words.tone)),
    u ? el("span", { class: "card__update" }, chip("Update available", "info")) : null,
    el("span", { class: "card__notes" },
      warn.length ? chip(warn.length === 1 ? "1 warning" : `${warn.length} warnings`, "warning") : null,
      o && !o.reachable ? chip("Not reachable from outside", "warning") : null));
  const numbers = AppDetails.state.numbers?.[s.id];
  const activity = down ? "Cannot reach it" : numbers?.length ? numbers.join(" · ") : numbersOff || !st ? "" : "Nothing to report";
  // Every card has the same parts in the same order, so each line sits in the same place on every card.
  return el("li", { class: "card app-card", "data-state": words.state, "data-tone": down ? "danger" : null },
    el("div", { class: "card__top" }, AppDetails.iconFor(s, old), el("h3", { class: "card__title" }, AppDetails.opener(s)),
      el("span", { class: "card__top-state" }, chip(words.label, words.tone))),
    el("p", { class: "small muted card__desc", text: s.description || "" }),
    el("p", { class: `small card__activity${down || !numbers?.length ? " muted" : ""}`, text: activity }),
    el("div", { class: "card__meta card__status" }, chips,
      versionCell(u ? u.installed : st?.version),
      el("span", { class: "card__ms num", text: st?.ms !== undefined ? `${st.ms} ms` : down ? "N/A" : "" }),
      el("span", { class: "card__group", text: s.group || "Other" })),
    el("div", { class: "card__meta card__actions" },
      home ? el("a", { class: "btn", href: home, target: "_blank", rel: "noopener noreferrer" },
        icon("external-link"), "Open", el("span", { class: "visually-hidden", text: ` ${s.name} (opens in a new tab)` })) : null,
      home && config.show_home_address ? copyButton(home, `home address for ${s.name}`) : null,
      home && config.show_home_address ? el("a", { class: "card__address", href: home, target: "_blank", rel: "noopener noreferrer" },
        el("code", { text: shortUrl(home) }), el("span", { class: "visually-hidden", text: `, opens ${s.name} in a new tab` })) : null));
}

// The version, which may break onto a second line only after a dot (2.7.0. then 5723), never inside a number.
function versionCell(version) {
  const parts = version ? `v${version}`.split(/(?<=\.)/) : [];
  return el("span", { class: "card__version num" }, parts.flatMap((p, i) => (i ? [el("wbr"), p] : [p])));
}

function groupsOf(services) {
  const down = design() === "health" ? services.filter((s) => AppDetails.status(s).state === "down") : [];
  const rest = services.filter((s) => !down.includes(s));
  const groups = [...AppDetails.state.config.groups];
  for (const s of rest) if (s.group && !groups.includes(s.group)) groups.push(s.group);
  const out = groups.map((g) => [g, rest.filter((s) => s.group === g)]);
  if (down.length) out.unshift(["Not responding", down]);
  out.push(["Other", rest.filter((s) => !s.group)]);
  return out.filter(([, items]) => items.length);
}

// The column names for the Status board design (hidden in the others; the cards carry their own words).
const headRow = () => el("li", { class: "apps-head", "aria-hidden": "true" },
  el("span", { text: "App" }), el("span", { text: "Status" }), el("span", { text: "Version" }), el("span", { text: "Reply" }), el("span", { text: "Category" }), el("span"));

function renderGroups(services) {
  const root = $("#app-groups");
  renderKeyed(root, groupsOf(services), ([title]) => title, ([title, items], old) => {
    const id = `group-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
    const section = old || el("section", { class: "app-group", "aria-labelledby": id },
      el("h2", { class: "group-heading", id, text: title }), el("ul", { class: "cards app-cards" }));
    const list = $("ul", section);
    const head = list.querySelector(".apps-head") || headRow();
    head.remove(); // renderKeyed looks after the cards only
    renderKeyed(list, items, (s) => s.id, (s, old) => AppDetails.morph(old, card(s, old)));
    list.prepend(head);
    return section;
  });
}

// Toolbar, summary and notice ----------------------------------------------------------------

function setShowInAddress() {
  const url = new URL(location.href);
  if (pressed.size) url.searchParams.set("show", [...pressed].join(",")); else url.searchParams.delete("show");
  history.replaceState(history.state, "", url);
}

function renderChips(services) {
  const box = $("#app-filters");
  const want = FILTERS.map((f) => ({ ...f, count: services.filter(f.test).length }))
    .filter((f) => f.count || pressed.has(f.key));
  renderKeyed(box, want, (f) => f.key, (f, old) => {
    const button = old || el("button", { type: "button", class: "filter-chip", onclick: () => {
      if (pressed.has(f.key)) pressed.delete(f.key); else pressed.add(f.key);
      setShowInAddress();
      render({ announceCount: true });
    } });
    button.textContent = `${f.label}, ${f.count}`;
    button.setAttribute("aria-pressed", String(pressed.has(f.key)));
    return button;
  });
  box.hidden = !want.length;
}

function filtered(services) {
  const q = nameFilter.trim().toLowerCase();
  const active = FILTERS.filter((f) => pressed.has(f.key));
  return services.filter((s) => (!q || s.name.toLowerCase().includes(q) || (s.description || "").toLowerCase().includes(q))
    && (!active.length || active.some((f) => f.test(s))));
}

function summaryText(services) {
  const { state } = AppDetails;
  if (!state.loaded.has("status")) return state.errors.status ? `Apps not checked: ${state.errors.status}` : "Checking your apps…";
  const up = services.filter((s) => AppDetails.status(s).state === "up").length;
  const down = services.filter((s) => AppDetails.status(s).state === "down").length;
  const updates = services.filter((s) => AppDetails.update(s)).length;
  const parts = [`${up} of ${services.length} running`];
  if (down) parts.push(`${down} not responding`);
  if (updates) parts.push(`${updates} ${updates === 1 ? "update" : "updates"} available`);
  parts.push(`checked at ${AppDetails.clock(state.checkedAt)}`);
  return parts.join(" · ");
}

// True for a while after the apps were started (Install apps, Your install): an app that does not answer then is
// most likely still starting, so the notice says so instead of showing an error.
let startedRecently = false;

function renderNotice(services) {
  const box = $("#attention");
  const down = services.filter((s) => AppDetails.status(s).state === "down");
  if (!down.length) { box.replaceChildren(); box.dataset.sig = ""; box.hidden = true; return; }
  const one = down.length === 1 ? down[0] : null;
  const starting = startedRecently;
  const title = starting ? (one ? `${one.name} is still starting` : `${down.length} apps are still starting`)
    : one ? `${one.name} is not responding` : `${down.length} apps are not responding`;
  const text = starting
    ? `${down.map((s) => s.name).join(", ")} ${one ? "has" : "have"} not answered yet. Apps can take a few minutes to answer after they start, longer on a small server. This clears when they do.`
    : one ? `${AppDetails.sentence(AppDetails.state.status[one.id]?.message || "It did not answer")} Check that its container is running.`
    : `${down.map((s) => s.name).join(", ")}. Check that their containers are running.`;
  const sig = `${title}|${text}`;
  if (box.dataset.sig === sig) return; // keep the button, and focus on it, when nothing changed
  box.dataset.sig = sig;
  const action = one
    ? el("button", { type: "button", class: "btn", "aria-haspopup": "dialog", onclick: (e) => AppDetails.open(one.id, e.currentTarget) }, `View ${one.name}`)
    : el("button", { type: "button", class: "btn", onclick: () => { pressed.clear(); pressed.add("down"); setShowInAddress(); render({ announceCount: true }); } }, "Show them");
  box.replaceChildren(el("div", { class: "notice", "data-tone": starting ? "muted" : "danger" }, icon(starting ? "hourglass" : "circle-alert"),
    el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: title }), el("p", { text })), action));
  box.hidden = false;
}

function showAll() {
  pressed.clear();
  nameFilter = "";
  $("#app-filter").value = "";
  setShowInAddress();
  render({ announceCount: true });
  $("#app-filter").focus();
}

function emptyState(services) {
  const box = $("#apps-empty");
  let node = null;
  if (!services.length) {
    node = el("div", { class: "empty" }, icon("layout-grid", 32), el("h2", { text: "No apps yet" }),
      el("p", { text: "Add the apps you run, such as Jellyfin or Sonarr. Starboard checks them and links to them from here." }),
      el("a", { class: "btn btn--primary", href: "/settings.html" }, icon("plus"), "Add an app"));
  } else if (!filtered(services).length) {
    const onlyUpdates = pressed.size === 1 && pressed.has("updates") && !nameFilter.trim();
    const all = el("button", { type: "button", class: "btn", onclick: showAll }, "Show all apps");
    if (onlyUpdates && !AppDetails.state.loaded.has("updates")) {
      node = el("div", { class: "empty" }, el("p", { text: "Asking your apps about updates…" }));
    } else if (onlyUpdates) {
      node = el("div", { class: "empty" }, icon("circle-check", 32), el("h2", { text: "No updates available" }),
        el("p", { text: "Sonarr, Radarr, Lidarr, Readarr and Prowlarr say when they have an update, and none has one. Other apps update when their container image is updated." }), all);
    } else {
      node = el("div", { class: "empty" }, icon("filter", 32), el("h2", { text: "No apps match" }),
        el("p", { text: "Change the filter, or show all apps." }), all);
    }
  }
  const sig = node ? node.textContent : "";
  if (box.dataset.sig !== sig) { box.dataset.sig = sig; box.replaceChildren(...(node ? [node] : [])); }
  box.hidden = !node;
}

function render({ announceCount = false } = {}) {
  if (!AppDetails.state.config) return;
  const services = apps();
  $("#apps-summary").textContent = summaryText(services);
  $("#apps-toolbar").hidden = !services.length;
  renderNotice(services);
  renderChips(services);
  const shown = filtered(services);
  renderGroups(shown);
  const count = shown.length === services.length ? `${services.length} ${services.length === 1 ? "app" : "apps"}` : `Showing ${shown.length} of ${services.length} apps`;
  $("#apps-count").textContent = count;
  emptyState(services);
  if (announceCount) announce(count);
}

async function check() {
  const button = $("#check-now");
  button.disabled = true;
  button.setAttribute("aria-busy", "true");
  $("#apps-summary").textContent = "Checking your apps…";
  await AppDetails.checkAgain("status", "outside", "updates", "health", "numbers");
  button.disabled = false;
  button.removeAttribute("aria-busy");
  announce(summaryText(apps()));
}

startPage().then(async () => {
  try {
    await AppDetails.load("config", "status");
  } catch (e) {
    $("#apps-summary").textContent = `Could not load your apps: ${e.message}`;
    return;
  }
  try { startedRecently = (await api("/api/stack/starting")).starting; } catch { startedRecently = false; }
  if (startedRecently) setTimeout(() => { startedRecently = false; render(); }, 15 * 60 * 1000);
  AppDetails.onChange(() => render());
  render();
  appChangeNotices();
  AppDetails.openFromAddress();
  let typing;
  $("#app-filter").addEventListener("input", (e) => {
    nameFilter = e.target.value;
    clearTimeout(typing);
    render();
    typing = setTimeout(() => announce($("#apps-count").textContent), 600);
  });
  $("#check-now").addEventListener("click", check);
  document.addEventListener("designchange", () => render());
  await AppDetails.load("outside", "updates", "health", "numbers");
  announce(summaryText(apps())); // once, when the first full check is done
});
