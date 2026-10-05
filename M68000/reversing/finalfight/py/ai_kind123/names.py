"""names.py: decode the HUD enemy-name table read by $5b640 (tag at 18(A6), kind 19(A6), subtype 20(A6)): entry = A0 + word[A0+2*kind] + 32*subtype,
 A0 = $5b682 + word[$5b682 + tag]; entry words: palette, 4 portrait tiles, palette, 10 name tiles ($44xx = ASCII xx, $4420 = blank)."""
import os
root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..'))
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
rw = lambda a: (rom[a] << 8) | rom[a + 1]
tag = 2
A0 = 0x5b682 + rw(0x5b682 + tag)
for kind in range(9):
    off = rw(A0 + 2 * kind)
    for st in range(0, 8):
        e = A0 + off + 32 * st
        w = [rw(e + 2 * i) for i in range(16)]
        if w[0] >> 8 != 1 or w[5] != 0x180: break
        name = ''.join(chr(x & 0xff) if (x >> 8) == 0x44 else '?' for x in w[6:])
        print('kind %d sub %d entry %06x pal %04x portrait %s name "%s"' % (kind, st, e, w[0], ' '.join('%04x' % x for x in w[1:5]), name.strip()))
