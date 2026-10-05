"""Count table of list A (type/variant) per level, from the ROM (`scripts_dump.entries`). usage: type_by_level.py"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from scripts_dump import entries
cnt = {}
for lv in range(6):
    for e in entries(0x6c000, lv): cnt[(e[2], e[3], lv)] = cnt.get((e[2], e[3], lv), 0) + 1
print("| type/variant | L0 | L1 | L2 | L3 | L4 | L5 |"); print("|---|---|---|---|---|---|---|")
for t, v in sorted(set((t, v) for t, v, l in cnt)):
    print(f"| ${t:02x}/{v:02x} | " + " | ".join(str(cnt.get((t, v, l), "")) for l in range(6)) + " |")
print("\ntotals:", [sum(n for (t, v, l), n in cnt.items() if l == lv) for lv in range(6)])
