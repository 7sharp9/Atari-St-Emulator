#!/usr/bin/env python3
"""Diff the two table sets selected by the ROM region word $726e0 (0 Japan; non-zero USA/other): placement trigger lists $6346 (non-zero) vs $631e (zero),
and the stage-script lists $5f7e (non-zero) vs $5f5e (zero). The sets are two copies of the same data at a fixed distance; a byte pair that differs only because
a long pointer into the set is shifted by that distance is not counted. Prints the genuinely differing bytes."""
import os
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
rom = open(os.path.join(root, 'scratchpad', 'finalfight', 'ff_main.bin'), 'rb').read()
w = lambda a: int.from_bytes(rom[a:a+2], 'big')
l = lambda a: int.from_bytes(rom[a:a+4], 'big')
print('region word $726e0 = %04x' % w(0x726e0))
def cmp(name, a0, b0, ln):
    dist = b0 - a0
    bad = []
    i = 0
    shifted = 0
    while i < ln:
        if rom[a0+i] != rom[b0+i]:
            # a shifted long pointer starting at i-3..i ?
            ok = False
            for s in range(0, 4):
                o = i - s
                if o >= 0 and o + 4 <= ln and l(b0+o) - l(a0+o) == dist:
                    shifted += 1; i = o + 4; ok = True; break
            if not ok: bad.append(i); i += 1
        else: i += 1
    print('%s: %x..%x vs +%x: %d bytes, %d shifted pointers, %d other differing bytes' % (name, a0, a0+ln, dist, ln, shifted, len(bad)))
    for o in bad: print('   +%x (abs %x / %x): %02x vs %02x   context %s | %s' % (o, a0+o, b0+o, rom[a0+o], rom[b0+o], rom[a0+o-6:a0+o+8].hex(), rom[b0+o-6:b0+o+8].hex()))
cmp('placement trigger lists $631e/$6346', 0x6b514, 0x6d104, 0x6ecf4 - 0x6d104)
cmp('stage scripts $5f5e/$5f7e', 0x6f320, 0x7066e, 0x719b6 - 0x7066e)
