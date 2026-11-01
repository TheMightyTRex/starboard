// Network: the server's connections, traffic over time, who can open Starboard, and outside access.

let range = null;

async function load() {
  try {
    const [ifaces, net, cfg, outside, hist] = await Promise.all([api("/api/interfaces"), api("/api/network"), api("/api/config"), api("/api/outside"), api(`/api/history?hours=${range.value}`)]);
    const detail = { 1: "Last hour", 6: "Last 6 hours", 24: "Last 24 hours" }[hist.hours];
    $("#network-charts").replaceChildren(
      lineChart({ title: "Traffic", detail, points: hist.points, series: [{ key: "rx", name: "Download", short: "↓" }, { key: "tx", name: "Upload", short: "↑" }], format: perSecond }));
    const stat = (v, l, tone) => el("div", { class: "stat", "data-tone": tone || "" }, el("span", { class: "stat__value", text: v }), el("span", { class: "stat__label", text: l }));
    const reachable = outside.items.filter((i) => i.reachable).length;
    $("#network-stats").replaceChildren(
      stat(net.network_access ? "Home network" : "This computer only", "Who can open Starboard (Settings, Security)"),
      stat(net.addresses[0] ? `${net.addresses[0]}:${net.port}` : `localhost:${net.port}`, "Starboard's address"),
      stat(outside.items.length ? `${reachable} of ${outside.items.length} reachable` : "Not set up", "Outside access", outside.items.length ? (reachable === outside.items.length ? "success" : "warning") : ""));
    $("#interfaces").replaceChildren(...ifaces.items.map((i) => el("li", { class: "row" },
      el("div", {}, el("p", { class: "row__title", text: i.name }),
        el("p", { class: "row__meta num", text: [i.address || "No IPv4 address", i.speed_mbps ? `${i.speed_mbps >= 1000 ? `${i.speed_mbps / 1000} Gbit/s` : `${i.speed_mbps} Mbit/s`}` : null,
          `${formatBytes(i.received)} received`, `${formatBytes(i.sent)} sent`].filter(Boolean).join(" · ") })),
      el("div", { class: "row__side" }, i.state === "up" ? chip("Connected", "success") : chip(i.state === "down" ? "Not connected" : "Unknown", i.state === "down" ? "danger" : "muted")))));
    const byId = Object.fromEntries(cfg.services.map((s) => [s.id, s]));
    $("#outside").replaceChildren(...(outside.items.length ? outside.items.map((o) => {
      const s = byId[o.id];
      return el("li", { class: "row" },
        el("div", { class: "service-row__main" }, appIcon(s, "app__icon app__icon--small"), el("div", {},
          el("p", { class: "row__title", text: s.name }), el("p", { class: "row__meta", text: o.reachable ? `${shortUrl(s.outside_link)} · ${o.ms} ms` : `${shortUrl(s.outside_link)} · ${o.message}` }))),
        el("div", { class: "row__side" }, o.reachable ? chip("Reachable", "success") : chip("Not reachable", "warning"), copyButton(s.outside_link, `outside address for ${s.name}`)));
    }) : [el("li", { class: "empty", text: "No outside addresses yet. Add one to an app in Settings, Apps." })]));
    $("#network-summary").textContent = `${ifaces.items.filter((i) => i.state === "up").length} connected · checked at ${new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}`;
  } catch (e) {
    $("#network-summary").textContent = e.message;
  }
}

startPage().then(() => {
  range = rangePicker(load);
  $("#range-row").append(range.element);
  $("#refresh").addEventListener("click", load);
  load();
});
