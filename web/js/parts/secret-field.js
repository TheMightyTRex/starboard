/* secret-field: a part of the shared components. Load it after components.js and parts/error-summary.js, on the pages that use it.
 * Made by tools/parts.py from components.js in github.com/TheMightyTRex/design-system: change it there, not here. */
(() => {
  const S = window.SharedComponents;
  const { focusable, announcer, toast, copyText, sprite, escapeHtml, num, fold, andList, say, ownStatus } = S.kit;
  const { showErrors, clearErrors, setFieldError } = S;

  /* Secret field: .secret-field[data-secret] with the input (type="password", readonly), and buttons with
     data-secret-show, data-secret-copy and data-secret-replace. data-name names it ("API key"). Show and Hide say the
     new state politely; Copy confirms in a toast without the value; Replace empties the box to enter a new one, with
     Save and Cancel (Enter and Escape), and fires secret-change with { value } for the app to save. The value is
     never written to an attribute, a message, the page title or the console. Set it with input.value, not in the
     markup, so it is not in the page's source. */
  function setupSecrets(root = document) {
    root.querySelectorAll(".secret-field[data-secret]").forEach((box) => {
      if (box.dataset.ready) return;
      box.dataset.ready = "1";
      const input = box.querySelector("input");
      const name = box.dataset.name || "secret";
      const show = box.querySelector("[data-secret-show]");
      const copy = box.querySelector("[data-secret-copy]");
      const replace = box.querySelector("[data-secret-replace]");
      let kept = "";
      let cancel = null;
      const label = (button, words, icon) => {
        // Built from nodes: the name comes from data-name, so it never goes into HTML (CodeQL, 20 November 2026).
        const hidden = Object.assign(document.createElement("span"), { className: "visually-hidden", textContent: ` ${name}` });
        button.innerHTML = sprite(icon);
        button.append(words, hidden);
      };
      const setShown = (shown, tell = true) => {
        input.type = shown ? "text" : "password";
        show?.setAttribute("aria-pressed", String(shown));
        if (show) label(show, shown ? "Hide" : "Show", shown ? "eye-off" : "eye");
        if (tell) say(`${name} ${shown ? "shown" : "hidden"}`);
      };
      const editing = (on) => {
        input.readOnly = !on;
        if (copy) copy.hidden = on;
        if (on) {
          label(replace, "Save", "check");
          replace.classList.add("btn--primary");
          cancel = document.createElement("button");
          cancel.type = "button";
          cancel.className = "btn btn--quiet";
          cancel.textContent = "Cancel";
          cancel.addEventListener("click", () => stop(false));
          replace.after(cancel);
        } else {
          label(replace, "Replace", "pencil");
          replace.classList.remove("btn--primary");
          cancel?.remove();
          cancel = null;
        }
      };
      const stop = (save) => {
        if (save && !input.value.trim()) {
          setFieldError(input, `Enter the new ${name}`);
          input.focus();
          return;
        }
        setFieldError(input, "");
        if (save) {
          const ok = box.dispatchEvent(new CustomEvent("secret-change", { cancelable: true, detail: { value: input.value } }));
          if (ok) say(`${name} replaced`);
        } else {
          input.value = kept;
          say(`${name} not changed`);
        }
        kept = "";
        editing(false);
        setShown(false, false);
        replace.focus();
      };
      if (show) setShown(false, false);
      show?.addEventListener("click", () => setShown(input.type === "password"));
      copy?.addEventListener("click", async () => {
        if (await copyText(input.value)) toast(`${name} copied`);
        else toast(`Your browser did not allow copying`, { tone: "warning", detail: `Select Show, then select the ${name} and copy it.` });
      });
      replace?.addEventListener("click", () => {
        if (!input.readOnly) return stop(true);
        kept = input.value;
        input.value = "";
        editing(true);
        input.focus();
        say(`Enter the new ${name}, then select Save`);
      });
      input.addEventListener("keydown", (event) => {
        if (input.readOnly) return;
        if (event.key === "Enter") {
          event.preventDefault();
          stop(true);
        } else if (event.key === "Escape") {
          event.preventDefault();
          stop(false);
        }
      });
    });
  }

  Object.assign(S, { setupSecrets });
  S.addSetup(setupSecrets);
})();
