# Starboard accessibility check, 12 November 2026

Owner: "do a full accessibility check. Keyboard and screen readers and other assistive tools."
Branch batch-1117b. Tool: `tools/a11y.sh` (new), against the made-up example server, 73 pages.

## What was checked

- **WCAG 2.2 AA by axe-core 4.14.0** on every page in Light, Dark and High contrast.
- **Structure:** one h1, headings in order, header, nav and main landmarks, the skip link as the first Tab stop,
  the tab title, a live region, the page language.
- **Screen readers:** every field has a label, every icon-only button has a name. Spot checks of the
  accessibility tree on the new backup page.
- **Keyboard:** up to 45 Tab stops per page, checking that focus is visible (a ring on the element, its card or
  its cover), that nothing traps focus, that focus never lands on something hidden, and that the sticky header
  never covers it.
- **Slide-outs:** focus moves into the Display slide-out, stays inside, and Escape closes it and returns focus
  to the button.
- **Other assistive set-ups:**
  - reflow at 320 px wide and at 175% text
  - forced colours (Windows High Contrast): focus rings stay
  - reduced motion: no transitions or animations
- **Size:** controls at least 24 by 24 px.

## First run: 48 findings, now fixed

- **Headings:** 11 pages went from h1 straight to h3. Their lists now have an h2 (hidden from sight, there for
  screen readers): Wanted, History, Downloads that need a look, Collections, Series, Authors, Networks, Stations.
- **Missing h1:** item pages opened without an item had no h1 and only a bare sentence. They now have an h1 and an
  empty state with Open <wall>.
- **Target size:** ticks and choices were 22 px, and the name buttons on app cards and rows were 20 px tall. They
  are now 24 by 24 and at least 24 px tall (design system ae38c4c).
- **Reflow:** a long folder path in a message pushed the backup page sideways at 320 px. Words now wrap in
  messages.
- **Test artefacts, fixed in the checker:**
  - The first scan ran before late content loaded; it now waits.
  - Focus rings drawn on a card or cover were counted as missing.
  - Two unnamed inputs looked like a trap.

## Second run: 4 findings, checked by hand

- **Target size, 2 pages (Dark and High contrast runs only):** Apps' primary button and Storage's "System disk"
  are 28 px or more tall, with no other target within 24 px. axe flags them only after a slide-out has opened over
  the page, so this is a test artefact.

## Not covered by the tool

- A real screen reader. Orca on this server or NVDA on Windows, reading the headings list and doing one task
  (make a full backup), is the last step in ACCESSIBILITY.md section 6. It needs a person listening.
- 400% browser zoom. Covered in part by 320 px reflow; not tested on its own.
