import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from cbrom import *
def ascii_ok(c): return 32 <= c < 127
res = []
tab = 0x1cce
for i in range(0x41):
    p = L(tab + 4*i); q = p; recs = []
    while True:
        attr = W(q); dst = L(q+2); q += 6; codes = []
        while True:
            c = B(q); q += 1
            if c & 0x80:
                c = (c << 8) | B(q); q += 1
                end = (c == 0xffff); break
            codes.append(c)
        recs.append((attr, dst, codes))
        if end: break
    res.append((i, p, recs))
