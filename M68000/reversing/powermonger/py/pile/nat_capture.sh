#!/bin/bash
# nat_capture.sh [snap] [n]: natural pile creations. From pm142/rand1.snap (default) stop n times (default 7) at $3a60 (the transfer
# entry of $39d4, after the slot or pile is found), dump the group table $51538 (1580 B), the pile pool $4bb4e (672 B) and the
# object array $51b66 (25550 B), then stop at the exit $3ae8 and dump the same. Each bp is bounded at 150M steps; a
# `hits 1 6522`-free design: the liveness is the census run's (census.repl). Output: $PM_WORK/pile/nat/cap.txt; parse with nat_parse.py.
R=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$R/tools/rdis.py" ]; do R=$(dirname "$R"); done
cd "${M68000_ROOT:-$R}" || exit 1
W=${PM_WORK:-scratchpad/pm162}/pile/nat; mkdir -p "$W"; SNAP=${1:-scratchpad/pm142/rand1.snap}; N=${2:-7}
{
  echo "disk scratchpad/powermonger.st"
  for i in $(seq 1 "$N"); do
    echo "bp 3a60 150000000"; echo "m 51538 1580"; echo "m 4bb4e 672"; echo "m 51b66 25550"
    echo "bp 3ae8 2000"; echo "m 51538 1580"; echo "m 4bb4e 672"; echo "m 51b66 25550"
  done
  echo q
} | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl > "$W/cap.txt" 2>&1
