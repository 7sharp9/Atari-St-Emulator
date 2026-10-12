#!/usr/bin/env bash
# The Ruin frames run.sh scores, from M68000/: mission 1 (pm88_f1.snap) with the
# camera on each of its two Ruins, plus the (22,46) Ruin with its rebuild counter
# (building record byte 16, $4f980) poked to 70 and 100 so the $119b2 overlay
# shows 17 and 23 of its 24 rows. Each capture is two successive $f898 frames
# (name_0 is the state, name_1 the screen drawn from it). Output in
# ${PM_WORK:-scratchpad/pmwork}/xcheck/ruin.
#
# Labelled poke: pm88_f1.snap holds the sample player's busy flag $2c993 = $ff
# with Timer A stopped (TACR 0), so a camera move that queues a sound waits at
# $1ae40 forever; `w 2c990 a8100000` clears the flag and keeps $2c990..$2c992.
set -eu
d=${PM_WORK:-scratchpad/pmwork}/xcheck/ruin; mkdir -p "$d"
for spec in r1:22:46:- r2:29:63:- k70:22:46:46 k100:22:46:64; do
  IFS=: read -r name cx cy b16 <<< "$spec"
  {
    echo "w 2c990 a8100000"
    printf 'w 4bb3a %04x%04x\n' "$cx" "$cy"
    [ "$b16" != - ] && echo "w 4f980 ${b16}000000"
    echo "s 2000000"
    echo "u f898 5000000"
    for i in 0 1; do echo "snap $d/${name}_$i.snap"; echo "bpc f898 1 5000000"; done
    echo q
  } > "$d/$name.cmds"
  ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/pm88_f1.snap repl \
    --disk-a scratchpad/powermonger.st < "$d/$name.cmds" > "$d/$name.txt" 2>&1
  echo "$name: $(grep -cE 'reached|hit \(' "$d/$name.txt") of 3 stops reached"
done
uv run python reversing/powermonger/py/snap2ram.py "$d"/*.snap
