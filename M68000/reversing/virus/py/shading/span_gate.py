"""Gate: the colour span routines behind $1f2bc, called directly through stserver as the tile filler $26b78 enters them
(`jsr 0(A0,A2.w)`): A0 = the colour's table (long at $1f2bc + 4*c), A2 = the word at A0 + 2*width, D4 = x of the first pixel,
D5 = width, A3 = the scanline's byte address, A1 = $ceba.  Model: pixels x..x+width-1 of the 4-plane line take colour c (c < 16),
the rest of the line is untouched; colours 16..23 take (c-16) with plane 3 from the alternating word at $1cb78 (inverted on each
call), i.e. a checker of colours c-16 and c-8.  The line is pre-filled with random words.  `control` models one pixel too wide.
Usage: span_gate.py <snap> [calls per colour] [control]"""
import os, random, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from stclient import StServer
snap = sys.argv[1]; N = int(sys.argv[2]) if len(sys.argv) > 2 else 60
CONTROL = len(sys.argv) > 3 and sys.argv[3] == 'control'
s = StServer(ROOT); s('load', snapshot=snap)
LINE = 0x78a00 + 160 * 20; random.seed(1)
def pixel(line, xx):
    o = (xx >> 4) * 8; bit = 15 - (xx & 15); v = 0
    for p in range(4): v |= ((struct.unpack('>H', line[o + 2 * p:o + 2 * p + 2])[0] >> bit) & 1) << p
    return v
tot = ok = 0
for c in range(24):
    base = struct.unpack('>L', s.read(0x1f2bc + 4 * c, 4))[0]
    for _ in range(N):
        w = random.choice([random.randint(1, 20), random.randint(1, 70), random.randint(1, 300)])
        x = random.randint(0, 319 - w); pre = [random.randint(0, 65535) for _ in range(80)]
        entry = (base + struct.unpack('>h', s.read(base + 2 * w, 2))[0]) & 0xffffff
        for i in range(80): s('poke', addr=LINE + 2 * i, width=2, value=pre[i])
        chk = struct.unpack('>H', s.read(0x1cb78, 2))[0]
        s.call(entry, d4=x, d5=w, a3=LINE, a1=0xceba, a0=base, max_steps=100000)
        got = s.read(LINE, 160); prel = b''.join(struct.pack('>H', v) for v in pre); m3 = ~chk & 0xffff
        good = True
        for xx in range(320):
            exp = pixel(prel, xx)
            if x <= xx < x + w + CONTROL:
                exp = c if c < 16 else (c - 16) | (8 if (m3 >> (15 - (xx & 15))) & 1 else 0)
            if pixel(got, xx) != exp: good = False; break
        tot += 1; ok += good
print('span calls matching the pixel model%s: %d/%d' % (' (control: one pixel too wide)' if CONTROL else '', ok, tot))
s.close()
