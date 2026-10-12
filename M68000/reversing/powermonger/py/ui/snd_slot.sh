#!/bin/bash
# snd_slot.sh [snap] [dispatches]
# The sound-event slot of $127e6/$1283c, live (strategy.md "$127e6 - the sound-event dispatcher").
#   census: at each of N dispatches, the pending counts at $127e6 entry and the entry $1283c gets (A1);
#           with a lit camp fire in view, event 17 ($129fa) is pending and chosen every time.
#   slot:   from the first $128d2 (the one player call), 40M steps with `watch 2c992` (sequence active)
#           and hits on the slot exits, then a backtrace and slot dump at each later $1ba3e call.
# Default start: scratchpad/pm148/arms/sheep/k120_tree_c1.snap (lit fire in view, slot empty).
# Work dir $PM_WORK (default scratchpad/pm160/snd).
ROOT=$(cd "$(dirname "$0")" && while [ ! -f tools/rdis.py ] && [ "$PWD" != / ]; do cd ..; done; pwd)
cd "$ROOT" || exit 1
W=${PM_WORK:-scratchpad/pm160/snd}; mkdir -p "$W"
SNAP=${1:-scratchpad/pm148/arms/sheep/k120_tree_c1.snap}
N=${2:-60}
run() { ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl < "$1" > "$2" 2>&1; }
{ echo "disk scratchpad/powermonger.st"
  for _ in $(seq "$N"); do printf 'bp 127e6 3000000\nm 1290c 896\nbp 1283c 2000\nm 58058 14\ns 1\nr\n'; done
  echo q; } > "$W/census.cmds"
printf '%s\n' "disk scratchpad/powermonger.st" "bp 128d2 400000" "m 58058 14" "u 1ba5e 2000" \
  "m 2c990 8" "m 58058 14" "watch 2c992 1" "hits 40000000 117c2 127e6 1284a 128c8 128d2 128e6 1ba3e" \
  "m 58058 14" q > "$W/slot.cmds"
printf '%s\n' "disk scratchpad/powermonger.st" "bp 128d2 400000" "u 1ba5e 2000" \
  "bp 1ba3e 40000000" "bt 1" "m 58058 14" "s 1" "bp 1ba3e 40000000" "bt 1" "m 58058 14" q > "$W/later.cmds"
run "$W/census.cmds" "$W/census.txt"
run "$W/slot.cmds" "$W/slot.txt"
run "$W/later.cmds" "$W/later.txt"
python3 - "$W" <<'EOF'
import re, sys
from collections import Counter
w = sys.argv[1]
t = open(f"{w}/census.txt").read()
pend, chosen = Counter(), Counter()
blocks = t.split("--- breakpoint $000127e6")[1:]
for b in blocks:
    row = next(l for l in b.splitlines() if len(l.split()) == 896)
    by = bytes.fromhex(row.replace(" ", ""))
    for i in range(64):
        if by[14 * i:14 * i + 2] != b"\0\0":
            pend[i] += 1
    a1 = int(re.search(r"A1:([0-9a-f]{8})", b.split("$0001283c")[1]).group(1), 16)
    chosen[(a1 - 0x1290c) // 14] += 1
print(f"census: {len(blocks)} dispatches; pending entry:count {dict(pend)}; chosen entry:count {dict(chosen)} (0 = sentinel)")
slot = lambda h: (lambda b: f"cd=${int.from_bytes(b[2:6],'big'):x} id={int.from_bytes(b[6:8],'big')} "
                  f"w8={int.from_bytes(b[8:10],'big')} pri={int.from_bytes(b[10:12],'big')} fl=${int.from_bytes(b[12:14],'big'):02x}")(bytes.fromhex(h.replace(' ', '')))
s = open(f"{w}/slot.txt").read()
dumps = re.findall(r"^((?:[0-9a-f]{2} ){13}[0-9a-f]{2})$", s, re.M)
seq = re.findall(r"^((?:[0-9a-f]{2} ){7}[0-9a-f]{2})$", s, re.M)
print("slot at the call ($128d2, already written):", slot(dumps[0]), "| run end:", slot(dumps[2]))
print("sequence bytes $2c990..7 after the call:", seq[0], "($2c992 active, $2c994 loop)")
for l in s.splitlines():
    if l.startswith("WATCH") or l.startswith("  $0"):
        print(" ", l.strip())
l = open(f"{w}/later.txt").read()
for blk in l.split("--- breakpoint $0001ba3e")[1:]:
    a1 = re.search(r"A1:([0-9a-f]{8})", blk).group(1)
    ret = re.search(r"return address \(A7\) = \$([0-9a-f]+)", blk).group(1)
    d = re.findall(r"^((?:[0-9a-f]{2} ){13}[0-9a-f]{2})$", blk, re.M)
    st = re.search(r"after (\d+) step", blk).group(1)
    print(f"later $1ba3e: +{st} steps, return ${ret}, entry {(int(a1,16)-0x1290c)//14}; slot then {slot(d[0])}")
EOF
