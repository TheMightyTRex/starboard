## What changed and why

<!-- One or two plain sentences. Link the task or issue. -->

## Done check

Run `/mnt/pool/build-cache/heavy-run-wt2 tools/done-check.sh` once on the final tip, then paste `done-check-out/summary.md` here. It must end with `DONE-CHECK PASSED`. Failures already on main are listed in `tools/done-check-baseline.json` and show as known on main.

```
(paste the summary)
```

## Per-screen acceptance

Per-screen acceptance checklist: the Accessibility check in the design system, https://themightytrex.github.io/design-system/guides/ai-checks.html (section 5)

- [ ] Every screen, slide-out, dialog and wizard step this change touches was looked at in light, dark and high contrast
- [ ] Keyboard only: every control reached in the visible order, focus returns to the opener, Escape closes

## Pictures

Help pictures and README screenshots wait for the release batch (HELP-AND-PICTURES-OWED.md). Tick if this change owes any:

- [ ] Pictures at release: this change adds or alters screens that need new or retaken help pictures (listed in the owed file)

## Self-review

- [ ] I read my own diff line by line
- [ ] Words follow the content rules (British English, no em dashes, no contractions, no "see" or "look")
- [ ] The release notes (CHANGELOG.md) say what changed, and Security if it fixes one
- [ ] I did not merge or release; both need the owner's OK
