#!/bin/bash
# chain_waves.sh <game numbers...>: for each chain game (scratchpad/virus/chain/long100/starts/main_gNNN.snap, nothing poked) stop at
# the end of $20e74 ($20f80) four times (the builds of counters 1..4; counter 0 is built before the start snapshot), snapshot each,
# then run pool_check.py on all four and virus_terrain.py on the counter-4 build (landscape 1).  About 8 minutes per game that
# reaches wave 4 (014, 045, 057, 074, 076, 079, 093); not part of gate_landscape.sh.  Output: $VIRUS_WORK/landscape/chain/.
d=$(cd "$(dirname "$0")" && pwd); A=$d; while [ ! -f "$d/tools/rdis.py" ]; do d=$(dirname "$d"); done; cd "$d" || exit 1
W=${VIRUS_WORK:-scratchpad/virus}; O=$W/landscape/chain; mkdir -p "$O"
for g in "$@"; do
  n=$(printf %03d $g); S=$W/chain/long100/starts/main_g$n.snap
  {
  for i in 1 2 3 4; do echo "bp 20f80 700000000"; echo "snap $O/g${n}_$i.snap"; done
  echo q
  } | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$S" repl > "$O/g$n.out" 2>&1
  for i in 1 2 3 4; do uv run python -I $A/pool_check.py $O/g${n}_$i.snap; done
  uv run python -I reversing/virus/py/virus_terrain.py $O/g${n}_4.snap | tail -1 | sed "s/^/g$n counter-4 terrain: /"
done
