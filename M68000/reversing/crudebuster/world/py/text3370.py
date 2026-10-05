import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from cbrom import *
tab = 0x3456
allc = set()
res = []
for i in range(24):
    p = L(tab + 4*i); q = p; lines = []
    while True:
        attr = W(q); dst = L(q+2); q += 6; codes = []
        while True:
            c = W(q); q += 2
            if c == 0xffff: end = True; break
            if c == 0xfffe: end = False; break
            codes.append(c); allc.add(c)
        lines.append((attr, dst, codes))
        if end: break
    res.append((i, p, lines))
if __name__ == "__main__":
    print(sorted(hex(c) for c in allc), len(allc))
    for i, p, lines in res:
        print(i, hex(p))
        for a, d, cs in lines: print("   ", hex(a), hex(d), " ".join("%x" % c for c in cs))
