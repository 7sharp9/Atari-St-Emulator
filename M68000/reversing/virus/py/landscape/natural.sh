#!/bin/bash
# natural.sh [out dir]: game 050 of the unpoked 100-game chain (py/chain/chain.py: scratchpad/virus/chain/long100/starts/main_g050.snap,
# which reaches counter 5), nothing poked.  `watch 32a4c 6` logs every write of the selector words $32a4c/$32a4e and the wave
# counter $32a50.  Stops: wave end $20fb4 (end_N.snap), end of the pay loop $210e8 (after_N.snap) and end of $20e74 $20f80
# (built_N.snap) for the five wave ends N = 0..4 (counters 1..5; N = 3 builds landscape 1).  About 3.5 minutes.
# Output: <out dir>/out.txt (default $VIRUS_WORK/landscape/natural) and the snapshots.
d=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$d/tools/rdis.py" ]; do d=$(dirname "$d"); done; cd "$d" || exit 1
W=${VIRUS_WORK:-scratchpad/virus}; O=${1:-$W/landscape/natural}; mkdir -p "$O"
S=$W/chain/long100/starts/main_g050.snap
{
echo "watch 32a4c 6"
for i in 0 1 2 3 4; do
  echo "bp 20fb4 700000000"; echo "snap $O/end_$i.snap"
  echo "bp 210e8 40000000"; echo "snap $O/after_$i.snap"
  echo "bp 20f80 40000000"; echo "snap $O/built_$i.snap"
done
echo q
} | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$S" repl > "$O/out.txt" 2>&1
echo "natural.sh rc=$? (watch lines: $(grep -c '^WATCH' "$O/out.txt"))"
