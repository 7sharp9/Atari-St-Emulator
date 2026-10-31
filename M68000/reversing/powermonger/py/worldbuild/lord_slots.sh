#!/usr/bin/env bash
# usage: [PAGES0=1] lord_slots.sh [k...]   (run from M68000/; default every land 0..143)
# Builds each land k from pm67_ok_pre with the build_land.sh pokes, stops at the end of the build ($13ce6) and dumps
# $4f914 (the lord high-water offset) and the 64 lord records $4e514. lord_slots.py then lists the slots below
# $4f914/32 that $2eac consumed but left unfilled (strategy.md "Towns, ranks and water").
# PAGES0=1: the Play Random Land roll ($5809c == 0, as build_land.sh), into lordslots0/.
# Output: $PM_WORK/lordslots{,0}/k<k>.txt (default PM_WORK=scratchpad/pm168)
B=${PM_WORK:-scratchpad/pm168}/lordslots${PAGES0:+0}; mkdir -p $B
ks=${*:-$(seq 0 143)}
for k in $ks; do
  seed=$(printf '%08x' $((k*0xb+0x3fb))); pages=$(printf '%04x0000' $((k*0x96+0x672)))
  [ -n "$PAGES0" ] && pages=00000000
  printf 'w 2df92 001400b1\nw 2df8e 001400b1\nw 2df96 00010001\nu 13b9a 80000000\nw 580a0 %s\nw 5809c %s\nu 13ce6 80000000\nm 5814a 2\nm 4f914 2\nm 4e514 2048\nq\n' $seed $pages > $B/k$k.cmds
  ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/pm67_ok_pre.snap repl --disk-a scratchpad/powermonger.st < $B/k$k.cmds > $B/k$k.txt 2>&1
done
