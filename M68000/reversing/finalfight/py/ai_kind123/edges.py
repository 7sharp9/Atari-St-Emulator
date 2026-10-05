"""edges.py <rec> <idx> [lo hi] [substate-of-state-hex...]: transition counts between states (class/state; state 0c and others listed expand to class/state/sub4)."""
import os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recs import *
G, P = load(sys.argv[1]); idx = int(sys.argv[2])
lo = int(sys.argv[3]) if len(sys.argv) > 3 else 0; hi = int(sys.argv[4]) if len(sys.argv) > 4 else 10**9
expand = set(int(x, 16) for x in sys.argv[5:]) if len(sys.argv) > 5 else {0xc}
E = collections.Counter(); D = collections.Counter(); prev = None; run = 0
def key(r):
    if r[2] == 2 and r[3] in expand: return '%02x.%02x' % (r[3], r[4])
    return '%02x:%02x' % (r[2], r[3]) if r[2] != 2 else '%02x' % r[3]
for f in sorted(P):
    if f < lo or f > hi: continue
    r = P[f].get(idx)
    if r is None: continue
    k = key(r)
    if prev is not None and k != prev:
        E[(prev, k)] += 1
        D[prev] += run
        run = 0
    run += 1
    prev = k
print('transitions:')
for (a, b), n in sorted(E.items()): print('  %s -> %s : %d' % (a, b, n))
