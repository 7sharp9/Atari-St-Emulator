"""inst_census.py: census of the instance block (rec+rec[12], length rec[13]-rec[12]) by template class (template+22): size, and the distribution of bytes 3, 5, 6 bits.
usage: inst_census.py SNAP..."""
import sys, collections
from st import St
for snap in sys.argv[1:]:
    s = St(snap); by = collections.defaultdict(list)
    for i in range(s.count(6)):
        a = s.obj(i)
        if a is None: continue
        sz = s.size(6, i); r = s.mem(a, sz)
        if r[15] & 0x80 or r[13] <= r[12]: continue
        t = (r[6] << 8) | r[7]; tm = s.mem(s.tmpl(t), 32)
        by[tm[22]].append((i, bytes(r[r[12]:r[13]])))
    print(snap)
    for cls in sorted(by):
        L = by[cls]; sizes = collections.Counter(len(b) for _, b in L)
        def bits(k): return ''.join(str(sum(1 for _, b in L if len(b) > k and b[k] >> n & 1)) + ',' for n in range(8))
        print('  class %02x: %3d objects, block sizes %s | byte3 bit counts (b0..b7) %s | byte5 %s | byte6 %s' % (cls, len(L), dict(sizes), bits(3), bits(5), bits(6)))
