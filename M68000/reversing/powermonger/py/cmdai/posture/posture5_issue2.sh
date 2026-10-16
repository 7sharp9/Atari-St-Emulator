#!/usr/bin/env bash
# The second natural posture-5 issue on rand1 (posture_watch.sh window 14, $67a2 at +1,498,838 = run step 651,498,838):
# stop at $67a2 and $67b0 (registers, $57fec, the group's posture/prev state/target/owner), then count the 10 posture
# readers, the invent executor $6c48, $6522 and the overwriter $6638 over the 267,880 steps posture held 5 (to the
# $6638 write at cumulative step 1,480,520,000), and print the posture word after.
# Output: ${PM_WORK:-scratchpad/pm162}/posture/issue2/out.txt
set -e
HERE=$(cd "$(dirname "$0")" && pwd); d=$HERE
while [ ! -f "$d/tools/rdis.py" ]; do d=$(dirname "$d"); done
cd "$d"
OUT=${PM_WORK:-scratchpad/pm162}/posture/issue2; mkdir -p "$OUT"
# side 3 group 0: A1 = $518ec; posture 136 = $51974, prev state 268 = $519f8, target 100 = $51950, owner 28 = $51908
printf '%s\n' 'disk scratchpad/powermonger.st' 's 651400000' 'bp 67a2 2000000' 'm 57fec 2' 'm 51974 2' 'm 519f8 2' 'm 51950 2' 'm 51908 2' 'bp 67b0 100' \
  'hits 267870 3110 644c 53c0 90fe c77e 35b4 3d52 150f2 1ce6 6cc6 6c48 6522 6638' 'm 51974 2' 's 200' 'm 51974 2' 'q' \
 | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/pm142/rand1.snap repl > "$OUT/out.txt" 2>&1
