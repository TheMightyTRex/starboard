#!/usr/bin/env bash
# Stops a commit that would publish private details: home network addresses, dynamic DNS names, email
# addresses, API keys or private keys. Also checks the words in .private-words (one per line, ignored by git),
# where you list your own server name, domain, user name and so on.
#
#   tools/check-private.sh            check every tracked file
#   tools/check-private.sh --staged   check what is about to be committed (used by the pre-commit hook)
set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

if [ "${1:-}" = "--staged" ]; then
  grep_cmd=(git grep --cached -I -n -E)
else
  grep_cmd=(git grep -I -n -E)
fi

# The checker itself and the tests contain the patterns on purpose.
exclude=(-- . ':!tools/check-private.sh' ':!tests/' ':!web/fonts/')
found=0

# The made-up examples the help centre uses (docs/help/HOW-THIS-HELP-IS-WRITTEN.md, rule 14). They are taken out
# of a line before the check, so anything else on that line is still caught, and .private-words below still
# checks them: if one of these is ever a real address of yours, list it there.
EXAMPLES='192\.168\.1\.2[01]([^0-9]|$)|sam@starboard-pi\.local'

check() {
  local label="$1" pattern="$2"
  local hits
  hits="$("${grep_cmd[@]}" "$pattern" "${exclude[@]}" 2>/dev/null | grep -v -E 'noreply@anthropic\.com|users\.noreply\.github\.com' \
    | while IFS= read -r line; do printf '%s\n' "$line" | sed -E "s/$EXAMPLES/ /g" | grep -q -E "$pattern" && printf '%s\n' "$line"; done || true)"
  if [ -n "$hits" ]; then
    printf '\n%s:\n%s\n' "$label" "$hits"
    found=1
  fi
}

check "Home network address" '(^|[^0-9.])(192\.168\.[0-9]{1,3}\.[0-9]{1,3}|10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|172\.(1[6-9]|2[0-9]|3[01])\.[0-9]{1,3}\.[0-9]{1,3}|100\.(6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\.[0-9]{1,3}\.[0-9]{1,3})([^0-9]|$)'
check "Dynamic DNS or tunnel name" '[a-z0-9-]+\.(ddns\.net|duckdns\.org|no-ip\.[a-z]+|hopto\.org|zapto\.org|ts\.net|ngrok\.io|myfritz\.net)'
check "Email address" '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
check "Possible API key (32 hex characters)" '(^|[^0-9a-fA-F])[0-9a-f]{32}([^0-9a-fA-F]|$)'
check "Possible token" '(ghp_|github_pat_|xox[bap]-|sk-[A-Za-z0-9]{20})'
check "Private key" 'BEGIN [A-Z ]*PRIVATE KEY'

# Public names that may appear even though they contain a private word: the project's GitHub account and the
# author name (in links, image addresses and the licence). They are taken out of a line before the check, so
# anything else on that line is still caught.
PUBLIC_NAMES='[Tt][Hh][Ee][Mm][Ii][Gg][Hh][Tt][Yy][Tt][Rr][Ee][Xx]([Uu][Kk])?'

if [ -f .private-words ]; then
  while IFS= read -r word; do
    [ -z "$word" ] || [ "${word#\#}" != "$word" ] && continue
    pattern="$(printf '%s' "$word" | sed 's/[][\.*^$(){}?+|/]/\\&/g')"
    hits="$("${grep_cmd[@]}" -i "$pattern" "${exclude[@]}" 2>/dev/null | while IFS= read -r line; do
      printf '%s\n' "$line" | cut -d: -f3- | sed -E "s/$PUBLIC_NAMES//g" | grep -q -i -E "$pattern" && printf '%s\n' "$line"
    done || true)"
    if [ -n "$hits" ]; then
      printf '\n%s:\n%s\n' "Private word from .private-words" "$hits"
      found=1
    fi
  done < .private-words
fi

if [ "$found" = 1 ]; then
  printf '\nStopped: remove the details above (or put them in ./data or .env, which git ignores).\n' >&2
  exit 1
fi
echo "No private details found."
