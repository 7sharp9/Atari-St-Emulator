"""Re-run every static proof for the track data against the live snapshots (agents/tracks/snaps/race_T.snap, made by
drive_track.py) and print one summary line per proof.  Usage:  uv run python prove_all.py [--drive]   (--drive first makes
any missing race_T.snap by driving the real game, ~1.5 min per track)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tkcommon import *
import numpy as np
import initmap, trackdata as TD, trackrender as TR, trackpath as TP, attrmap as AM, occlusion as OC, roadmask as RM
import collision as CO

if '--drive' in sys.argv:
    import drive_track
    for t in range(8):
        if not os.path.exists(out('snaps', 'race_%d.snap' % t)): drive_track.drive(t)

g = TR.Gfx()
tot = dict(bg=0, bgN=0)
print('== INIT.DAT split (loader $fd9a) vs live globals')
res, n = initmap.split_init(); ram0 = load_snap(out('snaps', 'race_0.snap'))
eq = sum(sum(1 for i in range(ln) if ram0[A4 + off + i] == b[i]) for off, ln, pos, b in res)
print('  %d copies, %d of %d INIT.DAT bytes equal to RAM' % (len(res), eq, n))
print('== per track (0-based T; Track N = T+1): background / collision fill / attribute map / occlusion / wall planes')
for t in range(8):
    ram = load_snap(out('snaps', 'race_%d.snap' % t))
    live = planar_to_idx(ram[0x59736:0x59736 + 32000]); buf = TR.build_bg(g, t); py = planar_to_idx(buf)
    bg = int((live[6:] == py[6:]).sum())                     # rows 0-5 are the HUD label strip painted later
    pl, seeds = CO.outline_plane(t); fill = CO.fill(pl, seeds)
    fl = int((fill == CO.plane_from_ram(ram, 0x61436 + 8000)).sum())
    am = AM.attr_map(t); at = sum(1 for a, b in zip(am, ram[0x671f6:0x671f6 + 1000]) if a == b)
    b2 = g.tiles(t); occ = OC.occlusion(g, t, planar_to_idx(b2))
    oc = int((occ == CO.plane_from_ram(ram, 0x61436 + 16000)).sum())
    b3 = g.tiles(t); g.scenery(t, b3); wall = RM.road_plane(planar_to_idx(b3))
    wl = int((wall == CO.plane_from_ram(ram, 0x61436)).sum())
    print('  Track %d: bg rows6-199 %d/%d | fill plane %d/64000 | attr map %d/1000 | occlusion %d/64000 | wall plane %d/64000' %
          (t + 1, bg, py[6:].size, fl, at, oc, wl))
print('== racing line closure (max join gap in world units, 8 units = 1 px) and lane lengths')
for t in range(8):
    e = [max(TP.closure_error(t, c)) for c in (0, 1)]
    print('  Track %d: %d records, even-car lane %d segs, odd-car lane %d segs, max gap %d units' %
          (t + 1, len(TD.waypoints(t)), len(TP.lane_segments(t, 0)), len(TP.lane_segments(t, 1)), max(e)))
