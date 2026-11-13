"""Shared setup for the panel2 scripts: repo root, stserver, base13 lock list, tile reader."""
import os, sys
_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, 'tools', 'rdis.py')):
    if os.path.dirname(_d) == _d:
        sys.exit('repo root (tools/rdis.py) not found')
    _d = os.path.dirname(_d)
sys.path.insert(0, os.path.join(_d, 'reversing', 'captive', 'py', 'ai'))
from cap import R, StServer, A6, W  # noqa: E402

OUT = os.path.join(W, 'phoopel', 'panel2')
os.makedirs(OUT, exist_ok=True)
SNAP = os.path.join(W, 'phoopel', 'base13.snap')
LOCKS, TILES = A6 + 8628, A6 + 9242
VEC = ((0, -1), (-1, 0), (0, 1), (1, 0))   # facing 0 N, 1 W, 2 S, 3 E

def lock_list(s, n=None):
    n = n or 24
    out = []
    for i in range(n):
        r = s.read(LOCKS + 10 * i, 10)
        out.append(dict(i=i, W=(r[0], r[1]), code=int.from_bytes(r[2:4], 'big'), D=(r[6], r[7]), b8=r[8], b9=r[9],
                        key=r[8] & 3, door=(r[8] >> 2) & 3))
    return out
