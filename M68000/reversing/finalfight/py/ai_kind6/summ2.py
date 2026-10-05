#!/usr/bin/env python3
"""summ2.py <char> (run directory: $K6_RUN_DIR) : per id summary from run/id<char>_<id>_frames.bin (single forced action at rel 60)"""
import sys, os
FS = 13*192 + 2*192 + 0x200
w = lambda r, o: int.from_bytes(r[o:o+2], 'big')
sw = lambda r, o: w(r, o) - 65536 if w(r, o) & 0x8000 else w(r, o)
ch = sys.argv[1]
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..'))
here = os.environ.get('K6_RUN_DIR') or os.path.join(ROOT, 'scratchpad/finalfight/p3/d/run')
for k in range(16):
    p = os.path.join(here, 'id%s_%d_frames.bin' % (ch, k))
    d = open(p, 'rb').read(); n = len(d)//FS
    def rec(fr):
        for i in range(13):
            r = d[fr*FS + i*192: fr*FS + (i+1)*192]
            if r[0] and r[19] == 6: return r
    def cody(fr): return d[fr*FS + 13*192: fr*FS + 14*192]
    start = 61; end = None; segs = []; cur = None; hits = []; ops = []; xs = []; ys = []
    prevhp = sw(cody(start), 24)
    for fr in range(start, n):
        r = rec(fr)
        if r is None: break
        if end is None and r[3] != 4: end = fr
        if end is None:
            if not ops or ops[-1][0] != r[154]: ops.append((r[154], fr))
            a = r[45]
            if cur and a != cur[0]: segs.append((cur[0], cur[1], fr - 1)); cur = None
            if a and not cur: cur = (a, fr)
            xs.append(w(r, 6)); ys.append(sw(r, 10))
        hp = sw(cody(fr), 24)
        if hp < prevhp: hits.append((fr, prevhp - hp, r[45]))
        prevhp = hp
    if cur: segs.append((cur[0], cur[1], (end or n) - 1))
    print('id %2d: len %s ops %s | atk boxes %s | x %d..%d ymax %d | hits %s' % (k, (end - start) if end else '>%d' % (n - start), [(hex(o), f - start) for o, f in ops],
          [(a, f - start, t - start) for a, f, t in segs], min(xs), max(xs), max(ys), [(f - start, dmg, b) for f, dmg, b in hits]))
