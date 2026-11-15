#!/bin/bash
# Natural corpus for claim_gate.py: $25168 entries 1..40 and every 9th to 416 from the two play anchors.
# Run from M68000/. Writes scratchpad/populous2/claim/game_{60m,start}_<n>.snap and game_*.json.
set -e
d=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$d/tools/rdis.py" ] && [ "$d" != / ]; do d=$(dirname "$d"); done; cd "$d"
H=$(python3 -c "print(','.join(str(i) for i in list(range(1,41))+list(range(47,420,9))))")
OUT=scratchpad/populous2/claim
rm -f $OUT/game_*
for s in game_60m game_start; do
  uv run python tools/capture_hits.py scratchpad/populous2/anchors/p2_$s.snap 25168 "$H" $OUT --name $s
done
