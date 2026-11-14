#!/bin/bash
# The reply engine under a click on the mouth against a no-click control: same snapshot (i1.snap: Izwals, one icon
# in the player's sentence, pointer 7 left and 25 below the mouth), same pointer move, same 600,000 steps.
# Run from M68000/:  bash reversing/captainblood/py/census_speak.sh [outdir]
OUT=${1:-scratchpad/captainblood/census}
SNAP=scratchpad/captainblood/i1.snap
A="e344 e45a e494 e6a2 e58a e22e e284"
mkdir -p "$OUT"
arm() {  # name, click line or empty
  { echo "mouse move -7 25"; echo "s 60000"; [ -n "$2" ] && echo "$2"; echo "hits 600000 $A"; echo "m dc44 8"; echo q; } \
    | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl > "$OUT/$1.log" 2>&1
  awk -v n="$1" '/^  \$0/ { c[$1] = $2 }
    END { printf "%s: encode %d engine %d scan %d match %d condition %d compose %d reply-line %d\n", n,
          c["$00e344"], c["$00e45a"], c["$00e494"], c["$00e6a2"], c["$00e58a"], c["$00e22e"], c["$00e284"] }' "$OUT/$1.log"
}
arm click "mouse down l"
arm control ""
