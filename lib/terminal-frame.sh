# shellcheck shell=bash
# The terminal frame for an app's terminal scripts. Its source is the design system (terminal/terminal-frame.sh in
# TheMightyTRex/design-system; tools/sync.py copies it): change it there. In Starboard, the Run first script
# (run-first.sh, which has a copy of this file between its "terminal-frame" lines, because it arrives on its own
# through curl) and the installer (install.sh, which reads this file). The rules are in docs/TERMINAL.md: a heading box and
# progress bar at the top, the menu on the bottom two lines, only the lines between them scrolling; numbered answers
# with the recommended one first; help as a box over the step; one bar for a job; plain lines for screen readers.
# A script sets IN (the terminal to read answers from, or empty), TTY (the window to draw in when there are no
# questions to ask, such as with --yes; it defaults to IN), PLAIN, STEPS, TITLES, LOG and an err function, then sources it.
# When another script runs it and needs to know how it stopped, it also sets STOP_FILE (see stopped_by_person).
# For its own name and feedback it sets APP_NAME, APP_VERSION, ISSUES (the repository for the feedback link, owner/name)
# and, when it has its own feedback flow, a function called app_feedback.
# tests/test_terminal_frame.py checks that run-first.sh's copy is the same. 7 November 2026.

APP_NAME="${APP_NAME:-Starboard}"
ISSUES="${ISSUES:-TheMightyTRex/starboard}"

# The page ------------------------------------------------------------------------------------------------------

