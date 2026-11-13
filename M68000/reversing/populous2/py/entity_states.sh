#!/bin/bash
# Populous II: per-state call counts of the entity update $2309a over 200 VBLs (2.4M steps,
# 29 game ticks) from p2_game_60m, then the occupant-list check on the end state.
# README "Objects and entities". Run from M68000/.
#   $2309a update_entities, $24a92 per-entity pre-dispatch call, $23164 state 2, $233b4 state 4,
#   $23580 state 6, $24f3a state 2's test, $25168 called from state 6.
set -e
OUT=${1:-scratchpad/populous2/entity_states}
mkdir -p "$OUT"
#   $230fa first dispatch, $23100 re-dispatch entry, $233d8 state-4 expiry, $23180 $24f3a returned 0,
#   $233e2 state-4 move path.
printf 'hits 2400000 2309a 230fa 23100 24a92 23164 23180 233b4 233d8 233e2 23580 24f3a 25168\nsnap %s/end.snap\nq\n' "$OUT" |
  dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/populous2/anchors/p2_game_60m.snap repl \
  > "$OUT/hits.log" 2>&1
grep -A13 '^--- hits over' "$OUT/hits.log"
echo "== start"; uv run python reversing/populous2/py/walkers.py scratchpad/populous2/anchors/p2_game_60m.snap | head -4
echo "== end";   uv run python reversing/populous2/py/walkers.py "$OUT/end.snap" | head -4
