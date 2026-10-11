#!/bin/bash
# roundtrip.sh <file-panel-snap> <disk.st> <tag> [mid-steps] [save-slot-y] [load-slot-y]
# Natural FILE-panel drive in ONE emulator process (the emulator keeps disk writes in memory only):
#   click slot row (default B, y=99) -> SAVE (170,99) with a hits census -> snap <tag>_S
#   -> run mid-steps (default 30M) -> snap <tag>_P -> options icon (71,138) -> FILE (142,92: the options panel reopens at the origin $aeac left, 128,67)
#   -> slot row (default B) -> LOAD (170,81) with a hits census -> snap <tag>_L -> 30M more -> snap <tag>_L30.
# The start snapshot must have the FILE panel open at origin x=128,y=67 ($7a38=8,$7a39=$43).
# BP=1: stop at $1beae (save done) and $1bdf8 (load done) and snap <tag>_S0 / <tag>_L0 there.
# Work dir $PM_WORK (default scratchpad/pm150/saveload)/out. ATARI_TRACE_FDC=1 log in <tag>.txt.
ROOT=$(cd "$(dirname "$0")" && while [ ! -f tools/rdis.py ] && [ "$PWD" != / ]; do cd ..; done; pwd)
cd "$ROOT" || exit 1
W=${PM_WORK:-scratchpad/pm150/saveload}/out; mkdir -p "$W"
SNAP=$1; DISK=$2; T=$3; MID=${4:-30000000}; SY=${5:-99}; LY=${6:-$SY}
A="75c4 75ce 7740 77a2 e288 e29c 1bdfe 1bd70 1bd52 d9fc db46 1bf0e cce2 1bed4 1bf04 1bef8 1bef2 1bee6 12726"
home() { echo "mouse move -400 -400"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"; }
# click x y steps [bp-addr snap-path]: with BP=1 and a bp address, the census is replaced by a stop at
# the bp (the routine's exit) and a snapshot there, so the RAM is the transfer's own image.
click() { home; echo "mouse move $1 $2"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
          echo "mouse down l"; echo "mouse move 0 0"
          if [ -n "$BP" ] && [ -n "$4" ]; then echo "bp $4 $3"; echo "snap $5"; else echo "hits $3 $A"; fi
          echo "mouse up l"; echo "mouse move 0 0"; echo "s 300000"; }
{ echo "disk $DISK"; echo "watch e296"
  click 147 $SY 600000; echo "m e290 12"
  click 170 99 3000000 1beae $W/${T}_S0.snap; echo "m 1bbfa 4"; echo "snap $W/${T}_S.snap"
  echo "s $MID"; echo "snap $W/${T}_P.snap"
  click 71 138 600000; click 142 92 600000; click 147 $LY 600000; echo "m e290 12"
  click 170 81 3000000 1bdf8 $W/${T}_L0.snap; echo "m 1bbfa 4"; echo "snap $W/${T}_L.snap"
  echo "s 30000000"; echo "snap $W/${T}_L30.snap"; echo q
} > "$W/$T.cmds"
ATARI_TRACE_FDC=1 ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl < "$W/$T.cmds" > "$W/$T.txt" 2>&1
grep -v '^FDC\|^mouse' "$W/$T.txt" | grep -v ' 0  first -1'
for s in S P L L30 S0 L0; do [ -f "$W/${T}_$s.snap" ] || continue; python3 reversing/powermonger/py/snap2ram.py "$W/${T}_$s.snap" >/dev/null; done
