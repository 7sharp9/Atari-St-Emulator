"""walls_all_tracks.py - rasterise the wall vector data of all 8 tracks (same decoder/Bresenham/flood-fill as rebuild_walls.py, verified pixel-exact on Track 1)
into one montage. Tracks other than 1 are NOT cross-checked against a live race (only Track 1's planes are resident in the snapshots).
usage: walls_all_tracks.py [snap]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pl import *
from rebuild_walls import decode, bresenham, flood
import numpy as np
from PIL import Image, ImageDraw

snap = sys.argv[1] if len(sys.argv) > 1 else sscfg.SNAP_RACE
r = Ram(snap)
tiles = []
for t in range(8):
    try:
        polys, lines, seeds, ns = decode(r, t)
        pl = np.zeros((200, 320), dtype=bool)
        for (a, b) in lines:
            bresenham(pl, a[0], a[1], b[0], b[1])
        edge = pl.copy()
        for (sx, sy) in seeds:
            flood(pl, sx, sy)
        img = np.zeros((200, 320, 3), dtype=np.uint8) + 235
        img[pl] = (70, 70, 80)
        img[edge] = (230, 30, 30)
        print('track %d: polylines %s segments %d seeds %s solid %.1f%%' % (t + 1, [len(p) for p in polys], len(lines), seeds, 100.0 * pl.mean()))
    except Exception as ex:
        print('track', t + 1, 'decode failed', ex)
        img = np.zeros((200, 320, 3), dtype=np.uint8)
    tiles.append(img)
S = 2
W, H = 320 * S, 200 * S
sheet = Image.new('RGB', (W * 4 + 30, H * 2 + 20), (20, 20, 20))
d = ImageDraw.Draw(sheet)
for i, t in enumerate(tiles):
    im = Image.fromarray(t).resize((W, H), Image.NEAREST)
    sheet.paste(im, ((i % 4) * (W + 10), (i // 4) * (H + 10)))
    d.text(((i % 4) * (W + 10) + 6, (i // 4) * (H + 10) + 4), 'track %d' % (i + 1), fill=(0, 0, 0))
sheet.save(os.path.join(OUT, 'walls_all_tracks.png'))
