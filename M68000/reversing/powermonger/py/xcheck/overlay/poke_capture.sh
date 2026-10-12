#!/usr/bin/env bash
# Capture one state + next-frame pair from pm88_f1.snap with the camera on a cell,
# applying labelled REPL pokes at the $f898 frame driver just before the state snap.
# Run from M68000/ (or anywhere: the repo root is found by walking up to tools/rdis.py).
#   poke_capture.sh <name> <camx> <camy> [m-addr ...] -- [w-line ...]
# e.g. poke_capture.sh ctl 22 46 51bfc 51c92 --
#      poke_capture.sh plough 22 46 51bfc -- "w 51c1c 00080000"
# Every name gets: <name>.cmds, <name>.txt (REPL output: the `m` lines show the
# records at the poke point, before the pokes), <name>_0/1.snap/.ram/.json.
# Output in ${PM_WORK:-scratchpad/pm156}/overlay/cap.
#
# Labelled poke always applied: `w 2c990 a8100000` clears pm88_f1's stuck
# sample-busy flag $2c993 (keeps $2c990..$2c992), as py/xcheck/ruin_capture.sh.
set -eu
d=$(cd "$(dirname "$0")" && pwd)
while [ ! -f "$d/tools/rdis.py" ]; do d=$(dirname "$d"); [ "$d" = / ] && { echo "no repo root"; exit 1; }; done
cd "$d"
name=$1 cx=$2 cy=$3; shift 3
ms=(); while [ $# -gt 0 ] && [ "$1" != -- ]; do ms+=("$1"); shift; done
[ $# -gt 0 ] && shift
out=${PM_WORK:-scratchpad/pm156}/overlay/cap; mkdir -p "$out"
{
  echo "w 2c990 a8100000"
  printf 'w 4bb3a %04x%04x\n' "$cx" "$cy"
  echo "s 2000000"
  echo "u f898 5000000"
  for a in ${ms[@]+"${ms[@]}"}; do echo "m $a 50"; done
  for w in "$@"; do echo "$w"; done
  echo "snap $out/${name}_0.snap"
  echo "bpc f898 1 5000000"
  echo "snap $out/${name}_1.snap"
  echo q
} > "$out/$name.cmds"
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/pm88_f1.snap repl \
  --disk-a scratchpad/powermonger.st < "$out/$name.cmds" > "$out/$name.txt" 2>&1 || true
if [ ! -f "$out/${name}_1.snap" ]; then
  echo "$name: no next frame: $(grep -m1 -E 'Step failed|Unhandled' "$out/$name.txt")"; exit 0
fi
echo "$name: $(grep -cE 'reached|hit \(' "$out/$name.txt") of 2 stops reached"
uv run python reversing/powermonger/py/snap2ram.py "$out/${name}_0.snap" "$out/${name}_1.snap" >/dev/null
for i in 0 1; do
  uv run python reversing/powermonger/py/dump_frame.py "$out/${name}_$i.ram" "$out/${name}_$i.json" | tail -1
done
