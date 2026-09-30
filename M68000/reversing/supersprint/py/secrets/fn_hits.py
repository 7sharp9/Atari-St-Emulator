"""fn_hits.py SNAP PRE N : run PRE steps, then count entries of every link-A6 function over the next N steps (prints those hit,
ordered by first hit step)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
import reach
ins = reach.load()
links = [a for a, t in ins if t.startswith('link')]
snap = sys.argv[1]; pre = int(sys.argv[2]); n = int(sys.argv[3])
r = R(getattr(sscfg, snap) if hasattr(sscfg, snap) else snap)
if pre: r.cmd('s %d' % pre)
h, regs = hits(r, n, links)
for a, (c, first, last) in sorted(h.items(), key=lambda kv: kv[1][1]):
    if c: print('%06x count %6d first %8d last %8d' % (a, c, first, last))
r.close()
