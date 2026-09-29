"""Decode and render Impossamole's sprite banks from a snapshot's RAM.

Two banks, both 4-plane interleaved ST rows, colour index 0 transparent (the blitters `$1b5a4`/`$1ad32`
build the mask as the OR of the four planes and `and`/`or` it onto the screen):
  bank 1  $3b600  128 bytes/frame  16 px x 16 rows  (8 bytes/row = 4 words); index = 6(A0) of a type-1 object
  bank 2  $42e00  384 bytes/frame  32 px x 24 rows  (16 bytes/row = 4 plane longwords); index = 6(A0) of the type-2 (hero) object
Bank 2 is populated only on a fresh-cold-boot lineage (README "Why no hero sprite was visible").

    uv run python reversing/impossamole/py/sprites.py <snap> --bank 1|2 <out.png> [--scale N] [--cols N]
    uv run python reversing/impossamole/py/sprites.py <snap> --font <out.png>     # 8x8 font at $24000
    uv run python reversing/impossamole/py/sprites.py <snap> --check              # sprites vs the live screen
    uv run python reversing/impossamole/py/sprites.py <snap> --frame <bank> <idx> <out.png> [--scale N]
"""
import argparse, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tiles import ram_from_snap, palette
from PIL import Image, ImageDraw

BANKS = {1: dict(base=0x3b600, stride=128, w=16, h=16, end=0x42e00),
         2: dict(base=0x42e00, stride=384, w=32, h=24, end=0x50000)}
TRANSPARENT = (255, 0, 255)


def frame_rows(ram, bank, idx):
    b = BANKS[bank]
    off = b['base'] + idx * b['stride']
    rows = []
    for y in range(b['h']):
        if b['w'] == 16:  # four plane words per row
            p = struct.unpack_from('>4H', ram, off + y * 8)
            rows.append([sum(((p[k] >> (15 - x)) & 1) << k for k in range(4)) for x in range(16)])
        else:  # four plane longwords per row (the blitter ORs 4 longs for the mask, $1b67c)
            p = struct.unpack_from('>4L', ram, off + y * 16)
            rows.append([sum(((p[k] >> (31 - x)) & 1) << k for k in range(4)) for x in range(32)])
    return rows


def frame_image(ram, bank, idx, pal):
    rows = frame_rows(ram, bank, idx)
    im = Image.new('RGB', (len(rows[0]), len(rows)))
    im.putdata([TRANSPARENT if v == 0 else pal[v] for r in rows for v in r])
    return im


def used_frames(ram, bank):
    b = BANKS[bank]
    n = (b['end'] - b['base']) // b['stride']
    return [i for i in range(n) if any(ram[b['base'] + i * b['stride']: b['base'] + (i + 1) * b['stride']])]


def sheet(ram, bank, pal, scale, cols):
    b = BANKS[bank]
    frames = used_frames(ram, bank)
    cw, ch = b['w'] * scale + 2, b['h'] * scale + 2 + 10
    rows_n = (frames[-1] // cols) + 1
    im = Image.new('RGB', (cols * cw, rows_n * ch), (40, 40, 40))
    d = ImageDraw.Draw(im)
    for i in frames:
        f = frame_image(ram, bank, i, pal).resize((b['w'] * scale, b['h'] * scale), Image.NEAREST)
        x, y = (i % cols) * cw + 1, (i // cols) * ch + 11
        im.paste(f, (x, y))
        d.text((x, y - 10), str(i), fill=(200, 200, 200))
    return im


FONT, FONT_GLYPHS = 0x24000, 128  # $25000 starts the tile-classification table, so 128 glyphs at most


def font_sheet(ram, pal, scale):
    """8x8 glyphs, 32 bytes each: 8 rows of 4 plane bytes (tile-string drawer $1c0aa, glyph = byte << 5)."""
    im = Image.new('RGB', (16 * 9 + 1, (FONT_GLYPHS // 16) * 9 + 1), (40, 40, 40))
    for g in range(FONT_GLYPHS):
        gi = Image.new('RGB', (8, 8))
        px = []
        for y in range(8):
            pl = ram[FONT + g * 32 + y * 4: FONT + g * 32 + y * 4 + 4]
            for x in range(8):
                v = sum(((pl[k] >> (7 - x)) & 1) << k for k in range(4))
                px.append(TRANSPARENT if v == 0 else pal[v])
        gi.putdata(px)
        im.paste(gi, (1 + (g % 16) * 9, 1 + (g // 16) * 9))
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST)


OBJ, OBJ_STRIDE, OBJ_SLOTS = 0x1a2ea, 0x6c, 20


def check(snap, ram):
    """For every live type-1/type-2 object slot, blit its frame at its declared (2(A0), 4(A0)) and count
    how many opaque pixels equal the screen pixel there, against both screen buffers ($1a2e4 draw buffer
    and the live video base). Sprites overlap and the HUD/other sprites draw over them, so this is a
    lower bound, reported per slot."""
    from tiles import screen_index_rows
    from gfxview import load_video_regs
    bufs = {'live': load_video_regs(str(snap))['base'], 'draw': struct.unpack_from('>I', ram, 0x1a2e4)[0]}
    scr = {k: screen_index_rows(ram, v) for k, v in bufs.items()}
    for s in range(OBJ_SLOTS):
        a = OBJ + s * OBJ_STRIDE
        typ, x, y, fr = struct.unpack_from('>4H', ram, a)
        h = ram[a + 14]
        if typ not in (1, 2) or not (0 <= x < 320 and 0 <= y < 200):
            continue
        bank = typ
        rows = frame_rows(ram, bank, fr)[:h]
        res = {}
        for k, sc in scr.items():
            n = m = 0
            for dy, r in enumerate(rows):
                for dx, v in enumerate(r):
                    if v and 0 <= x + dx < 320 and 0 <= y + dy < 200:
                        n += 1; m += sc[y + dy][x + dx] == v
            res[k] = (m, n)
        best = max(res.items(), key=lambda kv: kv[1][0] / max(kv[1][1], 1))
        print(f'slot {s:2d} type {typ} frame {fr:3d} at ({x:3d},{y:3d}) h={h:2d}: '
              f'{best[0]} buffer {best[1][0]}/{best[1][1]} opaque pixels match')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('snap')
    ap.add_argument('--bank', nargs=2, metavar=('N', 'OUT'))
    ap.add_argument('--frame', nargs=3, metavar=('BANK', 'IDX', 'OUT'))
    ap.add_argument('--font', metavar='OUT')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--scale', type=int, default=3)
    ap.add_argument('--cols', type=int, default=16)
    ap.add_argument('--pal-at', type=lambda s: int(s, 16))
    a = ap.parse_args()
    ram = ram_from_snap(Path(a.snap))
    pal = palette(a.snap, ram, a.pal_at)
    if a.bank:
        im = sheet(ram, int(a.bank[0]), pal, a.scale, a.cols)
        im.save(a.bank[1]); print('wrote', a.bank[1], im.size)
    if a.font:
        font_sheet(ram, pal, a.scale).save(a.font); print('wrote', a.font)
    if a.check:
        check(a.snap, ram)
    if a.frame:
        b = int(a.frame[0])
        im = frame_image(ram, b, int(a.frame[1]), pal)
        im.resize((im.width * a.scale, im.height * a.scale), Image.NEAREST).save(a.frame[2])


if __name__ == '__main__':
    main()
