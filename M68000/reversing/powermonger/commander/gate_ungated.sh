#!/usr/bin/env bash
# gate_ungated.sh - the order cases gate_orders.sh left open (commander handoff Open 4), in gate_orders.sh's structure: one
# arm per case, each arm and its control at the same step budget from the same snapshot with the same pokes but the order.
# Side 3 (an AI side) has its slot $58028 at state 2 (the AI silent); $58042[3] names the acting group ($400 group 0, run at
# once; $402/$404 groups 1/2, by carrier pigeon). Slot bytes 1..3 = type, x, y. The REPL keeps one watch range: the acting
# group's lead bytes 30/31 (prev mode = the arrival mode, current mode), or for the click arms the five command slots.
# Each run is two `hits` chunks of BUDGET/2 with a snapshot after each (<arm>.mid.snap, <arm>.snap); the check sums them.
#   from pm142/rand1.snap (side 3 group 0 at (38,83) with 12 boats, group 1 at lord 5's City (29,60)):
#   ctlL / ctlL1  no order, group 0's / group 1's lead watched
#   goto      $02 21 48  cell (33,72), group 0                    $6b8e -> $3888 (state 5, 30(lead) := $1e at $38c0); mode $1e -> $1515c -> $35f4
#   home      $0a 00 00  group 0; its lead's home 34(lead) is lord 12's Tower (33,70)
#                                                                 $6c16 -> $3c08 (state 7, 30(lead) := $4c at $3c6a); mode $4c -> $16176
#   ally      $1e 27 3d  side 2's lord 11 (39,61), 12 boats        gate_orders.sh's ally arm, accepted: the control of allyng
#   allyng    as ally, group 0's boats poked 12 -> 0 ($519bc)       $33b0: v = rel 0 + tribute 0 - 2 < 0, refused
#   allyp     $1e 0f 5c  side 1's (the player's) lord 9 (15,92)     $33b0 -> $c706 opens panel $1a
#   invent    $0e 1d 3c  own lord 5 (29,60), a WorkShop; group 1   $4562; $6c48 -> $3154; mode $22 -> $151a8 -> $5fa0 -> $5cde accepted
#   from allyp.mid.snap (the panel open on the player's screen; the pointer homed then moved to the button in all three):
#   allyyes / allyno  a click on YES (130,138) / NO (240,138)      YES $146 -> order $2a in side 1's slot -> $6dea -> $34a8; NO $162 -> $32
#   ctlP      no click
#   from pm143/run/rand1_s2.snap (rand1 + 100M steps: side 3's lord 3 City (37,13) holds 13 boats; group 2, 32 men,
#   posture 4, stands at (36,17)):
#   equip / ctlE    $10 25 0d  lord 3, group 2 (pigeon)            $6c6a -> $3154; mode $6e -> $15740 -> $61f8, lord arm $6306 -> $6352
#   inventT / ctlT  $0e 25 0d  lord 3, group 2, with side 3's throttle word $580a6[3].8 poked $128b -> 0 in both
#                   (the reload $60dc/$5cde writes is word8 + 4: 4 deliveries per credit instead of 4751)
# Usage: gate_ungated.sh [arm...]  (no args: the first two groups in order, then the check). BUDGET (60000000), PAR (6),
#   W (default: this script's directory/out). CHECK_ONLY=1 re-runs the check on existing outputs.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$HERE; while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); done; cd "$ROOT"
W=${W:-$ROOT/${CMD_WORK:-scratchpad/cmd1}/ungated}; mkdir -p "$W"
SNAP0=scratchpad/pm142/rand1.snap; SNAP2=scratchpad/pm143/run/rand1_s2.snap
BUDGET=${BUDGET:-60000000}; PAR=${PAR:-6}; HALF=$((BUDGET / 2))
HITS="6b8e 3888 1515c 6c16 3c08 16176 35f4 6d32 3154 15754 33b0 3458 34a8 c706 cada c9f8 6dea 6e56 4c2a 4562 6c48 151a8 5fa0 5cde 600a 60dc 6120 6c6a 15740 61f8 6306 6352 638c 6128"
G0="w 58048 0400053c"; G1="w 58048 0402053c"; G2="w 58048 0404053c"; ST2="w 5802c 02000400"  # longwords: keep side 4's $53c and slot bytes 04 00
L0=53b5a; L1=5257a; L2=528fe          # $51b66 + lead + 30 for side 3's group 0 ($1fd6), group 1 ($9f6), group 2 ($d7a)
YES="130 138"; NO="240 138"           # panel $1a at (112,76) (slot $7a36: x/16 7, y $4c), from snap_render of allyp.mid.snap
base() { case $1 in allyyes|allyno|ctlP) echo "$W/allyp.mid.snap";; equip|ctlE|inventT|ctlT) echo $SNAP2;; *) echo $SNAP0;; esac; }
pokes() { # arm -> its REPL poke lines
  case $1 in
    ctlL)    echo "$G0"; echo "w 58028 03000000"; echo "$ST2"; echo "watch $L0 2";;
    ctlL1)   echo "$G1"; echo "w 58028 03000000"; echo "$ST2"; echo "watch $L1 2";;
    goto)    echo "$G0"; echo "w 58028 03022148"; echo "$ST2"; echo "watch $L0 2";;
    home)    echo "$G0"; echo "w 58028 030a0000"; echo "$ST2"; echo "watch $L0 2";;
    ally)    echo "$G0"; echo "w 58028 031e273d"; echo "$ST2"; echo "watch $L0 2";;
    allyng)  echo "$G0"; echo "w 519bc 0000000c"; echo "w 58028 031e273d"; echo "$ST2"; echo "watch $L0 2";;  # group 1 keeps its 12 boats
    allyp)   echo "$G0"; echo "w 58028 031e0f5c"; echo "$ST2"; echo "watch $L0 2";;
    invent)  echo "$G1"; echo "w 58028 030e1d3c"; echo "$ST2"; echo "watch $L1 2";;
    equip)   echo "$G2"; echo "w 58028 0310250d"; echo "$ST2"; echo "watch $L2 2";;
    ctlE)    echo "$G2"; echo "w 58028 03000000"; echo "$ST2"; echo "watch $L2 2";;
    inventT) echo "$G2"; echo "w 5810e 0000000c"; echo "w 58028 030e250d"; echo "$ST2"; echo "watch $L2 2";;  # word +10 stays $000c
    ctlT)    echo "$G2"; echo "w 5810e 0000000c"; echo "w 58028 03000000"; echo "$ST2"; echo "watch $L2 2";;
    *) echo "unknown arm $1" >&2; exit 2;;
  esac
}
MOVE() { echo "mouse move -400 -400"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
         echo "mouse move $1 $2"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"; }   # py/clicks.py's homing, 1:1 after it
run() { # arm
  local arm=$1 xy
  { echo "disk scratchpad/powermonger.st"
    case $arm in
      allyyes|allyno|ctlP)   # hits starts before the press: the click is consumed while the button is down (CLAUDE.md)
        xy=$YES; [ $arm = allyno ] && xy=$NO
        MOVE $xy; echo "watch 58016 32"
        if [ $arm != ctlP ]; then echo "mouse down l"; echo "mouse move 0 0"; fi
        echo "hits 300000 $HITS"
        if [ $arm != ctlP ]; then echo "mouse up l"; echo "mouse move 0 0"; fi
        echo "hits $((HALF - 300000)) $HITS";;
      *) pokes "$arm"; echo "hits $HALF $HITS";;
    esac
    echo "snap $W/$arm.mid.snap"; echo "hits $HALF $HITS"; echo "snap $W/$arm.snap"; echo q; } > "$W/$arm.repl"
  ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$(base "$arm")" repl < "$W/$arm.repl" > "$W/$arm.out" 2> "$W/$arm.err"
}
P1="ctlL ctlL1 goto home ally allyng allyp invent equip ctlE inventT ctlT"; P2="allyyes allyno ctlP"
batch() { local n=0; for a in "$@"; do run "$a" & n=$((n + 1)); if [ $((n % PAR)) -eq 0 ]; then wait; fi; done; wait; }
if [ -z "${CHECK_ONLY:-}" ]; then
  if [ $# -gt 0 ]; then batch "$@"; else batch $P1; batch $P2; fi
fi
uv run python "$HERE/check_ungated.py" "$W"
