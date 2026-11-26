# Releasing Starboard

The same pattern as Storyarr: one list of releases in the code feeds the release notes in the app, the upgrade
guide and the notes on GitHub, so they always say the same thing.

## Each release

1. **Version.** Put the new number in `VERSION` (for example `0.5.0`).
2. **Release entry.** Add the release to the end of `RELEASES` in `starboard/releases.py`:
   - `added`, `changed`, `deprecated`, `removed` and `fixed`: one short title and one sentence each, in the
     content rules (British English, sentence case, no em dashes, no contractions). They are the same types as
     the changelog, and the notes show them in that order. Leave out a type with nothing in it.
   - `security`: every security fix, one title and one sentence each, written so a person can judge it.
   - `review`: the upgrade guide steps worth choosing after this upgrade, from `apps`, `keys`, `jellyfin`,
     `hours`, `alerts`, `preset` and `names`. Leave it empty when nothing needs choosing: the upgrade then
     finishes on its own and the notes wait under the version in the footer.
   - `settings`: what changes in people's settings, and the way back (`./update.sh --to v<previous>`).
3. **Notes.** Run `python3 tools/release_notes.py`. It writes `docs/releases/vX.Y.Z.md`.
4. **Changelog.** `CHANGELOG.md` follows the design system's changelog rules (`docs/CHANGELOGS.md` in the
   design system). Each change goes under `## [Unreleased]` as it is made, under Added, Changed, Deprecated,
   Removed, Fixed or Security, in that order, with every security fix under Security. **Each entry is one plain
   sentence** of about 15 to 20 words, never over 25, after a short bold title: `- **Title.** What changed for the
   reader.` Add a second short sentence only for a real warning or a number people need, and "Find out more in
   [help topic](link)" when a topic exists. Keep the long detail, owner quotes and ticket numbers in `TASKS.md` and
   the help, not in the changelog. The release entry in `starboard/releases.py` uses the same words. At release time:
   - rename `## [Unreleased]` to `## [X.Y.Z] (4 November 2026)`, with the release date written that way, and
     add a new, empty `## [Unreleased]` above it;
   - check it says the same as the release entry in `starboard/releases.py`, in the same types;
   - at the end of the file, change the Unreleased link to compare from the new tag, and add the new version's
     link under it:

     ```markdown
     [Unreleased]: https://github.com/TheMightyTRex/starboard/compare/vX.Y.Z...HEAD
     [X.Y.Z]: https://github.com/TheMightyTRex/starboard/compare/v<previous>...vX.Y.Z
     ```
5. **Checks.** Run the tests (`python3 -m unittest discover -s tests`), the browser journeys
   (`tools/journeys.sh`), the help centre check (`python3 tools/check-help.py`), the security scans (`tools/security-scan.sh`) and
   `tools/check-private.sh`.
   Also run the tests as GitHub does, `tools/test-as-another-user.sh` (a fresh copy, as uid 1001, in a container), so
   a test that passes only as your own user is found before the image fails to build. The design system's copies are
   checked by `tests/test_design_system_copies.py`: change the library and sync, never the copies.
   The API and the plug-ins must not break: run `bash tools/check-api.sh` (DASH-281). In one command it checks that
   `starboard/openapi.json` and `docs/help/developers/api-reference.md` are what their tools write, runs the contract
   tests (each `/api/v1` route against its description, with its scope, right and errors) and the plug-in tests, runs
   the update smoke test (`tools/update_smoke.py`: an example plug-in updated with a settings migration, rolled back,
   and updated to a version whose health check fails, which must go back by itself; DASH-424), and runs every example
   plug-in against this build with the smoke test from the `starboard-plugins` repository (set
   `STARBOARD_PLUGINS` if it is not beside this one; `SMOKE=required` fails when Docker or that repository is
   missing). CI runs the same command on every push, where the smoke test says it was not run. A change that breaks
   either is fixed, or becomes a new API version with a deprecation note, before it is merged.
   When the installer, `update.sh` or the image changed, also run `tools/vm/vm.sh test` on at least one PC system
   and `arm64` (only when the owner asks for virtual machine tests). Record the results and any change in system use
   in `docs/TESTING.md` ([Testing and system use](TESTING.md)).
6. **The update step (DASH-418, DASH-423).** Every release is tested as people will get it: as an update, and
   with the way back.
   - **Starboard:** run `tools/update_e2e.sh` (in containers, about 15 minutes; one heavy job at a time). It installs
     the release before this one in a sealed Docker, with plug-in data folders that belong to another user, updates
     it to this build with `./update.sh`, then to a made-up broken version that must go back by itself with the
     settings and plug-in data as they were, and then updates from the page's helper (Update now's own path). It
     ends with every container and folder it made removed. A release that fails it is not tagged.
   - **Plug-ins:** `bash tools/check-api.sh` runs the update smoke test (above); the `starboard-plugins` smoke test
     installs each plug-in's published version, updates it to the new one on the same data and rolls it back, and
     its settings must be as they were. A new plug-in version also passes
     `python3 -m starboard.plugin_tester --previous old/starboard-plugin.json new/` before it is published.
   - **Reelix:** a new Reelix image is updated to from the version before by Starboard's own Reelix update
     (`tools/update_e2e.sh` with `REELIX_FROM` and `REELIX_TO`, two published version tags), which must answer
     healthy, and go back by itself when it does not.
   - **Automatic updates:** nothing extra to run: they use the same update runs. Check the release does not change
     a part's default (each is deactivated until the owner chooses it), and that `starboard/auto_updates.py`'s
     words match the help.
7. **Screenshots, at every push.** Run `tools/screenshots.sh` and look at every picture in `docs/screenshots`:
   the screens must match what changed, and only example data may appear (no real names, addresses, titles or
   folders). A screen that is new or changed a lot gets its own shot: add it to the list in
   `tools/screenshots/shoot.mjs` and to the Screenshots table in the README.
8. **Security record.** List every security fix in the release's `security` entry (the notes show it under
   Security). Check CodeQL on GitHub has no open alerts that are not explained. Add a row for the release to
   "Security checks for each release" in `docs/SECURITY-AND-TESTS.md`: which checks ran and what they found.
9. **Commit and tag** on `main`: `git tag vX.Y.Z`.
10. **Publish** (the owner, TheMightyTRexUK, runs this after giving the OK to push):

   ```bash
   gh release create vX.Y.Z --notes-file docs/releases/vX.Y.Z.md
   ```

   Then wait for GitHub's **Image** and **Checks** runs for the tag to pass (`gh run list --limit 4`) before updating a
   server or telling anyone: a failed Image run means installs from the ready-made image stay on the old version.

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
`stepContent()` in `web/js/settings-setup.js`, so the same step also works in the set-up guide.
