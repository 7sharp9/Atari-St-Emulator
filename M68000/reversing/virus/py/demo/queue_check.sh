#!/bin/bash
# The infection target queue $27134..$2714b (reversing/virus/demo.md, "The carried-over table"), from capture_death.sh's N1 (next demo
# after a natural game over, seed poked at scatter B) and E1 (after an ESC).  About 2 minutes.  Nothing is poked here.
cd "$(dirname "$0")/../../../.." || exit 1
D=${VIRUS_WORK:-scratchpad/virus}/demo/death
R() { ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$1" repl 2>&1; }
echo "== N1, tick 1: the advance routine \$232e6 reads the map cell under entry 0 (D3 low byte after the mask at \$23314)"
{ echo "bp 232e6 20000000"; echo "bp 23314 100000"; echo "r"; echo "m 27134 6"; echo q; } | R $D/N1.snap | grep -E "^D0|^[0-9a-f]{2}( |$)" | tail -2
echo "== writes to entries 0..2 (\$27134, 18 bytes): N1 over 60M steps (a held queue writes nothing), E1 over 3M steps (positive control)"
echo "N1: $({ echo "watch 27134 18"; echo "s 60000000"; echo q; } | R $D/N1.snap | grep -c WATCH) writes"
echo "E1: $({ echo "watch 27134 18"; echo "s 3000000"; echo q; } | R $D/E1.snap | grep -c WATCH) writes"
echo "== first call of the homing behaviour \$21d62 (reads \$27134 as the target): tick and the 24 table bytes"
for s in N1 E1; do echo "$s:"; { echo "bp 21d62 30000000"; echo "m 32a44 2"; echo "m 27134 24"; echo q; } | R $D/$s.snap | grep -E "^[0-9a-f]{2} "; done
