"""plane2_vs_prep.py - explain rebuild_planes02.py's '7583 cleared in RAM': the decode (6793 px, Track 1) against plane 2 of ss_prep.snap (a mid-race snapshot):
   every differing pixel should lie in the HUD rows (0..31) where $158ea/$15e5a stamp digit masks, or in a gate box."""
import sys, os
sys.argv = [sys.argv[0]]
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import plane2_decode as D
from tkcommon import *
import numpy as np
g = D.TR.Gfx(); ram = load_snap(sscfg.SNAP_RACE)
recs = D.records(ram, 0); mine = D.decode_plane2(recs, planar_to_idx(g.tiles(0)), D.OCC.EDGE)
live = np.unpackbits(np.frombuffer(bytes(ram[0x61436 + 16000:0x61436 + 24000]), dtype=np.uint8)).reshape(200, 320).astype(bool)
d = mine != live; ys, xs = np.where(d)
print('ss_prep plane 2: live cleared %d, decode %d, differing %d; rows of differences %d..%d; inside rows 0..31: %d' % ((~live).sum(), (~mine).sum(), d.sum(), ys.min(), ys.max(), int(d[:32].sum())))
print('decode == live outside rows 0..31: %d/%d' % (int((mine[32:] == live[32:]).sum()), live[32:].size))
