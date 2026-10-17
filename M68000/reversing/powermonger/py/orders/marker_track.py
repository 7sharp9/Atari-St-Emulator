"""marker_track.py <snap>...: per snapshot, every $4c5f4 marker with byte15 != 0 or linked into a cell chain: byte15, (x, y), chained?"""
import sys
from pathlib import Path
ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(ROOT / 'reversing/powermonger/py/arms'))
import pm_fsm_ref as P
from disassemble import ram_from_snap
import sheep_cells as S
for snap in sys.argv[1:]:
    m = P.Mem(ram_from_snap(snap)); n = m.wu(0x4ccd4); rows = []
    for a in range(0x4c5f4 + 0x16, 0x4c5f4 + n, 0x16):
        p15 = P.s8(m.bu(a + 15))
        if p15 != 0:
            x, y = m.bu(a + 8), m.bu(a + 10)
            ch = a in [r[0] for r in S.cell_list(m, x, y)]
            rows.append((hex(a), p15, (x, y), ch, m.bu(a+6)))
    print(Path(snap).name, 'ops', [hex(m.wu(0x57f68+8*i+6)) for i in range(10)], len(rows), rows[:4])
