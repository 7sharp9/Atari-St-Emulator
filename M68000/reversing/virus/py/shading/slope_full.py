"""Gate: the whole slope table at $5ab58 (16384 longs; slot s = signed word index of the tile filler $26b78: s = (dx<<7)+dy, offset 4*s).
One formula over a signed dy: write s = dx*128 + dy with dy in -64..63 (the slots the first gate called 'dy 64..127' are the dy -64..-1
slots of the next dx).  entry = 1 when dy == 0, else -(trunc(dx*65536/dy)) with the low 8 bits of the magnitude cleared.
Valid slots are -8192..8127; from 8128 the longs overlay the flag bytes at $62a58.. (not table).  --break keeps the low byte (control).
Usage: slope_full.py <snap> [--break]"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
r = load_ram(sys.argv[1]); mask = 0xffffffff if '--break' in sys.argv else ~0xff
ok = n = 0; by = {'dy>0': [0, 0], 'dy<0': [0, 0], 'dy=0': [0, 0]}
for s in range(-8192, 8128):
    dx = (s + 64) >> 7; dy = s - dx * 128
    if dy == 0: e = 1
    else:
        num = dx * 65536; q = abs(num) // abs(dy); q = q if (num >= 0) == (dy > 0) else -q
        e = -(abs(q) & mask) if q >= 0 else (abs(q) & mask)
    got = struct.unpack('>l', r[0x5ab58 + 4 * s:0x5ab58 + 4 * s + 4])[0]
    k = 'dy=0' if dy == 0 else ('dy>0' if dy > 0 else 'dy<0')
    n += 1; ok += got == e; by[k][0] += got == e; by[k][1] += 1
print('slope table slots == model: %d/%d  %s' % (ok, n, {k: '%d/%d' % tuple(v) for k, v in by.items()}))
