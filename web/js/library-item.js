// One item in the Library (DASH-163): the header (name, meta line, description, progress, a fan of the cover), then
// its list (episodes, reading order, albums, the collection) and About. Read from Reelix one item at a time.

const ITEM_TAB = document.querySelector("[data-library-item]")?.dataset.libraryItem;
const WALL = { films: ["library-films.html", "Films"], tv: ["library-tv.html", "TV"], music: ["library-music.html", "Music"],
  radio: ["library-radio.html", "Radio"], books: ["library-books.html", "Books"], audiobooks: ["library-audiobooks.html", "Audiobooks"] };

function rowList(rows) {
  return el("ul", { class: "rows lib-order" }, ...rows.map((r) => el("li", { class: `row${r.number ? "" : " row--no-lead"}` },
    r.number ? el("span", { class: "lib-order__number", text: r.number }) : null,
    el("div", {},
      el("h3", { class: "row__title" }, r.href ? el("a", { href: r.href, text: r.title }) : r.title),
      el("div", { class: "row__meta", text: [r.date, r.note].filter(Boolean).join(" · ") })),
    el("div", { class: "row__side" }, r.status ? chip(r.status, r.tone) : null))));
}

// A long list in groups (a series' seasons): one disclosure each, the newest open. One group stays a plain list.
function groupList(list) {
  if (!list.groups || list.groups.length < 2) return rowList(list.rows);
  return el("div", { class: "lib-seasons" }, ...list.groups.map((g) => el("details", { class: "disclosure", open: g.open || null },
    el("summary", {}, el("span", { text: g.heading }), el("span", { class: "disclosure__meta", text: g.meta })),
    el("div", { class: "disclosure__body" }, rowList(g.rows)))));
}

function about(item) {
  return el("div", { class: "stack-4" },
    item.overview ? el("p", { class: "prose", text: item.overview }) : null,
    item.facts.length ? el("dl", { class: "facts" }, ...item.facts.flatMap((f) => [el("dt", { text: f.label }), el("dd", { text: f.value })])) : null);
}

// In-page tabs: the item's list first, then About. Arrow keys move between them (the tabs pattern).
function tabs(parts) {
  const list = el("div", { class: "lib-tabs", role: "tablist", "aria-label": "Sections" });
  const panels = [];
  parts.forEach((p, n) => {
    const tab = el("button", { type: "button", role: "tab", id: `tab-${p.key}`, "aria-controls": `panel-${p.key}`,
      "aria-selected": String(n === 0), tabindex: n === 0 ? "0" : "-1", text: p.label });
    const panel = el("section", { role: "tabpanel", id: `panel-${p.key}`, "aria-labelledby": `tab-${p.key}`, tabindex: "0", hidden: n !== 0 },
      p.heading && p.heading !== p.label ? el("h2", { class: "lib-panel-heading", text: p.heading }) : null, p.body);
    list.append(tab);
    panels.push(panel);
  });
  const select = (tab) => {
    $$("[role=tab]", list).forEach((t) => {
      const on = t === tab;
      t.setAttribute("aria-selected", String(on));
      t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute("aria-controls")).hidden = !on;
    });
  };
  list.addEventListener("click", (e) => { const t = e.target.closest("[role=tab]"); if (t) select(t); });
  list.addEventListener("keydown", (e) => {
    const all = $$("[role=tab]", list);
    const at = all.indexOf(document.activeElement);
    const go = { ArrowRight: at + 1, ArrowLeft: at - 1, Home: 0, End: all.length - 1 }[e.key];
    if (go === undefined || at < 0) return;
    e.preventDefault();
    const next = all[(go + all.length) % all.length];
    select(next);
    next.focus();
  });
  return [list, ...panels];
}

// The bar's width is set through the style object: the page's security policy refuses style attributes.
function bar(progress) {
  const span = el("span");
  span.style.width = `${Math.round(100 * progress.have / Math.max(1, progress.total))}%`;
  return span;
}

function head(item) {
  const fan = item.poster ? el("div", { class: "cover-fan lib-fan", "aria-hidden": "true" },
    el("img", { src: item.poster, alt: "", decoding: "async", onerror: (e) => e.target.closest(".cover-fan")?.remove() })) : null;
  const actions = [
    item.listen ? newTabLink(item.listen.href, item.listen.label, { className: "btn btn--primary" }) : null,
    item.open ? newTabLink(item.open.href, item.open.label, { className: item.listen ? "btn btn--quiet" : "btn" }) : null,
  ].filter(Boolean);
  return el("header", { class: "series-head" },
    el("div", { class: "series-head__text" },
      el("h1", { class: "series-head__name wordmark", text: item.title }),
      el("p", { class: "series-head__meta" }, ...item.meta.map((m) => el("span", { text: m })), item.status ? chip(item.status, item.tone) : null),
      item.overview ? el("p", { class: "series-head__desc clamp-3", text: item.overview }) : null,
      item.progress ? el("div", { class: "series-head__progress" }, el("span", { text: item.progress.text }),
        el("div", { class: "progress", role: "progressbar", "aria-label": item.progress.text, "aria-valuenow": String(Math.round(100 * item.progress.have / Math.max(1, item.progress.total))),
          "aria-valuemin": "0", "aria-valuemax": "100" }, bar(item.progress))) : null,
      actions.length ? el("div", { class: "series-head__actions" }, ...actions) : null),
    fan);
}

startPage().then(async () => {
  const [wallPage, wallLabel] = WALL[ITEM_TAB];
  const box = $("#item");
  const id = new URLSearchParams(location.search).get("id") || "";
  $("#item-back").replaceChildren(icon("arrow-left"), wallLabel);
  $("#item-back").href = `/${wallPage}`;
  if (!/^\d{1,12}$/.test(id)) {
    box.replaceChildren(el("div", { class: "empty" }, el("p", { text: "That page needs an item from the Library." })));
    return;
  }
  try {
    const item = await api(`/api/library/item?tab=${ITEM_TAB}&id=${id}`);
    document.title = `${item.title} · ${document.title}`;
    const parts = item.lists.filter((l) => l.rows.length).map((l) => ({ key: l.key, label: l.label, heading: l.heading, body: groupList(l) }));
    parts.push({ key: "about", label: "About", heading: "", body: about(item) });
    if (ITEM_TAB === "films") parts.unshift(parts.pop()); // a film opens on About, then its collection
    box.replaceChildren(head(item), ...(parts.length > 1 ? tabs(parts) : [parts[0].body]));
    box.setAttribute("aria-busy", "false");
  } catch (e) {
    box.setAttribute("aria-busy", "false");
    box.replaceChildren(el("div", { class: "notice", "data-tone": e.status === 409 ? "info" : "danger", role: "alert" },
      icon(e.status === 409 ? "info" : "circle-x"),
      el("div", { class: "notice__body" }, el("span", { class: "notice__title", text: e.status === 502 ? "Reelix did not find it" : "This page could not be read" }),
        el("p", { text: e.message }))));
  }
});
