"""mk_tracks.py - one race snapshot per track 0..7 (snap/race_t<N>.snap): from snap/sel2.snap (SELECT TRACK, joystick 0 = red car) hold right
N steps (N from track_range.py's table), fire, skip the prepare countdown with ESC, run into the race, 600k steps past the first $df18."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
from multiprocessing import Pool
HOLD = {0: 0, 1: 50000, 2: 100000, 3: 200000, 4: 250000, 5: 325000, 6: 950000, 7: 475000}
def mk(t):
    r = R(os.path.join(AGENT, 'snap', 'sel2.snap'))
    if HOLD[t]: r.cmd('kbd fe 08'); r.cmd('s %d' % HOLD[t])
    r.cmd('kbd fe %02x' % (0x88 if HOLD[t] else 0x80)); r.cmd('s 80000'); r.cmd('kbd fe 00')
    out, g = r.cmd('u be40 40000000'); trk = r.w16(g['A7'] + 4)
    out, g = r.cmd('u 18626 40000000')
    r.cmd('kbd 01'); r.cmd('s 30000'); r.cmd('kbd 81')
    out, g = r.cmd('u df18 60000000')
    r.cmd('s 600000')
    r.cmd('snap %s' % os.path.join(AGENT, 'snap', 'race_t%d.snap' % t)); r.close()
    return t, trk
if __name__ == '__main__':
    with Pool(8) as p: print(p.map(mk, range(8)))
