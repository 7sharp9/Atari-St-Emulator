"""layout_claims.py: proves the type-6 record layout claims over every record of a snapshot: header +10 room, +11 block count, +12/+13/+14 sub-block offsets,
anim block = 10 bytes iff template+12 bit 2, mover block start/len, script span.  usage: layout_claims.py SNAP"""
import sys
from st import St
s = St(sys.argv[1])
tot = 0; c = dict(order=0, order_n=0, anim_iff=0, anim_n=0, mover14=0, mover_n=0, scr_ok=0, scr_n=0, static_n=0, static_ok=0)
bad = []
for i in range(s.count(6)):
    a = s.obj(i)
    if a is None: continue
    n = s.size(6, i); r = s.mem(a, n); t = (r[6] << 8) | r[7]; ta = s.tmpl(t)
    if ta is None: continue
    tm = s.mem(ta, 32)
    if r[15] & 0x80:
        c['static_n'] += 1; c['static_ok'] += (n == 16 and r[12] == r[13] == r[14] == 0 and r[11] == 0)
        continue
    # script span: first list of r[11] blocks at +0x10
    p = 0x10; ok = True
    for _ in range(r[11]):
        if p >= n: ok = False; break
        p += r[p]
    c['scr_n'] += 1; c['scr_ok'] += (ok and p <= r[12] and (r[12] - p) in (0, ) or (ok and p == r[12]))
    c['order_n'] += 1; ordered = p <= r[12] <= r[13] <= r[14] <= n
    c['order'] += ordered
    if not ordered: bad.append((i, 'order', r[11], p, r[12], r[13], r[14], n))
    c['anim_n'] += 1; has_anim = (n - r[14]) == 10 and ordered
    c['anim_iff'] += (has_anim == bool(tm[12] & 4))
    if has_anim != bool(tm[12] & 4): bad.append((i, 'anim', tm[12], n - r[14]))
    if tm[12] & 1 and r[3] & 0x10:
        c['mover_n'] += 1; c['mover14'] += (r[14] - r[13] >= 14)
        if r[14] - r[13] < 14: bad.append((i, 'mover', tm[12], r[3], r[13], r[14]))
print(c)
print('exceptions:', bad[:20], len(bad))
