"""hist.py <dump> [lo hi]: DAMND (pool 4 record $ff9a68) state histogram of a dm.lua dump: per (+2,+3,+4,+5) the number of visits, the frames spent (min/mean/max per visit),
the animation list pointers seen (+32 long) and the attack box ids (+45 low 7 bits); then the transition list."""
import sys, collections, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dd import *
D = Dump(sys.argv[1])
lo = int(sys.argv[2]) if len(sys.argv) > 2 else 0
hi = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
fr = D.frames()
vis = collections.OrderedDict()
cur = None; start = None
seq = []
for i in range(D.n):
    f = int(fr[i])
    if f < lo or f > hi: continue
    if not D.u8(i, BOSS): continue
    key = (D.u8(i, BOSS + 2), D.u8(i, BOSS + 3), D.u8(i, BOSS + 4), D.u8(i, BOSS + 5))
    an = D.u32(i, BOSS + 32) & 0xffffff; atk = D.u8(i, BOSS + 45) & 0x7f
    if key != cur:
        if cur is not None: vis.setdefault(cur, []).append((f - start, anims, atks))
        cur = key; start = f; anims = set(); atks = set()
        seq.append((f, key))
    anims.add(an); atks.add(atk)
if cur is not None: vis.setdefault(cur, []).append((f - start + 1, anims, atks))
print('%-12s %5s %7s %5s %5s %5s  anims / attack boxes' % ('(+2,+3,+4,+5)', 'visit', 'frames', 'min', 'mean', 'max'))
for k, v in sorted(vis.items()):
    d = [x[0] for x in v]; an = set().union(*[x[1] for x in v]); at = set().union(*[x[2] for x in v])
    print('%02x %02x %02x %02x    %5d %7d %5d %5.1f %5d  %s / %s' % (*k, len(v), sum(d), min(d), sum(d) / len(d), max(d), ' '.join('%x' % a for a in sorted(an)), ' '.join('%02x' % a for a in sorted(at))))
if '--seq' in sys.argv:
    for f, k in seq: print(f, '%02x%02x%02x%02x' % k)
