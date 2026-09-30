"""Differential test of text.blit_glyph against the live glyph blitter $16528 (callcap)."""
import sys, os, random, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from calldiff import CallDiff
from text import *

cd = CallDiff()
R = cd.ram
font = bytes(R[A4 - 7770:A4 - 7770 + 336])
scr_addr = struct.unpack_from('>I', R, A4 - 78)[0]
random.seed(5)
ok = n = 0
trials = int(sys.argv[1]) if len(sys.argv) > 1 else 30
for t in range(trials):
    glyph = random.randrange(42); x = random.randrange(0, 310); y = random.randrange(0, 190)
    bg = random.randrange(16); fg = random.randrange(16)
    args = struct.pack('>IHhhHH', scr_addr, glyph, x, y, bg, fg)
    oc, ch, d = cd.call(0x16528, args)
    assert oc == 'returned', oc
    live = cd.apply(R[scr_addr:scr_addr + 32000], scr_addr, ch)
    mine = bytearray(R[scr_addr:scr_addr + 32000])
    blit_glyph(mine, font, glyph, x, y, bg, fg)
    eq = sum(1 for a, b in zip(live, mine) if a == b)
    ok += eq; n += 32000
    if eq != 32000: print('  mismatch glyph', glyph, 'x', x, 'y', y, 'bg', bg, 'fg', fg, 32000 - eq, 'bytes')
print('glyph blitter $16528: %d / %d screen bytes equal over %d random glyph draws' % (ok, n, trials))
cd.close()
