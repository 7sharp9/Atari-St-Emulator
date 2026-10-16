#!/bin/bash
# w58054.sh [snap] [windows]: natural census for $58054. watch $58052..$58055 (the word and the word below) over
# `windows` x 100M steps (default 6) of pm142/rand1.snap with a hits table per window: the direct readers and writers of
# $58054 ($2602 $2706 $285c $1acb8 $1acd2 $1acdc $1acf6 $1ad10 $126da), the indexed candidates whose base is below it
# ($58042 table: $253e $3d02 $685a $6ae4; $58016+6*side: $22b4 $26bc $70e2; $57f68+D0: $9b9e) and the tick $6522
# (liveness). Writes $PM_WORK/pile/w58054/out.txt (hits) and watch.txt (WATCH lines).
R=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$R/tools/rdis.py" ]; do R=$(dirname "$R"); done
cd "${M68000_ROOT:-$R}" || exit 1
W=${PM_WORK:-scratchpad/pm162}/pile/w58054; mkdir -p "$W"; SNAP=${1:-scratchpad/pm142/rand1.snap}; N=${2:-6}
A="2602 2706 285c 1acb8 1acd2 1acdc 1acf6 1ad10 126da 253e 3d02 685a 6ae4 22b4 26bc 70e2 9b9e 6522"
{
  echo "disk scratchpad/powermonger.st"; echo "watch 58052 4"; echo "m 58040 64"
  for i in $(seq 1 "$N"); do echo "hits 100000000 $A"; echo "m 58040 64"; done
  echo q
} | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl > "$W/out.txt" 2> "$W/watch.txt"
