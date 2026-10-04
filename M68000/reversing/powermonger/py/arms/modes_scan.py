"""modes_scan.py <snap>...: per snapshot the local group's food (112), men (52), state (76), and the number of men records
(byte6 0, owner > 0) in each mode byte 31, flagging $36/$38; plus the animals' categories.  (PowerMonger 148th, agent A)"""
import os, sys, collections
from pathlib import Path
def _root():
    if os.environ.get('M68000_ROOT'): return Path(os.environ['M68000_ROOT'])
    for p in Path(__file__).resolve().parents:
        if (p / 'tools' / 'pm_fsm_ref.py').exists(): return p
ROOT = _root()
sys.path.insert(0, str(ROOT / 'tools'))
import pm_fsm_ref as P
from pm_common import OBJ, OBJ_STRIDE
from disassemble import ram_from_snap
for f in sys.argv[1:]:
    m = P.Mem(ram_from_snap(f))
    local = m.wu(0x57ffe)
    A1 = 0x51538 + local * 0x13c
    modes = collections.Counter()
    for i in range(512):
        a = OBJ + i * OBJ_STRIDE
        if m.bu(a + 6) == 0 and P.s8(m.bu(a + 5)) > 0:
            modes[(P.s8(m.bu(a + 5)), m.bu(a + 31))] += 1
    n = P.s16(m.wu(0x4cff6)) // 20
    cats = collections.Counter(m.bu(0x4ccd6 + i * 20 + 6) for i in range(n))
    print(os.path.basename(f), 'group0 state', m.wu(A1 + 76), 'men', m.wu(A1 + 52), 'food', m.ws(A1 + 112),
          'local modes', {hex(k[1]): v for k, v in sorted(modes.items()) if k[0] == local}, 'animals', dict(cats))
