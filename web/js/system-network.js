// Network: download and upload now and over time, the server's connections, who can open Starboard (a link
// to Settings, Security) and each app's outside address. Outside access rows open the app details slide-out
// (app-details.js), the same one as on Apps.

let range = null;
let chart = null;

const clockNow = () => AppDetails.clock();

function stat(value, label, tone, extra) {
  return el("div", { class: "stat", "data-tone": tone || null },
    el("span", { class: "stat__value", text: value }), el("span", { class: "stat__label", text: label }), extra || null);
}

function outsideItems() {
  const { config, outside } = AppDetails.state;
  return (config?.services || []).filter((s) => s.enabled && s.outside_link).map((s) => ({ s, o: outside[s.id] }));
}

function renderStats(points) {
  const latest = points[points.length - 1];
  const items = outsideItems();
  const checked = items.filter((i) => i.o);
  const ok = checked.filter((i) => i.o.reachable).length;
  let outside;
  if (!items.length) outside = stat("None yet", "Outside addresses");
  else if (!AppDetails.state.loaded.has("outside")) outside = stat("Checking", "Outside addresses reachable");
  else {
    const bad = checked.length - ok;
    outside = stat(`${ok} of ${checked.length}`, "Outside addresses reachable", bad ? "warning" : "success",
      chip(bad ? `${bad} not reachable` : "All reachable", bad ? "warning" : "success"));
  }
  $("#network-stats").replaceChildren(
    stat(latest ? perSecond(latest.rx) : "Collecting", "Download now"),
    stat(latest ? perSecond(latest.tx) : "Collecting", "Upload now"),
    outside);
}

function renderAccess(net) {
  const where = net.addresses[0] ? `${net.addresses[0]}:${net.port}` : `localhost:${net.port}`;
  $("#access-line").replaceChildren(icon(net.network_access ? "shield-check" : "lock"),
    el("span", { text: net.network_access
      ? `Phones and computers on your home network can open Starboard at ${where}.`
      : "Only this computer can open Starboard." }),
    el("a", { href: "/settings-security.html", text: "Change who can open it in Security" }));
}

function renderInterfaces(items) {
  renderKeyed($("#interfaces"), items, (i) => i.name, (i, old) => {
    const vpn = /^(wg|tun|tap|ppp)/.test(i.name);
    const speed = i.speed_mbps ? (i.speed_mbps >= 1000 ? `${i.speed_mbps / 1000} Gb/s` : `${i.speed_mbps} Mb/s`) : null;
    const state = i.state === "up" ? chip("Connected", "success") : chip(i.state === "down" ? "Not connected" : "Unknown", i.state === "down" ? "danger" : "muted");
    return AppDetails.morph(old, el("li", { class: "row row--lead" },
      el("span", { class: "app-icon", "aria-hidden": "true" }, icon(vpn ? "shield-check" : /^wl/.test(i.name) ? "wifi" : "network", 20)),
      el("div", {}, el("div", { class: "row__title", text: vpn ? `VPN, ${i.name}` : i.name }),
        el("div", { class: "row__meta num", text: [i.address || "No IPv4 address", speed, `received ${formatBytes(i.received)}`, `sent ${formatBytes(i.sent)}`].filter(Boolean).join(" · ") })),
      el("div", { class: "row__side" }, state)));
  });
}

function renderOutside() {
  const items = outsideItems();
  const list = $("#outside");
  $("#outside-empty").hidden = !!items.length;
  list.hidden = !items.length;
  renderKeyed(list, items, (i) => i.s.id, ({ s, o }, old) => {
    const side = !o ? chip("Checking", "neutral") : !o.reachable ? chip("Not reachable", "danger")
      : o.cert_days != null && o.cert_days <= 14 ? chip("Certificate runs out soon", "warning") : chip("Reachable", "success");
    const cert = o?.cert_days == null ? "" : o.cert_days < 0 ? "certificate has run out" : `certificate runs out in ${o.cert_days} ${o.cert_days === 1 ? "day" : "days"}`;
    const after = !o ? "" : o.reachable ? [`${o.ms} ms`, cert].filter(Boolean).join(" · ") : (o.message || "no answer");
    return AppDetails.morph(old, el("li", { class: "row row--lead row--opens row--phone-short" },
      AppDetails.iconFor(s, old),
      el("div", {}, el("div", { class: "row__title" }, AppDetails.opener(s)),
        el("div", { class: "row__meta" }, el("code", { text: shortUrl(s.outside_link) }), after ? ` · ${after}` : "")),
      el("div", { class: "row__side" }, side)));
  });
}

function summary(ifaces) {
  const up = ifaces.filter((i) => i.state === "up").length;
  const parts = [`${up} ${up === 1 ? "connection" : "connections"} up`];
  const items = outsideItems();
  if (items.length && AppDetails.state.loaded.has("outside")) {
    parts.push(`${items.filter((i) => i.o?.reachable).length} of ${items.length} outside addresses reachable`);
  }
  parts.push(`updated at ${clockNow()}`);
  return parts.join(" · ");
}

let lastIfaces = [];
let lastPoints = [];

async function loadTraffic() {
  const hist = await api(`/api/history?hours=${range.value}`);
  lastPoints = hist.points;
  const detail = { 1: "Last hour", 6: "Last 6 hours", 24: "Last 24 hours" }[hist.hours];
  const opts = { title: "Traffic", detail, span: RANGE_WORDS[hist.hours], points: hist.points, format: perSecond,
    series: [{ key: "rx", name: "Download" }, { key: "tx", name: "Upload" }] };
  if (chart) chart.update(opts);
  else { chart = lineChart(opts); $("#network-charts").replaceChildren(chart); }
  renderStats(lastPoints);
}

async function load({ speak = false } = {}) {
  const button = $("#refresh");
  button.disabled = true;
  button.setAttribute("aria-busy", "true");
  try {
    const [ifaces, net] = await Promise.all([api("/api/interfaces"), api("/api/network"), loadTraffic()]);
    lastIfaces = ifaces.items;
    renderAccess(net);
    renderInterfaces(ifaces.items);
    renderOutside();
    $("#network-summary").textContent = summary(lastIfaces);
    await AppDetails.load("outside");
    $("#network-summary").textContent = summary(lastIfaces);
    if (speak) announce($("#network-summary").textContent);
  } catch (e) {
    $("#network-summary").textContent = e.message;
  } finally {
    button.disabled = false;
    button.removeAttribute("aria-busy");
  }
}

startPage().then(async () => {
  range = rangePicker(() => loadTraffic().catch((e) => problem(e.message)));
  $("#range-row").append(range.element);
  $("#refresh").addEventListener("click", () => { load({ speak: true }); AppDetails.load("status"); });
  try { await AppDetails.load("config"); } catch (e) { $("#network-summary").textContent = e.message; return; }
  AppDetails.onChange(() => { renderOutside(); renderStats(lastPoints); });
  await load({ speak: true });
  AppDetails.openFromAddress();
  AppDetails.load("status");
});
