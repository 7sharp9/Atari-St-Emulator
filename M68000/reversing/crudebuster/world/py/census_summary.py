"""census_summary.py <census_lN.txt ...>: activation counts per (pool, type, variant) of a census log; marks script-listed B types."""
import sys, re
from collections import Counter, defaultdict
sys.path.insert(0, __import__("os").path.dirname(__file__))
from cbrom import *
scriptB = defaultdict(Counter)
for lv in range(6):
    p = L(0x6d000 + 4*lv)
    while W(p) != 0xffff: scriptB[lv][B(p+2) & 0x7f] += 1; p += 8
for fn in sys.argv[1:]:
    lv = int(re.search(r"_l(\d)", fn).group(1))
    cnt = Counter(); maxf = 0; lvls = Counter()
    for l in open(fn):
        if l.startswith("S "):
            t = l.split(" ")
            pool, slot, h = t[2], int(t[3]), t[4].strip()
            ty = int(h[4:6], 16); var = int(h[32:34], 16) if len(h) > 33 else 0
            cnt[(pool, ty, var if pool != "C" else 0)] += 1
            maxf = max(maxf, int(t[1]))
        elif l.startswith("V "):
            m = re.search(r"lvl=(\d)", l); lvls[int(m.group(1))] += 1
    print("== census level", lv, "frames", maxf, "levels seen (30-frame samples):", dict(lvls))
    for pool in "ABC":
        row = sorted((k[1], k[2], v) for k, v in cnt.items() if k[0] == pool)
        print(" ", pool, " ".join("%d.%d x%d%s" % (t, vr, n, "*" if pool == "B" and t in scriptB[lv] else "") for t, vr, n in row))
