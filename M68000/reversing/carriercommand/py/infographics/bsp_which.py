"""bsp_which.py - which models the game draws from a snapshot: bp at the far ($8e68) and near ($9066) draw routines,
A0 - 4 looked up in the model table $4c4ce.  usage: bsp_which.py <snap> [steps]"""
import pathlib as _pl, sys as _sys, collections
_here = _pl.Path(__file__).resolve().parent
_sys.path.insert(0, str(_here.parent))
from ccpaths import *
_sys.path.insert(0, str(ROOT / 'tools'))
from stclient import StServer
import struct
snap = _sys.argv[1]; budget = int(_sys.argv[2]) if len(_sys.argv) > 2 else 1200000
s = StServer(str(ROOT)); print(s('load', snapshot=snap))
tab = s.read(0x4c4ce, 4 * 99); ids = {struct.unpack_from('>I', tab, 4 * i)[0]: i for i in range(99)}
s('bp_set', addrs=[0x8e68, 0x9066])
start = s('regs')['step'] if 'step' in s('regs') else None
seen = collections.Counter(); left = budget; r = None
while left > 0:
    r = s('run', max_steps=left)
    if not str(r.get('reason', r)).count('bp') and r.get('pc') not in ('$8e68', '$9066') and 'break' not in str(r): print('stop', r); break
    rg = s('regs'); pc = int(str(rg['pc']).lstrip('$'), 16); a0 = int(str(rg['a0']).lstrip('$'), 16)
    seen[(hex(pc), ids.get(a0 - 4, hex(a0)))] += 1
    left -= int(r.get('steps', 1)) if isinstance(r, dict) else 1
    s('step', n=1)
print(r); print(sorted(seen.items(), key=lambda x: -x[1]))
