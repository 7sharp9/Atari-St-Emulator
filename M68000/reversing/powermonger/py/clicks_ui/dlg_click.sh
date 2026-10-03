#!/bin/bash
# dlg_click.sh <snap> <x,y> <hex addrs...>
# Click a dialog button (no examine toggle) with a `hits` census over the click; dumps $7a36 (dialog
# descriptor), $3f2a0 (conquered-lands record) and $11420 before and after.
# Root: $M68000_ROOT, else four levels above this script (M68000/). Needs scratchpad/powermonger.st.
# pm142/yes_dlg.snap is the id-$18 "delete all of your conquered lands" dialog at screen (112,73); its
# YES cell is grid offset $7a (click 130,112), NO is $8a (click 202,112): YES gives hits 7658 1, 796e 1,
# 8838 53, $7a36 word 0 -> 0 and $3f2a0[0] 1 -> 0 (strategy.md "Dialogs").
ROOT=${M68000_ROOT:-$(cd "$(dirname "$0")/../../../.." && pwd)}
cd "$ROOT" || exit 1
SNAP=$1; XY=$2; shift 2; ADDRS="$*"; x=${XY%,*}; y=${XY#*,}
{ echo "m 7a36 8"; echo "m 3f2a0 8"; echo "m 11420 2"
  echo "mouse move -400 -400"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
  echo "mouse move $x $y"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
  echo "mouse down l"; echo "mouse move 0 0"; echo "hits 300000 $ADDRS"; echo "mouse up l"; echo "mouse move 0 0"; echo "s 300000"
  echo "m 7a36 8"; echo "m 3f2a0 8"; echo "m 11420 2"; echo q
} | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl --disk-a scratchpad/powermonger.st 2>&1 | grep -v "^mouse"
