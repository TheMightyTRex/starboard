#!/usr/bin/env bash
# The Run first script: the one thing to run on a new Linux computer, with or without a desktop.
#
#   curl -fsSL https://raw.githubusercontent.com/TheMightyTRex/starboard/main/run-first.sh | bash
#
# A short welcome wizard, in the same style as the terminal set-up. It checks what this computer already has
# (git, Python, Docker, Docker Compose, Docker running, your user allowed to use Docker), installs only what is
# missing after you say yes, downloads Starboard, and starts its installer. Then it opens the set-up in your
# browser if this computer has a desktop, or carries on in the terminal if it does not. You can choose the
# other one, and accessible mode (plain lines for software that reads text aloud) goes on to the installer.
#
#   --check        Only check this computer and say what is missing. Changes nothing.
#   --browser      Finish set-up in a browser (the default with a desktop)
#   --terminal     Finish set-up in the terminal (the default with no desktop, such as over SSH)
#   --plain        Accessible mode: plain lines with no boxes, colour or redrawing (the same as STARBOARD_PLAIN=1)
#   --yes          Do not ask: install what is missing and carry on (sudo still asks for your password)
#   --dir FOLDER   Where to put Starboard (default: ~/starboard)
#   -- ...         Anything after -- goes to ./install.sh, for example: -- --port 8096
#
# Run it as your normal user, not with sudo. It never types or keeps your password: sudo asks for it.
set -uo pipefail

REPO="${STARBOARD_REPO:-https://github.com/TheMightyTRex/starboard.git}"
DIR="${STARBOARD_DIR:-$HOME/starboard}"
CHECK=0
ASK=1
FINISH=""
PLAIN="${STARBOARD_PLAIN:+1}"
PASS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --check) CHECK=1 ;;
    --browser) FINISH=browser ;;
    --terminal) FINISH=terminal ;;
    --plain) PLAIN=1 ;;
    --yes) ASK=0 ;;
    --dir) DIR="${2:?--dir needs a folder}"; shift ;;
    --) shift; PASS=("$@"); break ;;
    -h|--help) sed -n '2,21p' "$0" 2>/dev/null || echo "See https://github.com/TheMightyTRex/starboard"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

# Answers come from the terminal even when this script arrives through a pipe (curl ... | bash).
IN=/dev/tty
if ! { : < /dev/tty; } 2>/dev/null; then
  IN=""
  [ "$ASK" = 0 ] || [ "$CHECK" = 1 ] || { echo "Stopped: no terminal to type in. Run it in a terminal, or add --yes." >&2; exit 2; }
fi
[ "$(id -u)" -ne 0 ] || { echo "Stopped: run this as your normal user, not root or sudo. It asks for your password when it needs it." >&2; exit 1; }

HELP_URL="https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/run-first.md"
STEPS=5
TITLES=("" "Welcome" "Check this computer" "Install what is missing" "Download Starboard" "Start the installer")

# The page ------------------------------------------------------------------------------------------------------

ROWS=24
COLS=80
measure() {
  local size
  size="$(stty size < "${IN:-/dev/null}" 2>/dev/null)" || size=""
  if [ -n "$size" ]; then ROWS="${size% *}"; COLS="${size#* }"; fi
  W=$(( COLS < 78 ? COLS : 78 ))
}
measure
FANCY=1
COLOUR=1
[ -z "$PLAIN" ] || FANCY=0
[ -n "$IN" ] && [ -t 1 ] || FANCY=0
[ "$COLS" -ge 60 ] && [ "$ROWS" -ge 20 ] || FANCY=0
case "$(locale charmap 2>/dev/null)" in UTF-8|utf8) ;; *) FANCY=0 ;; esac
[ -z "${NO_COLOR:-}" ] && [ "${TERM:-dumb}" != dumb ] || COLOUR=0

c() { if [ "$COLOUR" = 1 ]; then printf '\033[%sm%s\033[0m' "$1" "$2"; else printf '%s' "$2"; fi; }
accent() { c "1;36" "$1"; }
dim() { c "2" "$1"; }
rep() { local s="" i; for ((i = 0; i < $2; i++)); do s+="$1"; done; printf '%s' "$s"; }

