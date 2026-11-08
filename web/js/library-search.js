// Search (DASH-162): opens on what you already have (recently added, then each kind with its count), searches your
// library first as you type, then shows what Reelix finds under "Not in your library", with Add, or Follow for radio.
// Without Reelix, the page falls back to searching Sonarr, Radarr, Lidarr and Readarr (search.js).

const KIND_PAGE = { films: "library-films.html", tv: "library-tv.html", music: "library-music.html", radio: "library-radio.html",
  books: "library-books.html", audiobooks: "library-audiobooks.html" };
const KIND_ITEM = { films: "library-film.html", tv: "library-tv-show.html", music: "library-artist.html", radio: "library-radio-show.html",
  books: "library-book.html", audiobooks: "library-audiobook.html" };
const KIND_NAME = { films: ["film", "films"], tv: ["series", "series"], music: ["artist", "artists"], radio: ["show", "shows"],
  books: ["book", "books"], audiobooks: ["audiobook", "audiobooks"] };
let libTyping = 0;
let lookTyping = 0;
let lookAsked = "";
let libAsked = "";
let legacyMode = false; // no Reelix: search.js searches the apps instead

const nCount = (n, [one, many]) => `${n.toLocaleString("en-GB")} ${n === 1 ? one : many}`;

function smallCover(src, title, className = "cover cover--result") {
  const box = el("div", { class: className, "aria-hidden": "true" });
  if (src) {
    const img = el("img", { src, alt: "", loading: "lazy", decoding: "async" });
    img.addEventListener("error", () => img.replaceWith(el("span", { class: "lib-cover-title", text: title })), { once: true });
    box.append(img);
  } else box.append(el("span", { class: "lib-cover-title", text: title }));
  return box;
}

async function drawStart() {
  const box = $("#lib-start");
  const data = await api("/api/library/overview");
  const recent = data.recent.length ? el("section", { class: "media-section", "aria-labelledby": "recent-h" },
    el("h2", { id: "recent-h", text: "Recently added" }),
    el("ul", { class: "media-grid lib-recent", "data-size": "small" }, ...data.recent.slice(0, 8).map((c) => el("li", { class: "media-card lib-card" },
      smallCover(c.poster, c.title, "cover"),
      el("span", { class: "media-card__title" }, el("a", { href: `/${KIND_ITEM[c.tab]}?id=${c.id}`, text: c.title })),
      el("span", { class: "media-card__meta", text: c.meta || "" }))))) : null;
  const kinds = el("section", { class: "media-section", "aria-labelledby": "kinds-h" },
    el("h2", { id: "kinds-h", text: "Your library" }),
    el("ul", { class: "lib-kinds" }, ...data.tabs.map((t) => el("li", {},
      el("a", { href: `/${KIND_PAGE[t.tab]}` }, el("span", { text: t.label }),
        el("strong", { text: t.count === null ? "Reading…" : nCount(t.count, KIND_NAME[t.tab]) }))))));
  box.replaceChildren(...[recent, kinds].filter(Boolean));
  box.hidden = false;
  // Kinds still being read fill in a few seconds later.
  if (data.tabs.some((t) => t.count === null) && !$("#q").value.trim()) setTimeout(() => drawStart().catch(() => {}), 4000);
}

async function searchLibrary(q) {
  libAsked = q;
  const box = $("#lib-found");
  if (q.length < 2) { box.hidden = true; return; }
  const data = await api(`/api/library/search?q=${encodeURIComponent(q)}`);
  if (libAsked !== q || legacyMode) return;
  const total = data.library.reduce((n, g) => n + g.count, 0);
  box.replaceChildren(el("h2", { id: "found-h", text: total ? `In your library, ${total.toLocaleString("en-GB")}` : "In your library" }),
    ...(total ? data.library.map((g) => el("section", { class: "lib-search-group", "aria-label": g.label },
      el("h3", {}, g.label, " ", el("span", { class: "muted", text: `(${g.count.toLocaleString("en-GB")})` })),
      el("ul", { class: "rows" }, ...g.items.map((c) => el("li", { class: "row row--opens lib-row" },
        smallCover(c.poster, c.title),
        el("div", {}, el("h4", { class: "row__title" }, el("a", { href: `/${KIND_ITEM[g.tab]}?id=${c.id}`, text: c.title })),
          el("div", { class: "row__meta", text: [c.meta, c.count].filter(Boolean).join(" · ") })),
        el("div", { class: "row__side" }, c.status ? chip(c.status, c.tone) : null)))),
      g.count > g.items.length ? el("a", { href: `/${KIND_PAGE[g.tab]}?q=${encodeURIComponent(q)}`, text: `See all ${g.count.toLocaleString("en-GB")} in ${g.label}` }) : null))
      : [el("p", { class: "muted", text: `Nothing in your library matches "${q}".` })]));
  box.hidden = false;
  $("#lib-start").hidden = true;
  return total;
}

