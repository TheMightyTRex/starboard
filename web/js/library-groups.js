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

const gLetterId = (letter) => (letter === "#" ? "letter-num" : `letter-${letter.toLowerCase()}`);
const gCount = (n, [one, many]) => `${n.toLocaleString("en-GB")} ${n === 1 ? one : many}`;

function drawGroups(words) {
  const box = $("#groups");
  const shown = allGroups.filter((g) => !words || g.name.toLowerCase().includes(words.toLowerCase()));
  box.replaceChildren();
  let ul = null;
  let current = "";
  for (const g of shown) {
    if (g.letter !== current) {
      current = g.letter;
      ul = el("ul", { class: "rows" });
      box.append(el("section", { class: "lib-group", "aria-labelledby": gLetterId(current) },
        el("h2", { class: "wall-letter", id: gLetterId(current), tabindex: "-1", text: current }), ul));
    }
    const href = `/${G_WALL[G_TAB]}?group=${encodeURIComponent(g.name)}${G_BY ? `&by=${G_BY}` : ""}`;
    // TV, Networks (DASH-264): the network's logo in one colour, or its name on a plain tile; never a series' cover.
    const nameTile = () => el("div", { class: "cover cover--result network-logo", "aria-hidden": "true" }, el("span", { class: "network-logo__name", text: g.name }));
    const picture = G_TAB === "tv"
      ? (g.logo ? el("div", { class: "cover cover--result network-logo", "aria-hidden": "true" },
        el("img", { src: g.logo, alt: "", loading: "lazy", onerror: (e) => e.target.closest(".network-logo").replaceWith(nameTile()) })) : nameTile())
      : g.poster ? el("div", { class: "cover cover--result", "aria-hidden": "true" }, el("img", { src: g.poster, alt: "", loading: "lazy", onerror: (e) => e.target.remove() }))
        : el("div", { class: "cover cover--result", "aria-hidden": "true" });
    ul.append(el("li", { class: "row row--opens lib-row" }, picture,
      el("div", {},
        el("h3", { class: "row__title" }, el("a", { href, text: g.name })),
        el("div", { class: "row__meta", text: `${gCount(g.count, G_NOUN[G_TAB])}, ${g.have.toLocaleString("en-GB")} in your library` }))));
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
