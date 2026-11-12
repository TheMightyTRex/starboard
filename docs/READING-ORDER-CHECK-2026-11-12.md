# Starboard: reading order, keyboard and screen readers, 12 November 2026

Owner: "look at how people would use the app and check and make sure screen readers follow best practice on the
sequencing and order of the app." Then: this is now part of the standard accessibility test (memory, and
ACCESSIBILITY.md section 6 in the design system).

## How it was checked

- **Reading order** (`ORDER=1 tools/a11y.sh`, new). On every page, at desktop and phone width, and in each of the
  four app-card designs:
  - what a screen reader reads, compared with what is seen
  - Tab order down each column
  - landmark order (skip link, header, main, footer)
  - the h1 first
- **The main tasks by keyboard alone** (`TASKS=1 tools/a11y.sh`, new, 23 checks): sign in, Skip to main content,
  search, open a film, change a setting, edit an app in a slide-out, make and revoke a key, Show more. After each
  step it records where focus is and what is said.
- **Code read for focus after actions and for live regions.**

## Found and fixed

1. **Focus lost after a redraw.** About 430 places redraw part of a page. When the button that had focus went, a
   screen reader jumped back to the top of the page. One focus keeper for the whole app now moves focus to the
   same control drawn again, or the same row, or the same name in the same section, or else the section's
   heading. Slide-outs and confirm boxes do the same when their opener has gone, such as after Revoke.
2. **Whole lists were live regions**, so every row was read aloud on each change: Wanted, History, issues, search
   results, logs, On demand, dashboard cards (every refresh) and several settings sections. They are quiet now.
   Short summaries are said instead, such as "23 films missing", "12 more shown" or "Saved".
3. **Still to set up opened by itself** after signing in and took focus. Owner: it opens only from Go through them.
   A walk-through the person started carries on across pages. Help updated.
4. **The step page inside Still to set up took focus** as it loaded, so Escape could not close the slide-out. The
   step's heading now keeps focus until the person acts.
5. **Make a key and Add a folder did not start in their first field.** Typing went nowhere. They now do.
6. **Confirm boxes started on their X button.** They now start on their first field, or on Cancel for a danger
   choice, so pressing Enter never does the harm by mistake.
7. **The update notice came before the page's h1.** It now comes after the heading, and closing it gives focus to
   the h1.
8. **Show more on Wanted and History left focus on the button**, which had moved to the end. Focus now goes to the
   first new row, and the number added is said.

## Checked and right as it was

- Release notes and TV seasons: closed fold-outs read only their summaries, in order.
- Cards in a grid read left to right, then the next row, as shown.
- The skip link is the first Tab stop and goes into the page. Slide-outs take focus, keep it and give it back on
  Escape.

## Still for a person

- Listening with Orca or NVDA: the headings list and one task, such as making a full backup.