function addPanel(r, button) {
  const radio = r.kind === "radio";
  const ids = { p: "add-profile", f: "add-folder", s: "add-search", e: "add-error", fe: "add-ebook", fa: "add-audiobook", fo: "add-follow" };
  const profile = el("select", { class: "select", id: ids.p }, el("option", { text: "Loading…" }));
  const folder = el("select", { class: "select", id: ids.f }, el("option", { text: "Loading…" }));
  const search = el("input", { type: "checkbox", id: ids.s, checked: true });
  const ebook = el("input", { type: "checkbox", id: ids.fe, checked: true });
  const audio = el("input", { type: "checkbox", id: ids.fa, checked: true });
  const follow = el("select", { class: "select", id: ids.fo }, el("option", { value: "all", text: "Every episode, old and new" }),
    el("option", { value: "from_now_on", text: "New episodes only" }));
  const error = el("p", { class: "field-error", id: ids.e, role: "alert" });
  const verb = radio ? "Follow" : "Add";
  const submit = el("button", { type: "submit", form: "add-form", class: "btn btn--primary", disabled: !radio }, icon(radio ? "radio" : "plus"), radio ? "Follow this show" : "Add to Reelix");
  const fields = radio
    ? [el("div", { class: "field" }, el("label", { for: ids.fo, text: "Get" }), follow)]
    : [el("div", { class: "field" }, el("label", { for: ids.p, text: "Quality" }), profile),
      el("div", { class: "field" }, el("label", { for: ids.f, text: "Folder" }), folder),
      r.kind === "books" ? el("fieldset", {}, el("legend", { text: "Get it as" }),
        el("label", { class: "check", for: ids.fe }, ebook, el("span", { class: "check__text", text: "Ebook" })),
        el("label", { class: "check", for: ids.fa }, audio, el("span", { class: "check__text", text: "Audiobook" }))) : null,
      el("label", { class: "check", for: ids.s }, search, el("span", { class: "check__text", text: "Start looking for it now" }))];
  const form = el("form", { id: "add-form", class: "media-panel-section", novalidate: true }, ...fields.filter(Boolean), error);
  const panel = sidePanel({
    title: `${verb} ${r.title}`, opener: button,
    body: [el("div", { class: "side-panel__lead" }, smallCover(r.image, r.title, "cover"),
      el("div", { class: "media-panel-lead__text" }, el("h3", { text: r.year ? `${r.title} (${r.year})` : r.title }),
        r.detail ? el("span", { class: "small muted", text: r.detail }) : null)),
    r.overview ? el("p", { text: r.overview }) : null, form].filter(Boolean),
    foot: [submit, el("button", { type: "button", class: "btn btn--quiet", "data-closes": true, text: "Cancel" })],
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    submit.disabled = true;
    error.textContent = "";
    const options = radio ? { follow: follow.value } : {
      profile_id: Number(profile.value) || null, folder_id: Number(folder.value) || null, search: search.checked,
      formats: [ebook.checked ? "ebook" : "", audio.checked ? "audiobook" : ""].filter(Boolean),
    };
    if (r.kind === "books" && !options.formats.length) { error.textContent = "Choose ebook, audiobook or both"; submit.disabled = false; return; }
    try {
      const done = await api("/api/library/add", { method: "POST", body: { kind: r.kind, key: r.key, options } });
      panel.close();
      const added = chip(radio ? "Following" : "Added", "success");
      button.replaceWith(added);
      toast(radio ? `Following ${done.title}. Its episodes appear in Radio within a few minutes`
        : `Added ${done.title} to Reelix. It appears in ${done.tab === "tv" ? "TV" : done.tab[0].toUpperCase() + done.tab.slice(1)} within a few minutes`);
      added.closest("li")?.querySelector("h4")?.setAttribute("tabindex", "-1");
      added.closest("li")?.querySelector("h4")?.focus();
    } catch (e) {
      error.textContent = e.message;
      submit.disabled = false;
    }
  });
  if (!radio) {
    api(`/api/library/add-options?kind=${r.kind}`).then((o) => {
      profile.replaceChildren(...o.profiles.map((p) => el("option", { value: p.id, text: p.name })));
      folder.replaceChildren(...o.folders.map((f) => el("option", { value: f.id, text: f.free ? `${f.path} (${formatBytes(f.free)} free)` : f.path })));
      if (!o.folders.length) { error.textContent = "Reelix has no folder for this kind yet. Add one in Settings, Reelix."; return; }
      submit.disabled = false;
    }).catch((e) => { error.textContent = e.message; });
  }
}

