#!/bin/bash
# load_into.sh <file-panel-snap> <disk.st> <tag> <steps> [slot-row-y]
# Natural LOAD into a live land: click the slot row (default A, y=87) and LOAD (170,81) on a snapshot with
# the FILE panel open at 128,67, stop at $1bdf8 ($1bd70's exit) and snap <tag>_L0, then census the commander
# camp-wait decision $65b4, the commander tick $6522 and $66e8 over <steps>, print the clock $2df72, snap <tag>_end.
# One variable between runs: the disk (built by mk_savedisk.py from a source snapshot).
ROOT=$(cd "$(dirname "$0")" && while [ ! -f tools/rdis.py ] && [ "$PWD" != / ]; do cd ..; done; pwd)
cd "$ROOT" || exit 1
W=${PM_WORK:-scratchpad/pm150/saveload}/out; mkdir -p "$W"
SNAP=$1; DISK=$2; T=$3; N=$4; Y=${5:-87}
home() { echo "mouse move -400 -400"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"; }
{ echo "disk $DISK"; echo "m 2df72 2"
  home; echo "mouse move 147 $Y"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
  echo "mouse down l"; echo "mouse move 0 0"; echo "hits 600000 75c4 75ce"; echo "mouse up l"; echo "mouse move 0 0"; echo "s 300000"
  echo "m e290 12"
  home; echo "mouse move 170 81"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
  echo "mouse down l"; echo "mouse move 0 0"; echo "bp 1bdf8 5000000"; echo "m 2df72 2"; echo "snap $W/${T}_L0.snap"
  echo "mouse up l"; echo "mouse move 0 0"
  echo "hits $N 65b4 6522 66e8 1bef2 1bef8"; echo "m 2df72 2"; echo "snap $W/${T}_end.snap"; echo q
} > "$W/$T.cmds"
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl < "$W/$T.cmds" > "$W/$T.txt" 2>&1
grep -v '^mouse' "$W/$T.txt"
python3 reversing/powermonger/py/snap2ram.py "$W/${T}_L0.snap" "$W/${T}_end.snap"
