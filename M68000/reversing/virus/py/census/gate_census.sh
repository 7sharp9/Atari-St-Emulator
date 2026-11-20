#!/bin/bash
# Bounded census gate (about 3 minutes): traces ATARI_TRACE_EVENTS over
#   (a) attract game 050 from chain/long100/starts/main_g050.snap, 50M steps (5 chunks; $32a50 goes 0 -> 1 in the last),
#   (b) the game-over path from demo/death/long7.snap to the next $230c0 (49,998,717 steps, measured with `bp 230c0`),
# reduces them with reduce_evt.py and prints the call-target count, the count named in virus.sym and the coverage line.
# The control reruns the aggregation with an empty .sym: named must drop to 0.
# The full 1.23G-step run is not a gate: see README "Which code runs" for its commands.
HERE="$(cd "$(dirname "$0")" && pwd)"
d="$HERE"; while [ ! -f "$d/tools/rdis.py" ]; do d="$(dirname "$d")"; done
cd "$d" || exit 1
W="${VIRUS_WORK:-$d/scratchpad/virus}/census/gate"
rm -rf "$W"; mkdir -p "$W"
export CENSUS_DIR="$W"
PY=.venv/bin/python
V="${VIRUS_WORK:-scratchpad/virus}"
bash "$HERE/run_chunks.sh" g050 scratchpad/virus/chain/long100/starts/main_g050.snap 5 10000000 || exit 1
bash "$HERE/run_chunks.sh" over scratchpad/virus/demo/death/long7.snap 1 49998717 || exit 1
echo "== window: g050 50M steps + over 49,998,717 steps"
$PY "$HERE/aggregate.py" | grep -E '^(game-code|ALL)'
echo "== control: empty .sym"
: > "$W/empty.sym"
CENSUS_SYM="$W/empty.sym" $PY "$HERE/aggregate.py" | grep -E '^game-code'
