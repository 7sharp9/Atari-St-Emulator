"""poke_op.py <snap> <op> : print the REPL poke lines that claim forest op <op>'s first tree (worker_obj := the local lead, a byte6-0 man record)."""
import sys
from pathlib import Path
ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'tools'))
import pm_fsm_ref as P
from pm_common import OBJ
from disassemble import ram_from_snap
m = P.Mem(ram_from_snap(sys.argv[1])); op = int(sys.argv[2])
local = m.wu(0x57ffe); base = 0x51538 + local * 0x13c
lead = OBJ + P.s16(m.wu(base + 64))
assert m.bu(lead + 6) == 0, 'lead byte6 != 0'
t = 0x4d252 + m.wu(0x57f68 + 8 * op + 4)
print('w %x %04x%04x' % (t + 2, lead - OBJ, m.wu(t + 4)))
