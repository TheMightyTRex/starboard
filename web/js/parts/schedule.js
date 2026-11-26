/* schedule: a part of the shared components. Load it after components.js, on the pages that use it.
 * Made by tools/parts.py from components.js in github.com/TheMightyTRex/design-system: change it there, not here. */
(() => {
  const S = window.SharedComponents;
  const { focusable, announcer, toast, copyText, sprite, escapeHtml, num, fold, andList, say, ownStatus, notice } = S.kit;

  /* Schedule picker: .schedule[data-schedule] with [data-schedule-repeat] (day, week or hour), [data-schedule-time],
     [data-schedule-minute], day checkboxes valued 0 (Sunday) to 6 in [data-schedule-days], and [data-schedule-words]
     and [data-schedule-next] in a polite status. It reads the choice back in words ("Every weekday at 07:00", "Next:
     tomorrow at 07:00") and fires schedule-change with { repeat, days, time, minute, words }. scheduleWords(value) and
     nextRun(value) are exported for an app's own lists. */
  const DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  function scheduleWords({ repeat, days = [], time = "", minute = 0 }) {
    if (repeat === "hour") return Number(minute) ? `Every hour at ${Number(minute)} minute${Number(minute) === 1 ? "" : "s"} past` : "Every hour, on the hour";
    if (!time) return "Choose a time";
    if (repeat === "day" || days.length === 7) return `Every day at ${time}`;
    if (!days.length) return "No days chosen. Choose at least one day";
    const order = [...days].map(Number).sort((a, b) => ((a + 6) % 7) - ((b + 6) % 7));
    if (order.join() === "1,2,3,4,5") return `Every weekday at ${time}`;
    return `Every ${andList(order.map((d) => DAY_NAMES[d]))} at ${time}`;
  }
  function nextRun({ repeat, days = [], time = "", minute = 0 }, now = new Date()) {
    if (repeat === "hour") {
      const t = new Date(now);
      t.setSeconds(0, 0);
      t.setMinutes(Number(minute) || 0);
      if (t <= now) t.setHours(t.getHours() + 1);
      return t;
    }
    if (!time) return null;
    const [h, m] = time.split(":").map(Number);
    const allowed = repeat === "day" ? [0, 1, 2, 3, 4, 5, 6] : days.map(Number);
    for (let add = 0; add < 8; add++) {
      const t = new Date(now.getFullYear(), now.getMonth(), now.getDate() + add, h, m);
      if (t > now && allowed.includes(t.getDay())) return t;
    }
    return null;
  }
  function whenWords(t, now = new Date()) {
    const pad = (n) => String(n).padStart(2, "0");
    const at = `${pad(t.getHours())}:${pad(t.getMinutes())}`;
    const days = Math.round((new Date(t.getFullYear(), t.getMonth(), t.getDate()) - new Date(now.getFullYear(), now.getMonth(), now.getDate())) / 864e5);
    if (days === 0) return `today at ${at}`;
    if (days === 1) return `tomorrow at ${at}`;
    return `${DAY_NAMES[t.getDay()]} ${t.getDate()} ${MONTH_NAMES[t.getMonth()]} at ${at}`;
  }
  function setupSchedules(root = document) {
    root.querySelectorAll(".schedule[data-schedule]").forEach((box) => {
      if (box.dataset.ready) return;
      box.dataset.ready = "1";
      const repeat = box.querySelector("[data-schedule-repeat]");
      const time = box.querySelector("[data-schedule-time]");
      const minute = box.querySelector("[data-schedule-minute]");
      const days = box.querySelector("[data-schedule-days]");
      const words = box.querySelector("[data-schedule-words]");
      const next = box.querySelector("[data-schedule-next]");
      const update = (tell) => {
        const value = {
          repeat: repeat.value,
          days: [...days.querySelectorAll("input:checked")].map((d) => Number(d.value)),
          time: time?.value || "",
          minute: Number(minute?.value || 0),
        };
        days.closest("fieldset, .field").hidden = value.repeat !== "week";
        if (time) time.closest(".field").hidden = value.repeat === "hour";
        if (minute) minute.closest(".field").hidden = value.repeat !== "hour";
        value.words = scheduleWords(value);
        const t = nextRun(value);
        if (words) words.textContent = value.words;
        if (next) next.textContent = t ? `Next: ${whenWords(t)}` : "";
        if (tell) box.dispatchEvent(new CustomEvent("schedule-change", { detail: value }));
      };
      box.addEventListener("change", () => update(true));
      update(false);
    });
  }

  Object.assign(S, { scheduleWords, nextRun, setupSchedules });
  S.addSetup(setupSchedules);
})();
