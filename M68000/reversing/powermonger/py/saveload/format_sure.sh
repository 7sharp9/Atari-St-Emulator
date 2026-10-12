#!/bin/bash
# format_sure.sh [file-panel-snap]
# FORMAT's ARE YOU SURE branch ($1bec2) with the game disk in the drive, then each answer:
#   FORMAT (170,117) -> OK on the save-disk requester (120,118): $1bd38 finds DATA\SPRITE8.DAT, $1bec2 asks
#   -> snap sure; from it CANCEL (200,118): $1beec "FORMAT HAS BEEN CANCELLED", no writes -> snap cancel
#   -> from it OK (120,118): 80 Write Track commands and the ID sector, the land repainted -> snap ok
# Mounts a copy of scratchpad/powermonger.st (disk writes stay in process memory; the copy is never written).
# Work dir $PM_WORK (default scratchpad/pm154/format); PNG of each snapshot via tools/snap_render.py.
ROOT=$(cd "$(dirname "$0")" && while [ ! -f tools/rdis.py ] && [ "$PWD" != / ]; do cd ..; done; pwd)
cd "$ROOT" || exit 1
W=${PM_WORK:-scratchpad/pm154/format}; mkdir -p "$W"
SNAP=${1:-scratchpad/pm150/saveload/out/file.snap}
cp scratchpad/powermonger.st "$W/game.st"
A="1ba72 1bf0e cce2 1bd38 1bec2 1bf04 1beec d9fc 1bf2e"
click() { echo "mouse move -400 -400"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
          echo "mouse move $1 $2"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
          echo "mouse down l"; echo "mouse move 0 0"; echo "hits $3 $A"; echo "mouse up l"; echo "mouse move 0 0"; echo "s 300000"; }
run() { # run <name> <from-snap> <click...>: one process, then the census, the FDC count and a render
  local name=$1 from=$2; shift 2
  { echo "disk $W/game.st"; while [ $# -gt 0 ]; do click "$1" "$2" "$3"; shift 3; done; echo "snap $W/$name.snap"; echo q; } > "$W/$name.cmds"
  ATARI_TRACE_FDC=1 ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$from" repl < "$W/$name.cmds" > "$W/$name.txt" 2>&1
  echo "== $name: write-track commands $(grep -c WRITE-TRACK "$W/$name.txt"), sectors skipped $(grep -c skipped "$W/$name.txt")"
  grep -E '^\s*\$0' "$W/$name.txt" | grep -v ' 0  first -1'
  uv run python tools/snap_render.py "$W/$name.snap" "$W/$name.png"
}
run sure "$SNAP" 170 117 6000000 120 118 6000000
run cancel "$W/sure.snap" 200 118 30000000
run ok "$W/sure.snap" 120 118 30000000
cmp -s scratchpad/powermonger.st "$W/game.st" && echo "the mounted copy is unchanged on the host"
