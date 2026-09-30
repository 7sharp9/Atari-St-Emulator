"""drone_snap_trace.py - does a drone car's position get re-seeded onto the waypoint table entry when it changes waypoint?
Steps frame by frame (bpc $df18), logs per drone: WP, Q (1/8 px), the table entry for WP, and the jump in Q across each WP change.
usage: drone_snap_trace.py [frames]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pl import *
import ssport as P

n = int(sys.argv[1]) if len(sys.argv) > 1 else 400
h = Harness(sscfg.SNAP_RACE)
prev = None
changes = []
for i in range(n):
    if h.run_to(0xdf18, 1) is None:
        break
    r = h.snap_ram()
    m = P.Mem(r.b)
    st = {c: (m.a(P.WP, c), m.a(P.QX, c), m.a(P.QY, c), m.a(P.SPD, c), m.a(P.HEAD, c)) for c in (0, 2, 3)}
    if prev:
        for c in (0, 2, 3):
            if st[c][0] != prev[c][0]:
                tbl = m.gl(-4084)
                rec = (m.rws(tbl + 8 * st[c][0]), m.rws(tbl + 8 * st[c][0] + 2))
                jump = (st[c][1] - prev[c][1], st[c][2] - prev[c][2])
                changes.append((i, c, prev[c][0], st[c][0], prev[c][1:3], st[c][1:3], rec, jump))
    prev = st
print('frames', i + 1, 'waypoint changes', len(changes))
print('frame car wp_old->wp_new  Q_before -> Q_after   table_entry(new)  dQ')
for ch in changes[:25]:
    print(ch)
# how far is Q (after the change) from the table entry of the new waypoint (should be 0 if re-seeded)
print('after-change |Q - table entry| (1/8 px): max', max(max(abs(c[5][0] - c[6][0]), abs(c[5][1] - c[6][1])) for c in changes) if changes else None,
      ' of changes with jump>3:', sum(1 for c in changes if max(abs(c[7][0]), abs(c[7][1])) > 3), '/', len(changes))
h.close()
