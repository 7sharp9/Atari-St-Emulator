#!/bin/bash
# Drive the player's order to the second captain by pigeon, live, from a snapshot.
# Usage: drive_order.sh [snap] [boxxy] [iconxy] [tag]
#   snap   default scratchpad/pm142/rand1.snap (local side 1, groups k0 and k1 live)
#   boxxy  click on the second captain's figure (box k1 rectangle (119,16,177,82)), default 135,35
#   iconxy the order icon, default 97,156 (posture aggressive, slot $26 -> order $16 param 2)
# hits are started before each mouse down. Output: $PM_WORK/<tag>.out and snapshots <tag>_*.snap.
set -e
d="$(cd "$(dirname "$0")" && pwd)"; while [ ! -f "$d/tools/rdis.py" ] && [ "$d" != / ]; do d=$(dirname "$d"); done
[ -f "$d/tools/rdis.py" ] || d="$M68000_ROOT"
cd "$d"
W="${PM_WORK:-scratchpad/pm150/captain2}"
SNAP="${1:-scratchpad/pm142/rand1.snap}"
BOX="${2:-135,35}"; ICON="${3:-97,156}"; TAG="${4:-run}"
bx=${BOX%,*}; by=${BOX#*,}; ix=${ICON%,*}; iy=${ICON#*,}
A="133d4 1343a 1349e 13456 134b2 9036 6d90 3ce8 13678 6ac6 6b2e 6b20 4562 45ee 35a0 3ef4 41dc 6b38"
M="m 57fd2 8
m 58034 4
m 58042 10
m 57fd8 12"
{
echo "disk scratchpad/powermonger.st"
echo "$M"
echo "mouse move -400 -400"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
echo "mouse move $bx $by"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
echo "mouse down l"; echo "mouse move 0 0"; echo "hits 300000 $A"
echo "mouse up l"; echo "mouse move 0 0"; echo "hits 600000 $A"
echo "$M"
echo "snap $W/${TAG}_sel.snap"
echo "mouse move $((ix-bx)) $((iy-by))"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
echo "mouse down l"; echo "mouse move 0 0"; echo "hits 300000 $A"
echo "mouse up l"; echo "mouse move 0 0"; echo "hits 600000 $A"
echo "$M"
echo "snap $W/${TAG}_ord.snap"
echo "hits ${FLY:-12000000} $A"
echo "$M"
echo "snap $W/${TAG}_late.snap"
echo "q"
} > "$W/${TAG}.repl"
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl < "$W/${TAG}.repl" > "$W/${TAG}.out" 2>&1
echo "done: $W/${TAG}.out"
