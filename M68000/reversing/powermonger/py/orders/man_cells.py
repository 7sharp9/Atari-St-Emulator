"""man_cells.py <snap>...: cells whose chain $4a7a would classify 'man' (foreign man, no foreign settlement), with the chain's records and the distance to the local lead."""
import os, sys
from pathlib import Path
ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(ROOT / 'reversing/powermonger/py/arms'))
import pm_fsm_ref as P
from pm_common import OBJ
from disassemble import ram_from_snap
import sheep_cells as S
for snap in sys.argv[1:]:
    ram = ram_from_snap(snap); m = P.Mem(ram)
    local = m.wu(0x57ffe); base = 0x51538 + local * 0x13c
    lead = OBJ + P.s16(m.wu(base + 64)); lx, ly = m.bu(lead + 8), m.bu(lead + 10)
    seen = {}
    for s in range(1, 512):
        a = OBJ + 50 * s
        if m.bu(a + 6) in (0, 0xe) and P.s8(m.bu(a + 5)) > 0 and P.s8(m.bu(a + 5)) != local:
            x, y = m.bu(a + 8), m.bu(a + 10)
            seen.setdefault((x, y), None)
    out = []
    for (x, y) in seen:
        recs = S.cell_list(m, x, y)
        if S.classify(recs, local) == 'man':
            out.append((max(abs(x - lx), abs(y - ly)), (x, y), [(hex(r[0]), r[1], r[2], r[3]) for r in recs]))
    out.sort()
    print(snap, 'local', local, 'lead', (lx, ly), 'cells', len(out))
    for r in out[:5]: print('   ', r)
