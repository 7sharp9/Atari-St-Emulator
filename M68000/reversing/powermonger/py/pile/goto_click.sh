#!/bin/bash
# goto_click.sh [click|ctl] [word8hex]: from $PM_WORK/pile/goto/open.snap (open_pile.sh: the goods-pile panel of pile $4bba2 open,
# pointer at (105,69)) move the pointer to the panel's eye icon at (15,70) and click it ("click"), or move it there
# and hold no button ("ctl", the same-snapshot, same-budget control). Prints a hits table of the go-to path
# ($74d8 scjt[$18/$19], $ab34, its byte6-$2c arm $aba8) and the camera cell $4bb3a/$4bb3c before and after.
R=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$R/tools/rdis.py" ]; do R=$(dirname "$R"); done
cd "${M68000_ROOT:-$R}" || exit 1
W=${PM_WORK:-scratchpad/pm162}/pile/goto; ARM=${1:-click}; W8=$2
# word8hex: a labelled poke of the pile's word 8 ($4bbaa; the longword write keeps the food word $0337 at $4bbac)
{
  echo "disk scratchpad/powermonger.st"
  [ -n "$W8" ] && echo "w 4bbaa ${W8}0337"
  echo "m 4bba2 28"; echo "m 4bb3a 4"
  echo "mouse move -90 1"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
  if [ "$ARM" = click ]; then echo "mouse down l"; fi
  echo "mouse move 0 0"; echo "hits 300000 74d8 ab34 aba8 7518 13000 f898"
  if [ "$ARM" = click ]; then echo "mouse up l"; fi
  echo "mouse move 0 0"; echo "s 3000000"
  echo "m 4bb3a 4"; echo "m 7a36 32"; echo "snap $W/after_$ARM$W8.snap"; echo q
} | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$W/open.snap" repl 2>&1 | grep -v "^mouse" > "$W/goto_$ARM$W8.txt"
grep -v '^\s*$' "$W/goto_$ARM$W8.txt"
