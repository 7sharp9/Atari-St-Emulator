#!/usr/bin/env bash
# Every write to a group posture word (group +136 in the side-record frame = 60(A3) in the group-offset frame,
# word k of side s at $51538 + s*$13c + 136 + 2k) over a long natural run, with per-window liveness of the
# commander tick $6522 and hit counts of every posture writer found by the whole-image scan (py/raw_scan.py):
# $2466 $2760 $35e4 $65c8 $65f4 $6638 $666c $668c $672e $67b0, plus $67a2 (the follow-up table's rng arm).
# The watch covers $515c0..$51abb (sides 0..4) and is filtered to offsets 134..147 of the side record.
# Usage: posture_watch.sh [SNAP=scratchpad/pm142/rand1.snap] [WINDOWS=14] [WIN=50000000]
# Output: ${PM_WORK:-scratchpad/pm162}/posture/run/{out.txt,posture_writes.txt,watch_count.txt}
set -e
HERE=$(cd "$(dirname "$0")" && pwd); d=$HERE
while [ ! -f "$d/tools/rdis.py" ]; do d=$(dirname "$d"); done
cd "$d"
SNAP=${1:-scratchpad/pm142/rand1.snap}; NW=${2:-14}; WIN=${3:-50000000}
OUT=${PM_WORK:-scratchpad/pm162}/posture/run; mkdir -p "$OUT"
{ echo 'disk scratchpad/powermonger.st'
  echo 'm 515c0 12'; echo 'm 516fc 12'; echo 'm 51838 12'; echo 'm 51974 12'; echo 'm 51ab0 12'
  echo 'watch 515c0 1276'
  for i in $(seq "$NW"); do echo "hits $WIN 6522 2466 2760 35e4 65c8 65f4 6638 666c 668c 672e 67a2 67b0"; done
  echo 'm 515c0 12'; echo 'm 516fc 12'; echo 'm 51838 12'; echo 'm 51974 12'; echo 'm 51ab0 12'
  echo q; } \
 | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl 2>&1 >"$OUT/out.txt" \
 | python3 "$HERE/posture_filter.py" "$OUT/watch_count.txt" > "$OUT/posture_writes.txt"
