"""Gate: the slope table at $5ab58 used by the tile/polygon filler $26b78: entry[(dx<<7)+dy] (longs, index taken as a
signed word, so dx in -64..63, dy in 1..63 (dy 64..127 slots hold something else: not modelled)) == -(trunc(dx*65536/dy) with the low 8 bits cleared), 16.16 fixed.
Usage: python virus_slope.py <snap> [--break]   (--break: clear no bits, i.e. exact 16.16)"""
import os, struct, sys
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')): d = os.path.dirname(d)
sys.path.insert(0, os.path.join(d, 'tools'))
import gfxview
r = bytes(gfxview.load_ram(sys.argv[1])[0])
ok = n = 0; bad = []
mask = 0xffffffff if '--break' in sys.argv else ~0xff
for dx in range(-64, 64):
    for dy in range(1, 64):
        idx = (((dx << 7) + dy) & 0xffff) << 2
        idx = idx - 0x40000 if False else (idx & 0xffff)
        if idx >= 0x8000: idx -= 0x10000
        got = struct.unpack('>l', r[0x5ab58 + idx:0x5ab58 + idx + 4])[0]
        q = int(dx * 65536 / dy)                       # trunc toward zero
        exp = -(abs(q) & mask) if q >= 0 else (abs(q) & mask)
        n += 1; ok += got == exp
        if got != exp and len(bad) < 3: bad.append((dx, dy, got, exp))
print(f'slope table entries == -(trunc(dx*65536/dy) & ~$ff): {ok}/{n}', bad)
