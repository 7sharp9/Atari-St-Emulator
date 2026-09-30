"""Number formatter $1b522(dst, value, x, y, bg): value in tenths (clamped to 999): [hundreds digit if value >= 100] at x, tens digit at x+6,
'.' (glyph 10) at x+12, units digit at x+18; 6x6 glyph cells, foreground colour 0, background colour bg.  Differential test vs text.py."""
import sys, os, random, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from calldiff import CallDiff
from text import *

cd = CallDiff(); R = cd.ram
font = bytes(R[A4 - 7770:A4 - 7770 + 336])
scr = struct.unpack_from('>I', R, A4 - 78)[0]
random.seed(12)
ok = n = 0
for t in range(40):
    v = random.choice([0, 5, 9, 10, 99, 100, 101, 505, 999, 1000, 5000, random.randrange(0, 1500)])
    x = random.randrange(0, 290); y = random.randrange(0, 190); bg = random.randrange(16)
    oc, ch, d = cd.call(0x1B522, struct.pack('>HHhhH', 0, 0, 0, 0, 0)[:0] + struct.pack('>IHhhH', scr, v & 0xFFFF, x, y, bg))
    assert oc == 'returned', oc
    live = cd.apply(R[scr:scr + 32000], scr, ch); mine = bytearray(R[scr:scr + 32000])
    vv = min(v, 999)
    if vv > 99: blit_glyph(mine, font, vv // 100, x, y, bg, 0)
    blit_glyph(mine, font, (vv // 10) % 10, x + 6, y, bg, 0)
    blit_glyph(mine, font, 10, x + 12, y, bg, 0)
    blit_glyph(mine, font, vv % 10, x + 18, y, bg, 0)
    eq = sum(1 for a, b in zip(live, mine) if a == b); ok += eq; n += 32000
    if eq != 32000: print('  mismatch v', v, 'x', x, 'y', y, 'bg', bg, 32000 - eq)
print('number formatter $1b522: %d / %d screen bytes equal over 40 trials' % (ok, n))
cd.close()
