#!/bin/bash
# The computer god $25652 against its controller word (side record +26: 2 human, 4 computer).
# Three arms from p2_game_60m over the same 12,000,000 steps: unpoked, side 2 poked to human, side 1 poked to
# computer. Prints per arm the tick control $29226, the computer branch $25670, the cascade $25690, the three post
# sites seen in play ($25756 mailbox raise, $25878 level, $25a18 release) and the executed commands $292e4.
# Run from M68000/:  bash reversing/populous2/py/god_census.sh [outdir]
OUT=${1:-scratchpad/populous2/god}
SNAP=scratchpad/populous2/anchors/p2_game_60m.snap
mkdir -p "$OUT"
arm() {  # name, poke line or empty
  { [ -n "$2" ] && echo "$2"; echo "hits 12000000 29226 25670 25690 25756 25878 25a18 292e4"; echo q; } \
    | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl > "$OUT/$1.log" 2>&1
  awk -v n="$1" '/^  \$0/ { c[$1] = $2 }
    END { printf "%s: ticks %d computer-branch %d cascade %d posts %d+%d+%d commands %d\n", n,
          c["$029226"], c["$025670"], c["$025690"], c["$025756"], c["$025878"], c["$025a18"], c["$0292e4"] }' "$OUT/$1.log"
}
arm unpoked ""
arm side2_human "ww 47252 2"
arm side1_computer "ww 47118 4"
