#!/bin/bash
# One 3D frame of Midwinter from s_3d_6.snap: rebuilds the frame snapshots and the emulator's edge-table and
# screen captures under scratchpad/midwinter/pipeline/, then runs the census and the models against them.
# Run from M68000/:  bash reversing/midwinter/py/pipeline/run.sh
P=reversing/midwinter/py/pipeline
W=scratchpad/midwinter/pipeline
DISK=scratchpad/midwinter/zuul067.st
E="dotnet exec bin/Debug/net8.0/M68000.dll"
export ATARI_NOTRACE=1
mkdir -p $W
$E resume scratchpad/midwinter/agents/static/s_3d_6.snap repl --disk-a $DISK < $P/f1.repl > $W/f1.log 2>&1
$E resume $W/f1_start.snap repl --disk-a $DISK < $P/f1c.repl > $W/f1c.log 2>&1
$E resume $W/f1_start.snap repl --disk-a $DISK < $P/hits_frame.repl > $W/hits_frame.log 2>&1
$E resume $W/f1_build.snap repl --disk-a $DISK < $P/tables.repl > $W/tables.log 2>&1
$E resume $W/f1_build.snap repl --disk-a $DISK < $P/screens.repl > $W/screens.log 2>&1
echo "== census of one frame (225171 steps)"
grep -A50 "hits over" $W/hits_frame.log | awk '/^  \$0/ {printf "%s %s  ", $1, $2} END {print ""}'
echo "== projection"; uv run python $P/proj_check.py $W/f1_cells.snap | head -1
echo "== camera space, first cell"; uv run python $P/cam_check.py $W/f1_cells.snap | tail -1
echo "== draw list"; uv run python $P/polys.py $W/f1_build.snap | head -2
echo "== edge model"; uv run python $P/edge_model.py $W/f1_build.snap $W/tables.log | grep -v '^\[\]'
echo "== fill model"; uv run python $P/fill_model.py $W/f1_build.snap $W/screens.log $W/tables.log | grep -v '^\[\]'
