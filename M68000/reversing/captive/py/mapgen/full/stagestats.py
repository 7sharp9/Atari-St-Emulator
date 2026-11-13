"""Per-stage counters over chained bases: stagestats.py <d2> <lo> <hi>.
13268 $25414 switch doors, 13270 $25722 locks, 13750 $25c1e class-$80 carriers, 13614 $26478 items placed,
13608 $2676c vault distance, 13626 lock-list bytes; also object counts by item type from the object list 13724."""
import os, sys
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chain_run as CR
d2, lo, hi = (int(a) for a in sys.argv[1:4])
tot = Counter(); nz = Counter(); items = Counter(); mx = Counter()
for d0 in range(lo, hi):
    m, full, _ = CR.generate(d0, d2)
    for o in (13268, 13270, 13750, 13614, 13608):
        v = (m[o] << 8) | m[o + 1]
        tot[o] += v; nz[o] += v > 0; mx[o] = max(mx[o], v)
    q = int.from_bytes(m[13724:13728], 'big') - CR.FED + 4
    while True:
        ln = (full[q + 2] << 8) | full[q + 3]
        if ln & 0x8000:
            break
        for j in range(4, ln, 4):
            items[full[q + j]] += 1
        q += ln
print({o: (tot[o], nz[o], mx[o]) for o in tot}, '(sum, bases > 0, max)')
print('objects by item type:', {hex(k): v for k, v in sorted(items.items())})
