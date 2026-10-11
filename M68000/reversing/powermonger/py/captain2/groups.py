"""Dump the local side's group fields and the UI selection words from a .ram image.

Group k of side s: D2 = s*$13c + $4c + 2k, fields at $51538 + D2 + off (structure of arrays):
-48 owner side, -24 men, -12 lead offset ($51b66-relative), 0 state, 36 food, 48 sender, 60 posture.
Usage: groups.py <ram> [side]
"""
import os, struct, sys

d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, 'tools', 'rdis.py')) and d != '/':
    d = os.path.dirname(d)
sys.path.insert(0, os.path.join(d, 'tools'))
from disassemble import ram_from_snap

def w(b, a):
    return struct.unpack_from('>H', b, a)[0]

def sw(b, a):
    return struct.unpack_from('>h', b, a)[0]

b = ram_from_snap(sys.argv[1]) if sys.argv[1].endswith('.snap') else open(sys.argv[1], 'rb').read()
local = w(b, 0x57ffe)
side = int(sys.argv[2]) if len(sys.argv) > 2 else local
print('local $57ffe', local, ' $57fd2 sel', hex(w(b, 0x57fd2)), ' $57fd4 armed', hex(w(b, 0x57fd4)),
      ' $57fd6 csel', hex(w(b, 0x57fd6)), ' $58034 slot', hex(struct.unpack_from('>I', b, 0x58034)[0]))
print('$58042[side]', [hex(w(b, 0x58042 + 2 * s)) for s in range(5)])
print('$57fd8 counters', [w(b, 0x57fd8 + 2 * j) for j in range(6)])
for k in range(6):
    d2 = side * 0x13c + 0x4c + 2 * k
    g = 0x51538 + d2
    lead = w(b, g - 12)
    rec = 0x51b66 + lead
    print(f'k{k} D2={d2:#x} owner={sw(b, g-48)} men={sw(b, g-24)} lead={lead:#x} state={sw(b, g)} food={sw(b, g+36)} posture={sw(b, g+60)} '
          f'sender={w(b, g+48):#x} lead cell=({b[rec+8]},{b[rec+10]}) lead side={b[rec+5]} mode={b[rec+30]:#x}')
