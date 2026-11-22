/* error-summary: a part of the shared components. Load it after components.js, on the pages that use it.
 * Made by tools/parts.py from components.js in github.com/TheMightyTRex/design-system: change it there, not here. */
(() => {
  const S = window.SharedComponents;
  const { focusable, announcer, toast, copyText, sprite, escapeHtml, num, fold, andList, say, ownStatus } = S.kit;

  /* Error summary (after GOV.UK) and field errors. showErrors(form, [{ field: "id", message }]) writes each field's
     .field-error ("Error: " for screen readers), ties it with aria-describedby, sets aria-invalid, fills the form's
     .error-summary with a link to each field, shows it, moves focus to it and puts "Error: " in the page title.
     clearErrors(form) undoes it. A link in the summary moves focus to its field with the label in view. */
  function setFieldError(control, message) {
    const id = `${control.id}-error`;
    let error = document.getElementById(id);
    if (!message) {
      error?.remove();
      control.removeAttribute("aria-invalid");
      const left = (control.getAttribute("aria-describedby") || "").split(" ").filter((x) => x && x !== id);
      if (left.length) control.setAttribute("aria-describedby", left.join(" "));
      else control.removeAttribute("aria-describedby");
      return;
    }
    if (!error) {
      error = document.createElement("p");
      error.className = "field-error";
      error.id = id;
      const field = control.closest(".field, fieldset") || control.parentElement;
      let before = control;
      while (before.parentElement && before.parentElement !== field) before = before.parentElement;
      field.insertBefore(error, before);
    }
    error.innerHTML = `${sprite("circle-alert")}<span><span class="visually-hidden">Error: </span><span></span></span>`;
    error.querySelector("span > span:last-child").textContent = message;
    control.setAttribute("aria-invalid", "true");
    const ids = (control.getAttribute("aria-describedby") || "").split(" ").filter(Boolean);
    if (!ids.includes(id)) control.setAttribute("aria-describedby", [...ids, id].join(" "));
  }
  function clearErrors(form) {
    form.querySelectorAll('[aria-invalid="true"]').forEach((c) => c.id && setFieldError(c, ""));
    const summary = form.querySelector(".error-summary");
    if (summary) summary.hidden = true;
    document.title = document.title.replace(/^Error: /, "");
  }
  function showErrors(form, errors, options = {}) {
    clearErrors(form);
    if (!errors.length) return;
    let summary = form.querySelector(".error-summary");
    if (!summary) {
      summary = document.createElement("div");
      summary.className = "error-summary";
      summary.id = `${form.id || "form"}-errors`;
      form.prepend(summary);
    }
    summary.setAttribute("role", "alert");
    summary.tabIndex = -1;
    summary.setAttribute("aria-labelledby", `${summary.id}-h`);
    summary.innerHTML = `<h2 class="error-summary__title" id="${summary.id}-h">${sprite("circle-alert")}<span></span></h2><ul class="error-summary__list"></ul>`;
    summary.querySelector("h2 span").textContent = options.title || "There is a problem";
    const list = summary.querySelector("ul");
    for (const { field, message } of errors) {
      const control = document.getElementById(field);
      if (control) setFieldError(control, message);
      const li = document.createElement("li");
      li.append(Object.assign(document.createElement("a"), { href: `#${field}` }));
      li.firstChild.textContent = message;
      list.append(li);
    }
    summary.hidden = false;
    if (!document.title.startsWith("Error: ")) document.title = `Error: ${document.title}`;
    summary.focus();
    setupErrorSummaries(summary.parentElement);
  }
  function setupErrorSummaries(root = document) {
    if (document.documentElement.dataset.errorLinks) return;
    document.documentElement.dataset.errorLinks = "1";
    document.addEventListener("click", (event) => {
      const a = event.target.closest('.error-summary a[href^="#"]');
      if (!a) return;
      const control = document.getElementById(a.getAttribute("href").slice(1));
      if (!control) return;
      event.preventDefault();
      const legend = control.closest("fieldset")?.querySelector("legend");
      const label = (control.id && document.querySelector(`label[for="${control.id}"]`)) || legend || control;
      label.scrollIntoView({ block: "start" });
      control.focus({ preventScroll: true });
    });
  }

  Object.assign(S, { showErrors, clearErrors, setFieldError });
  S.addSetup(setupErrorSummaries);
})();
