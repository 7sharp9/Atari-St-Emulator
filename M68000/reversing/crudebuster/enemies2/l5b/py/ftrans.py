"""Print F lines of an objlog.txt only when a chosen set of columns changes.
usage: ftrans.py objlog.txt f0 f1 col,col,...   (columns are indexes into the F line fields: 2 lvl 3 sx 4 sy 5 px 6 py 7 hp 8 f40 9 f41 10 n, 11.. = CB_X values)"""
import sys
fn, f0, f1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
cols = [int(c) for c in sys.argv[4].split(",")]
last = None
for line in open(fn):
    if not line.startswith("F "): continue
    p = line.split()
    f = int(p[1])
    if f < f0 or f > f1: continue
    cur = tuple(p[c] for c in cols if c < len(p))
    if cur != last:
        print(line.rstrip()); last = cur
