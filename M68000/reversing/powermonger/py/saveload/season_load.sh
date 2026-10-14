#!/bin/bash
# season_load.sh [steps]
# Does a LOAD bring the slot's season $57fd0 with it? $57fd0 lies inside the LOAD region $3f768..$58368,
# the live tileset ([$ff9e] = $2e000, +3712) does not. Two disks built by mk_savedisk.py from
# pm150/saveload/out/file.ram (rand1, season 4): ctl.st, slot A unchanged; s0.st, slot A with $57fd0 := 0
# (a labelled poke of the slot's one season byte; cmp shows one byte). Each is loaded into file.snap by
# load_into.sh's clicks under `watch 57fd0 2`, then run <steps>, census the land rebuild $13d1a, the season
# read $13bdc and the dissolve $1abaa, and snap; season_tilediff.py says which season's art the live tileset holds. Output in $PM_WORK/season (default scratchpad/pm161/season).
ROOT=$(cd "$(dirname "$0")" && while [ ! -f tools/rdis.py ] && [ "$PWD" != / ]; do cd ..; done; pwd)
cd "$ROOT" || exit 1
W=${PM_WORK:-scratchpad/pm161}/season; mkdir -p "$W"
N=${1:-20000000}
SRC=scratchpad/pm150/saveload/out
python3 - "$SRC/file.ram" "$W/s0.ram" <<'E'
import sys
d = bytearray(open(sys.argv[1], 'rb').read()); d[0x57fd0:0x57fd2] = b'\0\0'; open(sys.argv[2], 'wb').write(d)
E
python3 reversing/powermonger/py/saveload/mk_savedisk.py "$SRC/file.ram" "$W/ctl.st" A="$SRC/file.ram"
python3 reversing/powermonger/py/saveload/mk_savedisk.py "$SRC/file.ram" "$W/s0.st" A="$W/s0.ram"
cmp -l "$W/ctl.st" "$W/s0.st"
home() { echo "mouse move -400 -400"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"; }
for T in ctl s0; do
  { echo "disk $W/$T.st"; echo "m 57fd0 2"
    home; echo "mouse move 147 87"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
    echo "mouse down l"; echo "mouse move 0 0"; echo "s 600000"; echo "mouse up l"; echo "mouse move 0 0"; echo "s 300000"
    home; echo "mouse move 170 81"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
    echo "watch 57fd0 2"
    echo "mouse down l"; echo "mouse move 0 0"; echo "bp 1bdf8 5000000"; echo "m 57fd0 2"; echo "snap $W/${T}_L0.snap"
    echo "mouse up l"; echo "mouse move 0 0"
    echo "hits $N 13d1a 13bdc 1abaa"; echo "m 57fd0 2"; echo "snap $W/${T}_end.snap"; echo q
  } > "$W/$T.cmds"
  ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SRC/file.snap" repl < "$W/$T.cmds" > "$W/$T.txt" 2>&1
  echo "== $T"; grep -E 'WATCH|hits over|^  \$0|^[0-9a-f]{2} [0-9a-f]{2}$|breakpoint' "$W/$T.txt"
  python3 reversing/powermonger/py/snap2ram.py "$W/${T}_L0.snap" "$W/${T}_end.snap"
done
python3 reversing/powermonger/py/season_tilediff.py "$W"/ctl_L0.ram "$W"/ctl_end.ram "$W"/s0_L0.ram "$W"/s0_end.ram
