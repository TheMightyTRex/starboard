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
STEPS=6
TITLES=("" "Welcome" "Check this computer" "Install what is missing" "Download Starboard" "Ready to install"
        "Install Starboard" "Done")

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
SMALL=0
if [ "$FANCY" = 1 ] && { [ "$COLS" -lt 60 ] || [ "$ROWS" -lt 20 ]; }; then FANCY=0; SMALL=1; fi
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
  if [ "$FANCY" = 0 ]; then say "$(printf '%s\n' "$1" | fold -s -w $(( COLS < 80 ? COLS - 1 : 79 )) | sed 's/ *$//')"; return; fi
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
# The same logo at 14 characters by 7 lines, for a window of 24 to 27 lines.
LOGO_SMALL=(
"          {S}▄{R}"
" {T}▄▄▄▄▄▄▄{S}▀████{R}"
" {T}█ ▄▄▄ ▄▄{S}█▀█{R}"
" {T}█ ███ ██▀ █{R}"
" {T}█ ███ ██▄ █{R}"
" {T}█▄▄▄▄▄▄▄▄▄█{R}"
"    {T}▄▄▄▄{R}"
)
# Which logo fits the window now: big from 28 lines (and 66 columns), small from 24, none below that.
logo_size() {
  if [ "$ROWS" -ge 28 ] && [ "$W" -ge 66 ]; then echo big
  elif [ "$ROWS" -ge 24 ]; then echo small
  else echo none; fi
}
logo_line() {
  local t="" s="" r="" art
  if [ "$COLOUR" = 1 ]; then t=$'\033[38;5;105m'; s=$'\033[38;5;209m'; r=$'\033[0m'; fi
  if [ "$2" = small ]; then art="${LOGO_SMALL[$1]}"; else art="${LOGO[$1]}"; fi
  local line="${art//\{T\}/$t}"
  line="${line//\{S\}/$s}"
  printf '%s' "${line//\{R\}/$r}"
}

header() {
  local title="$1" step="$2" inner=$(( W - 4 )) right="" left gap bar filled pct
  [ "$step" -gt 0 ] && [ "$step" -le "$STEPS" ] && right="step $step of $STEPS"
  left="Starboard | $title"
  gap=$(( inner - ${#left} - ${#right} - 2 )); [ "$gap" -ge 1 ] || gap=1
  HEADER=("$(dim "┌$(rep ─ $(( inner + 2 )))┐")"
          "$(dim "│")  $(c 1 Starboard)$(dim " | ")$(accent "$title")$(rep " " "$gap")$(dim "$right")  $(dim "│")"
          "$(dim "└$(rep ─ $(( inner + 2 )))┘")")
  bar=$(( W - 12 ))
  filled=$(( bar * (step - 1) / STEPS )); [ "$filled" -le "$bar" ] || filled=$bar
  pct=$(( 100 * (step - 1) / STEPS )); [ "$pct" -le 100 ] || pct=100
  HEADER+=("  $(c 36 "$(rep █ "$filled")")$(dim "$(rep ░ $(( bar - filled )))")  $(dim "$(printf '%3d%%' "$pct")")")
}

menu() {
  local line="" plain="" k label gap right="${MENU_RIGHT:-Enter: recommended}" keys
  read -ra keys <<< "$KEYS"  # read, not $KEYS, so ? is never taken as a file name pattern
  for k in "${keys[@]}"; do
    case "$k" in b) label="Back" ;; "?") label="Help" ;; q|Ctrl+C) label="Stop" ;; *) continue ;; esac
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
  MENU_RIGHT=""
  SCREEN=()
  if [ "$FANCY" = 0 ] && [ "$STEP" -gt "$STEPS" ]; then
    printf '\n== Starboard | %s\n' "${TITLES[$STEP]}"
    return
  fi
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
  if [ "$STEP" = 1 ]; then
    SCREEN=()
    say ""
    welcome
    printf '\n%s' "$PROMPT"
    return
  fi
  for (( i = (n > keep ? n - keep : 0); i < n; i++ )); do printf '%s\n' "${SCREEN[$i]}"; done
  printf '%s' "$PROMPT"
}
# The handler only notes the change: the step is drawn again between read slices (tty_read), never inside the
# handler, where a second change of size could arrive while the first is still being drawn.
RESIZED=0
POPUP=0
trap 'RESIZED=1' WINCH

