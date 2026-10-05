#!/usr/bin/env python3
"""Static scan: every call of $2874 (the 324(A5) command ring writer) with the D0 immediate that precedes it.
usage: ringcallers.py [target-hex ...]   (default 2874)
The repo root is derived from __file__ (reversing/finalfight/py/engine/)."""
import os, sys
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(root, 'reversing', 'finalfight', 'py'))
from callers import callers
rom = open(os.path.join(root, 'scratchpad', 'finalfight', 'ff_main.bin'), 'rb').read()
def w(a): return int.from_bytes(rom[a:a+2], 'big')
def prev_d0(c, tgt=None):
    # look back up to 24 bytes for an instruction that loads D0 with an immediate
    for back in range(2, 26, 2):
        a = c - back
        x = w(a)
        if x == 0x303c: return ('move.w', w(a+2), a)
        if x == 0x203c: return ('move.l', int.from_bytes(rom[a+2:a+6], 'big'), a)
        if (x & 0xf1ff) == 0x7000 and ((x >> 9) & 7) == 0:
            v = x & 0xff
            return ('moveq', v, a)
    return None
if __name__ == '__main__':
    tg = [int(t, 16) for t in (sys.argv[1:] or ['2874'])]
    for t in tg:
        for c, k in callers(t):
            p = prev_d0(c)
            print('%06x %-5s %s' % (c, k, ('%s #$%x @%x' % p) if p else '?'))
