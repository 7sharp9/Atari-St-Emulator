"""One-line-per-track summary of everything the data files hold for a track."""
import sys; sys.path.insert(0,'.')
from tkcommon import *
import trackdata as TD, trackpath as TP, attrmap as AM, occlusion as OC, trackrender as TR, struct
from render_all import start_grid, spawn_cells, gates
g = TR.Gfx()
hdr = 'Track | wp recs | forks | merges | gate-jumps | gates | lap px (even/odd lane) | outline pts/lines/seeds | strokes | occl rects | scenery | checkpoints | start grid (X,Y0,dY,hd) | extra skid polylines'
print(hdr)
for t in range(8):
    r = TD.waypoints(t)
    forks = sum(1 for x in r if x[3] == 0x100); gj = sum(1 for x in r if x[3] & 0x200); mg = sum(1 for x in r if x[3] & 0x400)
    lens = []
    for c in (0, 1):
        s = TP.lane_segments(t, c); lens.append(sum(abs(b[0]-a[0]) + abs(b[1]-a[1]) for _, a, b in s) // 8)
    lines, seeds = TD.outline(t); npts = sum(len(l) for l in lines)
    m = AM.attr_map(t); cp = sorted({(v >> 2) & 7 for v in m if (v & 3) == 2 and v & 0x7c})
    w = struct.unpack('>32h', g.init[-1262])[4*t:4*t+4]
    sk = {4: 3, 5: 2, 6: 3}.get(t, 0)
    print('%d | %d | %d | %d | %d | %d | %d/%d | %d/%d/%d | %d | %d | %d | %s | %s | %s' % (
        t+1, len(r), forks, mg, gj, len(gates(g, t)), lens[0], lens[1], npts, len(lines), len(seeds), len(AM.strokes(t)), len(OC.rects(g, t)),
        len(g.scenery_list(t)), cp, w, 'yes' if t + 1 in (5, 6, 7) else 'no'))
