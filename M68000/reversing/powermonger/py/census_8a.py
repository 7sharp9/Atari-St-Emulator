"""census8a.py <snaplist>: live persons in mode $8a: job (byte7&$1f), side, whether the home settlement's lord record names them (settlement 34(A1) -> $4f916; 10(settl) = captain record?), prev mode."""
import sys
from pathlib import Path
from collections import Counter
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from pm_export import ram_from_snap
job = Counter(); prev = Counter(); n = 0; sn = 0; atcap = 0; f7 = Counter(); cap9 = Counter()
for s in [l.strip() for l in open(sys.argv[1]) if l.strip()]:
    try: r = ram_from_snap(ROOT / s)
    except Exception: continue
    seen = False
    for i in range(512):
        a = 0x51b66 + 50*i
        if not (1 <= r[a+5] <= 127 and r[a+6] == 0): continue
        if r[a+31] == 0x8a:
            seen = True; n += 1; job[r[a+7] & 0x1f] += 1; prev[r[a+30]] += 1; f7[r[a+7]] += 1
    sn += seen
    # all job-9 men: what modes
    for i in range(512):
        a = 0x51b66 + 50*i
        if 1 <= r[a+5] <= 127 and r[a+6] == 0 and (r[a+7] & 0x1f) == 9: cap9[r[a+31]] += 1
print('men in mode $8a:', n, 'in', sn, 'snapshots; job', job.most_common(), 'prev', prev.most_common(4), 'byte7', f7.most_common(4))
print('modes of ALL job-9 men:', cap9.most_common(8))
