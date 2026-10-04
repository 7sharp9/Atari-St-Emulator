"""census_groups.py <snaplist-file | snap>...  (PowerMonger 148th, agent A)

Per snapshot, every group of every AI side (command slot state byte 4 == 4): side, group word offset D7, state 76, men 52,
food 112, pending 4, the side's eat period ($580a6 + side*$20, word 0), the own-side lords' home troops (word 8), the
enemy lords' home troops, and for a group with men > 4 the target the model's `$68fe` picks, the `$68ee` score and the
food margin (score - food).  Also the per-tick food drain and the number of ticks until food < score.

Repo root from __file__.  Output: one line per group, then totals.
    cd M68000 && .venv/bin/python reversing/powermonger/py/arms/census_groups.py scratchpad/pm144/allsnaps.txt
"""
import collections
import os
import sys
from pathlib import Path

def _root():
    if os.environ.get('M68000_ROOT'):
        return Path(os.environ['M68000_ROOT'])
    for p in Path(__file__).resolve().parents:
        if (p / 'tools' / 'pm_fsm_ref.py').exists():
            return p
    raise SystemExit('M68000 root not found')


ROOT = _root()
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'reversing/powermonger/py/cmdai'))
import pm_fsm_ref as P  # noqa: E402
import cmdai_ref as C  # noqa: E402
from disassemble import ram_from_snap  # noqa: E402


def lords(m):
    out = []
    a = C.LORDS
    while a != C.LORDS_END:
        if m.bu(a) != 0:
            out.append((a, m.bu(a), C.s16(m.wu(a + 8)), m.wu(a + 4), C.s16(m.wu(a + 6))))
        a += 32
    return out


def groups(snap):
    ram = ram_from_snap(snap)
    if len(ram) < 0x59000:
        return
    m = P.Mem(ram)
    A0 = C.CMD
    while A0 != C.CMD_END:
        if m.bu(A0 + 4) == 4:
            side = m.bu(A0)
            base = (C.GROUPS + C.sp16((side * 0x13c) & 0xffff)) & 0xfffff
            L = lords(m)
            for D7 in range(10, -1, -2):
                A1 = base + D7
                own = C.s16(m.wu(A1 + 28))
                if own <= 0:
                    continue
                A2 = (C.OBJ + C.sp16(m.wu(A1 + 64))) & 0xfffff
                lead_side = m.bu(A2 + 5)
                men = C.s16(m.wu(A1 + 52))
                food = C.s16(m.wu(A1 + 112))
                st = m.wu(A1 + 76)
                period = m.wu(C.ASSESS + lead_side * 0x20)
                eff = period * 2 if st == 6 else period
                drain = (men // 8 + 1)
                own_home = [h for (a, n, h, c, f) in L if n == lead_side]
                enemy_home = [h for (a, n, h, c, f) in L if n != lead_side]
                r = dict(snap=snap, slot_side=side, D7=D7, own28=own, lead_side=lead_side, state=st, men=men, food=food,
                         pending=m.wu(A1 + 4), period=period, drain=drain, own_home=own_home, enemy_home=enemy_home)
                score = None
                if men - 4 > 0:
                    m2 = P.Mem(ram)
                    m2.ww(A1 + 76, 6)
                    D3, A3, z = C.call_68fe(m2, A1, A2, men - 4)
                    if not z:
                        score = C.s16(C.call_68ee(men - 4, D3))
                        r['d'] = D3
                r['score'] = score
                yield r
        A0 += 6


def main():
    args = sys.argv[1:]
    snaps = []
    for a in args:
        if a.endswith('.snap'):
            snaps.append(a)
        else:
            snaps += [l.strip() for l in open(a) if l.strip()]
    tot = collections.Counter()
    rows = []
    for s in snaps:
        try:
            for r in groups(s):
                rows.append(r)
        except Exception as e:  # noqa
            print('ERR', s, type(e).__name__, e)
    for r in rows:
        print('%s slot_side %d D7 %2d own28 %d lead_side %d st %2d men %3d food %6d pend %d period %d drain/eat %d '
              'own_home %s enemy_home %s d %s score %s' % (
                  os.path.relpath(r['snap'], ROOT), r['slot_side'], r['D7'], r['own28'], r['lead_side'], r['state'], r['men'],
                  r['food'], r['pending'], r['period'], r['drain'], r['own_home'], r['enemy_home'], r.get('d'), r['score']))
    print('--- totals over %d snapshots, %d AI groups' % (len(snaps), len(rows)))
    print('by D7:', dict(collections.Counter(r['D7'] for r in rows)))
    print('by state:', dict(collections.Counter(r['state'] for r in rows)))
    print('periods:', dict(collections.Counter(r['period'] for r in rows)))
    print('food range:', min(r['food'] for r in rows), max(r['food'] for r in rows))
    print('men range:', min(r['men'] for r in rows), max(r['men'] for r in rows))
    sc = [r['score'] for r in rows if r['score'] is not None]
    print('score range:', (min(sc), max(sc)) if sc else None)


if __name__ == '__main__':
    main()
