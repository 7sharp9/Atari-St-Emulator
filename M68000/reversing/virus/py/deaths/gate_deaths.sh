#!/bin/bash
# Why the demo pilot loses each life (demo.md, "Why the demo loses its lives").  Fresh census of games 1 and 3 from
# scratchpad/virus/chain/long100/starts/ (about 2.5 minutes each, one emulator at a time), compared with the saved census,
# then the cause table over the 23 saved games (saved/gNNN.json, from death_census.py, not recomputed here).
# Not in the gate: cut_rising.py (the labelled poke trial, results in $W/deaths/cut100.txt) and scan_writers.py (raw scan).
# Output: $VIRUS_WORK/deaths/fresh/.
SD=$(cd "$(dirname "$0")" && pwd); cd "$SD" || exit 1
while [ ! -e tools/rdis.py ]; do cd .. || exit 1; [ "$PWD" = / ] && exit 1; done
W=${VIRUS_WORK:-scratchpad/virus}; G=$W/deaths; mkdir -p $G/fresh
export VIRUS_WORK=$W
for g in 1 3; do
  uv run python $SD/death_census.py $g $G/fresh 2>&1 | grep -E 'loss|done'
  uv run python $SD/compare.py $G/fresh/g00$g.json $G/saved/g00$g.json
done
echo "== control: fresh game 1 against saved game 3 (must not agree)"
uv run python $SD/compare.py $G/fresh/g001.json $G/saved/g003.json
echo "== cause table over the saved census"
uv run python $SD/aggregate.py $G/saved | sed -n '1,/^per death/p' | grep -v '^per death'
echo "== fuel per life"
uv run python $SD/lives.py | grep -E 'all lives|died with fuel 0|died with fuel > 0|ground, fuel|fuel-0 deaths|fuel>0 deaths'
