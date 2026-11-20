#!/bin/bash
# The pursuer $21f00, $2202c and the patrol states as models (reversing/virus/behaviours.md "The pursuers and the patrol").
# One fresh natural capture (chain game 45 at 300M steps, 2500 ticks, about a minute) gated on its own, then the 25 saved
# captures of waves 1 to 4 with the broken controls (seconds).  Inputs: $W/pursuer/snaps/g045_300.snap, $W/pursuer/caps/nat_*.json
# (scratchpad/ANCHORS.md "virus pursuer").
cd "$(dirname "$0")/../../../.." || exit 1
W=${VIRUS_WORK:-scratchpad/virus}; M=reversing/virus/py/behaviours; G=$W/pursuer/gate; rm -rf $G; mkdir -p $G
export VIRUS_WORK=$W
echo "== fresh capture from g045_300.snap, 2500 ticks"
VIRUS_MPC_WORK=$PWD/$G/mpcwork uv run python $M/cap_nat.py $W/pursuer/snaps/g045_300.snap 2500 $G/fresh.json | tail -1
uv run python $M/gate_pursuer.py $G/fresh.json | grep '=='
echo "== the 25 saved captures"
uv run python $M/gate_pursuer.py $W/pursuer/caps/nat_*.json | grep -E '==|exercised'
for c in nopull far steer4 oldship thrust1 keepbit nophase; do
  echo "== control $c"
  uv run python $M/gate_pursuer.py $W/pursuer/caps/nat_*.json --control $c | grep -E '^ *(pursuer/live|conversion|patrol/(attack|home)) .*== model'
done
