import sys; sys.path.insert(0,'.')
from tkcommon import *
import trackrender as TR
def compare(t, snap=None, verbose=True):
    snap = snap or out('snaps','race_%d.snap'%t)
    ram = load_snap(snap)
    live = ram[0x59736:0x59736+32000]
    g = TR.Gfx()
    py = TR.build_bg(g, t)
    li = planar_to_idx(live); pi = planar_to_idx(py)
    import numpy as np
    eq = (li == pi); n = int(eq.sum())
    if verbose: print('track %d: %d/%d pixels equal (%.3f%%)' % (t, n, eq.size, 100*n/eq.size))
    return li, pi, eq
if __name__ == '__main__':
    for t in map(int, sys.argv[1:] or [0]):
        li, pi, eq = compare(t)
