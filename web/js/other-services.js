// Other services: background services with no web page, and whether they are running.

let config = null;

function words(st) {
  if (!st || st.state === "unknown") return ["Not checked", "muted"];
  return st.state === "up" ? ["Running", "success"] : ["Not responding", "danger"];
}

async function load() {
  const button = $("#check-now");
  button.disabled = true;
  try {
    config = config || await api("/api/config");
    const services = config.services.filter((s) => s.enabled && s.background);
    const list = $("#services");
    list.replaceChildren();
    if (!services.length) {
      list.append(el("li", { class: "empty" }, "No background services yet. ", el("a", { href: "/settings.html", text: "Add one in Settings" }), " and tick Background service."));
      $("#services-summary").textContent = "None yet.";
      return;
    }
    const { items } = await api("/api/status");
    const byId = Object.fromEntries(items.map((i) => [i.id, i]));
    for (const s of services) {
      const st = byId[s.id];
      const [label, tone] = words(st);
      const how = st?.follows ? `Follows ${st.follows}` : s.url ? shortUrl(s.url) : "No address to check";
      list.append(el("li", { class: "row service-row" },
        el("div", { class: "service-row__main" }, appIcon(s, "app__icon app__icon--small"), el("div", {},
          el("p", { class: "row__title", text: s.name }),
          s.description ? el("p", { class: "row__meta", text: s.description }) : null,
          el("p", { class: "row__meta", text: st?.message ? `${how} · ${st.message}` : how }))),
        el("div", { class: "row__side" }, chip(label, tone))));
    }
    const checked = services.filter((s) => byId[s.id] && byId[s.id].state !== "unknown");
    const up = checked.filter((s) => byId[s.id].state === "up").length;
    const time = new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
    const text = `${up} of ${checked.length} running · ${services.length - checked.length} not checked · checked at ${time}`;
    $("#services-summary").textContent = text;
    announce(text);
  } catch (e) {
    $("#services-summary").textContent = e.message;
  } finally {
    button.disabled = false;
  }
}

startPage().then(() => { $("#check-now").addEventListener("click", load); load(); });
