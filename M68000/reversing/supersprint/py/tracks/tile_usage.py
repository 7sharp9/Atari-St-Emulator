"""Which of the 606+1158+1115+65 tile graphics in SUPER.DAT are referenced by the 11 tilemaps?  Renders unreferenced ones."""
import sys; sys.path.insert(0,'.')
from tkcommon import *
import trackdata as TD, trackrender as TR, struct
g = TR.Gfx(); used = [set() for _ in range(4)]
for m in range(11):
    for w in TD.tilemap(m):
        if w & 0x8000: used[(w >> 11) & 3].add(w & 0x7ff)
tot = g.counts
for s in range(4):
    print('tile set %d (%2d B records): %4d tiles, %4d referenced by the 11 tilemaps, %4d unreferenced' % (s, g.recsz[s], tot[s], len(used[s]), tot[s] - len(used[s])))
print('per tilemap: distinct composite tiles / copy tiles / zero words:',
      [(m, len({w & 0x7fff for w in TD.tilemap(m) if w & 0x8000}), sum(1 for w in TD.tilemap(m) if not w & 0x8000 and w), sum(1 for w in TD.tilemap(m) if w == 0)) for m in range(11)])
# render unreferenced tiles (palette: race palette) in a sheet, 8x8 each x4 zoom, 40 per row
pal = struct.unpack('>16H', g.init[-6078])
unref = [(s, i) for s in range(4) for i in range(tot[s]) if i not in used[s]]
print('total unreferenced tiles', len(unref))
def tile_img(s, i):
    w = 0x8000 | (s << 11) | i
    t = g.tile(w, bytearray(32000), 0)           # rows x 4 plane bytes
    im = Image.new('RGB', (8, 8))
    for r in range(8):
        for x in range(8):
            v = sum(((t[r][p] >> (7 - x)) & 1) << p for p in range(4)); im.putpixel((x, r), st_rgb(pal[v]))
    return im
cols = 48; Z = 3
rows = (len(unref) + cols - 1) // cols
sheet = Image.new('RGB', (cols * 8 * Z, max(1, rows) * 8 * Z), (30, 30, 30))
for k, (s, i) in enumerate(unref):
    sheet.paste(tile_img(s, i).resize((8 * Z, 8 * Z), Image.NEAREST), ((k % cols) * 8 * Z, (k // cols) * 8 * Z))
if unref: sheet.save(out('png', 'unreferenced_tiles.png'))
