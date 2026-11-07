// The help centre's search and theme button (tools/build_help.py). Search runs in the browser over
// search-index.json: every word typed must appear; matches in the title count most, then headings, then text.
(function () {
  "use strict";
  var root = (function () {
    var link = document.querySelector('link[href$="assets/css/help.css"]');
    return link ? link.getAttribute("href").replace("assets/css/help.css", "") : "";
  })();

  // Theme: follows the computer unless chosen here; remembered in this browser only.
  var themeBtn = document.querySelector(".help-theme");
  if (themeBtn) {
    var dark = function () {
      var t = document.documentElement.dataset.theme;
      return t ? t === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
    };
    var show = function () { themeBtn.setAttribute("aria-pressed", String(dark())); };
    themeBtn.hidden = false;
    show();
    themeBtn.addEventListener("click", function () {
      var next = dark() ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem("help-theme", next); } catch (e) { /* private window */ }
      show();
    });
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
