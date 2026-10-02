#!/usr/bin/env bash
# usage: cap_land.sh <k> : build land k from pm67_ok_pre (build_land.sh pokes) and snapshot at the entry of the build routines
# run from M68000/. snaps: $PM_WORK/cap/k<k>_<addr>.snap (default scratchpad/pm141/agents/build)
k=$1
B=${PM_WORK:-scratchpad/pm141/agents/build}/cap; mkdir -p $B
seed=$(printf '%08x' $((k*0xb+0x3fb))); pages=$(printf '%04x0000' $((k*0x96+0x672)))
cat > $B/k$k.cmds <<C
w 2df92 001400b1
w 2df8e 001400b1
w 2df96 00010001
u 13b9a 80000000
w 580a0 $seed
w 5809c $pages
bpc 10d1e 1 60000000
snap $B/k${k}_10d1e.snap
bpc 1073c 1 60000000
snap $B/k${k}_1073c.snap
bpc 4672 1 60000000
snap $B/k${k}_4672.snap
bpc 238c 1 60000000
snap $B/k${k}_238c.snap
bpc 2906 1 60000000
snap $B/k${k}_2906.snap
q
C
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/pm67_ok_pre.snap repl --disk-a scratchpad/powermonger.st < $B/k$k.cmds > $B/k$k.txt 2>&1
