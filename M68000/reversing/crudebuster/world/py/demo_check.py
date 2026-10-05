"""demo_check.py <framelog.csv> : check the decoded demo streams against the attract-run log.
Columns (framelog CB_ADDRS order): 0 f, 1 80018 (demo index), 2 80014, 3 80051 (P1 held), 4 80053 (P2 held), 5 80050, 6 80052, 7 8002a, 8 8002c,
9 8001a, 10 80022, 11 8004a, 12 80046 (level), 13 80042, 14 80044, 15-18 positions, 19 80040.
Model of $10b2 (demo replay): per frame: D0 = byte at ptr; cnt -= 1; if cnt == 0: ptr += 2, D0 = byte at ptr, cnt = count at ptr; held := D0.
The log value of $8002a at the frame before the first replay frame gives the first count (set by $8ce: count of the first pair)."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from cbrom import *
rows = [l.strip().split(",") for l in open(sys.argv[1])]
H = lambda s: int(s, 16)
# demo segments: frames where 80014 bit 3 set and 80040 bit 7 clear
segs = []; cur = None
for r in rows:
    on = (H(r[2]) & 8) != 0 and (H(r[19]) & 0x80) == 0
    if on and cur is None: cur = [int(r[0]), int(r[0]), H(r[1]), H(r[12])]
    elif on: cur[1] = int(r[0])
    elif cur is not None: segs.append(cur); cur = None
if cur: segs.append(cur)
print("demo segments (first frame, last frame, 80018, level 80046):", segs)
byf = {int(r[0]): r for r in rows}
tot_ok = tot = 0
for (f0, f1, idx, lvl) in segs:
    f0 += 1   # the first replay frame is the one after the demo flag appears (observed: $8002a first decrements at f0+1)
    res = []
    for who, base, col in (("P1", 0x5c000 + 0x400*idx, 3), ("P2", 0x5d000 + 0x400*idx, 4)):
        ptr = base; cnt = B(ptr+1)   # $8ce loads the first count
        exp = []
        for f in range(f0, f1 + 1):
            d0 = B(ptr); cnt -= 1
            if cnt == 0:
                ptr += 2; d0 = B(ptr); cnt = B(ptr+1)
            exp.append(d0)
        obs = [H(byf[f][col]) for f in range(f0, f1 + 1)]
        ok = sum(1 for a, b in zip(exp, obs) if a == b)
        res.append((who, ok, len(obs), ptr - base))
        tot_ok += ok; tot += len(obs)
    print("demo %d level %d frames %d..%d: " % (idx, lvl, f0, f1), " ".join("%s %d/%d (stream ptr end +%d)" % x for x in res))
print("TOTAL %d/%d frames equal" % (tot_ok, tot))
