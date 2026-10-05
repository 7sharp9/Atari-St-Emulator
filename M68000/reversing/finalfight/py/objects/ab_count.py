#!/usr/bin/env python3
"""ab_count.py <log> <from_rel> <to_rel> : per gfx region, the number of frames with a change and the total changed words in the rel window (lines "G name hash nwords")."""
import sys, collections
rel = None; n = collections.Counter(); w = collections.Counter()
lo, hi = int(sys.argv[2]), int(sys.argv[3])
for l in open(sys.argv[1]):
    p = l.split()
    if l.startswith('F '): rel = int(p[2].split('=')[1])
    elif l.startswith('G ') and rel is not None and lo <= rel <= hi: n[p[1]] += 1; w[p[1]] += int(p[3])
print(sys.argv[1], 'rel %d..%d' % (lo, hi), {k: (n[k], w[k]) for k in sorted(n)} or 'no gfx change')
