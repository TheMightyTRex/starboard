// Updates: each app's running version and, where the app reports it, whether a newer one is out.

async function load() {
  const button = $("#refresh");
  button.disabled = true;
  try {
    const [config, status, updates] = await Promise.all([api("/api/config"), api("/api/status"), api("/api/app-updates")]);
    const running = Object.fromEntries(status.items.map((i) => [i.id, i]));
    const reported = Object.fromEntries(updates.items.map((i) => [i.id, i]));
    $("#updates-errors").replaceChildren(...updates.errors.map((e) => el("p", { class: "notice", "data-tone": "warning", text: e.message })));
    const services = config.services.filter((s) => s.enabled && !s.background);
    // Updates first, then the rest by name.
    services.sort((a, b) => (reported[b.id]?.available ? 1 : 0) - (reported[a.id]?.available ? 1 : 0) || a.name.localeCompare(b.name));
    const list = $("#updates");
    list.replaceChildren();
    let available = 0;
    for (const s of services) {
      const r = reported[s.id];
      const version = r?.installed || running[s.id]?.version || "";
      let side;
      if (r?.available) { available += 1; side = chip(`Version ${r.latest} is out`, "info"); }
      else if (r) side = chip("Up to date", "success");
      else side = chip("Not reported", "muted");
      list.append(el("li", { class: "row service-row" },
        el("div", { class: "service-row__main" }, appIcon(s, "app__icon app__icon--small"), el("div", {},
          el("p", { class: "row__title", text: s.name }),
          el("p", { class: "row__meta num", text: version ? `Running version ${version}` : "Version not reported" }))),
        el("div", { class: "row__side" }, side)));
    }
    const time = new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
    const text = `${available} ${available === 1 ? "update" : "updates"} available · ${updates.items.length} of ${services.length} apps report updates · checked at ${time}`;
    $("#updates-summary").textContent = text;
    announce(text);
  } catch (e) {
    $("#updates-summary").textContent = e.message;
  } finally {
    button.disabled = false;
  }
}

startPage().then(() => { $("#refresh").addEventListener("click", load); load(); });
