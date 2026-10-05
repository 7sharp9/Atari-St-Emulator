"""react2.py <dump>: per DAMND hit (health drop), the reaction it caused: hit type (+63 at the drop), frames spent in (+2,+3) = (2,4) until it left or the next drop, the (+4,+5) path, the animation lists (+32) and where it went."""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dd import *
D = Dump(sys.argv[1]); fr = D.frames()
drops = [i for i in range(1, D.n) if D.u8(i, BOSS) and D.u8(i - 1, BOSS) and D.s16(i, BOSS + 24) < D.s16(i - 1, BOSS + 24) and D.u8(i, BOSS + 2) == 2]
agg = collections.defaultdict(list)
for k, i in enumerate(drops):
    end = drops[k + 1] if k + 1 < len(drops) else D.n
    j = i + 1
    while j < end and not (D.u8(j, BOSS + 2) == 2 and D.u8(j, BOSS + 3) == 4) and j < i + 4: j += 1
    t = D.u8(i, BOSS + 63)
    if not (D.u8(j, BOSS + 2) == 2 and D.u8(j, BOSS + 3) == 4): agg[t].append(('noreact', int(fr[i]))); continue
    n = 0; path = []; anims = []
    while j < end and D.u8(j, BOSS + 2) == 2 and D.u8(j, BOSS + 3) == 4:
        s = (D.u8(j, BOSS + 4), D.u8(j, BOSS + 5))
        if not path or path[-1] != s: path.append(s)
        a = D.u32(j, BOSS + 32) & 0xffffff
        if a not in anims: anims.append(a)
        n += 1; j += 1
    nxt = (D.u8(j, BOSS + 2), D.u8(j, BOSS + 3), D.u8(j, BOSS + 4)) if j < D.n else None
    agg[t].append((int(fr[i]), n, path, anims, nxt, j >= end))
for t, rs in sorted(agg.items()):
    print('hit type +63=%d: %d hits' % (t, len(rs)))
    for r in rs[:6]: print('   ', r[0], *(r[1:2] if r[0] != 'noreact' else []), ' '.join('%02x%02x' % s for s in r[2]) if r[0] != 'noreact' else 'no reaction (hit in another state)', ('anims ' + ' '.join('%x' % a for a in r[3][:6]) + ' next %s%s' % (r[4], ' (cut by next hit)' if r[5] else '')) if r[0] != 'noreact' else '')
