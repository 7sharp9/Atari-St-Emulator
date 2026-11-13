"""Can a base with a sealed key be finished without the region its door cuts off?

A base is finished by using EXPLOSIVES (item $1b) on a generator, tile $28/$29 (federation $deb4 -> 13410(A6) = 1,
then $be94; mapgen.md "Sealed keys"). For every base of missions lo+1..hi that has a key on its own door, this lists
the generator cells (tile $28/$29 in the model's tile layer, bit 7 ignored) and whether each can be stood beside
(an open 4-neighbour reachable from the entrance) with every sealed door of the base closed. Passability is
lockcensus.Grid's. Model output on the chained generator (gated 400/400).
Usage: finish.py <first mission index> <last mission index exclusive>"""
import sys
import os as _os
_M = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '../../../..'))  # M68000/
sys.path.insert(0, _M + '/reversing/captive/py/mapgen/full')
import lockcensus as LC
import chain_run as CR

lo, hi = int(sys.argv[1]), int(sys.argv[2])
nb = lambda c: [(c[0] + dx, c[1] + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
bases = blocked = nogen = 0
print('mission target D0 D2 | sealed doors | generators (x,y):beside-reachable with the sealed doors closed | finishable')
for mi in range(lo, hi):
    for t in range(11):
        d0, d2 = 11 * mi + t, (1 if t == 10 else 0)
        locks, m, _, full = LC.record_locks(d0, d2)
        sealed = {L['D'] for L in locks if L['K'] is not None and L['K'] == L['D']}
        if not sealed:
            continue
        p = int.from_bytes(m[13684:13688], 'big') - CR.FED
        tiles = full[p:p + 2048]
        gens = [(i % 64, i // 64) for i in range(2048) if tiles[i] & 0x7e == 0x28]
        g = LC.Grid(m)
        ex = LC.w(m, 32)
        reach = g.reach((ex % 64, ex // 64), sealed)
        ok = [any(n in reach for n in nb(c)) for c in gens]
        bases += 1
        nogen += not gens
        blocked += bool(gens) and not any(ok)
        print(f'{mi + 1:3d} {t + 1:2d} {d0:5d} {d2} | {sorted(sealed)} | '
              f'{" ".join(f"{c}:{o}" for c, o in zip(gens, ok)) or "none"} | {any(ok)}')
print(f'bases with a sealed key: {bases}; with no generator tile: {nogen}; with every generator behind a sealed door: {blocked}')
