#!/usr/bin/env python3
"""poke_tl.py <frames.bin> <rel0> [len]: timeline after a poke at relative frame rel0: state (2/3/4/5) changes with frame offsets, x, y, vx, vy, anim ptr, hp, box"""
import sys
FS = 13*192 + 2*192 + 0x200
d = open(sys.argv[1], 'rb').read(); n = len(d)//FS
r0 = int(sys.argv[2]); ln = int(sys.argv[3]) if len(sys.argv) > 3 else 300
w = lambda r, o: int.from_bytes(r[o:o+2], 'big')
l = lambda r, o: int.from_bytes(r[o:o+4], 'big')
sw = lambda r, o: w(r, o) - 65536 if w(r, o) & 0x8000 else w(r, o)
prev = None; xs = []; ys = []
for fr in range(r0, min(n, r0 + ln)):
    r = None
    for i in range(13):
        q = d[fr*FS + i*192: fr*FS + (i+1)*192]
        if q[0] and q[19] == 6: r = q
    if r is None: print('f+%d: record gone' % (fr - r0)); break
    key = (r[2], r[3], r[4], r[5])
    xs.append(w(r, 6)); ys.append(sw(r, 10))
    if key != prev:
        print('f+%03d st %d/%d/%d/%d x=%d y=%d gl=%d vx=%d vy=%d anim=%06x f46=%d hp=%d 63=%d 145=%d 99=%d' % (fr - r0, r[2], r[3], r[4], r[5], w(r, 6), sw(r, 10), sw(r, 14), sw(r, 80), sw(r, 84), l(r, 32) & 0xffffff, r[46], sw(r, 24), r[63], r[145], r[99]))
        prev = key
print('x range', min(xs), max(xs), 'ymax', max(ys))
