"""typename.py - world-name round trip through the conquest briefing UI ($1a5c4).

From a briefing snapshot (stopped in the $1afc4 click wait): click NEW GAME, type NAME on the
keyboard (IKBD make/break scancodes) and RETURN, stop at the next $1afc4 wait and snapshot.
usage: python typename.py <in_tag> <NAME> <out_tag>"""
import sys
from eg import *
from popdrive import click_lines
SC = dict(zip('ABCDEFGHIJKLMNOPQRSTUVWXYZ', [0x1e, 0x30, 0x2e, 0x20, 0x12, 0x21, 0x22, 0x23, 0x17, 0x24, 0x25, 0x26,
                                               0x32, 0x31, 0x18, 0x19, 0x10, 0x13, 0x1f, 0x14, 0x16, 0x2f, 0x11, 0x2d, 0x15, 0x2c]))
SC.update(zip('1234567890', range(2, 12)))
SC['\n'] = 0x1c
SC['\b'] = 0x0e

def key_lines(text):
    L = []
    for ch in text:
        L += ['kbd %02x' % SC[ch], 's 240000', 'kbd %02x' % (SC[ch] | 0x80), 's 240000']
    return L

if __name__ == '__main__':
    tin, name, tout = sys.argv[1], sys.argv[2].upper(), sys.argv[3]
    src = OUT + '/%s.snap' % tin
    m = ram(src)
    L = click_lines(sw(m, 0x24748), sw(m, 0x2474a), 240, 176)      # NEW GAME button (192..288, 168..184)
    L += key_lines(name + '\n')
    L += ['bp 1afc4 60000000', 'r', 'snap %s/%s.snap' % (OUT, tout)]
    out = repl(src, L)
    r = regs(out)
    print('\n'.join(x for x in out.splitlines() if x.startswith('PC') or 'breakpoint' in x))
    m = ram(OUT + '/%s.snap' % tout)
    print('name', repr(cstr(m, 0x37e86)), 'world(-18)', sw(m, r['A6'] - 18), 'rec', m[0x22ad8:0x22ae2].hex())
