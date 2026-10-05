"""Pool B ($81400, 32 x $40) episodes in a drive5.lua log made with CB_POOLB=1: type (+2), variant (+16), first/last frame, x, y, count per (type, variant).
usage: poolb.py <log> [first_frame] [last_frame]   (also prints the pool A deaths: first frame of state 2 per episode)"""
import sys, collections
sys.path.insert(0, __import__('os').path.dirname(__file__))
from loglib import load, u16
a = [x for x in sys.argv[1:] if x != '-v']
log = a[0]; f0 = int(a[1]) if len(a) > 1 else 0; f1 = int(a[2]) if len(a) > 2 else 10**9
live = {}; eps = []
last = -1
for line in open(log):
    p = line.split()
    if not p: continue
    if p[0] == 'B':
        f, slot, b = int(p[1]), int(p[2]), bytes.fromhex(p[3])
        if not (f0 <= f <= f1): continue
        e = live.get(slot)
        if e and e[1] == f - 1 and e[0][0] == b[2]:
            e[0][3] = f; live[slot] = (e[0], f)
        else:
            rec = [b[2], b[16], f, f, u16(b, 8), u16(b, 12), slot]; eps.append(rec); live[slot] = (rec, f)
c = collections.Counter((r[0], r[1]) for r in eps)
print("pool B (type, variant): episodes", {f"{k[0]:02x}/{k[1]:02x}": v for k, v in sorted(c.items())})
if "-v" in sys.argv:
    for r in eps: print(f"  type {r[0]:02x} var {r[1]:02x} frames {r[2]}..{r[3]} x {r[4]:04x} y {r[5]:04x} slot {r[6]}")
