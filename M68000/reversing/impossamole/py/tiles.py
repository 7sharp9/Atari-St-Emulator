"""Decode and render Impossamole's background art from a snapshot's RAM.

Background structure (README "Graphics"; graphics.md):
  level (420 block columns) -> block map $27600 (6 bytes per column, one block id per 32px row)
  -> block definitions $29000 (8 bytes per block: 4 big-endian word tile ids, row-major 2x2)
  -> tile bank $29800 (256 tiles x 128 bytes, 16x16 px, 4-plane interleaved words, the ST low-res
  row format: per row four words = planes 0..3 of 16 pixels).
The room-install routine $18ed4 and the tile drawer $19006 read exactly these tables.

    uv run python reversing/impossamole/py/tiles.py <snap> --sheet out.png [--scale N]
    uv run python reversing/impossamole/py/tiles.py <snap> --level out.png [--b0 B --b1 B]
    uv run python reversing/impossamole/py/tiles.py <snap> --cats out.png --b0 0 --b1 80   # collision categories over real tiles
    uv run python reversing/impossamole/py/tiles.py <snap> --palettes out.png   # the five world palettes ($2166e)
    uv run python reversing/impossamole/py/tiles.py <snap> --check        # compare with the live screen

The palette is the snapshot's live hardware palette ($ff8240) unless --pal-at <hex addr> names a 16-word
table in RAM (the four 16-colour tables at $21682.. are the world palettes).
"""
import argparse, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools'))
from pm_export import ram_from_snap
from gfxview import load_video_regs
from PIL import Image

BLOCKMAP, BLOCKDEF, TILEBANK = 0x27600, 0x29000, 0x29800
NBLOCKS, NTILES = 420, 256


