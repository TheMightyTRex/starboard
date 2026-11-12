// Library groups (DASH-163): collections, networks, stations, book series and authors, A to Z, each with how many
// items it holds; selecting one opens the wall filtered to it.

const G = document.querySelector("[data-library-groups]");
const G_TAB = G?.dataset.libraryGroups;
const G_BY = G?.dataset.by || "";
const G_WALL = { films: "library-films.html", tv: "library-tv.html", radio: "library-radio.html", books: "library-books.html",
  audiobooks: "library-audiobooks.html" };
const G_NOUN = { films: ["film", "films"], tv: ["series", "series"], radio: ["show", "shows"], books: ["book", "books"],
  audiobooks: ["audiobook", "audiobooks"] };
let allGroups = [];
// Drawn as banners with a completion ring (12 November 2026): Films, Collections; Audiobooks, Series and Authors.
const BANNERS = ["films", "audiobooks", "books"];

const gLetterId = (letter) => (letter === "#" ? "letter-num" : `letter-${letter.toLowerCase()}`);
const gCount = (n, [one, many]) => `${n.toLocaleString("en-GB")} ${n === 1 ? one : many}`;

// One collection: a banner made from its first poster, blurred, with its films in release order in front (a dashed
// outline for each one not in your library yet, over its faded cover when it has one), then its name, years and a ring showing how complete it is.
function collectionCard(g, href) {
  const films = g.films || [];
  const back = films.find((f) => f.poster)?.poster || g.poster;
  const art = el("div", { class: "collection-card__art", "aria-hidden": "true" },
    back ? el("img", { class: "collection-card__back", src: back, alt: "", loading: "lazy", onerror: (e) => e.target.remove() }) : null,
    // A wanted one shows its cover too, faded behind the dashed outline: a series of books you only want had no
    // covers at all before (owner, 12 November 2026).
    el("div", { class: "collection-card__posters" }, films.map((f) => f.poster
      ? el("img", { class: `collection-card__poster${f.have ? "" : " is-wanted"}`, src: f.poster, alt: "", loading: "lazy", onerror: (e) => e.target.replaceWith(el("span", { class: "collection-card__poster is-missing" })) })
      : el("span", { class: "collection-card__poster is-missing" }))));
  const share = g.count ? g.have / g.count : 0;
  const ring = el("span", { class: `collection-ring${g.have === g.count ? " is-complete" : ""}`, role: "img",
    "aria-label": `${g.have} of ${g.count} in your library` });
  ring.style.setProperty("--done", `${Math.round(share * 100)}`);
  ring.append(el("span", { class: "collection-ring__text", "aria-hidden": "true", text: `${g.have}/${g.count}` }));
  return el("li", { class: "collection-card" }, art,
    el("div", { class: "collection-card__body" },
      el("div", { class: "collection-card__words" },
        el("h3", { class: "collection-card__name" }, el("a", { class: "collection-card__link", href, text: g.name })),
        el("p", { class: "collection-card__meta", text: [g.years, gCount(g.count, G_NOUN[G_TAB])].filter(Boolean).join(" · ") })),
      ring));
}

