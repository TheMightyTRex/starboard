// The help centre's search and theme button (tools/build_help.py). Search runs in the browser over
// search-index.json: every word typed must appear; matches in the title count most, then headings, then text.
(function () {
  "use strict";
  var root = (function () {
    var link = document.querySelector('link[href$="assets/css/help.css"]');
    return link ? link.getAttribute("href").replace("assets/css/help.css", "") : "";
  })();

  var html = document.documentElement;
  function say(text) {
    var a = document.getElementById("help-announcer");
    if (a) { a.textContent = ""; setTimeout(function () { a.textContent = text; }, 50); }
  }

  // Display and accessibility: the app's own choices and classes, kept in this browser (localStorage).
  var DEFAULTS = { theme: "system", text: "100", motion: "device", contrast: false, underline: false, spacing: false };
  function readPrefs() {
    try { return Object.assign({}, DEFAULTS, JSON.parse(localStorage.getItem("help-display") || "{}")); } catch (e) { return Object.assign({}, DEFAULTS); }
  }
  function applyPrefs(p) {
    if (p.theme === "system") html.removeAttribute("data-theme"); else html.dataset.theme = p.theme;
    html.classList.remove("pref-text-125", "pref-text-150", "pref-text-175");
    if (p.text !== "100") html.classList.add("pref-text-" + p.text);
    html.classList.toggle("pref-contrast", !!p.contrast);
    html.classList.toggle("pref-motion", p.motion === "on");
    html.classList.toggle("pref-motion-off", p.motion === "off");
    html.classList.toggle("pref-underline", !!p.underline);
    html.classList.toggle("pref-spacing", !!p.spacing);
  }
  var form = document.getElementById("help-display-form");
  if (form) {
    var fill = function () {
      var p = readPrefs();
      form.theme.value = p.theme; form.text.value = p.text; form.motion.value = p.motion;
      form.contrast.checked = p.contrast; form.underline.checked = p.underline; form.spacing.checked = p.spacing;
    };
    fill();
    form.addEventListener("change", function () {
      var p = { theme: form.theme.value, text: form.text.value, motion: form.motion.value,
                contrast: form.contrast.checked, underline: form.underline.checked, spacing: form.spacing.checked };
      try { localStorage.setItem("help-display", JSON.stringify(p)); } catch (e) { /* private window: this page only */ }
      applyPrefs(p);
    });
    form.addEventListener("submit", function (e) { e.preventDefault(); });
    document.getElementById("help-display-reset").addEventListener("click", function () {
      try { localStorage.removeItem("help-display"); } catch (e) { /* nothing kept */ }
      applyPrefs(DEFAULTS); fill(); say("Display settings reset");
    });
  }

  // The left menu: each group opens and closes with its button; the whole menu hides and comes back.
  document.querySelectorAll(".help-nav__heading button").forEach(function (b) {
    b.addEventListener("click", function () {
      var open = b.getAttribute("aria-expanded") !== "true";
      b.setAttribute("aria-expanded", String(open));
      document.getElementById(b.getAttribute("aria-controls")).hidden = !open;
    });
  });
  // The page you are on is in view in the menu when a page opens (only the menu scrolls, not the page).
  var navBox = document.getElementById("help-nav"), here = navBox && navBox.querySelector("[aria-current=page]");
  if (here && navBox.scrollHeight > navBox.clientHeight) {
    navBox.scrollTop = here.offsetTop - navBox.offsetTop - navBox.clientHeight / 3;
  }
  var hide = document.querySelector(".help-nav__hide"), show = document.querySelector(".help-nav__show");
  function setHidden(hidden, focus) {
    html.classList.toggle("help-nav-hidden", hidden);
    if (hide) hide.setAttribute("aria-expanded", String(!hidden));
    if (show) { show.hidden = !hidden; show.setAttribute("aria-expanded", String(!hidden)); }
    try { localStorage.setItem("help-nav", hidden ? "hidden" : "shown"); } catch (e) { /* this page only */ }
    if (focus) (hidden ? show : hide).focus();
  }
  if (hide && show) {
    setHidden(html.classList.contains("help-nav-hidden"), false);
    hide.addEventListener("click", function () { setHidden(true, true); say("Menu hidden"); });
    show.addEventListener("click", function () { setHidden(false, true); say("Menu shown"); });
  }
  // On a phone the menu opens over the page from the Menu button, and Escape closes it.
  var menuBtn = document.querySelector(".help-menu-btn"), nav = document.getElementById("help-nav");
  if (menuBtn && nav) {
    var setOpen = function (open) {
      var header = document.querySelector(".site-header");
      if (open && header) nav.style.top = header.getBoundingClientRect().bottom + "px"; // the header wraps on a phone
      nav.classList.toggle("is-open", open);
      menuBtn.setAttribute("aria-expanded", String(open));
      if (open) { var cur = nav.querySelector("[aria-current=page]") || nav.querySelector("button"); if (cur) cur.focus(); }
    };
    menuBtn.addEventListener("click", function () { setOpen(!nav.classList.contains("is-open")); });
    nav.addEventListener("keydown", function (e) { if (e.key === "Escape" && nav.classList.contains("is-open")) { setOpen(false); menuBtn.focus(); } });
  }

  // On this page: the section being read is marked as you go down the article.
  var toc = document.querySelector(".help-toc");
  if (toc && "IntersectionObserver" in window) {
    var links = {};
    toc.querySelectorAll("a").forEach(function (a) { links[a.getAttribute("href").slice(1)] = a; });
    var heads = Object.keys(links).map(function (id) { return document.getElementById(id); }).filter(Boolean);
    var mark = function (id) {
      Object.keys(links).forEach(function (k) {
        if (k === id) links[k].setAttribute("aria-current", "location"); else links[k].removeAttribute("aria-current");
      });
    };
    var seen = {};
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { seen[e.target.id] = e.isIntersecting; });
      // The last heading above the top third of the window is the section being read.
      var current = heads[0].id;
      for (var i = 0; i < heads.length; i++) { if (heads[i].getBoundingClientRect().top < innerHeight / 3) current = heads[i].id; }
      mark(current);
    }, { rootMargin: "0px 0px -66% 0px" });
    heads.forEach(function (h) { io.observe(h); });
    window.addEventListener("scroll", function () {
      var current = heads[0].id;
      for (var i = 0; i < heads.length; i++) { if (heads[i].getBoundingClientRect().top < innerHeight / 3) current = heads[i].id; }
      mark(current);
    }, { passive: true });
    mark(heads[0].id);
  }

  var list = document.getElementById("help-results");
  if (!list) return;
  var count = document.getElementById("help-results-count");
  var input = document.getElementById("help-q");
  var docs = null;

  function words(q) {
    return q.toLowerCase().replace(/[^\w\s'-]/g, " ").split(/\s+/).filter(function (w) { return w.length > 1; });
  }
  function escapeHtml(s) {
    return s.replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; });
  }
  function snippet(text, terms) {
    var low = text.toLowerCase(), at = -1;
    for (var i = 0; i < terms.length && at < 0; i++) at = low.indexOf(terms[i]);
    if (at < 0) return "";
    var start = Math.max(0, at - 80), part = text.slice(start, start + 220);
    var out = escapeHtml((start ? "…" : "") + part + (start + 220 < text.length ? "…" : ""));
    terms.forEach(function (t) {
      out = out.replace(new RegExp("(" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi"), "<mark>$1</mark>");
    });
    return out;
  }
  function score(d, terms) {
    var title = d.title.toLowerCase(), heads = d.headings.join(" ").toLowerCase(), text = (d.summary + " " + d.text).toLowerCase();
    var total = 0;
    for (var i = 0; i < terms.length; i++) {
      var t = terms[i], s = 0;
      if (title.indexOf(t) >= 0) s += 10;
      if (heads.indexOf(t) >= 0) s += 4;
      var n = text.split(t).length - 1;
      if (n) s += Math.min(n, 5);
      if (!s) return 0; // every word must appear
      total += s;
    }
    return total;
  }
  function run() {
    var q = input.value.trim(), terms = words(q);
    list.replaceChildren();
    if (!terms.length) { count.textContent = 'Type what you want to do, such as "add a drive" or "forgotten password".'; return; }
    var found = docs.map(function (d) { return { d: d, s: score(d, terms) }; })
      .filter(function (r) { return r.s > 0; }).sort(function (a, b) { return b.s - a.s; }).slice(0, 30);
    count.textContent = found.length
      ? found.length + (found.length === 1 ? " article" : " articles") + " for " + q
      : "No articles for " + q + ". Try fewer words, or other words for the same thing.";
    found.forEach(function (r) {
      var li = document.createElement("li");
      var meta = [r.d.section, r.d.kind].filter(Boolean).join(" · ");
      li.innerHTML = '<a href="' + root + r.d.url + '">' + escapeHtml(r.d.title) + "</a>" +
        (meta ? '<p class="help-meta">' + escapeHtml(meta) + "</p>" : "") +
        "<p>" + (snippet(r.d.text, terms) || escapeHtml(r.d.summary)) + "</p>";
      list.append(li);
    });
    document.title = (q ? q + " · " : "") + "Search · Starboard help centre";
  }

  var params = new URLSearchParams(location.search);
  input.value = params.get("q") || "";
  fetch(root + "search-index.json").then(function (r) { return r.json(); }).then(function (data) {
    docs = data;
    run();
    var typing;
    input.addEventListener("input", function () {
      clearTimeout(typing);
      typing = setTimeout(function () {
        var u = new URL(location.href);
        u.searchParams.set("q", input.value);
        history.replaceState(null, "", u);
        run();
      }, 250);
    });
  }).catch(function () { count.textContent = "Search could not load. Every article is listed on the help centre home."; });
})();
