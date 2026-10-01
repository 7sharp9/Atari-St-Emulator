"""job_census.py - which job (jobnames at $a200: 0 soldier, 1 farmer, 2 merchant, 4 fisher, 8 shepherd, 9 leader)
is in each entity mode, over the given snapshots (live persons only: side byte 5 nonzero, category byte6 0).

    cd M68000 && python reversing/powermonger/py/job_census.py <snap>...

The job is `7(obj) & $f`, or 9 when bit 4 of byte 7 is set (the panel routine at $9d6e). Defaults to the seven
states of the 133rd pass. Result there: modes $56..$62 are all fishers (93 of 93), $4e..$54 all merchants (115),
$80..$88 shepherds, $0e mostly farmers (202 of 208), $8a leaders; $10/$12 are shared by every job.
"""
import collections
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from disassemble import ram_from_snap  # noqa: E402

DEFAULT = ['pm123/win/m1_s0', 'pm129/env5_12M', 'pm74_late', 'pm121/k5', 'pm121/k25', 'pm121/k0', 'pm121/k10']
paths = sys.argv[1:] or [os.path.join(ROOT, 'scratchpad', p + '.snap') for p in DEFAULT]
NAMES = {0: 'soldier', 1: 'farmer', 2: 'merchant', 4: 'fisher', 8: 'shepherd', 9: 'leader'}
tot = collections.defaultdict(collections.Counter)
used = []
for p in paths:
    if not os.path.exists(p):
        continue
    used.append(p)
    r = ram_from_snap(p)
    for i in range(512):
        a = 0x51b66 + 50 * i
        if r[a + 5] == 0 or r[a + 5] > 127 or r[a + 6] != 0:
            continue
        b7 = r[a + 7]
        tot[r[a + 31]][9 if b7 & 0x10 else b7 & 0xf] += 1
print(len(used), 'snapshots')
for mode in sorted(tot):
    print('$%02x' % mode, {NAMES.get(j, j): n for j, n in tot[mode].items()})
