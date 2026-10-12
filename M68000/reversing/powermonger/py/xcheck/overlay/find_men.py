#!/usr/bin/env python3
"""List every record in the $47970 per-cell buckets of a PowerMonger RAM image,
by category, with its cell: the place to point the camera for a capture.
  uv run python <this> <ram> [byte6 ...]
Bucket walk as tools/pm_render_ref.load_ram ($115e0: head word[$47970 +
(cy*64+cx)*2], record $51b66 + signed head, next = signed word[rec+0])."""
import sys
from pathlib import Path

b = Path(sys.argv[1]).read_bytes()
want = {int(x) for x in sys.argv[2:]}
u16 = lambda a: (b[a] << 8) | b[a + 1]
s16 = lambda v: v - 0x10000 if v >= 0x8000 else v
for cy in range(128):
    for cx in range(64):
        d4 = u16(0x47970 + (cy * 64 + cx) * 2)
        seen = 0
        while d4 and seen < 96:
            o = 0x51B66 + s16(d4)
            seen += 1
            c = b[o + 6]
            if not want or c in want:
                print(f"cell ({cx:2},{cy:3}) ${o:05x} b6 {c:2} b5 {b[o+5]} b7 ${b[o+7]:02x} b31 ${b[o+31]:02x} "
                      f"b33 {b[o+33]} b44 {b[o+44]} fx {b[o+9]} fy {b[o+11]} b17 {b[o+17]}")
            d4 = u16(o)
