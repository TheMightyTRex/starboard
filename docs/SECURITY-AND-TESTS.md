# Security: how Starboard protects you, and how it was tested

Starboard sits on your home network next to apps that hold your media and their keys, so it is built to give
away as little as possible and to need as little access as possible. This page says how it does that, what
the security review in November 2026 found and fixed, and which security tests pass today.

To report a problem, see [SECURITY.md](../SECURITY.md). For every other kind of test, see
[Testing and system use](TESTING.md).

Latest results: 3 November 2026.

## How Starboard protects you

**Signing in**
- One password of at least 10 characters, stored only as a PBKDF2-SHA256 hash with 600,000 rounds.
- The first password needs a one-time setup code that only someone with access to the server can read. It
  stops working once used.
- Five wrong attempts lock an address out for 15 minutes, and at most two password checks run at once, so
  guesses sent all together are counted too.
- Sign-in cookies are `HttpOnly` and `SameSite=Strict`, and can be HTTPS-only behind a reverse proxy.
- Changing the password, or **Sign out everywhere**, signs out every other browser.
- A forgotten password is reset only on the server itself (`./reset-password.sh`), which also signs everyone out.
- Send feedback (Snaglist) sends its reports without cookies, so **Save in Starboard** carries a key instead. The
  key is given only to a signed-in browser, works only while that sign-in does and while Send feedback is active,
  and needs Starboard's own header and `Origin` like every other change. A report is at most 512 KB.

**Requests**
- Every change needs a header only Starboard's own pages send, and a matching `Origin`, so another website
  cannot make your browser change anything.
- Starboard answers only to its own addresses and names, which stops DNS rebinding (another website reaching it
  through its own domain name).
- Requests of the wrong shape, impossible sizes and path tricks get a plain refusal. Slow or idle connections
  close after 30 seconds, and at most 64 requests run at once.

**Your keys**
- API keys stay in `data/config.json`, readable by your user only, and are never sent to the browser.
- A saved key goes only to the server it was saved for. Change an app's address and the key must be typed
  again, and keys are dropped if an app redirects to another server.
- The log removes personal details, such as email addresses and the names you give Starboard, before anything
  is written.

**Pages**
- A strict content security policy on every page: no inline scripts, nothing loaded from other sites except
  cover pictures. The one inline stylesheet allowed is Snaglist's, by its SHA-256 hash, worked out when
  Starboard starts.
- Pages build everything as text, never as HTML, so a name containing code is shown, never run.

**Your computer**
- The container runs as your user, read-only, with every Linux capability dropped and no new privileges.
- It is capped at 512 MB of memory and 200 processes, so a fault cannot take the whole server's.
- Every kind of access is optional and off unless you say yes: Docker, folders, per-app use, disk health,
  Live TV. **Settings, About and updates** lists each one and how to change it.
- Data files are `0600` and data folders `0700`.
- **Home network** can be switched off, so nothing else on the network can connect at all.

## The security review, November 2026

Two passes on Starboard 0.3.4: an independent code review by a reviewer who had not seen the other pass, and
attacks from outside against a throwaway copy. No critical issues were found. One high, four medium and
several low issues were found; all are fixed, and each fix has a test so it stays fixed.

| Severity | What was found | How it was fixed |
|---|---|---|
| High | A request with `Content-Length: -1`, sent without signing in, made Starboard read until the connection closed. Its memory grew from 28 MB to 337 MB. | The size must be a whole number of 0 or more; anything else is refused. Memory stays flat. |
| Medium | Password guesses sent all at once got past the 5-attempt limit. Forwarded addresses were believed from anyone when proxy trust was on. | Attempts are counted before the check, and at most 2 checks run at once. Forwarded addresses are believed only from the proxy. |
| Medium | The sign-in page's `next` address could send you to another site after signing in. | Only a page on this dashboard is used. |
| Medium | A stolen session could point an app at another server and press Test, sending the saved key there. | A saved key goes only to the server it was saved for, and never across a redirect. |
| Medium | App updates built a command from container labels, which a malicious image could abuse. | Names are limited to safe characters and quoted, folders are checked, and the helper image is pinned. |
| Low | `/css/../settings.html` showed a page's markup without signing in, to clients that do not tidy `..`. | Any path with a dot segment is refused. |
| Low | Idle or slow connections were held for ever. | They close after 30 seconds, with at most 64 at once. |
| Low | Badly shaped requests ended with an error in the log. | They get a plain refusal. |
| Low | Two uploads, or two runs of the same job, could collide. | Each claims a lock first. |
| Low | No size limits on history files or Live TV downloads. | 80 MB for history, 200 and 600 MB for Live TV, and pictures over 16 megapixels are refused. |
| Low | Live TV channel data could add lines to a playlist. | Channel data is cleaned and only web addresses are used. |
| Low | A folder name with special characters could break the installer's files. | Such names are refused. |
| Low | The disk health job, which runs as root, could be tricked into writing elsewhere. | It writes in a private folder and refuses linked folders. |
| Information | DNS rebinding could reach Starboard's open routes. | Starboard answers only to its own addresses and names. |

