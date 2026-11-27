# Starboard: rules for AI agents

Never say a change is done, and never mark a pull request ready, until `tools/done-check.sh` passes on the final tip (run it through `/mnt/pool/build-cache/heavy-run-wt2`) and its summary (`done-check-out/summary.md`) is in the pull request.

- Work in your own git worktree under `/mnt/pool/build-cache`, never in `~/src/starboard`.
- Failures already on main are listed in `tools/done-check-baseline.json`. Remove an item when it is fixed; never add one to hide a failure your change caused.
- Words: British English, sentence case, no em dashes, no contractions, never "see" or "look" in text people read (the design system's `docs/CONTENT-DESIGN.md`).
- Help pictures and README screenshots wait for the release batch; do not retake them in a feature pull request.
- Releases, merges and anything on the live server need the owner's OK.
- Start from `~/Documents/Claude/README.md`.
