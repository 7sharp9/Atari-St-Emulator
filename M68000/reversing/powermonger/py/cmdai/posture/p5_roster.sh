#!/usr/bin/env bash
# usage: p5_roster.sh [snap|dismiss|flag] [5|3 ...]   (run from anywhere under M68000/; output in ${PM_WORK:-scratchpad/pm168}/roster/)
# Does the fisher flag posture 5's trade clears (strategy.md "Posture 5 forced into the trade") still matter once the man
# (object 6, $51c92) is in a group roster? $1b8c, the roster unlink every dismiss runs per man, clears his bit 6 and word 28
# and calls $3c08, the reader of the job bits. snap: run p5_fisher.sh's arms (posture P poked at at63f4, its two lord pokes)
# 100M steps, past both men's roster joins (92.2M posture 5, 64.3M control), and snapshot. dismiss: from that snapshot give
# the man's group the dismiss order $14 00 00 through his side's slot (p5_roster.py), with its posture poked to 2
# so every man goes, and watch his bytes 30..31 for the mode $3c08 picks and then 60M steps on.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); done; cd "$ROOT"
W=${PM_WORK:-scratchpad/pm168}/roster; mkdir -p "$W"
S=scratchpad/pm162/posture/trade/at63f4.snap
what=${1:-snap}; shift || true
for p in ${@:-5 3}; do
  case $what in
  snap)
    { echo 'disk scratchpad/powermonger.st'; echo "w 51974 000${p}0002"; echo 'w 4e6f4 03000000'; echo 'w 4e6ec 00050000'
      for i in $(seq 10); do echo 'hits 10000000 6522'; done; echo 'm 51c92 50'; echo "snap $W/p${p}_100M.snap"; echo q; } > "$W/p${p}_snap.repl"
    ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$S" repl < "$W/p${p}_snap.repl" > "$W/p${p}_snap.out" 2>&1
    grep -E '^[0-9a-f]{2}( [0-9a-f]{2}){49}$' "$W/p${p}_snap.out" | sed "s/^/p$p object 6: /";;
  dismiss|flag)
    t=${what/dismiss/}; t=${t:+_flag}   # flag: the same dismiss with the man's bit 2 put back (byte 7 |= 4), the one-variable control
    uv run python "$ROOT/reversing/powermonger/py/cmdai/posture/p5_roster.py" "$W/p${p}_100M.snap" > "$W/p${p}_pokes.txt" || { echo "p$p: $(head -1 "$W/p${p}_pokes.txt"), no dismiss"; continue; }
    echo "p$p: $(head -1 "$W/p${p}_pokes.txt")"
    { echo 'disk scratchpad/powermonger.st'; grep -v '^#' "$W/p${p}_pokes.txt"
      [ -n "$t" ] && uv run python - "$W/p${p}_100M.snap" <<'PY'
import sys; sys.path.insert(0, 'tools')
from disassemble import ram_from_snap
b = ram_from_snap(sys.argv[1]); print(f'w 51c96 {b[0x51c96:0x51c99].hex()}{b[0x51c99] | 4:02x}')
PY
      echo 'watch 51cb0 2'
      echo 'hits 1000000 1cc4 1b8c 3c08'; echo 'm 51c92 50'
      for i in $(seq 6); do echo 'hits 10000000 15b8a 5f78 6522'; echo 'm 51c92 50'; done; echo q; } > "$W/p${p}_dismiss$t.repl"
    ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$W/p${p}_100M.snap" repl < "$W/p${p}_dismiss$t.repl" > "$W/p${p}_dismiss$t.out" 2> "$W/p${p}_dismiss$t.err";;
  esac
done
