#!/usr/bin/env bash
# natural entries of $2eac (the first 7) during the build of land k (run from M68000/): snapshots cap/nat<k>_2eac_<n>.snap, the entry registers are read from cap/nat<k>.txt by gate_build.py (townnat)
k=$1
B=${PM_WORK:-scratchpad/pm141/agents/build}/cap; mkdir -p $B
seed=$(printf '%08x' $((k*0xb+0x3fb))); pages=$(printf '%04x0000' $((k*0x96+0x672)))
{ echo "w 2df92 001400b1
w 2df8e 001400b1
w 2df96 00010001
u 13b9a 80000000
w 580a0 $seed
w 5809c $pages"
for n in 1 2 3 4 5 6 7; do echo "bpc 2eac 1 60000000
snap $B/nat${k}_2eac_$n.snap"; done; echo q; } > $B/nat$k.cmds
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/pm67_ok_pre.snap repl --disk-a scratchpad/powermonger.st < $B/nat$k.cmds > $B/nat$k.txt 2>&1
