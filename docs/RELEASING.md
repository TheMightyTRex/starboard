# Releasing Starboard

The same pattern as Storyarr: one list of releases in the code feeds the release notes in the app, the upgrade
guide and the notes on GitHub, so they always say the same thing.

## Each release

1. **Version.** Put the new number in `VERSION` (for example `0.5.0`).
2. **Release entry.** Add the release to the end of `RELEASES` in `starboard/releases.py`:
   - `added`, `changed` and `fixed`: one short title and one sentence each, in the content rules (British
     English, sentence case, no em dashes, no contractions).
   - `review`: the upgrade guide steps worth choosing after this upgrade, from `apps`, `keys`, `jellyfin`,
     `hours`, `alerts`, `preset` and `names`. Leave it empty when nothing needs choosing: the upgrade then
     finishes on its own and the notes wait under the version in the footer.
   - `settings`: what changes in people's settings, and the way back (`./update.sh --to v<previous>`).
3. **Notes.** Run `python3 tools/release_notes.py`. It writes `docs/releases/vX.Y.Z.md`.
4. **Changelog.** Add the same release to the top of `CHANGELOG.md`, with more detail if it helps.
5. **Checks.** Run the tests (`python3 -m unittest discover -s tests`), the browser journeys
   (`tools/journeys.sh`), the help centre check (`python3 tools/check-help.py`) and `tools/check-private.sh`.
   When the installer, `update.sh` or the image changed, also run `tools/vm/vm.sh test` on at least one PC system
   and `arm64`. Record the results and any change in system use in `docs/TESTING.md`
   ([Testing and system use](TESTING.md)).
6. **Screenshots, at every push.** Run `tools/screenshots.sh` and look at every picture in `docs/screenshots`:
   the screens must match what changed, and only example data may appear (no real names, addresses, titles or
   folders). A screen that is new or changed a lot gets its own shot: add it to the list in
   `tools/screenshots/shoot.mjs` and to the Screenshots table in the README.
7. **Commit and tag** on `main`: `git tag vX.Y.Z`.
8. **Publish** (David runs this himself, after his OK to push):

   ```bash
   gh release create vX.Y.Z --notes-file docs/releases/vX.Y.Z.md
   ```

   `./update.sh` on a server then fetches the new tag, rebuilds and restarts, and goes back if it does not start.

## What people see

- **Footer:** the version opens the release notes. When GitHub has a newer release, "Upgrade available" sits
  beside it.
- **After an upgrade with something to choose:** a notice on each page, with "Open the upgrade guide". The guide
  shows what is new in every release since the last one they finished, then only those questions, then Finish.
  "Remind me later" hides the notice until the browser is next opened; "Keep the defaults and finish" ends it.
- **After an upgrade with nothing to choose:** nothing interrupts. The upgrade is recorded quietly.
- **A fresh install** records its version at set-up, so it never sees an upgrade guide for releases it did not
  have. It gets the set-up guide instead, which can be run again from Settings, General.

## Big changes

When a release changes how something works in a way people should agree to (a new kind of access, a setting
whose default changes, data that moves), give it a `review` step. If no existing step fits, add one to
`stepContent()` in `web/js/settings.js`, so the same step also works in the set-up guide.