SCREEN=()
HEADER=()
DRAWN=0
STEP=0
KEYS=""
PROMPT=""

# Everything shown on a step goes through say, so the step can be drawn again when the window changes size.
say() {
  local line
  printf '%s\n' "$1"
  if [ "$FANCY" = 1 ]; then while IFS= read -r line; do SCREEN+=("$line"); done <<< "$1"; fi
}
# A paragraph, wrapped to the width and set in by two spaces.
para() {
  if [ "$FANCY" = 0 ]; then say "$1"; return; fi
  say "$(printf '%s\n' "$1" | fold -s -w $(( W - 4 )) | sed 's/ *$//; s/^/  /')"
}
ok() { if [ "$FANCY" = 1 ]; then say "  $(c 32 "✔") $1"; else say "Ready: $1"; fi; }
bad() { if [ "$FANCY" = 1 ]; then say "  $(c 33 "✘") $1"; else say "Missing: $1"; fi; }
note() { if [ "$FANCY" = 1 ]; then say "  $(c 33 "⚠") $1"; else say "Note: $1"; fi; }

# The logo: the monitor with four tiles, and the star, in the logo's two colours (tile and star).
LOGO=(
"               {S}▄{R}"
"             {S}▄▄█▄▄{R}"
" {T}███████████{S}▀█████▀{R}"
" {T}█  ▄▄▄▄  ▄▄▄{S}▄█▀█▄{R}"
" {T}█  ████ ████{S}▀  {T}█{S}▀{R}"
" {T}█  ▀▀▀▀ ▀▀▀▀▀  █{R}"
" {T}█  ████ █████  █{R}"
" {T}█  ▀▀▀▀  ▀▀▀▀  █{R}"
" {T}████████████████{R}"
"      {T}██████{R}"
)
logo_line() {
  local t="" s="" r=""
  if [ "$COLOUR" = 1 ]; then t=$'\033[38;5;105m'; s=$'\033[38;5;209m'; r=$'\033[0m'; fi
  local line="${LOGO[$1]//\{T\}/$t}"
  line="${line//\{S\}/$s}"
  printf '%s' "${line//\{R\}/$r}"
}

