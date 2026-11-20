#!/bin/bash
# Populous II: snapshot stopped at gen_land $1ebee's entry during the conquest world build (the briefing's PROCEED
# click, then bp). Run from anywhere.
#   bash reversing/populous2/py/gen_entry.sh                 -> anchors/p2_gen_entry.snap from anchors/p2_briefing
#   bash reversing/populous2/py/gen_entry.sh <out.snap> <N>  -> battle N's: resume p2_title, poke the battle number
#        $473a0 = N before the CONQUEST GAME click (battle_census.sh's route), 20M steps to the briefing, then the same
#        PROCEED click and bp. Battle 0 this way stops at the same step and seed as p2_gen_entry (control).
set -e
d=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$d/tools/rdis.py" ] && [ "$d" != / ]; do d=$(dirname "$d"); done; cd "$d"
OUT=${1:-scratchpad/populous2/anchors/p2_gen_entry.snap}
N=$2
rm -f "$OUT" "$OUT.prov.json"
if [ -z "$N" ]; then
  FROM=scratchpad/populous2/anchors/p2_briefing.snap; PRE=""
else
  FROM=scratchpad/populous2/anchors/p2_title.snap
  PRE=$(printf 'ww 473a0 %04x\n' "$N"; sed -n '/^mouse move 100 60/,/^s 20000000/p' reversing/populous2/drive.txt)
fi
{ [ -n "$PRE" ] && echo "$PRE"
  printf "mouse move -90 94\ns 300000\nmouse down l\ns 60000\nmouse up l\nbp 1ebee 80000000\nsnap $OUT\nm 47382 4\nm 473a0 2\nq\n"; } |
  ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$FROM" repl 2>&1 |
  grep -E 'breakpoint|state saved|^0[0-9a-f]* '
