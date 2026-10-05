"""Gate: in play the logic frame counter $8004a advances by exactly 1 per MAME frame (no lag), $80002 stays 0.
Input: framelog.csv from lua/framelog.lua with CB_ADDRS starting "8004a:w,80002:w".  usage: framecount_gate.py <csv> [first_frame]
"""
import csv, sys
first = int(sys.argv[2]) if len(sys.argv) > 2 else 800
v = [[int(x, 16) if i else int(x) for i, x in enumerate(r)] for r in csv.reader(open(sys.argv[1]))]
g = [r for r in v if r[0] >= first]
d = [(g[i + 1][1] - g[i][1]) & 0xffff for i in range(len(g) - 1)]
print("frames %d..%d: $8004a delta 1 in %d of %d steps; $80002 nonzero in %d frames" % (g[0][0], g[-1][0], d.count(1), len(d), sum(1 for r in g if r[2])))
