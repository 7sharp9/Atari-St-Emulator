#!/usr/bin/env bash
# usage: p5_dismiss.sh   (run from anywhere under M68000/; output in ${PM_WORK:-scratchpad/pm168}/dismiss/)
# The dismiss order at posture 5: $1cc4 lets `men >> ($30fe = posture - 2)` men go (lsr.w D0,D2 at $1cec), least
# equipped first. From pm142/rand1.snap, side 3's group 0 ($51938 in the group-offset frame, 12 men) is given the dismiss
# $14 00 00 through its command slot as commander/gate_orders.sh's `dismiss` arm does, with its posture word poked first
# ($51974: 0002 0002 -> 000P 0002, keeping group 1's word). Arms P = 5 and the controls P = 3 and 2.
# Per arm: the registers at $1cec (D0 the shift, D2 the men), then over the next 400K steps the loop passes ($1d22), the
# $1b8c calls and the exit $1d30, and the group's men word after them (40M steps later the group has refilled).
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); done; cd "$ROOT"
W=${PM_WORK:-scratchpad/pm168}/dismiss; mkdir -p "$W"
for P in 5 3 2; do
  printf 'disk scratchpad/powermonger.st\nw 51974 000%s0002\nw 58048 0400053c\nw 58028 03140000\nw 5802c 02000400\nbp 1cec 40000000\nhits 400000 1d22 1b8c 1d30\nm 51920 2\nq\n' $P > "$W/p$P.repl"
  ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/pm142/rand1.snap repl < "$W/p$P.repl" > "$W/p$P.out" 2>&1
  echo "posture $P: $(grep -A8 'breakpoint $00001cec' "$W/p$P.out" | grep -oE 'D0:[0-9a-f]+|D2:[0-9a-f]+' | tr '\n' ' ')" \
       "after: $(grep -E '^  \$001d22|^  \$001b8c|^  \$001d30' "$W/p$P.out" | awk '{print $1, $2}' | tr '\n' ' ') men at end $(grep -E '^[0-9a-f]{2} [0-9a-f]{2}$' "$W/p$P.out")"
done
