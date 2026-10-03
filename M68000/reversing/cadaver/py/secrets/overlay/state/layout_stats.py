"""layout_stats.py: for each template +12 value (and class byte +22), the distribution of (rec[13]-rec[12], rec[14]-rec[13], size-rec[14]) over every type-6 record: what sub-block sizes does the template flag byte imply?  usage: layout_stats.py SNAP"""
import sys, collections
from st import St
s = St(sys.argv[1])
d = collections.defaultdict(collections.Counter)
for i in range(s.count(6)):
    a = s.obj(i)
    if a is None: continue
    n = s.size(6, i); r = s.mem(a, n)
    t = (r[6] << 8) | r[7]; ta = s.tmpl(t)
    if not ta: continue
    tm = s.mem(ta, 32)
    d[tm[12]][(r[13] - r[12], r[14] - r[13], n - r[14], r[15] & 0x7f if False else r[15])] += 1
for k in sorted(d):
    print('tmpl+12=%02x:' % k, dict(d[k]) if len(d[k]) < 12 else dict(d[k].most_common(12)))
