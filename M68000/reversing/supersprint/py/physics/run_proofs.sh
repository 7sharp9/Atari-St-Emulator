#!/bin/sh
# Re-runs every headline proof from a fresh checkout state (no cached corpora). Run from M68000/: sh reversing/supersprint/py/physics/run_proofs.sh
PY=reversing/supersprint/py/physics
OUT=scratchpad/supersprint/agents/physics/evidence/final_proofs.txt
: > $OUT
run() { echo "### $*" | tee -a $OUT; uv run python "$@" 2>&1 | grep -v '^state ' | cut -c1-400 | tee -a $OUT; }
run $PY/rebuild_walls.py
run $PY/rebuild_surface.py
run $PY/rebuild_planes02.py
run $PY/test_df18.py 700 2
run $PY/fuzz_df18.py 1000 31
run $PY/test_ctl.py natural 300 4
run $PY/test_ctl.py fuzz 700 41
run $PY/test_samplers.py natural 450 5
run $PY/test_samplers.py fuzz 400 6
run $PY/test_trajectory.py 700 3
echo "### negative control (floor division instead of DIVS)" | tee -a $OUT
SS_MUTATE=floor uv run python $PY/test_ctl.py fuzz 200 5 2>&1 | head -1 | tee -a $OUT
SS_MUTATE=floor uv run python $PY/fuzz_df18.py 200 7 2>&1 | tail -2 | head -1 | cut -c1-100 | tee -a $OUT
run $PY/speed_vs_heading.py
