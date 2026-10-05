#!/usr/bin/env python3
"""fa.py <frames.bin> <from> <to> [-a]  per-frame view of the kind-6 record (changes only; -a every frame).
columns: frame st(3/4/5) op154 id149 anim(32) frame ptr(36) t40 f41 box44/45 atk-ptr(112) x y gl vx(80) vy(84) f46 f54 | cody x hp"""
import sys
FS = 13*192 + 2*192 + 0x200
d = open(sys.argv[1], 'rb').read()
n = len(d)//FS
lo, hi = int(sys.argv[2]), int(sys.argv[3])
allf = '-a' in sys.argv
def rec(fr, i): return d[fr*FS + i*192: fr*FS + (i+1)*192]
def pl(fr, i): return d[fr*FS + 13*192 + i*192: fr*FS + 13*192 + (i+1)*192]
w = lambda r, o: int.from_bytes(r[o:o+2], 'big')
l = lambda r, o: int.from_bytes(r[o:o+4], 'big')
sw = lambda r, o: w(r, o) - 65536 if w(r, o) & 0x8000 else w(r, o)
prev = None
phpp = None
for fr in range(lo, min(hi, n)):
    for i in range(13):
        r = rec(fr, i)
        if r[0] and r[19] == 6:
            p = pl(fr, 0)
            key = (r[3], r[4], r[5], r[154], l(r, 32), l(r, 36), r[44], r[45], w(r, 6), sw(r, 10), sw(r, 80), sw(r, 84))
            hp = sw(p, 24)
            hit = ''
            if phpp is not None and hp < phpp: hit = ' HIT -%d' % (phpp - hp)
            phpp = hp
            if allf or key != prev or hit:
                print('f%03d %d/%d/%d op%02x id%d anim%06x fr%06x t%d/%02x box%d/%d atk%06x x%d y%d gl%d vx%d vy%d f46=%d h54=%d | cody x%d hp%d%s' % (
                    fr, r[3], r[4], r[5], r[154], r[149], l(r, 32) & 0xffffff, l(r, 36) & 0xffffff, r[40], r[41], r[44], r[45], l(r, 112) & 0xffffff, w(r, 6), sw(r, 10), sw(r, 14), sw(r, 80), sw(r, 84), r[46], r[54], w(p, 6), hp, hit))
                prev = key
