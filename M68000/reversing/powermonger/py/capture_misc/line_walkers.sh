#!/bin/bash
# The unreferenced line library and river carver, called from m1_ready.snap (callcap restores the state).
# Expect: $10c7e 24 bytes changed (20 map bytes 00->80, 10 per colour plane, + 4 stack); $10ce4 returns -1;
# $10cae with D6=20 returns D0.w=028b; $10458 changes 1164 bytes (vriv_planes.py: alt 382, colA 128,
# colB 128, flags 504, rows 0..63). Usage: line_walkers.sh [outdir for vriv_cc.json]
ROOT="${M68000_ROOT:-$(cd "$(dirname "$0")/../../../.." && pwd)}"; HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$ROOT" || exit 1
SNAP=scratchpad/pm123/win/m1_ready.snap
OUT="${1:-scratchpad/pm146/capture}"; mkdir -p "$OUT"
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume $SNAP repl < "$HERE/cc_line.cmds" 2>&1 | grep -E "^--- callcap|^regdelta"
printf 'callcap 10458 5000000 %s/vriv_cc.json\nq\n' "$OUT" | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume $SNAP repl 2>&1 | grep -E "^--- callcap"
python3 "$HERE/vriv_planes.py" "$OUT/vriv_cc.json"
