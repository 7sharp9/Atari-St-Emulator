#!/bin/bash
# The enemy shot ($22e38 fire, $203f0 spawn, $20310 handler) as a model against natural captures of waves 1 to 4
# (reversing/virus/behaviours.md "The enemy shot").  Captures: cap_eshot.py from the pursuer corpus snapshots
# ($VIRUS_SNAPS, default scratchpad/virus/pursuer/snaps/), about 30 s each, 12 of them, one emulator at a time;
# FRESH=0 reuses the saved ones in $VIRUS_WORK/caps (default scratchpad/virus/eshot/caps).
d="$(cd "$(dirname "$0")" && pwd)"; r="$d"; while [ ! -f "$r/tools/rdis.py" ]; do r="$(dirname "$r")"; done
cd "$r" || exit 1
W="${VIRUS_WORK:-scratchpad/virus}/eshot"
[ "${FRESH:-1}" = 1 ] && { echo "== captures"; "$d/run_caps.sh"; }
echo "== gate"; uv run python "$d/gate_eshot.py" $W/caps/*.json
for c in mshift nomuzzle jit13 draw4 life21 box50 cost332 nograv far180; do
  echo "== control $c"; uv run python "$d/gate_eshot.py" $W/caps/*.json --control $c | grep -E 'MISMATCH|^== control'
done
