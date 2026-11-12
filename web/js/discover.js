// Discover by area (owner, 12 November 2026): Films, TV, Music, Radio, Books and Audiobooks, each with its own feeds
// from Reelix as rows of covers. Films and TV have genre chips, Radio its categories; choosing one adds its row at
// the top. A row is asked for only when it comes into view (lightweight rule). Each cover says In your library or
// Wanted, or has Add (Follow for radio), the same slide-out as Search.

const D = document.querySelector("[data-discover]");
const D_TAB = D?.dataset.discover;
const D_WORDS = { films: "films", tv: "series", music: "artists", radio: "shows", books: "books", audiobooks: "audiobooks" };

function dCard(c) {
  const kindWord = c.kind === "radio" ? "Follow" : "Add";
  let side;
  if (c.state === "have") side = chip("In your library", "success");
  else if (c.state === "wanted") side = chip("Wanted", "info");
  else {
    side = el("button", { type: "button", class: "btn btn--compact" }, icon(c.kind === "radio" ? "radio" : "plus"), kindWord,
      el("span", { class: "visually-hidden", text: ` ${c.title}` }));
    side.addEventListener("click", () => addPanel(c, side));
  }
  return el("li", { class: "discover-card" }, smallCover(c.image, c.title, "cover discover-card__cover"),
    el("h3", { class: "discover-card__title", text: c.title }),
    el("p", { class: "discover-card__meta", text: [c.year, c.detail].filter(Boolean).join(" · ") }),
    el("div", { class: "discover-card__action" }, side));
}

function dRow(r, { open = false } = {}) {
  const list = el("ul", { class: "discover-shelf", "aria-label": r.title }, el("li", { class: "muted small", text: "Loading…" }));
  const sec = el("section", { class: "discover-row", "aria-labelledby": `d-${r.id.replace(/[^a-z0-9]/gi, "-")}` },
    el("div", { class: "discover-row__head" }, el("h2", { id: `d-${r.id.replace(/[^a-z0-9]/gi, "-")}`, text: r.title }),
      r.source ? el("span", { class: "small muted", text: r.source }) : null), list);
  const load = async () => {
    try {
      const got = await api(`/api/library/discover-row?tab=${D_TAB}&row=${encodeURIComponent(r.id)}`);
      list.replaceChildren(...(got.items.length ? got.items.map(dCard) : [el("li", { class: "muted small", text: "Nothing here right now." })]));
    } catch (e) { list.replaceChildren(el("li", {}, notice("info", "This row did not load", e.message))); }
  };
  if (open || !("IntersectionObserver" in window)) load();
  else {
    const watch = new IntersectionObserver((seen) => { if (seen.some((s) => s.isIntersecting)) { watch.disconnect(); load(); } }, { rootMargin: "300px" });
    watch.observe(sec);
  }
  return sec;
}

async function startDiscover() {
  const holder = $("#discover-rows");
  let d;
  try { d = await api(`/api/library/discover?tab=${D_TAB}`); }
  catch (e) { holder.removeAttribute("aria-busy"); holder.replaceChildren(notice("danger", "Discover did not load", e.message)); return; }
  holder.removeAttribute("aria-busy");
  const picked = el("div", { id: "discover-picked" });
  const chips = d.genres.length ? el("div", { class: "filter-chips discover-genres", role: "group", "aria-label": D_TAB === "radio" ? "Categories" : "Genres" },
    ...d.genres.map((g) => {
      const b = el("button", { type: "button", class: "filter-chip", "aria-pressed": "false" }, g.title);
      b.addEventListener("click", () => {
        const on = b.getAttribute("aria-pressed") !== "true";
        $$(".discover-genres .filter-chip").forEach((x) => x.setAttribute("aria-pressed", "false"));
        b.setAttribute("aria-pressed", String(on));
        picked.replaceChildren(...(on ? [dRow(g, { open: true })] : []));
        if (on) picked.querySelector("h2")?.setAttribute("tabindex", "-1");
      });
      return b;
    })) : null;
  holder.replaceChildren(...[chips, picked, ...d.rows.map((r, n) => dRow(r, { open: n < 2 }))].filter(Boolean));
}

startPage().then((s) => { if (s && D) startDiscover(); });
