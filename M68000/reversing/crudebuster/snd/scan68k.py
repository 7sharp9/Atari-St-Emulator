#!/usr/bin/env python3
"""Raw-byte scan of the whole 68000 image for every reference to the sound-send routine $e1c (and the other latch writers).
Finds bsr.w/bra.w (displacement), jsr/jmp abs.w/abs.l, lea/move.l/pea of the literal address, and PC-relative table words."""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(HERE, '..', '..', '..'))
d = open(os.path.join(ROOT, 'scratchpad/crudebuster/rom/cbuster_main.bin'), 'rb').read()
T = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0xe1c
w = lambda a: (d[a] << 8) | d[a + 1]
hits = []
for a in range(0, len(d) - 6, 2):
    op = w(a)
    if op in (0x6100, 0x6000):                       # bsr.w / bra.w
        disp = w(a + 2); disp = disp - 0x10000 if disp & 0x8000 else disp
        if a + 2 + disp == T: hits.append((a, 'bsr.w' if op == 0x6100 else 'bra.w'))
    if op in (0x4eb8, 0x4ef8) and w(a + 2) == T: hits.append((a, 'jsr.w' if op == 0x4eb8 else 'jmp.w'))
    if op in (0x4eb9, 0x4ef9) and w(a + 2) == 0 and w(a + 4) == T: hits.append((a, 'jsr.l' if op == 0x4eb9 else 'jmp.l'))
    if w(a) == 0 and w(a + 2) == T and op == 0: hits.append((a, 'long literal 0000%04x' % T))
for a, k in hits: print('%06x %s' % (a, k))
print(len(hits), 'hits')
