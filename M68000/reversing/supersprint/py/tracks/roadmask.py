"""$154d2: -94(A4) 8000-byte 1bpp plane = 0 where the finished background pixel is colour 3, 4 or 7 (asphalt and its
   yellow edge colours), 1 elsewhere.  Runs after the scenery sprites and before the $1bc92 polylines.  Checked vs live."""
import sys; sys.path.insert(0,'.')
from tkcommon import *
import trackrender as TR, numpy as np
from collision import plane_from_ram
ROAD = (3, 4, 7)
def road_plane(idx): return ~np.isin(idx, ROAD)
if __name__ == '__main__':
    g = TR.Gfx()
    for t in map(int, sys.argv[1:] or range(8)):
        b = g.tiles(t); g.scenery(t, b)
        mine = road_plane(planar_to_idx(b))
        live = plane_from_ram(load_snap(out('snaps', 'race_%d.snap' % t)), 0x61436)
        print('track %d: road plane vs live -94(A4): %d/64000 equal, road px %d' % (t, int((mine == live).sum()), int((~mine).sum())))
