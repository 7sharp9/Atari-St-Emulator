#!/usr/bin/env bash
# gate_retire.sh: end the land from the local side's slot (side 1, $5801c, state 2) and read the verdict.
# Arms from pm142/rand1.snap (BUDGET steps, default 50M, run as 5 x 10M hits chunks with RAM dumps + snapshots):
#   ctl       no pokes (the verdict must not run)
#   post      $2e into side 1's slot (bytes 01 2e 00 00; +4 longword untouched, state already 2): ratio 0 -> defeat
#   postwin   as post, plus $57fce := 4 in the same poke batch ($6a3a runs before $d23a in the tick): victory
#   dissolve  no $2e; side 1 group 0's owner word $51690 := 0 (the state $2776 leaves): $d23a posts $2e itself
#   *0        the same with $3f2a0[0..3] zeroed first, to see whether the verdict writes the conquest flag
# Also: d2c8 = post, stop at the first $d2c8 and snapshot (the README's two-pass method; win/lose arms resume from it).
# Usage: gate_retire.sh [arm...]; outputs under $CMD_WORK/retire.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$HERE; while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); done; cd "$ROOT"
W=$ROOT/${CMD_WORK:-scratchpad/cmd1}/retire; mkdir -p "$W"
SNAP=scratchpad/pm142/rand1.snap
CHUNK=${CHUNK:-10000000}; N=${N:-5}
H="d2c8 1a4da 1a5b2 1a2bc 13de8 13e8e 6e10 71ae d25a 6a3a d23a 1bd30"
POST="w 5801c 012e0000"; RAT4="w 57fcc 00740004"; DIS="w 51690 00000001"; Z="w 3f2a0 00000000"  # neighbours from rand1
pokes() { case ${1%0} in
  ctl) ;; post) echo "$POST";; postwin) echo "$POST"; echo "$RAT4";; dissolve) echo "$DIS";;
  *) echo "unknown arm $1" >&2; exit 2;; esac
  case $1 in *0) echo "$Z";; esac; }
dump() { echo "m 57fce 2"; echo "m 3f2a0 4"; echo "m 2df6e 2"; echo "m 51690 2"; echo "m 5801c 6"; echo "r"; }
run() {
  local arm=$1
  if [ "$arm" = d2c8 ]; then
    { echo "disk scratchpad/powermonger.st"; echo "$POST"; echo "bp d2c8 5000000"; dump; echo "snap $W/d2c8.snap"; echo q; } > "$W/d2c8.repl"
  else
    { echo "disk scratchpad/powermonger.st"; pokes "$arm"; dump
      for i in $(seq 1 "$N"); do echo "hits $CHUNK $H"; dump; echo "snap $W/${arm}_$i.snap"; done; echo q; } > "$W/$arm.repl"
  fi
  ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl < "$W/$arm.repl" > "$W/$arm.out" 2> "$W/$arm.err"
}
for a in ${@:-ctl post postwin dissolve post0 postwin0 d2c8}; do run "$a" & done; wait
