// Settings, Alerts.

// Alerts --------------------------------------------------------------------

function startAlerts() {
  const w = () => config.watch;
  const save = async (body) => {
    try { await saveGeneral({ watch: body }, true); return true; } catch (err) { problem(err.message); return false; }
  };
  const switchFor = (labelId, checked, onChange) => {
    const input = el("input", { type: "checkbox", role: "switch", "aria-labelledby": labelId, checked });
    input.addEventListener("change", async () => { if (!(await onChange(input.checked))) input.checked = !input.checked; });
    return el("label", { class: "switch" }, input);
  };
  const selectFor = (labelId, options, value, onChange) => {
    const select = el("select", { class: "select", "aria-labelledby": labelId },
      options.map(([v, label]) => el("option", { value: String(v), text: label, selected: String(value) === String(v) })));
    let before = select.value;
    select.addEventListener("change", async () => { if (await onChange(select.value, select.selectedOptions[0].text)) before = select.value; else select.value = before; });
    return select;
  };

  // Watching
  const watching = el("ul", { class: "settings-rows" },
    settingRow("Watch in the background", withCost("Checks your apps every few minutes with no page open, keeps their uptime history and sends the alerts you choose here. Inactive: nothing runs in the background.", "watch"),
      switchFor("al-on-l", w().enabled, (on) => save({ enabled: on })), "al-on-l"),
    settingRow("How often", withCost("Each check is a few small requests. Every 5 minutes is plenty for a home server.", "every"),
      selectFor("al-every-l", [[1, "Every minute"], [5, "Every 5 minutes"], [10, "Every 10 minutes"], [15, "Every 15 minutes"], [30, "Every 30 minutes"], [60, "Every hour"]], w().every,
        (v, t) => save({ every: Number(v) })), "al-every-l"));

  // Where alerts go
  const kind = el("select", { class: "select", name: "kind" },
    [["", "Nowhere yet"], ["ntfy", "ntfy"], ["gotify", "Gotify"], ["webhook", "A webhook (JSON)"]].map(([v, t]) => el("option", { value: v, text: t, selected: w().channel.kind === v })));
  const url = el("input", { class: "input", name: "url", inputmode: "url", autocomplete: "off", placeholder: "https://ntfy.sh/your-topic", value: w().channel.url });
  const token = el("input", { class: "input", name: "token", type: "password", autocomplete: "off" });
  const tokenHint = el("span", {});
  const urlHint = el("span", {});
  const describe = () => {
    urlHint.textContent = { ntfy: "The topic's full address, such as https://ntfy.sh/a-long-private-name.", gotify: "Your Gotify server's address.", webhook: "Starboard posts JSON: title, message, level and source." }[kind.value] || "Choose a kind first.";
    tokenHint.textContent = `Optional for ntfy and webhooks; Gotify needs an application token.${w().channel.has_token ? " Leave blank to keep the saved one; it is never shown again." : ""}`;
  };
  kind.addEventListener("change", describe);
  describe();
  const channelError = el("div", { role: "alert" });
  const channelForm = el("form", { novalidate: true },
    el("div", { class: "form-grid" }, field("Send alerts to", kind), field("Address", url, { hint: urlHint, span: true }), field("Token", token, { hint: tokenHint, span: true })),
    el("div", { class: "actions" },
      el("button", { type: "submit", class: "btn", text: "Save where alerts go" }), savedNote("channel-saved"),
      el("button", { type: "button", class: "btn", id: "alert-test", onclick: async (e) => {
        e.currentTarget.disabled = true;
        try { await api("/api/alerts/test", { method: "POST" }); toast("Test alert sent. Check that it arrived."); }
        catch (err) { problem(`Not sent: ${err.message}`); }
        finally { $("#alert-test").disabled = false; }
      } }, icon("send"), "Send a test alert")),
    channelError);
  channelForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    channelError.replaceChildren();
    try {
      await saveGeneral({ watch: { channel: { kind: kind.value, url: url.value, token: token.value } } });
      token.value = "";
      describe();
      showSaved("channel-saved");
    } catch (err) { channelError.replaceChildren(notice("danger", "Not saved", err.message)); }
  });

  // What to alert on
  const a = () => w().alerts;
  const onOff = (key, labelId) => switchFor(labelId, a()[key], (on) => save({ alerts: { [key]: on } }));
  const alertRows = el("ul", { class: "settings-rows" },
    settingRow("An app stops answering", "After two checks in a row, so a restart does not alert. Another message when it answers again.", onOff("apps_down", "al-down-l"), "al-down-l"),
    settingRow("A disk reports a problem", "From Disk health: a failed health check, or reallocated, pending or uncorrectable sectors.", onOff("disk_problem", "al-disk-l"), "al-disk-l"),
    settingRow("A folder gets full", "For the folders on System, Storage.",
      selectFor("al-full-l", [[0, "Off"], [80, "At 80%"], [85, "At 85%"], [90, "At 90%"], [95, "At 95%"]], a().disk_full, (v, t) => save({ alerts: { disk_full: Number(v) } })), "al-full-l"),
    settingRow("A download needs attention", "When it has needed attention for 30 minutes.", onOff("download_stuck", "al-stuck-l"), "al-stuck-l"),
    settingRow("The server backup fails", "From Settings, General, Backup and restore.", onOff("backup_failed", "al-backup-l"), "al-backup-l"),
    settingRow("A certificate runs out soon", "For apps with an outside https:// address. Checked once a day.",
      selectFor("al-cert-l", [[0, "Off"], [7, "7 days before"], [14, "14 days before"], [30, "30 days before"]], a().cert_days, (v, t) => save({ alerts: { cert_days: Number(v) } })), "al-cert-l"));

  const weekly = el("ul", { class: "settings-rows" },
    settingRow("Weekly summary", withCost("On Monday morning: how each app did, disk health and how full your folders are. Sent where alerts go.", "weekly"),
      switchFor("al-week-l", w().weekly, (on) => save({ weekly: on })), "al-week-l"),
    // DASH-105: a new Starboard release, at most one message a week, only where your alerts go.
    settingRow("An update is ready", "One message when a newer Starboard is out, with a link to what is new (at most once a week), and one for each plug-in or app version that waits for you. Nothing is checked for it. What updates by itself is told afterwards instead.",
      switchFor("al-rel-l", w().releases !== false, (on) => save({ releases: on })), "al-rel-l"));

  $("#alerts-sections").removeAttribute("aria-busy");
  $("#alerts-sections").replaceChildren(
    section("al-watch", "Watching", "Uptime history on each app's details needs this active.", watching),
    section("al-where", "Where alerts go", "ntfy, Gotify or a webhook. Starboard keeps the token on the server.", channelForm),
    section("al-what", "What to alert on", "Each alert is sent once, and again only after it has cleared.", alertRows),
    section("al-week", "Weekly summary", null, weekly));
}
