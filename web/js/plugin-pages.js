// Plug-in pages drawn from the shared wizard and its parts (plug-in API 1.26, 28 November 2026): the wizard, a sentence with
// selects, media cards, rows behind Show more settings, a preview and the desktop notice. Loaded by plugins.js only when a
// plug-in answers with one of them, with the design system's parts for it (css/parts and js/parts), so a page without them
// loads nothing more. Everything here is drawn from data Starboard has already cleaned (starboard/plugin_custom.py).
// Loaded after common.js (el, icon, announce) and plugins.js.
const PluginPages = (() => {
  const PARTS = ["error-summary", "wizard-steps", "wizard-preview", "option-media", "sentence", "more-rows", "desktop-notice"];
  const partLoads = new Map();
  const loadPart = (name) => {
    if (!partLoads.has(name)) {
      document.head.append(el("link", { rel: "stylesheet", href: `/css/parts/${name}.css` }));
      partLoads.set(name, name === "desktop-notice" ? Promise.resolve() : new Promise((ok, fail) => {
        document.head.append(el("script", { src: `/js/parts/${name}.js`, onload: ok, onerror: () => fail(new Error("Could not load the page. Reload it.")) }));
      }));
    }
    return partLoads.get(name);
  };
  // In order: the error summary first, as the wizard needs it.
  const ensure = async () => { for (const n of PARTS) await loadPart(n); };

  const previewPane = (title, level) => el("section", { class: "wizard-preview", "aria-label": title },
    el(`h${Math.min(6, level)}`, { class: "wizard-preview__title", text: title }), el("div", { class: "wizard-preview__frame" }),
    el("ol", { class: "wizard-preview__strip", "aria-label": "The parts, in order", hidden: true }),
    el("p", { class: "wizard-preview__caption", role: "status", "aria-live": "polite" }), el("p", { class: "wizard-preview__total" }));

  const desktopNotice = () => el("div", { class: "notice desktop-notice", role: "note" }, icon("info"),
    el("div", { class: "notice__body" }, el("p", { text: "This page is for a computer screen. It is not made for phones." })));

  // A preview, as the pane draws it: set from data, said politely after a change and never when it opens.
  const showPreview = (pane, p, said = false) => window.SharedComponents.setPreview(pane, p, said);

  // A picture or short preview for a media card goes through Starboard, which asks the plug-in with its own key.
  const mediaAddress = (ctx, step, id, kind) => `/api/plugins/${ctx.p.id}/custom/${ctx.s.key}/media?${new URLSearchParams({ ...(step ? { step } : {}), id, kind })}`;

  const mediaPicture = (ctx, step, opt) => {
    const m = opt.media;
    const src = m.thumb ? m.thumb.src : m.thumb_path ? mediaAddress(ctx, step, opt.id, "thumb") : "";
    return el("div", { class: "option-card__media" },
      src ? el("img", { src, alt: "", width: 160, height: 90, loading: "lazy", decoding: "async" }) : null,
      m.length ? el("span", { class: "option-card__length", text: m.length }) : null);
  };
  const previewButton = (ctx, step, opt) => opt.media.preview ? el("div", { class: "option-card__actions" },
    el("button", { type: "button", class: "btn btn--compact", "data-preview-src": mediaAddress(ctx, step, opt.id, "preview"), "data-title": opt.label },
      "Play preview", el("span", { class: "visually-hidden", text: ` of ${opt.label}` }))) : null;

  // One option of a step: an option card, or a media card inside one.
  const optionCard = (ctx, st, o, type, name) => {
    const tags = [o.current ? el("span", { class: "wizard__tag", "data-tag": "current", text: "Current" }) : null,
      o.recommended ? el("span", { class: "wizard__tag", "data-tag": "recommended", text: "Recommended" }) : null];
    const attrs = { type, name, value: o.id, "data-label": o.label, ...(o.current ? { "data-current": "" } : {}), ...(o.recommended ? { "data-recommended": "" } : {}),
      ...(o.preview ? { "data-preview": JSON.stringify(o.preview) } : {}) };
    const id = `${name}-${o.id.replace(/[^A-Za-z0-9]+/g, "-")}`;
    if (o.media) {
      const input = el("input", { ...attrs, id });
      input.checked = o.checked || (o.current && !st.hasChecked);
      return el("div", { class: "option-card option-card--media", "data-kind": o.media.kind }, mediaPicture(ctx, st.id, o), input,
        el("label", { for: id }, el("strong", {}, o.label, ...tags), o.hint ? el("small", { text: o.hint }) : null), previewButton(ctx, st.id, o));
    }
    const input = el("input", attrs);
    input.checked = o.checked || (o.current && !st.hasChecked);
    return el("label", { class: "option-card" }, input, el("strong", {}, o.label, ...tags), o.hint ? el("small", { text: o.hint }) : null);
  };

  const stepNode = (ctx, st, wid, level) => {
    st.hasChecked = st.options.some((o) => o.checked);
    const name = `${wid}-${st.id}`;
    const attrs = { class: "wizard__step", "data-step": st.id, "data-title": st.title, id: `${wid}-${st.id}-step`, ...(st.optional ? { "data-optional": "" } : {}),
      ...(st.required ? { "data-required": "", "data-error": st.error || `Choose an answer to ${st.title.toLowerCase()}` } : {}) };
    const q = el(`h${Math.min(6, level)}`, { class: "wizard__q", text: st.question });
    const hint = st.hint ? el("p", { class: "muted", text: st.hint }) : null;
    let body;
    if (st.kind === "text" || st.kind === "number") {
      const id = `${name}-field`;
      body = el("div", { class: "wizard__field" }, el("label", { for: id, text: st.label || st.title }),
        el("input", { class: "input", id, type: st.kind === "number" ? "number" : "text", value: st.value || "", "data-label": st.label || st.title, autocomplete: "off" }),
        st.unit ? el("span", { class: "hint", text: st.unit }) : null);
    } else if (st.kind === "select") {
      const id = `${name}-field`;
      const sel = el("select", { class: "select", id }, st.options.map((o) => el("option", { value: o.id, text: o.label, ...(o.recommended ? { "data-recommended": o.id } : {}) })));
      sel.value = (st.options.find((o) => o.checked) || st.options.find((o) => o.current) || st.options[0]).id;
      body = el("div", { class: "wizard__field" }, el("label", { for: id, text: st.label || st.title }), sel);
    } else {
      const type = st.kind === "multi" || st.kind === "media" ? "checkbox" : "radio";
      body = el("fieldset", { class: `option-cards${st.kind === "media" ? " option-cards--row" : ""}` }, el("legend", { class: "visually-hidden", text: st.title }),
        st.options.map((o) => optionCard(ctx, st, o, type, name)));
    }
    return el("section", attrs, q, hint, body);
  };

  const foot = (data) => el("div", { class: "wizard__foot" },
    el("button", { type: "button", class: "btn btn--primary", "data-wizard-act": "next", text: "Continue" }),
    el("button", { type: "button", class: "btn", "data-wizard-act": "back", hidden: true, text: "Back" }),
    el("button", { type: "button", class: "btn btn--quiet", "data-wizard-act": "skip", text: "Skip this step" }),
    data.steps.some((s) => s.options.some((o) => o.recommended)) ? el("button", { type: "button", class: "btn btn--quiet", "data-wizard-act": "recommended", text: "Use the recommended choices" }) : null,
    el("button", { type: "button", class: "btn btn--primary", "data-wizard-act": "finish", hidden: true, text: data.finish }));

  // The shared wizard (docs/WIZARD.md): steps, then Check your answers, then the action named on the button.
  const wizard = (ctx, data) => {
    const wid = `pw-${ctx.p.id}-${ctx.s.key}`;
    const level = ctx.level;
    const steps = el("ol", { class: "steps", "aria-label": "Steps" }, [...data.steps.map((s) => s.title), "Check your answers"].map((t) => el("li", {}, t, el("span", { class: "visually-hidden" }))));
    const box = el("div", { class: "wizard", "data-wizard": wid, "data-mode": data.mode, "data-finish": data.finish, ...(data.review ? { "data-review": data.review } : {}) },
      data.mode_label ? el("p", { class: "muted", text: data.mode_label }) : null,
      el("div", { class: "meter wizard-progress" }, el("div", { class: "meter__label" }, el("span", { class: "wizard__count" }), el("span", { class: "numeric" })),
        el("div", { class: "progress", role: "progressbar", "aria-label": `${data.title || "Set-up"} progress` }, el("span"))),
      steps, ...data.steps.map((s) => stepNode(ctx, s, wid, level)),
      el("section", { class: "wizard__step wizard__check", "data-step": "check", "data-title": "Check your answers" }, el(`h${Math.min(6, level)}`, { class: "wizard__q", text: "Check your answers" })),
      foot(data));
    const layout = el("div", { class: "wizard-layout", "data-preview-scope": "" }, el("div", { class: "wizard-main" }, box));
    if (data.preview) layout.append(previewPane(data.preview.title, level + 1));
    box.addEventListener("wizard-finish", async (e) => {
      const fin = box.querySelector("[data-wizard-act='finish']");
      fin.disabled = true;
      const answers = Object.fromEntries(Object.entries(e.detail.answers).map(([k, v]) => [k, data.steps.find((s) => s.id === k)?.kind === "multi" || data.steps.find((s) => s.id === k)?.kind === "media"
        ? v.map((x) => x.value) : (v[0]?.value ?? "")]));
      try {
        const out = await ctx.post({ action: "wizard", answers });
        const again = el("button", { type: "button", class: "btn", text: "Run it again" });
        again.addEventListener("click", () => ctx.reload());
        layout.replaceChildren(el("div", { class: "stack-4" }, el("h3", { id: `${wid}-done`, tabindex: "-1", text: data.finish === "Finish" ? "Done" : "Saved" }),
          notice("success", out.said || "Saved", ""), el("div", { class: "actions" }, again)));
        layout.querySelector(`#${wid}-done`).focus();
      } catch (err) { fin.disabled = false; ctx.problem(err.message, fin); }
    });
    return layout;
  };

  // A setting read as one sentence, with a select in each gap; a change is saved at once.
  const sentence = (ctx, data) => {
    const wid = `pw-${ctx.p.id}-${ctx.s.key}`;
    const text = el("p", { class: "sentence__text" }, data.parts.map((x) => {
      if (x.id === undefined) return x.text;
      const sel = el("select", { class: "select sentence__select", "aria-label": x.label, "data-key": `gap:${x.id}`, id: `${wid}-${x.id}` }, x.options.map(([v, words]) => el("option", { value: v, text: words })));
      sel.value = x.value;
      sel.addEventListener("change", () => ctx.run({ action: "choose", id: x.id, value: sel.value }, sel));  // saved at once, the screen drawn again with focus kept
      return sel;
    }));
    return el("div", { class: "sentence", role: "group", "aria-label": data.title || "Sentence" }, text,
      el("p", { class: "sentence__readback", role: "status", "aria-live": "polite" }, el("strong", { text: "In plain words:" }), " ", el("span", { "data-readback": "" })));
  };

  // Media cards for a list with layout "media": each item as a media card with a Use tick (the item's Activate).
  const mediaCards = (ctx, items, run) => el("div", { class: "option-cards option-cards--row" }, items.map((it) => {
    const id = `pw-${ctx.p.id}-${ctx.s.key}-${it.id.replace(/[^A-Za-z0-9]+/g, "-")}`;
    const m = it.media;
    const tick = it.actions.includes("toggle") ? el("input", { type: "checkbox", id, "data-label": it.title, "data-key": `${it.id}:toggle` }) : null;
    if (tick) { tick.checked = it.on; tick.addEventListener("change", () => run({ action: "toggle", id: it.id }, tick)); }
    return el("div", { class: "option-card option-card--media", "data-kind": m ? m.kind : "video" }, m ? mediaPicture(ctx, "", { ...it, media: m }) : el("div", { class: "option-card__media" }), tick || el("span"),
      el(tick ? "label" : "div", tick ? { for: id } : {}, el("strong", { text: it.title }), it.detail ? el("small", { text: it.detail }) : null), m && m.preview ? previewButton(ctx, "", { ...it, label: it.title, media: m }) : null);
  }));

  // Show more settings: a switch, and the rows marked "more" drawn after it.
  const moreSwitch = (ctx, data, rows) => {
    const box = el("div", { class: "more", "data-key": `${ctx.p.id}-${ctx.s.key}` });
    const id = `pw-${ctx.p.id}-${ctx.s.key}-more`;
    const input = el("input", { type: "checkbox", role: "switch", id, "data-more-switch": "" });
    box.append(el("div", { class: "more__switch" }, el("label", { class: "switch", for: id }, el("span", {}, data.more_switch.label, data.more_switch.hint ? el("span", { class: "hint", text: ` ${data.more_switch.hint}` }) : null), input)));
    rows.forEach((r) => { r.setAttribute("data-more", ""); box.append(r); });
    return box;
  };

  return { ensure, wizard, sentence, mediaCards, moreSwitch, previewPane, showPreview, desktopNotice, // Only the parts' own set-up, never the whole page's again: the rows Starboard drew have their own.
    settle: (root) => { const c = window.SharedComponents; for (const f of ["setupWizards", "setupPreviewPanes", "setupOptionMedia", "setupSentences", "setupMoreRows"]) c[f]?.(root); } };
})();
