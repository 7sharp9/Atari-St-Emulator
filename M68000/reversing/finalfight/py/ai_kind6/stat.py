#!/usr/bin/env python3
"""stat.py <frames.bin> : state statistics of the kind-6 records (lives, sub-state transitions, attack ids, hurt types, evades, deaths)"""
import sys, collections
FS = 13*192 + 2*192 + 0x200
d = open(sys.argv[1], 'rb').read(); n = len(d)//FS
w = lambda r, o: int.from_bytes(r[o:o+2], 'big')
sw = lambda r, o: w(r, o) - 65536 if w(r, o) & 0x8000 else w(r, o)
def rec(fr, i): return d[fr*FS + i*192: fr*FS + (i+1)*192]
def cody(fr): return d[fr*FS + 13*192: fr*FS + 14*192]
frames23 = collections.Counter(); frames34 = collections.Counter()
trans = collections.Counter(); ids = collections.Counter(); hurt = collections.Counter(); evade = 0; deaths = 0; lives = 0
hits_on = collections.Counter(); hitevents = []
prev = {}; php = None; ops = collections.Counter(); hpdrops = collections.Counter()
for fr in range(n):
    for i in range(13):
        r = rec(fr, i)
        if not (r[0] and r[19] == 6):
            if i in prev: del prev[i]
            continue
        s2, s3, s4, s5 = r[2], r[3], r[4], r[5]
        frames23[(s2, s3)] += 1
        if s2 == 2: frames34[(s3, s4)] += 1
        p = prev.get(i)
        if p is None:
            lives += 1
        else:
            if p[1] != s3 and s2 == 2 and p[0] == 2:
                trans[(p[1], s3)] += 1
                if s3 == 6: hurt[r[63]] += 1
                if s3 == 8: evade += 1
            if p[0] != s2 and s2 == 4: deaths += 1
            if s3 == 4 and (p[3] != r[149] or p[1] != 4) and s2 == 2: ids[r[149]] += 1
            if s3 == 4 and r[154] != p[4] and s4 == 6: ops[r[154]] += 1
            if sw(r, 24) < sw(p[5], 24) if False else False: pass
        # health drop of the record -> hurt events (hp vs previous)
        php_ = p[6] if p else None
        hp = sw(r, 24)
        if p and hp < php_: hpdrops[php_ - hp] += 1
        prev[i] = (s2, s3, r[149], r[149], r[154], None, hp)
        # Cody hits
    c = cody(fr)
    if fr > 0:
        cp = cody(fr - 1)
        if sw(c, 24) < sw(cp, 24):
            # attacker: the kind-6 record with an active attack box
            for i in range(13):
                r = rec(fr - 1, i)
                if r[0] and r[19] == 6 and r[45]: hits_on[(r[20], r[45], sw(cp, 24) - sw(c, 24))] += 1
print('frames', n, 'lives', lives, 'deaths(2:2->4)', deaths)
print('frames per (2,3):', sorted(frames23.items()))
print('frames per (3,4) in main:', sorted(frames34.items()))
print('sub-state transitions (from,to):count', sorted(trans.items()))
print('attack id entries (id: count):', sorted(ids.items()))
print('ops started:', sorted((hex(k), v) for k, v in ops.items()))
print('hurt entries by type 63:', sorted(hurt.items()), 'evade entries (3 -> 8):', evade)
print('enemy hp drops:', sorted(hpdrops.items()))
print('hits on Cody (char, attack box idx, damage): count', sorted(hits_on.items()))
