import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from cbrom import *
tab = 0x1cce
for i in range(0x41):
    p = L(tab + 4*i)
    if p > 0x7ffff: print(i, "bad", hex(p)); continue
    out = []; q = p
    while True:
        attr = W(q); dst = L(q+2); q += 6; codes = []
        while True:
            c = B(q); q += 1
            if c & 0x80:
                c = (c << 8) | B(q); q += 1
                if c == 0xffff: codes.append("<END>"); break
                if c == 0xfffe: codes.append("<NEXT>"); break
                codes.append("<%04x>" % c)
            else: codes.append(c)
        out.append((attr, dst, codes))
        if codes[-1] == "<END>": break
    print(i, hex(p), [(hex(a), hex(d), " ".join(("%02x" % c) if isinstance(c, int) else c for c in cs)) for a, d, cs in out])
