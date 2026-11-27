/* log-view: a part of the shared components. Load it after components.js, on the pages that use it.
 * Made by tools/parts.py from components.js in github.com/TheMightyTRex/design-system: change it there, not here. */
(() => {
  const S = window.SharedComponents;
  const { focusable, announcer, toast, copyText, sprite, escapeHtml, num, fold, andList, say, ownStatus, notice } = S.kit;

  /* Log viewer: SharedComponents.logView(box, { lines, maxLines, show, fileName }) returns { add(lines), clear() }.
     Lines are strings ("12:01:03 ERROR Disk 3 did not answer") or { time, level, text }; levels are error, warning,
     info and debug. It keeps the newest maxLines (10,000) and draws only the newest `show` (1,000) that match, with
     Show earlier lines for more. New lines are drawn by themselves, never the whole list again. Following keeps the
     newest line in view; scrolling up pauses it. New errors are said politely, and only while following. */
  const LOG_LEVELS = { error: "Error", warning: "Warning", info: "Info", debug: "Debug" };
  const LOG_WORDS = /^(fatal|crit\w*|err\w*)$/i;
  function logLine(line) {
    if (typeof line !== "string") {
      const level = LOG_LEVELS[line.level] ? line.level : "info";
      const text = String(line.text ?? "");
      return { time: String(line.time ?? ""), level, text, low: text.toLowerCase() };
    }
    const m = /^(\S+(?: \d\d:\d\d:\d\d\S*)?)\s+\[?([A-Za-z]+)\]?:?\s+(.*)$/.exec(line);
    let level = "info";
    if (m) {
      const word = m[2];
      if (LOG_WORDS.test(word)) level = "error";
      else if (/^warn/i.test(word)) level = "warning";
      else if (/^(debug|trace)$/i.test(word)) level = "debug";
      else if (!/^(info|notice)$/i.test(word)) return { time: "", level, text: line, low: line.toLowerCase() };
      return { time: m[1], level, text: m[3], low: m[3].toLowerCase() };
    }
    return { time: "", level, text: line, low: line.toLowerCase() };
  }
  function logView(box, options = {}) {
    if (box.logView) return box.logView;
    const max = options.maxLines || Number(box.dataset.maxLines) || 10000;
    const step = options.show || Number(box.dataset.show) || 1000;
    const scroller = box.querySelector(".log-view__scroll");
    const list = box.querySelector(".log-view__lines");
    const search = box.querySelector("[data-log-search]");
    const levels = [...box.querySelectorAll("[data-log-level]")];
    const follow = box.querySelector("[data-log-follow]");
    const wrap = box.querySelector("[data-log-wrap]");
    const download = box.querySelector("[data-log-download]");
    const countLine = box.querySelector("[data-log-count]");
    [...levels, follow, wrap].forEach((b) => b && (b.dataset.ready = "1")); // not the filter chips' own toggling
    const all = [];
    let term = "";
    let limit = step;
    let hits = 0;
    let drawn = 0;
    let paused = false;
    let fresh = [];
    let errTimer = null;
    let earlier = null;
    const pressed = (b) => !b || b.getAttribute("aria-pressed") === "true";
    const following = () => follow && pressed(follow) && !paused;
    let on = new Set(levels.length ? levels.filter(pressed).map((b) => b.dataset.logLevel) : Object.keys(LOG_LEVELS));
    const termOk = (l) => !term || l.low.includes(term);
    const shows = (l) => on.has(l.level) && termOk(l);
    function draw(l) {
      const li = document.createElement("li");
      li.className = "log-view__line";
      li.dataset.level = l.level;
      const time = document.createElement("span");
      time.className = "log-view__time";
      time.textContent = l.time;
      const level = document.createElement("span");
      level.className = "log-view__level";
      level.textContent = LOG_LEVELS[l.level];
      const text = document.createElement("span");
      text.className = "log-view__text";
      if (term) {
        let i = 0;
        for (let at = l.low.indexOf(term); at !== -1; at = l.low.indexOf(term, i)) {
          text.append(l.text.slice(i, at));
          const mark = document.createElement("mark");
          mark.className = "log-view__match";
          mark.textContent = l.text.slice(at, at + term.length);
          text.append(mark);
          i = at + term.length;
        }
        text.append(l.text.slice(i));
      } else text.textContent = l.text;
      li.append(time, level, text);
      l.node = li;
      return li;
    }
    function counts() {
      const n = { error: 0, warning: 0, info: 0, debug: 0 };
      for (const l of all) if (termOk(l)) n[l.level]++;
      for (const b of levels) {
        const c = b.querySelector("[data-count]");
        if (c) c.textContent = num(n[b.dataset.logLevel] || 0);
      }
    }
    function sayCount() {
      if (!countLine) return;
      const filtered = term || on.size < Object.keys(LOG_LEVELS).length;
      let words = filtered ? `${num(hits)} of ${num(all.length)} lines match` : `${num(all.length)} lines`;
      if (drawn < hits) words += `. Showing the newest ${num(drawn)}`;
      if (follow && !following()) words += ". Following is paused";
      countLine.textContent = `${words}.`;
    }
    function earlierRow() {
      if (drawn >= hits) {
        earlier?.remove();
        earlier = null;
        return;
      }
      if (!earlier) {
        earlier = document.createElement("li");
        earlier.className = "log-view__earlier";
        earlier.innerHTML = '<button class="btn" type="button"></button>';
        earlier.firstChild.addEventListener("click", () => {
          const before = scroller.scrollHeight;
          limit += step;
          render();
          scroller.scrollTop += scroller.scrollHeight - before;
          (earlier?.firstChild || scroller).focus();
        });
      }
      earlier.firstChild.textContent = `Show ${num(Math.min(step, hits - drawn))} earlier lines`;
      list.prepend(earlier);
    }
    function toEnd() {
      if (following()) scroller.scrollTop = scroller.scrollHeight;
    }
    function render() {
      on = new Set(levels.length ? levels.filter(pressed).map((b) => b.dataset.logLevel) : Object.keys(LOG_LEVELS));
      const matched = all.filter(shows);
      hits = matched.length;
      const from = Math.max(0, hits - limit);
      drawn = hits - from;
      const frag = document.createDocumentFragment();
      for (let i = from; i < hits; i++) frag.append(draw(matched[i]));
      if (!hits) {
        const empty = document.createElement("li");
        empty.className = "log-view__empty";
        empty.textContent = all.length ? "No lines match. Change the search or the levels." : "No lines yet.";
        frag.append(empty);
      }
      earlier = null;
      list.replaceChildren(frag);
      earlierRow();
      counts();
      sayCount();
      toEnd();
    }
    function add(lines) {
      const frag = document.createDocumentFragment();
      for (const raw of [].concat(lines)) {
        const l = logLine(raw);
        all.push(l);
        if (shows(l)) {
          hits++;
          drawn++;
          frag.append(draw(l));
        }
        if (l.level === "error" && following()) fresh.push(l);
      }
      if (all.length > max) {
        for (const old of all.splice(0, all.length - max)) {
          if (shows(old)) hits--;
          if (old.node?.isConnected) {
            old.node.remove();
            drawn--;
          }
        }
      }
      list.querySelector(".log-view__empty")?.remove();
      list.append(frag);
      while (drawn > limit) {
        const first = earlier ? earlier.nextElementSibling : list.firstElementChild;
        if (!first) break;
        first.remove();
        drawn--;
      }
      earlierRow();
      counts();
      sayCount();
      toEnd();
      if (fresh.length && !errTimer) {
        errTimer = setTimeout(() => {
          const n = fresh.length;
          const newest = fresh[n - 1].text.slice(0, 120);
          say(n === 1 ? `New error: ${newest}` : `${n} new errors. The newest: ${newest}`);
          fresh = [];
          errTimer = null;
        }, 1500);
      }
    }
    function setFollow(value) {
      paused = !value;
      follow?.setAttribute("aria-pressed", String(value));
      sayCount();
      toEnd();
    }
    let typing = null;
    search?.addEventListener("input", () => {
      clearTimeout(typing);
      typing = setTimeout(() => {
        term = search.value.trim().toLowerCase();
        limit = step;
        render();
        say(term ? `${num(hits)} ${hits === 1 ? "line matches" : "lines match"}` : `${num(hits)} lines`);
      }, 200);
    });
    for (const b of levels)
      b.addEventListener("click", () => {
        b.setAttribute("aria-pressed", String(!pressed(b)));
        limit = step;
        render();
      });
    follow?.addEventListener("click", () => setFollow(!following()));
    wrap?.addEventListener("click", () => {
      const now = !pressed(wrap);
      wrap.setAttribute("aria-pressed", String(now));
      box.toggleAttribute("data-wrap", now);
      toEnd();
    });
    // Only a move up by the person pauses following; text growing as fonts load or the box narrows does not.
    let lastTop = 0;
    scroller.addEventListener("scroll", () => {
      const atEnd = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight < 24;
      if (following() && !atEnd && scroller.scrollTop < lastTop - 4) setFollow(false);
      lastTop = scroller.scrollTop;
    }, { passive: true });
    if (window.ResizeObserver) new ResizeObserver(toEnd).observe(list);
    download?.addEventListener("click", () => {
      const text = all.map((l) => [l.time, LOG_LEVELS[l.level].toUpperCase(), l.text].filter(Boolean).join(" ")).join("\n");
      const url = URL.createObjectURL(new Blob([text + "\n"], { type: "text/plain" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = options.fileName || box.dataset.file || "log.txt";
      document.body.append(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
    if (follow) paused = !pressed(follow);
    box.toggleAttribute("data-wrap", pressed(wrap) && Boolean(wrap));
    render();
    if (options.lines) add(options.lines);
    box.logView = {
      add,
      clear() {
        all.length = 0;
        limit = step;
        render();
      },
      get size() {
        return all.length;
      },
    };
    return box.logView;
  }
  function setupLogViews(root = document) {
    root.querySelectorAll(".log-view[data-log-view]").forEach((box) => logView(box));
  }

  Object.assign(S, { logView });
  S.addSetup(setupLogViews, true);
})();
