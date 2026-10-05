"""demostreams.py: decode the three demo input streams ($5c000/$5d000 + 0x400*n, pairs (input byte, count)); print the runs."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from cbrom import *
NAMES = {0: "up", 1: "down", 2: "left", 3: "right", 4: "b1", 5: "b2", 6: "b3", 7: "start"}
def desc(b): return "+".join(NAMES[i] for i in range(8) if b & (1 << i)) or "-"
def runs(base, limit=0x400):
    out = []; p = base
    while p < base + limit:
        b, c = B(p), B(p+1)
        out.append((p, b, c)); p += 2
        if b == 0 and c == 0 and p - base > 2: break
    return out
def pointers():
    return [(L(0x5e000 + 4*i), L(0x5f000 + 4*i)) for i in range(3)]
if __name__ == "__main__":
    for n in range(3):
        for who, base in (("P1", 0x5c000 + 0x400*n), ("P2", 0x5d000 + 0x400*n)):
            r = runs(base)
            # trailing fill: find the last non-zero pair
            while r and r[-1][1] == 0 and r[-1][2] == 0: r.pop()
            tot = sum(c for _, _, c in r)
            print("demo %d %s base $%x pairs %d sum counts %d" % (n, who, base, len(r), tot))
            print("   ", " ".join("%02x*%d" % (b, c) for _, b, c in r[:40]), "..." if len(r) > 40 else "")
    print("pointer tables $5e000/$5f000:", [(hex(a), hex(b)) for a, b in pointers()])
    print("level words of the demo records $87a/$896/$8b2:", [W(L(0x86e + 4*i)) for i in range(3)])
