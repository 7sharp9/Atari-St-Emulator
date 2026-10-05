"""trans.py <rec file> <idx> [lo hi]: print state transitions (2/3/4/5 bytes) of pool-2 record idx with position, hp, 44/45, 22/63, Cody hp"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recs import *
G, P = load(sys.argv[1]); idx = int(sys.argv[2])
lo = int(sys.argv[3]) if len(sys.argv) > 3 else 0; hi = int(sys.argv[4]) if len(sys.argv) > 4 else 10**9
prev = None; last = None
for f in sorted(P):
    if f < lo or f > hi: continue
    r = P[f].get(idx)
    if r is None: continue
    s = st(r)
    if s != prev:
        c = P[f]['c']
        print('%d st=%s x=%04x y=%04x hp=%04x b44/45=%02x/%02x b22/63=%02x/%02x t30=%d b23=%d f136/137/129=%d/%d/%d tgt=%d/%04x slot146=%d c.hp=%04x c.st=%s cx=%04x cy=%04x' % (
            f, s, w(r, 6), w(r, 10), w(r, 24), r[44], r[45], r[22], r[63], r[30], r[23], r[136], r[137], r[129], w(r, 144), w(r, 148), w(r, 146), w(c, 24), st(c), w(c, 6), w(c, 10)))
        prev = s
