"""Hazard/pickup state probe. Start from race_T.snap (taken at $beb2, before $a6c4/$a68a/$a8a0/$a828 run), optionally poke the
race counter -1748(A4), run, and dump the object-system globals + a screenshot.
usage: hazard_probe.py T racecounter [steps]"""
import sys; sys.path.insert(0,'.')
from tkcommon import *
import struct
V = dict(race=-1748, oil_n=-1858, obst_n=-1766, roam=-1776, arrows=-1792, gates=-1808, wr_state=-1850, wr_timer=-1848,
         wr_col=-1852, wr_row=-1854, bonus_flag=-1846, bonus_phase=-1836, bonus_col=-1840, bonus_row=-1842, bonus_cell=-1844,
         ramp=-1896, banner=-1802, wrench_pick=-1856)
def probe(T, race, steps=2500000, tag=None):
    r = Repl(out('snaps', 'race_%d.snap' % T))
    if race is not None:
        cur = r.mem(A4 - 1748, 4)
        r.cmd('w %x %04x%s' % (A4 - 1748, race, cur[2:].hex()))
    r.cmd('s %d' % steps)
    b = r.mem(A4 - 1900, 160)
    w = lambda o, n=1: [struct.unpack('>h', b[(o + 1900) + 2*i:(o + 1900) + 2*i + 2])[0] for i in range(n)]
    st = {k: w(o)[0] for k, o in V.items()}
    st['oil_types'] = w(-1888, 3); st['oil_row'] = w(-1878, 3); st['oil_col'] = w(-1868, 3)
    st['obst_row'] = w(-1764, 4); st['obst_col'] = w(-1756, 4); st['obst_state'] = w(-1774, 4)
    st['roam_xy'] = w(-1780, 2); st['gate_state'] = w(-1814, 3); st['gate_pos'] = w(-1820, 3); st['gate_val'] = w(-1832, 3)
    if tag:
        p = out('snaps', 'haz_%s.snap' % tag); r.cmd('snap ' + p); render_snap(p, out('dbg', 'haz_%s.png' % tag))
    r.close(); return st
if __name__ == '__main__':
    T = int(sys.argv[1]); race = int(sys.argv[2]); steps = int(sys.argv[3]) if len(sys.argv) > 3 else 2500000
    print(probe(T, race, steps, tag='t%d_r%d' % (T, race)))
