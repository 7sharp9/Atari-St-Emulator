#!/bin/bash
# All Archipelagos gates from fresh captures. Needs py/run_drive.sh first (it writes the snapshots, about a minute).
#   island map: model vs the game's 64K map, five islands, 65536/65536 each; control (RNG step changed) lower
#   $16166: 9/9 parameter fields for N=150 and N=4321; control 2/9
#   RNG $16622: s = 5s + 1, 11792/11792 successive seeds; control 0
d=$(cd "$(dirname "$0")" && pwd)
"$d/capture_islands.sh" || exit 1
"$d/gate_islands_only.sh"
"$d/gate_params.sh"
uv run python "$d/gate_rng.py"
