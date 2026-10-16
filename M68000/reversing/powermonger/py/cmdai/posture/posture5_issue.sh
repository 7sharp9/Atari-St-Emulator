#!/usr/bin/env bash
# The natural posture-5 issue on rand1: run to just before it (89.5M steps in, from posture_watch.sh's $67a2 hit at
# window 2 + 39,562,319), stop at the rng arm $67a2, print the registers, $57fec and the group's posture, prev state
# (268) and target (100), step to the write $67b0 and print D1; then count the posture readers over the 176,100 steps
# the posture held (to the $65c8 rewrite at 918,491,706) and print the posture word at the end.
# Output: ${PM_WORK:-scratchpad/pm162}/posture/issue/out.txt
set -e
HERE=$(cd "$(dirname "$0")" && pwd); d=$HERE
while [ ! -f "$d/tools/rdis.py" ]; do d=$(dirname "$d"); done
cd "$d"
OUT=${PM_WORK:-scratchpad/pm162}/posture/issue; mkdir -p "$OUT"
printf '%s\n' 'disk scratchpad/powermonger.st' 's 89500000' 'bp 67a2 2000000' 'm 57fec 2' 'm 51838 2' 'm 518bc 2' 'm 51814 2' 'm 517cc 2' 'bp 67b0 100' \
  'hits 176100 3110 644c 53c0 90fe c77e 35b4 3d52 150f2 1ce6 6cc6 6c48 6522 65c8' 'm 51838 2' 'q' \
 | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/pm142/rand1.snap repl > "$OUT/out.txt" 2>&1
