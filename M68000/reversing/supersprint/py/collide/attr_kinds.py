"""attr_kinds.py - which (kind, payload) surface-map values each track's map holds at race start (from the per-track snapshots)."""
import sys, os, collections
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'reversing', 'supersprint', 'py', 'physics'))
import pl
from pl import Ram, sscfg
for t in range(8):
    r = Ram(os.path.join(sscfg.WORK, 'agents', 'tracks', 'snaps', 'race_%d.snap' % t))
    mb = r.gl(-1910); c = collections.Counter(r.u8(mb + k) & 0x7f for k in range(1000))
    c.pop(0, None)
    kinds = collections.defaultdict(list)
    for v in sorted(c): kinds[v & 3].append('%02x(n%d)' % (v >> 2, c[v]))
    print('T%d gates=%d' % (t + 1, r.g(-1808)), {k: ' '.join(v) for k, v in sorted(kinds.items())})
