#!/usr/bin/env bash
# Byte6 36/38/42: what the game does with a record it cannot draw. Needs the b6_36/38/42
# _0 snapshots from run_cases.sh (ONLY="b6_36 b6_38 b6_42"). From each poke point run 400k
# steps counting the fault path: $1162e (the (A4)+ read of $fff95600 that bus-errors), the
# game's bus-error handler $112a/$1130 (clr.l $2c1ba / rte), the bogus PCs its rte pops from
# the 14-byte group-0 frame ($f95600, then $f90000 once the stack reaches $2c1ba and the clr
# zeroes the stacked address's low word) and $11640 / $20 (the illegal word and TOS's bomb
# exit the old emulator reached, now never hit). The emulator prints the double bus fault
# that halts the CPU; the halting step is found by bisection. End states are compared.
#   bomb_check.sh           (from anywhere; repo root found via tools/rdis.py)
# Output in ${PM_WORK:-scratchpad/pm156}/overlay/cap: b6_NN_halt.snap/.ram.
set -eu
d=$(cd "$(dirname "$0")" && pwd)
while [ ! -f "$d/tools/rdis.py" ]; do d=$(dirname "$d"); done
cd "$d"
C=${PM_WORK:-scratchpad/pm156}/overlay/cap
emu() { ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$C/b6_$1_0.snap" repl 2>&1; }
for c in 36 38 42; do
  printf 'disk scratchpad/powermonger.st\nhits 400000 1162e 112a 1130 f95600 f90000 11640 20\nsnap %s/b6_%s_halt.snap\nq\n' "$C" $c |
    emu $c | grep -E 'double bus|^  \$' | sed "s/^/b6_$c /"
  lo=108263; hi=400000
  while [ $((hi - lo)) -gt 1 ]; do
    m=$(((lo + hi) / 2))
    if printf 'disk scratchpad/powermonger.st\ns %s\nq\n' $m | emu $c | grep -q 'double bus'; then hi=$m; else lo=$m; fi
  done
  echo "b6_$c halted at step $hi"
  uv run python reversing/powermonger/py/snap2ram.py "$C/b6_${c}_halt.snap" >/dev/null
done
uv run python - "$C" <<'EOF'
import sys
C = sys.argv[1]
ram = {c: open(f"{C}/b6_{c}_halt.ram", "rb").read() for c in ("36", "38", "42")}
for c in ("38", "42"):
    diff = [i for i in range(len(ram["36"])) if ram["36"][i] != ram[c][i]]
    print(f"b6_{c} end RAM vs b6_36: {len(diff)} bytes differ {[hex(i) for i in diff[:8]]}")
EOF
