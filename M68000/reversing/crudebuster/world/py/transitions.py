"""transitions.py <framelog.csv> <col,col,...> [names]: print rows where the chosen columns change."""
import sys
rows = [l.strip().split(",") for l in open(sys.argv[1])]
cols = [int(c) for c in sys.argv[2].split(",")]
prev = None
for r in rows:
    k = tuple(r[c] for c in cols)
    if k != prev:
        print(r[0], " ".join("%s" % x for x in k)); prev = k
