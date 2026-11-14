"""causelib.py - causeway planner support: map access, walkability, snapshot loading.
Reuses reversing/populous/py (popmem, popgen, popdrive); locates the repo root via tools/rdis.py."""
import os, sys, struct
def _root():
    d = os.path.dirname(os.path.abspath(__file__))
    while d != os.path.dirname(d):
        if os.path.exists(os.path.join(d, 'tools', 'rdis.py')) or os.path.exists(os.path.join(d, 'M68000', 'tools', 'rdis.py')):
            return d if os.path.exists(os.path.join(d, 'tools', 'rdis.py')) else os.path.join(d, 'M68000')
        d = os.path.dirname(d)
    raise SystemExit('repo root not found')
R = _root()
PY = os.path.join(R, 'reversing', 'populous', 'py')
sys.path.insert(0, PY); sys.setrecursionlimit(100000)
from popmem import ram, w, sw, l
from popgen import Gen
N = 65
HEIGHTS, SHAPE, ENT = 0x34be4, 0x36e78, 0x3b278
from popcfg import WORK
DATA = os.path.join(WORK, 'causeway')   # gate output: snaps/<tag>/, gate_<tag>.json, table.json, PNGs
os.makedirs(DATA, exist_ok=True)

def heights(m): return [sw(m, HEIGHTS + 2*i) for i in range(N*N)]
def shapes(m): return list(m[SHAPE:SHAPE+4096])
def entities(m):
    out = []
    for i in range(0xd0):
        a = ENT + 0x16*i
        st = sw(m, a+4)
        if st > 0:
            out.append(dict(i=i, flags=m[a], side=m[a+1], str=st, cell=w(m, a+8)))
    return out

def corners_of(cx, cy):
    return ((cx, cy), (cx+1, cy), (cx+1, cy+1), (cx, cy+1))

def cell_walkable(h, cx, cy, shape=None):
    """A cell is land (walkable per $18198: shape != 0) iff any of its four corners is above 0
    ($c0ee: s=(a+b+c+d)>>2, bits = corners > s; sea only if bits==0 and s==0).  Rock $2f and swamp $35
    (from the real shape map when given) are not walkable."""
    if not (0 <= cx < 64 and 0 <= cy < 64): return False
    if shape is not None and shape[cy*64+cx] in (0x2f, 0x35): return False
    return any(h[y*N+x] > 0 for x, y in corners_of(cx, cy))

def components(h, shape):
    seen = {}; comps = []
    for y in range(64):
        for x in range(64):
            if (x, y) in seen or not cell_walkable(h, x, y, shape): continue
            comp = []; st = [(x, y)]; seen[(x, y)] = len(comps)
            while st:
                a, b = st.pop(); comp.append((a, b))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        q = (a+dx, b+dy)
                        if q not in seen and cell_walkable(h, q[0], q[1], shape):
                            seen[q] = len(comps); st.append(q)
            comps.append(comp)
    return comps, seen
