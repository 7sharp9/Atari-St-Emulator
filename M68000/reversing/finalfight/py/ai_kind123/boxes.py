"""boxes.py <A0 = 56(A6) base> <char data 92(A6) base before $2fa2> [rank list]: print hurt boxes (A0 + 8*i), attack boxes (A0 + word(A0) + 16*i: dx dy hw hh, +8 word dmg row index,
 +10, +11 flags byte (bit7 hard), +12 sound), and, per rank, health (word[base+2*rank]), defence class (byte[base+64+rank]) and damage byte[base + $60 + rank + word(+8)]."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anim import rom, rw, s16
A0 = int(sys.argv[1], 16); CD = int(sys.argv[2], 16)
ranks = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else [0, 4, 7]
off = rw(A0)
print('attack list at %06x (A0+%x)' % (A0 + off, off))
nh = (off - 8) // 8 if off > 8 else 0
for i in range(1, 16):
    a = A0 + 8 * i
    if a >= A0 + off: break
    print('hurt %2d: dx=%d dy=%d hw=%d hh=%d' % (i, s16(rw(a)), s16(rw(a + 2)), rw(a + 4), rw(a + 6)))
for i in range(1, 12):
    a = A0 + off + 16 * i
    v = [rw(a + 2 * k) for k in range(8)]
    if all(x == 0 for x in v): continue
    print('atk %2d @%06x: dx=%d dy=%d hw=%d hh=%d  w8=%04x(row %d) w10=%04x b11=%02x w12=%04x w14=%04x' % (i, a, s16(v[0]), s16(v[1]), v[2], v[3], v[4], v[4] // 32, v[5], v[5] & 0xff, v[6], v[7]))
print('char data %06x: health(rank) %s' % (CD, ' '.join('%d:%d' % (r, rw(CD + 2 * r)) for r in ranks)))
print('  defence class by rank %s' % ' '.join('%d:%d' % (r, rom[CD + 64 + r]) for r in ranks))
rows = sorted(set(rw(A0 + off + 16 * i + 8) for i in range(1, 12)))
for row in rows:
    print('  dmg row idx %04x: %s' % (row, ' '.join('r%d=%d' % (r, rom[CD + 0x60 + r + row]) for r in ranks)))