**Left as they are, on purpose**
- A settings backup contains your apps' keys, because that is what it is for. Downloading or restoring one asks
  for the password again.
- Once signed in, you can point Starboard at any address on your network. That is what a dashboard does; the
  answers stay on the server.
- The content policy allows `https:` pictures, so search results can show covers.
- The sign-in page shows the dashboard's name and design before you sign in.

## Security tests and results

Each check has an ID, which the test scripts print beside their results. The tests run with every change; their commands are in
[Testing and system use](TESTING.md), and they run before every release.

| ID | What is tested | How | Result |
|---|---|---|---|
| SEC-01 | Every API route refuses without signing in | Unit test; install tests on 5 systems | Pass |
| SEC-02 | A change without Starboard's header, or from another site, is refused | Unit test | Pass |
| SEC-03 | Password guessing, one at a time and 30 at once | Unit tests | Pass |
| SEC-04 | A forwarded address from anyone but the proxy is ignored | Unit test | Pass |
| SEC-05 | After signing in, `next` cannot send you to another site (3 tricks) | Browser journey | Pass |
| SEC-06 | A saved key is not sent to a new server, or across a redirect | Unit tests | Pass |
| SEC-07 | Names, categories, descriptions and notes that look like code are shown as text | Browser journey | Pass |
| SEC-08 | Path tricks such as `/css/../settings.html` | Unit tests | Pass |
| SEC-09 | A negative `Content-Length` is refused | Unit test | Pass. The 30-second time-out is in the code but has no test yet. |
| SEC-10 | A request for another host name (DNS rebinding) | Unit test; install tests on 5 systems | Pass |
| SEC-11 | Cookies are `HttpOnly` and `SameSite=Strict` | Unit test | Pass. HTTPS-only cookies have no test yet. |
| SEC-12 | The content policy is on all 26 pages and blocks nothing | Unit test; browser journey | Pass |
| SEC-13 | A saved key appears in no page or answer | Unit test; browser journey | Pass |
| SEC-14 | `.env` and data files are readable by the owner only | Install tests; unit tests | Pass |
| SEC-15 | Container labels cannot run commands | Unit test | Pass |
| SEC-16 | A history file over 80 MB is refused, before the upload | Unit test | Pass. The Live TV and picture limits have no test yet. |
| SEC-17 | The setup code is needed, and works only once | Unit test | Pass. Guessing the code has no test yet. |
| SEC-18 | A new password signs out every other browser | Unit test | Pass |
| SEC-19 | Scan with OWASP ZAP, signed out and signed in (active) | `tools/security-scan.sh` | Pass: no failures; the warnings left are explained below |
| SEC-20 | Known issues in the image and its libraries (Trivy) | `tools/security-scan.sh` | Pass: 0 after updating Pillow (see below) |
| SEC-21 | With Docker access off, Starboard cannot reach Docker | Install tests | Pass |
| SEC-22 | With home network off, nothing outside the computer can connect | Install tests on 5 systems | Pass |
| SEC-23 | No personal details in the repository | `tools/check-private.sh` before every commit | Pass |
| SEC-24 | Save in Starboard needs a key from a signed-in session, ends with it, and only while Send feedback is active; the policy lets in only Snaglist's stylesheet | Unit test, browser journey | Pass |

The 5 systems are clean installs of Ubuntu 24.04, Debian 12 and Fedora 42, and 64-bit ARM with 1 GB and with
512 MB of memory.

