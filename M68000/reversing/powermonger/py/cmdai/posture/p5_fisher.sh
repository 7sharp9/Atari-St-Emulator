#!/usr/bin/env bash
# Posture 5's lasting effect on the side-3 fisherman (object 6, $51c92): watch its mode bytes 30..31 and its
# job bytes 6..7 for 200M steps after the forced trade, posture 5 against the posture-3 control (trade5_fwd.sh's pokes).
set -e
HERE=$(cd "$(dirname "$0")" && pwd); d=$HERE; while [ ! -f "$d/tools/rdis.py" ]; do d=$(dirname "$d"); done; cd "$d"
O=${PM_WORK:-scratchpad/pm167}/p5job; mkdir -p "$O"
S=scratchpad/pm162/posture/trade/at63f4.snap
N=${N:-20}
for p in 5 3; do for w in mode job; do
  case $w in mode) wa='watch 51cb0 2';; job) wa='watch 51c98 2';; esac
  { echo 'disk scratchpad/powermonger.st'; echo "w 51974 000${p}0002"; echo 'w 4e6f4 03000000'; echo 'w 4e6ec 00050000'
    echo "$wa"; for i in $(seq $N); do echo 'hits 10000000 6522'; echo 'm 51c92 50'; done; echo q; } |
    ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$S" repl > "$O/p${p}_$w.out" 2> "$O/p${p}_$w.err" &
done; done
wait
uv run python "$HERE/p5_fisher.py" "$O"
