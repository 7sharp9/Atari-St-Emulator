#!/usr/bin/env python3
"""Decode Case.pic: a 388-byte animation player plus nine 32,000-byte planar frames.

Usage (from M68000/): uv run python -I reversing/captive/py/world/case_frames.py <Case.pic> <outdir>
Code hunk layout (file offset 32 = code offset 0): player code $0..$bd, VBL flag $be, screen
pointer $c0, palette $c8 (16 ST words), frame-offset list $e8 (longs, -1 ends), frames from $184,
each four 8,000-byte bitplanes. Writes frame0..8.png, a strip case_strip.png, and prints the play
order (each entry is shown for 7 VBLs by the player's loop $46..$70).
"""
import os, struct, sys
from PIL import Image
src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
d = open(src, 'rb').read()
assert struct.unpack('>I', d[:4])[0] == 0x3f3
code = d[32:]
pal = []
for i in range(16):
    w = struct.unpack('>H', code[0xc8 + 2 * i:0xca + 2 * i])[0]
    pal.append((((w >> 8) & 7) * 255 // 7, ((w >> 4) & 7) * 255 // 7, (w & 7) * 255 // 7))
order, p = [], 0xe8
while True:
    v = struct.unpack('>i', code[p:p + 4])[0]
    if v < 0:
        break
    order.append(v // 32000)
    p += 4
first = 0x3e800 // 32000                 # shown before the list, at $2c..$3e
print('palette', ['%03x' % struct.unpack('>H', code[0xc8 + 2 * i:0xca + 2 * i])[0] for i in range(16)])
print('play order', [first] + order, 'frames', (len(code) - 0x184) // 32000)
frames = []
for f in range(9):
    b = code[0x184 + 32000 * f:0x184 + 32000 * (f + 1)]
    im = Image.new('RGB', (320, 200)); px = im.load()
    for y in range(200):
        for x in range(320):
            o, bit = y * 40 + (x >> 3), 7 - (x & 7)
            px[x, y] = pal[sum(((b[k * 8000 + o] >> bit) & 1) << k for k in range(4))]
    im.save(os.path.join(out, f'case_frame{f}.png'))
    frames.append(im)
strip = Image.new('RGB', (320 * 3, 200 * 3))
for f, im in enumerate(frames):
    strip.paste(im, ((f % 3) * 320, (f // 3) * 200))
strip.save(os.path.join(out, 'case_strip.png'))