## Security scans, 3 November 2026

`tools/security-scan.sh` runs six free scanners, all in Docker from pinned images. ZAP scans a throwaway copy on a
private Docker network with no way out, so it can never reach other apps on the same computer.

| Scanner | What it checks | Found | Now |
|---|---|---|---|
| Trivy | Known problems in the image's system packages and Python libraries; the Dockerfile | Pillow 11.3.0 had 58 known problems (5 critical, 35 high), and pip 6 more. The system packages and the Dockerfile were clean. | 0. Pillow is 13.0.0, pip is removed from the image, and Pillow may open only the picture formats logos use. |
| OWASP ZAP | The running dashboard, signed out (baseline) and signed in (active attacks on every page and API it finds) | No failures. The sign-in form could put the password in the address if Enter was pressed before the page script loaded. Two cross-origin headers were missing. Routes starting `/api/containers` answered any longer address too. | Fixed, each with a test. The warnings left are explained below. |
| Gitleaks | Keys and passwords anywhere in the git history | One: a made-up key in the test that checks the log hides keys | Nothing real. The made-up key is listed in `.gitleaksignore`. |
| Bandit | Risky patterns in the Python code | 21 places that open web addresses or listen on the network. One was real: a Live TV stream check followed `file:` links written inside a playlist from the internet. | Fixed, with a test. The other 20 were checked by hand and each is marked with its reason. |
| ShellCheck | Mistakes in the shell scripts | 3 small warnings in test tools; the installer, updater and reset script were clean | Fixed |
| Hadolint | The Dockerfile | It suggests pinning the exact `tzdata` version | Left on purpose: Alpine removes old versions, so a pin breaks builds. Trivy covers the risk. |

**ZAP warnings left, on purpose**
- **No anti-CSRF tokens:** every change needs Starboard's own header and a matching `Origin` (SEC-02), which does the
  same job. The forms ZAP flags are the Display panel's, which send nothing to the server.
- **Wildcard in the content policy:** `img-src https:`, so search results can show covers.
- **No Cross-Origin-Embedder-Policy:** it would block those cover pictures too.
- **Information only:** comments containing the word "from", times in API answers, answers that are not cached on
  purpose, and display settings kept in the browser.
- **A private address, signed in only:** `/api/network` lists the addresses you can open Starboard from, so it
  includes the server's home network address. The signed-out scan finds none.
- **Two false alarms, checked on 7 November 2026 and left out for those addresses only:** "SQL injection" on
  `/api/history?hours=`, where `hours` is only looked up in a fixed list (1, 6 or 24) and Starboard has no SQL
  database; the answers differed because the history grew between ZAP's two requests. "Path traversal" on
  `/api/config/general`, where the server name is free text that is saved and shown back, never used as a path.

## Security scans, 4 November 2026 (0.7.6)

The same six scanners. Trivy, Gitleaks, Bandit, ShellCheck, Hadolint and ZAP signed out found nothing new (ZAP
signed out: 58 passed). ZAP's active scan signed in passed 110 checks and raised two warnings across two runs, both
false alarms:

- **SQL injection (first run only):** Starboard has no database; its settings are a JSON file. The check compares
  answers to changed values, and the new server name, which refuses more than 10 characters, answers long and short
  values differently. It did not come back in the second run.
- **Path traversal on `server_name` (`PUT /api/config/general`, test value "general"):** the server name is only
  stored, sent to signed-in pages and shown as text. Nothing reads a file with it. The check is not turned off for the
  whole app, because it could find a real problem elsewhere.

`SCAN_REPORTS=folder tools/security-scan.sh --full` now keeps ZAP's reports, with each warning's address.

## Security review of the set-up wizards, 5 November 2026 (0.9.0)

Two independent reviews read every set-up path: the Run first script, `install.sh`, the terminal set-up, the browser
set-up guide, Install apps and the routes they use. Each finding was checked again in the code before it was fixed,
and each fix has a test where code can test it:

- **What the set-up hands to the installer (medium):** `data/setup-host.json` is in the data folder, which the
  container can write to. The Run first script now passes on only `--disk Media=`, `--livetv-folder` and
  `--disk-health`, each folder checked again by the same rule as the server, from a regular file only.
