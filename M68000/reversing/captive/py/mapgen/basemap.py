"""Render the generated bases of a gen.py json, one PNG per case.

    uv run python -I reversing/captive/py/mapgen/basemap.py <in.json> <outdir>

Cell colour: black = not carved (G0 = 0), dark grey = block wall (G0 = $ffff), otherwise the colour of the cell's
floor (block table, module bytes 0..15), lighter where G1's feature is room floor ($1f/$33), white = lift end
(feature 4, 5, 6, $35-$37), red = the entry cell (column 32(A6), row 0). 8 px per cell. Files are named
base_d0_<D0>_d2_<D2>.png; a relative <outdir> is under scratchpad/captive/agents/mapgen/.
"""
import json
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen import grids, outpath  # noqa: E402

FLOOR = {1: (60, 110, 200), 2: (60, 170, 90), 3: (200, 150, 50), 4: (170, 70, 170), 5: (60, 180, 180)}
LIFT = (4, 5, 6, 0x35, 0x36, 0x37)


def render(o):
    g = grids(o)
    v = g['vars']
    im = Image.new('RGB', (64, 32))
    for y in range(32):
        for x in range(64):
            i = 64 * y + x
            w, f = g['g0'][i], g['feat'][i] & 0x7f
            if w == 0xffff:
                c = (70, 70, 70)
            elif w == 0:
                c = (0, 0, 0)
            elif f in LIFT:
                c = (255, 255, 255)
            else:
                c = FLOOR.get(v[(y >> 3) * 4 + (x >> 4)], (120, 120, 120))
                if f in (0x1f, 0x33):
                    c = tuple(min(255, k + 60) for k in c)
            im.putpixel((x, y), c)
    im.putpixel((int.from_bytes(v[32:34], 'big'), 0), (255, 0, 0))
    return im.resize((512, 256), Image.NEAREST)


def main():
    out = outpath(sys.argv[2])
    os.makedirs(out, exist_ok=True)
    for o in json.load(open(outpath(sys.argv[1]))):
        p = os.path.join(out, f'base_d0_{o["args"][0]}_d2_{o["args"][2]}.png')
        render(o).save(p)
        print(p)


if __name__ == '__main__':
    main()
