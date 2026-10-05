import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from cbrom import *
tab = 0x5930
n = 19
res = []
for i in range(n):
    p = L(tab+4*i); q = p; recs = []
    while True:
        attr = W(q); dst = L(q+2); q += 6; cur = []
        while True:
            c = B(q); q += 1
            if c == 0xff: end = True; break
            if c == 0xfe: end = False; q += 1; break
            cur.append(c)
        recs.append((attr, dst, cur))
        if end: break
    res.append((i, p, recs))
if __name__ == "__main__":
    for i, p, recs in res:
        print(i, hex(p))
        for attr, dst, ln in recs: print("   ", hex(attr), hex(dst), " ".join("%02x" % c for c in ln), "|", "".join(chr(c) if 32 <= c < 127 else "." for c in ln))