- **The setup code (medium to low):** a link planted at `data/setup-token` could have sent a host file, such as an
  SSH key, to the container. The code is now read only from a regular file, never through a link, and only as code
  characters, in the terminal set-up, `install.sh` and the Run first script.
- **Files the scripts write (low):** the hand-over is written to a new file and moved into place; Docker's installer
  and the logs use private temporary files instead of fixed names in `/tmp`.
- **Host names (low):** any name starting with the machine's name was allowed, which let DNS rebinding reach a native
  install. Now only the machine's name, alone or with a home-network ending.
- **Folders (low):** the installer's folder options must match whole and are never `/`, a system folder or a top
  folder; Install apps also refuses `/var/spool` and top folders.
- **Disk health (low, possible):** the root job's report folder now belongs to root, and `chown -h` never follows a
  link.
- **The first password (low):** checked and saved under one lock.

The scans then found nothing new. Trivy, Gitleaks, ShellCheck and Hadolint passed; Bandit flagged the refused-folder
lists (they name `/tmp` to refuse it), now marked. ZAP signed out passed 58 checks; ZAP signed in passed 109 with two
false alarms:

- **SQL injection on `/api/logs?level=`:** the level is picked from a fixed list (all, problems, detail), and anything
  else counts as all, so a changed value gives the same answer. There is no database.
- **Path traversal on `server_name`:** as for 0.7.6 and 0.7.7, the name is never used as a path.

The full report, with the Reelix wizard's review, is kept with the project's notes.

## Security scans, 5 November 2026 (0.8.0)

Trivy, ShellCheck and Hadolint found nothing. ZAP signed out passed 58 checks with no warnings. Three findings, none
of them a weakness:

- **Gitleaks, a "generic API key" in `tests/test_terminal_setup.py`:** a made-up token in the test that checks a
  feedback report never holds what was typed. Added to `.gitleaksignore` with a note; Gitleaks then found nothing.
- **Bandit, B310 on the download of an app's changelog (`starboard/changes.py`):** the address only ever comes from
  Starboard's fixed table of `https://` addresses. Now also checked to start with `https://` before it is opened;
  Bandit then found nothing.
- **ZAP signed in, SQL injection on `site_name` (`PUT /api/config/general`):** a false alarm. Starboard has no
  database; its settings are a JSON file, and the answer repeats the name it was sent, so changed values give
  changed answers. ZAP passed the other 110 checks.

## Security scans, 4 November 2026 (0.7.7)

Trivy, Gitleaks, Bandit, ShellCheck and Hadolint found nothing. ZAP signed out found one new warning: Python's own
error answer (501, for a request method Starboard does not handle) had no content policy or other security headers.
Fixed: those answers now carry the same headers, with a test; ZAP signed out then passed 58 checks with no warnings.
ZAP's active scan signed in passed 109 checks, with two warnings, both false alarms:

- **SQL injection on `/api/history?hours=3-2`:** `hours` is picked from a fixed list (1, 6 or 24), and anything else
  counts as 1. "3-2" happens to equal 1, so the answer matched; nothing is worked out, and there is no database.
- **Path traversal on `server_name`:** as for 0.7.6, the name is never used as a path.

## CodeQL on GitHub, 3 November 2026

GitHub's code scanning (CodeQL) checks the Python, JavaScript and workflow files on every push. Its first scan
raised 19 alerts:

| Alerts | What CodeQL saw | What it was |
|---|---|---|
| 1 | A slow pattern match on a saved copy's name | Real. A long name full of hyphens made the check slow. Fixed: the name is length-checked and the pattern can match only one way |
| 2 | A line break in a header value | Real, though no value could carry one today. Fixed: a header value with a line break is never sent |
| 1 | An old TLS version allowed | Real in principle. Fixed: certificate checks require TLS 1.2 or newer |
| 13 | A file name from a request used in a path | Not real: each name is checked first, by a strict pattern with no `/`, or against the list of files that exist |
| 1 | Server-side request forgery in the app check | By design: signed-in people point Starboard at their own apps, at `http://` or `https://` addresses only (see "Left as they are, on purpose") |
| 1 | A password stored in clear text | Not Starboard: the screenshot tool's made-up password for its example server |

