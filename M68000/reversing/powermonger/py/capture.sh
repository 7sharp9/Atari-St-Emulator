#!/usr/bin/env bash
# run from M68000/; output in $PM_WORK/cap (default scratchpad/pmwork)
# capture.sh <src.snap> <name> <camx> <camy> <nframes> [settle] [yawword]
# pokes the camera ($4bb3a/$4bb3c) onto a cell, settles, snaps N successive $f898 frames.
# From pm88_f1.snap, add `w 2c990 a8100000` first (its sample-busy flag $2c993 is stuck at $ff;
# a camera move that queues a sound otherwise waits at $1ae40 forever, py/xcheck/ruin_capture.sh).
src=$1; name=$2; cx=$3; cy=$4; n=$5; settle=${6:-2000000}; yaw=$7
d=${PM_WORK:-scratchpad/pmwork}/cap; mkdir -p $d
{
  printf 'w 4bb3a %04x%04x\n' $cx $cy
  [ -n "$yaw" ] && printf 'w ff9a %s0015\n' $yaw
  echo "s $settle"
  echo "u f898 5000000"
  for i in $(seq 0 $((n-1))); do
    echo "snap $d/${name}_$i.snap"
    echo "bpc f898 1 5000000"
  done
  echo q
} > $d/$name.cmds
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume $src repl --disk-a scratchpad/powermonger.st < $d/$name.cmds > $d/$name.txt 2>&1
grep -E "hit \(|gave up" $d/$name.txt | awk '{print $7}' | tr '\n' ' '; echo
uv run python reversing/powermonger/py/snap2ram.py $d/${name}_*.snap
for i in $(seq 0 $((n-1))); do uv run python reversing/powermonger/py/dump_frame.py $d/${name}_$i.ram $d/${name}_$i.json; done
