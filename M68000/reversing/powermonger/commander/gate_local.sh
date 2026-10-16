#!/usr/bin/env bash
# gate_local.sh: does an order written into the LOCAL side's slot (side 1, $5801c) run like an AI side's?
# From pm142/rand1.snap, arms of BUDGET steps (default 30M), each with a watch on $5801a..$58021 (side 1's slot plus the
# two bytes below it, so a longword write starting at slot 0's +4 that covers side 1's bytes 0/1 is caught too).
#   ctl   no pokes
#   atk   side 1 group 0 (acting word $58044 := $188) attack $0c on side 4's lord 13 Base at (40,115)
#   men   side 1 group 0 get men $08 at own lord 9 City (15,92), 17 men at home
#   ctlL  no pokes, budget LONG (default 200M): does anything write side 1's slot in a long unaided run?
# Usage: gate_local.sh [arm...]; writes under $CMD_WORK/local_orders (default scratchpad/cmd1).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$HERE; while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); done; cd "$ROOT"
W=$ROOT/${CMD_WORK:-scratchpad/cmd1}/local_orders; mkdir -p "$W"
SNAP=scratchpad/pm142/rand1.snap
BUDGET=${BUDGET:-30000000}; LONG=${LONG:-200000000}
HITS="6a3a 6ac6 6b38 6c32 4a7a 4b80 6bea 3154 15122 6522 71ae 6e10 d2c8 77c2 d23a 4562 45d0"
SEL="w 58044 018802c4"          # longword: side 1 word $188 (group 0), side 2 word $2c4 kept
ST2="w 58020 02000200"          # longword: side 1 state 2, pad 0, side 2 bytes 0/1 = 02 00 kept
pokes() { case $1 in
  ctl|ctlL) ;;
  atk) echo "$SEL"; echo "w 5801c 010c2873"; echo "$ST2";;
  men) echo "$SEL"; echo "w 5801c 01080f5c"; echo "$ST2";;
  *) echo "unknown arm $1" >&2; exit 2;; esac; }
run() {
  local arm=$1 b=$BUDGET; [ "$arm" = ctlL ] && b=$LONG
  { echo "disk scratchpad/powermonger.st"; pokes "$arm"; echo "watch 5801a 8"; echo "hits $b $HITS"
    echo "snap $W/$arm.snap"; echo q; } > "$W/$arm.repl"
  ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl < "$W/$arm.repl" > "$W/$arm.out" 2> "$W/$arm.err"
}
for a in ${@:-ctl atk men ctlL}; do run "$a" & done; wait
