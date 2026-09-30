"""Bonus (attr 0x11, $abd4) pickup: wait for the bonus object to appear, teleport the human car on it, and compare the car's
6-digit score array -4846(A4)+car*6 before/after ($16084 adds a descriptor from -4900(A4): 100/150/200/250 by growth stage)."""
import sys; sys.path.insert(0,'.')
from tkcommon import *
import struct
from wrench_probe import rw, setw
def digits(r, car): return list(r.mem(A4 - 4846 + 6 * car, 6))
def main(T):
    r = Repl(out('snaps', 'race_%d.snap' % T)); r.cmd('s 3000000')
    flags = rw(r, -3914, 4); human = [i for i in range(4) if flags[i] == 0][0]
    mapptr = struct.unpack('>I', r.mem(A4 - 1910, 4))[0]
    for _ in range(3000):
        r.cmd('s 12000')
        if rw(r, -1836)[0] >= 1 and (rw(r, -1838)[0] & 0x7f) >= 0: 
            cell = rw(r, -1844)[0]
            if r.mem(mapptr + cell, 1)[0] & 0x11 == 0x11: break
    col, row = rw(r, -1840)[0], rw(r, -1842)[0]; cell = rw(r, -1844)[0]
    print('track %d: bonus object phase=%d stage(-1838&0x7f)>>2=%d at cell col=%d row=%d (px %d,%d) attr=%s' % (
        T + 1, rw(r, -1836)[0], (rw(r, -1838)[0] & 0x7f) >> 2, col, row, col * 8, row * 8, r.mem(mapptr + cell, 2).hex()))
    before = digits(r, human); head = rw(r, -3706, 4)[human]
    import initmap
    res = initmap.split_init()[0]; tab = struct.unpack('>64h', [b for o, ln, pos, b in res if o == -4566][0])
    dx1, dy1 = tab[4 * head], tab[4 * head + 1]
    X = col * 8 + 4 - dx1; Y = row * 8 + 4 - dy1
    for o, v in ((-3786, X * 8), (-3738, X * 8), (-3794, Y * 8), (-3746, Y * 8)): setw(r, o + 2 * human, v)
    r.cmd('s 40000')
    after = digits(r, human)
    print('human slot %d score digits before %s after %s ; pickup flag -1846=%d ; cell now %s' % (human, before, after, rw(r, -1846)[0], r.mem(mapptr + cell, 2).hex()))
    r.close()
if __name__ == '__main__': main(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
