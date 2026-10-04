"""Shop drive: move the hero onto a shop-man cell (map object kind $11, `special_items.txt`); the kind-$11 handler
$d194 (needs |dx|,|dy| <= 8 to the cell) clears the cell, plays 16 mini frames ($cc36) and calls $ea7c -> the shop screen
$f690 (BTCLIPS picture bank, price table $17a8e per mechanics.md), which then waits for input.

LABELLED POKE: `w 1f014 <x:4 hex><y:4 hex>` = hero x/y words := the cell.
usage: drive_shop.py [level=0] [index=0] [steps=1700000]   -> $OUT/boss/shop<level>_<index>.snap/.png
Steps to the shop screen: $ea7c is entered ~1.40M steps after the poke, $f690 ~1.44M (level 0, hits census 1/1/1).
"""
import os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from btcommon import *
level = int(sys.argv[1]) if len(sys.argv) > 1 else 0
idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
steps = int(sys.argv[3]) if len(sys.argv) > 3 else 1700000
x, y = shops()[level][idx]
p = f"{OUT}/boss/shop{level}_{idx}.snap"
os.makedirs(os.path.dirname(p), exist_ok=True)
out = run_repl(level_snap(level), "\n".join([f"w 1f014 {x:04x}{y:04x}", f"hits {steps} ea7c f690 fa9c", f"snap {p}", "m 1f000 16", "quit"]) + "\n")
print("\n".join(l for l in out.splitlines() if "$00" in l and "hits" not in l or l.startswith("00 ")))
subprocess.run([sys.executable, os.path.join(ROOT, "tools", "snap_render.py"), p, p[:-5] + ".png"], capture_output=True)
