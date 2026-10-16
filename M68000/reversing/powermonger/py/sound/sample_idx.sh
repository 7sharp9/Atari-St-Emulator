#!/bin/bash
# sample_idx.sh [snap] [k] [pcs...]: register samples at the indexed accesses below $58054. For each PC (default the four
# $58042-table sites $253e $3d02 $685a $6ae4 and $9b9e) stop k times (default 15) with `bp PC 40000000` / `s 1`, each from where
# the previous stop left off, in one process from pm142/rand1.snap. Output: $PM_WORK/pile/w58054/idx.txt; the index register
# per site is D2 ($253e, $6ae4), D4 ($3d02), D3 ($685a), D0 ($9b9e).
R=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$R/tools/rdis.py" ]; do R=$(dirname "$R"); done
cd "${M68000_ROOT:-$R}" || exit 1
W=${PM_WORK:-scratchpad/pm162}/pile/w58054; mkdir -p "$W"; SNAP=${1:-scratchpad/pm142/rand1.snap}; K=${2:-15}; shift 2 2>/dev/null
PCS=${*:-"253e 3d02 685a 6ae4 9b9e"}
{
  echo "disk scratchpad/powermonger.st"
  for pc in $PCS; do for i in $(seq 1 "$K"); do echo "bp $pc 40000000"; echo "s 1"; done; done
  echo q
} | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl > "$W/idx.txt" 2>&1
