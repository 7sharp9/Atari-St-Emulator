"""setters.py <lo> <hi>: find animation setters (moveq #0,D0 / move.b 20(A6),D0 / lea 6(PC),A1 / jmp $3b10.w, optionally with the 21(A6) / long-table variants) and print each setter's
 per-subtype animation: step list with (timer, flag, hurt box, attack box)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anim import *
lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
pat = bytes.fromhex('7000102e001443fa00064ef83b10')
a = lo
found = []
while True:
    i = rom.find(pat, a, hi)
    if i < 0: break
    A1 = i + 8 + 6   # lea 6(PC): PC = addr of the extension word = i+8 ; +6 -> after jmp (i+14) = table
    found.append((i, i + 14))
    a = i + 2
for addr, tbl in found:
    print('setter %06x table %06x: words %04x %04x' % (addr, tbl, rw(tbl), rw(tbl + 2)))
    for idx in (0, 1):
        sc = tbl + rw(tbl + 2 * idx)
        st = steps(sc)
        sig = ' '.join('%d/%02x/h%02x/a%02x' % (s[1], s[2], s[4], s[5]) for s in st if s[0] not in ('LOOP', 'LOOPTO', 'END'))
        tail = [s for s in st if s[0] in ('LOOP', 'LOOPTO', 'END')]
        print('   sub%d script %06x: %s %s' % (idx, sc, sig, tail[-1:] if tail else ''))