const LOOK_KINDS = [["films", "Films"], ["tv", "TV"], ["books", "Books"], ["music", "Music"], ["radio", "Radio"]];

function lookupRow(kind, r) {
  const action = el("button", { type: "button", class: "btn" }, icon(kind === "radio" ? "radio" : "plus"), kind === "radio" ? "Follow" : "Add",
    el("span", { class: "visually-hidden", text: ` ${r.title}` }));
  action.addEventListener("click", () => addPanel(r, action));
  return el("li", { class: "row lib-row" }, smallCover(r.image, r.title),
    el("div", {}, el("h4", { class: "row__title", text: r.year ? `${r.title} (${r.year})` : r.title }),
      el("div", { class: "row__meta", text: r.detail || "" }),
      r.overview ? el("p", { class: "small muted clamp-2 result-overview", text: r.overview }) : null),
    el("div", { class: "row__side" }, action));
}

// Each kind is asked for on its own and shown when it arrives, in a fixed order, so nothing jumps about.
async function lookupReelix(q) {
  lookAsked = q;
  const box = $("#lookup");
  if (q.length < 3) { box.hidden = true; return; }
  box.hidden = false;
  box.setAttribute("aria-busy", "true");
  const heading = el("h2", { text: "Not in your library" });
  const status = el("p", { class: "muted", text: `Looking for "${q}"…` });
  const slots = LOOK_KINDS.map(([kind]) => el("div", { class: "lib-search-group", "data-kind": kind }));
  box.replaceChildren(heading, status, ...slots);
  let found = 0;
  await Promise.all(LOOK_KINDS.map(async ([kind, label], n) => {
    try {
      const data = await api(`/api/library/lookup?q=${encodeURIComponent(q)}&kind=${kind}`);
      if (lookAsked !== q || legacyMode) return;
      const items = data.groups[0]?.items || [];
      found += items.length;
      slots[n].replaceChildren(...data.errors.map((err) => el("p", { class: "small muted" }, icon("info", 16), " ", err.message)),
        ...(items.length ? [el("h3", { text: label }), el("ul", { class: "rows" }, ...items.map((r) => lookupRow(kind, r)))] : []));
    } catch (e) {
      if (lookAsked === q) slots[n].replaceChildren(el("p", { class: "small muted" }, icon("info", 16), " ", `${label}: ${e.message}`));
    }
  }));
  if (lookAsked !== q) return;
  heading.textContent = found ? `Not in your library, ${found}` : "Not in your library";
  status.textContent = found ? "" : `Reelix found nothing else for "${q}". Check the spelling or try fewer words.`;
  status.hidden = !found ? false : true;
  box.setAttribute("aria-busy", "false");
  if (legacyMode) box.hidden = true;
  announce(`${found} found that are not in your library`);
}

function remember(q) {
  const url = new URL(location.href);
  if (q) url.searchParams.set("q", q); else url.searchParams.delete("q");
  history.replaceState(null, "", url);
}

function runBoth(q, now = false) {
  clearTimeout(libTyping);
  clearTimeout(lookTyping);
  remember(q);
  if (!q) {
    $("#lib-found").hidden = true;
    $("#lookup").hidden = true;
    $("#lib-start").hidden = false;
    $("#search-summary").textContent = "Your library first, then what Reelix can add.";
    return;
  }
  libTyping = setTimeout(() => searchLibrary(q).then((n) => {
    if (n !== undefined) { $("#search-summary").textContent = `Results for "${q}"`; if (now) announce(`${n} in your library`); }
  }).catch(() => {}), now ? 0 : 200);
  lookTyping = setTimeout(() => lookupReelix(q), now ? 0 : 900);
}

startPage().then(async () => {
  const q = new URLSearchParams(location.search).get("q") || "";
  const submit = (e) => { if (!legacyMode) { e.preventDefault(); e.stopImmediatePropagation(); runBoth($("#q").value.trim(), true); } };
  const typed = () => { if (!legacyMode) runBoth($("#q").value.trim()); };
  $("#search-form").addEventListener("submit", submit);
  $("#q").addEventListener("input", typed);
  if (q) { $("#q").value = q; runBoth(q, true); } else $("#q").focus();
  try {
    await drawStart();
    if ($("#q").value.trim()) $("#lib-start").hidden = true;
  } catch (e) {
    if (e.status === 409) { // no Reelix: search the apps as before
      legacyMode = true;
      $("#search-form").removeEventListener("submit", submit);
      $("#lib-found").hidden = true;
      $("#lookup").hidden = true;
      window.legacySearchStart?.();
      return;
    }
    $("#lib-start").replaceChildren(el("p", { class: "field-error", text: e.message }));
    $("#lib-start").hidden = false;
  }
});