ROWS=24
COLS=80
measure() {
  local size
  size="$(stty size < "${TTY:-${IN:-/dev/null}}" 2>/dev/null)" || size=""
  if [ -n "$size" ]; then ROWS="${size% *}"; COLS="${size#* }"; fi
  W=$(( COLS < 100 ? COLS : 100 ))
  # The frame and text sit in a column centred in a wider window; L is its left margin, PAD those spaces.
  if [ "${FANCY:-0}" = 1 ]; then L=$(( (COLS - W) / 2 )); else L=0; fi
  PAD="$(printf '%*s' "$L" "")"
}
measure
FANCY=1
COLOUR=1
[ -z "$PLAIN" ] || FANCY=0
[ -n "${TTY:-$IN}" ] && [ -t 1 ] || FANCY=0
SMALL=0
# SMALL: the scripts say why they show plain lines.
# shellcheck disable=SC2034
if [ "$FANCY" = 1 ] && { [ "$COLS" -lt 60 ] || [ "$ROWS" -lt 20 ]; }; then FANCY=0; SMALL=1; fi
case "$(locale charmap 2>/dev/null)" in UTF-8|utf8) ;; *) FANCY=0 ;; esac
[ "${TERM:-dumb}" != dumb ] || FANCY=0
[ -z "${NO_COLOR:-}" ] && [ "${TERM:-dumb}" != dumb ] || COLOUR=0
[ "$FANCY" = 1 ] || COLOUR=0  # plain lines are read aloud: no colour codes in them
measure  # again, now that it is known whether the column is centred

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
  printf '%s\n' "$1" | sed "s/^/$PAD/"
  if [ "$FANCY" = 1 ]; then while IFS= read -r line; do SCREEN+=("$line"); done <<< "$1"; fi
}
# A paragraph, wrapped to the width and set in by two spaces.
para() {
  if [ "$FANCY" = 0 ]; then say "$(printf '%s\n' "$1" | fold -s -w $(( COLS < 80 ? COLS - 1 : 79 )) | sed 's/ *$//')"; return; fi
  wrap_para "$1" | sed "s/^/$PAD/"
  SCREEN+=($'\x01'"$1")  # kept as text, so a change of window size wraps it again at the new width
}
wrap_para() { printf '%s\n' "$1" | fold -s -w $(( W - 4 )) | sed 's/ *$//; s/^/  /'; }
# A hanging line: a lead (such as "  ● 1  " or "  ✔ "), then text wrapped under itself. Style
# "dim" dims the text; "(recommended)" and "(your last answer)" are shown in green. Kept as text, so a change of
# window size wraps it again.
hang() {
  local lead="$1" style="$2" text="$3"
  if [ "$FANCY" = 0 ]; then
    # Plain lines wrap between words inside the window too, the rest of the text set in under the lead.
    local w=$(( COLS < 80 ? COLS - 1 : 79 )) pad
    pad="$(printf '%*s' "${#lead}" "")"
    say "$(printf '%s\n' "$lead$text" | fold -s -w $(( w - ${#pad} )) | sed 's/ *$//' | sed "2,\$s/^/$pad/")"
    return
  fi
  wrap_hang "$lead" "$style" "$text" | sed "s/^/$PAD/"
  SCREEN+=($'\x02'"$lead"$'\x03'"$style"$'\x04'"$text")
}
wrap_hang() {
  local lead="$1" style="$2" text="$3" first=1 line out vis indent
  vis="$(printf '%s' "$lead" | sed 's/\x1b\[[0-9;]*m//g')"
  indent="$(printf '%*s' "${#vis}" "")"
  while IFS= read -r line; do
    line="${line% }"
    [ "$style" = dim ] && line="$(dim "$line")"
    if [ "$COLOUR" = 1 ]; then
      line="${line//(recommended)/$(c 32 "(recommended)")}"
      line="${line//(your last answer)/$(c 32 "(your last answer)")}"
    fi
    if [ "$first" = 1 ]; then out="$lead$line"; first=0; else out="$indent$line"; fi
    printf '%s\n' "$out"
  done < <(printf '%s\n' "$text" | fold -s -w $(( W - ${#vis} - 2 > 20 ? W - ${#vis} - 2 : 20 )))
}
# The step's lines at the width now: paragraphs and answers are wrapped again.
screen_lines() {
  local item rest
  for item in "${SCREEN[@]}"; do
    case "${item:0:1}" in
      $'\x01') wrap_para "${item:1}" ;;
      $'\x02') rest="${item:1}"; wrap_hang "${rest%%$'\x03'*}" "$(printf '%s' "${rest#*$'\x03'}" | sed 's/\x04.*//')" "${rest#*$'\x04'}" ;;
      *) printf '%s\n' "$item" ;;
    esac
  done
}
ok() { if [ "$FANCY" = 1 ]; then hang "  $(c 32 "✔") " "" "$1"; else say "Ready: $1"; fi; }
bad() { if [ "$FANCY" = 1 ]; then hang "  $(c 33 "✘") " "" "$1"; else say "Missing: $1"; fi; }
note() { if [ "$FANCY" = 1 ]; then hang "  $(c 33 "⚠") " "" "$1"; else say "Note: $1"; fi; }


header() {
  local title="$1" step="$2" inner=$(( W - 4 )) right="" left gap bar filled pct
  [ "$step" -gt 0 ] && [ "$step" -le "$STEPS" ] && right="step $step of $STEPS"
  left="$APP_NAME | $title"
  gap=$(( inner - ${#left} - ${#right} - 2 )); [ "$gap" -ge 1 ] || gap=1
  HEADER=("$(dim "┌$(rep ─ $(( inner + 2 )))┐")"
          "$(dim "│")  $(c 1 "$APP_NAME")$(dim " | ")$(accent "$title")$(rep " " "$gap")$(dim "$right")  $(dim "│")"
          "$(dim "└$(rep ─ $(( inner + 2 )))┘")")
  bar=$(( W - 8 ))  # with its two spaces either side and the percentage, the bar ends where the box does
  filled=$(( bar * (step - 1) / STEPS )); [ "$filled" -le "$bar" ] || filled=$bar
  pct=$(( 100 * (step - 1) / STEPS )); [ "$pct" -le 100 ] || pct=100
  HEADER+=("  $(c 36 "$(rep █ "$filled")")$(dim "$(rep ░ $(( bar - filled )))")  $(dim "$(printf '%3d%%' "$pct")")")
}

menu() {
  local line="" plain="" k label gap right keys
  right="${MENU_RIGHT:-Enter: recommended}"
  [ "${CAME_BACK:-0}" = 1 ] && [ -z "$MENU_RIGHT" ] && right="Enter: keep"
  read -ra keys <<< "$KEYS"  # read, not $KEYS, so ? is never taken as a file name pattern
  for k in "${keys[@]}"; do
    case "$k" in b) label="Back" ;; "?") label="Help" ;; f) label="Feedback" ;; r) label="Report this problem" ;;
      q|Ctrl+C) label="Stop" ;; *) continue ;; esac
    line+="$(accent "$k") $label   "; plain+="$k $label   "
  done
  [ $(( W - 4 - ${#plain} - ${#right} )) -ge 3 ] || right=""  # a narrow window: the keys matter more
  gap=$(( W - 4 - ${#plain} - ${#right} )); [ "$gap" -ge 1 ] || gap=1
  printf '\0337\033[%d;1H\033[2K\033[%d;%dH%s\033[%d;1H\033[2K\033[%d;%dH  %s%s%s\0338' $(( ROWS - 1 )) $(( ROWS - 1 )) \
    $(( L + 1 )) "$(dim "$(rep ─ "$W")")" "$ROWS" "$ROWS" $(( L + 1 )) "$line" "$(rep " " "$gap")" "$(dim "$right")"
}

# A cleared page: the heading box and progress bar at the top, the menu on the last two lines, and only the lines
# between them scrolling. Plain mode prints a heading line instead.
page() {
  STEP="$1"
  KEYS="? f q"; [ "$STEP" -gt "${FIRST_BACK:-1}" ] && KEYS="b ? f q"
  [ -n "$IN" ] || KEYS="Ctrl+C"  # drawn without questions (--yes): only stopping works
  MENU_RIGHT=""
  SCREEN=()
  if [ "$FANCY" = 0 ] && [ "$STEP" -gt "$STEPS" ]; then
    printf '\n== %s | %s\n' "$APP_NAME" "${TITLES[$STEP]}"
    return
  fi
  if [ "$FANCY" = 0 ]; then
    printf '\n== %s | %s (step %d of %d)\n' "$APP_NAME" "${TITLES[$STEP]}" "$STEP" "$STEPS"
    if [ -z "$IN" ]; then :
    elif [ "$STEP" -gt "${FIRST_BACK:-1}" ]; then echo "Type b to go back, ? for help, f to send feedback or q to stop."
    else echo "Type ? for help, f to send feedback or q to stop."; fi
    [ "${CAME_BACK:-0}" = 1 ] && echo "You came back to this step. Your last answer is in [brackets]: press Enter to keep it."
    return
  fi
  measure
  header "${TITLES[$STEP]}" "$STEP"
  draw_page
  say ""
  if [ "${CAME_BACK:-0}" = 1 ]; then
    note "You came back to this step. Your last answer is marked: press Enter to keep it."
    say ""
  fi
}
draw_page() {
  local i top=$(( ${#HEADER[@]} + 1 ))
  printf '\033[r\033[2J'
  for i in "${!HEADER[@]}"; do printf '\033[%d;%dH%s' $(( i + 1 )) $(( L + 1 )) "${HEADER[$i]}"; done
  printf '\033[%d;%dr' "$top" $(( ROWS - 2 ))
  menu
  printf '\033[%d;1H' "$top"
  DRAWN=1
}
# The window changed size: the same step, drawn again to fit, with its last lines and the question.
resized() {
  [ "$FANCY" = 1 ] && [ "$DRAWN" = 1 ] || return 0
  measure
  if [ "$COLS" -lt 60 ] || [ "$ROWS" -lt 20 ]; then
    # Too small for the frame: say so on a cleared window, and draw the step again when it is larger.
    printf '\033[r\033[2J\033[1;1H%s\n%s' "This window is too small for the boxed look. Make it at least 60 by 20." "$PROMPT"
    return 0
  fi
  header "${TITLES[$STEP]}" "$STEP"
  local keep=$(( ROWS - 2 - ${#HEADER[@]} - 1 ))
  draw_page
  # A step that draws itself (Run first's welcome, with the logo) does so again at the new size.
  if declare -F "redraw_step_$STEP" >/dev/null; then
    SCREEN=()
    say ""
    "redraw_step_$STEP"
    printf '\n%s%s' "$PAD" "$PROMPT"
    return
  fi
  screen_lines | tail -n "$keep" | sed "s/^/$PAD/"
  printf '%s%s' "$PAD" "$PROMPT"
}
# The handler only notes the change: the step is drawn again between read slices (tty_read), never inside the
# handler, where a second change of size could arrive while the first is still being drawn.
RESIZED=0
POPUP=0
trap 'RESIZED=1' WINCH

# Gives the whole window back: no scrolling area, the menu gone, the cursor under the last thing shown.
ECHO_WAS=""
finish() {
  [ -z "${KEEP:-}" ] || { kill "$KEEP" 2>/dev/null; KEEP=""; }
  [ -z "$ECHO_WAS" ] || { stty "$ECHO_WAS" < "${IN:-/dev/tty}" 2>/dev/null; ECHO_WAS=""; }
  if [ "$FANCY" = 1 ] && [ "$DRAWN" = 1 ]; then
    printf '\0337\033[r\033[%d;1H\033[2K\033[%d;1H\033[2K\0338\n' $(( ROWS - 1 )) "$ROWS"
    DRAWN=0
  fi
}
trap 'finish' EXIT
STOP_WORDS="Stopped. Nothing else was changed."
# A script run by another (Starboard's installer, run by its Run first script) can set STOP_FILE: when the person
# stops it (q or Ctrl+C), "stopped" is written there, so the caller can tell a person's own stop from a fault and
# does not show an error number for it. The script's err function writes its error number there itself.
stopped_by_person() { [ -z "${STOP_FILE:-}" ] || printf 'stopped\n' > "$STOP_FILE" 2>/dev/null || true; }
trap 'finish; echo; echo "$STOP_WORDS"; stopped_by_person; exit 130' INT

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
  left=$(( L + (W - bw) / 2 )); inner=$(( bw - 4 ))
  local keep=$(( ROWS - 2 - ${#HEADER[@]} )) shown=()
  mapfile -t shown < <(screen_lines | tail -n "$keep")
  printf '\033[r\033[2J'
  for line in "${HEADER[@]}" "${shown[@]}"; do
    [ "$row" -le $(( ROWS - 2 )) ] || break
    wrapped="$(printf '%s' "$line" | sed 's/\x1b\[[0-9;]*m//g')"
    printf '\033[%d;%dH%s' "$row" $(( L + 1 )) "$(c "2;90" "$wrapped")"; row=$(( row + 1 ))
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
  printf '\0337\033[%d;1H\033[2K\033[%d;%dH%s\033[%d;1H\033[2K\033[%d;%dH  %s %s\0338' $(( ROWS - 1 )) $(( ROWS - 1 )) $(( L + 1 )) \
    "$(dim "$(rep ─ "$W")")" "$ROWS" "$ROWS" $(( L + 1 )) "$(accent Enter)" "$key"
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
  local question="$1" default="$2" helptext="$3" title
  if [ -z "$IN" ] || [ "${ASK:-1}" = 0 ]; then ANSWER="$default"; return 0; fi  # --yes: never stop to ask
  # The menu's right side says what Enter does here.
  if [ "$FANCY" = 1 ]; then
    case "$question" in
      "Press Enter"*) [ "$MENU_RIGHT" = "Enter: carry on" ] || { MENU_RIGHT="Enter: carry on"; menu; } ;;
    esac
  fi
  # A question longer than the column is wrapped between words: its first lines go above, so the line the answer
  # is typed on fits.
  local room lead rest=() i
  lead="  $(accent "›") "
  if [ "$FANCY" = 1 ]; then room=$(( W - 6 )); else room=$(( COLS < 80 ? COLS - 2 : 78 )); lead=""; fi
  if [ "${#question}" -gt "$room" ]; then
    mapfile -t rest < <(printf '%s\n' "$question" | fold -s -w "$room" | sed 's/ *$//')
    printf '\n'
    for (( i = 0; i < ${#rest[@]} - 1; i++ )); do
      printf '%s%s%s\n' "$PAD" "$lead" "${rest[$i]}"; [ "$FANCY" = 1 ] && SCREEN+=("$lead${rest[$i]}")
      [ "$FANCY" = 1 ] && lead="    "
    done
    question="${rest[-1]}"
    PROMPT="$lead$question "; [ "$FANCY" = 1 ] || PROMPT="$question "
    printf '%s%s' "$PAD" "$PROMPT"
  else
    PROMPT="$lead$question "; [ "$FANCY" = 1 ] || PROMPT="$question "
    printf '\n%s%s' "$PAD" "$PROMPT"; [ "$FANCY" = 1 ] && SCREEN+=("")
  fi
  if tty_read; then ANSWER="$REPLY_LINE"; else ANSWER="q"; fi
  [ "$FANCY" = 1 ] && SCREEN+=("$PROMPT$ANSWER")
  ANSWER="$(printf '%s' "$ANSWER" | sed 's/^ *//; s/ *$//')"
  case "$ANSWER" in
    q|Q) finish; echo; echo "$STOP_WORDS Run it again at any time."; stopped_by_person; exit 1 ;;
    b|B)
      [ "$STEP" -gt "${FIRST_BACK:-1}" ] && return 10
      forget_prompt
      if [ "$STEP" -le 1 ]; then say "  This is the first step: there is nothing to go back to."
      else say "  Your answers are saved from here on. To change one, run this again when it has finished."; fi
      ask "$@"; return $? ;;
    "?")
      forget_prompt
      # The help's title is the question being asked, as it is written (HELP_TITLE when choose asks it).
      title="${HELP_TITLE:-$question}"; title="${title%:}"; title="${title% \[*\]}"
      popup "Help: $title" "$helptext"
      redraw_step
      ask "$@"; return $? ;;
    f|F) forget_prompt; feedback ""; redraw_step; ask "$@"; return $? ;;
    r|R)
      if [ -n "${LAST_PROBLEM:-}" ]; then forget_prompt; feedback "$LAST_PROBLEM"; redraw_step; ask "$@"; return $?; fi ;;
    "") ANSWER="$default" ;;
  esac
  return 0
}
# The prompt and the answer typed to it (?, f) leave the step's lines, so drawing it again shows the prompt once.
forget_prompt() {
  [ "$FANCY" = 1 ] || return 0
  local n=${#SCREEN[@]}
  [ "$n" -ge 2 ] && SCREEN=("${SCREEN[@]:0:$(( n - 2 ))}")
}
# The step exactly as it was, after help or feedback: the heading, the bar, the menu and its last lines.
redraw_step() {
  [ "$FANCY" = 1 ] || return 0
  measure
  header "${TITLES[$STEP]}" "$STEP"
  draw_page
  screen_lines | tail -n $(( ROWS - 3 - ${#HEADER[@]} )) | sed "s/^/$PAD/"
}

# Feedback, from any question: f, or r for Report this problem after a job failed. An app with its own feedback flow
# (the kinds, a question or two, the report, then a QR code, the link or a file: docs/TERMINAL.md section 7) defines
# app_feedback, which returns non-zero when it cannot run yet. Otherwise, or before the app is on the computer, the
# report is a link to type or copy. Nothing typed as an answer goes in either.
FEEDBACK_WHO="${FEEDBACK_WHO:-$APP_NAME}"
feedback() {
  local problem="$1" title link words
  if declare -F app_feedback >/dev/null && app_feedback "$problem"; then return 0; fi
  title="$FEEDBACK_WHO, step $STEP: ${TITLES[$STEP]}"
  [ -z "$problem" ] || title="$title: $problem"
  words="$APP_NAME $(printf '%s' "${APP_VERSION:-}" | tr -cd '0-9A-Za-z.-'), $(. /etc/os-release 2>/dev/null; printf '%s' "${PRETTY_NAME:-Linux}"), $(uname -m)."
  link="https://github.com/$ISSUES/issues/new?title=$(urlencode "$title")&body=$(urlencode "$words")&labels=feedback"
  popup "Send feedback" "Open this link on your phone or another computer to write your report on GitHub. It already says where you are and which system this is. Nothing you typed here is in it.

$link"
}
urlencode() {
  local s="$1" i ch out=""
  for (( i = 0; i < ${#s}; i++ )); do
    ch="${s:i:1}"
    case "$ch" in [A-Za-z0-9.~_-]) out+="$ch" ;; " ") out+="+" ;; *) out+="$(printf '%%%02X' "'$ch")" ;; esac
  done
  printf '%s' "$out"
}


# choose "question" default "help" "answer" "answer|what it means" ...: numbered answers, the default marked with
# a dot, the recommended one first and saying so. Sets CHOICE (1, 2 ...). Returns as ask does: 10 for Back, 11 to
# draw the step again.
CHOICE=""
choose() {
  local question="$1" default="$2" helptext="$3"; shift 3
  local opts=("$@") i name about mark
  say ""
  para "$question"
  if [ "$FANCY" = 1 ]; then
    case "${opts[$(( default - 1 ))]}" in
      *"(your last answer)"*) MENU_RIGHT="Enter: keep" ;;
      *) MENU_RIGHT="Enter: recommended" ;;
    esac
    menu
  fi
  for i in "${!opts[@]}"; do
    name="${opts[$i]%%|*}"; about=""
    [[ "${opts[$i]}" == *"|"* ]] && about="${opts[$i]#*|}"
    if [ "$FANCY" = 1 ]; then
      mark=" "; [ $(( i + 1 )) = "$default" ] && mark="$(accent "●")"
      hang "  $mark $(accent "$(printf '%2d' $(( i + 1 )))")  " "" "$name"
      [ -z "$about" ] || hang "        " dim "$about"
    else
      hang "  $(( i + 1 )). " "" "$name${about:+: $about}"
    fi
  done
  while :; do
    HELP_TITLE="$question"
    ask "Your choice [$default]:" "$default" "$helptext" || { local rc=$?; HELP_TITLE=""; return "$rc"; }
    HELP_TITLE=""
    if [[ "$ANSWER" =~ ^[0-9]+$ ]] && [ "$ANSWER" -ge 1 ] && [ "$ANSWER" -le "${#opts[@]}" ]; then
      CHOICE="$ANSWER"
      return 0
    fi
    say "  Type a number from 1 to ${#opts[@]}, ? for help or q to stop."
  done
}

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
  printf '\r\033[2K%s  %s %s  %s' "$PAD" "$(c 36 "$line")" "$(c 36 "${SPIN[$(( tick % 10 ))]}")" "$(printf '%s' "$name" | cut -c1-$(( W - bar - 8 )))"
  BAR_LINE="  $line  $name"
}
# The words beside a job's bar: its name, which job of how many, what it is doing now when the job says (JOB_DETAIL,
# such as "step 3 of 8" while Starboard builds), and the time so far, so a long job never looks stuck.
JOB_DETAIL=""
# JOB_COUNT names a function that prints how far a job has got, such as "5 of 12 installed": shown after the timer.
JOB_COUNT=""
JOB_START=0
DETAIL_NOW=""
job_words() {
  local name="$1" n="$2" of="$3" tick="$4" t=$(( SECONDS - JOB_START )) words
  if [ -n "$JOB_DETAIL" ] && [ $(( tick % 8 )) = 0 ]; then DETAIL_NOW="$("$JOB_DETAIL" 2>/dev/null)"; fi
  if [ -n "$JOB_COUNT" ] && [ $(( tick % 8 )) = 0 ]; then COUNT_NOW="$("$JOB_COUNT" 2>/dev/null)"; fi
  words="$name ($n of $of)"
  [ -z "$DETAIL_NOW" ] || words+=", $DETAIL_NOW"
  if [ "$t" -ge 60 ]; then words+=" · $(( t / 60 )) min $(printf '%02d' $(( t % 60 ))) s"; elif [ "$t" -ge 3 ]; then words+=" · $t s"; fi
  [ -z "$JOB_COUNT" ] || [ -z "$COUNT_NOW" ] || words+=" · $COUNT_NOW"
  printf '%s' "$words"
}

# A job is a shell command, or the name of one of the script's own functions (run in a subshell).
run_job() { if declare -F "$1" >/dev/null; then ( "$1" ); else bash -c "$1"; fi; }

# work "name" "command" n of: runs one job quietly. Returns the command's status.
work() {
  local name="$1" cmd="$2" n="$3" of="$4" pid tick=0 status
  printf '\n== %s\n$ %s\n' "$name" "$cmd" >> "$LOG"
  if [ "$FANCY" = 0 ]; then
    say "$name ($n of $of). Please wait..."
    # Keys pressed meanwhile are not shown (each Enter would push the words above off the screen) and are dropped.
    ECHO_WAS="$(stty -g < "${IN:-/dev/tty}" 2>/dev/null)" && stty -echo < "${IN:-/dev/tty}" 2>/dev/null
    # Never silent for long (TERMINAL.md): "Still working" every 2 minutes, with the count when the job has one.
    run_job "$cmd" >> "$LOG" 2>&1 < /dev/null &
    pid=$!; JOB_START=$SECONDS
    while kill -0 "$pid" 2>/dev/null; do
      sleep 1
      local t=$(( SECONDS - JOB_START ))
      if [ "$t" -gt 0 ] && [ $(( t % ${STILL_EVERY:-120} )) = 0 ]; then
        local more=""
        if [ -n "$JOB_COUNT" ]; then COUNT_NOW="$("$JOB_COUNT" 2>/dev/null)"; [ -z "$COUNT_NOW" ] || more=", $COUNT_NOW"; fi
        if [ -n "$JOB_DETAIL" ]; then DETAIL_NOW="$("$JOB_DETAIL" 2>/dev/null)"; [ -z "$DETAIL_NOW" ] || more+=", $DETAIL_NOW"; fi
        say "Still working: $name ($(( t / 60 )) min$more)."
      fi
    done
    wait "$pid"; status=$?
    if [ -n "$ECHO_WAS" ]; then
      while read -r -t 0.01 -n 1000 _ < "${IN:-/dev/tty}" 2>/dev/null; do :; done
      stty "$ECHO_WAS" < "${IN:-/dev/tty}" 2>/dev/null; ECHO_WAS=""
    fi
    if [ "$status" = 0 ]; then say "Done: $name."; else say "Did not finish: $name."; fi
    return "$status"
  fi
  run_job "$cmd" >> "$LOG" 2>&1 < /dev/null &
  pid=$!
  JOB_START=$SECONDS; DETAIL_NOW=""
  # While a job runs, only Ctrl+C works: the menu says so.
  local keys_were="$KEYS" right_were="$MENU_RIGHT"
  KEYS="Ctrl+C"; MENU_RIGHT="Please wait"; menu
  # Keys pressed while the bar moves (Enter, out of impatience) would print new lines under it and repeat the bar
  # down the window: they are not shown until the job ends, and dropped then.
  ECHO_WAS="$(stty -g < "${IN:-/dev/tty}" 2>/dev/null)" && stty -echo < "${IN:-/dev/tty}" 2>/dev/null
  while kill -0 "$pid" 2>/dev/null; do
    if [ "$RESIZED" = 1 ]; then RESIZED=0; PROMPT=""; resized; fi
    frame "$n" "$of" "$(job_words "$name" "$n" "$of" "$tick")" "$tick"
    # A job can set the terminal back to showing keys (apt and Docker's installer do): hide them again.
    if [ -n "$ECHO_WAS" ] && [ $(( tick % 8 )) = 0 ]; then stty -echo < "${IN:-/dev/tty}" 2>/dev/null; fi
    tick=$(( tick + 1 ))
    sleep 0.12
  done
  wait "$pid"; status=$?
  if [ -n "$ECHO_WAS" ]; then
    while read -r -t 0.01 -n 1000 _ < "${IN:-/dev/tty}" 2>/dev/null; do :; done
    stty "$ECHO_WAS" < "${IN:-/dev/tty}" 2>/dev/null; ECHO_WAS=""
  fi
  KEYS="$keys_were"; MENU_RIGHT="$right_were"; menu
  if [ "$status" = 0 ]; then
    printf '\r\033[2K'
    ok "$name"
    DONE_JOBS+=("$name")
  else
    # The bar stays where it stopped, marked, so the problem below it is about this job.
    frame "$n" "$of" "$name ($n of $of): did not finish" 0
    printf '\n'
    SCREEN+=("$BAR_LINE")
  fi
  return "$status"
}

# A job failed and the person chose Try again: the page is drawn afresh, with the jobs already done ticked and one
# new bar for the job tried again, so bars never pile up under one another.
jobs_page() {
  local step="$1" intro="$2" done_job
  page "$step"
  para "$intro"
  say ""
  for done_job in "${DONE_JOBS[@]}"; do ok "$done_job"; done
}

# A job did not finish: the problem in plain words under its bar, with the error number, then Try again
# (recommended), Show the details or Stop. job_failed "name" "why" "what to try" "code": returns 0 to try again,
# stops the script otherwise.
job_failed() {
  local name="$1" why="$2" tip="$3" code="$4"
  say ""
  note "$name did not work. Error $code."
  para "$why${tip:+ $tip}"
  printf 'Error %s while %s\n' "$code" "${name,}" >> "$LOG"
  [ -z "$IN" ] || [ "${ASK:-1}" = 0 ] && { finish; echo "The details are in $LOG"; err "$code"; exit 1; }
  LAST_PROBLEM="Error $code: $name did not work. $why"
  local keys_were="$KEYS"
  KEYS="${KEYS/f/f r}"
  [ "$FANCY" = 1 ] && menu
  while :; do
    choose "What do you want to do?" 1 \
"Try again runs the same job again. Nothing that already worked is undone.

Show the details shows the last lines the job printed, which help if you ask someone for help or report a problem.

Report this problem makes a report with the error already in it, to send from your phone or as a link.

Stop leaves this computer as it is now. Run it again at any time: it carries on from what is missing." \
      "Try again (recommended)" "Show the details" "Report this problem" "Stop" || continue  # Back: ask again
    case "$CHOICE" in
      1) KEYS="$keys_were"; LAST_PROBLEM=""; return 0 ;;
      2) say ""; say "$(dim "$(tail -n 25 "$LOG" | fold -s -w $(( W - 6 )) | tail -n 30 | sed 's/^/    /')")"; say ""; para "The whole log is in $LOG" ;;
      3) forget_prompt; feedback "$LAST_PROBLEM"; redraw_step ;;
      4) finish; echo; echo "Stopped. The details are in $LOG"; err "$code"; exit 1 ;;
    esac
  done
}

# A card: a title, then rows of a label and a value, in a box the column's width. A long value wraps inside it.
CARD_W=0
card() {
  local title="$1"
  if [ "$FANCY" = 0 ]; then say "$title"; [ $# -lt 3 ] || card_row "$2" "$3"; return; fi
  CARD_W=$(( W - 4 ))
  say "  $(c 36 "╭─ $title ")$(c 36 "$(rep ─ $(( CARD_W - ${#title} - 4 )))╮")"
  [ $# -lt 3 ] || card_row "$2" "$3"
}
card_row() {
  local label="$1" value="$2" first=1 piece width
  if [ "$FANCY" = 0 ]; then say "$label: $value"; return; fi
  width=$(( CARD_W - 20 ))
  while IFS= read -r piece; do
    piece="${piece% }"
    if [ "$first" = 1 ]; then
      say "  $(c 36 "│") $(dim "$(printf '%-18s' "$label")")$piece$(rep " " $(( width - ${#piece} )))$(c 36 "│")"; first=0
    else
      say "  $(c 36 "│") $(printf '%-18s' "")$piece$(rep " " $(( width - ${#piece} )))$(c 36 "│")"
    fi
  done < <(printf '%s\n' "$value" | fold -s -w "$width")
}
card_end() { [ "$FANCY" = 0 ] || say "  $(c 36 "╰$(rep ─ $(( CARD_W - 1 )))╯")"; }
