#!/usr/bin/env bash
# capture_ai.sh: the AI's natural $4a7a entries (no pokes, no input) from the census starts (census.sh): rand1 (hits 1..6, all
# foreign-settlement targets), W5G_k80_c1 and W5G_k108_c1 (the livelocked re-issues: records, no target), X10G_k25_c1 (empty
# cells).  tools/capture_hits.py into ${PM_WORK:-scratchpad/pm162}/g4a7a/nat/n4a7a_<name>.json; gate with gate_4a7a_nat.py.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=${M68000_ROOT:-$HERE}
while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); [ "$ROOT" = / ] && { echo "no repo root"; exit 1; }; done
cd "$ROOT"
OUT=${PM_WORK:-scratchpad/pm162}/g4a7a/nat
L=scratchpad/pm148/arms/long
cap() { uv run python tools/capture_hits.py "$1" 4a7a "$2" "$OUT" --name "n4a7a_$3" --max 100000000 || true; }
cap scratchpad/pm142/rand1.snap 1,2,3,4,5,6 rand1
cap $L/W5G_k80_c1.snap 1,2,300 k80
cap $L/W5G_k108_c1.snap 1,2,400,750 k108
cap $L/X10G_k25_c1.snap 1,2,12 k25
