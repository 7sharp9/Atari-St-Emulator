#!/bin/bash
# The creature gates from fresh captures (each script captures its own entry snapshot from scratchpad/archipelagos/m2.snap).
#   gate_creature.py 300: callcap states, model == emulator 300/300 (poked states); controls: add a bug name
#     (order, shift, lim5, nofoot, noclobber) as the last argument, 12 to 184 of 300
#   gate_creature_idle.py 40: watch-log gate, 2/2 natural events, 40/40 poked events; controls order/lim5/shift lower
d=$(cd "$(dirname "$0")" && pwd)
cd "$d" || exit 1
uv run python gate_creature.py 300
uv run python gate_creature_idle.py 40
