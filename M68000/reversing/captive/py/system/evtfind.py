"""Indexes of records whose pc is in [lo,hi): first N, with counts."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evt import read
ev = read(sys.argv[1]); lo = int(sys.argv[2], 16); hi = int(sys.argv[3], 16); n = int(sys.argv[4]) if len(sys.argv) > 4 else 20
idx = [i for i, r in enumerate(ev) if lo <= (r[1] & 0xffffff) < hi]
print('count', len(idx), 'first', idx[:n], 'last', idx[-3:] if idx else None)
