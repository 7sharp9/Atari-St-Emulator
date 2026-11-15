#!/bin/bash
# Gate battle_god: later conquest battles reached by one poke of the battle number before the CONQUEST GAME click.
# Builds the start snapshots of battles 0, 10, 260 and 485 (battle_census.sh with a 1-step census), checks the
# CONQUEST.PAK record decode against them (conquest_records.py), then the computer god's model against callcap on
# the first 100 natural ticks of battle 485 (kind-4 powers) and of battle 260 (the magnet's command 8).
# Control: kind 4 with the search radius 3 fails the one kind-4 tick of battle 485.
# Run from M68000/:  bash reversing/populous2/py/god/gate_battle.sh [outdir]
set -e
d=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$d/tools/rdis.py" ] && [ "$d" != / ]; do d=$(dirname "$d"); done; cd "$d"
OUT=${1:-scratchpad/populous2/battle_gate}
P=reversing/populous2/py/god
bash $P/battle_census.sh "$OUT" 1 0 10 260 485 > "$OUT.census.out" 2>&1
uv run python $P/conquest_records.py "$OUT"/b{0,10,260,485}_start.snap
for n in 485 260; do
  echo "battle $n:"
  uv run python $P/god_gate.py "$OUT/b${n}_start.snap" 100 2>/dev/null | grep -E '^states|^paths'
done
echo "control radius (kind 4 searches 3 cells), battle 485:"
uv run python $P/god_gate.py "$OUT/b485_start.snap" 100 --control radius 2>/dev/null | grep -E '^states'
