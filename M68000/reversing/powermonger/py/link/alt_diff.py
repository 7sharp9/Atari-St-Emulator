"""alt_diff.py <a.snap> <b.snap>...: altitude plane ($3f86c, 64 x 128 cells) differences of each later snapshot against the first."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve()
while not (ROOT / 'tools' / 'rdis.py').exists(): ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / 'tools'))
from pm_export import ram_from_snap
A = 0x3f86c
r0 = ram_from_snap(Path(sys.argv[1]))
for s in sys.argv[2:]:
    r = ram_from_snap(Path(s))
    d = [(i % 64, i // 64, r0[A + i], r[A + i]) for i in range(8192) if r0[A + i] != r[A + i]]
    print(s, 'altitude cells differing', len(d), 'values', sorted({(a, b) for _, _, a, b in d})[:6], 'first', d[:3])
