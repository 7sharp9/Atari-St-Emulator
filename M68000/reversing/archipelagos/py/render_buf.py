#!/usr/bin/env python3
"""render_buf.py snap out.png [base_hex]: render a 320x200x4bpp screen at an explicit base (default: live base)."""
import os, sys
d = os.path.abspath(os.path.dirname(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    d = os.path.dirname(d)
sys.path.insert(0, os.path.join(d, 'tools'))
from gfxview import load_ram, load_video_regs
from PIL import Image
snap, out = sys.argv[1], sys.argv[2]
ram, _ = load_ram(snap)
regs = load_video_regs(snap)
base = int(sys.argv[3], 16) if len(sys.argv) > 3 else regs['base']
pal = [((w >> 8 & 7) * 36, (w >> 4 & 7) * 36, (w & 7) * 36) for w in regs['palette_words']]
img = Image.new('RGB', (320, 200)); px = img.load()
for y in range(200):
    for xb in range(20):
        o = base + y * 160 + xb * 8
        w = [ram[o + 2 * i] << 8 | ram[o + 2 * i + 1] for i in range(4)]
        for b in range(16):
            v = sum(((w[p] >> (15 - b)) & 1) << p for p in range(4))
            px[xb * 16 + b, y] = pal[v]
img.save(out)
