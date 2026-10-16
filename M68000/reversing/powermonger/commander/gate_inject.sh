#!/usr/bin/env bash
# gate_inject.sh - the command-buffer injection gate (README step 1). From pm142/rand1.snap, four arms of 30M steps,
# each watching side 3's slot $58028..$5802d:
#   ctl  unpoked: side 3's AI writes its slot (a $08, a $22 and a $02 order in this window)
#   A    slot state 4 -> 2, no order: the AI writes nothing into the slot
#   B    state 2 + attack $0c on player lord 9 at (15,92), $58042[3] left at $402 (group 1): goes by pigeon, group 1 ends
#        in state 8 with opponent class 2 (a lord)
#   C    as B with $58042[3] := $400 (group 0): runs at once ($6c32, $4a7a, $4b80 within the first pass)
# Writes under $CMD_WORK (default scratchpad/cmd1). Run from M68000/.
set -euo pipefail
ROOT=$(pwd); while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); done; cd "$ROOT"
W=${CMD_WORK:-scratchpad/cmd1}; mkdir -p "$W"
SNAP=scratchpad/pm142/rand1.snap
run() { # arm, poke lines...
  local arm=$1; shift
  { echo "disk scratchpad/powermonger.st"; for p in "$@"; do echo "$p"; done
    echo "watch 58028 6"; echo "hits 30000000 6c32 4a7a 4b80 45d0"; echo "snap $W/$arm.snap"; echo q; } > "$W/$arm.repl"
  ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl < "$W/$arm.repl" > "$W/$arm.out" 2> "$W/$arm.err"
}
run ctl
run A "w 58028 03000000" "w 5802c 02000400"
run B "w 58028 030c0f5c" "w 5802c 02000400"
run C "w 58048 0400053c" "w 58028 030c0f5c" "w 5802c 02000400"
uv run python - "$W" <<'EOF'
import re, struct, sys
sys.path.insert(0, 'tools')
from disassemble import ram_from_snap
w = sys.argv[1]
def ai_writes(arm):  # writes into the slot by the AI ($6822 at $6860/$6876, $6522 at $6550)
    return sum(1 for l in open(f'{w}/{arm}.err') if re.search(r'pc=\$00(6860|6876|6550) ', l))
def hits(arm, a):
    m = re.search(rf'\${a:06x}\s+(\d+)', open(f'{w}/{arm}.out').read()); return int(m.group(1))
def grp(arm):
    r = ram_from_snap(f'{w}/{arm}.snap'); h = lambda a: struct.unpack_from('>h', r, a)[0]; b = 0x51538 + 0x13c * 3
    return [h(b + 76 + 2 * k) for k in range(3)], [h(b + 280 + 2 * k) for k in range(3)]
checks = [
    ('ctl: AI writes its slot', ai_writes('ctl') >= 1),
    ('A: AI writes nothing', ai_writes('A') == 0),
    ('A: no attack', hits('A', 0x6c32) == 0),
    ('B: attack runs once', [hits('B', a) for a in (0x6c32, 0x4a7a, 0x4b80)] == [1, 1, 1]),
    ('B: group 1 state 8, class 2', grp('B')[0][1] == 8 and grp('B')[1][1] == 2),
    ('C: attack runs once', [hits('C', a) for a in (0x6c32, 0x4a7a, 0x4b80)] == [1, 1, 1]),
    ('C: group 0 marching or fighting', grp('C')[0][0] in (8, 0xd)),
]
for name, ok in checks: print('PASS' if ok else 'FAIL', name)
print(f"{sum(ok for _, ok in checks)}/{len(checks)}")
EOF
