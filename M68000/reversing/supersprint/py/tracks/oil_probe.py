"""Effect of the three oil-class attribute cells on a car ($b798 -> $bb16 branch): put a stationary human car (speed poked to 40)
on a cell whose attribute byte we set to 1 / 5 / 9 (= type<<2 | 1, what $a6c4 writes) and watch -3730(A4) speed and -3866(A4)
(turn accumulator).  Cone cell (0x15) for comparison.  usage: oil_probe.py [T]"""
import sys; sys.path.insert(0,'.')
from tkcommon import *
import struct, initmap
from wrench_probe import rw, setw
NSTEP = 6
def run(T, val):
    r = Repl(out('snaps', 'race_%d.snap' % T)); r.cmd('s 3000000')
    flags = rw(r, -3914, 4); human = [i for i in range(4) if flags[i] == 0][0]
    mapptr = struct.unpack('>I', r.mem(A4 - 1910, 4))[0]
    col, row = 8, 12; cell = col + row * 40
    cur = r.mem(mapptr + cell, 4); r.cmd('w %x %02x%02x%s' % (mapptr + cell, val, val, cur[2:].hex()))   # marks cell and cell+1 like $a6c4
    head = rw(r, -3706, 4)[human]
    tab = struct.unpack('>64h', initmap.split_init()[0][[o for o, *_ in initmap.split_init()[0]].index(-4566)][3])
    dx1, dy1, dx2, dy2 = tab[4 * head: 4 * head + 4]
    X = col * 8 + 4 - dx1; Y = row * 8 + 4 - dy1                      # first sample point lands mid-cell
    for o, v in ((-3786, X * 8), (-3738, X * 8), (-3794, Y * 8), (-3746, Y * 8)): setw(r, o + 2 * human, v)
    setw(r, -3730 + 2 * human, 40)
    trace = []
    for k in range(NSTEP):
        r.cmd('s 12000')
        trace.append((rw(r, -3730, 4)[human], rw(r, -3866, 4)[human], rw(r, -3706, 4)[human]))
    a = r.mem(mapptr + cell, 2); r.close()
    return human, head, trace, a
if __name__ == '__main__':
    T = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    if len(sys.argv) > 2: NSTEP = int(sys.argv[2])
    for val, name in ((0x01, 'type0 (blue puddle)'), (0x05, 'type1 (black oil)'), (0x09, 'type2 (yellow slick)'), (0x15, 'cone (t=5)'), (0x00, 'control (no hazard)')):
        human, head, trace, a = run(T, val)
        print('%-22s attr %02x: speed/turn-acc/heading per ~frame %s ; cell after %02x%02x' % (name, val, trace, a[0], a[1]))
