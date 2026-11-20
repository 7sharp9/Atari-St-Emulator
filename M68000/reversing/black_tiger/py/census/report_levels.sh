#!/bin/bash
# Compare the census runs of run_levels.sh (plus the D0_timeout control) per level against level index 0.
# usage: report_levels.sh   (prints the table and spans; writes census/levels_vs_L0.json)
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../../.." && pwd)"
C="${BT_WORK:-$ROOT/scratchpad/black_tiger}/census"
[ -d "$C/D0_timeout" ] || "$ROOT/.venv/bin/python" "$ROOT/tools/code_census.py" run "$ROOT/scratchpad/black_tiger/play_start.snap" \
  "$C/D0_timeout" --chunks 5 --per-chunk "$HERE/timeout.txt" --disk-a "$C/../bt_auto.st" --read 17846:2 --read 1f00c:2 \
  --stop-if-changed 17846:2 > "$C/D0_timeout.log" 2>&1
args=(--range a2fc 1f274 --sym "$ROOT/reversing/black_tiger/black_tiger.sym" --group "L0=$C/[LBD]0_*/chunk_*.npz")
for k in 1 2 3 4 5 6 7; do args+=(--group "L$k=$C/[LB]${k}_*/chunk_*.npz"); done
"$ROOT/.venv/bin/python" "$ROOT/tools/code_census.py" report "${args[@]}" --base L0 --top 60 --json "$C/levels_vs_L0.json"
