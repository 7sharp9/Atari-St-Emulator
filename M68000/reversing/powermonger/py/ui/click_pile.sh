#!/bin/bash
# click_pile.sh <snap> <camx> <camy> <x,y> [toggle=1] [hits addrs]: poke the camera cell, then examine-tool click at screen (x,y) with a `hits` census
# (ui/uiclick.py shape, py/clicks_ui/click_hits.sh). Prints the hits table, $57fea, slot table $7a36, dialog id $7a3c and panel slot 0 grid.
ROOT=${M68000_ROOT:-$(cd "$(dirname "$0")/../../../.." && pwd)}
cd "$ROOT" || exit 1
SNAP=$1; CX=$2; CY=$3; XY=$4; TOG=${5:-1}; ADDRS=${6:-"95f6 7b10 a91a 9656 9684 96ae e39e"}
x=${XY%,*}; y=${XY#*,}; px=0; py=0
{
  printf 'w 4bb3a %04x%04x\n' "$CX" "$CY"; echo "s 3000000"
  echo "mouse move -400 -400"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
  if [ "$TOG" = 1 ]; then
    echo "mouse move 75 191"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
    echo "mouse down l"; echo "mouse move 0 0"; echo "s 300000"; echo "mouse up l"; echo "mouse move 0 0"; echo "s 300000"
    px=75; py=191
  fi
  echo "mouse move $((x-px)) $((y-py))"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
  echo "mouse down l"; echo "mouse move 0 0"; echo "hits ${HITSTEPS:-300000} $ADDRS"; echo "mouse up l"; echo "mouse move 0 0"; echo "s 300000"
  echo "m 57fea 2"; echo "m 7a36 32"; echo "m 7a3c 2"; echo "m 7bac 400"
  echo q
} | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl --disk-a scratchpad/powermonger.st 2>&1 | grep -v "^mouse" > "${OUT:-/dev/stdout}"
