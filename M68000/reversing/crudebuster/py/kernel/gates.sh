#!/bin/sh
# Architecture gates (architecture.md). About 3 minutes; one MAME run for the spawn gates, one for the frame counter.
#   gates.sh [outdir]   (default scratchpad/crudebuster/kernel_gates)
here=$(cd "$(dirname "$0")" && pwd)
cb=$(cd "$here/../.." && pwd)
root=$(cd "$cb/../.." && pwd)
out=${1:-$root/scratchpad/crudebuster/kernel_gates}
mkdir -p "$out"
PY=${PY:-$root/.venv/bin/python}
[ -x "$PY" ] || PY=python3
python3 "$here/static_gate.py"
export CB_DIR=$cb/lua CB_OUT=$out
CB_RUN=$out/run_f CB_PLAN=$cb/lua/plans/play1.lua CB_STOP=2400 CB_ADDRS="8004a:w,80002:w" "$cb/cbmame.sh" run "$cb/lua/framelog.lua" 300 >/dev/null 2>&1
"$PY" "$here/framecount_gate.py" "$out/framelog.csv"
CB_RUN=$out/run_s CB_PLAN=$cb/lua/plans/walk1.lua CB_STOP=4000 "$cb/cbmame.sh" run "$cb/lua/spawnlog.lua" 400 >/dev/null 2>&1
python3 "$here/spawn_gate.py" "$out/spawnlog.txt"
python3 "$here/throttle_gate.py" "$out/spawnlog.txt"
