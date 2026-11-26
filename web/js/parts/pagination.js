/* pagination: a part of the shared components. Load it after components.js, on the pages that use it.
 * Made by tools/parts.py from components.js in github.com/TheMightyTRex/design-system: change it there, not here. */
(() => {
  const S = window.SharedComponents;
  const { focusable, announcer, toast, copyText, sprite, escapeHtml, num, fold, andList, say, ownStatus, notice } = S.kit;

  /* Pagination: pagination(nav, { page, pageSize, total, noun, sizes, href, onPage, onSize, focus }) draws the
     links and "Showing 21 to 40 of 312". With href(page) each is a real link; with onPage(page) the page changes in
     place, says the new place politely and moves focus to `focus` (the table or its heading) or the current page. */
  function pagination(nav, o) {
    const sizes = o.sizes || [20, 50, 100];
    const last = Math.max(1, Math.ceil(o.total / o.pageSize));
    const page = Math.min(Math.max(1, o.page), last);
    const from = o.total ? (page - 1) * o.pageSize + 1 : 0;
    const to = Math.min(o.total, page * o.pageSize);
    const summary = `Showing ${num(from)} to ${num(to)} of ${num(o.total)}${o.noun ? ` ${escapeHtml(o.noun)}` : ""}`;
    const want = [...new Set([1, page - 1, page, page + 1, last])].filter((p) => p >= 1 && p <= last).sort((a, b) => a - b);
    const pages = [];
    want.forEach((p, i) => {
      if (i && p - want[i - 1] === 2) pages.push(p - 1);
      else if (i && p - want[i - 1] > 2) pages.push(0);
      pages.push(p);
    });
    const link = (p, inner, extra = "") =>
      `<a class="pagination__link" href="${escapeHtml(o.href ? o.href(p) : `#page-${p}`)}" data-page="${p}"${extra}>${inner}</a>`;
    const id = nav.id || (nav.id = `pages-${Math.random().toString(36).slice(2, 8)}`);
    let html = `<p class="pagination__summary">${summary}</p><ul class="pagination__pages">`;
    if (page > 1) html += `<li>${link(page - 1, `${sprite("chevron-left")}Previous<span class="visually-hidden"> page</span>`, ' rel="prev"')}</li>`;
    for (const p of pages)
      html += p
        ? `<li${p !== page && p !== 1 && p !== last ? ' class="pagination__near"' : ""}>${link(p, num(p), p === page ? ` aria-current="page" aria-label="Page ${p}, current page"` : ` aria-label="Page ${p}"`)}</li>`
        : '<li class="pagination__gap" aria-hidden="true">…</li>';
    if (page < last) html += `<li>${link(page + 1, `Next<span class="visually-hidden"> page</span>${sprite("chevron-right")}`, ' rel="next"')}</li>`;
    html += "</ul>";
    if (o.onSize)
      html += `<div class="pagination__size"><label for="${id}-size">Rows per page</label><select class="select" id="${id}-size">${sizes
        .map((s) => `<option${s === o.pageSize ? " selected" : ""}>${s}</option>`)
        .join("")}</select></div>`;
    nav.innerHTML = html;
    if (o.onPage)
      nav.querySelectorAll("[data-page]").forEach((a) =>
        a.addEventListener("click", (event) => {
          event.preventDefault();
          const next = Number(a.dataset.page);
          o.onPage(next);
          pagination(nav, { ...o, page: next });
          (o.focus || nav.querySelector('[aria-current="page"]'))?.focus();
          say(nav.querySelector(".pagination__summary").textContent);
        }),
      );
    nav.querySelector("select")?.addEventListener("change", (event) => {
      const size = Number(event.target.value);
      const first = Math.floor((from - 1) / size) + 1;
      o.onSize(size, first);
      pagination(nav, { ...o, pageSize: size, page: first });
      nav.querySelector("select").focus();
      say(nav.querySelector(".pagination__summary").textContent);
    });
    return { page, last, from, to, summary };
  }

  Object.assign(S, { pagination });
})();
