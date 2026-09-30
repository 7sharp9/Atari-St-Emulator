"""The 16x8 'cell sprites' blitted by $14262 (oil, cones, wrench, bonus, ...): SUPER.DAT sprite sheet +$cc0, 64 bytes each
(8 rows x one 16-px group x 4 planes).  Renders ids 0..N to agents/tracks/png/cell_sprites.png."""
import sys; sys.path.insert(0,'.')
from tkcommon import *
import trackdata as TD, trackrender as TR, struct
from PIL import ImageDraw
def cell(i):
    d = TD.sup(); o = TD.F['sprites'] + 0xcc0 + i * 64
    buf = bytearray(16 * 4 * 8 // 4 * 0)
    rows = []
    for r in range(8):
        ws = struct.unpack('>4H', d[o + 8 * r: o + 8 * r + 8]); px = []
        for x in range(16):
            px.append(sum(((ws[p] >> (15 - x)) & 1) << p for p in range(4)))
        rows.append(px)
    return rows
if __name__ == '__main__':
    g = TR.Gfx(); pal = struct.unpack('>16H', g.init[-6078])
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 48
    S = 6
    sheet = Image.new('RGB', (8 * (16 * S + 6), ((n + 7) // 8) * (8 * S + 14)), (40, 40, 40)); d = ImageDraw.Draw(sheet)
    for i in range(n):
        im = Image.new('RGB', (16, 8))
        for y, row in enumerate(cell(i)):
            for x, v in enumerate(row): im.putpixel((x, y), st_rgb(pal[v]))
        sheet.paste(im.resize((16 * S, 8 * S), Image.NEAREST), ((i % 8) * (16 * S + 6), (i // 8) * (8 * S + 14) + 12))
        d.text(((i % 8) * (16 * S + 6), (i // 8) * (8 * S + 14)), '%d/%x' % (i, i), fill=(255, 255, 255))
    sheet.save(out('png', 'cell_sprites.png')); print('ok')
