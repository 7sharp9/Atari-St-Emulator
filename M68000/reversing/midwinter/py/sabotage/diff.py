"""diff.py a.snap b.snap [lo hi]: differing byte runs in the program's data range (default $22000..$2dd2e)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state import ram_from_snap
a, b = ram_from_snap(sys.argv[1]), ram_from_snap(sys.argv[2])
lo, hi = (int(sys.argv[3], 16), int(sys.argv[4], 16)) if len(sys.argv) > 4 else (0x22000, 0x2dd2e)
i = lo; runs = []
while i < hi:
    if a[i] != b[i]:
        j = i
        while j < hi and (a[j] != b[j] or (j + 1 < hi and a[j+1] != b[j+1])): j += 1
        runs.append((i, j)); i = j
    i += 1
for i, j in runs:
    print('%06x..%06x  %s -> %s' % (i, j, a[i:j].hex()[:48], b[i:j].hex()[:48]))
print(len(runs), 'runs')
