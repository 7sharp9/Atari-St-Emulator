"""Drone speed cap -3874(A4)[car] after $be40's per-car init: formula from $c1fe..$c226 is 0x3c - 4*track + 4*car + raceCounter(-1748)
(drones only).  Measure it on race_T snapshots (race counter optionally poked) and compare."""
import sys; sys.path.insert(0,'.')
from tkcommon import *
import struct
from wrench_probe import rw
def probe(T, race=None, snapdir='snaps'):
    r = Repl(out(snapdir, 'race_%d.snap' % T))
    if race is not None:
        cur = r.mem(A4 - 1748, 4); r.cmd('w %x %04x%s' % (A4 - 1748, race, cur[2:].hex()))
    r.cmd('s 1500000')
    caps = rw(r, -3874, 4); flags = rw(r, -3914, 4); rc = rw(r, -1748)[0]; r.close()
    ok = all(caps[c] == 0x3c - 4 * T + 4 * c + rc for c in range(4) if flags[c] != 0)
    return caps, flags, rc, ok
if __name__ == '__main__':
    for T in map(int, sys.argv[1:] or range(8)):
        for race in (None, 7):
            caps, flags, rc, ok = probe(T, race, 'snaps_old')
            print('Track %d race counter %d: caps %s drone flags %s -> formula 60-4T+4car+race matches for all drones: %s' % (T + 1, rc, caps, flags, ok), flush=True)
