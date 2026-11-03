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
