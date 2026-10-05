import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from cbrom import *
tab = 0x2962
N = (L(tab) - tab) // 4
res = []
for i in range(N):
    p = L(tab+4*i); q = p; recs = []
    while True:
        attr = W(q); dst = L(q+2); q += 6; cur = []
        while True:
            c = W(q); q += 2
            if c == 0xffff: end = True; break
            if c == 0xfffe: end = False; break
            cur.append(c)
        recs.append((attr, dst, cur))
        if end: break
    res.append((i, p, recs))
def big(c):
    """e000-font glyph code -> char (A=0xb4 step 4, digits from 0x8c)"""
    if c == 0: return " "
    if 0xb4 <= c <= 0xb4 + 4*25 and (c-0xb4) % 4 == 0: return chr(65 + (c-0xb4)//4)
    if 0x8c <= c <= 0x8c + 4*9 and (c-0x8c) % 4 == 0: return chr(48 + (c-0x8c)//4)
    return "<%x>" % c
if __name__ == "__main__":
    print(N, "strings")
    for i, p, recs in res:
        print(i, hex(p))
        for attr, dst, cs in recs: print("   ", hex(attr), hex(dst), " ".join("%x" % c for c in cs), "|", "".join(big(c) for c in cs))
