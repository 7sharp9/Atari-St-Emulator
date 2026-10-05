"""hist.py <rec> <idx> [lo hi]: histogram of (class, state) = bytes 2,3 and the substate 4 while in state 3, frames per state; plus hp trace and hit events (22/63 changes)."""
import os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recs import *
G, P = load(sys.argv[1]); idx = int(sys.argv[2])
lo = int(sys.argv[3]) if len(sys.argv) > 3 else 0; hi = int(sys.argv[4]) if len(sys.argv) > 4 else 10**9
H = collections.Counter(); H4 = collections.Counter(); hp = None; events = []
prevhp = None
for f in sorted(P):
    if f < lo or f > hi: continue
    r = P[f].get(idx)
    if r is None: continue
    H[(r[2], r[3])] += 1
    if r[3] == 0xc: H4[(r[4],)] += 1
    h = w(r, 24)
    if prevhp is not None and h != prevhp: events.append((f, s16(prevhp), s16(h), r[22], r[63], r[3], r[4]))
    prevhp = h
print('frames', sum(H.values()))
for k, v in sorted(H.items()): print('  class %02x state %02x: %d frames' % (k[0], k[1], v))
print('  in state 0c, substate 4(A6): ' + ' '.join('%02x:%d' % (k[0], v) for k, v in sorted(H4.items())))
print('  hp changes (frame, old, new, b22, b63, state, sub):', events[:30])