def st_rgb(w):
    r, g, b = (w >> 8) & 7, (w >> 4) & 7, w & 7
    return (r * 255 // 7, g * 255 // 7, b * 255 // 7)


def palette(snap, ram, pal_at=None):
    if pal_at is not None:
        words = struct.unpack_from('>16H', ram, pal_at)
    else:
        words = load_video_regs(str(snap))['palette_words']
    return [st_rgb(w) for w in words]


def tile_pixels(ram, t):
    """16x16 palette indices of tile t (list of 16 rows of 16 ints)."""
    base = TILEBANK + t * 128
    rows = []
    for y in range(16):
        p = struct.unpack_from('>4H', ram, base + y * 8)
        rows.append([sum(((p[k] >> (15 - x)) & 1) << k for k in range(4)) for x in range(16)])
    return rows


def block_tiles(ram, b):
    return struct.unpack_from('>4H', ram, BLOCKDEF + b * 8)


def level_index_image(ram, b0=0, b1=NBLOCKS):
    """Palette-index image of block columns [b0,b1): 32px per block column, 192px tall."""
    w = (b1 - b0) * 32
    img = [bytearray(w) for _ in range(192)]
    cache = {}
    for col in range(b0, b1):
        for row in range(6):
            blk = ram[BLOCKMAP + col * 6 + row]
            for i, t in enumerate(block_tiles(ram, blk)):
                if t not in cache:
                    cache[t] = tile_pixels(ram, t)
                px, py = (col - b0) * 32 + (i & 1) * 16, row * 32 + (i >> 1) * 16
                for y, r in enumerate(cache[t]):
                    img[py + y][px:px + 16] = bytes(r)
    return img


def to_image(rows, pal):
    im = Image.new('P', (len(rows[0]), len(rows)))
    im.putpalette([c for rgb in pal for c in rgb] + [0] * (768 - 48))
    im.putdata([v for r in rows for v in r])
    return im.convert('RGB')


def screen_index_rows(ram, base):
    rows = []
    for y in range(200):
        r = []
        for g in range(20):
            p = struct.unpack_from('>4H', ram, base + y * 160 + g * 8)
            r += [sum(((p[k] >> (15 - x)) & 1) << k for k in range(4)) for x in range(16)]
        rows.append(r)
    return rows


def check(snap, ram):
    """Render the level at the live camera and slide it over the live screen for the best offset."""
    vr = load_video_regs(str(snap))
    cam = struct.unpack_from('>H', ram, 0x227b6)[0]
    b0 = cam // 32
    lv = level_index_image(ram, b0, min(NBLOCKS, b0 + 11))
    scr = screen_index_rows(ram, vr['base'])
    fine = cam - b0 * 32
    best = None
    for dy in range(0, 12):
        for dx in range(0, 40):
            # screen pixel (sx, sy) shows level pixel (fine + sx - dx, sy - dy)
            n = m = 0
            for sy in range(dy + 8, dy + 184, 2):
                for sx in range(dx + 8, dx + 248, 2):
                    lx = fine + sx - dx
                    if 0 <= lx < len(lv[0]) and 0 <= sy - dy < 192:
                        n += 1
                        m += scr[sy][sx] == lv[sy - dy][lx]
            if n and (best is None or m / n > best[0]):
                best = (m / n, dx, dy, n)
    print(f'camera {cam:#x} block {b0} fine {fine}; best offset dx={best[1]} dy={best[2]}: '
          f'{best[0]*100:.1f}% of {best[3]} sampled pixels match')
    return best


CATTINT = {1: (60, 255, 90), 2: (60, 140, 255), 3: (255, 90, 255), 9: (255, 40, 40)}


def category_overlay(snap, ram, pal, b0, b1):
    """Real-tile render of blocks [b0,b1) with the $25000 collision categories tinted over the 8px map cells
    ($31800; 1 green, 2 blue, 3 magenta, 9 red). Wide ranges are folded into rows of 40 blocks."""
    from level_map import load
    _, tiles, cls = load(snap)
    base = to_image(level_index_image(ram, b0, b1), pal).convert('RGBA')
    ov = Image.new('RGBA', base.size, (0, 0, 0, 0))
    px = ov.load()
    for r in range(24):
        for c in range(b0 * 4, b1 * 4):
            k = cls[tiles[r][c]]
            if k in CATTINT:
                for y in range(8):
                    for x in range(8):
                        px[(c - b0 * 4) * 8 + x, r * 8 + y] = CATTINT[k] + (150,)
    full = Image.alpha_composite(base, ov).convert('RGB')
    per = 40 * 32
    n = (full.width + per - 1) // per
    out = Image.new('RGB', (min(per, full.width), 192 * n))
    for i in range(n):
        out.paste(full.crop((i * per, 0, min((i + 1) * per, full.width), 192)), (0, i * 192))
    return out


PALTAB = 0x2166e  # 5 longword pointers, indexed by $bb76 - 1 (the per-frame template $b19a / $e082 read it)


def palette_swatches(ram, scale=16):
    """One row of 16 colours per world, from the pointer table at $2166e."""
    rows = []
    for w in range(5):
        a = struct.unpack_from('>I', ram, PALTAB + 4 * w)[0]
        rows.append((w + 1, a, [st_rgb(x) for x in struct.unpack_from('>16H', ram, a)]))
    im = Image.new('RGB', (16 * scale, 5 * scale))
    for i, (_, _, pal) in enumerate(rows):
        for c, rgb in enumerate(pal):
            im.paste(rgb, (c * scale, i * scale, (c + 1) * scale, (i + 1) * scale))
    return im, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('snap')
    ap.add_argument('--sheet'); ap.add_argument('--level'); ap.add_argument('--check', action='store_true')
    ap.add_argument('--palettes', metavar='OUT')
    ap.add_argument('--cats', metavar='OUT')
    ap.add_argument('--b0', type=int, default=0); ap.add_argument('--b1', type=int, default=NBLOCKS)
    ap.add_argument('--scale', type=int, default=2)
    ap.add_argument('--pal-at', type=lambda s: int(s, 16))
    a = ap.parse_args()
    ram = ram_from_snap(Path(a.snap))
    pal = palette(a.snap, ram, a.pal_at)
    if a.sheet:
        im = Image.new('RGB', (16 * 17 + 1, 16 * 17 + 1), (40, 40, 40))
        for t in range(NTILES):
            im.paste(to_image(tile_pixels(ram, t), pal), (1 + (t % 16) * 17, 1 + (t // 16) * 17))
        im.resize((im.width * a.scale, im.height * a.scale), Image.NEAREST).save(a.sheet)
        print('wrote', a.sheet)
    if a.level:
        im = to_image(level_index_image(ram, a.b0, a.b1), pal)
        im.resize((im.width * a.scale, im.height * a.scale), Image.NEAREST).save(a.level)
        print('wrote', a.level, im.size)
    if a.cats:
        category_overlay(a.snap, ram, pal, a.b0, a.b1).save(a.cats); print('wrote', a.cats)
    if a.palettes:
        im, rows = palette_swatches(ram)
        im.save(a.palettes)
        for w, addr, pal in rows:
            print(f'world {w}: {addr:#x}')
    if a.check:
        check(a.snap, ram)


if __name__ == '__main__':
    main()
