#!/bin/bash
# campaign_next.sh <won final.snap> <land> [out dir]: the next campaign land from a won land's loop end.
# From a loop.py final.snap stopped at $d2c8 after a winning retire (ratio 4): 40M steps through the victory routine
# to the main menu (strategy.md "The campaign": $3f2a0[land] := 1), Continue Conquest (160,102) to the conquest map
# $1120e, then a click on <land> (cell 24 x 40 px, col = land % 13, row = land / 13, the pointer in the cell's left
# 16 / top 32 px; only rows 0..4 without scrolling) to $11414, and on to the built land's first $f898.
# The land must be free and N/S/W/E of a conquered one, or $11414 is never reached.
# Writes <out>/{won.snap, map.snap, built.snap, build.txt}; prints $3f2a0[0..3] after the win and $580a4 at the pick.
d=$(cd "$(dirname "$0")" && pwd); R=$d; while [ ! -f "$R/tools/rdis.py" ]; do R=$(dirname "$R"); done
cd "$R"; P=reversing/powermonger/py
S=$1; LAND=$2; O=${3:-${CMD_WORK:-scratchpad/cmd1}/campaign/l$LAND}; mkdir -p $O
X=$(( 8 + 24 * (LAND % 13) + 8 )); Y=$(( 8 + 40 * (LAND / 13) + 12 ))
python3 $P/clicks.py disk:scratchpad/powermonger.st s:40000000 m:3f2a0:4 snap:$O/won.snap \
  home 160,102 bp:1120e:30000000 s:20000000 snap:$O/map.snap \
  home $X,$Y bp:11414:5000000 m:580a4:2 u:f898:80000000 s:30000000 u:f898:5000000 snap:$O/built.snap q > $O/build.cmds
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume $S repl < $O/build.cmds > $O/build.txt 2>&1
grep -E 'breakpoint|saved to' $O/build.txt
grep -E '^[0-9a-f]{2}( [0-9a-f]{2})+$' $O/build.txt | sed -n '1s/^/$3f2a0: /p;2s/^/$580a4: /p'
