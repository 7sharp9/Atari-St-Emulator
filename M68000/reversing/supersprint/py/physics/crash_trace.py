"""crash_trace.py - head-on wall impact at the car's speed cap (-> $b3fc crash path): poke speed = cap for the human car, hold fire, log frames.
usage: crash_trace.py [frames] [out.csv] [--png prefix]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pl import *
import ssport as P

n = int(sys.argv[1]) if len(sys.argv) > 1 else 150
h = Harness(sscfg.SNAP_RACE)
h.cmd('kbd fe 80')
h.run_to(0xdf18, 1)
ram = h.snap_ram()
# human car 1 starts at x=31 heading west; give it full speed
poke_arr(h, P.SPD, [60, 110, 68, 72])
rows = []
hdr = 'frame X Y HEAD SPD STUN FLAG TURN SAFEX SAFEY h1896 h1894 h1890 h1892'.split()
shots = []
for i in range(n):
    if h.run_to(0xdf18, 1) is None:
        break
    r = h.snap_ram()
    m = P.Mem(r.b)
    c = 1
    rows.append([i, m.a(P.X, c), m.a(P.Y, c), m.a(P.HEAD, c), m.a(P.SPD, c), m.a(P.STUN, c), m.a(P.FLAG, c), m.a(P.TURN, c),
                 m.a(P.SAFEX, c), m.a(P.SAFEY, c), m.g(-1896), m.g(-1894), m.g(-1890), m.g(-1892)])
    if len(sys.argv) > 3 and i in (6, 10, 14, 20, 40, 80):
        h.cmd('snap %s' % os.path.join(OUT, 'crash_f%03d.snap' % i))
h.close()
import csv
if len(sys.argv) > 2 and not sys.argv[2].startswith('--'):
    with open(sys.argv[2], 'w', newline='') as f:
        w = csv.writer(f); w.writerow(hdr); w.writerows(rows)
first = next((k for k in range(1, len(rows)) if rows[k][6] != 0), None)
print('crash frame index', first)
print(' '.join('%6s' % x for x in hdr))
for row in rows[max(0, (first or 0) - 3):(first or 0) + 12] + rows[-6:]:
    print(' '.join('%6s' % x for x in row))
