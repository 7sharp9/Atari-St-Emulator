"""Render the terrain model as PNGs (terrain.md).

usage: render_terrain.py <gen_in.snap> <d_ski.snap> <outdir>
  island.png: the whole island, file 37.2's 50 x 50 grid after the first subdivision ($1999a), 100 x 100 cells;
  local.png:  the 100 x 100 grid of d_ski.snap at its finest level, each cell split into its two triangles and
              coloured by the game's shading bytes ($197ec), sea (height 0) in blue.
"""
import os, sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import terrain_gen as tg  # noqa: E402


def island(entry):
    m = tg.Mem(tg.load_ram(entry)[0])
    m.setw(tg.P_SHIFT, 4)
    tg.subdivide(m, 0x4a104)
    tg.heights_1991a(m)
    hs = [m.w(a) for a in range(tg.GRID, tg.GRID_END, 4)]
    top = max(hs) or 1
    img = Image.new('RGB', (100, 100))
    for i, h in enumerate(hs):
        v = 60 + 195 * h // top
        img.putpixel((i % 100, i // 100), (20, 40, 140) if h == 0 else (v, v, v))
    return img.resize((400, 400), Image.NEAREST)


def local(snap):
    r = tg.load_ram(snap)[0]
    base = int.from_bytes(r[0x12ce2:0x12ce6], 'big')
    par = int.from_bytes(r[0x157a8:0x157aa], 'big')
    S = 6
    img = Image.new('RGB', (100 * S, 100 * S))
    px = img.load()
    for i in range(10000):
        a = base + 4 * i
        row, col = divmod(i, 100)
        h, s2, s3 = int.from_bytes(r[a:a + 2], 'big'), r[a + 2], r[a + 3]
        odd = (row + col + par) & 1
        for y in range(S):
            for x in range(S):
                upper = (x + y < S) if odd else (x > y)
                s = s2 if upper else s3
                v = 40 + 9 * min(s, 23)
                px[col * S + x, row * S + y] = (20, 40, 140) if h == 0 and s == 24 else (v, v, min(255, v + 10))
    return img


if __name__ == '__main__':
    os.makedirs(sys.argv[3], exist_ok=True)
    island(sys.argv[1]).save(os.path.join(sys.argv[3], 'island.png'))
    local(sys.argv[2]).save(os.path.join(sys.argv[3], 'local.png'))
