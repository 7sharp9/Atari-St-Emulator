#!/bin/bash
# arm_3a18.sh [poke|none] [snap]: add-to-existing-pile arm $3a18 -> $3a60 of the goods-pile transfer $39d4. From pm142/rand1.snap stop at
# the SECOND natural $39d4 (bpc; the first one made a pile at cell $12e7 in pool slot $4bb4e; A3=$517fe, lead A1=$52fe8). `poke`
# overwrites the lead's bytes 8..11 (longword at 52ff0, old value dumped first) with the first lead's 27 78 4b 78 so that the lead's
# cell $39ec = $12e7; `none` is the same-snapshot, same-budget control. Then `hits` over 5000 steps and dumps of the pool and group.
R=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$R/tools/rdis.py" ]; do R=$(dirname "$R"); done
cd "${M68000_ROOT:-$R}" || exit 1
W=${PM_WORK:-scratchpad/pmwork}/piles; mkdir -p "$W"
V=${1:-poke}; SNAP=${2:-scratchpad/pm142/rand1.snap}
{
  echo "disk scratchpad/powermonger.st"
  echo "bpc 39d4 2 400000000"
  echo "m 52fe8 50"; echo "m 4bb4e 112"; echo "m 517fe 100"; echo "m 51862 96"
  [ "$V" = poke ] && echo "w 52ff0 27784b78"
  echo "hits 5000 3a18 3a50 3a60 3a8e 3ac8 3ad8 3ae8"
  echo "m 4bb4e 112"; echo "m 517fe 100"; echo "m 51862 96"
  echo q
} | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl > "$W/arm_3a18_$V.txt" 2>&1
grep -E "^ *\\$|hits|^[0-9a-f]{2} " "$W/arm_3a18_$V.txt" | cut -c1-200
