#!/bin/bash
# Fresh captures for the picture-island and disk-block gate (gate_pictures.py), from n0.snap (py/run_drive.sh).
# Writes pic/ent_N.snap + exit_N.snap (the $15a20 entry and the $15b8e return) for N = 15, 25, 85 (picture islands)
# and 6, 99 (parameter block from the disk).
# POKE: the island number `ww 1d566 N`, at the entry of the block loader $1b142 (after the code-word screen, before
# it reads N), so the block, the picture and the build all follow N as they would for an island chosen in play.
# A poke on the map screen (capture_islands.sh's N > 100 runs) is too late for N <= 100: the block in $1defe stays
# island 1's.
d=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$d/tools/rdis.py" ] && [ "$d" != / ]; do d=$(dirname "$d"); done
cd "$d" || exit 1
W=scratchpad/archipelagos; DLL=bin/Debug/net8.0/M68000.dll
mkdir -p $W/pic
for N in 15 25 85 6 99; do
ATARI_NOTRACE=1 dotnet exec $DLL resume $W/n0.snap repl --disk-a $W/tmb58.st 2>&1 <<E2 | grep -E "breakpoint|gave|ILLEGAL|bad"
kbd 02
s 40000
kbd 82
s 100000
kbd 1c
s 40000
kbd 9c
bp 1b142 3000000
ww 1d566 $(printf '%04x' $N)
bp 15a20 8000000
snap $W/pic/ent_$N.snap
bp 15b8e 60000000
snap $W/pic/exit_$N.snap
q
E2
done
