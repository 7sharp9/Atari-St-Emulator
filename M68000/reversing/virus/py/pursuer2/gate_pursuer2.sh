#!/bin/bash
# Two-hit pursuer hit paths: first hit $22164, damaged $221ac, kill $216d6 (pursuer2.py), gated on natural captures, then on labelled pokes
# (cap_poke.py: ground contact), then the broken controls. Inputs: $W/pursuer/caps/nat_*.json (scratchpad/ANCHORS.md "virus pursuer"),
# $W/behaviours/gate/snaps/{c1065,w5}.snap, $W/pursuer/snaps/g014_500.snap. Output: $VIRUS_WORK/pursuer2/ (about 2 minutes).
SD=$(cd "$(dirname "$0")" && pwd); cd "$SD" || exit 1
while [ ! -e tools/rdis.py ]; do cd .. || exit 1; [ "$PWD" = / ] && exit 1; done
W=${VIRUS_WORK:-scratchpad/virus}; M=$SD; G=$W/pursuer2; mkdir -p $G/mpc
export VIRUS_MPC_WORK=$PWD/$G/mpc VIRUS_WORK=$W
echo "== fresh natural captures (game 50 c1065 and w5, not used to derive the model)"
for s in c1065 w5; do uv run python reversing/virus/py/behaviours/cap_nat.py $W/behaviours/gate/snaps/$s.snap 4000 $G/nat_$s.json | tail -1; done
echo "== natural: 25 saved captures + 2 fresh"
uv run python $M/gate_pursuer2.py $W/pursuer/caps/nat_*.json $G/nat_*.json | grep -E 'ALL9|removed|kill\.|score|exerc|skipp|miss'
echo "== labelled pokes (same snapshot g014_500: control, then y := ground height under a live record)"
S=$W/pursuer/snaps/g014_500.snap
uv run python $M/cap_poke.py $S 345 $G/ctl.json none 0 | tail -1
uv run python $M/cap_poke.py $S 345 $G/ground1.json ground1 330 | tail -1
uv run python $M/cap_poke.py $S 345 $G/dgnd3.json dgnd3 336 | tail -1
uv run python $M/cap_poke.py $S 345 $G/dgnd0.json dgnd0 337 | tail -1
for f in ctl ground1 dgnd3 dgnd0; do echo "-- $f"; uv run python $M/gate_pursuer2.py $G/$f.json | grep -E 'ALL9|removed|kill\.|score|skipp|miss'; done
for c in count4 nofall award100 stun4 killall shift9 shift12 nohitbit unsigned_tilt pad_keep keepground ground_no_kill; do
  echo "== control $c"
  uv run python $M/gate_pursuer2.py $W/pursuer/caps/nat_*.json $G/ground1.json $G/dgnd3.json $G/dgnd0.json --control $c | grep -E 'ALL9|removed|score|multiset'
done
