"""statstable.py: health, defence class and per-attack damage by rank for every (kind, subtype) of kinds 1-3, from the char data $2fa2 reads
 (health word[base+2*rank], defence byte[base+64+rank], damage byte[base+$60+rank+row], row = word 8 of the attack box)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anim import rom, rw
CASES = [  # name, p56 (box base), p92 (char data base), number of attack boxes
    ('J (k1 s0)', 0x298c4, 0x29974, 4), ('TWO.P (k1 s1)', 0x2a1c0, 0x2a270, 4),
    ('AXL (k2 s0)', 0x2be98, 0x2bf30, 4), ('SLASH (k2 s1)', 0x2cb74, 0x2cc0c, 4),
    ('ANDORE Jr. (k3 s0)', 0x30e14, 0x30eec, 7), ('ANDORE (k3 s1)', 0x30e14, 0x3100c, 7), ('G/U/F.ANDORE (k3 s2-4, 1P)', 0x30e14, 0x3112c, 7)]
RANKS = [0, 4, 8, 12, 16, 24, 31]
for name, a0, cd, nb in CASES:
    print(name)
    print('   rank           ' + ' '.join('%4d' % r for r in RANKS))
    print('   health         ' + ' '.join('%4d' % rw(cd + 2 * r) for r in RANKS))
    print('   defence class  ' + ' '.join('%4d' % rom[cd + 64 + r] for r in RANKS))
    off = rw(a0)
    for i in range(1, nb + 1):
        e = a0 + off + 16 * i
        dx, dy, hw, hh, row, flags = rw(e) , rw(e + 2), rw(e + 4), rw(e + 6), rw(e + 8), rw(e + 10)
        print('   atk id %d box dx=%d dy=%d hw=%d hh=%d row=%02x type=%d: ' % (i, dx if dx < 0x8000 else dx - 65536, dy, hw, hh, row, flags & 0xff) + ' '.join('%4d' % rom[cd + 0x60 + r + row] for r in RANKS))
