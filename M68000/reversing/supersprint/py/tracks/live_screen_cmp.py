"""Compare the Python-built Track 1 background with a LIVE on-screen race frame (the shifter's current base in ss_prep.snap:
cars, HUD numbers and the wrench sprite are present).  Reports equal pixels and lists the differing blobs."""
import sys; sys.path.insert(0,'.')
from tkcommon import *
import trackrender as TR, numpy as np
from gfxview import load_video_regs

def blobs(mask, gap=3):
    h, w = mask.shape; seen = np.zeros_like(mask); res = []
    ys, xs = np.nonzero(mask)
    pts = set(zip(ys.tolist(), xs.tolist()))
    while pts:
        y0, x0 = pts.pop(); st = [(y0, x0)]; comp = [(y0, x0)]
        while st:
            y, x = st.pop()
            for dy in range(-gap, gap + 1):
                for dx in range(-gap, gap + 1):
                    q = (y + dy, x + dx)
                    if q in pts: pts.remove(q); st.append(q); comp.append(q)
        yy = [p[0] for p in comp]; xx = [p[1] for p in comp]
        res.append((min(xx), min(yy), max(xx), max(yy), len(comp)))
    return sorted(res, key=lambda b: -b[4])

if __name__ == '__main__':
    snap = sys.argv[1] if len(sys.argv) > 1 else sscfg.SNAP_RACE
    track = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    ram = load_snap(snap); regs = load_video_regs(snap)
    live = planar_to_idx(ram[regs['base']:regs['base'] + 32000])
    py = planar_to_idx(TR.build_bg(TR.Gfx(), track))
    eq = live == py
    print('live screen base $%x vs Python track %d background: %d/%d pixels equal (%.2f%%)' % (regs['base'], track + 1, eq.sum(), eq.size, 100 * eq.mean()))
    bl = blobs(~eq)
    print('%d differing blobs; the largest (x0,y0,x1,y1,pixels):' % len(bl))
    for b in bl[:12]: print('  ', b)
    inside = ~eq[6:, :]
    print('differing pixels in rows >= 6 (playfield, below the HUD label strip): %d' % inside.sum())
