import sys
from pathlib import Path
ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(ROOT / 'reversing/powermonger/py/arms'))
import pm_fsm_ref as P
from disassemble import ram_from_snap
import sheep_cells as S
m = P.Mem(ram_from_snap(sys.argv[1])); a = int(sys.argv[2], 16)
x, y = m.bu(a + 8), m.bu(a + 10)
print('marker', hex(a), 'byte5', m.bu(a + 5), 'cell', (x, y), 'words 0,2', hex(m.wu(a)), hex(m.wu(a + 2)), 'in its cell chain:', a in [r[0] for r in S.cell_list(m, x, y)])
