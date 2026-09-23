#!/usr/bin/env bash
# run from M68000/; output in $PM_WORK (default scratchpad/pmwork)
# build land k for real from pm67_ok_pre (README "Driving a later land"), settle, census.
# usage: build_land.sh <k> [settle-steps] [season 0-3: pokes byte $58146 at $13b9a]   (run from M68000/)
k=$1; settle=${2:-30000000}; season=$3; tag=k$k${season:+_s$season}
d=${PM_WORK:-scratchpad/pmwork}; mkdir -p $d
seed=$(printf '%08x' $((k*0xb+0x3fb))); pages=$(printf '%04x0000' $((k*0x96+0x672)))
# the season is byte[$58146] & 3, read at $13bdc before $10d1e: poke it here
SEASON_POKE=$( [ -n "$season" ] && printf 'w 58146 %02x190750' $((0x1c+season)) || echo 'r' )
cat > $d/$tag.cmds <<C
w 2df92 001400b1
w 2df8e 001400b1
w 2df96 00010001
u 13b9a 80000000
$SEASON_POKE
w 580a0 $seed
w 5809c $pages
u 13ce6 80000000
s $settle
u f898 5000000
snap $d/$tag.snap
q
C
start=$(date +%s)
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/pm67_ok_pre.snap repl --disk-a scratchpad/powermonger.st < $d/$tag.cmds > $d/$tag.txt 2>&1
echo "$tag $(( $(date +%s)-start ))s $(grep -E 'reached|gave up' $d/$tag.txt | tr '\n' ' ')"
py -3 reversing/powermonger/py/census.py $d/$tag.snap
