#!/usr/bin/env python3
"""Stage-script scanner (agent E).  Lists every 16-byte spawn entry (tag byte 8, kind byte 9) found in the script areas of the
two tables $5f5e (list 0) and $5f7e (list 1); stage = 190(A5), area = 191(A5).  The live list is list 1: $5b1e does
`tst.w $726e0.l` and the ROM word there is $0002 (non-zero), so `lea $5f7e` is taken [R].
Entry layout from $5ee6/$5e84 [R]: +0 delay word, +2 tracked flag, +4 x, +6 y (bit 15 = random +-15), +8 tag, +9 kind,
+10/+11 subtype bytes (+20/+21 of the record), +12 anim frame (+54), +13 (+98), +14 variant (+96; negative = 169(A5)),
+15 one-player-only flag ($5f46).
A hit is dropped when the entry two bytes before or after it also parses (mis-aligned overlap).
usage: scripts.py [tag] [kind...]   (default tag 2, every kind)"""
import os, sys
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..'))
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
w = lambda a: int.from_bytes(rom[a:a+2], 'big')
l = lambda a: int.from_bytes(rom[a:a+4], 'big')
tag = int(sys.argv[1], 0) if len(sys.argv) > 1 else 2
kinds = [int(k, 0) for k in sys.argv[2:]]
def valid(q):
    return rom[q+8] == tag and w(q) < 0x400 and w(q+2) in (0, 1) and (w(q+4) & 0x7fff) < 0x4000 and rom[q+15] < 2 and rom[q+9] < 40
out = []
bases = sorted(l(tb + 4*st) for tb in (0x5f5e, 0x5f7e) for st in range(8))
for lst, tb in enumerate((0x5f5e, 0x5f7e)):
    for st in range(8):
        base = l(tb + 4*st)
        n = w(base) // 2
        offs = [w(base + 2*a) for a in range(n)]
        for a, off in enumerate(offs):
            p = base + off
            nxt = [base + o for o in offs if base + o > p]
            nb = [b for b in bases if b > base]
            end = min(nxt + nb[:1]) if (nxt or nb) else p + 0x400
            q = p + 2
            while q + 16 <= end:
                if valid(q) and (not kinds or rom[q+9] in kinds) and not valid(q-2) and not valid(q+2):
                    out.append((lst, st, a, q, w(q), w(q+2), w(q+4), w(q+6), rom[q+9], rom[q+10], rom[q+11], rom[q+12], rom[q+13], rom[q+14], rom[q+15]))
                q += 2
for o in out:
    print('list%d stage%d area%d @%06x delay=%04x tracked=%d x=%04x y=%04x kind=%d sub20=%d sub21=%d f12=%02x b13=%02x b14=%02x b15=%02x' % o)
