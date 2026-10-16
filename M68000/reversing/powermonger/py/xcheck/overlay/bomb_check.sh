#!/usr/bin/env bash
# Byte6 36/38/42: what the game does with a record it cannot draw. Needs the b6_36/38/42
# _0 snapshots from run_cases.sh (ONLY="b6_36 b6_38 b6_42"). From each poke point run to
# the illegal word at $11640, then to $20, where TOS's bomb handler returns into the
# vector table; check TOS's crash record ($380 = $12345678, $3c4 = exception number) and
# the 16 bomb rows it draws at screen row 100 ($28280 + 160k, 32 bytes = 4 bombs).
#   bomb_check.sh           (from anywhere; repo root found via tools/rdis.py)
# Output in ${PM_WORK:-scratchpad/pm156}/overlay/cap: b6_NN_trap/bomb.snap/.ram.
set -eu
d=$(cd "$(dirname "$0")" && pwd)
while [ ! -f "$d/tools/rdis.py" ]; do d=$(dirname "$d"); done
cd "$d"
C=${PM_WORK:-scratchpad/pm156}/overlay/cap
for c in 36 38 42; do
  printf 'u 11640 400000\nsnap %s/b6_%s_trap.snap\nu 20 20000000\nsnap %s/b6_%s_bomb.snap\nq\n' "$C" $c "$C" $c |
    ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$C/b6_${c}_0.snap" repl \
      --disk-a scratchpad/powermonger.st 2>&1 | grep reached | sed "s/^/b6_$c /"
  uv run python reversing/powermonger/py/snap2ram.py "$C/b6_${c}_trap.snap" "$C/b6_${c}_bomb.snap" >/dev/null
done
uv run python - "$C" <<'EOF'
import sys
C = sys.argv[1]
ram = lambda n: open(f"{C}/{n}.ram", "rb").read()
rows = lambda b: b"".join(b[0x28280 + 160 * k:0x28280 + 160 * k + 32] for k in range(16))
ref = None
for c in ("36", "38", "42"):
    t, b = ram(f"b6_{c}_trap"), ram(f"b6_{c}_bomb")
    changed = sum(rows(t)[i] != rows(b)[i] for i in range(512))
    print(f"b6_{c}: $380={b[0x380:0x384].hex()} $3c4={b[0x3c4]} bomb rows changed {changed}/512 bytes")
    ref = ref or rows(b)
    print(f"b6_{c}: bomb rows equal to b6_36: {rows(b) == ref}")
EOF
