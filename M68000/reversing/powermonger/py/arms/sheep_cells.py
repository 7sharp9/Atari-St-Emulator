"""sheep_cells.py <snap>...: for every cell holding a sheep, the other records of the `$47970` bucket (kind, owner), the order
`$4a7a` would take (its classification by `$4aa0..$4b60`), and the distance to the local side's group-0 lead.  (PowerMonger 148th, agent A)"""
import os, sys
from pathlib import Path
def _root():
    if os.environ.get('M68000_ROOT'): return Path(os.environ['M68000_ROOT'])
    for p in Path(__file__).resolve().parents:
        if (p / 'tools' / 'pm_fsm_ref.py').exists(): return p
ROOT = _root()
sys.path.insert(0, str(ROOT / 'tools'))
import pm_fsm_ref as P
from pm_common import OBJ
from disassemble import ram_from_snap
def cell_list(m, x, y):
    out = []
    off = P.s16(m.wu(0x47970 + ((y * 64 + x) * 2)))
    n = 0
    while off != 0 and n < 200:
        a = OBJ + off
        out.append((a, m.bu(a + 5), m.bu(a + 6), m.bu(a + 7)))
        off = P.s16(m.wu(a))
        n += 1
    return out
def classify(recs, own):
    """$4a7a: settlement (2/$10) of another owner -> 'settlement'; else man (0/$e, owner > 0, != own) -> 'man'; else $8/$14/$16 -> 'animal'; $4 -> 'tree'"""
    A2 = A4 = A5 = False
    for a, o, k, f in recs:
        if k in (2, 0x10):
            if P.s8(o) != own: return 'settlement'
            continue
        if k in (0, 0xe):
            if P.s8(o) > 0 and P.s8(o) != own: A2 = True
            continue
        if k in (8, 0x14, 0x16): A4 = True
        if k == 4: A5 = True
    return 'man' if A2 else 'animal' if A4 else 'tree' if A5 else 'none'
def run(snap):
    ram = ram_from_snap(snap); m = P.Mem(ram)
    local = m.wu(0x57ffe)
    base = 0x51538 + local * 0x13c
    lead = OBJ + P.s16(m.wu(base + 64))
    lx, ly, men = m.bu(lead + 8), m.bu(lead + 10), m.wu(base + 52)
    n = P.s16(m.wu(0x4cff6)) // 20
    cells = {}
    for i in range(n):
        a = 0x4ccd6 + i * 20
        if m.bu(a + 6) == 8:
            cells.setdefault((m.bu(a + 8), m.bu(a + 10)), []).append((m.bu(a + 7), P.s8(m.bu(a + 5))))
    res = []
    for (x, y), sh in cells.items():
        recs = cell_list(m, x, y)
        res.append((max(abs(x - lx), abs(y - ly)), (x, y), classify(recs, local), len(sh), sorted(set(s[0] for s in sh)), sorted(set(s[1] for s in sh)), [(hex(r[2]), r[1]) for r in recs if r[2] != 8]))
    return local, (lx, ly), men, sorted(res)
if __name__ == '__main__':
    for s in sys.argv[1:]:
        local, lead, men, res = run(s)
        print(s, 'local', local, 'lead', lead, 'men', men)
        for r in res[:6]: print('   ', r)
