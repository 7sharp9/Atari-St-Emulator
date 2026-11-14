#!/bin/bash
# $16166 gate: the parameter block it computes for N = 150 and 4321, modelled from N alone (9 fields each),
# then with the seed constant changed (BUG=1).
d=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$d/tools/rdis.py" ] && [ "$d" != / ]; do d=$(dirname "$d"); done
cd "$d" || exit 1
W=scratchpad/archipelagos
uv run python reversing/archipelagos/py/island_params.py $W/gen/ent_150.snap $W/gen/ent_4321.snap | cut -c1-40
BUG=1 uv run python reversing/archipelagos/py/island_params.py $W/gen/ent_150.snap $W/gen/ent_4321.snap | cut -c1-40
