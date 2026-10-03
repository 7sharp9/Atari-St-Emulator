"""f15_census.py: distribution of the rec+15 bits (non-static records) by template class (template+22) and by template +12/+23, both levels.  usage: f15_census.py SNAP..."""
import sys, collections
from st import St
for snap in sys.argv[1:]:
    s = St(snap); by = collections.defaultdict(collections.Counter); tot = collections.Counter()
    for i in range(s.count(6)):
        a = s.obj(i)
        if a is None: continue
        r = s.mem(a, s.size(6, i))
        if r[15] & 0x80: continue
        tm = s.mem(s.tmpl((r[6] << 8) | r[7]), 32)
        for b in range(7):
            if r[15] >> b & 1: by[tm[22]][b] += 1; tot[b] += 1
        by[tm[22]]['n'] += 1
    print(snap, 'bit totals', dict(sorted(tot.items())))
    for cls in sorted(by): print('   class %02x: n=%3d  %s' % (cls, by[cls]['n'], {b: v for b, v in sorted(by[cls].items(), key=lambda kv: str(kv[0])) if b != 'n'}))
