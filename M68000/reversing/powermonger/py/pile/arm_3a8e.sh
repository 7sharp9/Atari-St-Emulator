#!/bin/bash
# arm_3a8e.sh [val] [snap]: catapult/cannon arm $3a8e..$3aa4 of the goods-pile transfer $39d4. From pm142/rand1.snap stop at the
# first natural $39d4 (D7=0, A3=$51a74, lead A1=$53dc6, shift D0=0), optionally poke the lead's byte 44 (longword 53df2: val 0e|10
# then 00 09 f6; "none" = no poke, the control), run `hits` over 5000 steps and dump the lead record, its goods $51ac8 and the pool.
R=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$R/tools/rdis.py" ]; do R=$(dirname "$R"); done
cd "${M68000_ROOT:-$R}" || exit 1
W=${PM_WORK:-scratchpad/pmwork}/piles; mkdir -p "$W"
V=${1:-none}; SNAP=${2:-scratchpad/pm142/rand1.snap}
{
  echo "disk scratchpad/powermonger.st"
  echo "bp 39d4 200000000"
  echo "m 53dc6 50"; echo "m 51ac8 96"; echo "m 51a74 100"
  [ "$V" != none ] && printf 'w 53df2 %02x0009f6\n' "$((16#$V))"
  echo "hits 5000 39d4 3a18 3a50 3a60 3a8e 3a96 3aa0 3aa4 3ac8 3ad8 3ae8 3aee"
  echo "m 53dc6 50"; echo "m 51ac8 96"; echo "m 4bb4e 672"
  echo q
} | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl > "$W/arm_3a8e_$V.txt" 2>&1
grep -E "^ *\\$|hits|^[0-9a-f]{2} " "$W/arm_3a8e_$V.txt" | cut -c1-260
