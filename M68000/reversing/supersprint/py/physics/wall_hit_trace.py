"""wall_hit_trace.py - run the human (red, joystick-0) car into a wall live and record the per-frame state around the impact.
Fire (accelerate) is held; optional steering byte. Frame boundary = bpc $df18 entry.
usage: wall_hit_trace.py <joystick byte hex, e.g. 80> <frames> [out.csv]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pl import *
import ssport as P

byte = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x80
n = int(sys.argv[2]) if len(sys.argv) > 2 else 120
h = Harness(sscfg.SNAP_RACE)
h.cmd('kbd fe %02x' % byte)
rows = []
hdr = 'frame X Y HEAD TGT SPD STUN FLAG VX VY QX QY PX PY F1 F2 TURN'.split()
for i in range(n):
    if h.run_to(0xdf18, 1) is None:
        break
    r = h.snap_ram()
    m = P.Mem(r.b)
    c = 1
    rows.append([i, m.a(P.X, c), m.a(P.Y, c), m.a(P.HEAD, c), m.a(P.TGT, c), m.a(P.SPD, c), m.a(P.STUN, c), m.a(P.FLAG, c),
                 m.a(P.VX, c), m.a(P.VY, c), m.a(P.QX, c), m.a(P.QY, c), m.a(P.PX, c), m.a(P.PY, c), m.au(P.F1, c), m.au(P.F2, c), m.a(P.TURN, c)])
h.close()
import csv
if len(sys.argv) > 3:
    with open(sys.argv[3], 'w', newline='') as f:
        w = csv.writer(f); w.writerow(hdr); w.writerows(rows)
# find the first frame where STUN jumps up or FLAG becomes nonzero
first = next((k for k in range(1, len(rows)) if rows[k][6] > rows[k - 1][6] or rows[k][7] != 0), None)
print('first impact frame index', first)
lo = max(0, (first or 0) - 4)
print(' '.join('%6s' % x for x in hdr))
for row in rows[lo:(first or 0) + 18]:
    print(' '.join('%6s' % x for x in row))
