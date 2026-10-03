#!/bin/bash
# click_hits.sh <snap> "<hex addrs>" <x,y> [toggle=1]
# Examine-tool click on screen (x,y) with a `hits` census over the click; prints the hits table and
# $57fea, $7a36 (dialog descriptor), $7a3c (dialog id), and the first 352 bytes of panel slot 0 ($7bac).
# toggle=1 first clicks the inspect icon (75,191), which sets $57fea; toggle=0 gives the no-toggle control.
# Pointer motion is the README trap sequence of ../clicks.py (home, 1:1 move, 300000-step hold).
# Root: $M68000_ROOT, else four levels above this script (M68000/). Needs scratchpad/powermonger.st.
# Ash on pm123/win/m1_s0.snap at 218,70: hits 95f6 7b10 a91a a738 = 1 each (strategy.md "How a panel opens").
ROOT=${M68000_ROOT:-$(cd "$(dirname "$0")/../../../.." && pwd)}
cd "$ROOT" || exit 1
SNAP=$1; ADDRS=$2; XY=$3; TOG=${4:-1}
x=${XY%,*}; y=${XY#*,}; px=0; py=0
{
  echo "mouse move -400 -400"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
  if [ "$TOG" = 1 ]; then
    echo "mouse move 75 191"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
    echo "mouse down l"; echo "mouse move 0 0"; echo "s 300000"; echo "mouse up l"; echo "mouse move 0 0"; echo "s 300000"
    px=75; py=191
  fi
  echo "mouse move $((x-px)) $((y-py))"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
  echo "mouse down l"; echo "mouse move 0 0"; echo "hits 300000 $ADDRS"; echo "mouse up l"; echo "mouse move 0 0"; echo "s 300000"
  echo "m 57fea 2"; echo "m 7a36 8"; echo "m 7a3c 2"; echo "m 7bac 160"
  echo q
} | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl --disk-a scratchpad/powermonger.st 2>&1 | grep -v "^mouse"
