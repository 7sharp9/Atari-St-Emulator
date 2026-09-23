"""ktrack.py <snap> <frames> <every> : run on and print every knight (entity +14 != 0) each `every` frames."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pwlib import *
import powers_ref as P
snap, n, every = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
r = Repl2(snap)
for f in range(0, n, every):
    r.cmd('s %d' % (every * 105000))
    m = bytearray(0x3c4e4)
    ents = r.mem(P.ENT, 0x16 * 210)
    fr = int.from_bytes(r.mem(P.FRAME, 2), 'big'); ne = int.from_bytes(r.mem(P.NENT, 2), 'big')
    ks = []
    for i in range(ne):
        e = ents[0x16 * i:0x16 * i + 0x16]
        t = int.from_bytes(e[14:18], 'big')
        if t:
            ti = (t - P.ENT) // 0x16
            te = ents[0x16 * ti:0x16 * ti + 0x16]
            c, tc = int.from_bytes(e[8:10], 'big'), int.from_bytes(te[8:10], 'big')
            ks.append('k%d fl%02x s%d str%d (%d,%d) -> e%d fl%02x s%d str%d (%d,%d)' % (i, e[0], e[1], int.from_bytes(e[4:6], 'big', signed=True), c & 63, c >> 6,
                      ti, te[0], te[1], int.from_bytes(te[4:6], 'big', signed=True), tc & 63, tc >> 6))
    print('frame', fr, 'n', ne, '; '.join(ks), flush=True)
r.close()
