# Develop Starboard

Running Starboard from a checkout, its tests and tools, and keeping your own details out of the repository.

## Keep your details out of the repository

Settings, API keys, sessions and backups live in `./data`, `./backups` and `.env`, which git ignores. Before
contributing, run `tools/install-hooks.sh`: every commit is then checked for home network addresses, dynamic
DNS names, email addresses, keys and the words you list in `.private-words` (also ignored by git).

## Run and test it

```bash
STARBOARD_DATA=./data python3 -m starboard     # http://127.0.0.1:8095
python3 -m unittest discover -s tests
bash tools/check-api.sh                        # after any change: the API contract, plug-in tests and smoke test
tools/checks.sh                                # likely bugs, the writing rules, spelling and the workflows (15 seconds)
python3 tools/apply_shell.py                   # after adding a page to the menu (starboard/shell.py)
tools/screenshots.sh                           # retake the README screenshots from example data
tools/journeys.sh                              # browser journeys against example data
python3 tools/check-help.py                    # the help centre's links, layout and writing rules
tools/vm/vm.sh test ubuntu                     # a fresh install on a clean system (also debian, fedora, arm64)
```

What each test covers, and the latest results, are in [docs/TESTING.md](TESTING.md).

These checks run once a week on GitHub (Actions, Code and writing checks), with the unit tests under coverage.py, and
can be run there by hand at any time; they do not run on every push or release. Claude Code also checks each file it
edits in this repository with `tools/checks.sh --file` (`.claude/settings.json`), which takes about 2 seconds.
The rules are in `ruff.toml`, `biome.jsonc`, `_typos.toml` and `tools/checks/vale`; each rule that is switched off says why.

The header, menus and Display panel are in `starboard/shell.py`; the server fills them into each page when it first
serves it, so the page files hold only the shell markers (`tools/apply_shell.py` adds those). Design tokens are in
`web/css/tokens.css`; the five designs in `web/css/designs.css`.


## The help centre

The help is written in Markdown in `docs/help`, to the rules in `docs/help/HOW-THIS-HELP-IS-WRITTEN.md`. Its web pages are
built by the design system's help centre builder, with the settings in `help-centre.json`, and published on GitHub
Pages by `.github/workflows/help.yml` when a change reaches main. To build them here:

```bash
python3 tools/check-help.py
../design-system/tools/help_centre/build.sh _site      # then open _site/help/index.html
```
