"""Follow plane 2 (11322(A6)) from every non-wall cell and report where each walk ends. Bits 0-2 are the generated
flow field toward the nearest lift (0 N, 1 W, 2 S, 3 E; 4/5 = lift cell, stop); `trail` follows bits 3-5 instead,
the field creatures read, which starts equal to bits 0-2 and is overwritten by the party's breadcrumbs.
field.py <snap> [trail]"""
import os, sys, collections; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from cap import *
from gfxview import load_ram
snap = snappath(sys.argv[1])
sh = 3 if len(sys.argv) > 2 and sys.argv[2] == 'trail' else 0
ram, base = load_ram(snap)
g = ram[A6 + 9242 - base:][:2048]; p = ram[A6 + 11322 - base:][:2048]
D = {0: (0, -1), 1: (-1, 0), 2: (0, 1), 3: (1, 0)}
ends = collections.Counter(); walls = 0; steps = []
for y in range(32):
    for x in range(64):
        if g[y * 64 + x] & 0x7f == 0: continue
        cx, cy = x, y
        for n in range(300):
            d = (p[cy * 64 + cx] >> sh) & 7
            if d > 3: ends[(cx, cy, d)] += 1; steps.append(n); break
            nx, ny = cx + D[d][0], cy + D[d][1]
            if not (0 <= nx < 64 and 0 <= ny < 32) or g[ny * 64 + nx] & 0x7f == 0: ends[('wall', cx, cy)] += 1; break
            cx, cy = nx, ny
        else: ends['loop'] += 1
print('walk ends:', ends.most_common(12)); print('cells reaching a stop:', len(steps), 'max path', max(steps) if steps else None)
