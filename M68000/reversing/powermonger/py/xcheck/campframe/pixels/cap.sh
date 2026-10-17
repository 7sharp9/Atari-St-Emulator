#!/usr/bin/env bash
# cap.sh <snap> <name> <nframes> [pre-steps]: n consecutive $f898 frames (no pokes), dumped to $PM_WORK/camp/cap/<name>_i.{snap,ram,json}
d=$(cd "$(dirname "$0")" && pwd)
while [ ! -f "$d/tools/rdis.py" ]; do d=$(dirname "$d"); [ "$d" = / ] && { echo "no repo root"; exit 1; }; done
cd "$d"
snap=$1; name=$2; n=$3; pre=${4:-0}
out=${PM_WORK:-scratchpad/pmwork}/camp/cap; mkdir -p "$out"
{
  echo "disk scratchpad/powermonger.st"
  [ "$pre" != 0 ] && echo "s $pre"
  echo "u f898 5000000"
  for i in $(seq 0 $((n-1))); do echo "snap $out/${name}_$i.snap"; echo "bpc f898 1 5000000"; done
  echo q
} > "$out/$name.cmds"
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$snap" repl < "$out/$name.cmds" > "$out/$name.txt" 2>&1
uv run python reversing/powermonger/py/snap2ram.py "$out"/${name}_*.snap
for i in $(seq 0 $((n-1))); do uv run python reversing/powermonger/py/dump_frame.py "$out/${name}_$i.ram" "$out/${name}_$i.json"; done