Each fix has a test. On GitHub, the 15 alerts that need no change are dismissed with these reasons; the 4 fixed
alerts close when CodeQL scans the fix.

## Security checks for each release

Every release runs the checks below before it is tagged, and adds a row here. A release's notes list its security
fixes under Security.

| Release | Unit and API tests | Browser journeys | Security scans | CodeQL | Install tests | Notes |
|---|---|---|---|---|---|---|
| 0.7.4 (3 November 2026) | 117 passed | 19 passed | Trivy 0, ZAP no failures, Gitleaks 0, Bandit 0, ShellCheck 0, Hadolint 0 | First run after release: 19 alerts; 4 fixed for the next release (3 problems), 15 explained and dismissed | Ubuntu, Debian, Fedora, 64-bit ARM: 17 of 17 each | Pillow 13.0.0; see the Security section of the 0.7.4 notes |
| 0.7.5 (3 November 2026) | 123 passed | 29 passed | Trivy 0, ZAP no failures signed out (58 passed) and signed in (111 passed), Gitleaks 0, Bandit 0, ShellCheck 0, Hadolint 0 | 0 open: the 15 explained alerts stay dismissed; the new Snaglist file raised none | Ubuntu 24.04 and 64-bit ARM: 17 of 17 each | Docker Bench's finding fixed (memory and process limits); the 3 CodeQL problems fixed; Send feedback's key and stylesheet hash tested (SEC-24) |
| 0.7.6 (4 November 2026) | 125 passed | 29 passed | Trivy 0, Gitleaks 0, Bandit 0, ShellCheck 0, Hadolint 0, ZAP no failures signed out (58 passed) and signed in (110 passed; 2 warnings, both false alarms, explained above) | 0 open | Not needed: the installer, update.sh and the image did not change | The new menu and server name; help check 71 articles, 0 problems |
| 0.7.7 (4 November 2026) | 135 passed | 29 passed | Trivy 0, Gitleaks 0, Bandit 0, ShellCheck 0, Hadolint 0, ZAP signed out 1 warning fixed then 58 passed, signed in 109 passed with 2 false alarms (explained above) | 0 open | Ubuntu 24.04 and 64-bit ARM: 17 of 17 each | Keep-alive, long-lived caching, streamed Live TV guides, bytecode built into the image |
| 0.8.0 (5 November 2026) | 206 passed | 36 passed | Trivy 0, Gitleaks 0 (1 made-up test token ignored), Bandit 0 (1 fixed), ShellCheck 0, Hadolint 0, ZAP signed out 58 passed, signed in 110 passed with 1 false alarm (explained above) | 0 open | Ubuntu 24.04 and 64-bit ARM: 17 of 17 each | Terminal set-up, drive pools and the pool helper, feedback with a QR code; help check 81 articles, 0 problems |
| 0.9.0 (5 November 2026) | 218 passed | 36 passed | Trivy 0, Gitleaks 0, Bandit 0 (refused-folder lists marked), ShellCheck 0, Hadolint 0, ZAP signed out 58 passed, signed in 109 passed with 2 false alarms (explained above) | 0 open | Ubuntu 24.04 and 64-bit ARM: 17 of 17 each; the Run first script on bare Debian 12, Ubuntu 24.04 and Fedora 42: 12 of 12 each | Security review of every set-up wizard, its findings fixed; the Run first script; one order for both set-ups; help check 83 articles, 0 problems |
| 0.9.1 (5 November 2026) | 218 passed | 36 passed | Trivy 0, Gitleaks 0, Bandit 0, ShellCheck 0, Hadolint 0, ZAP signed out 58 passed (the active scan signed in not repeated: only update.sh and the help changed) | 0 open | Ubuntu 24.04: 17 of 17, including ./update.sh --check | update.sh lists the changes without a broken pipe; help on capital letters and a 404 |
| 0.9.2 (5 November 2026) | 219 passed | 36 passed | Trivy 0, Gitleaks 0, Bandit 0, ShellCheck 0, Hadolint 0, ZAP signed out 58 passed, no warnings | 0 open | Ubuntu 24.04 and 64-bit ARM: 17 of 17 each; the Run first script on bare Ubuntu 24.04: 12 of 12 | Releases and Restore pages, Sign out on Settings pages, Help per page; help check 83 articles, 0 problems |
| 0.10.0 (7 November 2026) | 247 passed | 36 passed | Trivy 0, Gitleaks 0 (one made-up test key added to the ignore list), Bandit 0, ShellCheck 0 after one fix (install.sh called echo before defining it), Hadolint 0, ZAP signed out 58 passed, no warnings | 0 open | Fresh installs on Debian 13, Ubuntu 26.04, Linux Mint 22.3 and the emulated Raspberry Pi OS, terminal and browser routes (os-tests findings 1 to 22); Reelix set-up against the real Reelix Lite 0.8.6 image | Reelix route, Which Reelix and Settings, Reelix; a test move of a real stack into Reelix; help check 89 articles, 0 problems |
| 0.11.0 (8 November 2026) | 343 passed | not run (released without them, at the owner's request) | Not run for this release | 0 open | The terminal rules check on fresh Ubuntu 26.04 machines: 80x24, 80x30, 140x60, resize and browser cases passed; Debian 13 started, stopped early | Terminal frame, error numbers, help slide-outs and radio; help check 99 articles, 0 problems |
| 0.12.0 (8 November 2026) | 372 passed | 36 passed (one phone-width fault from 0.11.0 fixed) | Trivy 0 after one fix (zlib CVE-2026-4738, medium, in the base image), Gitleaks 0, Bandit 0, Hadolint 0, ZAP signed out 58 passed, no warnings; ShellCheck 12 warnings (11 unused variables, 1 SC2155) in install.sh and run-first.sh, from 0.11.0, not changed in this release | 1 open from 0.11.0 (a slow regular expression in tests/test_wizard_rules.py, py/redos), fixed in this release | Not rerun: the installer and update.sh did not change; the image change (zlib) was built and started (healthz 200). Takeover and roll back rehearsal, 98 of 98; a real server's apps moved into a test Reelix | Take over the apps you already run, move them into Reelix, roll back; help check 100 articles, 0 problems |
| 0.12.1 (8 November 2026) | 375 passed | 36 passed | Not rerun: a small change (Reelix's token read from its log, and a button); Bandit-style risks reviewed by hand: one Docker log read of two named containers, nothing new reachable | 0 open | Not needed: the installer, update.sh and the image did not change | Reelix's set-up after a start from the browser, Finish setting up Reelix; help check 100 articles, 0 problems |
| 0.12.2 (8 November 2026) | 378 passed | 36 passed | Not rerun: a small change (qBittorrent's user name read from its settings file, messages placed under each step) | 0 open | Not needed: the installer, update.sh and the image did not change | qBittorrent's user name; messages under each step; help check 100 articles, 0 problems |
| 0.13.0 (9 November 2026) | 467 passed (2 skipped) | 67 passed | Trivy 0, Gitleaks 0 (1 made-up test token ignored), Bandit 0, Hadolint 0, ShellCheck: the 11 known unused variables in install.sh (DASH-153), ZAP signed out 58 passed | 0 open | The terminal set-up ran on test machines (Debian, Ubuntu, Mint, Fedora) on night/terminal-fixes before the merge; no new run (owner: no more test machine runs unless asked) | Merges night/terminal-fixes, night/reelix-steps and night/library-search. |

## Other free checks you can run

These suit Starboard and cost nothing:
- **On GitHub, free for public repositories:** secret scanning with push protection and CodeQL code scanning are
  on for Starboard. Dependabot alerts add little, because Starboard has only one outside package.
- **Nmap** from another computer on your network, to confirm which ports your server really has open.
- **Lynis** and **Docker Bench for Security**, to audit the server itself and its Docker set-up rather than
  Starboard.
  Docker Bench was run on 3 November 2026. Its one finding for Starboard was that the container had no memory
  or process limit; the compose files now set 512 MB and 200 processes (and the `--native` service the same).
- **testssl.sh**, if you put Starboard behind a reverse proxy with HTTPS.

## Not tested yet

- Connection time-outs, HTTPS-only cookies, the Live TV and picture size limits, and guessing the setup code.
  Each is in the code, and was checked by hand in the review, but has no automatic test yet.
- Windows and Mac, which Starboard does not support yet, and a physical Raspberry Pi.
