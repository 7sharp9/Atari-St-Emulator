"""ops_scan.py <snap>: forest ops ($57f68), first tree, its cell, tree_state, worker_obj, marker chain length, distance to the local lead, and a man record usable as worker."""
import sys
from pathlib import Path
ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'tools'))
import pm_fsm_ref as P
from pm_common import OBJ
from disassemble import ram_from_snap
m = P.Mem(ram_from_snap(sys.argv[1]))
local = m.wu(0x57ffe); base = 0x51538 + local * 0x13c
lead = OBJ + P.s16(m.wu(base + 64)); lx, ly = m.bu(lead + 8), m.bu(lead + 10)
print('local', local, 'lead', hex(lead), (lx, ly), 'oplen', m.wu(0x57fb8))
for i in range(10):
    op = 0x57f68 + 8 * i
    tc = m.wu(op)
    if not tc: break
    t = 0x4d252 + m.wu(op + 4)
    cell = m.wu(t + 10); x, y = cell & 63, cell >> 6
    k, mk = 0, m.wu(op + 6)
    while mk and k < 100:
        k += 1; mk = m.wu(0x4c5f4 + mk + 20)
    print('op', i, 'tgt', hex(tc), 'tree0', hex(t), 'cell', (x, y), 'dist', max(abs(x-lx), abs(y-ly)), 'state', hex(m.bu(t+7)), 'cat', m.bu(t+6), 'worker', hex(m.wu(t+2)), 'markers', k, 'marker_off', hex(m.wu(op+6)))
