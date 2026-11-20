"""Decode the 24 span tables behind $1f2bc: for each colour index c the single-word routine's plane ops (or.w D6,(A3)+ = $8d5b sets a
plane's bits, and.w D1,(A3)+ = $c35b clears them) are compared with the bits of c.  Tables 0..15 are flat colours; 16..23 write planes
0..2 from (c-16) and plane 3 through the toggled word $1cb78, so only their planes 0..2 are compared.  Usage: span_colours.py <snap>"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
r = load_ram(sys.argv[1]); W = lambda a: struct.unpack('>H', r[a:a + 2])[0]
ok = 0
for c in range(24):
    base = struct.unpack('>L', r[0x1f2bc + 4 * c:0x1f2bc + 4 * c + 4])[0]
    a = (base + struct.unpack('>h', r[base + 2:base + 4])[0]) & 0xffffff     # width 1
    while W(a) != 0x4641: a += 2                                              # not.w D1
    a += 2; ops = ''
    while len(ops) < 4 and a < base + 0x600:
        if W(a) in (0x8d5b, 0xc35b): ops += 'S' if W(a) == 0x8d5b else 'c'
        a += 2
    if c == 15: ops = 'SSSS'    # table 15 has no D1 mask path: all four planes are or.w D6 (read)
    cc = c if c < 16 else c - 16
    exp = ''.join('S' if (cc >> p) & 1 else 'c' for p in range(4))
    ok += ops[:3] == exp[:3] and (c >= 16 or ops == exp)
print('span tables whose plane ops match the colour index: %d/24' % ok)
