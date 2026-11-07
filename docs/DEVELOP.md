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
python3 tools/apply_shell.py                   # after changing the header or menu
tools/screenshots.sh                           # retake the README screenshots from example data
tools/journeys.sh                              # browser journeys against example data
python3 tools/check-help.py                    # the help centre's links, layout and writing rules
tools/vm/vm.sh test ubuntu                     # a fresh install on a clean system (also debian, fedora, arm64)
```

What each test covers, and the latest results, are in [docs/TESTING.md](TESTING.md).

The header and Display panel are written into every page by `tools/apply_shell.py`. Design tokens are in
`web/css/tokens.css`; the five designs in `web/css/designs.css`.


## The help centre

The help is written in Markdown in `docs/help`, to the rules in `docs/help/HOW-THIS-HELP-IS-WRITTEN.md`. Its web pages are
built by the design system's help centre builder, with the settings in `help-centre.json`, and published on GitHub
Pages by `.github/workflows/help.yml` when a change reaches main. To build them here:

```bash
python3 tools/check-help.py
../design-system/tools/help_centre/build.sh _site      # then open _site/help/index.html
```
