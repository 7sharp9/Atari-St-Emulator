"""render_super1.py: SUPER1.DAT [0x2e60,0x4280) -> PNGs.  The 40 cells at 0x2ee0 are an 8x8 colour font (64 bytes per glyph: 8 rows x 4
plane words, the data in the high byte of each word; colour index = p0 + 2*p1 + 4*p2 + 8*p3).  Glyph indices: 0..25 A..Z, 26..35 0..9,
36 '.', 37 ',', 38/39 = '!' and apostrophe-like marks.  The text at 0x3a9a is a stream of glyph indices (0x28 = blank, 0xff = page end)
wrapped here at 40 columns (INFERRED layout).  The file has no palette: the PNGs use a neutral index palette (0 black, 1 white, 2 red, 3 yellow, 4 green, 5 cyan)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uc import *
sys.path.insert(0, os.path.join(sscfg.R, 'tools'))
from PIL import Image, ImageDraw
import struct
d = open(os.path.join(sscfg.FILES, 'SUPER1.DAT'), 'rb').read()
BASE = 0x2ee0

def pal_from_snap(snap, off):
    from gfxview import load_ram
    ram, _ = load_ram(snap)
    out = []
    for i in range(16):
        w = struct.unpack_from('>H', ram, A4 + off + 2 * i)[0]
        out.append(tuple(v * 255 // 7 for v in ((w >> 8) & 7, (w >> 4) & 7, w & 7)))
    return out

def glyph(i):
    cell = d[BASE + i * 64:BASE + i * 64 + 64]
    rows = []
    for r in range(8):
        p = [cell[r * 8 + 2 * k] for k in range(4)]
        rows.append([sum(((p[k] >> (7 - x)) & 1) << k for k in range(4)) for x in range(8)])
    return rows

def put(img, ox, oy, rows, pal, S):
    for y, row in enumerate(rows):
        for x, v in enumerate(row):
            for dy in range(S):
                for dx in range(S): img.putpixel((ox + x * S + dx, oy + y * S + dy), pal[v])

def main():
    pal = [(0, 0, 0), (255, 255, 255), (230, 40, 40), (255, 230, 60), (60, 220, 80), (60, 220, 230)] + [(128, 128, 128)] * 10
    S = 4
    img = Image.new('RGB', (20 * (8 * S + 2) + 2, 2 * (8 * S + 2) + 2), (40, 40, 40))
    for i in range(40): put(img, 2 + (i % 20) * (8 * S + 2), 2 + (i // 20) * (8 * S + 2), glyph(i), pal, S)
    img.save(os.path.join(PNG, 'super1_old_credits_font_40_glyphs_8x8.png')); print('font', img.size)
    # pages
    stream = d[0x3a9a:0x3c8c]
    pages, cur = [], []
    for v in stream:
        if v == 0xff: pages.append(cur); cur = []
        else: cur.append(v)
    print('pages', [len(p) for p in pages])
    img = Image.new('RGB', (328, 2 * 8 * 8 + 12), (0, 0, 0))
    for k, pg in enumerate(pages[:2]):
        for n, v in enumerate(pg):
            if v >= 40: continue
            put(img, 4 + (n % 40) * 8, 2 + k * 70 + (n // 40) * 8, glyph(v), pal, 1)
    img = img.resize((img.width * 2, img.height * 2), Image.NEAREST)
    img.save(os.path.join(PNG, 'super1_old_credits_text_2_pages_40col.png')); print('pages img', img.size)
    # text dump
    def ch(v):
        return chr(65 + v) if v < 26 else str(v - 26) if v < 36 else {0x24: '.', 0x25: ',', 0x26: '!', 0x27: "'", 0x28: ' '}.get(v, '?')
    open(os.path.join(DATA, 'super1_old_credits_text.txt'), 'w').write('\n=====\n'.join(
        '\n'.join(''.join(ch(v) for v in pg[i:i + 40]) for i in range(0, len(pg), 40)) for pg in pages))

main()