header() {
  local title="$1" step="$2" inner=$(( W - 4 )) right="" left gap bar filled pct
  [ "$step" -gt 0 ] && right="step $step of $STEPS"
  left="Starboard | $title"
  gap=$(( inner - ${#left} - ${#right} - 2 )); [ "$gap" -ge 1 ] || gap=1
  HEADER=("$(dim "┌$(rep ─ $(( inner + 2 )))┐")"
          "$(dim "│")  $(c 1 Starboard)$(dim " | ")$(accent "$title")$(rep " " "$gap")$(dim "$right")  $(dim "│")"
          "$(dim "└$(rep ─ $(( inner + 2 )))┘")")
  bar=$(( W - 12 ))
  filled=$(( bar * (step - 1) / STEPS ))
  pct=$(( 100 * (step - 1) / STEPS ))
  HEADER+=("  $(c 36 "$(rep █ "$filled")")$(dim "$(rep ░ $(( bar - filled )))")  $(dim "$(printf '%3d%%' "$pct")")")
}

menu() {
  local line="" plain="" k label gap right="Enter: recommended"
  for k in $KEYS; do
    case "$k" in b) label="Back" ;; "?") label="Help" ;; q) label="Stop" ;; *) continue ;; esac
    line+="$(accent "$k") $label   "; plain+="$k $label   "
  done
  gap=$(( W - 4 - ${#plain} - ${#right} )); [ "$gap" -ge 1 ] || gap=1
  printf '\0337\033[%d;1H\033[2K%s\033[%d;1H\033[2K  %s%s%s\0338' $(( ROWS - 1 )) "$(dim "$(rep ─ "$W")")" \
    "$ROWS" "$line" "$(rep " " "$gap")" "$(dim "$right")"
}

# A cleared page: the heading box and progress bar at the top, the menu on the last two lines, and only the lines
# between them scrolling. Plain mode prints a heading line instead.
page() {
  STEP="$1"
  KEYS="? q"; [ "$STEP" -gt 1 ] && KEYS="b ? q"
  SCREEN=()
  if [ "$FANCY" = 0 ]; then
    printf '\n== Starboard | %s (step %d of %d)\n' "${TITLES[$STEP]}" "$STEP" "$STEPS"
    if [ "$STEP" -gt 1 ]; then echo "Type b to go back, ? for help or q to stop."; else echo "Type ? for help or q to stop."; fi
    return
  fi
  measure
  header "${TITLES[$STEP]}" "$STEP"
  draw_page
  say ""
}
draw_page() {
  local i top=$(( ${#HEADER[@]} + 1 ))
  printf '\033[r\033[2J'
  for i in "${!HEADER[@]}"; do printf '\033[%d;1H%s' $(( i + 1 )) "${HEADER[$i]}"; done
  printf '\033[%d;%dr' "$top" $(( ROWS - 2 ))
  menu
  printf '\033[%d;1H' "$top"
  DRAWN=1
}
# The window changed size: the same step, drawn again to fit, with its last lines and the question.
resized() {
  [ "$FANCY" = 1 ] && [ "$DRAWN" = 1 ] || return 0
  measure
  [ "$COLS" -ge 60 ] && [ "$ROWS" -ge 20 ] || return 0
  header "${TITLES[$STEP]}" "$STEP"
  local keep=$(( ROWS - 2 - ${#HEADER[@]} - 1 )) n=${#SCREEN[@]} i
  draw_page
  for (( i = (n > keep ? n - keep : 0); i < n; i++ )); do printf '%s\n' "${SCREEN[$i]}"; done
  printf '%s' "$PROMPT"
}
trap resized WINCH

# Gives the whole window back: no scrolling area, the menu gone, the cursor under the last thing shown.
finish() {
  if [ "$FANCY" = 1 ] && [ "$DRAWN" = 1 ]; then
    printf '\0337\033[r\033[%d;1H\033[2K\033[%d;1H\033[2K\0338\n' $(( ROWS - 1 )) "$ROWS"
    DRAWN=0
  fi
}
trap 'finish' EXIT
trap 'finish; echo; echo "Stopped. Nothing else was changed."; exit 130' INT

# Help over the step: a box in the middle, the step dimmed behind it. Enter closes it.
popup() {
  local title="$1" text="$2"
  if [ "$FANCY" = 0 ]; then printf '%s\n' "$text" | fold -s -w 76; return; fi
  local bw=$(( W - 6 < 62 ? W - 6 : 62 )) left inner row=1 line top=3 i
  left=$(( (W - bw) / 2 )); inner=$(( bw - 4 ))
  local body=() wrapped
  while IFS= read -r line; do body+=("$line"); done < <(printf '%s\n' "$text" | fold -s -w "$inner" | sed 's/ *$//')
  local keep=$(( ROWS - 2 - ${#HEADER[@]} )) n=${#SCREEN[@]}
  printf '\033[r\033[2J'
  for line in "${HEADER[@]}" "${SCREEN[@]:$(( n > keep ? n - keep : 0 ))}"; do
    [ "$row" -le $(( ROWS - 2 )) ] || break
    wrapped="$(printf '%s' "$line" | sed 's/\x1b\[[0-9;]*m//g')"
    printf '\033[%d;1H%s' "$row" "$(c "2;90" "$wrapped")"; row=$(( row + 1 ))
  done
  local t="${title:0:$(( bw - 6 ))}"
  printf '\033[%d;%dH%s%s%s' "$top" $(( left + 1 )) "$(c 36 "╭─ ")" "$(accent "$t")" "$(c 36 " $(rep ─ $(( bw - 5 - ${#t} )))╮")"
  body=("" "${body[@]}" "" "$(printf '%*s' "$inner" "Enter: close help")")
  for i in "${!body[@]}"; do
    line="${body[$i]}"
    [ "$i" = $(( ${#body[@]} - 1 )) ] && line="$(dim "$line")" || line="$line$(rep " " $(( inner - ${#line} )))"
    printf '\033[%d;%dH%s %s %s' $(( top + 1 + i )) $(( left + 1 )) "$(c 36 "│")" "$line" "$(c 36 "│")"
  done
  printf '\033[%d;%dH%s' $(( top + 1 + ${#body[@]} )) $(( left + 1 )) "$(c 36 "╰$(rep ─ $(( bw - 2 )))╯")"
  printf '\0337\033[%d;1H\033[2K%s\033[%d;1H\033[2K  %s Close help\0338' $(( ROWS - 1 )) "$(dim "$(rep ─ "$W")")" "$ROWS" "$(accent Enter)"
  read -r _ < "$IN" || true
}

# ask "question" "default" "help": sets ANSWER. Returns 0 for an answer, 10 for Back, 11 to draw the step again.
ANSWER=""
ask() {
  local question="$1" default="$2" helptext="$3"
  if [ -z "$IN" ]; then ANSWER="$default"; return 0; fi
  PROMPT="  $(accent "›") $question "; [ "$FANCY" = 1 ] || PROMPT="$question "
  printf '\n%s' "$PROMPT"; [ "$FANCY" = 1 ] && SCREEN+=("")
  IFS= read -r ANSWER < "$IN" || ANSWER="q"
  [ "$FANCY" = 1 ] && SCREEN+=("$(printf '%s' "$PROMPT")$ANSWER")
  ANSWER="$(printf '%s' "$ANSWER" | sed 's/^ *//; s/ *$//')"
  case "$ANSWER" in
    q|Q) finish; echo; echo "Stopped. Nothing else was changed. Run it again at any time."; exit 1 ;;
    b|B) [ "$STEP" -gt 1 ] && return 10; ANSWER="$default" ;;
    "?") popup "Help: ${TITLES[$STEP]}" "$helptext"; [ "$FANCY" = 1 ] && return 11; ask "$@"; return $? ;;
    "") ANSWER="$default" ;;
  esac
  return 0
}

# This computer --------------------------------------------------------------------------------------------------

OS_ID=""; OS_NAME="Linux"
if [ -r /etc/os-release ]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  OS_ID="${ID:-}"; OS_NAME="${PRETTY_NAME:-Linux}"
fi
PKG=""
if command -v apt-get >/dev/null; then PKG=apt; elif command -v dnf >/dev/null; then PKG=dnf; fi
MINT=0; [ "$OS_ID" = linuxmint ] && MINT=1
has() { command -v "$1" >/dev/null 2>&1; }

desktop() { [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ] && has xdg-open; }
DESKTOP=0; desktop && DESKTOP=1
[ -n "$FINISH" ] || { if [ "$DESKTOP" = 1 ]; then FINISH=browser; else FINISH=terminal; fi; }

# The checks: a name, whether it is ready, and the commands that put it right.
NEED=()      # what is missing, in words
FIX=()       # the commands to run, in order
NEW_GROUP=0  # the user was just added to the docker group: run the installer within it
check() {
  NEED=(); FIX=()
  local base=()
  has curl || base+=(curl)
  has git || base+=(git)
  has python3 || base+=(python3)
  if [ ${#base[@]} -gt 0 ]; then
    NEED+=("${base[@]}")
    case "$PKG" in
      apt) FIX+=("sudo apt-get update" "sudo apt-get install -y ${base[*]} ca-certificates") ;;
      dnf) FIX+=("sudo dnf install -y ${base[*]}") ;;
    esac
  fi
  if ! has docker; then
    NEED+=("Docker" "Docker Compose" "Docker running")
    if [ "$MINT" = 1 ]; then
      FIX+=("sudo apt-get install -y docker.io docker-compose-v2")
    else
      FIX+=("curl -fsSL https://get.docker.com -o /tmp/get-docker.sh" "sudo sh /tmp/get-docker.sh")
    fi
    has systemctl && FIX+=("sudo systemctl enable --now docker")
  else
    if ! docker compose version >/dev/null 2>&1; then
      NEED+=("Docker Compose")
      case "$PKG" in
        apt) if [ "$MINT" = 1 ] || [ "$OS_ID" = ubuntu ]; then FIX+=("sudo apt-get install -y docker-compose-v2")
             else FIX+=("sudo apt-get install -y docker-compose-plugin"); fi ;;
        dnf) FIX+=("sudo dnf install -y docker-compose-plugin") ;;
      esac
    fi
    if has systemctl && ! systemctl is-active --quiet docker 2>/dev/null; then
      NEED+=("Docker running")
      FIX+=("sudo systemctl enable --now docker")
    fi
  fi
  if ! id -nG | tr ' ' '\n' | grep -qx docker; then
    if getent group docker 2>/dev/null | cut -d: -f4 | tr ',' '\n' | grep -qx "$USER"; then
      NEW_GROUP=1  # added already; this sign-in does not know yet
    else
      NEED+=("Your user allowed to use Docker")
      FIX+=("sudo usermod -aG docker $USER")
    fi
  fi
}
is_missing() { local n; for n in "${NEED[@]}"; do [ "$n" = "$1" ] && return 0; done; return 1; }
memory_mb() { awk '/MemTotal/ {printf "%d", $2 / 1024}' /proc/meminfo 2>/dev/null; }
free_gb() { df -Pk "$HOME" 2>/dev/null | awk 'NR == 2 {printf "%.0f", $4 / 1048576}'; }

show_checks() {
  local mem free item
  mem="$(memory_mb)"; free="$(free_gb)"
  para "$OS_NAME, $(( ${mem:-0} / 1024 )).$(( ${mem:-0} % 1024 * 10 / 1024 )) GB of memory, ${free:-?} GB free in your home folder."
  [ "${mem:-0}" -ge 900 ] || note "Less than 1 GB of memory: choose the Small server preset later, in Starboard's settings."
  say ""
  for item in curl git python3 "Docker" "Docker Compose" "Docker running" "Your user allowed to use Docker"; do
    if is_missing "$item"; then bad "$item"; else ok "$item"; fi
  done
  if [ -d "$DIR/.git" ]; then ok "Starboard downloaded, in ${DIR/#$HOME/~}"; else bad "Starboard downloaded"; fi
}

# The steps ------------------------------------------------------------------------------------------------------

step_1() {
  page 1
  if [ "$FANCY" = 1 ]; then
    local i text=(
      ""
      "$(c 1 "Welcome to Starboard")"
      ""
      "This sets up everything else for you:"
      "it checks this computer, installs what"
      "is missing when you say yes, downloads"
      "Starboard and starts its installer."
      ""
      "Nothing changes until you say yes.")
    for i in "${!LOGO[@]}"; do
      say "$(logo_line "$i")$(rep " " $(( 22 - ${#LOGO[$i]} + $(printf '%s' "${LOGO[$i]}" | grep -o '{[TSR]}' | wc -l) * 3 )))${text[$i]:-}"
    done
  else
    say "Welcome to Starboard. This sets up everything else for you: it checks this computer, installs what is missing when you say yes, downloads Starboard and starts its installer. Nothing changes until you say yes."
  fi
  say ""
  if [ "$DESKTOP" = 1 ]; then
    para "This computer has a desktop, so set-up can open in your browser by itself at the end."
  else
    para "No desktop found (for example, you are connected over SSH), so set-up can carry on here in the terminal. Or finish in a browser on a phone or another computer at home."
  fi
  say ""
  local b="" t=""
  [ "$FINISH" = browser ] && b=" (recommended)" || t=" (recommended)"
  say "  1. In a browser$b"
  say "  2. Here in the terminal$t"
  local def=1; [ "$FINISH" = terminal ] && def=2
  ask "How do you want to finish setting up? [$def]" "$def" \
"Both ways ask the same questions: your password, what you want to watch, listen to and read, and when downloads may run.

In a browser: the set-up guide opens by itself on this computer's desktop. With no desktop, open the address it prints on a phone or another computer at home.

Here in the terminal: every question is asked in this window. For a server with no desktop and nothing else to finish on.

You can change your mind later: the terminal set-up can be run again, and the browser always works." || return $?
  case "$ANSWER" in
    1) FINISH=browser ;;
    2) FINISH=terminal ;;
    *) return 11 ;;
  esac
}

step_2() {
  page 2
  para "Checking what this computer already has. This changes nothing."
  say ""
  check
  show_checks
  say ""
  if [ ${#NEED[@]} -eq 0 ]; then para "Everything Starboard needs is here."; else para "Not everything is here yet. The next step asks before it installs anything."; fi
  [ "$CHECK" = 1 ] && { finish; [ ${#NEED[@]} -eq 0 ]; exit $?; }
  ask "Press Enter to carry on" "" \
"Starboard runs each app in its own sealed box with Docker, so they cannot change the rest of the computer. Docker Compose starts them together. git downloads Starboard and its updates. Python checks Starboard has started.

Your user needs to be allowed to use Docker, so Starboard's installer does not need your password every time. This is the same as administrator control of the computer, so only do it for your own user." || return $?
}

step_3() {
  page 3
  check
  if [ ${#NEED[@]} -eq 0 ]; then
    ok "Nothing to install."
    ask "Press Enter to carry on" "" "Everything Starboard needs is already on this computer." || return $?
    return 0
  fi
  if [ -z "$PKG" ] || [ ${#FIX[@]} -eq 0 ]; then
    note "This Linux is not one this script knows how to install on. It knows Debian, Ubuntu, Linux Mint, Fedora and Raspberry Pi OS."
    para "Install Docker by hand, then run this again: https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/install-docker.md"
    finish; exit 1
  fi
  local items=() item list="" start="" allow=""
  for item in "${NEED[@]}"; do
    case "$item" in
      "Docker running") start=" Then Docker is started." ;;
      "Your user allowed to use Docker") allow=" Your user is allowed to use Docker." ;;
      *) items+=("$item") ;;
    esac
  done
  for item in "${!items[@]}"; do
    if [ "$item" = 0 ]; then list="${items[0]}"
    elif [ "$item" = $(( ${#items[@]} - 1 )) ]; then list+=" and ${items[$item]}"
    else list+=", ${items[$item]}"; fi
  done
  [ -z "$list" ] || list="To install: $list."
  para "${list:-Nothing to install.}$start$allow These commands run, in order:"
  say ""
  local cmd
  for cmd in "${FIX[@]}"; do say "    $(dim "$cmd")"; done
  say ""
  para "sudo asks for the password you use to sign in to this computer. Nothing shows as you type. It can take a few minutes."
  local def=y
  if [ "$ASK" = 1 ]; then
    ask "Install them now? [Y/n]" "y" \
"These are the same commands as Starboard's help page, Install Docker. Docker's own install script is used on Debian, Ubuntu, Fedora and Raspberry Pi OS; Linux Mint uses its own packages.

Answer n to install them yourself: the commands are printed so you can copy them. Then run this script again." || return $?
    def="$ANSWER"
  fi
  case "$def" in
    n|N|no|No)
      finish
      echo "Nothing was installed. To do it yourself, run these, then run this script again:"
      printf '  %s\n' "${FIX[@]}"
      exit 1 ;;
  esac
  say ""
  for cmd in "${FIX[@]}"; do
    say "  $(accent "›") $cmd"
    if ! bash -c "$cmd" < "${IN:-/dev/null}"; then
      say ""
      note "That did not work. Read the lines above, then see the help: $HELP_URL"
      finish; exit 1
    fi
  done
  [[ " ${FIX[*]} " == *"usermod -aG docker"* ]] && NEW_GROUP=1
  check
  say ""
  if [ ${#NEED[@]} -gt 0 ]; then note "Still missing: ${NEED[*]}. See the help: $HELP_URL"; finish; exit 1; fi
  ok "Everything is installed."
  ask "Press Enter to carry on" "" "Docker is installed and running. You do not need to sign out: the installer runs with your new Docker access straight away." || return $?
}

step_4() {
  page 4
  local where="${DIR/#$HOME/~}"
  if [ -d "$DIR/.git" ]; then
    para "Starboard is already in $where. Updating it to the newest version."
    say ""
    if git -C "$DIR" pull --ff-only -q < /dev/null; then ok "Up to date."; else note "Could not update it. Carrying on with the version you have."; fi
  elif [ -e "$DIR" ]; then
    note "$where exists but is not a Starboard download. Move it or choose another folder with --dir, then run this again."
    finish; exit 1
  else
    para "Downloading Starboard into $where. This can take a minute or two."
    say ""
    if git clone --progress "$REPO" "$DIR" < /dev/null; then ok "Downloaded."; else note "The download did not work. Check this computer is online, then run this again."; finish; exit 1; fi
  fi
  ask "Press Enter to carry on" "" "Starboard's own files go in this folder, with your settings in its data folder. Updates come with ./update.sh, from the same folder." || return $?
}

step_5() {
  page 5
  local look="Standard"; [ "$FANCY" = 0 ] && look="Accessible: plain lines"
  local how="In a browser"; [ "$FINISH" = terminal ] && how="Here in the terminal"
  if [ "$FANCY" = 1 ]; then
    say "  $(c 36 "╭─ Ready ")$(c 36 "$(rep ─ $(( W - 12 )))╮")"
    local label value
    for label in "Finish set-up" "Look" "Folder"; do
      case "$label" in "Finish set-up") value="$how" ;; Look) value="$look" ;; Folder) value="${DIR/#$HOME/~}" ;; esac
      say "  $(c 36 "│") $(dim "$(printf '%-15s' "$label")")$value$(rep " " $(( W - 20 - ${#value} )))$(c 36 "│")"
    done
    say "  $(c 36 "╰$(rep ─ $(( W - 4 )))╯")"
  else
    say "Finish set-up: $how"; say "Look: $look"; say "Folder: ${DIR/#$HOME/~}"
  fi
  say ""
  para "Starboard's installer asks a few questions of its own first, about what Starboard may access. If you are unsure, the answer in capitals is the safe one."
  ask "Press Enter to start the installer" "" \
"The installer builds and starts Starboard with Docker. Answer yes to Docker access if you want Starboard to start your media apps for you.

Afterwards, update with ./update.sh in the same folder." || return $?
}

# Run it -------------------------------------------------------------------------------------------------------

# Accessible mode is asked before anything is drawn, in plain words, so software that reads text aloud reads it.
if [ "$FANCY" = 1 ] && [ "$ASK" = 1 ] && [ "$CHECK" = 0 ]; then
  printf '\nStarboard: the Run first script.\n'
  printf 'Press Enter to start, or type a and press Enter for accessible mode: plain lines with no boxes or colour, for software that reads text aloud.\n> '
  IFS= read -r first < "$IN" || first=""
  case "$first" in a|A) FANCY=0; PLAIN=1 ;; q|Q) echo "Stopped. Nothing was changed."; exit 1 ;; esac
fi

if [ "$CHECK" = 1 ]; then n=2; else n=1; fi
while [ "$n" -le "$STEPS" ]; do
  "step_$n"; rc=$?
  case "$rc" in
    0) n=$(( n + 1 )) ;;
    10) n=$(( n - 1 )) ;;
    *) ;;
  esac
done
finish

cmd=(./install.sh)
[ "$FINISH" = terminal ] && cmd+=(--terminal)
[ -n "$PLAIN" ] && cmd+=(--plain)
cmd+=("${PASS[@]}")
cd "$DIR" || exit 1
echo
status=0
if [ "$NEW_GROUP" = 1 ] && ! id -nG | tr ' ' '\n' | grep -qx docker; then
  # Just allowed to use Docker: run the installer within that group now, so nobody has to sign out first.
  sg docker -c "$(printf '%q ' "${cmd[@]}")" < "${IN:-/dev/null}" || status=$?
else
  "${cmd[@]}" < "${IN:-/dev/null}" || status=$?
fi
[ "$status" = 0 ] || exit "$status"

if [ "$FINISH" = browser ]; then
  port="$(sed -n 's/^STARBOARD_PORT=//p' .env 2>/dev/null | tail -n 1)"; port="${port:-8095}"
  url="http://localhost:$port/"
  [ -s data/setup-token ] && url="http://localhost:$port/setup.html#code=$(cat data/setup-token)"
  if [ "$DESKTOP" = 1 ]; then
    echo
    echo "Opening the set-up in your browser. If it does not open, go to http://localhost:$port"
    xdg-open "$url" >/dev/null 2>&1 &
  else
    echo
    echo "Finish set-up in a browser on a phone or another computer at home: open the address above and enter the setup code."
  fi
fi
if [ "$NEW_GROUP" = 1 ]; then
  echo "Sign out and back in once, so ordinary docker commands work in new terminals too."
fi
