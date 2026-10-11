"""felled_census.py - how many live `$4d252` trees are felled (state byte +7 == $0d exactly, the value `$156d0` writes
and the season wrap `$1ac92` tests) in each snapshot. Usage: (from M68000/) uv run python reversing/powermonger/py/season/felled_census.py <snap-glob>... ; prints per-land max and totals."""
import collections
import glob
import sys
from pathlib import Path

here = Path(__file__).resolve()
ROOT = next(p for p in here.parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'tools'))
from disassemble import ram_from_snap  # noqa: E402

snaps = sorted({s for g in sys.argv[1:] for s in glob.glob(g)})
per = collections.defaultdict(list)
n_with = 0
for s in snaps:
    r = ram_from_snap(s)
    w = lambda a: int.from_bytes(r[a:a + 2], 'big')
    n = w(0x4e512)
    st = [r[o + 7] for o in range(0x4d252 + 12, 0x4d252 + n, 12) if w(o + 10)]
    d = st.count(0x0d)
    n_with += d > 0
    land = Path(s).stem.rsplit('_c', 1)[0]
    per[land].append((d, len(st)))
for land, v in sorted(per.items()):
    print('%-16s snaps %3d  felled max %3d of %3d trees, last %3d' % (land, len(v), max(x[0] for x in v), v[-1][1], v[-1][0]))
print('snapshots %d, with a felled tree %d' % (len(snaps), n_with))
