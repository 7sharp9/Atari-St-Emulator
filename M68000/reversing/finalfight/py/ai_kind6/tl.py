#!/usr/bin/env python3
"""Timeline of the kind-6 records in a k6run frames.bin. tl.py <frames.bin> [from [to]] [-v]  (state bytes change lines)"""
import sys
FS = 13*192 + 2*192 + 0x200
d = open(sys.argv[1], 'rb').read()
n = len(d)//FS
lo = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 0
hi = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else n
def rec(fr, i): return d[fr*FS + i*192: fr*FS + (i+1)*192]
def pl(fr, i): return d[fr*FS + 13*192 + i*192: fr*FS + 13*192 + (i+1)*192]
w = lambda r, o: int.from_bytes(r[o:o+2], 'big')
sw = lambda r, o: w(r, o) - 65536 if w(r, o) & 0x8000 else w(r, o)
prev = {}
for fr in range(lo, min(hi, n)):
    for i in range(13):
        r = rec(fr, i)
        if r[0] and r[19] == 6:
            key = (r[2], r[3], r[4], r[5], r[147], r[149], r[154], r[161])
            if prev.get(i) != key:
                prev[i] = key
                p = pl(fr, 0)
                print('f%03d #%d st=%d/%d/%d/%d a147=%d a149=%d a154=%d b161=%d | x=%d y=%d gl=%d hp=%d f46=%d f54=%d box44/45=%d/%d 22=%d 63=%d 30=%d 23=%d | cody x=%d y=%d hp=%d' % (
                    fr, i, r[2], r[3], r[4], r[5], r[147], r[149], r[154], r[161], w(r, 6), sw(r, 10), sw(r, 14), sw(r, 24), r[46], r[54], r[44], r[45], r[22], r[63], r[30], r[23], w(p, 6), sw(p, 10), sw(p, 24)))
