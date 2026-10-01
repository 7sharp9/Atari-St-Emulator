"""tree_census.py - what `$4d252` holds: trees, not animals (economy.md section 2).

    cd M68000 && python reversing/powermonger/py/tree_census.py <snap>...            # array vs render records
    python reversing/powermonger/py/tree_census.py --chain [glob]                      # who runs the gather modes

First form: for each snapshot, every live `$4d252` entry (slot 0 reserved, stride 12, `cell` word at +10 nonzero) is matched
against the cells of the `$47970` bucket-walk records of byte6 4 (the building/tree frame category) and byte6 8 (animals). Cell
packing is {y:7, x:6} = `y << 6 | x`. 134th: 203 of 203 on `pm123/win/m1_s0`, 154 of 154 on `pm129/env5_12M`, every one on a byte6 4
record, none on byte6 8, and the count of byte6 4 records equals the array's.

--chain: the job (`7(obj) & $f`, 9 with bit 4 set) of every live man in the gather-chain modes `$3e/$40/$42/$44/$46/$6a` over every
`scratchpad/pm*/**/*.snap` (or the given glob): all four civilian jobs run it, so it is not a shepherd FSM.
"""
import collections
import glob
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from disassemble import ram_from_snap  # noqa: E402
from census import walk  # noqa: E402


def array_vs_records(snap):
    r = ram_from_snap(snap)
    w = lambda a: int.from_bytes(r[a:a + 2], 'big')
    n = w(0x4e512)
    live = [(o, w(o + 10), r[o + 6], r[o + 7]) for o in range(0x4d252 + 12, 0x4d252 + n, 12) if w(o + 10)]
    cells = collections.defaultdict(set)
    nrec = collections.Counter()
    for _o, x, y, rec in walk(r)[0]:
        cells[rec[6]].add((y << 6) | x)
        nrec[rec[6]] += 1
    on4 = sum(1 for _o, c, _k, _s in live if c in cells[4])
    on8 = sum(1 for _o, c, _k, _s in live if c in cells[8])
    print('%s: %d live entries, categories %s, tree_state %s; on a byte6 4 record %d, on byte6 8 %d; byte6 4 records %d (%d cells), byte6 8 records %d'
          % (os.path.relpath(snap, ROOT), len(live), sorted({k for _o, _c, k, _s in live}),
             sorted({s & 0x7f for _o, _c, _k, s in live}), on4, on8, nrec[4], len(cells[4]), nrec[8]))


def chain(pattern):
    want = (0x3e, 0x40, 0x42, 0x44, 0x46, 0x6a)
    jobs = collections.defaultdict(collections.Counter)
    names = {0: 'soldier', 1: 'farmer', 2: 'merchant', 4: 'fisher', 8: 'shepherd', 9: 'leader'}
    for p in sorted(glob.glob(pattern, recursive=True)):
        try:
            r = ram_from_snap(p)
        except Exception:
            continue
        if len(r) < 0x59000:
            continue
        for i in range(512):
            a = 0x51b66 + 50 * i
            if r[a + 5] == 0 or r[a + 5] > 127 or r[a + 6] != 0 or r[a + 31] not in want:
                continue
            jobs[r[a + 31]][names.get(9 if r[a + 7] & 0x10 else r[a + 7] & 0xf)] += 1
    for m in sorted(jobs):
        print('$%02x' % m, dict(jobs[m]))


if __name__ == '__main__':
    if sys.argv[1:2] == ['--chain']:
        chain(sys.argv[2] if len(sys.argv) > 2 else str(ROOT / 'scratchpad/pm*/**/*.snap'))
    else:
        for s in sys.argv[1:]:
            array_vs_records(s)