# Gives the whole window back: no scrolling area, the menu gone, the cursor under the last thing shown.
finish() {
  [ -z "${KEEP:-}" ] || { kill "$KEEP" 2>/dev/null; KEEP=""; }
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
  local all=() wrapped room=$(( ROWS - 9 )) from=0
  while IFS= read -r line; do all+=("$line"); done < <(printf '%s\n' "$text" | fold -s -w "$inner" | sed 's/ *$//')
  [ "$room" -ge 4 ] || room=4
  while [ "$from" -lt "${#all[@]}" ]; do
    local body=("${all[@]:$from:$room}") foot="Enter: close help"
    from=$(( from + room ))
    [ "$from" -lt "${#all[@]}" ] && foot="Enter: more below"
    POPUP=1
    popup_page "$title" "$foot" "${body[@]}"
    POPUP=0
  done
  RESIZED=0
}
# One page of help: the step dimmed behind, the box over it, and Enter to go on.
popup_page() {
  local title="$1" foot="$2"; shift 2
  local body=("$@") bw=$(( W - 6 < 62 ? W - 6 : 62 )) left inner row=1 line top=3 i wrapped
  left=$(( (W - bw) / 2 )); inner=$(( bw - 4 ))
  local keep=$(( ROWS - 2 - ${#HEADER[@]} )) n=${#SCREEN[@]}
  printf '\033[r\033[2J'
  for line in "${HEADER[@]}" "${SCREEN[@]:$(( n > keep ? n - keep : 0 ))}"; do
    [ "$row" -le $(( ROWS - 2 )) ] || break
    wrapped="$(printf '%s' "$line" | sed 's/\x1b\[[0-9;]*m//g')"
    printf '\033[%d;1H%s' "$row" "$(c "2;90" "$wrapped")"; row=$(( row + 1 ))
  done
  local t="${title:0:$(( bw - 6 ))}"
  printf '\033[%d;%dH%s%s%s' "$top" $(( left + 1 )) "$(c 36 "╭─ ")" "$(accent "$t")" "$(c 36 " $(rep ─ $(( bw - 5 - ${#t} )))╮")"
  body=("" "${body[@]}" "" "$(printf '%*s' "$inner" "$foot")")
  for i in "${!body[@]}"; do
    line="${body[$i]}"
    [ "$i" = $(( ${#body[@]} - 1 )) ] && line="$(dim "$line")" || line="$line$(rep " " $(( inner - ${#line} )))"
    printf '\033[%d;%dH%s %s %s' $(( top + 1 + i )) $(( left + 1 )) "$(c 36 "│")" "$line" "$(c 36 "│")"
  done
  printf '\033[%d;%dH%s' $(( top + 1 + ${#body[@]} )) $(( left + 1 )) "$(c 36 "╰$(rep ─ $(( bw - 2 )))╯")"
  local key="Close help"; [ "$foot" = "Enter: more below" ] && key="More"
  printf '\0337\033[%d;1H\033[2K%s\033[%d;1H\033[2K  %s %s\0338' $(( ROWS - 1 )) "$(dim "$(rep ─ "$W")")" "$ROWS" "$(accent Enter)" "$key"
  tty_read || true
}

# Reads one line from the terminal into REPLY_LINE. It reads in one-second slices, because bash holds a signal
# until read returns: between slices a change of window size is drawn. Typed letters wait in the terminal meanwhile.
REPLY_LINE=""
tty_read() {
  local rc
  REPLY_LINE=""
  while :; do
    IFS= read -r -t 1 REPLY_LINE < "$IN" && return 0
    rc=$?
    [ "$rc" -gt 128 ] || return 1
    if [ "$RESIZED" = 1 ] && [ "$POPUP" = 0 ]; then RESIZED=0; resized; fi
  done
}

# ask "question" "default" "help": sets ANSWER. Returns 0 for an answer, 10 for Back, 11 to draw the step again.
ANSWER=""
ask() {
  local question="$1" default="$2" helptext="$3"
  if [ -z "$IN" ]; then ANSWER="$default"; return 0; fi
  PROMPT="  $(accent "›") $question "; [ "$FANCY" = 1 ] || PROMPT="$question "
  printf '\n%s' "$PROMPT"; [ "$FANCY" = 1 ] && SCREEN+=("")
  if tty_read; then ANSWER="$REPLY_LINE"; else ANSWER="q"; fi
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
  NEED=(); FIX=(); FIX_NAME=()
  local base=()
  has curl || base+=(curl)
  has git || base+=(git)
  has python3 || base+=(python3)
  if [ ${#base[@]} -gt 0 ]; then
    NEED+=("${base[@]}")
    case "$PKG" in
      apt) fix "Updating the list of software" "sudo apt-get update"
           fix "Installing $(words "${base[@]}")" "sudo apt-get install -y ${base[*]} ca-certificates" ;;
      dnf) fix "Installing $(words "${base[@]}")" "sudo dnf install -y ${base[*]}" ;;
    esac
  fi
  if ! has docker; then
    NEED+=("Docker" "Docker Compose" "Docker running")
    if [ "$MINT" = 1 ]; then
      [ "$PKG" = apt ] && [ ${#base[@]} -eq 0 ] && fix "Updating the list of software" "sudo apt-get update"
      fix "Installing Docker and Docker Compose" "sudo apt-get install -y docker.io docker-compose-v2"
    else
      fix "Downloading Docker's installer" "curl -fsSL https://get.docker.com -o /tmp/get-docker.sh"
      fix "Installing Docker and Docker Compose" "sudo sh /tmp/get-docker.sh"
    fi
    has systemctl && fix "Starting Docker" "sudo systemctl enable --now docker"
  else
    if ! docker compose version >/dev/null 2>&1; then
      NEED+=("Docker Compose")
      case "$PKG" in
        apt) if [ "$MINT" = 1 ] || [ "$OS_ID" = ubuntu ]; then fix "Installing Docker Compose" "sudo apt-get install -y docker-compose-v2"
             else fix "Installing Docker Compose" "sudo apt-get install -y docker-compose-plugin"; fi ;;
        dnf) fix "Installing Docker Compose" "sudo dnf install -y docker-compose-plugin" ;;
      esac
    fi
    if has systemctl && ! systemctl is-active --quiet docker 2>/dev/null; then
      NEED+=("Docker running")
      fix "Starting Docker" "sudo systemctl enable --now docker"
    fi
  fi
  if ! id -nG | tr ' ' '\n' | grep -qx docker; then
    if getent group docker 2>/dev/null | cut -d: -f4 | tr ',' '\n' | grep -qx "$USER"; then
      NEW_GROUP=1  # added already; this sign-in does not know yet
    else
      NEED+=("Your user allowed to use Docker")
      fix "Allowing your user to use Docker" "sudo usermod -aG docker $USER"
    fi
  fi
}
fix() { FIX_NAME+=("$1"); FIX+=("$2"); }
# "git", "git and python3", "curl, git and python3"
words() {
  local out="" i
  for (( i = 1; i <= $#; i++ )); do
    if [ "$i" = 1 ]; then out="${!i}"; elif [ "$i" = "$#" ]; then out+=" and ${!i}"; else out+=", ${!i}"; fi
  done
  printf '%s' "$out"
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

# Work happens quietly. What the commands print goes to this log, and the person sees a progress bar with an
# animation; plain mode prints one line as each job starts and finishes. The log is kept for "Show the details".
LOG="${TMPDIR:-/tmp}/starboard-run-first-$(id -u).log"
KEEP=""
SPIN=(⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏)

# One frame: the bar fills job by job, a lighter band moves through the job that is running, then the job's name.
frame() {
  local n="$1" of="$2" name="$3" tick="$4" bar=$(( W - 30 < 40 ? W - 30 : 40 )) filled from to i line=""
  [ "$bar" -ge 10 ] || bar=10
  filled=$(( bar * (n - 1) / of ))
  from=$filled; to=$(( bar * n / of ))
  for (( i = 0; i < bar; i++ )); do
    if [ "$i" -lt "$filled" ]; then line+="█"
    elif [ "$i" -lt "$to" ] && [ $(( (i - from + tick) % 6 )) -lt 2 ]; then line+="▓"
    elif [ "$i" -lt "$to" ]; then line+="▒"
    else line+="░"; fi
  done
  printf '\r\033[2K  %s %s  %s' "$(c 36 "$line")" "$(c 36 "${SPIN[$(( tick % 10 ))]}")" "$(printf '%s' "$name" | cut -c1-$(( W - bar - 8 )))"
}

# work "name" "command" n of: runs one job quietly. Returns the command's status.
work() {
  local name="$1" cmd="$2" n="$3" of="$4" pid tick=0 status
  printf '\n== %s\n$ %s\n' "$name" "$cmd" >> "$LOG"
  if [ "$FANCY" = 0 ]; then
    say "$name ($n of $of). Please wait..."
    bash -c "$cmd" >> "$LOG" 2>&1 < /dev/null; status=$?
    [ "$status" = 0 ] && say "Done: $name."
    return "$status"
  fi
  bash -c "$cmd" >> "$LOG" 2>&1 < /dev/null &
  pid=$!
  while kill -0 "$pid" 2>/dev/null; do
    if [ "$RESIZED" = 1 ]; then RESIZED=0; PROMPT=""; resized; fi
    frame "$n" "$of" "$name" "$tick"
    tick=$(( tick + 1 ))
    sleep 0.12
  done
  wait "$pid"; status=$?
  printf '\r\033[2K'
  [ "$status" = 0 ] && ok "$name"
  return "$status"
}

# What went wrong, in plain words, from the end of the log; and what to try.
explain() {
  local tail; tail="$(tail -n 40 "$LOG" 2>/dev/null)"
  case "$tail" in
    *"Could not resolve"*|*"Temporary failure resolving"*|*"Failed to fetch"*|*"Could not connect"*|*"curl: (6)"*|*"curl: (7)"*|*"Network is unreachable"*|*"unable to access"*)
      WHY="This computer could not reach the internet to download it."
      TIP="Check the network cable or Wi-Fi, then try again." ;;
    *"Could not get lock"*|*"is held by process"*|*"dpkg was interrupted"*|*"Waiting for cache lock"*|*"another process"*)
      WHY="Another program is installing updates on this computer right now. This often happens just after Linux is installed."
      TIP="Wait a few minutes for it to finish, then try again." ;;
    *"No space left"*)
      WHY="The disk is full."
      TIP="Free some space, then try again." ;;
    *"Unable to locate package"*|*"No match for argument"*|*"has no installation candidate"*)
      WHY="This version of Linux does not offer one of the things to install."
      TIP="Update Linux to its newest version, or install Docker by hand with the help page Install Docker." ;;
    *"a password is required"*|*"incorrect password"*|*"not in the sudoers"*|*"may not run sudo"*)
      WHY="Your user is not allowed to install software on this computer."
      TIP="Run this as the user you made when installing Linux, or ask whoever looks after this computer." ;;
    *)
      WHY="Something went wrong while ${1,}."
      TIP="Try again. If it happens again, choose Show the details." ;;
  esac
}

# Something failed: say what, in plain words, and offer to try again, show the details, or stop.
# Returns 0 to try again; stops the script otherwise.
problem() {
  local name="$1"
  explain "$name"
  say ""
  note "$name did not work."
  para "$WHY $TIP"
  [ -z "$IN" ] && { finish; echo "The details are in $LOG"; exit 1; }
  while :; do
    say ""
    say "  1. Try again (recommended)"
    say "  2. Show the details"
    say "  3. Stop"
    ask "What do you want to do? [1]" "1" \
"Try again runs the same job again. Nothing that already worked is undone.

Show the details shows the last lines the job printed, which help if you ask someone for help or report a problem.

Stop leaves this computer as it is now. Run the script again at any time: it carries on from what is missing." || { [ $? = 11 ] && continue; }
    case "$ANSWER" in
      1) return 0 ;;
      2) say ""; say "$(dim "$(tail -n 15 "$LOG" | cut -c1-$(( W - 4 )) | sed 's/^/    /')")"; say ""; para "The whole log is in $LOG" ;;
      3) finish; echo; echo "Stopped. The details are in $LOG"; echo "Help: $HELP_URL"; exit 1 ;;
    esac
  done
}

# sudo asks for the password once, before the quiet part, so the question is never hidden.
sudo_once() {
  sudo -n true 2>/dev/null && return 0
  para "First, sudo asks for the password you use to sign in to this computer. Nothing shows as you type."
  say ""
  # shellcheck disable=SC2024  # the redirect is for sudo itself: it reads the password from the terminal
  while ! sudo -v < "${IN:-/dev/null}"; do
    printf 'sudo: the password was not accepted\n' >> "$LOG"
    problem "Checking your password" || return 1
  done
  # Keep it fresh while the jobs run, and stop when the script ends.
  ( while sleep 50; do sudo -n -v 2>/dev/null || exit; done ) &
  KEEP=$!
}

# The steps ------------------------------------------------------------------------------------------------------

welcome() {
  local size i art text col
  size="$(logo_size)"
  if [ "$FANCY" = 0 ] || [ "$size" = none ]; then
    if [ "$FANCY" = 1 ]; then say "  $(c 1 "Welcome to Starboard")"; say ""; fi
    para "$([ "$FANCY" = 0 ] && printf 'Welcome to Starboard. ')This sets up everything else for you: it checks this computer, installs what is missing when you say yes, downloads Starboard and starts its installer. Nothing changes until you say yes."
  else
    if [ "$size" = big ]; then
      art=("${LOGO[@]}"); col=22
      text=("" "$(c 1 "Welcome to Starboard")" "" "This sets up everything else for you:" "it checks this computer, installs what"
            "is missing when you say yes, downloads" "Starboard and starts its installer." "" "Nothing changes until you say yes.")
    else
      art=("${LOGO_SMALL[@]}"); col=18
      text=("$(c 1 "Welcome to Starboard")" "" "This checks this computer, installs" "what is missing when you say yes,"
            "downloads Starboard and starts its" "installer. Nothing changes until" "you say yes.")
    fi
    for i in "${!art[@]}"; do
      say "$(logo_line "$i" "$size")$(rep " " $(( col - ${#art[$i]} + $(printf '%s' "${art[$i]}" | grep -o '{[TSR]}' | wc -l) * 3 )))${text[$i]:-}"
    done
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
}

step_1() {
  page 1
  welcome
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
  para "${list:-Nothing to install.}$start$allow"
  say ""
  local i
  for i in "${!FIX_NAME[@]}"; do say "  $(dim "$(( i + 1 )).") ${FIX_NAME[$i]}"; done
  say ""
  para "sudo asks for the password you use to sign in to this computer, once. Then it works quietly: it can take a few minutes."
  local def=y
  if [ "$ASK" = 1 ]; then
    ask "Install them now? [Y/n]" "y" \
"These are the same steps as Starboard's help page, Install Docker. Docker's own install script is used on Debian, Ubuntu, Fedora and Raspberry Pi OS; Linux Mint uses its own packages.

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
  page 3
  : > "$LOG"
  [[ " ${FIX[*]} " != *"sudo "* ]] || sudo_once
  para "Please wait, this can take some time..."
  say ""
  PROMPT=""
  for i in "${!FIX[@]}"; do
    until work "${FIX_NAME[$i]}" "${FIX[$i]//sudo /sudo -n }" $(( i + 1 )) ${#FIX[@]}; do
      problem "${FIX_NAME[$i]}"
      say ""
    done
  done
  [[ " ${FIX[*]} " == *"usermod -aG docker"* ]] && NEW_GROUP=1
  check
  say ""
  if [ ${#NEED[@]} -gt 0 ]; then
    note "Still missing: $(words "${NEED[@]}")."
    para "The jobs finished, but these are still not in place. Run the script again; if it happens again, the details are in $LOG and the help is at $HELP_URL"
    finish; exit 1
  fi
  ok "Everything is installed."
  ask "Press Enter to carry on" "" "Docker is installed and running. You do not need to sign out: the installer runs with your new Docker access straight away." || return $?
}

step_4() {
  page 4
  local where="${DIR/#$HOME/~}"
  if [ -d "$DIR/.git" ]; then
    para "Starboard is already in $where. Updating it to the newest version."
    say ""
    if work "Updating Starboard" "git -C $(printf '%q' "$DIR") pull --ff-only -q" 1 1; then :; else note "It could not be updated, so it carries on with the version you have."; fi
  elif [ -e "$DIR" ]; then
    note "$where exists but is not a Starboard download. Move it or choose another folder with --dir, then run this again."
    finish; exit 1
  else
    para "Downloading Starboard into $where. Please wait, this can take a minute or two..."
    say ""
    PROMPT=""
    until work "Downloading Starboard" "git clone -q $(printf '%q %q' "$REPO" "$DIR")" 1 1; do
      rm -rf "$DIR"
      problem "Downloading Starboard"
      say ""
    done
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
  tty_read || true; first="$REPLY_LINE"
  case "$first" in a|A) FANCY=0; PLAIN=1 ;; q|Q) echo "Stopped. Nothing was changed."; exit 1 ;; esac
fi

if [ "$SMALL" = 1 ]; then
  para "This window is $COLS by $ROWS characters, so set-up shows plain lines. For the boxed look, make it at least 60 by 20 and run this again."
fi
if [ "$CHECK" = 1 ]; then n=2; else n=1; fi
while [ "$n" -lt "$STEPS" ]; do
  "step_$n"; rc=$?
  case "$rc" in
    0) n=$(( n + 1 )) ;;
    10) n=$(( n - 1 )) ;;
    *) ;;
  esac
done
cmd=(./install.sh)
[ "$FINISH" = terminal ] && cmd+=(--terminal)
[ -n "$PLAIN" ] && cmd+=(--plain)
cmd+=("${PASS[@]}")
cd "$DIR" || exit 1

# The hand-over: what is on this computer, for the set-up's recommended answers (How to start, Storage). The drive
# list is in the same form as the disk health job's, so Starboard reads it the same way.
handover() {
  local drives apps memory
  drives="$(lsblk -J -b -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,LABEL,MODEL,SERIAL 2>/dev/null || echo '{}')"
  apps="$( { docker ps --format '{{.Names}}' 2>/dev/null || sudo -n docker ps --format '{{.Names}}' 2>/dev/null; } \
           | grep -iE 'sonarr|radarr|lidarr|readarr|prowlarr|bazarr|jellyfin|emby|plex|seerr|qbittorrent|sabnzbd|transmission|deluge|nzbget|audiobookshelf' \
           | sed 's/.*/"&"/' | paste -sd, -)"
  memory="$(awk '/MemTotal/ {printf "%d", $2 / 1024}' /proc/meminfo 2>/dev/null)"
  mkdir -p data && chmod 700 data
  printf '{"written": "%s", "memory_mb": %s, "apps": [%s], "lsblk": %s}\n' "$(date -Iseconds)" "${memory:-0}" "$apps" "$drives" \
    > data/run-first.json
}
handover

# Step 6: the installer runs inside the same frame. Its questions and messages scroll between the heading and the
# menu. On the terminal path, the terminal set-up then takes the window with its own frame.
page 6
KEYS="Ctrl+C"; MENU_RIGHT="Enter: the answer in capitals"
[ "$FANCY" = 1 ] && menu
para "Starboard's installer asks a few questions about what Starboard may access. Press Enter for the answer in capitals, which is the safe one."
say ""
status=0
[ "$FANCY" = 1 ] && export STARBOARD_QUIET_BUILD=1
if [ "$NEW_GROUP" = 1 ] && ! id -nG | tr ' ' '\n' | grep -qx docker; then
  # Just allowed to use Docker: run the installer within that group now, so nobody has to sign out first.
  sg docker -c "$(printf '%q ' "${cmd[@]}")" < "${IN:-/dev/null}" || status=$?
else
  "${cmd[@]}" < "${IN:-/dev/null}" || status=$?
fi
if [ "$FINISH" = terminal ]; then
  DRAWN=0  # the terminal set-up drew its own frame and gave the window back
  [ "$status" = 0 ] || exit "$status"
  # The set-up's changes to this computer (free space for the media folder, the Live TV folder, disk health),
  # applied with the installer, which asks for the password itself where it needs sudo.
  if [ -s data/setup-host.json ]; then
    mapfile -t host < <(python3 -c 'import json; [print(a) for a in json.load(open("data/setup-host.json"))["args"]]' 2>/dev/null)
    apply=()
    for (( i = 0; i < ${#host[@]}; i++ )); do
      case "${host[$i]}" in
        --disk|--livetv-folder)
          folder="${host[$((i + 1))]#*=}"
          if [ -d "$folder" ]; then apply+=("${host[$i]}" "${host[$((i + 1))]}")
          else echo "Not yet: $folder is made when the apps start. Run ./install.sh ${host[$i]} ${host[$((i + 1))]} after that."; fi
          i=$(( i + 1 )) ;;
        *) apply+=("${host[$i]}") ;;
      esac
    done
    if [ ${#apply[@]} -gt 0 ]; then
      echo
      echo "Applying the set-up's changes to this computer: ./install.sh ${apply[*]}"
      ./install.sh --yes "${apply[@]}" < "${IN:-/dev/null}" && rm -f data/setup-host.json
    fi
  fi
  [ "$NEW_GROUP" = 1 ] && echo "Sign out and back in once, so ordinary docker commands work in new terminals too."
  exit 0
fi
if [ "$status" != 0 ]; then
  say ""
  note "The installer stopped."
  para "The reason is on the line that starts with Stopped, above. Put it right, then run this script again: it carries on from where it stopped."
  finish
  exit "$status"
fi

port="$(sed -n 's/^STARBOARD_PORT=//p' .env 2>/dev/null | tail -n 1)"; port="${port:-8095}"
lan="$(hostname -I 2>/dev/null | awk '{print $1}')"
code="$(cat data/setup-token 2>/dev/null)"
url="http://localhost:$port/"
[ -n "$code" ] && url="http://localhost:$port/setup.html#code=$code"

# The end: "Done", where to open Starboard and the setup code, then the window goes back to the terminal.
page 7
KEYS=""; MENU_RIGHT=""
[ "$FANCY" = 1 ] && menu
ok "Starboard is installed and running."
say ""
if [ "$FANCY" = 1 ]; then
  rows=("On this computer|http://localhost:$port")
  [ -n "$lan" ] && rows+=("On other devices|http://$lan:$port")
  [ -n "$code" ] && rows+=("Setup code|$code")
  rows+=("Update later|cd ${DIR/#$HOME/~} && ./update.sh")
  say "  $(c 36 "╭─ Open Starboard ")$(c 36 "$(rep ─ $(( W - 21 )))╮")"
  for r in "${rows[@]}"; do
    label="${r%%|*}"; value="${r#*|}"
    say "  $(c 36 "│") $(dim "$(printf '%-18s' "$label")")$value$(rep " " $(( W - 23 - ${#value} )))$(c 36 "│")"
  done
  say "  $(c 36 "╰$(rep ─ $(( W - 4 )))╯")"
else
  say "On this computer: http://localhost:$port"
  [ -n "$lan" ] && say "On other devices: http://$lan:$port"
  [ -n "$code" ] && say "Setup code: $code"
  say "Update later: cd ${DIR/#$HOME/~} && ./update.sh"
fi
say ""
if [ "$DESKTOP" = 1 ]; then
  para "Opening the set-up in your browser, with the setup code filled in. If it does not open, go to http://localhost:$port"
  xdg-open "$url" >/dev/null 2>&1 &
else
  para "Finish setting up in a browser on a phone or another computer at home: open the address for other devices and enter the setup code."
fi
[ "$NEW_GROUP" = 1 ] && para "Sign out and back in once, so ordinary docker commands work in new terminals too."
finish
