#!/bin/bash
# Gate `attractor`: the attractor `$22486`/`$224a6` as models (reversing/virus/behaviours.md): record fields per tick, the ship's
# velocity pull `$22ebe`, the fuel drain `$225d6`, the hit counter, plus labelled-poke runs for the ground kill, ship contact and
# a same-snapshot poked/unpoked pair with a watch on $32a2e.  About 5 minutes (three natural captures of 4500 ticks, five short
# poke runs).  Inputs: $P/snaps/g014_400.snap, g093_300.snap, g045_400.snap, g014_500.snap and the 25 saved captures $P/caps/nat_*.json
# (the pursuer corpus, scratchpad/ANCHORS.md "virus pursuer").  Data goes under $VIRUS_WORK/attractor/ (default scratchpad/virus/attractor/).
here="$(cd "$(dirname "$0")" && pwd)"
R="$here"; while [ ! -f "$R/tools/rdis.py" ]; do R="$(dirname "$R")"; [ "$R" = / ] && { echo repo root not found; exit 1; }; done
cd "$R" || exit 1
P=${VIRUS_PURSUER:-scratchpad/virus/pursuer}
W=${VIRUS_WORK:-scratchpad/virus}/attractor; mkdir -p $W/caps $W/mpcwork
export VIRUS_MPC_WORK=$W/mpcwork
G="uv run python $here/gate_attractor.py"
for s in g014_400 g093_300 g045_400; do
  [ -f $W/caps/nat_$s.json ] || uv run python $here/cap_poke.py $P/snaps/$s.snap 4500 $W/caps/nat_$s.json none | tail -1
done
for m in none near far touch ground; do
  [ -f $W/caps/poke_$m.json ] || uv run python $here/cap_poke.py $P/snaps/g014_500.snap 90 $W/caps/poke_$m.json $m | tail -1
done
echo "== natural: 3 fresh captures (wave 2 -> 3 or 4, through the wave change) + the 25 saved ones"
$G $W/caps/nat_*.json $P/caps/nat_*.json | grep -v '^ miss'
echo "== labelled pokes (ship moved next to an attractor / attractor moved into the ground), 90 ticks each, snapshot g014_500"
for m in none near far touch ground; do echo "-- poke mode $m"; $G $W/caps/poke_$m.json | sed 1,2d | grep -v '^ miss'; done
echo "== broken-model controls on the natural set (every one must lose matches)"
for c in pull5 pull7 pullold pull_a00 drain24 drain26 drain800 noclamp spring2c0 drag3 vclampa0 waitkeep life4 nohitstore; do
  echo "-- control $c"; $G $W/caps/nat_*.json $P/caps/nat_*.json --control $c | grep -v '^ miss' | grep -E '^  (fly|wait|kill|drain 1|pull only|fuel empty|watch)'
done
