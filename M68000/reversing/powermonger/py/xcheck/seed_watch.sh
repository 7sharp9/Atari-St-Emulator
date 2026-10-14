#!/usr/bin/env bash
# Does the RNG long `_seed` $2df84 (the tree birds' jitter, port/SPEC.md "Birds over a tree")
# move in long play, and who moves it?
#   1. watch $2df84 over STEPS steps from rand1 (Play Random Land, two idle player captains);
#   2. the first NBP calls of $12c9a by return address;
#   3. the tick $6522 and $12c9a per 25M-step window from 600M, to bound the end of play.
# `watch` prints the snapshot's cumulative step counter, not steps into the run:
# the `hits` over the first 5M steps runs under the watch, and seed_bursts.py lines its first draw up with the first watched one.
# Usage: seed_watch.sh [STEPS=1500000000] [NBP=80]; output in $PM_WORK/seed (default scratchpad/pm161/seed).
set -e
d=$(cd "$(dirname "$0")" && pwd)
while [ ! -f "$d/tools/rdis.py" ]; do d=$(dirname "$d"); done
cd "$d"
STEPS=${1:-1500000000}; NBP=${2:-80}
OUT=${PM_WORK:-scratchpad/pm161}/seed; mkdir -p "$OUT"
SNAP=scratchpad/pm142/rand1.snap
run() { ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl; }

printf 'disk scratchpad/powermonger.st\nm 2df84 4\nwatch 2df84 4\nhits 5000000 12c9a\ns %s\nm 2df84 4\nq\n' $((STEPS - 5000000)) \
  | run > "$OUT/watch_out.txt" 2> "$OUT/watch.txt" &
{ echo 'disk scratchpad/powermonger.st'
  for i in $(seq "$NBP"); do echo 'bp 12c9a 400000000'; echo 'bt 1'; echo 's 1'; done; echo q; } \
  | run > "$OUT/callers.txt" 2>&1 &
{ echo 'disk scratchpad/powermonger.st'; echo 's 600000000'
  for i in $(seq 8); do echo 'hits 25000000 6522 12c9a'; done; echo q; } \
  | run > "$OUT/end.txt" 2>&1 &
wait

echo "callers of \$12c9a (first $NBP):"; grep "return address (A7)" "$OUT/callers.txt" | sort | uniq -c
echo "per 25M-step window from 600M:"; grep -A2 "hits over" "$OUT/end.txt" | grep '\$0'
python3 "$(dirname "$0")/seed_bursts.py" "$OUT/watch_out.txt" "$OUT/watch.txt"
