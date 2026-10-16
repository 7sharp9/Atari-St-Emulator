#!/bin/bash
# open_pile.sh: from pm143/run/p0k0_s4.snap open the goods-pile panel of pile $4bba2 (click_pile.sh's drive: camera (44,110),
# inspect icon, click (105,69)), dump the pile record, the slot table and the camera cell, and save the opened state as
# $PM_WORK/pile/goto/open.snap for the go-to click (goto_click.sh).
R=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$R/tools/rdis.py" ]; do R=$(dirname "$R"); done
cd "${M68000_ROOT:-$R}" || exit 1
W=${PM_WORK:-scratchpad/pm162}/pile/goto; mkdir -p "$W"
{
  echo "disk scratchpad/powermonger.st"
  printf 'w 4bb3a %04x%04x\n' 44 110; echo "s 3000000"
  echo "mouse move -400 -400"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
  echo "mouse move 75 191"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
  echo "mouse down l"; echo "mouse move 0 0"; echo "s 300000"; echo "mouse up l"; echo "mouse move 0 0"; echo "s 300000"
  echo "mouse move 30 -122"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
  echo "mouse down l"; echo "mouse move 0 0"; echo "hits 100000 95f6 7b10 9656"; echo "mouse up l"; echo "mouse move 0 0"; echo "s 300000"
  echo "m 4bba2 28"; echo "m 7a36 32"; echo "m 4bb3a 4"; echo "snap $W/open.snap"; echo q
} | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/pm143/run/p0k0_s4.snap repl 2>&1 | grep -v "^mouse" > "$W/open.txt"
grep -v '^\s*$' "$W/open.txt"
