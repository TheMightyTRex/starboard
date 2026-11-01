// Coming up: the next two weeks from every app's calendar, by day.

startPage().then(async () => {
  try {
    const data = await api("/api/calendar");
    $("#calendar-errors").replaceChildren(...data.errors.map((e) => el("p", { class: "notice", "data-tone": "warning", text: e.message })));
    const root = $("#calendar");
    if (!data.items.length) {
      root.append(el("p", { class: "empty", text: "Nothing is due in the next two weeks." }));
      $("#calendar-summary").textContent = "Nothing due in the next two weeks.";
      return;
    }
    const byDay = new Map();
    for (const item of data.items) {
      const day = new Date(item.when).toDateString();
      if (!byDay.has(day)) byDay.set(day, []);
      byDay.get(day).push(item);
    }
    const today = new Date().toDateString();
    for (const [day, items] of byDay) {
      const heading = day === today ? "Today" : formatDate(day);
      const id = `day-${byDay.size}-${root.children.length}`;
      root.append(el("section", { "aria-labelledby": id },
        el("h2", { class: "day-heading", id, text: heading }),
        el("ul", { class: "rows" }, items.map((i) => el("li", { class: "row" },
          el("div", {}, el("p", { class: "row__title", text: i.title }), el("p", { class: "row__meta", text: `${i.detail} · ${i.service_name}` })),
          el("div", { class: "row__side" }, i.have ? chip("In library", "success") : chip(new Date(i.when) < new Date() ? "Wanted" : "Not released", "neutral")))))));
    }
    const have = data.items.filter((i) => i.have).length;
    $("#calendar-summary").textContent = `${data.items.length} due · ${have} already in your library`;
  } catch (e) {
    $("#calendar-summary").textContent = e.message;
  }
});
