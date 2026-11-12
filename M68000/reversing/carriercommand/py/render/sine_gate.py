"""sine_gate.py - the table at $1864 (4096 words) == round(16384*sin(2*pi*k/4096)) for every k; $1c28..$24b0 is the k=482..1574 slice."""
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent)); _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import struct, math, sys
from rig import RAM
w = [struct.unpack('>h', RAM[0x1864 + 2*k: 0x1866 + 2*k])[0] for k in range(4096)]
m = sum(1 for k in range(4096) if w[k] == round(16384 * math.sin(2 * math.pi * k / 4096)))
print('sine table $1864: exact match', m, '/ 4096 ; first word', w[0], 'peak', max(w), 'at k', w.index(max(w)), ' end $%x' % (0x1864 + 8192))
print('$1c28 is entry', (0x1c28 - 0x1864) // 2, '; $24b0 is entry', (0x24b0 - 0x1864) // 2, '(angle %.1f..%.1f deg)' % (((0x1c28-0x1864)//2)*360/4096, ((0x24b0-0x1864)//2)*360/4096))
