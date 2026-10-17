#!/bin/bash
# nat_arms.sh <snap> [steps]: natural census of the $39d4 arms. A $3a60 entry not preceded by $3a50 is the add-to-pile arm ($3a18 taken):
# arm count = hits($3a60) - hits($3a50). Also $3a8e (goods half, lead byte 44 test), $3a96 (catapult/cannon arm taken), $3aee ($3a48 bit-5 arm).
R=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$R/tools/rdis.py" ]; do R=$(dirname "$R"); done
cd "${M68000_ROOT:-$R}" || exit 1
W=${PM_WORK:-scratchpad/pmwork}/piles; mkdir -p "$W"
S=${1:-scratchpad/pm142/rand1.snap}; N=${2:-600000000}; B=$(basename "$S" .snap)
{ echo "disk scratchpad/powermonger.st"; echo "hits $N 39d4 3a50 3a60 3a8e 3a96 3aee 3ac8 2776"; echo q; } |
 ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$S" repl > "$W/nat_$B.txt" 2>&1
echo "== $S $N"; grep -E '^ *\$|hits over' "$W/nat_$B.txt"
