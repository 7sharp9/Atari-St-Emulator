#!/usr/bin/env python3
"""island_params.py <snap>... (BUG=1: broken control): compare the game's island parameter block ($1697a..$16988, $1698a) in each snapshot
against a Python model of $16166 (seed from island number word at $1d566). Prints N/N."""
import os, sys
d = os.path.abspath(os.path.dirname(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    d = os.path.dirname(d)
sys.path.insert(0, os.path.join(d, 'tools'))
from gfxview import load_ram

def model(n, bug=0):
    s = (4 * n + 0x1388 + bug) & 0xFFFF
    def rnd():
        nonlocal s
        s = (5 * s + 1) & 0xFFFF
    def sc(m):                      # $16050: (low byte of seed * m) / 255
        return ((s & 0xFF) * m) // 255
    out = {}
    rnd(); out[0x1697a] = sc(40) + 0x14
    rnd(); out[0x1697c] = sc(100) + 100
    out[0x1697e] = out[0x1697c] >> 1
    rnd(); t1 = out[0x16980] = sc(32) + 0xF
    rnd(); t2 = out[0x16982] = sc(32) + t1 + 0xF
    rnd(); t3 = sc(32) + t2 + 0xF
    out[0x16984] = 100 if t3 >= 100 else t3
    out[0x16986] = 100
    rnd(); out[0x16988] = sc(80) + 10
    out[0x1698a] = (4 * n + 0x3039) & 0xFFFF
    return out

if __name__ == '__main__':
    bug = int(os.environ.get('BUG', '0'))
    for snap in sys.argv[1:]:
        ram, _ = load_ram(snap)
        w = lambda a: ram[a] << 8 | ram[a + 1]
        n = w(0x1d566)
        m = model(n, bug)
        ok = sum(w(a) == v for a, v in m.items())
        print(f'{os.path.basename(snap)} N={n}: {ok}/{len(m)}', {hex(a): (w(a), v) for a, v in m.items() if w(a) != v})
