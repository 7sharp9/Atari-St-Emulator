"""surface_effect_trace.py - live effect of a surface-map cell value on the human car: poke cell value V into the map cells under the car's
path (row y=4, x=0..7: pixels x 0..63, y 32..39 on the top straight), hold fire, log per frame.
usage: surface_effect_trace.py <cellvalue hex> [frames] [initial speed]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pl import *
import ssport as P

v = int(sys.argv[1], 16)
n = int(sys.argv[2]) if len(sys.argv) > 2 else 70
h = Harness(sscfg.SNAP_RACE)
h.cmd('kbd fe 80')
h.run_to(0xdf18, 1)
ram = h.snap_ram()
mb = ram.gl(-1910)
for row in (4, 5):
    for x0 in (0, 4, 8, 12, 16, 20, 24, 28):
        h.cmd('w %x %02x%02x%02x%02x' % (mb + row * 40 + x0, v, v, v, v))
if len(sys.argv) > 3:
    poke_arr(h, P.SPD, [60, int(sys.argv[3]), 68, 72])
rows = []
hdr = 'frame X Y HEAD SPD TURN F1 F2 mapcell(3,4) wrench -1856 -1774'.split()
for i in range(n):
    if h.run_to(0xdf18, 1) is None:
        break
    r = h.snap_ram()
    m = P.Mem(r.b)
    c = 1
    rows.append([i, m.a(P.X, c), m.a(P.Y, c), m.a(P.HEAD, c), m.a(P.SPD, c), m.a(P.TURN, c), hex(m.au(P.F1, c)), hex(m.au(P.F2, c)), hex(m.rb(mb + 4 * 40 + 3)), m.a(P.WRENCH, c), m.g(-1856), m.g(-1774)])
h.close()
print('cell value %#x' % v)
print(' '.join('%8s' % x for x in hdr))
prev = None
for row in rows:
    key = tuple(row[3:8])
    if prev is None or key != prev or row[8] != (rows[row[0]-1][8] if row[0] else None) or row[0] % 10 == 0:
        print(' '.join('%8s' % x for x in row))
    prev = key
