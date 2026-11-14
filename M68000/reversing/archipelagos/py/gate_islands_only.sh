#!/bin/bash
# Island gates: py/island_model.py against the game's map at the $15b8e return, five islands, then the same
# with the model's RNG step changed (BUG=1). Needs py/capture_islands.sh first.
d=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$d/tools/rdis.py" ] && [ "$d" != / ]; do d=$(dirname "$d"); done
cd "$d" || exit 1
W=scratchpad/archipelagos; P="uv run python reversing/archipelagos/py"
for BUG in 0 1; do export BUG
 echo "== model BUG=$BUG"
 $P/island_model.py $W/isl/ent1.snap $W/isl/exit1.snap | grep cells
 $P/island_model.py $W/isl/ent_defaults.snap $W/isl/exit_defaults.snap | grep cells
 $P/island_model.py $W/isl/ent_setB.snap $W/isl/exit_setB.snap | grep cells
 $P/island_model.py $W/gen/ent_150.snap $W/gen/exit_150.snap | grep cells
 $P/island_model.py $W/gen/ent_4321.snap $W/gen/exit_4321.snap | grep cells
done
