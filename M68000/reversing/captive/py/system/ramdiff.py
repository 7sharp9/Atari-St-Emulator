"""Changed-byte ranges between two snapshots' RAM (merged with a gap), optionally excluding ranges."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import util  # noqa: F401  (puts tools/ on sys.path)
from gfxview import load_ram
a, ba = load_ram(sys.argv[1]); b, bb = load_ram(sys.argv[2])
excl = [tuple(int(x, 16) for x in r.split('-')) for r in sys.argv[3:]]
runs = []; s = None; last = -10
for i in range(min(len(a), len(b))):
    if a[i] != b[i] and not any(lo <= i < hi for lo, hi in excl):
        if s is None or i - last > 8:
            if s is not None: runs.append((s, last))
            s = i
        last = i
if s is not None: runs.append((s, last))
for lo, hi in runs:
    print(f'${lo:06x}-${hi:06x} ({hi-lo+1} bytes) old={a[lo:min(hi+1,lo+16)].hex()} new={b[lo:min(hi+1,lo+16)].hex()}')
