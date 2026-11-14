#!/bin/bash
# Every Virus gate from the captures made by drive.sh and capture.sh, each with one broken-model control.
# Output lines go to stdout and to $W/gates/<gate>/out.txt.  Usage: bash reversing/virus/py/gate_all.sh
cd "$(dirname "$0")/../../.." || exit 1
W=${VIRUS_WORK:-scratchpad/virus}; P=reversing/virus/py; G=$W/gates; PY="uv run python -I"
run() { name=$1; shift; mkdir -p $G/$name; { "$@"; } 2>&1 | tee -a $G/$name/out.txt; }
for d in terrain objects grid tiles slope flight flight_auto particles; do mkdir -p $G/$d; : > $G/$d/out.txt; done
S=$W/drive/g_game2.snap
run terrain $PY $P/virus_terrain.py $S
run terrain $PY $P/virus_terrain.py $S --delta $W/cap/cc_l1.json --level 1
run terrain $PY $P/virus_terrain.py $S --delta $W/cap/cc_l2.json --level 2
run terrain echo "control: constant shifted"; run terrain $PY $P/virus_terrain.py $S --break
run terrain echo "control: level 1 variant on level 2 data"; run terrain $PY $P/virus_terrain.py $S --delta $W/cap/cc_l1.json --level 2
run objects $PY $P/virus_objects.py $S $W/cap/cc_l1.json 1
run objects $PY $P/virus_objects.py $S $W/cap/cc_l2.json 2
run objects echo "control: one draw short"; run objects $PY $P/virus_objects.py $S $W/cap/cc_l2.json 2 --break-count
run objects echo "control: type order swapped"; run objects $PY $P/virus_objects.py $S $W/cap/cc_l2.json 2 --break-order
for i in 1 2 3 4; do run grid $PY $P/virus_grid.py $W/fl/f$i.snap $W/fl/cc$i.json; done
run grid echo "control: first-row depth \$f00"; run grid $PY $P/virus_grid.py $W/fl/f1.snap $W/fl/cc1.json --break
run tiles $PY $P/virus_tiles_check.py $W/cap/tile_bp.txt
run tiles echo "control: type array read two words off"; run tiles $PY $P/virus_tiles_check.py $W/cap/tile_bp.txt --break
run slope $PY $P/virus_slope.py $W/fl/f2.snap
run slope echo "control: low byte kept"; run slope $PY $P/virus_slope.py $W/fl/f2.snap --break
run flight $PY $P/virus_flight.py $W/cap/flight_bp.txt $W/fl/f1.snap
run flight echo "control: thrust shift 4"; run flight $PY $P/virus_flight.py $W/cap/flight_bp.txt $W/fl/f1.snap --break
run flight_auto $PY $P/virus_flight.py $W/cap/flight_auto_bp.txt $W/fl/f1.snap
run flight_auto echo "control: thrust shift 4"; run flight_auto $PY $P/virus_flight.py $W/cap/flight_auto_bp.txt $W/fl/f1.snap --break
run flight_auto echo "autopilot entry counts (poke wb 62a5f ff):"; run flight_auto grep -E '^  \$0(2538c|254aa)' $W/cap/auto_hits.txt
run particles $PY $P/virus_particles.py $W/cap/part_bp.txt $W/fl/f1.snap
run particles echo "control: drag >>3"; run particles $PY $P/virus_particles.py $W/cap/part_bp.txt $W/fl/f1.snap --break
