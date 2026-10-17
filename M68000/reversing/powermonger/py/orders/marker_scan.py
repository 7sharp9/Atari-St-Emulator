"""marker_scan.py <snap>...: forest markers ($4c5f4 pool, stride 22, length word $4ccd4) that sit in a $47970 cell chain with byte6 $14/$16, and the cells holding them."""
import sys
from pathlib import Path
ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(ROOT / 'reversing/powermonger/py/arms'))
import pm_fsm_ref as P
from pm_common import OBJ
from disassemble import ram_from_snap
import sheep_cells as S
for snap in sys.argv[1:]:
    m = P.Mem(ram_from_snap(snap))
    n = m.wu(0x4ccd4); hit = []
    live = 0
    for a in range(0x4c5f4 + 0x16, 0x4c5f4 + n, 0x16):
        b6 = m.bu(a + 6)
        if m.bu(a + 15) != 0: live += 1
        if b6 in (0x14, 0x16):
            hit.append((hex(a), m.bu(a + 5), P.s8(m.bu(a + 15)), m.bu(a + 8), m.bu(a + 10)))
    print(snap, 'len', hex(n), 'moving(byte15!=0)', live, 'cat14/16', len(hit))
    for h in hit[:8]: print('   ', h)
    # chain check: which marker records are linked into a cell chain
    cells = {}
    for a in range(0x4c5f4 + 0x16, 0x4c5f4 + n, 0x16):
        cells.setdefault((m.bu(a + 8), m.bu(a + 10)), []).append(a)
    for (x, y), al in list(cells.items())[:6]:
        ch = S.cell_list(m, x, y)
        print('   cell', (x, y), 'markers', len(al), 'chain', [(hex(r[0]), r[2]) for r in ch][:12])
