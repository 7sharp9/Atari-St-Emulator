"""Tornado hit test ($ea56): race counter poked to 5 so $b094 enables the roaming object; park the human car at (x, y+12) of the
tornado ((-1780,-1782)(A4)) and watch -3866(A4)[car] (set to 0x1c) and -3826(A4)[car] (|= 0x10); control: car 40 px away."""
import sys; sys.path.insert(0,'.')
from tkcommon import *
import struct
from wrench_probe import rw, setw
def run(T, dist):
    r = Repl(out('snaps', 'race_%d.snap' % T))
    cur = r.mem(A4 - 1748, 4); r.cmd('w %x 0005%s' % (A4 - 1748, cur[2:].hex()))
    r.cmd('s 3000000')
    flags = rw(r, -3914, 4); human = [i for i in range(4) if flags[i] == 0][0]
    tx, ty = rw(r, -1780)[0], rw(r, -1782)[0]
    X, Y = tx + dist, ty + 12
    for o, v in ((-3786, X * 8), (-3738, X * 8), (-3794, Y * 8), (-3746, Y * 8)): setw(r, o + 2 * human, v)
    before = (rw(r, -3866, 4)[human], rw(r, -3826, 4)[human] & 0xffff)
    r.cmd('s 6000')
    after = (rw(r, -3866, 4)[human], rw(r, -3826, 4)[human] & 0xffff)
    r.close(); return (tx, ty), before, after
if __name__ == '__main__':
    T = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    for dist in (0, 5, 7, 9, 40):
        t, b, a = run(T, dist)
        print('tornado at %s, car dx=%-2d : (turn-acc, flags) before %s after %s' % (t, dist, (b[0], hex(b[1])), (a[0], hex(a[1]))))
