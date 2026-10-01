"""mode_census.py <snap>...: live persons (side byte5 in 1..127, category byte6 == 0) in modes $12/$34/$36 (+$10 for context):
count, previous-mode byte 30 histogram, category/job (byte7&$1f) and carried item 33, and for $34 the dwell bytes 18/19 and 48 link."""
import sys
from pathlib import Path
from collections import Counter
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from pm_export import ram_from_snap
WATCH = (0x10, 0x12, 0x34, 0x36)
for s in sys.argv[1:]:
    r = ram_from_snap(ROOT / s)
    live = [0x51b66 + 50 * i for i in range(512)]
    live = [a for a in live if 1 <= r[a + 5] <= 127 and r[a + 6] == 0]
    modes = Counter(r[a + 31] for a in live)
    print('%s: %d live persons; top modes %s' % (s, len(live), [('%02x' % m, n) for m, n in modes.most_common(8)]))
    for m in WATCH:
        sel = [a for a in live if r[a + 31] == m]
        if not sel: print('  mode $%02x: 0' % m); continue
        prev = Counter(r[a + 30] for a in sel)
        job = Counter(r[a + 7] & 0x1f for a in sel)
        extra = ''
        if m == 0x34:
            extra = ' dwell hi/lo %s tgt48 alive %d' % (Counter((r[a + 18], r[a + 19]) for a in sel).most_common(4),
                    sum(1 for a in sel if 0 < r[0x51b66 + int.from_bytes(r[a + 48:a + 50], 'big') + 5] < 128))
        if m == 0x36:
            extra = ' tgt48 alive %d dwell %s' % (sum(1 for a in sel if 0 < r[0x51b66 + int.from_bytes(r[a + 48:a + 50], 'big') + 5] < 128),
                    Counter(int.from_bytes(r[a + 18:a + 20], 'big', signed=True) for a in sel).most_common(3))
        if m == 0x12:
            extra = ' dwell(18) %s' % Counter(int.from_bytes(r[a + 18:a + 20], 'big', signed=True) for a in sel).most_common(5)
        print('  mode $%02x: %d  prev %s  job %s%s' % (m, len(sel), [('%02x' % p, n) for p, n in prev.most_common(5)],
              job.most_common(4), extra))
