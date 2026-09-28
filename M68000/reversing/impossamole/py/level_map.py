"""Render Impossamole's whole-level collision map from a snapshot's RAM.

The raw tile map is 1680 columns x 24 rows of bytes at $31800 (row stride $690, 8px tiles; README
"`$be96`'s tile classification"). Each raw id maps through the 256-byte table at $25000 to a category
(0 background, 4 walkable, 9 hazard, 1/2/3 unidentified). The map is fully resident, so the level can
be read without playing it.

    uv run python reversing/impossamole/py/level_map.py <snap> <out.png> [--raw] [--x0 COL --x1 COL]

Default colours by category; --raw colours by raw tile id instead (a stable hue per id).
--rooms marks room boundaries (blue) and exit triggers (cyan = top, orange = bottom).
Marks the camera window ($227b6, 320px wide) and the level limit ($227b8) with vertical lines.
"""
import argparse, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools'))
from pm_export import ram_from_snap
from PIL import Image, ImageDraw

MAP, COLS, ROWS, CLS = 0x31800, 1680, 24, 0x25000
CATCOL = {0: (12, 12, 24), 4: (200, 170, 60), 9: (230, 40, 40),
          1: (60, 200, 90), 2: (60, 140, 230), 3: (200, 90, 220)}


def transitions(ram):
    """Room table for the current world ($bb76, 1-based): $c028 has the start room (start block, end
    block); $e0aa points to per-world 10-byte records (dir, trigger block, dest start block, dest end
    block, dest hero block-x), dir 0 = leave through the top, 1 = through the bottom, ended by $ffff."""
    w = ram[0xbb76]
    sb, eb = struct.unpack_from('>2H', ram, 0xc028 + 8 * (w - 1) + 4)
    a = struct.unpack_from('>I', ram, 0xe0aa + 4 * (w - 1))[0]
    recs = []
    while struct.unpack_from('>h', ram, a)[0] >= 0:
        recs.append(struct.unpack_from('>5H', ram, a)); a += 10
    return w, (sb, eb), recs


def load(snap):
    ram = ram_from_snap(Path(snap))
    return ram, [[ram[MAP + r * COLS + c] for c in range(COLS)] for r in range(ROWS)], ram[CLS:CLS + 256]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('snap'); ap.add_argument('out')
    ap.add_argument('--raw', action='store_true')
    ap.add_argument('--x0', type=int, default=0); ap.add_argument('--x1', type=int, default=COLS)
    ap.add_argument('--scale', type=int, default=6)
    ap.add_argument('--rooms', action='store_true', help='mark room boundaries and top/bottom exits')
    a = ap.parse_args()
    ram, tiles, cls = load(a.snap)
    cam = struct.unpack_from('>H', ram, 0x227b6)[0]
    lim = struct.unpack_from('>H', ram, 0x227b8)[0]
    s = a.scale
    img = Image.new('RGB', ((a.x1 - a.x0) * s, ROWS * s))
    px = img.load()
    for r in range(ROWS):
        for c in range(a.x0, a.x1):
            t = tiles[r][c]
            col = ((t * 53) % 256, (t * 97) % 256, (t * 151) % 256) if a.raw else CATCOL[cls[t]]
            for dy in range(s):
                for dx in range(s):
                    px[(c - a.x0) * s + dx, r * s + dy] = col
    d = ImageDraw.Draw(img)
    if a.rooms:
        w, start, recs = transitions(ram)
        for sb, eb in {start} | {(r[2], r[3]) for r in recs}:
            for b in (sb, eb):
                x = (b * 4 - a.x0) * s
                if 0 <= x < img.width:
                    d.line([(x, 0), (x, ROWS * s)], fill=(90, 90, 255))
        for dr, trig, *_ in recs:
            x = (trig * 4 - a.x0) * s
            if 0 <= x < img.width:
                y0, y1 = (0, 8) if dr == 0 else (ROWS * s - 8, ROWS * s)
                d.rectangle([x, y0, x + 4 * s, y1], fill=(0, 255, 255) if dr == 0 else (255, 140, 0))
    for x in (cam // 8, (cam + 320) // 8, (lim + 320) // 8):
        if a.x0 <= x <= a.x1:
            d.line([((x - a.x0) * s, 0), ((x - a.x0) * s, ROWS * s)], fill=(255, 255, 255))
    img.save(a.out)
    used = max((c for c in range(COLS) if any(tiles[r][c] for r in range(ROWS))), default=0)
    print(f'camera=${cam:x} limit=${lim:x} last non-zero column={used} (x={used * 8})')


if __name__ == '__main__':
    main()
