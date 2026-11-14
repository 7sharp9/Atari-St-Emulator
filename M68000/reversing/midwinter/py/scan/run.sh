#!/bin/bash
# The scan gate from fresh captures. Run from M68000/:  bash reversing/midwinter/py/scan/run.sh
# Needs scratchpad/midwinter/pipeline/f1_start.snap (made by reversing/midwinter/py/pipeline/run.sh).
S=reversing/midwinter/py/scan
D=scratchpad/midwinter/scan
[ -f scratchpad/midwinter/pipeline/f1_start.snap ] || { echo "run reversing/midwinter/py/pipeline/run.sh first"; exit 1; }
bash $S/cap_scan.sh
uv run python $S/gate_scan.py | tail -1
uv run python $S/gate_scan.py --break | tail -1
bash $S/cap_cells.sh 100 300 640 899
for h in 100 300 640 899; do echo "projection heading $h: $(uv run python reversing/midwinter/py/pipeline/proj_check.py $D/cells/c$h.snap | head -1)"; done
