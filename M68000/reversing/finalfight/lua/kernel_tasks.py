"""Task lifecycle from kernel_log.txt (lua/kernel_log.lua): who created, restarted, killed or ended each
task slot, and with which entry point. Writer PCs are the kernel's own (kernel.md, ROM listing):

  $842/$848  trap #0 create (state $0c00, entry A0 at +4)      $966/$96c  pool create (slots 12-15, $938)
  $92a/$930  trap #7 restart-self (state $0c00, entry A0)      $858       trap #1 exit-self (state 0)
  $876       trap #2 kill                                      $89c       trap #3 sleep (word $01tt or $0200)
  $8f2       trap #5 suspend                                   $918       trap #6 wake

Usage: kernel_tasks.py [kernel_log.txt]   (default <repo>/M68000/scratchpad/finalfight/run/kernel_log.txt)
"""
import collections
import os
import re
import sys

ROOT = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "scratchpad", "finalfight", "run", "kernel_log.txt")
TCB = 0xFF1000
PAT = re.compile(r"f=(\d+) v=([\d.]+) pc=(\w+) w a=(\w+) m=(\w+) d=(\w+)")

rows = []
for line in open(path):
    m = PAT.match(line)
    if m:
        rows.append((int(m[1]), float(m[2]), int(m[3], 16), int(m[4], 16), int(m[5], 16), int(m[6], 16)))

NAMES = {0x842: "create", 0x966: "pool-create", 0x92A: "restart", 0x858: "exit", 0x876: "kill"}
events = []  # (frame, slot, kind, entry)
for i, (f, v, pc, a, k, d) in enumerate(rows):
    if not (TCB <= a < TCB + 0x100 and (a - TCB) % 16 == 0):
        continue
    slot = (a - TCB) // 16
    if pc in (0x842, 0x966, 0x92A) and d == 0x0C00:
        hi = lo = None
        for j in range(i + 1, min(i + 8, len(rows))):
            if rows[j][3] == a + 4:
                hi = rows[j][5]
            if rows[j][3] == a + 6:
                lo = rows[j][5]
        entry = (hi << 16) | lo if hi is not None and lo is not None else None
        events.append((f, slot, NAMES[pc], entry))
    elif pc in (0x858, 0x876):
        events.append((f, slot, NAMES[pc], None))

for f, slot, kind, entry in events:
    print(f"f={f:5d} slot {slot:2d} {kind:11s}" + (f" entry ${entry:06x}" if entry is not None else ""))

print()
by = collections.defaultdict(list)
for f, slot, kind, entry in events:
    if entry is not None:
        by[entry].append((f, slot, kind))
for entry, lst in sorted(by.items()):
    print(f"entry ${entry:06x}: {len(lst)} starts, slots {sorted(set(s for _, s, _ in lst))}, first f={lst[0][0]}")
