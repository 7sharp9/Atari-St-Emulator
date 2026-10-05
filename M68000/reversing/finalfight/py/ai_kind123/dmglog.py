"""dmglog.py <rec> <idx>: Cody health drops caused by the fighter (Cody's +22 = attack id (45 of the attacker), +63 = hit type) with the fighter's state; summarised by (attack id, damage)."""
import os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recs import *
G, P = load(sys.argv[1]); idx = int(sys.argv[2])
prev = None; ev = []
for f in sorted(P):
    c = P[f]['c']; h = w(c, 24); r = P[f].get(idx)
    if prev is not None and h < prev and r is not None and s16(h) > -100:
        ev.append((f, prev - h, c[22], c[63], r[3], r[4], c[60 + 1] if False else w(c, 60)))
    prev = h
cnt = collections.Counter((e[2], e[3], e[1], '%02x.%02x' % (e[4], e[5])) for e in ev)
print('hits on Cody:', len(ev))
for k, v in sorted(cnt.items()): print('  atk id %d type %d dmg %d (enemy state %s) x%d' % (k[0], k[1], k[2], k[3], v))
