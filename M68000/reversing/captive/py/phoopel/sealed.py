"""What a sealed key's door cuts off: for every lock whose key K lies on its own door D (missions lo..hi-1, the same
bases as keyondoor.py), the open cells reachable from the entrance only through D, and which other locks' prizes,
doors and wall items fall inside that region. Passability is lockcensus.Grid's (open cells by $24efc's rule plus
every arrow edge, so lifts and shafts count). Model output on the chained generator (gated 400/400); not run in play.
Usage: sealed.py <first mission index> <last mission index exclusive>"""
import sys
import os as _os
_M = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '../../../..'))  # M68000/
sys.path.insert(0, _M + '/reversing/captive/py/mapgen/full')
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import lockcensus as LC
from shown import shown

lo, hi = int(sys.argv[1]), int(sys.argv[2])
sizes = []
print('mission target D0 D2 lock door(x,y) doorkind keykind shown | open cells | cut off | other locks inside (prize/door/wall)')
for mi in range(lo, hi):
    for t in range(11):
        d0, d2 = 11 * mi + t, (1 if t == 10 else 0)
        locks, m, _, _ = LC.record_locks(d0, d2)
        sealed = [(i, L) for i, L in enumerate(locks) if L['K'] is not None and L['K'] == L['D']]
        if not sealed:
            continue
        g = LC.Grid(m)
        ex = LC.w(m, 32)
        ent = (ex % 64, ex // 64)
        every = g.reach(ent, set())
        for i, L in sealed:
            cut = every - g.reach(ent, {L['D']}) - {L['D']}
            inside = [(j, sum(L2[k] in cut for k in ('E', 'D', 'W'))) for j, L2 in enumerate(locks) if j != i]
            inside = [f'{j}:{"".join(k[0] for k in ("E", "D", "W") if locks[j][k] in cut)}' for j, n in inside if n]
            sizes.append(len(cut))
            print(f'{mi + 1:3d} {t + 1:2d} {d0:5d} {d2} {i:2d} {L["D"]} {L["door"]} {L["key"]} {shown(L["code"], d0):05d}'
                  f' | {len(every):4d} | {len(cut):4d} | {" ".join(inside) or "-"}')
sizes.sort()
print(f'sealed keys: {len(sizes)}; cells cut off: min {sizes[0]}, median {sizes[len(sizes) // 2]}, max {sizes[-1]}')
