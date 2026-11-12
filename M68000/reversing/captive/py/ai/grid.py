"""Print the level grid (9242(A6), 64x32) and plane 2 (11322(A6)) fields: grid.py <snap> [field]
field: walk (. = $20/$60 floor, # = 0) | tile | p2dir (plane2 bits 3-5) | p2lo (bits 0-2) | p2hi (bits 6-7) | occ (grid bit 7)"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from cap import *
from gfxview import load_ram
snap = sys.argv[1] if os.path.isabs(sys.argv[1]) else os.path.join(R, sys.argv[1])
field = sys.argv[2] if len(sys.argv) > 2 else 'tile'
ram, base = load_ram(snap)
g = ram[A6 + 9242 - base:A6 + 9242 - base + 2048]
p = ram[A6 + 11322 - base:A6 + 11322 - base + 2048]
w = lambda a: int.from_bytes(ram[a - base:a - base + 2], 'big')
px, py = w(A6 + 26), w(A6 + 28)
for y in range(32):
    row = ''
    for x in range(64):
        i = y * 64 + x
        if field == 'tile': v = f'{g[i] & 0x7f:02x}'
        elif field == 'p2dir': d = (p[i] >> 3) & 7; v = ' ' + ('^<v>'[d] if d < 4 else '.')
        elif field == 'p2lo': v = f' {p[i] & 7}'
        elif field == 'p2hi': v = f' {p[i] >> 6}'
        elif field == 'walk': c = g[i] & 0x7e; v = ' .' if c in (0x20, 0x60) else ' #' if c == 0 else f'{g[i] & 0x7f:02x}'
        elif field == 'occ': v = ' #' if g[i] & 0x80 else ' .'
        if (x, y) == (px, py): v = v[:-1] + '@'
        row += v
    print(row)
