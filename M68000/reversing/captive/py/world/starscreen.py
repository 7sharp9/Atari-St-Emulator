#!/usr/bin/env python3
"""Check the map screen against the universe generator: the white pixels inside the map grid are
exactly the 50 generated planets.

Usage (from M68000/):
  uv run python -I tools/snap_render.py scratchpad/captive/mission1.snap <png>
  uv run python -I reversing/captive/py/world/starscreen.py <png> scratchpad/captive/mission1.snap
Collects the white (252,252,252) pixels in the grid box (x 55..149, y 68..159 of the 320x200
render), generates the 51 map cells (slot 0 = space station, 1..50 = planets) from the snapshot's
mission index 14776(A6), and searches the integer offset and scale (pixel = off + s*cell) that
puts the most cells on white pixels. Expected on mission1.snap: 50/51 cells, the miss is slot 0
(the station, not drawn as a dot), and 0 white pixels left unexplained.
With --png <out>, writes the grid area x4 with each generated cell outlined (red: on a white pixel,
yellow: not).
"""
import os
import struct
import sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # sibling universe.py (-I drops it)
import universe as U  # noqa: E402
from gfxview import load_ram  # noqa: E402  (universe puts tools/ on the path)


def main():
    png, snap = sys.argv[1], sys.argv[2]
    im = Image.open(png).convert('RGB')
    box = [(x, y) for y in range(68, 160) for x in range(55, 150)]
    white = {p for p in box if im.getpixel(p) == (252, 252, 252)}
    green = sorted(p for p in box if im.getpixel(p) == (36, 216, 36))
    ram, _ = load_ram(snap)
    mission = struct.unpack('>H', ram[U.A6 + 14776:U.A6 + 14778])[0]
    xytab = list(ram[0x3047c:0x3047c + 32])
    cells = [(v >> 16, v & 0xffff) for v in U.generate(mission, xytab, [(0, 0)] * 8)[0]]
    best = None
    for s in (1, 2, 3):
        for ox in range(40, 110):
            for oy in range(50, 120):
                n = sum((ox + s * x, oy + s * y) in white for x, y in cells)
                if best is None or n > best[0]:
                    best = (n, s, ox, oy)
    n, s, ox, oy = best
    hit = {(ox + s * x, oy + s * y) for x, y in cells}
    print(f'mission index {mission}; white pixels in grid: {len(white)}; green marker: {green}')
    print(f'fit pixel = ({ox},{oy}) + {s}*cell: {n}/51 map cells on a white pixel')
    print('cells not on white (slot, cell):',
          [(i, c) for i, c in enumerate(cells) if (ox + s * c[0], oy + s * c[1]) not in white])
    print('white pixels no cell explains:', len(white - hit))
    if '--png' in sys.argv:
        from PIL import ImageDraw
        x0, y0 = 55, 60
        big = im.crop((x0, y0, 150, 160)).resize((95 * 4, 100 * 4), Image.NEAREST)
        dr = ImageDraw.Draw(big)
        for x, y in cells:
            px, py = (ox + s * x - x0) * 4, (oy + s * y - y0) * 4
            col = (255, 0, 0) if (ox + s * x, oy + s * y) in white else (255, 255, 0)
            dr.rectangle((px - 3, py - 3, px + 6, py + 6), outline=col)
        big.save(sys.argv[sys.argv.index('--png') + 1])


if __name__ == '__main__':
    main()
