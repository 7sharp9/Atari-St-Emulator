#!/bin/bash
# arm.sh <name> <pre-delay steps> <hold steps>
# From scratchpad/captainblood/f3_33M.snap (the title's key wait): optional `s PRE`, optional POKE (a REPL line, e.g.
# POKE="w 4ba 00000871", a labelled poke of _hz_200), `kbd 39`, `s HOLD`, `kbd b9`, run to $b7fc (galaxy built), then dump
# the planet table $ba4e, the position $ba46, the Random seed $29b8 and _hz_200 $4ba to
# scratchpad/captainblood/galaxy/arms/<name>.txt (and .snap). Any directory inside the repo works as the start.
R=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$R/tools/rdis.py" ] && [ "$R" != / ]; do R=$(dirname "$R"); done
cd "$R" || exit 1
W=scratchpad/captainblood; D=$W/galaxy/arms; mkdir -p $D
N=$1; PRE=${2:-0}; HOLD=${3:-200000}
{
 [ "$PRE" != 0 ] && echo "s $PRE"
 [ -n "$POKE" ] && echo "$POKE"
 echo "kbd 39"; echo "s $HOLD"; echo "kbd b9"
 echo "bp b7fc 60000000"
 echo "m ba4e 512"; echo "m ba46 8"; echo "m 29b8 4"; echo "m 4ba 4"
 echo "snap $D/$N.snap"
} | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume $W/f3_33M.snap repl > $D/$N.txt 2>&1
