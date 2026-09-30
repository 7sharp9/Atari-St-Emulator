"""track_range.py - which track indices can SELECT TRACK ($19164) return?  Snapshot inside the select loop (attract + joystick-0 fire,
stopped at the channel read $193c4).  Hold joystick-0 right ($08) or left ($04) for N steps, then fire ($80); read the track argument
that the session passes to the race routine $be40 (first stack word after the return address) and the difficulty word -3954(A4)..."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
from multiprocessing import Pool
SEL = os.path.join(AGENT, 'snap', 'sel2.snap')
def one(args):
    direction, n = args
    r = R(SEL)
    if n: r.cmd('kbd fe %02x' % direction); r.cmd('s %d' % n)
    r.cmd('kbd fe %02x' % (direction | 0x80 if n else 0x80)); r.cmd('s 80000'); r.cmd('kbd fe 00')
    out, g = r.cmd('u be40 40000000')
    tr = r.w16(g['A7'] + 4) if g['PC'] == 0xbe40 else None
    r.close()
    return direction, n, tr
if __name__ == '__main__':
    if not os.path.exists(SEL):
        r = R(sscfg.SNAP_ATTRACT); r.cmd('s 500000'); press(r, ['fe', '80'][:0] or ['2a'], 0) if False else None
        r.cmd('kbd fe 80'); r.cmd('s 60000'); r.cmd('kbd fe 00')
        out, g = r.cmd('u 193c4 3000000'); print('select loop at', hex(g['PC']))
        r.cmd('snap %s' % SEL); r.close()
    jobs = [(d, n) for d in (0x08, 0x04) for n in range(0, 1100001, 50000)]
    with Pool(6) as p: res = p.map(one, jobs)
    for d in (0x08, 0x04):
        print('hold', 'right' if d == 8 else 'left ', [(n // 1000, t) for dd, n, t in res if dd == d])
    print('track indices seen:', sorted(set(t for _, _, t in res if t is not None)))
