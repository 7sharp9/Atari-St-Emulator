"""Group-list statistics per mission from the emulator's stage dumps (final state, after the last stage).

    uv run python -I reversing/captive/py/mapgen/full/groups.py

Missions 1, 5, 20: D0 = 11 * (mission - 1) + target, target 0..10 (mapgen.md "Call interface and seeds"), at D2 = 0
and D2 = 1. Mission 1 reads the shared dumps (scratchpad/captive/mapgen_stages/dumps), 5 and 20 scratchpad/captive/mapgen_full/pdumps/
(pdump.py). Group list at fed 4532(A6) = $1c782; record: x, y, size word, +4 carry byte, +5 flags, +6 timer,
+7 period, members of 8 bytes (+0 type, +1 slot, +2 hp word, +4 byte, +5 skill).
"""
import os
import sys
from collections import Counter
from statistics import mean, median

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pmodels  # noqa: E402,F401
import common  # noqa: E402

FED = common.FED
SHARED = common.DUMPS
MINE = os.path.join(common.R, 'scratchpad', 'captive', 'mapgen_full', 'pdumps')


def groups(f, start=0x1c782):
    p = start - FED
    out = []
    while True:
        ln = (f[p + 2] << 8) | f[p + 3]
        if ln & 0x8000:
            return out
        out.append(bytes(f[p:p + ln]))
        p += ln


def per_stage(recs):
    """Number of groups each stage added (stage callee -> count)."""
    c = Counter()
    prev = 0
    for (stop, callee), (_, m, f) in zip(common.STAGES, recs):
        n = len(groups(f))
        if n != prev:
            c[callee] += n - prev
        prev = n
    return c


def main():
    missions = {1: range(0, 11), 5: range(44, 55), 20: range(209, 220)}
    for d2 in (0, 1):
        for mi, d0s in missions.items():
            common.DUMPS = SHARED if mi == 1 else MINE
            ng, nm, per, hp, sk, b4, hos, rel, car, types, stg = [], [], [], [], [], [], 0, 0, 0, Counter(), Counter()
            for d0 in d0s:
                recs = common.load(d2, d0)
                f = recs[-1][2]
                gs = groups(f)
                stg += per_stage(recs)
                ng.append(len(gs))
                for g in gs:
                    nmem = (len(g) - 8) // 8
                    nm.append(nmem)
                    per.append(g[7])
                    hos += bool(g[5] & 0x10)
                    rel += bool(g[5] & 0x40)
                    car += bool(g[4] & 0x80)
                    types[g[8]] += 1
                    for j in range(nmem):
                        m = g[8 + 8 * j:16 + 8 * j]
                        hp.append((m[2] << 8) | m[3])
                        b4.append(m[4])
                        sk.append(m[5])
            G = sum(ng)
            print(f'D2={d2} mission {mi:2d} (D0 {d0s.start}..{d0s.stop - 1}): groups/base {min(ng)}..{max(ng)} mean {mean(ng):.1f}; '
                  f'members/group mean {mean(nm):.2f}; members total {sum(nm)}')
            print(f'    period +7 median {median(per)} mean {mean(per):.1f} range {min(per)}..{max(per)}; '
                  f'hp median {median(hp)} mean {mean(hp):.0f} range {min(hp)}..{max(hp)}; skill +5 median {median(sk)} mean {mean(sk):.1f}; '
                  f'+4 byte mean {mean(b4):.1f}')
            print(f'    hostile {hos}/{G} ({100 * hos / G:.0f}%), relentless {rel}/{G}, carrying {car}/{G}; '
                  f'types used {len(types)}: {sorted(types)}')
            print('    groups by stage: ' + ', '.join(f'${c:x} {n}' for c, n in sorted(stg.items(), key=lambda t: -t[1])))


if __name__ == '__main__':
    main()
