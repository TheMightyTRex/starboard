/* tag-input: a part of the shared components. Load it after components.js, on the pages that use it.
 * Made by tools/parts.py from components.js in github.com/TheMightyTRex/design-system: change it there, not here. */
(() => {
  const S = window.SharedComponents;
  const { focusable, announcer, toast, copyText, sprite, escapeHtml, num, fold, andList, say, ownStatus, notice } = S.kit;

  /* Tag input: .tag-input[data-tag-input] > ul.tag-input__list + input.tag-input__field, and a hidden input that
     holds the words joined with commas. Enter or a comma adds what is in the box (several at once when pasted with
     commas); leaving the box adds it too. Each tag has its own Remove button named with the word. Backspace in an
     empty box moves focus to the last Remove button. Adding and removing are said politely; after a removal, focus
     goes to the next Remove button, or back to the box. Fires tags-change with { values }. */
  function setupTagInputs(root = document) {
    root.querySelectorAll(".tag-input[data-tag-input]").forEach((box) => {
      if (box.dataset.ready) return;
      box.dataset.ready = "1";
      const field = box.querySelector(".tag-input__field");
      const list = box.querySelector(".tag-input__list");
      const hidden = box.querySelector('input[type="hidden"]');
      const values = () => [...list.children].map((li) => li.dataset.value);
      const changed = () => {
        if (hidden) hidden.value = values().join(",");
        box.dispatchEvent(new CustomEvent("tags-change", { detail: { values: values() } }));
      };
      const make = (value) => {
        const li = document.createElement("li");
        li.className = "tag-input__tag";
        li.dataset.value = value;
        li.innerHTML = `<span></span><button type="button">${sprite("x")}</button>`;
        li.firstChild.textContent = value;
        li.lastChild.setAttribute("aria-label", `Remove ${value}`);
        return li;
      };
      [...list.children].forEach((li) => {
        if (!li.querySelector("button")) li.replaceWith(make(li.dataset.value || li.textContent.trim()));
      });
      const add = (text) => {
        const added = [];
        const already = [];
        for (const part of text.split(",").map((p) => p.trim()).filter(Boolean)) {
          if (values().some((v) => v.toLowerCase() === part.toLowerCase())) already.push(part);
          else {
            list.append(make(part));
            added.push(part);
          }
        }
        if (added.length) changed();
        const words = [added.length && `${andList(added)} added`, already.length && `${andList(already)} ${already.length === 1 ? "is" : "are"} already in the list`];
        if (added.length || already.length) say(words.filter(Boolean).join(". "));
      };
      field.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === ",") {
          event.preventDefault();
          add(field.value);
          field.value = "";
        } else if (event.key === "Backspace" && !field.value && list.lastElementChild) {
          event.preventDefault();
          list.lastElementChild.querySelector("button").focus();
        }
      });
      field.addEventListener("input", () => {
        if (!field.value.includes(",")) return;
        const parts = field.value.split(",");
        field.value = parts.pop();
        add(parts.join(","));
      });
      field.addEventListener("blur", () => {
        if (!field.value.trim()) return;
        add(field.value);
        field.value = "";
      });
      list.addEventListener("click", (event) => {
        const button = event.target.closest("button");
        if (!button) return;
        const li = button.closest("li");
        const after = li.nextElementSibling || li.previousElementSibling;
        li.remove();
        changed();
        say(`${li.dataset.value} removed`);
        (after?.querySelector("button") || field).focus();
      });
      box.addEventListener("click", (event) => {
        if (event.target === box || event.target === list) field.focus();
      });
    });
  }

  Object.assign(S, { setupTagInputs });
  S.addSetup(setupTagInputs);
})();
