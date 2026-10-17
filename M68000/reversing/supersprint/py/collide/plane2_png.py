"""plane2_png.py - montage of the decoded plane 2 (cars drawn BEHIND the red pixels) over the pre-scenery art, all 8 tracks -> agents/collide/png/plane2_all_tracks.png"""
import sys, os
sys.argv = [sys.argv[0]]
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import plane2_decode as D
from tkcommon import *
import numpy as np
from PIL import Image
g = D.TR.Gfx(); W = os.path.join(sscfg.WORK, 'agents', 'collide', 'png'); os.makedirs(W, exist_ok=True)
sheet = Image.new('RGB', (1280, 400))
for t in range(8):
    ram = load_snap(out('snaps', 'race_%d.snap' % t)); idx = planar_to_idx(g.tiles(t))
    m = D.decode_plane2(D.records(ram, t), idx, D.OCC.EDGE)
    rgb = np.stack([idx * 12] * 3, -1).astype(np.uint8)
    rgb[~m] = (0.45 * rgb[~m] + 0.55 * np.array([255, 0, 0])).astype(np.uint8)
    sheet.paste(Image.fromarray(rgb), ((t % 4) * 320, (t // 4) * 200))
sheet.save(os.path.join(W, 'plane2_all_tracks.png')); print('wrote', os.path.join(W, 'plane2_all_tracks.png'))
