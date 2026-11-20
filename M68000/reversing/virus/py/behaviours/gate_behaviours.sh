#!/bin/bash
# Behaviours gate (about 10 minutes): the wave-5 mothership, the chaser `$21afe` and the mothership's chaser `$2279a`, the launch, and
# the provoking scan `$201b4`, each with its failing control. Everything is captured afresh into W/behaviours/gate/ (W = $VIRUS_WORK or
# scratchpad/virus); the start snapshots are built from chain/long100/starts/main_g050.snap by build_snaps.py (needs py/chain/chain.py's chain).
# Labelled pokes: mothership_drive.py poke A (ship placed 3 x nose short of the mothership, velocity 0), B ($62a5d := 0), C (--trials:
# chaser velocities and life words set at four ticks). Not in the gate (4 games, about 15 minutes): `python3 census_chunks.py 14 830000000`
# and the same for 45 740000000, 50 1180000000, 93 780000000, then `python3 summarize.py <game>`.
d="$(cd "$(dirname "$0")" && pwd)"; r="$d"; while [ ! -f "$r/tools/rdis.py" ]; do r="$(dirname "$r")"; done
cd "$r" || exit 1
W="${VIRUS_WORK:-$r/scratchpad/virus}/behaviours/gate"; mkdir -p "$W"
export VIRUS_MPC_WORK="$W/mpc"
P="uv run python $d"
$P/build_snaps.py "$W/snaps" || exit 1
S="$W/snaps"
echo "== mothership, ship poked in range (A, B): launches, hits, kill"
$P/mothership_drive.py $S/w5.snap 900 nofire $W/ms_nofire.json || exit 1
$P/mothership_drive.py $S/w5.snap 600 autofire $W/ms_fire.json || exit 1
echo "== control: no poke (ship far, no launch)"
$P/mothership_drive.py $S/w5.snap 900 nofire $W/ms_nopoke.json --nopoke || exit 1
$P/mothership_drive.py $S/w5.snap 700 nofire $W/ms_trials.json --trials || exit 1
echo "== launch gate"
for c in none vy life; do echo "-- control $c"; $P/gate_launch.py $W/ms_nofire.json --control $c; done
echo "== chaser gates: mothership chaser \$2279a with poke C, then a natural capture of \$21afe"
$P/capture_events.py $S/c1065.snap 1500 $W/cap_c1065.json || exit 1
$P/capture_events.py $S/c1065.snap 700 $W/cap_c1065_lp.json auto --lifepoke || exit 1
for c in none drag pull clamp period oldship; do echo "-- 2279a control $c"; $P/gate_chaser.py --capture $W/ms_trials.json --control $c | sed -n 2,4p; done
for c in none drag pull clamp oldship; do echo "-- 21afe natural control $c"; $P/gate_chaser.py --capture $W/cap_c1065.json --control $c | sed -n 2,3p; done
for c in none period; do echo "-- 21afe with life poke control $c"; $P/gate_chaser.py --capture $W/cap_c1065_lp.json --control $c | sed -n 2,4p; done
echo "== provoking scans"
$P/provoke_check.py $S/p135.snap 30000000 $S/p255.snap 40000000 $S/p415.snap 60000000 $S/p495.snap 30000000 | grep -v '^---'