function drawGroups(words) {
  const box = $("#groups");
  const shown = allGroups.filter((g) => !words || g.name.toLowerCase().includes(words.toLowerCase()));
  box.replaceChildren();
  let ul = null;
  let current = "";
  // TV networks: one grid of square cards, A to Z, the A to Z bar jumping to each letter's first card (owner,
  // 10 November 2026). Other groups: a list under a heading for each letter.
  // Radio stations the same way (owner, 11 November 2026, DASH-321).
  const square = G_TAB === "tv" || G_TAB === "radio";
  const banner = BANNERS.includes(G_TAB);  // one grid of banners too, A to Z (12 November 2026)
  const grid = square ? el("ul", { class: "network-grid", "aria-label": G_TAB === "tv" ? "Networks, A to Z" : "Stations, A to Z" })
    : banner ? el("ul", { class: "collection-grid", "aria-label": `${$("h1")?.textContent || "Groups"}, A to Z` }) : null;
  if (grid) box.append(grid);
  let firstOfLetter = false;
  for (const g of shown) {
    firstOfLetter = g.letter !== current;
    if (g.letter !== current) {
      current = g.letter;
      if (!grid) {
        ul = el("ul", { class: "rows" });
        box.append(el("section", { class: "lib-group", "aria-labelledby": gLetterId(current) },
          el("h2", { class: "wall-letter", id: gLetterId(current), tabindex: "-1", text: current }), ul));
      }
    }
    if (grid) ul = grid;
    const href = `/${G_WALL[G_TAB]}?group=${encodeURIComponent(g.name)}${G_BY ? `&by=${G_BY}` : ""}`;
    if (banner) {  // banners with a completion ring (owner chose idea C, 12 November 2026)
      const card = collectionCard(g, href);
      if (firstOfLetter) { card.id = gLetterId(current); card.tabIndex = -1; }
      ul.append(card);
      continue;
    }
    // TV, Networks (DASH-264): the network's logo in one colour, or its name on a plain tile; never a series' cover.
    const nameTile = () => el("div", { class: "cover cover--result network-logo", "aria-hidden": "true" }, el("span", { class: "network-logo__name", text: g.name }));
    const picture = square
      ? (g.logo ? el("div", { class: "cover cover--result network-logo", "aria-hidden": "true" },
        logoTone(el("img", { src: g.logo, alt: "", loading: "lazy", onerror: (e) => e.target.closest(".network-logo").replaceWith(nameTile()) }), g.name, g.logo_tone, g.logo_kind || "network")) : nameTile())
      : g.poster ? el("div", { class: "cover cover--result", "aria-hidden": "true" }, el("img", { src: g.poster, alt: "", loading: "lazy", onerror: (e) => e.target.remove() }))
        : el("div", { class: "cover cover--result", "aria-hidden": "true" });
    const meta = `${gCount(g.count, G_NOUN[G_TAB])}, ${g.have.toLocaleString("en-GB")} in your library`;
    // The whole card opens the network: its link covers the card (network-card__link::after), so one tab stop each.
    ul.append(square
      ? el("li", { class: "network-card", ...(firstOfLetter ? { id: gLetterId(current), tabindex: "-1" } : {}) }, picture,
        el("h3", { class: "network-card__name" }, el("a", { class: "network-card__link", href, text: g.name })),
        el("p", { class: "network-card__meta", text: meta }))
      : el("li", { class: "row row--opens lib-row" }, picture,
        el("div", {},
          el("h3", { class: "row__title" }, el("a", { href, text: g.name })),
          el("div", { class: "row__meta", text: meta }))));
  }
  const nav = $("#lib-az");
  nav.hidden = !shown.length;
  window.SharedComponents.azJump(nav, new Set(shown.map((g) => g.letter)));
  $("#groups-count").textContent = shown.length ? `${shown.length.toLocaleString("en-GB")} of ${allGroups.length.toLocaleString("en-GB")}` : "";
  if (!shown.length) {
    box.append(el("div", { class: "empty" }, el("p", { text: allGroups.length ? "Nothing matches. Check the spelling." : "There is nothing to group yet." })));
  }
}

startPage().then(async () => {
  if (!G_TAB) return;
  try {
    const data = await api(`/api/library/groups?tab=${G_TAB}${G_BY ? `&by=${G_BY}` : ""}`);
    allGroups = data.groups;
    drawGroups("");
  } catch (e) {
    $("#groups").replaceChildren(el("div", { class: "empty" }, el("p", {
      text: e.status === 409 ? "Starboard shows your library from Reelix. Add Reelix with its key first." : e.message }),
      e.status === 409 ? el("a", { class: "btn btn--primary", href: "/settings.html" }, "Manage apps") : null));
  } finally {
    $("#groups").setAttribute("aria-busy", "false");
  }
  let typing = 0;
  $("#groups-q").addEventListener("input", () => { clearTimeout(typing); typing = setTimeout(() => drawGroups($("#groups-q").value.trim()), 150); });
  $("#groups-search").addEventListener("submit", (e) => { e.preventDefault(); drawGroups($("#groups-q").value.trim()); });
});
