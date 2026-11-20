#!/bin/bash
# Object types, pool kind and launch pad table gates, each with its failing control; captures afresh from
# scratchpad/virus/demo/S1b.snap (py/demo/capture.sh) and scratchpad/virus/drive/g_game2.snap (drive.sh).
# Usage: bash reversing/virus/py/objects/gate_objects.sh      (about 6 minutes)
cd "$(dirname "$0")/../../../.." || exit 1
W=${VIRUS_WORK:-scratchpad/virus}; P=reversing/virus/py/objects; G=$W/objects/gate; PY="uv run python -I"
S1=$W/demo/S1b.snap; GS=$W/drive/g_game2.snap
mkdir -p $G
{
echo "== pad table (pad_table.py)"
$PY $P/pad_table.py model $S1 2>&1 | grep -v '^---\|WARN'
$PY $P/pad_table.py reads $S1 12 2>&1 | grep -v '^---\|WARN'
$PY $P/pad_table.py writes $S1 400 2>&1 | grep -v '^---\|WARN'
$PY $P/pad_table.py screen $GS $G/pad 2>&1 | grep -v '^---\|WARN' | grep 'grid (row'
echo "== falling infection (pool_capture.py, gate_infection_fall.py)"
$PY $P/pool_capture.py $S1 1190 $G/s1b.json 2>&1 | grep 'frames'
$PY $P/gate_infection_fall.py $G/s1b.json
for c in --break-gravity --break-ground --break-cell; do echo "control $c"; $PY $P/gate_infection_fall.py $G/s1b.json $c; done
echo "== object shapes (object_shapes.py)"
$PY $P/object_shapes.py $S1 $G/shapes --n 3 --types 1,2,3,4,5,6,7,8,9,11 2>&1 | grep 'inside the object box'
$PY $P/object_shapes.py $S1 $G/shapes --types 10,12 --cells '10:5,7;10:3,7;12:20,85;12:20,86' 2>&1 | grep 'inside the object box'
$PY $P/object_shapes.py $S1 $G/shapes_flags --n 1 --flags 0x10,0x20 --types 1,2,3,4,5,6,7,8,9,11 2>&1 | grep 'inside the object box'
$PY $P/objects_montage.py $G/shapes $G/shapes_flags reversing/virus/objects.png
} 2>&1 | tee $G/out.txt
