"""census.py: census of every type-6 record header in a snapshot (id, size, +3,+10..+15, template idx and template +11,+12,+22, sub-block spans).
usage: census.py SNAP [csv-out]"""
import sys
from st import St
s = St(sys.argv[1])
rows = []
for i in range(s.count(6)):
    a = s.obj(i)
    if a is None: continue
    n = s.size(6, i); r = s.mem(a, n)
    t = (r[6] << 8) | r[7]; ta = s.tmpl(t)
    tm = s.mem(ta, 32) if ta else bytes(32)
    rows.append((i, n, r, t, tm))
print('id size  +3 +10 +11 +12 +13 +14 +15 | tmpl t11 t12 t22')
for i, n, r, t, tm in rows:
    print('%4d %4d  %02x  %02x  %02x  %02x  %02x  %02x  %02x | %4d  %02x  %02x  %02x' % (i, n, r[3], r[10], r[11], r[12], r[13], r[14], r[15], t, tm[11], tm[12], tm[22]))
