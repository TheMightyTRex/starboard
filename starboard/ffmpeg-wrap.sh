#!/bin/bash
# Live TV fix for Jellyfin (DASH-169, 8 November 2026). FFmpeg 7.1 and later refuse HLS segments whose address has
# no media file ending (ad-tracking links on Samsung TV Plus and Amagi channels such as U&Laughs). For Live TV inputs
# only, add -extension_picky 0. Other inputs (library files, On demand links) are untouched.
# Starboard's Install apps guide writes this into Jellyfin's settings folder as ffmpeg-wrap/ffmpeg, with ffprobe as a
# link to it, and sets FFMPEG_PATH to it in data/stack/compose.yaml. Remove that line to go back to plain FFmpeg.
REAL=/usr/lib/jellyfin-ffmpeg/$(basename "$0")
live() { [[ "$1" =~ ^https?:// && ( "$1" == *.m3u8* || "$1" == *jmp2.uk/* || "$1" == */iptv/* ) ]]; }
# ffprobe ignores options a format does not use, so add it once at the front.
if [[ "$(basename "$0")" == ffprobe ]]; then
  for a in "$@"; do live "$a" && exec "$REAL" -extension_picky 0 "$@"; done
  exec "$REAL" "$@"
fi
args=(); added=0; prev=""
for a in "$@"; do
  if [[ "$prev" == "-i" ]] && live "$a"; then
    unset 'args[${#args[@]}-1]'; args+=(-extension_picky 0 -i); added=1
  fi
  args+=("$a"); prev="$a"
done
if [[ $added == 0 ]]; then exec "$REAL" "$@"; fi
start=$SECONDS
"$REAL" "${args[@]}"; rc=$?
# Option not found (exit 8) straight away: the input was not HLS after all, so run it as given.
if [[ $rc == 8 && $((SECONDS - start)) -lt 5 ]]; then exec "$REAL" "$@"; fi
exit $rc
