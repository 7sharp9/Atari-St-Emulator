#!/bin/bash
# xfer_timing.sh [snap]
# Why a captain-figure click in transfer mode is handled twice (strategy.md, the captain boxes and the tick tail).
# Both arms: the transfer icon (103,186) clicked for real, then the figure click at (135,35) is POKED as a latched
# click (`$2df8e`, `$2df96`) with the press stamp `$2df74` equal to the clock `$2df70` (both set to $200):
#   A: poked at $130fc, after this pass's clock increment $1302e and before its UI sections
#   B: poked at the tail $1373c, after the UI sections
# Same snapshot and budget; expect A: $133d4 twice, $04 then $22 posted, $6d90 1, $3ce8 0 (the $22 dropped);
# B: $133d4 once, $04 only. Work dir $PM_WORK (default scratchpad/pm160/xfer).
ROOT=$(cd "$(dirname "$0")" && while [ ! -f tools/rdis.py ] && [ "$PWD" != / ]; do cd ..; done; pwd)
cd "$ROOT" || exit 1
W=${PM_WORK:-scratchpad/pm160/xfer}; mkdir -p "$W"
SNAP=${1:-scratchpad/pm142/rand1.snap}
for arm in A B; do
  [ $arm = A ] && bp=130fc || bp=1373c
  { printf '%s\n' "disk scratchpad/powermonger.st" "mouse move -400 -400" "s 300000" "mouse move 0 0" "s 300000" \
      "mouse move 103 186" "s 300000" "mouse move 0 0" "s 300000" "mouse down l" "mouse move 0 0" "s 300000" \
      "mouse up l" "mouse move 0 0" "s 600000" "m 57fd6 2" "bp $bp 400000" \
      "w 2df70 00000200" "w 2df74 00000200" "w 2df8e 00870023" "w 2df96 00010000" \
      "watch 5801d 1" "hits 1500000 133d4 6d90 3ce8" "m 57fd6 2" q; } > "$W/arm$arm.cmds"
  ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl < "$W/arm$arm.cmds" > "$W/arm$arm.txt" 2>&1
  echo "== arm $arm (poke at \$$bp)"
  grep -E 'WATCH' "$W/arm$arm.txt" | grep -v '<- \$0$'
  grep -E '^  \$0' "$W/arm$arm.txt"
done
